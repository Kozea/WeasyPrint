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
import sys
import math
import shutil
import functools

import cairo

from .css import get_all_computed_styles
from .formatting_structure.build import build_formatting_structure
from .urls import FILESYSTEM_ENCODING
from . import layout
from . import draw
from . import images
from . import pdf


class Document(object):
    """Abstract output document."""
    def __init__(self, element_tree, enable_hinting, url_fetcher, media_type,
                 user_stylesheets, ua_stylesheets):
        self.element_tree = element_tree  #: lxml HtmlElement object
        self.enable_hinting = enable_hinting
        self.style_for = get_all_computed_styles(
            element_tree, media_type, url_fetcher,
            user_stylesheets, ua_stylesheets)
        self.get_image_from_uri =  functools.partial(
            images.get_image_from_uri, {}, url_fetcher)

    def render_pages(self):
        """Do the layout and return a list of page boxes."""
        return list(layout.layout_document(
            self.enable_hinting, self.style_for, self.get_image_from_uri,
            build_formatting_structure(
                self.element_tree, self.style_for, self.get_image_from_uri)))

    def draw_page(self, page, surface, scale):
        """Draw page on surface at scale cairo device units per CSS pixel."""
        return draw.draw_page(self.enable_hinting, self.get_image_from_uri,
                              page, surface, scale)

    def get_png_surfaces(self, resolution=None):
        """Yield (width, height, image_surface) tuples, one for each page."""
        px_resolution = (resolution or 96) / 96
        for page in self.render_pages():
            width = int(math.ceil(page.margin_width() * px_resolution))
            height = int(math.ceil(page.margin_height() * px_resolution))
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
            self.draw_page(page, surface, px_resolution)
            yield width, height, surface, page

    def get_png_pages(self, resolution=None, _with_pages=False):
        """Yield (width, height, png_bytes) tuples, one for each page."""
        for width, height, surface, page in self.get_png_surfaces(resolution):
            file_obj = io.BytesIO()
            surface.write_to_png(file_obj)
            if _with_pages:
                yield width, height, file_obj.getvalue(), page
            else:
                yield width, height, file_obj.getvalue()

    def write_png(self, target=None, resolution=None):
        """Write a single PNG image."""
        surfaces = list(self.get_png_surfaces(resolution))
        if len(surfaces) == 1:
            _, _, surface, _ = surfaces[0]
        else:
            total_height = sum(height for _, height, _, _ in surfaces)
            max_width = max(width for width, _, _, _ in surfaces)
            surface = cairo.ImageSurface(
                cairo.FORMAT_ARGB32, max_width, total_height)
            context = cairo.Context(surface)
            pos_y = 0
            for width, height, page_surface, _ in surfaces:
                pos_x = (max_width - width) // 2
                context.set_source_surface(page_surface, pos_x, pos_y)
                context.paint()
                pos_y += height

        if target is None:
            target = io.BytesIO()
            surface.write_to_png(target)
            return target.getvalue()
        else:
            if sys.version_info[0] < 3 and isinstance(target, unicode):
                # py2cairo 1.8 does not support unicode filenames.
                target = target.encode(FILESYSTEM_ENCODING)
            surface.write_to_png(target)

    def write_pdf(self, target=None):
        """Write a single PNG image."""
        # Use an in-memory buffer. We will need to seek for metadata
        # TODO: avoid this if target can seek? Benchmark first.
        file_obj = io.BytesIO()
        # We’ll change the surface size for each page
        surface = cairo.PDFSurface(file_obj, 1, 1)
        px_to_pt = pdf.PX_TO_PT
        pages = self.render_pages()
        for page in pages:
            surface.set_size(page.margin_width() * px_to_pt,
                             page.margin_height() * px_to_pt)
            self.draw_page(page, surface, px_to_pt)
            surface.show_page()
        surface.finish()

        pdf.write_pdf_metadata(pages, file_obj)

        if target is None:
            return file_obj.getvalue()
        else:
            file_obj.seek(0)
            if hasattr(target, 'write'):
                shutil.copyfileobj(file_obj, target)
            else:
                with open(target, 'wb') as fd:
                    shutil.copyfileobj(file_obj, fd)
