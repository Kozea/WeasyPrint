# coding: utf8
"""
    weasyprint.document
    -------------------

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import io
import sys
import math
import shutil
import functools

import cairocffi as cairo

from . import CSS
from . import images
from .logger import LOGGER
from .css import get_all_computed_styles
from .formatting_structure import boxes
from .formatting_structure.build import build_formatting_structure
from .layout import layout_document
from .layout.backgrounds import percentage
from .draw import draw_page, stacked
from .pdf import write_pdf_metadata
from .compat import izip, iteritems, unicode
from .urls import FILESYSTEM_ENCODING


def _get_matrix(box):
    """Return the matrix for the CSS transforms on this box.

    :returns: a :class:`cairocffi.Matrix` object or :obj:`None`.

    """
    # "Transforms apply to block-level and atomic inline-level elements,
    #  but do not apply to elements which may be split into
    #  multiple inline-level boxes."
    # http://www.w3.org/TR/css3-2d-transforms/#introduction
    if box.style.transform and not isinstance(box, boxes.InlineBox):
        border_width = box.border_width()
        border_height = box.border_height()
        origin_x, origin_y = box.style.transform_origin
        origin_x = box.border_box_x() + percentage(origin_x, border_width)
        origin_y = box.border_box_y() + percentage(origin_y, border_height)

        matrix = cairo.Matrix()
        matrix.translate(origin_x, origin_y)
        for name, args in box.style.transform:
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


class _TaggedTuple(tuple):
    """A tuple with a :attr:`sourceline` attribute,
    The line number in the HTML source for whatever the tuple represents.

    """


def _gather_links_and_bookmarks(box, bookmarks, links, anchors, matrix):
    transform = _get_matrix(box)
    if transform:
        matrix = transform * matrix if matrix else transform

    bookmark_label = box.bookmark_label
    bookmark_level = box.bookmark_level
    link = box.style.link
    anchor_name = box.style.anchor
    has_bookmark = bookmark_label and bookmark_level
    # 'link' is inherited but redundant on text boxes
    has_link = link and not isinstance(box, boxes.TextBox)
    # In case of duplicate IDs, only the first is an anchor.
    has_anchor = anchor_name and anchor_name not in anchors
    is_attachment = hasattr(box, 'is_attachment') and box.is_attachment

    if has_bookmark or has_link or has_anchor:
        pos_x, pos_y, width, height = box.hit_area()
        if has_link:
            link_type, target = link
            if link_type == 'external' and is_attachment:
                link_type = 'attachment'
            if matrix:
                link = _TaggedTuple(
                    (link_type, target, rectangle_aabb(
                        matrix, pos_x, pos_y, width, height)))
            else:
                link = _TaggedTuple(
                    (link_type, target, (pos_x, pos_y, width, height)))
            link.sourceline = box.sourceline
            links.append(link)
        if matrix and (has_bookmark or has_anchor):
            pos_x, pos_y = matrix.transform_point(pos_x, pos_y)
        if has_bookmark:
            bookmarks.append((bookmark_level, bookmark_label, (pos_x, pos_y)))
        if has_anchor:
            anchors[anchor_name] = pos_x, pos_y

    for child in box.all_children():
        _gather_links_and_bookmarks(child, bookmarks, links, anchors, matrix)


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

        #: A list of ``(bookmark_level, bookmark_label, target)`` tuples.
        #: :obj:`bookmark_level` and :obj:`bookmark_label` are respectively
        #: an integer and an Unicode string, based on the CSS properties
        #: of the same names. :obj:`target` is a ``(x, y)`` point
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

        #: A dict mapping anchor names to their target, ``(x, y)`` points
        #: in CSS pixels form the top-left of the page.)
        self.anchors = anchors = {}

        _gather_links_and_bookmarks(
            page_box, bookmarks, links, anchors, matrix=None)
        self._page_box = page_box
        self._enable_hinting = enable_hinting

    def paint(self, cairo_context, left_x=0, top_y=0, scale=1, clip=False):
        """Paint the page in cairo, on any type of surface.

        :param cairo_context:
            Any :class:`cairocffi.Context` object.

            .. note::

                In case you get a :class:`cairo.Context` object
                (eg. form PyGTK),
                it is possible to :ref:`convert it to cairocffi
                <converting_pycairo>`.
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
    that do not belong to specific pages but to the whole document.

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
    a set of :class:`metadata <DocumentMetadata>` and a ``url_fetcher``.

    """
    @classmethod
    def _render(cls, html, stylesheets, enable_hinting):
        style_for = get_all_computed_styles(html, user_stylesheets=[
            css if hasattr(css, 'rules')
            else CSS(guess=css, media_type=html.media_type)
            for css in stylesheets or []])
        get_image_from_uri = functools.partial(
            images.get_image_from_uri, {}, html.url_fetcher)
        page_boxes = layout_document(
            enable_hinting, style_for, get_image_from_uri,
            build_formatting_structure(
                html.root_element, style_for, get_image_from_uri))
        return cls([Page(p, enable_hinting) for p in page_boxes],
                   DocumentMetadata(**html._get_metadata()), html.url_fetcher)

    def __init__(self, pages, metadata, url_fetcher):
        #: A list of :class:`Page` objects.
        self.pages = pages
        #: A :class:`DocumentMetadata` object.
        #: Contains information that does not belong to a specific page
        #: but to the whole document.
        self.metadata = metadata
        #: A ``url_fetcher`` for resources that have to be read when writing
        #: the output.
        self.url_fetcher = url_fetcher

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
        return type(self)(pages, self.metadata, self.url_fetcher)

    def resolve_links(self):
        """Resolve internal hyperlinks.

        Links to a missing anchor are removed with a warning.
        If multiple anchors have the same name, the first is used.

        :returns:
            A generator yielding lists (one per page) like :attr:`Page.links`,
            except that :obj:`target` for internal hyperlinks is
            ``(page_number, x, y)`` instead of an anchor name.
            The page number is an index (0-based) in the :attr:`pages` list,
            ``x, y`` are in CSS pixels from the top-left of the page.

        """
        anchors = {}
        for i, page in enumerate(self.pages):
            for anchor_name, (point_x, point_y) in iteritems(page.anchors):
                anchors.setdefault(anchor_name, (i, point_x, point_y))
        for page in self.pages:
            page_links = []
            for link in page.links:
                link_type, anchor_name, rectangle = link
                if link_type == 'internal':
                    target = anchors.get(anchor_name)
                    if target is None:
                        LOGGER.warning(
                            'No anchor #%s for internal URI reference '
                            'at line %s' % (anchor_name, link.sourceline))
                    else:
                        page_links.append((link_type, target, rectangle))
                else:
                    # External link
                    page_links.append(link)
            yield page_links

    def make_bookmark_tree(self):
        """Make a tree of all bookmarks in the document.

        :return: a list of bookmark subtrees.
            A subtree is ``(label, target, children)``. :obj:`label` is
            a string, :obj:`target` is ``(page_number, x, y)`` like in
            :meth:`resolve_links`, and :obj:`children` is itself a (recursive)
            list of subtrees.

        """
        root = []
        # At one point in the document, for each "output" depth, how much
        # to add to get the source level (CSS values of bookmark-level).
        # Eg. with <h1> then <h3>, level_shifts == [0, 1]
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

    def write_pdf(self, target=None, zoom=1, attachments=None):
        """Paint the pages in a PDF file, with meta-data.

        PDF files written directly by cairo do not have meta-data such as
        bookmarks/outlines and hyperlinks.

        :param target:
            A filename, file-like object, or :obj:`None`.
        :type zoom: float
        :param zoom:
            The zoom factor in PDF units per CSS units.
            **Warning**: All CSS units (even physical, like ``cm``)
            are affected.
            For values other than 1, physical CSS units will thus be “wrong”.
            Page size declarations are affected too, even with keyword values
            like ``@page { size: A3 landscape; }``
        :param attachments: A list of additional file attachments for the
            generated PDF document or :obj:`None`. The list's elements are
            :class:`Attachment` objects, filenames, URLs or file-like objects.
        :returns:
            The PDF as byte string if :obj:`target` is :obj:`None`, otherwise
            :obj:`None` (the PDF is written to :obj:`target`.)

        """
        # 0.75 = 72 PDF point (cairo units) per inch / 96 CSS pixel per inch
        scale = zoom * 0.75
        # Use an in-memory buffer. We will need to seek for metadata
        # TODO: avoid this if target can seek? Benchmark first.
        file_obj = io.BytesIO()
        # (1, 1) is overridden by .set_size() below.
        surface = cairo.PDFSurface(file_obj, 1, 1)
        context = cairo.Context(surface)
        for page in self.pages:
            surface.set_size(page.width * scale, page.height * scale)
            page.paint(context, scale=scale)
            surface.show_page()
        surface.finish()

        write_pdf_metadata(self, file_obj, scale, self.metadata, attachments,
                           self.url_fetcher)

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
        for page, width, height in izip(self.pages, widths, heights):
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
            :obj:`None` (the image is written to :obj:`target`.)
            :obj:`png_width` and :obj:`png_height` are the size of the
            final image, in PNG pixels.

        """
        surface, max_width, sum_heights = self.write_image_surface(resolution)
        if target is None:
            target = io.BytesIO()
            surface.write_to_png(target)
            png_bytes = target.getvalue()
        else:
            if sys.version_info[0] < 3 and isinstance(target, unicode):
                # py2cairo 1.8 does not support unicode filenames.
                target = target.encode(FILESYSTEM_ENCODING)
            surface.write_to_png(target)
            png_bytes = None
        return png_bytes, max_width, sum_heights
