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
from .css import get_all_computed_styles
from .formatting_structure.build import build_formatting_structure
from .layout import layout_document
from .draw import draw_page, stacked
from .pdf import write_pdf_metadata
from .compat import izip
from .urls import FILESYSTEM_ENCODING


class Page(object):
    """Represents a single rendered page."""
    def __init__(self, page, enable_hinting=False, resolution=96):
        self._page_box = page
        self._enable_hinting = enable_hinting
        self._dppx = resolution / 96
        #: The page width, including margins, in cairo user units.
        self.width = page.margin_width() * self._dppx
        #: The page height, including margins, in cairo user units.
        self.height = page.margin_height() * self._dppx

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
    @classmethod
    def render(cls, html, stylesheets, resolution, enable_hinting):
        style_for = get_all_computed_styles(html, user_stylesheets=[
            css if hasattr(css, 'rules')
            else CSS(guess=css, media_type=html.media_type)
            for css in stylesheets or []])
        get_image_from_uri =  functools.partial(
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
        """Return a new :class:`Document` with a subset of the pages."""
        if pages == 'all':
            pages = self.pages
        return type(self)(pages)

    def write_pdf(self, target=None):
        """Paint pages; write PDF bytes to ``target``, or return them
        if ``target`` is ``None``.

        This function also adds PDF metadata (bookmarks, hyperlinks, …).
        PDF files coming straight from :class:`cairo.PDFSurface` do not have
        such metadata.

        :param target: a filename, file object, or ``None``
        :returns: a bytestring if ``target`` is ``None``.

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

        write_pdf_metadata(self.pages, file_obj)

        if target is None:
            return file_obj.getvalue()
        else:
            file_obj.seek(0)
            if hasattr(target, 'write'):
                shutil.copyfileobj(file_obj, target)
            else:
                with open(target, 'wb') as fd:
                    shutil.copyfileobj(file_obj, fd)

    def write_png(self, target=None, with_size=False):
        """Paint pages vertically; write PNG bytes to ``target``, or return them
        if ``target`` is ``None``.

        :param target: a filename, file object, or ``None``
        :param with_size: if true, also return the size of the PNG image.
        :returns:
            ``output`` or ``(output, png_width, png_height)`` (depending
            on ``with_size``). ``output`` is a byte string (if ``target``
            is ``None``) or ``None``.

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
        if with_size:
            return png_bytes, max_width, sum_heights
        else:
            return png_bytes
