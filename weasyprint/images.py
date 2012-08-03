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

import cairo

from .css.computed_values import LENGTHS_TO_PIXELS
from .logger import LOGGER
from .text import USING_INTROSPECTION

# TODO: currently CairoSVG only support images with an explicit
# width and height. When it supports images with only an intrinsic ratio
# this API will need to change.


# Do not try to import PyGObject 3 if we already have PyGTK
# that tends to segfault.
if not USING_INTROSPECTION:
    from gtk import gdk
    from gtk.gdk import PixbufLoader

    def save_pixels_to_png(pixels, width, height, filename):
        """Save raw pixels to a PNG file through pixbuf and PyGTK."""
        gdk.pixbuf_new_from_data(
            pixels, gdk.COLORSPACE_RGB, True, 8, width, height, width * 4
        ).save(filename, 'png')

    def gdkpixbuf_loader(file_obj, string):
        """Load raster images with gdk-pixbuf through PyGTK."""
        pixbuf = get_pixbuf(file_obj, string)
        dummy_context = cairo.Context(cairo.PDFSurface(None, 1, 1))
        gdk.CairoContext(dummy_context).set_source_pixbuf(pixbuf, 0, 0)
        pattern = dummy_context.get_source()
        result = pattern, pixbuf.get_width(), pixbuf.get_height()
        return lambda: result
else:
    # Use PyGObject introspection
    try:
        from gi.repository import GdkPixbuf
    except ImportError:
        LOGGER.warn('Could not import gdk-pixbuf-introspection: raster '
                    'images formats other than PNG will not be supported.')
    else:
        from gi.repository.GdkPixbuf import PixbufLoader
        PIXBUF_VERSION = (GdkPixbuf.PIXBUF_MAJOR,
                          GdkPixbuf.PIXBUF_MINOR,
                          GdkPixbuf.PIXBUF_MICRO)
        if PIXBUF_VERSION < (2, 25, 0):
            LOGGER.warn('Using gdk-pixbuf %s.%s.%s with introspection. '
                        'Versions before 2.25.0 are known to be buggy.',
                        *PIXBUF_VERSION)

    def save_pixels_to_png(pixels, width, height, filename):
        """Save raw pixels to a PNG file through pixbuf and introspection."""
        from gi.repository import GdkPixbuf
        GdkPixbuf.Pixbuf.new_from_data(
            pixels, GdkPixbuf.Colorspace.RGB, True, 8,
            width, height, width * 4, None, None
        ).savev(filename, 'png', [], [])

    try:
        # Unfornately cairo_set_source_pixbuf is not part of Pixbuf itself
        from gi.repository import Gdk

        def gdkpixbuf_loader(file_obj, string):
            """Load raster images with gdk-pixbuf through introspection+Gdk."""
            pixbuf = get_pixbuf(file_obj, string)
            dummy_context = cairo.Context(cairo.PDFSurface(None, 1, 1))
            Gdk.cairo_set_source_pixbuf(dummy_context, pixbuf, 0, 0)
            pattern = dummy_context.get_source()
            result = pattern, pixbuf.get_width(), pixbuf.get_height()
            return lambda: result

    except ImportError:
        # Gdk is not available, go through PNG.
        def gdkpixbuf_loader(file_obj, string):
            """Load raster images with gdk-pixbuf through introspection,
            without Gdk and going through PNG.

            """
            pixbuf = get_pixbuf(file_obj, string)
            _, png = pixbuf.save_to_bufferv('png', ['compression'], ['0'])
            return cairo_png_loader(None, png)


def get_pixbuf(file_obj=None, string=None, chunck_size=16 * 1024):
    """Create a Pixbuf object."""
    loader = PixbufLoader()
    try:
        if file_obj:
            while 1:
                chunck = file_obj.read(chunck_size)
                if not chunck:
                    break
                loader.write(chunck)
        elif string:
            loader.write(string)
        else:
            raise ValueError('Could not load image: empty content')
    finally:
        # Pixbuf is really unhappy if we don’t do this:
        loader.close()
    return loader.get_pixbuf()


def cairo_png_loader(file_obj, string):
    """Return a cairo Surface from a PNG byte stream."""
    surface = cairo.ImageSurface.create_from_png(file_obj or BytesIO(string))
    pattern = cairo.SurfacePattern(surface)
    result = pattern, surface.get_width(), surface.get_height()
    return lambda: result


def cairosvg_loader(file_obj, string, uri):
    """Return a cairo Surface from a SVG byte stream.

    This loader uses CairoSVG: http://cairosvg.org/
    """
    from cairosvg.surface import SVGSurface
    from cairosvg.parser import Tree

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
    if file_obj:
        string = file_obj.read()

    # Do not keep a Surface object alive, but regenerate it as needed.
    # If a surface for a SVG image is still alive by the time we call
    # show_page(), cairo will rasterize the image instead writing vectors.
    def draw_svg():
        # Draw to a cairo surface but do not write to a file
        tree = Tree(bytestring=string, url=uri)
        surface = ScaledSVGSurface(tree, output=None, dpi=96)
        if not (surface.width > 0 and surface.height > 0):
            raise ValueError(
                'Images without an intrinsic size are not supported.')
        pattern = cairo.SurfacePattern(surface.cairo)
        return pattern, surface.width, surface.height

    return draw_svg


def get_image_from_uri(cache, url_fetcher, uri, type_=None):
    """Get a :class:`cairo.Surface`` from an image URI."""
    try:
        missing = object()
        function = cache.get(uri, missing)
        if function is not missing:
            return function()
        result = url_fetcher(uri)
        try:
            if not type_:
                type_ = result['mime_type']  # Use eg. the HTTP header
            #else: the type was forced by eg. a 'type' attribute on <embed>
            if type_ == 'image/svg+xml':
                function = cairosvg_loader(
                    result.get('file_obj'), result.get('string'), uri)
            elif type_ == 'image/png':
                function = cairo_png_loader(
                    result.get('file_obj'), result.get('string'))
            else:
                function = gdkpixbuf_loader(
                    result.get('file_obj'), result.get('string'))
        finally:
            if 'file_obj' in result:
                try:
                    result['file_obj'].close()
                except Exception:  # pragma: no cover
                    # May already be closed or something.
                    # This is just cleanup anyway.
                    pass

        cache[uri] = function
        return function()
    except Exception as exc:
        LOGGER.warn('Error for image at %s : %r', uri, exc)
