"""Document generation management."""

import functools
import io
import shutil

from . import CSS
from .anchors import gather_anchors, make_page_bookmark_tree
from .css import get_all_computed_styles
from .css.counters import CounterStyle
from .css.targets import TargetCollector
from .draw import draw_page, stacked
from .formatting_structure.build import build_formatting_structure
from .html import get_html_metadata
from .images import get_image_from_uri as original_get_image_from_uri
from .layout import LayoutContext, layout_document
from .logger import PROGRESS_LOGGER
from .matrix import Matrix
from .pdf import generate_pdf
from .text.fonts import FontConfiguration


class Page:
    """Represents a single rendered page.

    Should be obtained from :attr:`Document.pages` but not
    instantiated directly.

    """
    def __init__(self, page_box):
        #: The page width, including margins, in CSS pixels.
        self.width = page_box.margin_width()

        #: The page height, including margins, in CSS pixels.
        self.height = page_box.margin_height()

        #: The page bleed widths as a :obj:`dict` with ``'top'``, ``'right'``,
        #: ``'bottom'`` and ``'left'`` as keys, and values in CSS pixels.
        self.bleed = {
            side: page_box.style[f'bleed_{side}'].value
            for side in ('top', 'right', 'bottom', 'left')}

        #: The :obj:`list` of ``(level, label, target, state)``
        #: :obj:`tuples <tuple>`. ``level`` and ``label`` are respectively an
        #: :obj:`int` and a :obj:`string <str>`, based on the CSS properties
        #: of the same names. ``target`` is an ``(x, y)`` point in CSS pixels
        #: from the top-left of the page.
        self.bookmarks = []

        #: The :obj:`list` of ``(link_type, target, rectangle, box)``
        #: :obj:`tuples <tuple>`. A ``rectangle`` is ``(x, y, width, height)``,
        #: in CSS pixels from the top-left of the page. ``link_type`` is one of
        #: three strings:
        #:
        #: * ``'external'``: ``target`` is an absolute URL
        #: * ``'internal'``: ``target`` is an anchor name (see
        #:   :attr:`Page.anchors`).
        #:   The anchor might be defined in another page,
        #:   in multiple pages (in which case the first occurence is used),
        #:   or not at all.
        #: * ``'attachment'``: ``target`` is an absolute URL and points
        #:   to a resource to attach to the document.
        self.links = []

        #: The :obj:`dict` mapping each anchor name to its target, an
        #: ``(x, y)`` point in CSS pixels from the top-left of the page.
        self.anchors = {}

        #: The :obj:`list` of ``(element, attributes, rectangle)`` :obj:`tuples
        #: <tuple>`. A ``rectangle`` is ``(x, y, width, height)``, in CSS
        #: pixels from the top-left of the page. ``atributes`` is a
        #: :obj:`dict` of HTML tag attributes and values.
        self.inputs = []

        gather_anchors(
            page_box, self.anchors, self.links, self.bookmarks, self.inputs)
        self._page_box = page_box

    def paint(self, stream, left_x=0, top_y=0, scale=1, clip=False):
        """Paint the page into the PDF file.

        :type stream: ``document.Stream``
        :param stream:
            A document stream.
        :param float left_x:
            X coordinate of the left of the page, in PDF points.
        :param float top_y:
            Y coordinate of the top of the page, in PDF points.
        :param float scale:
            Zoom scale.
        :param bool clip:
            Whether to clip/cut content outside the page. If false or
            not provided, content can overflow.

        """
        with stacked(stream):
            # Make (0, 0) the top-left corner, and make user units CSS pixels:
            stream.transform(a=scale, d=scale, e=left_x, f=top_y)
            if clip:
                stream.rectangle(0, 0, self.width, self.height)
                stream.clip()
            draw_page(self._page_box, stream)


