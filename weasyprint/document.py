"""
    weasyprint.document
    -------------------

    :copyright: Copyright 2011-2018 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import functools
import io
import math
import shutil
import warnings

import cairocffi as cairo

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
from .layout.backgrounds import percentage
from .logger import LOGGER
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
        origin_x = box.border_box_x() + percentage(origin_x, border_width)
        origin_y = box.border_box_y() + percentage(origin_y, border_height)

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
            bookmarks.append((bookmark_level, bookmark_label, (pos_x, pos_y)))
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
        assert groups['tz_hour'].startswith(('+', '-'))
        assert groups['tz_minute']
        iso_date += '%+03i:%02i' % (
            int(groups['tz_hour']), int(groups['tz_minute']))
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

        #: The page bleed width, in CSS pixels.
        self.bleed = {
            side: page_box.style['bleed_%s' % side].value
            for side in ('top', 'right', 'bottom', 'left')}

        #: A list of ``(bookmark_level, bookmark_label, target)`` tuples.
        #: :obj:`bookmark_level` and :obj:`bookmark_label` are respectively
        #: an integer and a Unicode string, based on the CSS properties
        #: of the same names. :obj:`target` is an ``(x, y)`` point
        #: in CSS pixels from the top-left of the page.
        self.bookmarks = bookmarks = []

        #: A list of ``(link_type, target, rectangle)`` tuples.
        #: A rectangle is ``(x, y, width, height)``, in CSS pixels from
        #: the top-left of the page. :obj:`link_type` is one of two strings:
        #:
        #: * ``'external'``: :obj:`target` is an absolute URL
        #: * ``'internal'``: :obj:`target` is an anchor name (see
        #:   :attr:`Page.anchors`).
        #    The anchor might be defined in another page,
        #    in multiple pages (in which case the first occurence is used),
        #    or not at all.
        #: * ``'attachment'``: :obj:`target` is an absolute URL and points
        #:   to a resource to attach to the document.
        self.links = links = []

        #: A dict mapping each anchor name to its target, an ``(x, y)`` point
        #: in CSS pixels from the top-left of the page.
        self.anchors = anchors = {}

        _gather_links_and_bookmarks(
            page_box, bookmarks, links, anchors, matrix=None)
        self._page_box = page_box
        self._enable_hinting = enable_hinting

    def paint(self, cairo_context, left_x=0, top_y=0, scale=1, clip=False):
        """Paint the page in cairo, on any type of surface.

        :param cairo_context:
            Any :class:`cairocffi.Context` object.
        :param left_x:
            X coordinate of the left of the page, in cairo user units.
        :param top_y:
            Y coordinate of the top of the page, in cairo user units.
        :param scale:
            Zoom scale in cairo user units per CSS pixel.
        :param clip:
            Whether to clip/cut content outside the page. If false or
            not provided, content can overflow.
        :type left_x: float
        :type top_y: float
        :type scale: float
        :type clip: bool

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
    """Contains meta-information about a :class:`Document`
    that belongs to the whole document rather than specific pages.

    New attributes may be added in future versions of WeasyPrint.

    .. _W3C’s profile of ISO 8601: http://www.w3.org/TR/NOTE-datetime

    """
    def __init__(self, title=None, authors=None, description=None,
                 keywords=None, generator=None, created=None, modified=None,
                 attachments=None):
        #: The title of the document, as a string or :obj:`None`.
        #: Extracted from the ``<title>`` element in HTML
        #: and written to the ``/Title`` info field in PDF.
        self.title = title
        #: The authors of the document as a list of strings.
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
        #: `W3C’s profile of ISO 8601`_.
        #: Extracted from the ``<meta name=dcterms.created>`` element in HTML
        #: and written to the ``/CreationDate`` info field in PDF.
        self.created = created
        #: The modification date of the document, as a string or :obj:`None`.
        #: Dates are in one of the six formats specified in
        #: `W3C’s profile of ISO 8601`_.
        #: Extracted from the ``<meta name=dcterms.modified>`` element in HTML
        #: and written to the ``/ModDate`` info field in PDF.
        self.modified = modified
        #: File attachments as a list of tuples of URL and a description or
        #: :obj:`None`.
        #: Extracted from the ``<link rel=attachment>`` elements in HTML
        #: and written to the ``/EmbeddedFiles`` dictionary in PDF.
        self.attachments = attachments or []


