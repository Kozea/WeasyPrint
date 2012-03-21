# coding: utf8
"""
    weasyprint.images
    -----------------

    Fetch and decode images in various formats.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from io import BytesIO
import contextlib

import cairo

from .utils import urlopen
from .css.computed_values import LENGTHS_TO_PIXELS
from .logger import LOGGER


# Map MIME types to functions that take a byte stream and return
# ``(pattern, width, height)`` a cairo Pattern and its dimension in pixels.
FORMAT_HANDLERS = {}

# TODO: currently CairoSVG only support images with an explicit
# width and height. When it supports images with only an intrinsic ratio
# this API will need to change.


def register_format(mime_type):
    """Register a handler for a give image MIME type."""
    def _decorator(function):
        FORMAT_HANDLERS[mime_type] = function
        return function
    return _decorator


@register_format('image/png')
def png_handler(file_like, _uri):
    """Return a cairo Surface from a PNG byte stream."""
    surface = cairo.ImageSurface.create_from_png(file_like)
    pattern = cairo.SurfacePattern(surface)
    return pattern, surface.get_width(), surface.get_height()


@register_format('image/svg+xml')
def cairosvg_handler(file_like, uri):
    """Return a cairo Surface from a SVG byte stream.

    This handler uses CairoSVG: http://cairosvg.org/
    """
    from cairosvg.surface import SVGSurface
    from cairosvg.parser import Tree, ParseError

    class ScaledSVGSurface(SVGSurface):
        """
        Have the cairo Surface object have intrinsic dimension
        in pixels instead of points.
        """
        @property
        def device_units_per_user_units(self):
            scale = super(ScaledSVGSurface, self).device_units_per_user_units
            return scale * LENGTHS_TO_PIXELS['pt']

    if uri.startswith('data:'):
        # Don’t pass data URIs to CairoSVG.
        # They are useless for relative URIs anyway.
        uri = None
    # Draw to a cairo surface but do not write to a file
    tree = Tree(file_obj=file_like, url=uri)
    surface = ScaledSVGSurface(tree, output=None, dpi=96)
    pattern = cairo.SurfacePattern(surface.cairo)
    return pattern, surface.width, surface.height


def fallback_handler(file_like, uri):
    """
    Parse a byte stream with PIL and return a cairo Surface.

    PIL supports many raster image formats and does not take a `format`
    parameter, it guesses the format from the content.
    """
    from pystacia import read_blob
    from pystacia.util import TinyException
    with contextlib.closing(read_blob(file_like.read())) as image:
        png_bytes = image.get_blob('png')
    return png_handler(BytesIO(png_bytes), uri)


def get_image_from_uri(uri, type_=None):
    """Get a :class:`cairo.Surface`` from an image URI."""
    try:
        file_like, mime_type, _charset = urlopen(uri)
        if not type_:
            type_ = mime_type  # Use eg. the HTTP header
        #else: the type was forced by eg. a 'type' attribute on <embed>
        handler = FORMAT_HANDLERS.get(type_, fallback_handler)
        return handler(file_like, uri)
    except Exception as exc:
        LOGGER.warn('Error for image at %s : %r', uri, exc)
    finally:
        try:
            file_like.close()
        except Exception:
            # May already be closed or something. This is just cleanup anyway.
            pass