class DocumentMetadata:
    """Meta-information belonging to a whole :class:`Document`.

    New attributes may be added in future versions of WeasyPrint.

    """
    def __init__(self, title=None, authors=None, description=None,
                 keywords=None, generator=None, created=None, modified=None,
                 attachments=None, lang=None, custom=None):
        #: The title of the document, as a string or :obj:`None`.
        #: Extracted from the ``<title>`` element in HTML
        #: and written to the ``/Title`` info field in PDF.
        self.title = title
        #: The authors of the document, as a list of strings.
        #: (Defaults to the empty list.)
        #: Extracted from the ``<meta name=author>`` elements in HTML
        #: and written to the ``/Author`` info field in PDF.
        self.authors = authors or []
        #: The description of the document, as a string or :obj:`None`.
        #: Extracted from the ``<meta name=description>`` element in HTML
        #: and written to the ``/Subject`` info field in PDF.
        self.description = description
        #: Keywords associated with the document, as a list of strings.
        #: (Defaults to the empty list.)
        #: Extracted from ``<meta name=keywords>`` elements in HTML
        #: and written to the ``/Keywords`` info field in PDF.
        self.keywords = keywords or []
        #: The name of one of the software packages
        #: used to generate the document, as a string or :obj:`None`.
        #: Extracted from the ``<meta name=generator>`` element in HTML
        #: and written to the ``/Creator`` info field in PDF.
        self.generator = generator
        #: The creation date of the document, as a string or :obj:`None`.
        #: Dates are in one of the six formats specified in
        #: `W3C’s profile of ISO 8601 <https://www.w3.org/TR/NOTE-datetime>`_.
        #: Extracted from the ``<meta name=dcterms.created>`` element in HTML
        #: and written to the ``/CreationDate`` info field in PDF.
        self.created = created
        #: The modification date of the document, as a string or :obj:`None`.
        #: Dates are in one of the six formats specified in
        #: `W3C’s profile of ISO 8601 <https://www.w3.org/TR/NOTE-datetime>`_.
        #: Extracted from the ``<meta name=dcterms.modified>`` element in HTML
        #: and written to the ``/ModDate`` info field in PDF.
        self.modified = modified
        #: File attachments, as a list of tuples of URL and a description or
        #: :obj:`None`. (Defaults to the empty list.)
        #: Extracted from the ``<link rel=attachment>`` elements in HTML
        #: and written to the ``/EmbeddedFiles`` dictionary in PDF.
        self.attachments = attachments or []
        #: Document language as BCP 47 language tags.
        #: Extracted from ``<html lang=lang>`` in HTML.
        self.lang = lang
        #: Custom metadata, as a dict whose keys are the metadata names and
        #: values are the metadata values.
        self.custom = custom or {}


