# coding: utf8
"""
    weasyprint.images
    -----------------

    Fetch and decode images in various formats.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division
# XXX No unicode_literals, cffi likes native strings

import sys
from io import BytesIO
from functools import partial

import cffi
import cairocffi as cairo

from .logger import LOGGER
from .compat import xrange


ffi = cffi.FFI()
ffi.cdef('''

    typedef unsigned long   gsize;
    typedef unsigned int    guint32;
    typedef unsigned int    guint;
    typedef unsigned char   guchar;
    typedef char        gchar;
    typedef int         gint;
    typedef gint        gboolean;
    typedef guint32     GQuark;
    typedef void*       gpointer;
    typedef struct {
        GQuark       domain;
        gint         code;
        gchar       *message;
    } GError;
    typedef struct {
        gchar *name;
        /* ... */
    } GdkPixbufFormat;
    typedef enum {
        GDK_COLORSPACE_RGB
    } GdkColorspace;
    typedef ...         GdkPixbufLoader;
    typedef ...         GdkPixbuf;


    GdkPixbufLoader * gdk_pixbuf_loader_new          (void);
    GdkPixbufFormat * gdk_pixbuf_loader_get_format   (GdkPixbufLoader *loader);
    GdkPixbuf *       gdk_pixbuf_loader_get_pixbuf   (GdkPixbufLoader *loader);
    gboolean          gdk_pixbuf_loader_write        (
        GdkPixbufLoader *loader, const guchar *buf, gsize count,
        GError **error);
    gboolean          gdk_pixbuf_loader_close        (
        GdkPixbufLoader *loader, GError **error);


    GdkColorspace     gdk_pixbuf_get_colorspace      (const GdkPixbuf *pixbuf);
    int               gdk_pixbuf_get_n_channels      (const GdkPixbuf *pixbuf);
    gboolean          gdk_pixbuf_get_has_alpha       (const GdkPixbuf *pixbuf);
    int               gdk_pixbuf_get_bits_per_sample (const GdkPixbuf *pixbuf);
    int               gdk_pixbuf_get_width           (const GdkPixbuf *pixbuf);
    int               gdk_pixbuf_get_height          (const GdkPixbuf *pixbuf);
    int               gdk_pixbuf_get_rowstride       (const GdkPixbuf *pixbuf);
    guchar *          gdk_pixbuf_get_pixels          (const GdkPixbuf *pixbuf);
    gsize             gdk_pixbuf_get_byte_length     (const GdkPixbuf *pixbuf);
    GdkPixbuf *       gdk_pixbuf_add_alpha           (
        const GdkPixbuf *pixbuf, gboolean substitute_color,
        guchar r, guchar g, guchar b);

    void              g_object_ref                   (gpointer object);
    void              g_object_unref                 (gpointer object);
    void              g_error_free                   (GError *error);
    void              g_type_init                    (void);

''')

gobject = ffi.dlopen('gobject-2.0')
gdk_pixbuf = ffi.dlopen('gdk_pixbuf-2.0')

gobject.g_type_init()
cairo.install_as_pycairo()  # for CairoSVG


# TODO: currently CairoSVG only support images with an explicit
# width and height. When it supports images with only an intrinsic ratio
# this API will need to change.


def handle_g_error(error):
    if error != ffi.NULL:
        error_message = error.message
        gobject.g_error_free(error)
        return ValueError(
            'Pixbuf error: ' + error_message.decode('utf8', 'replace'))


class Pixbuf(object):
    def __init__(self, handle):
        self._handle = ffi.gc(handle, gobject.g_object_unref)

    def __getattr__(self, name):
        return partial(getattr(gdk_pixbuf, 'gdk_pixbuf_' + name), self._handle)


def get_pixbuf(file_obj=None, string=None):
    """Create a Pixbuf object."""
    if file_obj:
        string = file_obj.read()
    if not string:
        raise ValueError('Could not load image: empty content')
    loader = ffi.gc(
        gdk_pixbuf.gdk_pixbuf_loader_new(), gobject.g_object_unref)
    error = ffi.new('GError **')

    gdk_pixbuf.gdk_pixbuf_loader_write(
        loader, ffi.new('guchar[]', string), len(string), error)
    write_exception = handle_g_error(error[0])
    gdk_pixbuf.gdk_pixbuf_loader_close(loader, error)
    close_exception = handle_g_error(error[0])
    if write_exception is not None:
        raise write_exception  # Only after closing
    if close_exception is not None:
        raise close_exception

    format_ = gdk_pixbuf.gdk_pixbuf_loader_get_format(loader)
    is_jpeg = format_ != ffi.NULL and ffi.string(format_.name) == b'jpeg'
    jpeg_data = string if is_jpeg else None

    pixbuf = gdk_pixbuf.gdk_pixbuf_loader_get_pixbuf(loader)
    assert pixbuf != ffi.NULL
    gobject.g_object_ref(pixbuf)
    return Pixbuf(pixbuf), jpeg_data


def gdkpixbuf_loader(file_obj, string):
    """Load raster images with gdk-pixbuf through introspection
    and Gdk.

    """
    pixbuf, jpeg_data = get_pixbuf(file_obj, string)
    if not pixbuf.get_has_alpha():
        # False means: no "substitute" color that becomes transparent.
        pixbuf = Pixbuf(pixbuf.add_alpha(False, 0, 0, 0))
    assert pixbuf.get_colorspace() == 'GDK_COLORSPACE_RGB'
    assert pixbuf.get_n_channels() == 4
    width = pixbuf.get_width()
    height = pixbuf.get_height()
    rowstride = pixbuf.get_width()
    pixels = ffi.buffer(pixbuf.get_pixels(), pixbuf.get_byte_length())
    # TODO: remove this when cffi buffers support slicing.
    pixels = pixels[:]

    # Convert GdkPixbuf’s big-endian RGBA to cairo’s native-endian ARGB
    cairo_stride = cairo.ImageSurface.format_stride_for_width('ARGB32', width)
    data = bytearray(cairo_stride * height)
    big_endian = sys.byteorder == 'big'
    row_length = width * 4  # stride == row_length + padding
    for y in xrange(height):
        offset = rowstride * y
        end = offset + row_length
        red = pixels[offset:end:4]
        green = pixels[offset + 1:end:4]
        blue = pixels[offset + 2:end:4]
        alpha = pixels[offset + 3:end:4]
        offset = cairo_stride * y
        end = offset + row_length
        if big_endian:
            data[offset:end:4] = alpha
            data[offset + 1:end:4] = red
            data[offset + 2:end:4] = green
            data[offset + 3:end:4] = blue
        else:
            data[offset + 3:end:4] = alpha
            data[offset + 2:end:4] = red
            data[offset + 1:end:4] = green
            data[offset:end:4] = blue

    surface = cairo.ImageSurface('ARGB32', width, height, data, cairo_stride)
    add_jpeg_data(surface, jpeg_data)
    get_pattern = lambda: cairo.SurfacePattern(surface)
    return get_pattern, width, height


def cairo_png_loader(file_obj, string, jpeg_data=None):
    """Return a cairo Surface from a PNG byte stream."""
    surface = cairo.ImageSurface.create_from_png(file_obj or BytesIO(string))
    add_jpeg_data(surface, jpeg_data)
    get_pattern = lambda: cairo.SurfacePattern(surface)
    return get_pattern, surface.get_width(), surface.get_height()


def add_jpeg_data(surface, jpeg_data):
    if jpeg_data:
        # TODO: remove this when cffi/cairocffi support byte string as buffers.
        jpeg_data = bytearray(jpeg_data)
        surface.set_mime_data('image/jpeg', jpeg_data)


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
#        import traceback
#        traceback.print_exc()
        image = None
    cache[uri] = image
    return image
