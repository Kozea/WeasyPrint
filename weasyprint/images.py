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

import cairocffi
cairocffi.install_as_pycairo()  # for CairoSVG

import cairosvg.parser
import cairosvg.surface
assert cairosvg.surface.cairo is cairocffi, (
    'CairoSVG is using pycairo instead of cairocffi. '
    'Make sure it is not imported before WeasyPrint.')

try:
    from cairocffi import pixbuf
except OSError:
    pixbuf = None

from .logger import LOGGER


def gdkpixbuf_loader(file_obj, string):
    """Load raster images with GDK-PixBuf."""
    if pixbuf is None:
        raise OSError(
            'Could not load GDK-Pixbuf. '
            'PNG and SVG are the only image formats available.')
    if string is None:
        string = file_obj.read()
    surface, format_name = pixbuf.decode_to_image_surface(string)
    if format_name == 'jpeg':
        surface.set_mime_data('image/jpeg', string)
    get_pattern = lambda: cairocffi.SurfacePattern(surface)
    return get_pattern, surface.get_width(), surface.get_height()


def cairo_png_loader(file_obj, string):
    """Return a cairo Surface from a PNG byte stream."""
    surface = cairocffi.ImageSurface.create_from_png(
        file_obj or BytesIO(string))
    get_pattern = lambda: cairocffi.SurfacePattern(surface)
    return get_pattern, surface.get_width(), surface.get_height()


class ScaledSVGSurface(cairosvg.surface.SVGSurface):
    """
    Have the cairo Surface object have intrinsic dimension
    in pixels instead of points.
    """
    @property
    def device_units_per_user_units(self):
        scale = super(ScaledSVGSurface, self).device_units_per_user_units
        return scale / 0.75


def cairosvg_loader(file_obj, string, uri):
    """Return a cairo Surface from a SVG byte stream.

    This loader uses CairoSVG: http://cairosvg.org/
    """
    if uri.lower().startswith('data:'):
        # Don’t pass data URIs to CairoSVG.
        # They are useless for relative URIs anyway.
        uri = None
    if file_obj:
        string = file_obj.read()

    def get_surface():
        tree = cairosvg.parser.Tree(bytestring=string, url=uri)
        # Draw to a cairo surface but do not write to a file
        surface = ScaledSVGSurface(tree, output=None, dpi=96)
        return surface.cairo, surface.width, surface.height

    def get_pattern():
        # Do not re-use the Surface object, but regenerate it as needed.
        # If a surface for a SVG image is still alive by the time we call
        # show_page(), cairo will rasterize the image instead writing vectors.
        surface, _, _ = get_surface()
        return cairocffi.SurfacePattern(surface)

    # Render once to get the size and trigger any exception.
    # If this does not raise, future calls to get_pattern() will hopefully
    # not raise either.
    _, width, height = get_surface()
    if not (width > 0 and height > 0):
        raise ValueError('Images without an intrinsic size are not supported.')
    return get_pattern, width, height


def get_image_from_uri(cache, url_fetcher, uri, type_=None):
    """Get a cairo Pattern from an image URI."""
    try:
        missing = object()
        image = cache.get(uri, missing)
        if image is not missing:
            return image
        result = url_fetcher(uri)
        try:
            if not type_:
                type_ = result['mime_type']  # Use eg. the HTTP header
            #else: the type was forced by eg. a 'type' attribute on <embed>

            if type_ == 'image/svg+xml':
                image = cairosvg_loader(
                    result.get('file_obj'), result.get('string'), uri)
            elif type_ == 'image/png':
                image = cairo_png_loader(
                    result.get('file_obj'), result.get('string'))
            else:
                image = gdkpixbuf_loader(
                    result.get('file_obj'), result.get('string'))
        finally:
            if 'file_obj' in result:
                try:
                    result['file_obj'].close()
                except Exception:  # pragma: no cover
                    # May already be closed or something.
                    # This is just cleanup anyway.
                    pass
    except Exception as exc:
        LOGGER.warn('Error for image at %s : %r', uri, exc)
        image = None
    cache[uri] = image
    return image
