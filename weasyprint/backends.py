# coding: utf8
"""
    weasyprint.backends
    -------------------

    Abstract over the API differences of the various cairo surfaces.

    Expected usage:

    * Create an instance
    * For each page: call .start_page() and paint on the returned context
    * Call .finish()

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import io
import math
import shutil

import cairo

from . import draw
from . import pdf


class SimplePDFBackend(object):
    @classmethod
    def get_dummy_surface(cls):
        return cairo.PDFSurface(None, 1, 1)

    def __init__(self, target):
        # We’ll change the surface size in .start_page()
        self.surface = cairo.PDFSurface(target, 1, 1)
        self.started = False

    def start_page(self, width, height):
        surface = self.surface
        # Start a new page, except if this is the first:
        if self.started:
            surface.show_page()
        else:
            self.started = True

        px_to_pt = pdf.PX_TO_PT
        surface.set_size(width * px_to_pt, height * px_to_pt)
        context = draw.CairoContext(surface)
        context.scale(px_to_pt, px_to_pt)
        return context

    def finish(self, _document):
        self.surface.finish()


class MetadataPDFBackend(SimplePDFBackend):
    def __init__(self, target):
        self.target = target
        self.fileobj = io.BytesIO()
        super(MetadataPDFBackend, self).__init__(self.fileobj)

    def finish(self, document):
        super(MetadataPDFBackend, self).finish(document)
        fileobj = self.fileobj
        target = self.target
        pdf.write_pdf_metadata(document, fileobj)

        fileobj.seek(0)
        if hasattr(target, 'write'):
            shutil.copyfileobj(fileobj, target)
        else:
            with open(target, 'wb') as fd:
                shutil.copyfileobj(fileobj, fd)


class PNGBackend(object):
    @classmethod
    def get_dummy_surface(cls):
        return cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1)

    def __init__(self, target):
        self.target = target
        self.pages = []

    def start_page(self, width, height):
        width = int(math.ceil(width))
        height = int(math.ceil(height))
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        self.pages.append((width, height, surface))
        return draw.CairoContext(surface)

    def finish(self, _document):
        pages = self.pages
        if len(pages) == 1:
            _, _, surface = pages[0]
        else:
            total_height = sum(height for width, height, surface in pages)
            max_width = max(width for width, height, surface in pages)
            surface = cairo.ImageSurface(
                cairo.FORMAT_ARGB32, max_width, total_height)
            context = draw.CairoContext(surface)

            pos_y = 0
            for width, height, page_surface in pages:
                pos_x = (max_width - width) // 2
                context.set_source_surface(page_surface, pos_x, pos_y)
                context.paint()
                pos_y += height

        surface.write_to_png(self.target)
