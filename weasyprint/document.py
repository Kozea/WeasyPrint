# coding: utf8
"""
    weasyprint.document
    -------------------

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import io
import sys
import math
import shutil
import functools

import cairo

from . import CSS
from . import images
from .logger import LOGGER
from .css import get_all_computed_styles
from .formatting_structure import boxes
from .formatting_structure.build import build_formatting_structure
from .layout import layout_document
from .draw import draw_page, stacked
from .pdf import write_pdf_metadata
from .compat import izip, iteritems
from .urls import FILESYSTEM_ENCODING


class _TaggedTuple(tuple):
    """A tuple with a :attr:`sourceline` attribute,
    The line number in the HTML source for whatever the tuple represents.

    """


def _get_metadata(box, bookmarks, links, anchors, matrix):
    bookmark_label = box.bookmark_label
    bookmark_level = box.bookmark_level
    link = box.style.link
    anchor_name = box.style.anchor
    has_bookmark = bookmark_label and bookmark_level
    # 'link' is inherited but redundant on text boxes
    has_link = link and not isinstance(box, boxes.TextBox)
    # In case of duplicate IDs, only the first is an anchor.
    has_anchor = anchor_name and anchor_name not in anchors

    if has_bookmark or has_link or has_anchor:
        pos_x, pos_y, width, height = box.hit_area()
        pos_x, pos_y = matrix.transform_point(pos_x, pos_y)
        width, height = matrix.transform_distance(width, height)
        if has_bookmark:
            bookmarks.append((bookmark_level, bookmark_label, (pos_x, pos_y)))
        if has_link:
            link_type, target = link
            link = _TaggedTuple(
                (link_type, target, (pos_x, pos_y, width, height)))
            link.sourceline = box.sourceline
            links.append(link)
        if has_anchor:
            anchors[anchor_name] = pos_x, pos_y

    for child in box.all_children():
        _get_metadata(child, bookmarks, links, anchors, matrix)


class Page(object):
    """Represents a single rendered page.

    Should be obtained from :attr:`Document.pages` but not
    instantiated directly.

    """
    def __init__(self, page, enable_hinting=False, resolution=96):
        dppx = resolution / 96

        #: The page width, including margins, in cairo user units.
        self.width = page.margin_width() * dppx

        #: The page height, including margins, in cairo user units.
        self.height = page.margin_height() * dppx

        #: A list of ``(bookmark_level, bookmark_label, point)`` tuples.
        #: A point is ``(x, y)`` in cairo units from the top-left of the page.
        self.bookmarks = []

        #: A list of ``(link_type, target, rectangle)`` tuples.
        #: A rectangle is ``(x, y, width, height)``, in cairo units
        #: form the top-left of the page.
        #: The link type one of two strings:
        #:
        #: * ``'external'``: :obj:`target` is an absolute URL
        #: * ``'internal'``: :obj:`target` is an anchor name (see
        #:   :attr:`Page.anchors` and :meth:`Document.all_anchors`).
        #:   An anchor might be defined in another page, or not at all.
        self.links = []

        #: A dict mapping anchor names to points (``(x, y)`` in cairo units
        #: form the top-left of the page.)
        self.anchors = {}

        _get_metadata(page, self.bookmarks, self.links, self.anchors,
                      cairo.Matrix(xx=dppx, yy=dppx))
        self._page_box = page
        self._enable_hinting = enable_hinting
        self._dppx = dppx

    def paint(self, cairo_context, left_x=0, top_y=0, clip=False):
        """Paint the surface in cairo, on any type of surface.

        :param cairo_context: any :class:`cairo.Context` object.
        :type left_x: float
        :param left_x:
            X coordinate of the left of the page, in user units.
        :type top_y: float
        :param top_y:
            Y coordinate of the top of the page, in user units.
        :type clip: bool
        :param clip:
            Whether to clip/cut content outside the page. If false or
            not provided, content can overflow.

        """
        with stacked(cairo_context):
            if self._enable_hinting:
                left_x, top_y = cairo_context.user_to_device(left_x, top_y)
                width, height = cairo_context.user_to_device_distance(
                    self.width, self.height)
                # Hint in device space
                left_x = int(left_x)
                top_y = int(top_y)
                width = int(math.ceil(width))
                height = int(math.ceil(height))
                left_x, top_y = cairo_context.device_to_user(left_x, top_y)
                width, height = cairo_context.device_to_user_distance(
                    width, height)
            else:
                width = self.width
                height = self.height
            cairo_context.translate(left_x, top_y)
            # The top-left corner is now (0, 0)
            if clip:
                cairo_context.rectangle(0, 0, width, height)
                cairo_context.clip()
            cairo_context.scale(self._dppx, self._dppx)
            # User units are now CSS pixels
            draw_page(self._page_box, cairo_context, self._enable_hinting)


class Document(object):
    """A rendered document, with access to individual pages
    ready to be painted on any cairo surfaces.

    Should be obtained from :meth:`HTML.render() <weasyprint.HTML.render>`
    but not instantiated directly.

    """
    @classmethod
    def _render(cls, html, stylesheets, resolution, enable_hinting):
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
        return cls([Page(p, enable_hinting, resolution) for p in page_boxes])

    def __init__(self, pages):
        #: A list of :class:`Page` objects.
        self.pages = pages

    def copy(self, pages='all'):
        """Take a subset of the pages.

        :param pages:
            An iterable of :class:`Page` objects from :attr:`pages`.
        :return:
            A new :class:`Document` object.

        Examples::

            # Lists count from 0 but page numbers usually from 1
            # [::2] is a slice of even list indexes but odd-numbered pages.
            document.copy(document.pages[::2]).write_pdf('odd_pages.pdf')
            document.copy(document.pages[1::2]).write_pdf('even_pages.pdf')

            for i, page in enumerate(document.pages):
                document.copy(page).write_png('page_%s.png' % i)

        """
        if pages == 'all':
            pages = self.pages
        elif not isinstance(pages, list):
            pages = list(pages)
        return type(self)(pages)

    def resolve_links(self):
        """Resolve internal hyperlinks.

        Links to a missing anchor are removed with a warning.
        If multiple anchors have the same name, the first is used.

        :returns:
            A generator yielding lists (one per page) like :attr:`Page.links`,
            except that :obj:`target` for internal hyperlinks is
            ``(page_number, x, y)`` instead of an anchor name.
            The page number is an index (0-based) in the :attr:`pages` list,
            ``x, y`` are in cairo units from the top-left of the page.

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
                        LOGGER.warn(
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

    def write_pdf(self, target=None):
        """Paint the pages in a PDF file, with meta-data.

        PDF files written directly by cairo do not have meta-data such as
        bookmarks/outlines and hyperlinks.

        :param target:
            A filename, file-like object, or ``None``.
        :returns:
            The PDF as byte string if :obj:`target` is ``None``, otherwise
            ``None`` (the PDF is written to :obj:`target`.)

        """
        # Use an in-memory buffer. We will need to seek for metadata
        # TODO: avoid this if target can seek? Benchmark first.
        file_obj = io.BytesIO()
        # (1, 1) is overridden by .set_size() below.
        surface = cairo.PDFSurface(file_obj, 1, 1)
        context = cairo.Context(surface)
        for page in self.pages:
            surface.set_size(page.width, page.height)
            page.paint(context)
            surface.show_page()
        surface.finish()

        write_pdf_metadata(self, file_obj)

        if target is None:
            return file_obj.getvalue()
        else:
            file_obj.seek(0)
            if hasattr(target, 'write'):
                shutil.copyfileobj(file_obj, target)
            else:
                with open(target, 'wb') as fd:
                    shutil.copyfileobj(file_obj, fd)

    def write_png(self, target=None):
        """Paint the pages vertically to a single PNG image.

        There is no decoration around pages other than those specified in CSS
        with ``@page`` rules. The final image is as wide as the widest page.
        Each page is below the previous one, centered horizontally.

        :param target:
            A filename, file-like object, or ``None``.
        :returns:
            A ``(png_bytes, png_width, png_height)`` tuple. :obj:`png_bytes`
            is a byte string if :obj:`target` is ``None``, otherwise ``None``
            (the image is written to :obj:`target`.)
            :obj:`png_width` and :obj:`png_height` are the size of the
            final image, in PNG pixels.

        """
        # This duplicates the hinting logic in Page.paint. There is a
        # dependency cycle otherwise:
        #   this → hinting logic → context → surface → this
        # But since we do no transform here, cairo_context.user_to_device and
        # friends are identity functions.
        widths = [int(math.ceil(p.width)) for p in self.pages]
        heights = [int(math.ceil(p.height)) for p in self.pages]
        max_width = max(widths)
        sum_heights = sum(heights)
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, max_width, sum_heights)
        context = cairo.Context(surface)

        pos_y = 0
        for page, width, height in izip(self.pages, widths, heights):
            pos_x = (max_width - width) / 2
            with stacked(context):
                page.paint(context, pos_x, pos_y, clip=True)
            pos_y += height

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