class Document(object):
    """A rendered document, with access to individual pages
    ready to be painted on any cairo surfaces.

    Typically obtained from :meth:`HTML.render() <weasyprint.HTML.render>`,
    but can also be instantiated directly
    with a list of :class:`pages <Page>`,
    a set of :class:`metadata <DocumentMetadata>`, and a ``url_fetcher``.

    """
    @classmethod
    def _render(cls, html, stylesheets, enable_hinting,
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
        style_for, cascaded_styles, computed_styles = get_all_computed_styles(
            html, user_stylesheets, presentational_hints, font_config,
            page_rules, target_collector)
        get_image_from_uri = functools.partial(
            original_get_image_from_uri, {}, html.url_fetcher)
        LOGGER.info('Step 4 - Creating formatting structure')
        root_box = build_formatting_structure(
            html.etree_element, style_for, get_image_from_uri,
            html.base_url, target_collector)
        page_boxes = layout_document(
            enable_hinting, style_for, get_image_from_uri, root_box,
            font_config, html, cascaded_styles, computed_styles,
            target_collector)
        rendering = cls(
            [Page(p, enable_hinting) for p in page_boxes],
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
        #: A ``url_fetcher`` for resources that have to be read when writing
        #: the output.
        self.url_fetcher = url_fetcher
        # Keep a reference to font_config to avoid its garbage collection until
        # rendering is destroyed. This is needed as font_config.__del__ removes
        # fonts that may be used when rendering
        self._font_config = font_config

    def copy(self, pages='all'):
        """Take a subset of the pages.

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

            all_pages = [p for p in doc.pages for doc in documents]
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

        Links to a missing anchor are removed with a warning.

        If multiple anchors have the same name, the first one is used.

        :returns:
            A generator yielding lists (one per page) like :attr:`Page.links`,
            except that :obj:`target` for internal hyperlinks is
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

        :return: a list of bookmark subtrees.
            A subtree is ``(label, target, children)``. :obj:`label` is
            a string, :obj:`target` is ``(page_number, x, y)`` like in
            :meth:`resolve_links`, and :obj:`children` is a
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
            for level, label, (point_x, point_y) in page.bookmarks:
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
                subtree = label, (page_number, point_x, point_y), children
                last_by_depth[depth - 1].append(subtree)
                del last_by_depth[depth:]
                last_by_depth.append(children)
        return root

    def add_hyperlinks(self, links, anchors, context, scale):
        """Include hyperlinks in current page."""
        if cairo.cairo_version() < 11504:
            return

        # TODO: Instead of using rects, we could use the drawing rectangles
        # defined by cairo when drawing targets. This would give a feeling
        # similiar to what browsers do with links that span multiple lines.
        for link in links:
            link_type, link_target, rectangle = link
            if link_type == 'external':
                attributes = "rect=[{} {} {} {}] uri='{}'".format(
                    *([i * scale for i in rectangle] + [link_target]))
            elif link_type == 'internal':
                attributes = "rect=[{} {} {} {}] dest='{}'".format(
                    *([i * scale for i in rectangle] + [link_target]))
            elif link_type == 'attachment':
                # Attachments are handled in write_pdf_metadata
                continue
            context.tag_begin(cairo.TAG_LINK, attributes)
            context.tag_end(cairo.TAG_LINK)

        for anchor in anchors:
            anchor_name, x, y = anchor
            attributes = "name='{}' x={} y={}".format(
                anchor_name, x * scale, y * scale)
            context.tag_begin(cairo.TAG_DEST, attributes)
            context.tag_end(cairo.TAG_DEST)

    def write_pdf(self, target=None, zoom=1, attachments=None):
        """Paint the pages in a PDF file, with meta-data.

        PDF files written directly by cairo do not have meta-data such as
        bookmarks/outlines and hyperlinks.

        :param target:
            A filename, file-like object, or :obj:`None`.
        :type zoom: float
        :param zoom:
            The zoom factor in PDF units per CSS units.  **Warning**:
            All CSS units are affected, including physical units like
            ``cm`` and named sizes like ``A4``.  For values other than
            1, the physical CSS units will thus be “wrong”.
        :param attachments: A list of additional file attachments for the
            generated PDF document or :obj:`None`. The list's elements are
            :class:`Attachment` objects, filenames, URLs, or file-like objects.
        :returns:
            The PDF as byte string if :obj:`target` is :obj:`None`, otherwise
            :obj:`None` (the PDF is written to :obj:`target`).

        """
        # 0.75 = 72 PDF point (cairo units) per inch / 96 CSS pixel per inch
        scale = zoom * 0.75
        # Use an in-memory buffer. We will need to seek for metadata
        # TODO: avoid this if target can seek? Benchmark first.
        file_obj = io.BytesIO()
        # (1, 1) is overridden by .set_size() below.
        surface = cairo.PDFSurface(file_obj, 1, 1)
        context = cairo.Context(surface)

        LOGGER.info('Step 6 - Drawing')

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

        LOGGER.info('Step 7 - Adding PDF metadata')

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
                title, destination, children = bookmarks.pop(0)
                page, x, y = destination
                link_attribs = 'page={} pos=[{} {}]'.format(
                    page + 1, x * scale, y * scale)
                outline = surface.add_outline(
                    levels.pop(), title, link_attribs, 0)
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
        LOGGER.info('Step 6 - Drawing')
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
            A ``(png_bytes, png_width, png_height)`` tuple. :obj:`png_bytes`
            is a byte string if :obj:`target` is :obj:`None`, otherwise
            :obj:`None` (the image is written to :obj:`target`).
            :obj:`png_width` and :obj:`png_height` are the size of the
            final image, in PNG pixels.

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
