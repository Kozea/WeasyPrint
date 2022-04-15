"""Document generation management."""

import functools
import hashlib
import io
import shutil
import zlib
from os.path import basename
from urllib.parse import unquote, urlsplit

import pydyf
from fontTools import subset
from fontTools.ttLib import TTFont, TTLibError, ttFont

from . import CSS, Attachment, __version__
from .css import get_all_computed_styles
from .css.counters import CounterStyle
from .css.targets import TargetCollector
from .draw import draw_page, stacked
from .formatting_structure.build import build_formatting_structure
from .html import W3C_DATE_RE, get_html_metadata
from .images import get_image_from_uri as original_get_image_from_uri
from .layout import LayoutContext, layout_document
from .links import (
    add_links, create_bookmarks, gather_links_and_bookmarks,
    make_page_bookmark_tree, resolve_links)
from .logger import LOGGER, PROGRESS_LOGGER
from .matrix import Matrix
from .stream import Stream
from .text.fonts import FontConfiguration
from .urls import URLFetchingError


def _w3c_date_to_pdf(string, attr_name):
    """Tranform W3C date to PDF format."""
    if string is None:
        return None
    match = W3C_DATE_RE.match(string)
    if match is None:
        LOGGER.warning(f'Invalid {attr_name} date: {string!r}')
        return None
    groups = match.groupdict()
    pdf_date = ''
    found = groups['hour']
    for key in ('second', 'minute', 'hour', 'day', 'month', 'year'):
        if groups[key]:
            found = True
            pdf_date = groups[key] + pdf_date
        elif found:
            pdf_date = f'{(key in ("day", "month")):02d}{pdf_date}'
    if groups['hour']:
        assert groups['minute']
        if groups['tz_hour']:
            assert groups['tz_hour'].startswith(('+', '-'))
            assert groups['tz_minute']
            tz_hour = int(groups['tz_hour'])
            tz_minute = int(groups['tz_minute'])
            pdf_date += f"{tz_hour:+03d}'{tz_minute:02d}"
        else:
            pdf_date += 'Z'
    return pdf_date


def _write_pdf_attachment(pdf, attachment, url_fetcher):
    """Write an attachment to the PDF stream.

    :return:
        the attachment PDF dictionary.

    """
    # Attachments from document links like <link> or <a> can only be URLs.
    # They're passed in as tuples
    url = ''
    if isinstance(attachment, tuple):
        url, description = attachment
        attachment = Attachment(
            url=url, url_fetcher=url_fetcher, description=description)
    elif not isinstance(attachment, Attachment):
        attachment = Attachment(guess=attachment, url_fetcher=url_fetcher)

    try:
        with attachment.source as (source_type, source, url, _):
            if isinstance(source, bytes):
                source = io.BytesIO(source)
            uncompressed_length = 0
            stream = b''
            md5 = hashlib.md5()
            compress = zlib.compressobj()
            for data in iter(lambda: source.read(4096), b''):
                uncompressed_length += len(data)
                md5.update(data)
                compressed = compress.compress(data)
                stream += compressed
            compressed = compress.flush(zlib.Z_FINISH)
            stream += compressed
            file_extra = pydyf.Dictionary({
                'Type': '/EmbeddedFile',
                'Filter': '/FlateDecode',
                'Params': pydyf.Dictionary({
                    'CheckSum': f'<{md5.hexdigest()}>',
                    'Size': uncompressed_length,
                })
            })
            file_stream = pydyf.Stream([stream], file_extra)
            pdf.add_object(file_stream)

    except URLFetchingError as exception:
        LOGGER.error('Failed to load attachment: %s', exception)
        return

    # TODO: Use the result object from a URL fetch operation to provide more
    # details on the possible filename.
    if url and urlsplit(url).path:
        filename = basename(unquote(urlsplit(url).path))
    else:
        filename = 'attachment.bin'

    attachment = pydyf.Dictionary({
        'Type': '/Filespec',
        'F': pydyf.String(),
        'UF': pydyf.String(filename),
        'EF': pydyf.Dictionary({'F': file_stream.reference}),
        'Desc': pydyf.String(attachment.description or ''),
    })
    pdf.add_object(attachment)
    return attachment


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

        #: The :obj:`list` of ``(link_type, target, rectangle)`` :obj:`tuples
        #: <tuple>`. A ``rectangle`` is ``(x, y, width, height)``, in CSS
        #: pixels from the top-left of the page. ``link_type`` is one of three
        #: strings:
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

        gather_links_and_bookmarks(
            page_box, self.anchors, self.links, self.bookmarks)
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
                 attachments=None):
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
        #: `W3C’s profile of ISO 8601 <http://www.w3.org/TR/NOTE-datetime>`_.
        #: Extracted from the ``<meta name=dcterms.created>`` element in HTML
        #: and written to the ``/CreationDate`` info field in PDF.
        self.created = created
        #: The modification date of the document, as a string or :obj:`None`.
        #: Dates are in one of the six formats specified in
        #: `W3C’s profile of ISO 8601 <http://www.w3.org/TR/NOTE-datetime>`_.
        #: Extracted from the ``<meta name=dcterms.modified>`` element in HTML
        #: and written to the ``/ModDate`` info field in PDF.
        self.modified = modified
        #: File attachments, as a list of tuples of URL and a description or
        #: :obj:`None`. (Defaults to the empty list.)
        #: Extracted from the ``<link rel=attachment>`` elements in HTML
        #: and written to the ``/EmbeddedFiles`` dictionary in PDF.
        self.attachments = attachments or []


