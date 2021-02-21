"""
    weasyprint.svg
    --------------

    Render SVG images.

"""

from xml.etree import ElementTree

from .colors import color
from .shapes import circle, ellipse, rect
from .svg import svg
from .utils import normalize, size


TAGS = {
    'circle': circle,
    'ellipse': ellipse,
    'rect': rect,
    'svg': svg,
}


class SVG:
    def __init__(self, bytestring_svg):
        self.tree = ElementTree.fromstring(bytestring_svg)

    def get_intrinsic_size(self, font_size):
        intrinsic_width = self.tree.get('width', '100%')
        intrinsic_height = self.tree.get('height', '100%')

        if '%' in intrinsic_width:
            intrinsic_width = None
        else:
            intrinsic_width = size(intrinsic_width, font_size)
        if '%' in intrinsic_height:
            intrinsic_height = None
        else:
            intrinsic_height = size(intrinsic_height, font_size)

        return intrinsic_width, intrinsic_height

    def get_viewbox(self):
        viewbox = self.tree.get('viewBox')
        if viewbox:
            return tuple(
                float(number) for number in normalize(viewbox).split())

    def draw(self, stream, concrete_width, concrete_height, base_url,
             url_fetcher):
        self.stream = stream
        self.concrete_width = concrete_width
        self.concrete_height = concrete_height
        self.normalized_diagonal = (
            ((concrete_width ** 2 + concrete_height ** 2) ** 0.5) / (2 ** 0.5))
        self.base_url = base_url
        self.url_fetcher = url_fetcher

        self.draw_node(self.tree, size('12pt'))

    def draw_node(self, node, font_size):
        font_size = size(node.get('font-size', '1em'), font_size, font_size)

        self.stream.push_state()

        x = size(node.get('x', 0), font_size, self.concrete_width)
        y = size(node.get('y', 0), font_size, self.concrete_height)
        self.stream.transform(1, 0, 0, 1, x, y)

        local_name = node.tag.split('}', 1)[1]

        if local_name in TAGS:
            TAGS[local_name](self, node, font_size)

        for child in node:
            self.draw_node(child, font_size)

        self.fill_stroke(node, font_size)

        self.stream.pop_state()

    def fill_stroke(self, node, font_size):
        fill = node.get('fill', 'black')
        fill_rule = node.get('fill-rule')

        if fill == 'none':
            fill = None
        if fill and fill != 'none':
            fill_color = color(fill)[0:-1]
            self.stream.set_color_rgb(*fill_color)

        stroke = node.get('stroke')
        stroke_width = node.get('stroke-width', '1px')
        dash_array = tuple(
            float(value) for value in
            normalize(node.get('stroke-dasharray', '')).split())
        offset = size(node.get('stroke-dashoffset', 0))
        line_cap = node.get('stroke-linecap', 'butt')
        line_join = node.get('stroke-linejoin', 'miter')
        miter_limit = float(node.get('stroke-miterlimit', 4))

        if stroke:
            stroke_color = color(stroke)[:3]
            self.stream.set_color_rgb(*stroke_color, stroke=True)
        if stroke_width:
            line_width = size(stroke_width, font_size)
            if line_width > 0:
                self.stream.set_line_width(line_width)
        if dash_array:
            if (not all(value == 0 for value in dash_array) and
                    not any(value < 0 for value in dash_array)):
                if offset < 0:
                    sum_dashes = sum(float(value) for value in dash_array)
                    offset = sum_dashes - abs(offset) % sum_dashes
                self.stream.set_dash(dash_array, offset)
        if line_cap in ('round', 'square'):
            line_cap = 1 if line_cap == 'round' else 2
        else:
            line_cap = 0
        if line_join in ('miter-clip', 'arc', 'miter'):
            line_join = 0
        elif line_join == 'round':
            line_join = 1
        elif line_join == 'bevel':
            line_join = 2
        if miter_limit < 0:
            miter_limit = 4
        self.stream.set_line_cap(line_cap)
        self.stream.set_line_join(line_join)
        self.stream.set_miter_limit(miter_limit)

        even_odd = fill_rule == 'evenodd'
        if fill and stroke:
            self.stream.fill_and_stroke(even_odd)
        elif stroke:
            self.stream.stroke()
        elif fill:
            self.stream.fill(even_odd)
