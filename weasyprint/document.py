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
import shutil

import cairo

from .css import get_all_computed_styles
from .formatting_structure.build import build_formatting_structure
from . import layout
from . import draw
from . import images
from . import pdf


class Document(object):
    """Abstract output document."""
    def __init__(self, element_tree, enable_hinting, url_fetcher,
                 user_stylesheets, user_agent_stylesheets):
        self.element_tree = element_tree  #: lxml HtmlElement object
        self.enable_hinting = enable_hinting
        self.url_fetcher = url_fetcher
        self.user_stylesheets = user_stylesheets
        self.user_agent_stylesheets = user_agent_stylesheets
        self._image_cache = {}
        self._computed_styles = None
        self._formatting_structure = None
        self._pages = None

    # This is mostly useful to make pseudo_type optional.
    def style_for(self, element, pseudo_type=None):
        """
        Convenience method to get the computed styles for an element.
        """
        return self.computed_styles.get((element, pseudo_type))

    @property
    def computed_styles(self):
        """
        dict of (element, pseudo_element_type) -> StyleDict
        StyleDict: a dict of property_name -> PropertyValue,
                   also with attribute access
        """
        if self._computed_styles is None:
            self._computed_styles = get_all_computed_styles(
                self.element_tree, url_fetcher=self.url_fetcher,
                user_stylesheets=self.user_stylesheets,
                ua_stylesheets=self.user_agent_stylesheets,
                medium='print')
        return self._computed_styles

    @property
    def formatting_structure(self):
        """
        The root of the formatting structure tree, ie. the Box
        for the root element.
        """
        if self._formatting_structure is None:
            self._formatting_structure = build_formatting_structure(
                self.element_tree, self.style_for, self.get_image_from_uri)
        return self._formatting_structure

    @property
    def pages(self):
        """
        List of layed-out pages with an absolute size and postition
        for every box.
        """
        if self._pages is None:
            context = layout.LayoutContext(
                self.enable_hinting, self.style_for, self.get_image_from_uri)
            self._pages = list(layout.layout_document(
                context, self.formatting_structure))
        return self._pages

    def get_image_from_uri(self, uri, type_=None):
        return images.get_image_from_uri(
            self._image_cache, self.url_fetcher, uri, type_)

    def get_png_surfaces(self, resolution=None):
        """Yield (width, height, image_surface) tuples, one for each page."""
        px_resolution = (resolution or 96) / 96
        for page in self.pages:
            width = int(math.ceil(page.margin_width() * px_resolution))
            height = int(math.ceil(page.margin_height() * px_resolution))
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
            context = draw.make_cairo_context(
                surface, self.enable_hinting, self.get_image_from_uri)
            context.scale(px_resolution, px_resolution)
            draw.draw_page(page, context)
            yield width, height, surface

    def get_png_pages(self, resolution=None):
        """Yield (width, height, png_bytes) tuples, one for each page."""
        for width, height, surface in self.get_png_surfaces(resolution):
            file_obj = io.BytesIO()
            surface.write_to_png(file_obj)
            yield width, height, file_obj.getvalue()

    def write_png(self, target=None, resolution=None):
        """Write a single PNG image."""
        surfaces = list(self.get_png_surfaces(resolution))
        if len(surfaces) == 1:
            _, _, surface = surfaces[0]
        else:
            total_height = sum(height for _, height, _ in surfaces)
            max_width = max(width for width, _, _ in surfaces)
            surface = cairo.ImageSurface(
                cairo.FORMAT_ARGB32, max_width, total_height)
            context = cairo.Context(surface)
            pos_y = 0
            for width, height, page_surface in surfaces:
                pos_x = (max_width - width) // 2
                context.set_source_surface(page_surface, pos_x, pos_y)
                context.paint()
                pos_y += height

        if target is None:
            target = io.BytesIO()
            surface.write_to_png(target)
            return target.getvalue()
        else:
            surface.write_to_png(target)

    def write_pdf(self, target=None):
        """Write a single PNG image."""
        # Use an in-memory buffer. We will need to seek for metadata
        # TODO: avoid this if target can seek? Benchmark first.
        file_obj = io.BytesIO()
        # We’ll change the surface size for each page
        surface = cairo.PDFSurface(file_obj, 1, 1)
        px_to_pt = pdf.PX_TO_PT
        for page in self.pages:
            surface.set_size(page.margin_width() * px_to_pt,
                             page.margin_height() * px_to_pt)
            context = draw.make_cairo_context(
                surface, self.enable_hinting, self.get_image_from_uri)
            context.scale(px_to_pt, px_to_pt)
            draw.draw_page(page, context)
            surface.show_page()
        surface.finish()

        pdf.write_pdf_metadata(self.pages, file_obj)

        if target is None:
            return file_obj.getvalue()
        else:
            file_obj.seek(0)
            if hasattr(target, 'write'):
                shutil.copyfileobj(file_obj, target)
            else:
                with open(target, 'wb') as fd:
                    shutil.copyfileobj(file_obj, fd)
