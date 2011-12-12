# coding: utf8

#  WeasyPrint converts web documents (HTML, CSS, ...) to PDF.
#  Copyright (C) 2011  Simon Sapin
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Handle various image formats.
"""

from __future__ import division
from StringIO import StringIO

import cairo

from .utils import urlopen


# Map MIME types to functions that take a byte stream and return
# ``(surface, width, height)`` a cairo Surface and its dimension in pixels.
FORMAT_HANDLERS = {}

# TODO: currently CairoSVG only support images with an explicit
# width and height. When it supports images with only an intrinsic ratio
# this API will need to change.


def register_format(mime_type):
    """Register a handler for a give image MIME type."""
    def decorator(function):
        FORMAT_HANDLERS[mime_type] = function
        return function
    return decorator


@register_format('image/png')
def png_handler(file_like):
    """Return a cairo Surface from a PNG byte stream."""
    surface = cairo.ImageSurface.create_from_png(file_like)
    return surface, surface.get_width(), surface.get_height()


@register_format('image/svg+xml')
def cairosvg_handler(file_like):
    """Return a cairo Surface from a SVG byte stream.

    This handler uses CairoSVG: http://cairosvg.org/
    """
    # TODO: also offer librsvg?
    try:
        import cairosvg
    except ImportError:
        return None
    from cairosvg.surface_type import DummySurface
    # TODO: find a way to pass file_like to the parser, not read the
    # whole string in memory.
    surface = cairosvg.svg2surface(file_like.read(), DummySurface)
    return surface.cairo, surface.width, surface.height


def fallback_handler(file_like):
    """
    Parse a byte stream with PIL and return a cairo Surface.

    PIL supports many raster image formats and does not take a `format`
    parameter, it guesses the format from the content.
    """
    try:
        from PIL import Image
    except ImportError:
        try:
            # It is sometimes installed with another name...
            import Image
        except ImportError:
            return None  # PIL is not installed
    if not (hasattr(file_like, 'seek') and hasattr(file_like, 'tell')):
        # PIL likes to have these methods
        file_like = StringIO(file_like.read())
    png = StringIO()
    image = Image.open(file_like)
    image = image.convert('RGBA')
    image.save(png, "PNG")
    png.seek(0)
    return png_handler(png)


def get_image_surface_from_uri(uri):
    """Get a :class:`cairo.Surface`` from an image URI."""
    try:
        file_like, mime_type, _charset = urlopen(uri)
    except IOError:
        # TODO: warn
        return None
    # TODO: implement image type sniffing?
# http://www.w3.org/TR/html5/fetching-resources.html#content-type-sniffing:-image
    handler = FORMAT_HANDLERS.get(mime_type, fallback_handler)
    try:
        return handler(file_like)
    except (IOError, MemoryError):
        # Network or parsing error
        # TODO: warn
        return None
    finally:
        file_like.close()
