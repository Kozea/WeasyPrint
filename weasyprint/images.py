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

from .logger import LOGGER
from .text import USING_INTROSPECTION

# TODO: currently CairoSVG only support images with an explicit
# width and height. When it supports images with only an intrinsic ratio
# this API will need to change.


# None as a the target for PDFSurface is new in pycairo 1.8.8.
# This helps with compat with earlier versions:
_DUMMY_FILE = BytesIO()
DUMMY_SURFACE = cairo.PDFSurface(_DUMMY_FILE, 1, 1)


# Do not try to import PyGObject 3 if we already have PyGTK
# that tends to segfault.
if not USING_INTROSPECTION:
    # Use PyGObject introspection
    try:
        from gtk import gdk
        from gtk.gdk import PixbufLoader
    # Old version of PyGTK raise RuntimeError when there is not X server.
    except (ImportError, RuntimeError) as exception:
        def gdkpixbuf_loader(file_obj, string, pixbuf_error=exception):
            raise pixbuf_error
    else:
        def gdkpixbuf_loader(file_obj, string):
            """Load raster images with gdk-pixbuf through PyGTK."""
            pixbuf = get_pixbuf(file_obj, string)
            dummy_context = cairo.Context(DUMMY_SURFACE)
            gdk.CairoContext(dummy_context).set_source_pixbuf(pixbuf, 0, 0)
            surface = dummy_context.get_source().get_surface()
            get_pattern = lambda: cairo.SurfacePattern(surface)
            return get_pattern, pixbuf.get_width(), pixbuf.get_height()
else:
    # Use PyGObject introspection
    try:
        from gi.repository import GdkPixbuf
        from gi.repository.GdkPixbuf import PixbufLoader
    except ImportError as exception:
        def gdkpixbuf_loader(file_obj, string, pixbuf_error=exception):
            raise pixbuf_error
    else:
        PIXBUF_VERSION = (GdkPixbuf.PIXBUF_MAJOR,
                          GdkPixbuf.PIXBUF_MINOR,
                          GdkPixbuf.PIXBUF_MICRO)
        if PIXBUF_VERSION < (2, 25, 0):
            LOGGER.warn('Using gdk-pixbuf %s.%s.%s with introspection. '
                        'Versions before 2.25.0 are known to be buggy. '
                        'Images formats other than PNG may not be supported.',
                        *PIXBUF_VERSION)
        try:
            # Unfornately cairo_set_source_pixbuf is not part of Pixbuf itself
            from gi.repository import Gdk

            def gdkpixbuf_loader(file_obj, string):
                """Load raster images with gdk-pixbuf through introspection
                and Gdk.

                """
                pixbuf = get_pixbuf(file_obj, string)
                dummy_context = cairo.Context(DUMMY_SURFACE)
                Gdk.cairo_set_source_pixbuf(dummy_context, pixbuf, 0, 0)
                surface = dummy_context.get_source().get_surface()
                get_pattern = lambda: cairo.SurfacePattern(surface)
                return get_pattern, pixbuf.get_width(), pixbuf.get_height()

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
    get_pattern = lambda: cairo.SurfacePattern(surface)
    return get_pattern, surface.get_width(), surface.get_height()


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
            return scale / 0.75

    if uri.startswith('data:'):
        # Don’t pass data URIs to CairoSVG.
        # They are useless for relative URIs anyway.
        uri = None
    if file_obj:
        string = file_obj.read()

    def get_surface():
        tree = Tree(bytestring=string, url=uri)
        # Draw to a cairo surface but do not write to a file
        surface = ScaledSVGSurface(tree, output=None, dpi=96)
        return surface.cairo, surface.width, surface.height

    def get_pattern():
        # Do not re-use the Surface object, but regenerate it as needed.
        # If a surface for a SVG image is still alive by the time we call
        # show_page(), cairo will rasterize the image instead writing vectors.
        surface, _, _ = get_surface()
        return cairo.SurfacePattern(surface)

    # Render once to get the size and trigger any exception.
    # If this does not raise, future calls to get_pattern() will hopefully
    # not raise either.
    _, width, height = get_surface()
    if not (width > 0 and height > 0):
        raise ValueError('Images without an intrinsic size are not supported.')
    return get_pattern, width, height


def get_image_from_uri(cache, url_fetcher, uri, type_=None):
    """Get a :class:`cairo.Surface`` from an image URI."""
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
