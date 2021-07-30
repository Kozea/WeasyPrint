"""
    weasyprint.svg.utils
    --------------------

    Util functions for SVG rendering.

"""

import re
from math import cos, radians, sin, tan
from urllib.parse import urlparse

from tinycss2.color3 import parse_color


class PointError(Exception):
    """Exception raised when parsing a point fails."""


def normalize(string):
    """Give a canonical version of a given value string."""
    string = (string or '').replace('E', 'e')
    string = re.sub('(?<!e)-', ' -', string)
    string = re.sub('[ \n\r\t,]+', ' ', string)
    string = re.sub(r'(\.[0-9-]+)(?=\.)', r'\1 ', string)
    return string.strip()


def size(string, font_size=None, percentage_reference=None):
    """Compute size from string, resolving units and percentages."""
    from ..css.utils import LENGTHS_TO_PIXELS

    if not string:
        return 0

    try:
        return float(string)
    except ValueError:
        # Not a float, try something else
        pass

    string = normalize(string).split(' ', 1)[0]
    if string.endswith('%'):
        assert percentage_reference is not None
        return float(string[:-1]) * percentage_reference / 100
    elif string.endswith('em'):
        assert font_size is not None
        return font_size * float(string[:-2])
    elif string.endswith('ex'):
        # Assume that 1em == 2ex
        assert font_size is not None
        return font_size * float(string[:-2]) / 2

    for unit, coefficient in LENGTHS_TO_PIXELS.items():
        if string.endswith(unit):
            return float(string[:-len(unit)]) * coefficient

    # Unknown size
    return 0


def point(svg, string, font_size):
    """Pop first two size values from a string."""
    match = re.match('(.*?) (.*?)(?: |$)', string)
    if match:
        x, y = match.group(1, 2)
        string = string[match.end():]
        return (*svg.point(x, y, font_size), string)
    else:
        raise PointError


def preserve_ratio(svg, node, font_size, width, height, viewbox=None):
    """Compute scale and translation needed to preserve ratio."""
    viewbox = viewbox or node.get_viewbox()
    if viewbox:
        viewbox_width, viewbox_height = viewbox[2:]
    else:
        return 1, 1, 0, 0

    scale_x = width / viewbox_width if viewbox_width else 1
    scale_y = height / viewbox_height if viewbox_height else 1

    aspect_ratio = node.get('preserveAspectRatio', 'xMidYMid').split()
    align = aspect_ratio[0]
    if align == 'none':
        x_position = 'min'
        y_position = 'min'
    else:
        meet_or_slice = aspect_ratio[1] if len(aspect_ratio) > 1 else None
        if meet_or_slice == 'slice':
            scale_value = max(scale_x, scale_y)
        else:
            scale_value = min(scale_x, scale_y)
        scale_x = scale_y = scale_value
        x_position = align[1:4].lower()
        y_position = align[5:].lower()

    if node.tag == 'marker':
        translate_x, translate_y = svg.point(
            node.get('refX'), node.get('refY', '0'), font_size)
    else:
        translate_x = 0
        if x_position == 'mid':
            translate_x = (width - viewbox_width * scale_x) / 2
        elif x_position == 'max':
            translate_x = width - viewbox_width * scale_x

        translate_y = 0
        if y_position == 'mid':
            translate_y += (height - viewbox_height * scale_y) / 2
        elif y_position == 'max':
            translate_y += height - viewbox_height * scale_y

    translate_x -= viewbox[0] * scale_x
    translate_y -= viewbox[1] * scale_y

    return scale_x, scale_y, translate_x, translate_y


def parse_url(url):
    """Parse a URL, possibly in a "url(…)" string."""
    if url and url.startswith('url(') and url.endswith(')'):
        url = url[4:-1]
    return urlparse(url or '')


def color(string):
    """Safely parse a color string and return a RGBA tuple."""
    return parse_color(string or '') or (0, 0, 0, 1)


def transform(transform_string, font_size, normalized_diagonal):
    """Get a matrix corresponding to the transform string."""
    # TODO: merge with Page._gather_links_and_bookmarks and
    # css.validation.properties.transform
    from ..document import Matrix

    transformations = re.findall(
        r'(\w+) ?\( ?(.*?) ?\)', normalize(transform_string))
    matrix = Matrix()

    for transformation_type, transformation in transformations:
        values = [
            size(value, font_size, normalized_diagonal)
            for value in transformation.split(' ')]
        if transformation_type == 'matrix':
            matrix = Matrix(*values) @ matrix
        elif transformation_type == 'rotate':
            matrix = Matrix(
                cos(radians(float(values[0]))),
                sin(radians(float(values[0]))),
                -sin(radians(float(values[0]))),
                cos(radians(float(values[0])))) @ matrix
        elif transformation_type.startswith('skew'):
            if len(values) == 1:
                values.append(0)
            if transformation_type in ('skewX', 'skew'):
                matrix = Matrix(
                    c=tan(radians(float(values.pop(0))))) @ matrix
            if transformation_type in ('skewY', 'skew'):
                matrix = Matrix(
                    b=tan(radians(float(values.pop(0))))) @ matrix
        elif transformation_type.startswith('translate'):
            if len(values) == 1:
                values.append(0)
            if transformation_type in ('translateX', 'translate'):
                matrix = Matrix(e=values.pop(0)) @ matrix
            if transformation_type in ('translateY', 'translate'):
                matrix = Matrix(f=values.pop(0)) @ matrix
        elif transformation_type.startswith('scale'):
            if len(values) == 1:
                values.append(values[0])
            if transformation_type in ('scaleX', 'scale'):
                matrix = Matrix(a=values.pop(0)) @ matrix
            if transformation_type in ('scaleY', 'scale'):
                matrix = Matrix(d=values.pop(0)) @ matrix

    return matrix