class Document:
    """A rendered document ready to be painted in a pydyf stream.

    Typically obtained from :meth:`HTML.render() <weasyprint.HTML.render>`, but
    can also be instantiated directly with a list of :class:`pages <Page>`, a
    set of :class:`metadata <DocumentMetadata>`, a :func:`url_fetcher
    <weasyprint.default_url_fetcher>` function, and a :class:`font_config
    <weasyprint.text.fonts.FontConfiguration>`.

    """

    @classmethod
    def _build_layout_context(cls, html, stylesheets, presentational_hints,
                              optimize_size, font_config, counter_style,
                              image_cache, forms):
        if font_config is None:
            font_config = FontConfiguration()
        if counter_style is None:
            counter_style = CounterStyle()
        target_collector = TargetCollector()
        page_rules = []
        user_stylesheets = []
        image_cache = {} if image_cache is None else image_cache
        for css in stylesheets or []:
            if not hasattr(css, 'matcher'):
                css = CSS(
                    guess=css, media_type=html.media_type,
                    font_config=font_config, counter_style=counter_style)
            user_stylesheets.append(css)
        style_for = get_all_computed_styles(
            html, user_stylesheets, presentational_hints, font_config,
            counter_style, page_rules, target_collector, forms)
        get_image_from_uri = functools.partial(
            original_get_image_from_uri, cache=image_cache,
            url_fetcher=html.url_fetcher, optimize_size=optimize_size)
        PROGRESS_LOGGER.info('Step 4 - Creating formatting structure')
        context = LayoutContext(
            style_for, get_image_from_uri, font_config, counter_style,
            target_collector)
        return context

    @classmethod
    def _render(cls, html, stylesheets, presentational_hints, optimize_size,
                font_config, counter_style, image_cache, forms):
        if font_config is None:
            font_config = FontConfiguration()

        if counter_style is None:
            counter_style = CounterStyle()

        context = cls._build_layout_context(
            html, stylesheets, presentational_hints, optimize_size,
            font_config, counter_style, image_cache, forms)

        root_box = build_formatting_structure(
            html.etree_element, context.style_for, context.get_image_from_uri,
            html.base_url, context.target_collector, counter_style,
            context.footnotes)

        page_boxes = layout_document(html, root_box, context)
        rendering = cls(
            [Page(page_box) for page_box in page_boxes],
            DocumentMetadata(**get_html_metadata(html)),
            html.url_fetcher, font_config, optimize_size)
        rendering._html = html
        return rendering

    def __init__(self, pages, metadata, url_fetcher, font_config,
                 optimize_size):
        #: A list of :class:`Page` objects.
        self.pages = pages
        #: A :class:`DocumentMetadata` object.
        #: Contains information that does not belong to a specific page
        #: but to the whole document.
        self.metadata = metadata
        #: A function or other callable with the same signature as
        #: :func:`weasyprint.default_url_fetcher` called to fetch external
        #: resources such as stylesheets and images. (See :ref:`URL Fetchers`.)
        self.url_fetcher = url_fetcher
        #: A :obj:`dict` of fonts used by the document. Keys are hashes used to
        #: identify fonts, values are ``Font`` objects.
        self.fonts = {}

        # Keep a reference to font_config to avoid its garbage collection until
        # rendering is destroyed. This is needed as font_config.__del__ removes
        # fonts that may be used when rendering
        self.font_config = font_config
        # Set of flags for PDF size optimization. Can contain "images" and
        # "fonts".
        self._optimize_size = optimize_size

    def build_element_structure(self, structure, etree_element=None):
        if etree_element is None:
            etree_element = self._html.etree_element
            structure[etree_element] = {'parent': None}
        for child in etree_element:
            structure[child] = {'parent': etree_element}
            self.build_element_structure(structure, child)

    def copy(self, pages='all'):
        """Take a subset of the pages.

        :type pages: :term:`iterable`
        :param pages:
            An iterable of :class:`Page` objects from :attr:`pages`.
        :return:
            A new :class:`Document` object.

        Examples:

        Write two PDF files for odd-numbered and even-numbered pages::

            # Python lists count from 0 but pages are numbered from 1.
            # [::2] is a slice of even list indexes but odd-numbered pages.
            document.copy(document.pages[::2]).write_pdf('odd_pages.pdf')
            document.copy(document.pages[1::2]).write_pdf('even_pages.pdf')

        Combine multiple documents into one PDF file,
        using metadata from the first::

            all_pages = [p for doc in documents for p in doc.pages]
            documents[0].copy(all_pages).write_pdf('combined.pdf')

        """
        if pages == 'all':
            pages = self.pages
        elif not isinstance(pages, list):
            pages = list(pages)
        return type(self)(
            pages, self.metadata, self.url_fetcher, self.font_config,
            self._optimize_size)

    def make_bookmark_tree(self, scale=1, transform_pages=False):
        """Make a tree of all bookmarks in the document.

        :param float scale:
            Zoom scale.
        :param bool transform_pages:
            A boolean defining whether the default PDF page transformation
            matrix has to be applied to bookmark coordinates, setting the
            bottom-left corner as the origin.
        :return: A list of bookmark subtrees.
            A subtree is ``(label, target, children, state)``. ``label`` is
            a string, ``target`` is ``(page_number, x, y)``  and ``children``
            is a list of child subtrees.

        """
        root = []
        # At one point in the document, for each "output" depth, how much
        # to add to get the source level (CSS values of bookmark-level).
        # E.g. with <h1> then <h3>, level_shifts == [0, 1]
        # 1 means that <h3> has depth 3 - 1 = 2 in the output.
        skipped_levels = []
        last_by_depth = [root]
        previous_level = 0
        for page_number, page in enumerate(self.pages):
            if transform_pages:
                matrix = Matrix(a=scale, d=-scale, f=page.height * scale)
            else:
                matrix = Matrix(a=scale, d=scale)
            previous_level = make_page_bookmark_tree(
                page, skipped_levels, last_by_depth, previous_level,
                page_number, matrix)
        return root

    def write_pdf(self, target=None, zoom=1, attachments=None, finisher=None,
                  identifier=None, variant=None, version=None,
                  custom_metadata=False):
        """Paint the pages in a PDF file, with metadata.

        :type target:
            :class:`str`, :class:`pathlib.Path` or :term:`file object`
        :param target:
            A filename where the PDF file is generated, a file object, or
            :obj:`None`.
        :param float zoom:
            The zoom factor in PDF units per CSS units.  **Warning**:
            All CSS units are affected, including physical units like
            ``cm`` and named sizes like ``A4``.  For values other than
            1, the physical CSS units will thus be "wrong".
        :param list attachments: A list of additional file attachments for the
            generated PDF document or :obj:`None`. The list's elements are
            :class:`weasyprint.Attachment` objects, filenames, URLs or
            file-like objects.
        :param finisher: A finisher function, that accepts the document and a
            :class:`pydyf.PDF` object as parameters, can be passed to perform
            post-processing on the PDF right before the trailer is written.
        :param bytes identifier: A bytestring used as PDF file identifier.
        :param str variant: A PDF variant name.
        :param str version: A PDF version number.
        :param bool custom_metadata: A boolean defining whether custom HTML
            metadata should be stored in the generated PDF.
        :returns:
            The PDF as :obj:`bytes` if ``target`` is not provided or
            :obj:`None`, otherwise :obj:`None` (the PDF is written to
            ``target``).

        """
        pdf = generate_pdf(
            self, target, zoom, attachments, self._optimize_size, identifier,
            variant, version, custom_metadata)

        if finisher:
            finisher(self, pdf)

        output = io.BytesIO()
        pdf.write(output, version=pdf.version, identifier=identifier)

        if target is None:
            return output.getvalue()
        else:
            output.seek(0)
            if hasattr(target, 'write'):
                shutil.copyfileobj(output, target)
            else:
                with open(target, 'wb') as fd:
                    shutil.copyfileobj(output, fd)
