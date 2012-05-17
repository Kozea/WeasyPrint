# coding: utf8
"""
    weasyprint.document
    -------------------

    Entry point to the rendering process.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import io
import math

import cairo

from .css import get_all_computed_styles
from .css.computed_values import LENGTHS_TO_PIXELS
from .formatting_structure import boxes
from .formatting_structure.build import build_formatting_structure
from . import layout
from . import draw
from . import images
from . import utils
from . import pdf


class Document(object):
    """Abstract output document."""
    def __init__(self, dom, user_stylesheets, user_agent_stylesheets):
        #: lxml HtmlElement object
        self.dom = dom
        self.user_stylesheets = user_stylesheets
        self.user_agent_stylesheets = user_agent_stylesheets
        self._image_cache = {}

        # TODO: remove this when Margin boxes variable dimension is correct.
        self._auto_margin_boxes_warning_shown = False

    def style_for(self, element, pseudo_type=None):
        """
        Convenience method to get the computed styles for an element.
        """
        return self.computed_styles.get((element, pseudo_type))

    @utils.cached_property
    def computed_styles(self):
        """
        dict of (element, pseudo_element_type) -> StyleDict
        StyleDict: a dict of property_name -> PropertyValue,
                   also with attribute access
        """
        return get_all_computed_styles(
            self,
            user_stylesheets=self.user_stylesheets,
            ua_stylesheets=self.user_agent_stylesheets,
            medium='print')

    @utils.cached_property
    def formatting_structure(self):
        """
        The root of the formatting structure tree, ie. the Box
        for the root element.
        """
        return build_formatting_structure(self, self.computed_styles)

    @utils.cached_property
    def pages(self):
        """
        List of layed-out pages with an absolute size and postition
        for every box.
        """
        return layout.layout_document(self, self.formatting_structure)

    def get_image_from_uri(self, uri, type_=None):
        """
        Same as ``weasy.images.get_image_from_uri`` but cache results
        """
        missing = object()
        surface = self._image_cache.get(uri, missing)
        if surface is missing:
            surface = images.get_image_from_uri(uri, type_)
            self._image_cache[uri] = surface
        return surface

    def write_to(self, target=None):
        """Like .write_to() but returns a byte stringif target is None."""
        if target is None:
            target = io.BytesIO()
            self._write_to(target)
            return target.getvalue()
        else:
            self._write_to(target)


class PNGDocument(Document):
    """PNG output document."""
    def __init__(self, dom, *args, **kwargs):
        super(PNGDocument, self).__init__(dom, *args, **kwargs)
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1)

    def draw_page(self, page):
        """Draw a single page and return an ImageSurface."""
        width = int(math.ceil(page.outer_width))
        height = int(math.ceil(page.outer_height))
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        context = draw.CairoContext(surface)
        draw.draw_page(self, page, context)
        self.surface.finish()
        return width, height, surface

    def write_page_to(self, page_index, target):
        """Write a single page as PNG into a file-like or filename `target`."""
        _width, _height, surface = self.draw_page(self.pages[page_index])
        surface.write_to_png(target)

    def draw_all_pages(self):
        """Draw all pages and return a single ImageSurface.

        Pages are layed out vertically each above the next and centered
        horizontally.
        """
        pages = [self.draw_page(page) for page in self.pages]
        if len(pages) == 1:
            return pages[0]
        total_height = sum(height for width, height, surface in pages)
        max_width = max(width for width, height, surface in pages)
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
            max_width, total_height)
        context = draw.CairoContext(surface)

        position_y = 0
        for width, height, page_surface in pages:
            position_x = (max_width - width) // 2
            context.set_source_surface(page_surface, position_x, position_y)
            context.paint()
            position_y += height

        return max_width, total_height, surface

    def _write_to(self, target):
        """Write all pages as PNG into a file-like or filename `target`.

        Pages are layed out vertically each above the next and centered
        horizontally.
        """
        _width, _height, surface = self.draw_all_pages()
        surface.write_to_png(target)


class PDFDocument(Document):
    """PDF output document."""
    def __init__(self, dom, *args, **kwargs):
        super(PDFDocument, self).__init__(dom, *args, **kwargs)
        # Use a dummy page size initially
        self.surface = cairo.PDFSurface(None, 1, 1)

    def _write_to(self, target):
        """
        Write the whole document as PDF into a file-like or filename `target`.
        """
        bytesio = io.BytesIO()

        # The actual page size is set for each page.
        surface = cairo.PDFSurface(bytesio, 1, 1)

        px_to_pt = 1 / LENGTHS_TO_PIXELS['pt']
        for page in self.pages:
            # Actual page size is here. May be different between pages.
            surface.set_size(
                page.outer_width * px_to_pt,
                page.outer_height * px_to_pt)
            context = draw.CairoContext(surface)
            context.scale(px_to_pt, px_to_pt)
            draw.draw_page(self, page, context)
            surface.show_page()

        surface.finish()

        links = [self._get_link_rectangles(page) for page in self.pages]
        destinations = dict(self._get_link_destinations())
        bookmark_list = []
        bookmark_levels = {0: {
            'count': 0, 'first': None, 'last': None,
            'prev': None, 'next': None, 'parent': None}}
        bookmark_level = lambda: max(bookmark_levels)
        for i, (level, label, destination) in enumerate(self._get_bookmarks()):
            bookmark = {
                'count': 0, 'first': None, 'last': None, 'prev': None,
                'next': None, 'parent': None, 'label': label,
                'destination': destination}
            bookmark_list.append(bookmark)
            if level < bookmark_level():
                count = 0
                while level < bookmark_level():
                    count += bookmark_levels.pop(bookmark_level())['count'] + 1
                bookmark['prev'] = bookmark_list.index(bookmark_levels[level])
                bookmark['parent'] = bookmark_list.index(
                    bookmark_levels[level - 1])
                bookmark_levels[level]['next'] = i
                bookmark_levels[level - 1]['count'] += count + 1
            elif level > bookmark_level():
                level = min(level, bookmark_level() + 1)
                bookmark['parent'] = i - 1
                bookmark_levels[level - 1]['first'] = i
                bookmark_levels[level - 1]['count'] += 1
            else:
                bookmark['prev'] = bookmark_list.index(bookmark_levels[level])
                bookmark['parent'] = bookmark_list.index(
                    bookmark_levels[level - 1])
                bookmark_levels[level]['next'] = i
                bookmark_levels[level - 1]['count'] += (
                    bookmark_levels[level]['count'] + 1)
            bookmark_levels[level - 1]['last'] = i
            bookmark_levels[level] = bookmark

        bookmark_levels[level - 1]['count'] += (
            bookmark_levels[level]['count'] + 1)
        bookmark_list[0]['parent'] = None

        if hasattr(target, 'write'):
            pdf.write(bytesio, target, links, destinations, bookmark_list)
        else:
            with open(target, 'wb') as fd:
                pdf.write(bytesio, fd, links, destinations, bookmark_list)

    def _get_bookmarks(self, page=None, box=None):
        if page is None:
            for page in self.pages:
                for bookmark in self._get_bookmarks(page, page):
                    yield bookmark
        else:
            if box.bookmark_label and box.style.bookmark_level != 'none':
                position_x = box.position_x
                position_y = page.outer_height - box.position_y
                yield (
                    box.style.bookmark_level,
                    box.bookmark_label,
                    (self.pages.index(page),
                     position_x / LENGTHS_TO_PIXELS['pt'],
                     position_y / LENGTHS_TO_PIXELS['pt']))

            if isinstance(box, boxes.ParentBox):
                for child in box.children:
                    for bookmark in self._get_bookmarks(page, child):
                        yield bookmark

    def _get_link_rectangles(self, page, box=None):
        if box is None:
            box = page

        if box.style.link:
            position_x = box.position_x
            position_y = page.outer_height - box.position_y
            yield (
                box.style.link,
                position_x / LENGTHS_TO_PIXELS['pt'],
                position_y / LENGTHS_TO_PIXELS['pt'],
                (position_x + box.margin_width()) / LENGTHS_TO_PIXELS['pt'],
                (position_y - box.margin_height()) / LENGTHS_TO_PIXELS['pt'])

        if isinstance(box, boxes.ParentBox):
            for child in box.children:
                for rectangle in self._get_link_rectangles(page, child):
                    yield rectangle

    def _get_link_destinations(self, page=None, box=None, names=None):
        if page is None:
            names = set()
            for page in self.pages:
                for destination in self._get_link_destinations(
                        page, page, names):
                    yield destination
        else:
            if box.style.anchor and box.style.anchor not in names:
                names.add(box.style.anchor)
                position_x = box.position_x
                position_y = page.outer_height - box.position_y
                yield (
                    box.style.anchor,
                    (self.pages.index(page),
                     position_x / LENGTHS_TO_PIXELS['pt'],
                     position_y / LENGTHS_TO_PIXELS['pt']))

            if isinstance(box, boxes.ParentBox):
                for child in box.children:
                    for destination in self._get_link_destinations(
                            page, child, names):
                        yield destination
