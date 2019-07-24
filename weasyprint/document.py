"""
    weasyprint.document
    -------------------

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import collections
import functools
import io
import math
import shutil
import warnings

import cairocffi as cairo
from weasyprint.layout import LayoutContext

from . import CSS
from .css import get_all_computed_styles
from .css.targets import TargetCollector
from .draw import draw_page, stacked
from .fonts import FontConfiguration
from .formatting_structure import boxes
from .formatting_structure.build import build_formatting_structure
from .html import W3C_DATE_RE
from .images import get_image_from_uri as original_get_image_from_uri
from .layout import layout_document
from .layout.percentages import percentage
from .logger import LOGGER, PROGRESS_LOGGER
from .pdf import write_pdf_metadata

if cairo.cairo_version() < 11504:
    warnings.warn(
        'There are known rendering problems and missing features with '
        'cairo < 1.15.4. WeasyPrint may work with older versions, but please '
        'read the note about the needed cairo version on the "Install" page '
        'of the documentation before reporting bugs. '
        'http://weasyprint.readthedocs.io/en/latest/install.html')


def _get_matrix(box):
    """Return the matrix for the CSS transforms on this box.

    :returns: a :class:`cairocffi.Matrix` object or :obj:`None`.

    """
    # "Transforms apply to block-level and atomic inline-level elements,
    #  but do not apply to elements which may be split into
    #  multiple inline-level boxes."
    # http://www.w3.org/TR/css3-2d-transforms/#introduction
    if box.style['transform'] and not isinstance(box, boxes.InlineBox):
        border_width = box.border_width()
        border_height = box.border_height()
        origin_x, origin_y = box.style['transform_origin']
        offset_x = percentage(origin_x, border_width)
        offset_y = percentage(origin_y, border_height)
        origin_x = box.border_box_x() + offset_x
        origin_y = box.border_box_y() + offset_y

        matrix = cairo.Matrix()
        matrix.translate(origin_x, origin_y)
        for name, args in box.style['transform']:
            if name == 'scale':
                matrix.scale(*args)
            elif name == 'rotate':
                matrix.rotate(args)
            elif name == 'translate':
                translate_x, translate_y = args
                matrix.translate(
                    percentage(translate_x, border_width),
                    percentage(translate_y, border_height),
                )
            else:
                if name == 'skewx':
                    args = (1, 0, math.tan(args), 1, 0, 0)
                elif name == 'skewy':
                    args = (1, math.tan(args), 0, 1, 0, 0)
                else:
                    assert name == 'matrix'
                matrix = cairo.Matrix(*args) * matrix
        matrix.translate(-origin_x, -origin_y)
        box.transformation_matrix = matrix
        return matrix


def rectangle_aabb(matrix, pos_x, pos_y, width, height):
    """Apply a transformation matrix to an axis-aligned rectangle
    and return its axis-aligned bounding box as ``(x, y, width, height)``

    """
    transform_point = matrix.transform_point
    x1, y1 = transform_point(pos_x, pos_y)
    x2, y2 = transform_point(pos_x + width, pos_y)
    x3, y3 = transform_point(pos_x, pos_y + height)
    x4, y4 = transform_point(pos_x + width, pos_y + height)
    box_x1 = min(x1, x2, x3, x4)
    box_y1 = min(y1, y2, y3, y4)
    box_x2 = max(x1, x2, x3, x4)
    box_y2 = max(y1, y2, y3, y4)
    return box_x1, box_y1, box_x2 - box_x1, box_y2 - box_y1


def _gather_links_and_bookmarks(box, bookmarks, links, anchors, matrix):
    transform = _get_matrix(box)
    if transform:
        matrix = transform * matrix if matrix else transform

    bookmark_label = box.bookmark_label
    if box.style['bookmark_level'] == 'none':
        bookmark_level = None
    else:
        bookmark_level = box.style['bookmark_level']
    state = box.style['bookmark_state']
    link = box.style['link']
    anchor_name = box.style['anchor']
    has_bookmark = bookmark_label and bookmark_level
    # 'link' is inherited but redundant on text boxes
    has_link = link and not isinstance(box, boxes.TextBox)
    # In case of duplicate IDs, only the first is an anchor.
    has_anchor = anchor_name and anchor_name not in anchors
    is_attachment = hasattr(box, 'is_attachment') and box.is_attachment

    if has_bookmark or has_link or has_anchor:
        pos_x, pos_y, width, height = box.hit_area()
        if has_link:
            token_type, link = link
            assert token_type == 'url'
            link_type, target = link
            assert isinstance(target, str)
            if link_type == 'external' and is_attachment:
                link_type = 'attachment'
            if matrix:
                link = (
                    link_type, target, rectangle_aabb(
                        matrix, pos_x, pos_y, width, height))
            else:
                link = (link_type, target, (pos_x, pos_y, width, height))
            links.append(link)
        if matrix and (has_bookmark or has_anchor):
            pos_x, pos_y = matrix.transform_point(pos_x, pos_y)
        if has_bookmark:
            bookmarks.append(
                (bookmark_level, bookmark_label, (pos_x, pos_y), state))
        if has_anchor:
            anchors[anchor_name] = pos_x, pos_y

    for child in box.all_children():
        _gather_links_and_bookmarks(child, bookmarks, links, anchors, matrix)


def _w3c_date_to_iso(string, attr_name):
    """Tranform W3C date to ISO-8601 format."""
    if string is None:
        return None
    match = W3C_DATE_RE.match(string)
    if match is None:
        LOGGER.warning('Invalid %s date: %r', attr_name, string)
        return None
    groups = match.groupdict()
    iso_date = '%04i-%02i-%02iT%02i:%02i:%02i' % (
        int(groups['year']),
        int(groups['month'] or 1),
        int(groups['day'] or 1),
        int(groups['hour'] or 0),
        int(groups['minute'] or 0),
        int(groups['second'] or 0))
    if groups['hour']:
        assert groups['minute']
        if groups['tz_hour']:
            assert groups['tz_hour'].startswith(('+', '-'))
            assert groups['tz_minute']
            iso_date += '%+03i:%02i' % (
                int(groups['tz_hour']), int(groups['tz_minute']))
        else:
            iso_date += '+00:00'
    return iso_date


class Page(object):
    """Represents a single rendered page.

    .. versionadded:: 0.15

    Should be obtained from :attr:`Document.pages` but not
    instantiated directly.

    """
    def __init__(self, page_box, enable_hinting=False):
        #: The page width, including margins, in CSS pixels.
        self.width = page_box.margin_width()

        #: The page height, including margins, in CSS pixels.
        self.height = page_box.margin_height()

        #: The page bleed widths as a :obj:`dict` with ``'top'``, ``'right'``,
        #: ``'bottom'`` and ``'left'`` as keys, and values in CSS pixels.
        self.bleed = {
            side: page_box.style['bleed_%s' % side].value
            for side in ('top', 'right', 'bottom', 'left')}

        #: The :obj:`list` of ``(bookmark_level, bookmark_label, target)``
        #: :obj:`tuples <tuple>`. ``bookmark_level`` and ``bookmark_label``
        #: are respectively an :obj:`int` and a :obj:`string <str>`, based on
        #: the CSS properties of the same names. ``target`` is an ``(x, y)``
        #: point in CSS pixels from the top-left of the page.
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

        _gather_links_and_bookmarks(
            page_box, self.bookmarks, self.links, self.anchors, matrix=None)
        self._page_box = page_box
        self._enable_hinting = enable_hinting

    def paint(self, cairo_context, left_x=0, top_y=0, scale=1, clip=False):
        """Paint the page in cairo, on any type of surface.

        :type cairo_context: :class:`cairocffi.Context`
        :param cairo_context:
            Any cairo context object.
        :type left_x: float
        :param left_x:
            X coordinate of the left of the page, in cairo user units.
        :type top_y: float
        :param top_y:
            Y coordinate of the top of the page, in cairo user units.
        :type scale: float
        :param scale:
            Zoom scale in cairo user units per CSS pixel.
        :type clip: bool
        :param clip:
            Whether to clip/cut content outside the page. If false or
            not provided, content can overflow.

        """
        with stacked(cairo_context):
            if self._enable_hinting:
                left_x, top_y = cairo_context.user_to_device(left_x, top_y)
                # Hint in device space
                left_x = int(left_x)
                top_y = int(top_y)
                left_x, top_y = cairo_context.device_to_user(left_x, top_y)
            # Make (0, 0) the top-left corner:
            cairo_context.translate(left_x, top_y)
            # Make user units CSS pixels:
            cairo_context.scale(scale, scale)
            if clip:
                width = self.width
                height = self.height
                if self._enable_hinting:
                    width, height = (
                        cairo_context.user_to_device_distance(width, height))
                    # Hint in device space
                    width = int(math.ceil(width))
                    height = int(math.ceil(height))
                    width, height = (
                        cairo_context.device_to_user_distance(width, height))
                cairo_context.rectangle(0, 0, width, height)
                cairo_context.clip()
            draw_page(self._page_box, cairo_context, self._enable_hinting)


class DocumentMetadata(object):
    """Meta-information belonging to a whole :class:`Document`.

    .. versionadded:: 0.20

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
        #:
        #: .. versionadded:: 0.22
        self.attachments = attachments or []


