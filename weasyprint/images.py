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
cairo.install_as_pycairo()  # for CairoSVG

import cairosvg.parser
import cairosvg.surface
assert cairosvg.surface.cairo is cairo, (
    'CairoSVG is using pycairo instead of cairocffi. '
    'Make sure it is not imported before WeasyPrint.')


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
    typedef ...         cairo_t;


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
    gboolean          gdk_pixbuf_save_to_buffer      (
        GdkPixbuf *pixbuf, gchar **buffer, gsize *buffer_size,
        const char *type, GError **error, ...);

    void              gdk_cairo_set_source_pixbuf    (
        cairo_t *cr, const GdkPixbuf *pixbuf, double pixbuf_x, double pixbuf_y);


    void              g_object_ref                   (gpointer object);
    void              g_object_unref                 (gpointer object);
    void              g_error_free                   (GError *error);
    void              g_type_init                    (void);

''')

gobject = ffi.dlopen('gobject-2.0')
gdk_pixbuf = ffi.dlopen('gdk_pixbuf-2.0')
try:
    gdk = ffi.dlopen('gdk-3')
except OSError:
    try:
        gdk = ffi.dlopen('gdk-x11-2.0')
    except OSError:
        gdk = None

gobject.g_type_init()


# TODO: currently CairoSVG only support images with an explicit
# width and height. When it supports images with only an intrinsic ratio
# this API will need to change.


def handle_g_error(error, raise_=False):
    if error != ffi.NULL:
        error_message = ffi.string(error.message).decode('utf8', 'replace')
        gobject.g_error_free(error)
        exception = ValueError('Pixbuf error: ' + error_message)
        if raise_:
            raise exception
        else:
            return exception


class Pixbuf(object):
    def __init__(self, handle):
        self._pointer = ffi.gc(handle, gobject.g_object_unref)

    def __getattr__(self, name):
        return partial(getattr(gdk_pixbuf, 'gdk_pixbuf_' + name), self._pointer)


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
    surface = (
        pixbuf_to_cairo_gdk(pixbuf) if gdk is not None
        else pixbuf_to_cairo_slices(pixbuf) if not pixbuf.get_has_alpha()
        else pixbuf_to_cairo_png(pixbuf))
    if jpeg_data:
        surface.set_mime_data('image/jpeg', jpeg_data)
    get_pattern = lambda: cairo.SurfacePattern(surface)
    return get_pattern, surface.get_width(), surface.get_height()


def pixbuf_to_cairo_gdk(pixbuf):
    """Convert with GDK.

    This method is fastest but GDK is not always available.

    """
    dummy_context = cairo.Context(cairo.PDFSurface(None, 1, 1))
    gdk.gdk_cairo_set_source_pixbuf(
        ffi.cast('cairo_t *', dummy_context._pointer), pixbuf._pointer, 0, 0)
    return dummy_context.get_source().get_surface()


def pixbuf_to_cairo_slices(pixbuf):
    """Slice-based byte swapping.

    This method is 2~5x slower than GDK but does not support an alpha channel.
    (cairo uses pre-multiplied alpha, but not Pixbuf.)

    """
    assert pixbuf.get_colorspace() == 'GDK_COLORSPACE_RGB'
    assert pixbuf.get_n_channels() == 3
    assert pixbuf.get_bits_per_sample() == 8
    width = pixbuf.get_width()
    height = pixbuf.get_height()
    rowstride = pixbuf.get_rowstride()
    pixels = ffi.buffer(pixbuf.get_pixels(), pixbuf.get_byte_length())
    # TODO: remove this when cffi buffers support slicing with a stride.
    pixels = pixels[:]

    # Convert GdkPixbuf’s big-endian RGBA to cairo’s native-endian ARGB
    cairo_stride = cairo.ImageSurface.format_stride_for_width('RGB24', width)
    data = bytearray(cairo_stride * height)
    big_endian = sys.byteorder == 'big'
    pixbuf_row_length = width * 3  # stride == row_length + padding
    cairo_row_length = width * 4  # stride == row_length + padding
    for y in xrange(height):
        offset = rowstride * y
        end = offset + pixbuf_row_length
        red = pixels[offset:end:3]
        green = pixels[offset + 1:end:3]
        blue = pixels[offset + 2:end:3]

        offset = cairo_stride * y
        end = offset + cairo_row_length
        if big_endian:
            # data[offset:end:4] is left un-initialized
            data[offset + 1:end:4] = red
            data[offset + 2:end:4] = green
            data[offset + 3:end:4] = blue
        else:
            # data[offset + 3:end:4] is left un-initialized
            data[offset + 2:end:4] = red
            data[offset + 1:end:4] = green
            data[offset:end:4] = blue

    return cairo.ImageSurface('ARGB32', width, height, data, cairo_stride)


def pixbuf_to_cairo_png(pixbuf):
    """Going through PNG.

    This method is 20~30x slower than GDK but always works.

    """
    buffer_pointer = ffi.new('gchar **')
    buffer_size = ffi.new('gsize *')
    error = ffi.new('GError **')
    pixbuf.save_to_buffer(
        buffer_pointer, buffer_size, ffi.new('char[]', b'png'), error,
        ffi.new('char[]', b'compression'), ffi.new('char[]', b'0'),
        ffi.NULL)
    handle_g_error(error[0], raise_=True)
    png_bytes = ffi.buffer(buffer_pointer[0], buffer_size[0])
    return cairo.ImageSurface.create_from_png(BytesIO(png_bytes))


def cairo_png_loader(file_obj, string):
    """Return a cairo Surface from a PNG byte stream."""
    surface = cairo.ImageSurface.create_from_png(file_obj or BytesIO(string))
    get_pattern = lambda: cairo.SurfacePattern(surface)
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
    if uri.startswith('data:'):
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
