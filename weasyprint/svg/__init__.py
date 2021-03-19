"""
    weasyprint.svg
    --------------

    Render SVG images.

"""

import re
from math import cos, pi, radians, sin, tan
from xml.etree import ElementTree

from .bounding_box import (
    BOUNDING_BOX_METHODS, is_non_empty_bounding_box, is_valid_bounding_box)
from .colors import color
from .defs import draw_gradient_or_pattern, linear_gradient, marker, use
from .path import path
from .shapes import circle, ellipse, line, polygon, polyline, rect
from .svg import svg
from .utils import (
    clip_marker_box, normalize, paint, parse_url, preserve_ratio, size)

TAGS = {
    # 'a': None,
    'circle': circle,
    # 'clipPath': None,
    'ellipse': ellipse,
    # 'filter': None,
    # 'image': None,
    'line': line,
    'linearGradient': linear_gradient,
    'marker': marker,
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
    'use': use,
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
        if '}' in etree_node.tag:
            self.tag = etree_node.tag.split('}', 1)[1]
        else:
            self.tag = etree_node.tag
        self.update = etree_node.attrib.update

        self.vertices = []
        self.bounding_box = None

    def inherit(self, child):
        child = Node(child)
        child.update([
            (key, value) for key, value in self.attrib.items()
            if key not in NOT_INHERITED_ATTRIBUTES and
            key not in child.attrib])
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

    def get_intrinsic_size(self, font_size):
        intrinsic_width = self.get('width', '100%')
        intrinsic_height = self.get('height', '100%')

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
        viewbox = self.get('viewBox')
        if viewbox:
            return tuple(
                float(number) for number in normalize(viewbox).split())

    def get_href(self):
        return self.get('{http://www.w3.org/1999/xlink}href', self.get('href'))

    def get_child(self, id_):
        for child in self:
            if child.get('id') == id_:
                return child
            grandchild = child.get_child(id_)
            if grandchild:
                return grandchild


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

        self.parse_all_defs(self.tree)

    def get_intrinsic_size(self, font_size):
        return self.tree.get_intrinsic_size(font_size)

    def get_viewbox(self):
        return self.tree.get_viewbox()

    def point(self, x, y, font_size):
        return (
            size(x, font_size, self.concrete_width),
            size(y, font_size, self.concrete_height))

    def length(self, length, font_size):
        return size(length, font_size, self.normalized_diagonal)

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
        if node.tag == 'defs':
            return

        font_size = size(node.get('font-size', '1em'), font_size, font_size)

        self.stream.push_state()

        x, y = self.point(node.get('x'), node.get('y'), font_size)
        self.stream.transform(1, 0, 0, 1, x, y)
        self.transform(node.get('transform'), font_size)

        if node.tag in TAGS:
            TAGS[node.tag](self, node, font_size)

        for child in node:
            self.draw_node(child, font_size)

        self.fill_stroke(node, font_size)

        self.draw_markers(node, font_size)

        self.stream.pop_state()

    def draw_markers(self, node, font_size):
        if not node.vertices:
            return

        markers = {}
        common_marker = parse_url(node.get('marker')).fragment
        for position in ('start', 'mid', 'end'):
            attribute = 'marker-{}'.format(position)
            if attribute in node.attrib:
                markers[position] = parse_url(node.attrib[attribute]).fragment
            else:
                markers[position] = common_marker

        angle1, angle2 = None, None
        position = 'start'

        while node.vertices:
            # Calculate position and angle
            point = node.vertices.pop(0)
            angles = node.vertices.pop(0) if node.vertices else None
            if angles:
                if position == 'start':
                    angle = pi - angles[0]
                else:
                    angle = (angle2 + pi - angles[0]) / 2
                angle1, angle2 = angles
            else:
                angle = angle2
                position = 'end'

            # Draw marker (if a marker exists for 'position')
            marker = markers[position]
            if marker:
                marker_node = self.markers.get(marker)

                # Calculate scale based on current stroke (if requested)
                if marker_node.get('markerUnits') == 'userSpaceOnUse':
                    scale = 1
                else:
                    scale = self.length(node.get('stroke-width', 1), font_size)

                # Calculate position, (additional) scale and clipping based on
                # marker properties
                if 'viewBox' in node.attrib:
                    scale_x, scale_y, translate_x, translate_y = (
                        preserve_ratio(svg, marker_node, font_size))
                    clip_box = clip_marker_box(
                        svg, marker_node, font_size, scale_x, scale_y)
                else:
                    # Calculate sizes
                    marker_width, marker_height = self.point(
                        marker_node.get('markerWidth', 3),
                        marker_node.get('markerHeight', 3),
                        font_size)
                    bounding_box = self.calculate_bounding_box(
                        marker_node, font_size)

                    # Calculate position and scale (preserve aspect ratio)
                    translate_x, translate_y = self.point(
                        marker_node.get('refX', '0'),
                        marker_node.get('refY', '0'),
                        font_size)
                    if is_valid_bounding_box(bounding_box):
                        scale_x = scale_y = min(
                            marker_width / bounding_box[2],
                            marker_height / bounding_box[3])
                    else:
                        scale_x = scale_y = 1

                    # No clipping since viewbox is not present
                    clip_box = None

                # Override angle (if requested)
                node_angle = marker_node.get('orient', '0')
                if node_angle not in ('auto', 'auto-start-reverse'):
                    angle = radians(float(node_angle))
                elif node_angle == 'auto-start-reverse':
                    if position == 'start':
                        angle += radians(180)

                # Draw marker path
                # See http://www.w3.org/TR/SVG/painting.html#MarkerAlgorithm
                for child in marker_node:
                    self.stream.push_state()
                    self.stream.transform(
                        scale * scale_x * cos(angle),
                        scale * scale_x * sin(angle),
                        -scale * scale_y * sin(angle),
                        scale * scale_y * cos(angle),
                        *point)
                    self.stream.transform(
                        1, 0, 0, 1, -translate_x, -translate_y)

                    # Add clipping (if present and requested)
                    overflow = marker_node.get('overflow', 'hidden')
                    if clip_box and overflow in ('hidden', 'scroll'):
                        self.stream.push_state()
                        self.stream.rectangle(*clip_box)
                        self.stream.pop_state()
                        self.stream.clip()

                    self.draw_node(child, font_size)
                    self.stream.pop_state()

            position = 'mid' if angles else 'start'

    def fill_stroke(self, node, font_size):
        fill_source, fill_color = paint(node.get('fill', 'black'))
        fill_drawn = draw_gradient_or_pattern(
            self, node, fill_source, font_size, stroke=False)
        if fill_color and not fill_drawn:
            fill_color = color(fill_color)[:3]
            self.stream.set_color_rgb(*fill_color)
        fill = fill_color or fill_drawn

        stroke_source, stroke_color = paint(node.get('stroke'))
        stroke_drawn = draw_gradient_or_pattern(
            self, node, stroke_source, font_size, stroke=True)
        if stroke_color and not stroke_drawn:
            stroke_color = color(stroke_color)[:3]
            self.stream.set_color_rgb(*stroke_color, stroke=True)
        stroke = stroke_color or stroke_drawn
        stroke_width = node.get('stroke-width', '1px')
        if stroke_width:
            line_width = self.length(stroke_width, font_size)
            if line_width > 0:
                self.stream.set_line_width(line_width)

        dash_array = tuple(
            float(value) for value in
            normalize(node.get('stroke-dasharray')).split())
        offset = self.length(node.get('stroke-dashoffset'), font_size)
        line_cap = node.get('stroke-linecap', 'butt')
        line_join = node.get('stroke-linejoin', 'miter')
        miter_limit = float(node.get('stroke-miterlimit', 4))
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

        even_odd = node.get('fill-rule') == 'evenodd'
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
                self.length(value, font_size)
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

    def calculate_bounding_box(self, node, font_size):
        if node.bounding_box is None and node.tag in BOUNDING_BOX_METHODS:
            bounding_box = BOUNDING_BOX_METHODS[node.tag](
                self, node, font_size)
            if is_non_empty_bounding_box(bounding_box):
                node.bounding_box = bounding_box
        return node.bounding_box
