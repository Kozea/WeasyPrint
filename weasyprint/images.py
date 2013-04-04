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
import math

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
from .compat import xrange


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
        self.intrinsic_ratio = (
            self.intrinsic_width / self.intrinsic_height
            if self.intrinsic_height != 0 else float('inf'))

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
            base_url if not base_url.lower().startswith('data:') else None)
        self._svg_data = svg_data

        # TODO: find a way of not doing twice the whole rendering.
        svg = self._render()
        # TODO: support SVG images with none or only one of intrinsic
        #       width, height and ratio.
        if not (svg.width > 0 and svg.height > 0):
            raise ValueError(
                'SVG images without an intrinsic size are not supported.')
        self.intrinsic_width = svg.width
        self.intrinsic_height = svg.height
        self.intrinsic_ratio = self.intrinsic_width / self.intrinsic_height

    def _render(self):
        # Draw to a cairo surface but do not write to a file.
        # This is a CairoSVG surface, not a cairo surface.
        return ScaledSVGSurface(
            cairosvg.parser.Tree(
                bytestring=self._svg_data, url=self._base_url),
            output=None, dpi=96)

    def draw(self, context, concrete_width, concrete_height, _image_rendering):
        # Do not re-use the rendered Surface object,
        # but regenerate it as needed.
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


def percentage(value, refer_to):
    """Return the evaluated percentage value, or the value unchanged."""
    if value is None:
        return value
    elif value.unit == 'px':
        return value.value
    else:
        assert value.unit == '%'
        return refer_to * value.value / 100


def process_color_stops(gradient_line_size, color_stops):
    """
    Gradient line size: distance between the starting point and ending point.
    Color stop: list of (color, positions).
    Position: None, or Dimension in px or %.
              0 is the starting point, 1 the ending point.

    http://dev.w3.org/csswg/css-images-3/#color-stop-syntax

    Return processed color stops, as a list of floats in px.

    """
    positions = [percentage(position, gradient_line_size)
                 for _color, position in color_stops]

    # First and last default to 100%
    if positions[0] is None:
        positions[0] = 0
    if positions[-1] is None:
        positions[-1] = gradient_line_size

    # Make sure positions are increasing.
    previous_pos = positions[0]
    for i, position in enumerate(positions):
        if position is not None:
            if position < previous_pos:
                positions[i] = previous_pos
            else:
                previous_pos = position

    # Assign missing values
    previous_i = -1
    for i, position in enumerate(positions):
        if position is not None:
            base = positions[previous_i]
            increment = (position - base) / (i - previous_i)
            for j in xrange(previous_i + 1, i):
                positions[j] = base + j * increment
            previous_i = i

    # Normalize to [0..1]
    first = positions[0]
    last = positions[-1]
    if last != first:
        diff = last - first
        color_stops = [
            ((pos - first) / diff, r, g, b, a)
            for ((r, g, b, a), _), pos in zip(color_stops, positions)]
    else:
        color_stops = [(0, r, g, b, a) for (r, g, b, a), _ in color_stops]
    return first, last, color_stops


class LinearGradient(object):
    intrinsic_width = None
    intrinsic_height = None
    intrinsic_ratio = None

    def __init__(self, color_stops, direction, repeating):
        # ('corner', keyword) or ('angle', radians)
        self.direction_type, self.direction = direction
        # List of (rgba, dimension)
        self.color_stops = color_stops
        # bool
        self.repeating = repeating

    def layout(self, width, height):
        """Gradient box: (width, height). Top-left is coordinates (0, 0)

        Returns (points, color_stops)
        points: (x0, y0, x1, y1), coordinates of the start and ending points.
        color_stops: list of (offset, red, green, blue, alpha), all in [0..1]
        offset 0 is the starting point, offset 1 the ending point.

        """
        # (dy, dy) is an unit vector pointing to the desired direction.
        # positive dx: right, positive dy: down
        if self.direction_type == 'corner':
            factor_x, factor_y = {
                'top_left': (-1, -1), 'top_right': (1, -1),
                'bottom_left': (-1, 1), 'bottom_right': (1, 1)}[self.direction]
            diagonal = math.sqrt(width ** 2 + height ** 2)
            dx = factor_x * height / diagonal
            dy = factor_y * width / diagonal
        else:
            # 0 upwards, then clockwise
            angle = self.direction
            dx = math.sin(angle)
            dy = -math.cos(angle)

        # Distance between starting and ending point:
        distance = width * dx + height * dy
        first, last, stops = process_color_stops(distance, self.color_stops)
        return (width / 2 + dx * (first - distance / 2),
                height / 2 + dy * (first - distance / 2),
                width / 2 + dx * (last - distance / 2),
                height / 2 + dy * (last - distance / 2)), stops

    def draw(self, context, concrete_width, concrete_height, _image_rendering):
        points, color_stops = self.layout(concrete_width, concrete_height)
        gradient = cairocffi.LinearGradient(*points)
        for color_stop in color_stops:
            gradient.add_color_stop_rgba(*color_stop)
        gradient.set_extend(cairocffi.EXTEND_REPEAT if self.repeating
                            else cairocffi.EXTEND_PAD)
        context.set_source(gradient)
        context.paint()
