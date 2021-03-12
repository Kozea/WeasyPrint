"""
    weasyprint.svg
    --------------

    Render SVG images.

"""

import re
from math import cos, radians, sin, tan
from xml.etree import ElementTree

from .colors import color
from .path import path
from .shapes import circle, ellipse, line, polygon, polyline, rect
from .svg import svg
from .utils import normalize, size

TAGS = {
    # 'a': None,
    'circle': circle,
    # 'clipPath': None,
    'ellipse': ellipse,
    # 'filter': None,
    # 'image': None,
    'line': line,
    # 'linearGradient': None,
    # 'marker': None,
    # 'mask': None,
    'path': path,
    # 'pattern': None,
    'polyline': polyline,
    'polygon': polygon,
    # 'radialGradient': None,
    'rect': rect,
    'svg': svg,
    # 'text': None,
    # 'textPath': None,
    # 'tspan': None,
    # 'use': None,
}

NOT_INHERITED_ATTRIBUTES = frozenset((
    'clip',
    'clip-path',
    'filter',
    'height',
    'id',
    'mask',
    'opacity',
    'overflow',
    'rotate',
    'stop-color',
    'stop-opacity',
    'style',
    'transform',
    'transform-origin',
    'viewBox',
    'width',
    'x',
    'y',
    'dx',
    'dy',
    '{http://www.w3.org/1999/xlink}href',
    'href',
))

COLOR_ATTRIBUTES = frozenset((
    'fill',
    'flood-color',
    'lighting-color',
    'stop-color',
    'stroke',
))

DEF_TYPES = frozenset((
    'marker',
    'gradient',
    'pattern',
    'path',
    'mask',
    'filter',
    'image',
))


class Node:
    def __init__(self, etree_node):
        self._etree_node = etree_node

        self.attrib = etree_node.attrib
        self.get = etree_node.get
        self.set = etree_node.set
        self.tag = etree_node.tag
        self.update = etree_node.attrib.update

        self.vertices = []

    def inherit(self, child):
        child = Node(child)
        child.update([
            (key, value) for key, value in self.attrib.items()
            if key not in NOT_INHERITED_ATTRIBUTES])
        for key in COLOR_ATTRIBUTES:
            if child.get(key) == 'currentColor':
                child.set(key, child.get('color', 'black'))
        for key, value in child.attrib.items():
            if value == 'inherit':
                child.set(key, self.get(key))
        return child

    def __iter__(self):
        for child in self._etree_node:
            yield self.inherit(child)


class SVG:
    def __init__(self, bytestring_svg, url):
        self.tree = Node(ElementTree.fromstring(bytestring_svg))
        self.url = url

        self.filters = {}
        self.gradients = {}
        self.images = {}
        self.markers = {}
        self.masks = {}
        self.patterns = {}
        self.paths = {}

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

        self.parse_all_defs(self.tree)
        self.draw_node(self.tree, size('12pt'))

    def draw_node(self, node, font_size):
        if node.tag == 'defs':
            return

        font_size = size(node.get('font-size', '1em'), font_size, font_size)

        self.stream.push_state()

        x = size(node.get('x', 0), font_size, self.concrete_width)
        y = size(node.get('y', 0), font_size, self.concrete_height)
        self.stream.transform(1, 0, 0, 1, x, y)
        self.transform(node.get('transform'), font_size)

        if '}' in node.tag:
            local_name = node.tag.split('}', 1)[1]
        else:
            local_name = node.tag

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

    def transform(self, transform_string, font_size):
        from ..document import Matrix

        if not transform_string:
            return

        transformations = re.findall(
            r'(\w+) ?\( ?(.*?) ?\)', normalize(transform_string))
        matrix = Matrix()

        for transformation_type, transformation in transformations:
            values = [
                size(value, font_size, self.normalized_diagonal)
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

        if matrix.determinant:
            self.stream.transform(
                matrix[0][0], matrix[0][1],
                matrix[1][0], matrix[1][1],
                matrix[2][0], matrix[2][1])

    def parse_all_defs(self, node):
        self.parse_def(node)
        for child in node:
            self.parse_all_defs(child)

    def parse_def(self, node):
        for def_type in DEF_TYPES:
            if def_type in node.tag.lower() and 'id' in node.attrib:
                getattr(self, f'{def_type}s')[node.attrib['id']] = node
