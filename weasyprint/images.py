# coding: utf8
"""
    weasyprint.images
    -----------------

    Fetch and decode images in various formats.

    :copyright: Copyright 2011-2013 Simon Sapin and contributors, see AUTHORS.
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


# Map values of the image-rendering property to cairo FILTER values:
# Values are normalized to lower case.
IMAGE_RENDERING_TO_FILTER = dict(
    optimizespeed=cairocffi.FILTER_FAST,
    auto=cairocffi.FILTER_GOOD,
    optimizequality=cairocffi.FILTER_BEST,
)


class RasterImage(object):
    def __init__(self, image_surface):
        self.image_surface = image_surface
        self.intrinsic_width = image_surface.get_width()
        self.intrinsic_height = image_surface.get_height()
        self.intrinsic_ratio = self.intrinsic_width / self.intrinsic_height

    def draw(self, context, concrete_width, concrete_height, image_rendering):
        if self.intrinsic_width > 0 and self.intrinsic_height > 0:
            context.scale(concrete_width / self.intrinsic_width,
                          concrete_height / self.intrinsic_height)
            context.set_source_surface(self.image_surface)
            context.get_source().set_filter(
                IMAGE_RENDERING_TO_FILTER[image_rendering])
            context.paint()


class ScaledSVGSurface(cairosvg.surface.SVGSurface):
    """
    Have the cairo Surface object have intrinsic dimension
    in pixels instead of points.
    """
    @property
    def device_units_per_user_units(self):
        scale = super(ScaledSVGSurface, self).device_units_per_user_units
        return scale / 0.75


class SVGImage(object):
    def __init__(self, svg_data, base_url):
        # Don’t pass data URIs to CairoSVG.
        # They are useless for relative URIs anyway.
        self._base_url = (
            base_url if not base_url.lower().startswith('data:')  else None)
        self._svg_data = svg_data

        # TODO: find a way of not doing twice the whole rendering.
        svg = self._render()
        # TODO: support SVG images with none or only one of intrinsic
        #       width, height and ratio.
        if not (svg.width > 0 and svg.height > 0):
            raise ValueError(
                'SVG Images without an intrinsic size are not supported.')
        self.intrinsic_width = svg.width
        self.intrinsic_height = svg.height
        self.intrinsic_ratio = self.intrinsic_width / self.intrinsic_height

    def _render(self):
        # Draw to a cairo surface but do not write to a file.
        # This is a CairoSVG surface, not a cairo surface.
        return ScaledSVGSurface(
            cairosvg.parser.Tree(bytestring=self._svg_data, url=self._base_url),
            output=None, dpi=96)

    def draw(self, context, concrete_width, concrete_height, image_rendering):
        # Do not re-use the rendered Surface object, but regenerate it as needed.
        # If a surface for a SVG image is still alive by the time we call
        # show_page(), cairo will rasterize the image instead writing vectors.
        svg = self._render()
        context.scale(concrete_width / svg.width, concrete_height / svg.height)
        context.set_source_surface(svg.cairo)
        context.paint()


def get_image_from_uri(cache, url_fetcher, uri, forced_mime_type=None):
    """Get a cairo Pattern from an image URI."""
    try:
        missing = object()
        image = cache.get(uri, missing)
        if image is not missing:
            return image
        result = url_fetcher(uri)
        mime_type = forced_mime_type or result['mime_type']
        try:
            if mime_type == 'image/svg+xml':
                image = SVGImage(
                    result.get('string') or result['file_obj'].read(), uri)
            elif mime_type == 'image/png':
                image = RasterImage(cairocffi.ImageSurface.create_from_png(
                    result.get('file_obj') or BytesIO(result.get('string'))))
            else:
                if pixbuf is None:
                    raise OSError(
                        'Could not load GDK-Pixbuf. '
                        'PNG and SVG are the only image formats available.')
                string = result.get('string') or result['file_obj'].read()
                surface, format_name = pixbuf.decode_to_image_surface(string)
                if format_name == 'jpeg':
                    surface.set_mime_data('image/jpeg', string)
                image = RasterImage(surface)
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