class Document:
    """A rendered document ready to be painted in a pydyf stream.

    Typically obtained from :meth:`HTML.render() <weasyprint.HTML.render>`, but
    can also be instantiated directly with a list of :class:`pages <Page>`, a
    set of :class:`metadata <DocumentMetadata>`, a :func:`url_fetcher
    <weasyprint.default_url_fetcher>` function, and a :class:`font_config
    <weasyprint.text.fonts.FontConfiguration>`.

    """

    @classmethod
    def _build_layout_context(cls, html, stylesheets,
                              presentational_hints=False,
                              optimize_size=('fonts',), font_config=None,
                              counter_style=None, image_cache=None):
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
            counter_style, page_rules, target_collector)
        get_image_from_uri = functools.partial(
            original_get_image_from_uri, cache=image_cache,
            url_fetcher=html.url_fetcher, optimize_size=optimize_size)
        PROGRESS_LOGGER.info('Step 4 - Creating formatting structure')
        context = LayoutContext(
            style_for, get_image_from_uri, font_config, counter_style,
            target_collector)
        return context

    @classmethod
    def _render(cls, html, stylesheets, presentational_hints=False,
                optimize_size=('fonts',), font_config=None, counter_style=None,
                image_cache=None):
        if font_config is None:
            font_config = FontConfiguration()

        if counter_style is None:
            counter_style = CounterStyle()

        context = cls._build_layout_context(
            html, stylesheets, presentational_hints, optimize_size,
            font_config, counter_style, image_cache)

        root_box = build_formatting_structure(
            html.etree_element, context.style_for, context.get_image_from_uri,
            html.base_url, context.target_collector, counter_style,
            context.footnotes)

        page_boxes = layout_document(html, root_box, context)
        rendering = cls(
            [Page(page_box) for page_box in page_boxes],
            DocumentMetadata(**get_html_metadata(html)),
            html.url_fetcher, font_config, optimize_size)
        return rendering

    def _reference_resources(self, pdf, resources, images, fonts):
        if 'Font' in resources:
            assert resources['Font'] is None
            resources['Font'] = fonts
        self._use_references(pdf, resources, images)
        pdf.add_object(resources)
        return resources.reference

    def _use_references(self, pdf, resources, images):
        # XObjects
        for key, x_object in resources.get('XObject', {}).items():
            # Images
            if x_object is None:
                x_object = images[key]
                if x_object.number is not None:
                    # Image already added to PDF
                    resources['XObject'][key] = x_object.reference
                    continue

            pdf.add_object(x_object)
            resources['XObject'][key] = x_object.reference

            # Masks
            if 'SMask' in x_object.extra:
                pdf.add_object(x_object.extra['SMask'])
                x_object.extra['SMask'] = x_object.extra['SMask'].reference

            # Resources
            if 'Resources' in x_object.extra:
                x_object.extra['Resources'] = self._reference_resources(
                    pdf, x_object.extra['Resources'], images,
                    resources['Font'])

        # Patterns
        for key, pattern in resources.get('Pattern', {}).items():
            pdf.add_object(pattern)
            resources['Pattern'][key] = pattern.reference
            if 'Resources' in pattern.extra:
                pattern.extra['Resources'] = self._reference_resources(
                    pdf, pattern.extra['Resources'], images, resources['Font'])

        # Shadings
        for key, shading in resources.get('Shading', {}).items():
            pdf.add_object(shading)
            resources['Shading'][key] = shading.reference

        # Alpha states
        for key, alpha in resources.get('ExtGState', {}).items():
            if 'SMask' in alpha and 'G' in alpha['SMask']:
                alpha['SMask']['G'] = alpha['SMask']['G'].reference

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
        self._font_config = font_config
        # Set of flags for PDF size optimization. Can contain "images" and
        # "fonts".
        self._optimize_size = optimize_size

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
            pages, self.metadata, self.url_fetcher, self._font_config,
            self._optimize_size)

    def make_bookmark_tree(self):
        """Make a tree of all bookmarks in the document.

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
        matrix = Matrix()
        for page_number, page in enumerate(self.pages):
            previous_level = make_page_bookmark_tree(
                page, skipped_levels, last_by_depth, previous_level,
                page_number, matrix)
        return root

    def write_pdf(self, target=None, zoom=1, attachments=None, finisher=None):
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
        :returns:
            The PDF as :obj:`bytes` if ``target`` is not provided or
            :obj:`None`, otherwise :obj:`None` (the PDF is written to
            ``target``).

        """
        # 0.75 = 72 PDF point per inch / 96 CSS pixel per inch
        scale = zoom * 0.75

        PROGRESS_LOGGER.info('Step 6 - Creating PDF')

        pdf = pydyf.PDF()
        states = pydyf.Dictionary()
        x_objects = pydyf.Dictionary()
        patterns = pydyf.Dictionary()
        shadings = pydyf.Dictionary()
        images = {}
        resources = pydyf.Dictionary({
            'ExtGState': states,
            'XObject': x_objects,
            'Pattern': patterns,
            'Shading': shadings,
        })
        pdf.add_object(resources)
        pdf_names = []

        # Links and anchors
        page_links_and_anchors = list(resolve_links(self.pages))
        attachment_links = [
            [link for link in page_links if link[0] == 'attachment']
            for page_links, page_anchors in page_links_and_anchors]

        # Annotations
        annot_files = {}
        # A single link can be split in multiple regions. We don't want to
        # embed a file multiple times of course, so keep a reference to every
        # embedded URL and reuse the object number.
        for page_links in attachment_links:
            for link_type, annot_target, rectangle, _ in page_links:
                if link_type == 'attachment' and target not in annot_files:
                    # TODO: Use the title attribute as description. The comment
                    # above about multiple regions won't always be correct,
                    # because two links might have the same href, but different
                    # titles.
                    annot_files[annot_target] = _write_pdf_attachment(
                        pdf, (annot_target, None), self.url_fetcher)

        # Bookmarks
        root = []
        # At one point in the document, for each "output" depth, how much
        # to add to get the source level (CSS values of bookmark-level).
        # E.g. with <h1> then <h3>, level_shifts == [0, 1]
        # 1 means that <h3> has depth 3 - 1 = 2 in the output.
        skipped_levels = []
        last_by_depth = [root]
        previous_level = 0

        for page_number, (page, links_and_anchors, page_links) in enumerate(
                zip(self.pages, page_links_and_anchors, attachment_links)):
            # Draw from the top-left corner
            matrix = Matrix(scale, 0, 0, -scale, 0, page.height * scale)

            # Links and anchors
            links, anchors = links_and_anchors

            page_width = scale * (
                page.width + page.bleed['left'] + page.bleed['right'])
            page_height = scale * (
                page.height + page.bleed['top'] + page.bleed['bottom'])
            left = -scale * page.bleed['left']
            top = -scale * page.bleed['top']
            right = left + page_width
            bottom = top + page_height

            page_rectangle = (
                left / scale, top / scale,
                (right - left) / scale, (bottom - top) / scale)
            stream = Stream(
                self, page_rectangle, states, x_objects, patterns, shadings,
                images)
            stream.transform(d=-1, f=(page.height * scale))
            page.paint(stream, scale=scale)
            pdf.add_object(stream)

            pdf_page = pydyf.Dictionary({
                'Type': '/Page',
                'Parent': pdf.pages.reference,
                'MediaBox': pydyf.Array([left, top, right, bottom]),
                'Contents': stream.reference,
                'Resources': resources.reference,
            })
            pdf.add_page(pdf_page)

            add_links(links, anchors, matrix, pdf, pdf_page, pdf_names)

            # Bleed
            bleed = {key: value * 0.75 for key, value in page.bleed.items()}

            trim_left = left + bleed['left']
            trim_top = top + bleed['top']
            trim_right = right - bleed['right']
            trim_bottom = bottom - bleed['bottom']

            # Arbitrarly set PDF BleedBox between CSS bleed box (MediaBox) and
            # CSS page box (TrimBox) at most 10 points from the TrimBox.
            bleed_left = trim_left - min(10, bleed['left'])
            bleed_top = trim_top - min(10, bleed['top'])
            bleed_right = trim_right + min(10, bleed['right'])
            bleed_bottom = trim_bottom + min(10, bleed['bottom'])

            pdf_page['TrimBox'] = pydyf.Array([
                trim_left, trim_top, trim_right, trim_bottom])
            pdf_page['BleedBox'] = pydyf.Array([
                bleed_left, bleed_top, bleed_right, bleed_bottom])

            # Annotations
            # TODO: splitting a link into multiple independent rectangular
            # annotations works well for pure links, but rather mediocre for
            # other annotations and fails completely for transformed (CSS) or
            # complex link shapes (area). It would be better to use /AP for all
            # links and coalesce link shapes that originate from the same HTML
            # link. This would give a feeling similiar to what browsers do with
            # links that span multiple lines.
            for link_type, annot_target, rectangle, _ in page_links:
                annot_file = annot_files[annot_target]
                if link_type == 'attachment' and annot_file is not None:
                    rectangle = (
                        *matrix.transform_point(*rectangle[:2]),
                        *matrix.transform_point(*rectangle[2:]))
                    annot = pydyf.Dictionary({
                        'Type': '/Annot',
                        'Rect': pydyf.Array(rectangle),
                        'Subtype': '/FileAttachment',
                        'T': pydyf.String(),
                        'FS': annot_file.reference,
                        'AP': pydyf.Dictionary({'N': pydyf.Stream([], {
                            'Type': '/XObject',
                            'Subtype': '/Form',
                            'BBox': pydyf.Array(rectangle),
                            'Length': 0,
                        })})
                    })
                    pdf.add_object(annot)
                    if 'Annots' not in pdf_page:
                        pdf_page['Annots'] = pydyf.Array()
                    pdf_page['Annots'].append(annot.reference)

            # Bookmarks
            previous_level = make_page_bookmark_tree(
                page, skipped_levels, last_by_depth, previous_level,
                page_number, matrix)

        # Outlines
        outlines, count = create_bookmarks(root, pdf)
        if outlines:
            outlines_dictionary = pydyf.Dictionary({
                'Count': count,
                'First': outlines[0].reference,
                'Last': outlines[-1].reference,
            })
            pdf.add_object(outlines_dictionary)
            for outline in outlines:
                outline['Parent'] = outlines_dictionary.reference
            pdf.catalog['Outlines'] = outlines_dictionary.reference

        PROGRESS_LOGGER.info('Step 7 - Adding PDF metadata')

        # PDF information
        if self.metadata.title:
            pdf.info['Title'] = pydyf.String(self.metadata.title)
        if self.metadata.authors:
            pdf.info['Author'] = pydyf.String(
                ', '.join(self.metadata.authors))
        if self.metadata.description:
            pdf.info['Subject'] = pydyf.String(self.metadata.description)
        if self.metadata.keywords:
            pdf.info['Keywords'] = pydyf.String(
                ', '.join(self.metadata.keywords))
        if self.metadata.generator:
            pdf.info['Creator'] = pydyf.String(self.metadata.generator)
        pdf.info['Producer'] = pydyf.String(f'WeasyPrint {__version__}')
        if self.metadata.created:
            pdf.info['CreationDate'] = pydyf.String(
                _w3c_date_to_pdf(self.metadata.created, 'created'))
        if self.metadata.modified:
            pdf.info['ModDate'] = pydyf.String(
                _w3c_date_to_pdf(self.metadata.modified, 'modified'))

        # Embedded files
        attachments = self.metadata.attachments + (attachments or [])
        pdf_attachments = []
        for attachment in attachments:
            pdf_attachment = _write_pdf_attachment(
                pdf, attachment, self.url_fetcher)
            if pdf_attachment is not None:
                pdf_attachments.append(pdf_attachment)
        if pdf_attachments:
            content = pydyf.Dictionary({'Names': pydyf.Array()})
            for i, pdf_attachment in enumerate(pdf_attachments):
                content['Names'].append(pydyf.String(f'attachment{i}'))
                content['Names'].append(pdf_attachment.reference)
            pdf.add_object(content)
            if 'Names' not in pdf.catalog:
                pdf.catalog['Names'] = pydyf.Dictionary()
            pdf.catalog['Names']['EmbeddedFiles'] = content.reference

        # Embeded fonts
        pdf_fonts = pydyf.Dictionary()
        fonts_by_file_hash = {}
        for font in self.fonts.values():
            fonts_by_file_hash.setdefault(font.hash, []).append(font)
        font_references_by_file_hash = {}
        for file_hash, fonts in fonts_by_file_hash.items():
            content = fonts[0].file_content

            if 'fonts' in self._optimize_size:
                # Optimize font
                cmap = {}
                for font in fonts:
                    cmap = {**cmap, **font.cmap}
                full_font = io.BytesIO(content)
                optimized_font = io.BytesIO()
                options = subset.Options(
                    retain_gids=True, passthrough_tables=True,
                    ignore_missing_glyphs=True, hinting=False)
                options.drop_tables += ['GSUB', 'GPOS', 'SVG']
                subsetter = subset.Subsetter(options)
                subsetter.populate(gids=cmap)
                try:
                    ttfont = TTFont(full_font, fontNumber=fonts[0].index)
                    subsetter.subset(ttfont)
                except TTLibError:
                    LOGGER.warning('Unable to optimize font')
                else:
                    ttfont.save(optimized_font)
                    content = optimized_font.getvalue()

            if fonts[0].png or fonts[0].svg:
                # Add empty glyphs instead of PNG or SVG emojis
                full_font = io.BytesIO(content)
                try:
                    ttfont = TTFont(full_font, fontNumber=fonts[0].index)
                    if 'loca' not in ttfont or 'glyf' not in ttfont:
                        ttfont['loca'] = ttFont.getTableClass('loca')()
                        ttfont['glyf'] = ttFont.getTableClass('glyf')()
                        ttfont['glyf'].glyphOrder = ttfont.getGlyphOrder()
                        ttfont['glyf'].glyphs = {
                            name: ttFont.getTableModule('glyf').Glyph()
                            for name in ttfont['glyf'].glyphOrder}
                    else:
                        for glyph in ttfont['glyf'].glyphs:
                            ttfont['glyf'][glyph] = (
                                ttFont.getTableModule('glyf').Glyph())
                    for table_name in ('CBDT', 'CBLC', 'SVG '):
                        if table_name in ttfont:
                            del ttfont[table_name]
                    output_font = io.BytesIO()
                    ttfont.save(output_font)
                    content = output_font.getvalue()
                except TTLibError:
                    LOGGER.warning('Unable to save emoji font')

            # Include font
            font_type = 'otf' if content[:4] == b'OTTO' else 'ttf'
            if font_type == 'otf':
                font_extra = pydyf.Dictionary({'Subtype': '/OpenType'})
            else:
                font_extra = pydyf.Dictionary({'Length1': len(content)})
            font_stream = pydyf.Stream([content], font_extra, compress=True)
            pdf.add_object(font_stream)
            font_references_by_file_hash[file_hash] = font_stream.reference

        for font in self.fonts.values():
            widths = pydyf.Array()
            for i in sorted(font.widths):
                if i - 1 not in font.widths:
                    widths.append(i)
                    current_widths = pydyf.Array()
                    widths.append(current_widths)
                current_widths.append(font.widths[i])
            font_type = 'otf' if font.file_content[:4] == b'OTTO' else 'ttf'
            font_descriptor = pydyf.Dictionary({
                'Type': '/FontDescriptor',
                'FontName': font.name,
                'FontFamily': pydyf.String(font.family),
                'Flags': font.flags,
                'FontBBox': pydyf.Array(font.bbox),
                'ItalicAngle': font.italic_angle,
                'Ascent': font.ascent,
                'Descent': font.descent,
                'CapHeight': font.bbox[3],
                'StemV': font.stemv,
                'StemH': font.stemh,
                (f'FontFile{3 if font_type == "otf" else 2}'):
                    font_references_by_file_hash[font.hash],
            })
            if font_type == 'otf':
                font_descriptor['Subtype'] = '/OpenType'
            pdf.add_object(font_descriptor)
            subfont_dictionary = pydyf.Dictionary({
                'Type': '/Font',
                'Subtype': f'/CIDFontType{0 if font_type == "otf" else 2}',
                'BaseFont': font.name,
                'CIDSystemInfo': pydyf.Dictionary({
                    'Registry': pydyf.String('Adobe'),
                    'Ordering': pydyf.String('Identity'),
                    'Supplement': 0,
                }),
                'W': widths,
                'FontDescriptor': font_descriptor.reference,
            })
            pdf.add_object(subfont_dictionary)
            to_unicode = pydyf.Stream([
                b'/CIDInit /ProcSet findresource begin',
                b'12 dict begin',
                b'begincmap',
                b'/CIDSystemInfo',
                b'<< /Registry (Adobe)',
                b'/Ordering (UCS)',
                b'/Supplement 0',
                b'>> def',
                b'/CMapName /Adobe-Identity-UCS def',
                b'/CMapType 2 def',
                b'1 begincodespacerange',
                b'<0000> <ffff>',
                b'endcodespacerange',
                f'{len(font.cmap)} beginbfchar'.encode()])
            for glyph, text in font.cmap.items():
                unicode_codepoints = ''.join(
                    f'{letter.encode("utf-16-be").hex()}' for letter in text)
                to_unicode.stream.append(
                    f'<{glyph:04x}> <{unicode_codepoints}>'.encode())
            to_unicode.stream.extend([
                b'endbfchar',
                b'endcmap',
                b'CMapName currentdict /CMap defineresource pop',
                b'end',
                b'end'])
            pdf.add_object(to_unicode)
            font_dictionary = pydyf.Dictionary({
                'Type': '/Font',
                'Subtype': '/Type0',
                'BaseFont': font.name,
                'Encoding': '/Identity-H',
                'DescendantFonts': pydyf.Array([subfont_dictionary.reference]),
                'ToUnicode': to_unicode.reference,
            })
            pdf.add_object(font_dictionary)
            pdf_fonts[font.hash] = font_dictionary.reference

        pdf.add_object(pdf_fonts)
        resources['Font'] = pdf_fonts.reference
        self._use_references(pdf, resources, images)

        # Anchors
        if pdf_names:
            # Anchors are name trees that have to be sorted
            name_array = pydyf.Array()
            for anchor in sorted(pdf_names):
                name_array.append(pydyf.String(anchor[0]))
                name_array.append(anchor[1])
            pdf.catalog['Names'] = pydyf.Dictionary(
                {'Dests': pydyf.Dictionary({'Names': name_array})})

        if finisher:
            finisher(self, pdf)

        file_obj = io.BytesIO()
        pdf.write(file_obj)

        if target is None:
            return file_obj.getvalue()
        else:
            file_obj.seek(0)
            if hasattr(target, 'write'):
                shutil.copyfileobj(file_obj, target)
            else:
                with open(target, 'wb') as fd:
                    shutil.copyfileobj(file_obj, fd)