BookmarkSubtree = collections.namedtuple(
    'BookmarkSubtree', ('label', 'destination', 'children', 'state'))


class Document(object):
    """A rendered document ready to be painted on a cairo surface.

    Typically obtained from :meth:`HTML.render() <weasyprint.HTML.render>`, but
    can also be instantiated directly with a list of :class:`pages <Page>`, a
    set of :class:`metadata <DocumentMetadata>`, a :func:`url_fetcher
    <weasyprint.default_url_fetcher>` function, and a :class:`font_config
    <weasyprint.fonts.FontConfiguration>`.

    """

    @classmethod
    def _build_layout_context(cls, html, stylesheets, enable_hinting,
                              presentational_hints=False, font_config=None):
        if font_config is None:
            font_config = FontConfiguration()
        target_collector = TargetCollector()
        page_rules = []
        user_stylesheets = []
        for css in stylesheets or []:
            if not hasattr(css, 'matcher'):
                css = CSS(
                    guess=css, media_type=html.media_type,
                    font_config=font_config)
            user_stylesheets.append(css)
        style_for = get_all_computed_styles(
            html, user_stylesheets, presentational_hints, font_config,
            page_rules, target_collector)
        get_image_from_uri = functools.partial(
            original_get_image_from_uri, {}, html.url_fetcher)
        PROGRESS_LOGGER.info('Step 4 - Creating formatting structure')
        context = LayoutContext(
            enable_hinting, style_for, get_image_from_uri, font_config,
            target_collector)
        return context

    @classmethod
    def _render(cls, html, stylesheets, enable_hinting,
                presentational_hints=False, font_config=None):
        if font_config is None:
            font_config = FontConfiguration()

        context = cls._build_layout_context(
            html, stylesheets, enable_hinting, presentational_hints,
            font_config)

        root_box = build_formatting_structure(
            html.etree_element, context.style_for, context.get_image_from_uri,
            html.base_url, context.target_collector)

        page_boxes = layout_document(html, root_box, context)
        rendering = cls(
            [Page(page_box, enable_hinting) for page_box in page_boxes],
            DocumentMetadata(**html._get_metadata()),
            html.url_fetcher, font_config)
        return rendering

    def __init__(self, pages, metadata, url_fetcher, font_config):
        #: A list of :class:`Page` objects.
        self.pages = pages
        #: A :class:`DocumentMetadata` object.
        #: Contains information that does not belong to a specific page
        #: but to the whole document.
        self.metadata = metadata
        #: A function or other callable with the same signature as
        #: :func:`default_url_fetcher` called to fetch external resources such
        #: as stylesheets and images.  (See :ref:`url-fetchers`.)
        self.url_fetcher = url_fetcher
        # Keep a reference to font_config to avoid its garbage collection until
        # rendering is destroyed. This is needed as font_config.__del__ removes
        # fonts that may be used when rendering
        self._font_config = font_config

    def copy(self, pages='all'):
        """Take a subset of the pages.

        .. versionadded:: 0.15

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

        Write each page to a numbred PNG file::

            for i, page in enumerate(document.pages):
                document.copy(page).write_png('page_%s.png' % i)

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
            pages, self.metadata, self.url_fetcher, self._font_config)

    def resolve_links(self):
        """Resolve internal hyperlinks.

        .. versionadded:: 0.15

        Links to a missing anchor are removed with a warning.

        If multiple anchors have the same name, the first one is used.

        :returns:
            A generator yielding lists (one per page) like :attr:`Page.links`,
            except that ``target`` for internal hyperlinks is
            ``(page_number, x, y)`` instead of an anchor name.
            The page number is a 0-based index into the :attr:`pages` list,
            and ``x, y`` are in CSS pixels from the top-left of the page.

        """
        anchors = set()
        paged_anchors = []
        for i, page in enumerate(self.pages):
            paged_anchors.append([])
            for anchor_name, (point_x, point_y) in page.anchors.items():
                if anchor_name not in anchors:
                    paged_anchors[-1].append((anchor_name, point_x, point_y))
                    anchors.add(anchor_name)
        for page in self.pages:
            page_links = []
            for link in page.links:
                link_type, anchor_name, rectangle = link
                if link_type == 'internal':
                    if anchor_name not in anchors:
                        LOGGER.error(
                            'No anchor #%s for internal URI reference',
                            anchor_name)
                    else:
                        page_links.append((link_type, anchor_name, rectangle))
                else:
                    # External link
                    page_links.append(link)
            yield page_links, paged_anchors.pop(0)

    def make_bookmark_tree(self):
        """Make a tree of all bookmarks in the document.

        .. versionadded:: 0.15

        :return: A list of bookmark subtrees.
            A subtree is ``(label, target, children, state)``. ``label`` is
            a string, ``target`` is ``(page_number, x, y)`` like in
            :meth:`resolve_links`, and ``children`` is a
            list of child subtrees.

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
            for level, label, (point_x, point_y), state in page.bookmarks:
                if level > previous_level:
                    # Example: if the previous bookmark is a <h2>, the next
                    # depth "should" be for <h3>. If now we get a <h6> we’re
                    # skipping two levels: append 6 - 3 - 1 = 2
                    skipped_levels.append(level - previous_level - 1)
                else:
                    temp = level
                    while temp < previous_level:
                        temp += 1 + skipped_levels.pop()
                    if temp > previous_level:
                        # We remove too many "skips", add some back:
                        skipped_levels.append(temp - previous_level - 1)

                previous_level = level
                depth = level - sum(skipped_levels)
                assert depth == len(skipped_levels)
                assert depth >= 1

                children = []
                subtree = BookmarkSubtree(
                    label, (page_number, point_x, point_y), children, state)
                last_by_depth[depth - 1].append(subtree)
                del last_by_depth[depth:]
                last_by_depth.append(children)
        return root

    def add_hyperlinks(self, links, anchors, context, scale):
        """Include hyperlinks in current PDF page.

        .. versionadded:: 43


        """
        if cairo.cairo_version() < 11504:
            return

        # We round floats to avoid locale problems, see
        # https://github.com/Kozea/WeasyPrint/issues/742

        # TODO: Instead of using rects, we could use the drawing rectangles
        # defined by cairo when drawing targets. This would give a feeling
        # similiar to what browsers do with links that span multiple lines.
        for link in links:
            link_type, link_target, rectangle = link
            if link_type == 'external':
                attributes = "rect=[{} {} {} {}] uri='{}'".format(*(
                    [int(round(i * scale)) for i in rectangle] +
                    [link_target.replace("'", '%27')]))
            elif link_type == 'internal':
                attributes = "rect=[{} {} {} {}] dest='{}'".format(*(
                    [int(round(i * scale)) for i in rectangle] +
                    [link_target.replace("'", '%27')]))
            elif link_type == 'attachment':
                # Attachments are handled in write_pdf_metadata
                continue
            context.tag_begin(cairo.TAG_LINK, attributes)
            context.tag_end(cairo.TAG_LINK)

        for anchor in anchors:
            anchor_name, x, y = anchor
            attributes = "name='{}' x={} y={}".format(
                anchor_name.replace("'", '%27'), int(round(x * scale)),
                int(round(y * scale)))
            context.tag_begin(cairo.TAG_DEST, attributes)
            context.tag_end(cairo.TAG_DEST)

    def write_pdf(self, target=None, zoom=1, attachments=None):
        """Paint the pages in a PDF file, with meta-data.

        PDF files written directly by cairo do not have meta-data such as
        bookmarks/outlines and hyperlinks.

        :type target: str, pathlib.Path or file object
        :param target:
            A filename where the PDF file is generated, a file object, or
            :obj:`None`.
        :type zoom: float
        :param zoom:
            The zoom factor in PDF units per CSS units.  **Warning**:
            All CSS units are affected, including physical units like
            ``cm`` and named sizes like ``A4``.  For values other than
            1, the physical CSS units will thus be "wrong".
        :type attachments: list
        :param attachments: A list of additional file attachments for the
            generated PDF document or :obj:`None`. The list's elements are
            :class:`Attachment` objects, filenames, URLs or file-like objects.
        :returns:
            The PDF as :obj:`bytes` if ``target`` is not provided or
            :obj:`None`, otherwise :obj:`None` (the PDF is written to
            ``target``).

        """
        # 0.75 = 72 PDF point (cairo units) per inch / 96 CSS pixel per inch
        scale = zoom * 0.75
        # Use an in-memory buffer, as we will need to seek for
        # metadata. Directly using the target when possible doesn't
        # significantly save time and memory use.
        file_obj = io.BytesIO()
        # (1, 1) is overridden by .set_size() below.
        surface = cairo.PDFSurface(file_obj, 1, 1)
        context = cairo.Context(surface)

        PROGRESS_LOGGER.info('Step 6 - Drawing')

        paged_links_and_anchors = list(self.resolve_links())
        for page, links_and_anchors in zip(
                self.pages, paged_links_and_anchors):
            links, anchors = links_and_anchors
            surface.set_size(
                math.floor(scale * (
                    page.width + page.bleed['left'] + page.bleed['right'])),
                math.floor(scale * (
                    page.height + page.bleed['top'] + page.bleed['bottom'])))
            with stacked(context):
                context.translate(
                    page.bleed['left'] * scale, page.bleed['top'] * scale)
                page.paint(context, scale=scale)
                self.add_hyperlinks(links, anchors, context, scale)
                surface.show_page()

        PROGRESS_LOGGER.info('Step 7 - Adding PDF metadata')

        # TODO: overwrite producer when possible in cairo
        if cairo.cairo_version() >= 11504:
            # Set document information
            for attr, key in (
                    ('title', cairo.PDF_METADATA_TITLE),
                    ('description', cairo.PDF_METADATA_SUBJECT),
                    ('generator', cairo.PDF_METADATA_CREATOR)):
                value = getattr(self.metadata, attr)
                if value is not None:
                    surface.set_metadata(key, value)
            for attr, key in (
                    ('authors', cairo.PDF_METADATA_AUTHOR),
                    ('keywords', cairo.PDF_METADATA_KEYWORDS)):
                value = getattr(self.metadata, attr)
                if value is not None:
                    surface.set_metadata(key, ', '.join(value))
            for attr, key in (
                    ('created', cairo.PDF_METADATA_CREATE_DATE),
                    ('modified', cairo.PDF_METADATA_MOD_DATE)):
                value = getattr(self.metadata, attr)
                if value is not None:
                    surface.set_metadata(key, _w3c_date_to_iso(value, attr))

            # Set bookmarks
            bookmarks = self.make_bookmark_tree()
            levels = [cairo.PDF_OUTLINE_ROOT] * len(bookmarks)
            while bookmarks:
                bookmark = bookmarks.pop(0)
                title = bookmark.label
                destination = bookmark.destination
                children = bookmark.children
                state = bookmark.state
                page, x, y = destination

                # We round floats to avoid locale problems, see
                # https://github.com/Kozea/WeasyPrint/issues/742
                link_attribs = 'page={} pos=[{} {}]'.format(
                    page + 1, int(round(x * scale)),
                    int(round(y * scale)))

                outline = surface.add_outline(
                    levels.pop(), title, link_attribs,
                    cairo.PDF_OUTLINE_FLAG_OPEN if state == 'open' else 0)
                levels.extend([outline] * len(children))
                bookmarks = children + bookmarks

        surface.finish()

        # Add extra PDF metadata: attachments, embedded files
        attachment_links = [
            [link for link in page_links if link[0] == 'attachment']
            for page_links, page_anchors in paged_links_and_anchors]
        # Write extra PDF metadata only when there is a least one from:
        # - attachments in metadata
        # - attachments as function parameters
        # - attachments as PDF links
        # - bleed boxes
        condition = (
            self.metadata.attachments or
            attachments or
            any(attachment_links) or
            any(any(page.bleed.values()) for page in self.pages))
        if condition:
            write_pdf_metadata(
                file_obj, scale, self.url_fetcher,
                self.metadata.attachments + (attachments or []),
                attachment_links, self.pages)

        if target is None:
            return file_obj.getvalue()
        else:
            file_obj.seek(0)
            if hasattr(target, 'write'):
                shutil.copyfileobj(file_obj, target)
            else:
                with open(target, 'wb') as fd:
                    shutil.copyfileobj(file_obj, fd)

    def write_image_surface(self, resolution=96):
        """Render pages on a cairo image surface.

        .. versionadded:: 0.17

        There is no decoration around pages other than those specified in CSS
        with ``@page`` rules. The final image is as wide as the widest page.
        Each page is below the previous one, centered horizontally.

        :type resolution: float
        :param resolution:
            The output resolution in PNG pixels per CSS inch. At 96 dpi
            (the default), PNG pixels match the CSS ``px`` unit.
        :returns:
            A ``(surface, png_width, png_height)`` tuple. ``surface`` is a
            cairo :class:`ImageSurface <cairocffi.ImageSurface>`. ``png_width``
            and ``png_height`` are the size of the final image, in PNG pixels.

        """
        dppx = resolution / 96

        # This duplicates the hinting logic in Page.paint. There is a
        # dependency cycle otherwise:
        #   this → hinting logic → context → surface → this
        # But since we do no transform here, cairo_context.user_to_device and
        # friends are identity functions.
        widths = [int(math.ceil(p.width * dppx)) for p in self.pages]
        heights = [int(math.ceil(p.height * dppx)) for p in self.pages]

        max_width = max(widths)
        sum_heights = sum(heights)
        surface = cairo.ImageSurface(
            cairo.FORMAT_ARGB32, max_width, sum_heights)
        context = cairo.Context(surface)
        pos_y = 0
        PROGRESS_LOGGER.info('Step 6 - Drawing')
        for page, width, height in zip(self.pages, widths, heights):
            pos_x = (max_width - width) / 2
            page.paint(context, pos_x, pos_y, scale=dppx, clip=True)
            pos_y += height
        return surface, max_width, sum_heights

    def write_png(self, target=None, resolution=96):
        """Paint the pages vertically to a single PNG image.

        There is no decoration around pages other than those specified in CSS
        with ``@page`` rules. The final image is as wide as the widest page.
        Each page is below the previous one, centered horizontally.

        :param target:
            A filename, file-like object, or :obj:`None`.
        :type resolution: float
        :param resolution:
            The output resolution in PNG pixels per CSS inch. At 96 dpi
            (the default), PNG pixels match the CSS ``px`` unit.
        :returns:
            A ``(png_bytes, png_width, png_height)`` tuple. ``png_bytes`` is a
            byte string if ``target`` is :obj:`None`, otherwise :obj:`None`
            (the image is written to ``target``).  ``png_width`` and
            ``png_height`` are the size of the final image, in PNG pixels.

        """
        surface, max_width, sum_heights = self.write_image_surface(resolution)
        if target is None:
            target = io.BytesIO()
            surface.write_to_png(target)
            png_bytes = target.getvalue()
        else:
            surface.write_to_png(target)
            png_bytes = None
        return png_bytes, max_width, sum_heights
