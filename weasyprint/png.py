# coding: utf8
"""
    weasyprint.png
    ---------------

    PNG output.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import io
import sys
import math

import cairo

from .urls import FILESYSTEM_ENCODING
from .draw import stacked
from .compat import izip


def pages_to_surface(pages, resolution=None):
    """Paint pages vertically for pixel output.

    :param pages: a list of Page objects
    :param resolution: PNG pixels per CSS inch, defaults to 96.
    :returns: a cairo.ImageSurface object

    """
    px_resolution = (resolution or 96) / 96
    widths = [int(math.ceil(p.width * px_resolution)) for p in pages]
    heights = [int(math.ceil(p.height * px_resolution)) for p in pages]
    max_width = max(widths)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, max_width, sum(heights))
    context = cairo.Context(surface)

    pos_y = 0
    for page, width, height in izip(pages, widths, heights):
        pos_x = (max_width - width) // 2
        with stacked(context):
            # Translate and clip at integer PNG pixel coordinates,
            # not float CSS px.
            context.translate(pos_x, pos_y)
            context.rectangle(0, 0, width, height)
            context.clip()
            context.scale(px_resolution, px_resolution)
            page.paint(context)
        pos_y += height
    return surface


def surface_to_png(surface, target=None):
    """Write PNG bytes to ``target``, or return them if ``target`` is ``None``.

    :param surface: a cairo.ImageSurface object
    :param target: a filename, file object, or ``None``
    :returns: a bytestring if ``target`` is ``None``.

    """
    if target is None:
        target = io.BytesIO()
        surface.write_to_png(target)
        return target.getvalue()
    else:
        if sys.version_info[0] < 3 and isinstance(target, unicode):
            # py2cairo 1.8 does not support unicode filenames.
            target = target.encode(FILESYSTEM_ENCODING)
        surface.write_to_png(target)


def pages_to_png(pages, resolution=None, target=None):
    """Paint pages vertically; write PNG bytes to ``target``, or return them
    if ``target`` is ``None``.

    :param pages: a list of Page objects
    :param target: a filename, file object, or ``None``
    :returns: a bytestring if ``target`` is ``None``.

    """
    return surface_to_png(pages_to_surface(pages, resolution), target)
