"""
    weasyprint.svg
    --------------

    Render SVG images.

"""

import re
from math import cos, hypot, pi, radians, sin, sqrt, tan
from xml.etree import ElementTree

from cssselect2 import ElementWrapper

from .bounding_box import (
    BOUNDING_BOX_METHODS, is_non_empty_bounding_box, is_valid_bounding_box)
from .colors import color
from .css import parse_declarations, parse_stylesheets
from .defs import (
    apply_filters, draw_gradient_or_pattern, paint_mask, parse_def, use)
from .image import image, svg
from .path import path
from .shapes import circle, ellipse, line, polygon, polyline, rect
from .text import text
from .utils import normalize, parse_url, preserve_ratio, size

# TODO: clipPath
TAGS = {
    'a': text,
    'circle': circle,
    'ellipse': ellipse,
    'filter': parse_def,
    'image': image,
    'line': line,
    'linearGradient': parse_def,
    'marker': parse_def,
    'mask': parse_def,
    'path': path,
    'pattern': parse_def,
    'polyline': polyline,
    'polygon': polygon,
    'radialGradient': parse_def,
    'rect': rect,
    'svg': svg,
    'text': text,
    'textPath': text,
    'tspan': text,
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
    def __init__(self, wrapper, style):
        self._wrapper = wrapper
        self._etree_node = etree_node = wrapper.etree_element
        self._style = style

        self.attrib = etree_node.attrib
        self.get = etree_node.get

        self.vertices = []
        self.bounding_box = None

    @property
    def tag(self):
        return self._etree_node.tag.split('}', 1)[-1]

    @property
    def text(self):
        return self._etree_node.text

    @property
    def tail(self):
        return self._etree_node.tail

    def inherit(self, wrapper):
        child = Node(wrapper, self._style)

        for key, value in self.attrib.items():
            if key not in NOT_INHERITED_ATTRIBUTES:
                if key not in child.attrib:
                    child.attrib[key] = value

        style_attr = child.get('style')
        if style_attr:
            normal_attr, important_attr = parse_declarations(style_attr)
        else:
            normal_attr, important_attr = [], []
        normal_matcher, important_matcher = self._style
        normal = [rule[-1] for rule in normal_matcher.match(wrapper)]
        important = [rule[-1] for rule in important_matcher.match(wrapper)]
        declarations_lists = normal, [normal_attr], important, [important_attr]
        for declarations_list in declarations_lists:
            for declarations in declarations_list:
                for name, value in declarations:
                    self.attrib[name] = value.strip()

        for key in COLOR_ATTRIBUTES:
            if child.get(key) == 'currentColor':
                child.attrib[key] = child.get('color', 'black')

        for key, value in child.attrib.items():
            if value == 'inherit':
                child.attrib[key] = self.get(key)

        if child.tag in ('text', 'textPath', 'a'):
            child._wrapper.etree_children, _ = child.text_children(
                wrapper, trailing_space=True, text_root=True)

        return child

    def __iter__(self):
        for wrapper in self._wrapper:
            yield self.inherit(wrapper)

    def get_intrinsic_size(self, font_size):
        intrinsic_width = self.get('width', '100%')
        if '%' in intrinsic_width:
            intrinsic_width = None
        else:
            intrinsic_width = size(intrinsic_width, font_size)

        intrinsic_height = self.get('height', '100%')
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

    @staticmethod
    def handle_white_spaces(string, preserve):
        if not string:
            return ''
        if preserve:
            return re.sub('[\n\r\t]', ' ', string)
        else:
            string = re.sub('[\n\r]', '', string)
            string = re.sub('\t', ' ', string)
            return re.sub(' +', ' ', string)

    def get_child(self, id_):
        for child in self:
            if child.get('id') == id_:
                return child
            grandchild = child.get_child(id_)
            if grandchild:
                return grandchild

    def text_children(self, element, trailing_space, text_root=False):
        children = []
        space = '{http://www.w3.org/XML/1998/namespace}space'
        preserve = self.get(space) == 'preserve'
        self._etree_node.text = self.handle_white_spaces(
            element.etree_element.text, preserve)
        if trailing_space and not preserve:
            self._etree_node.text = self.text.lstrip(' ')

        original_rotate = [
            float(i) for i in
            normalize(self.get('rotate')).strip().split(' ') if i]
        rotate = original_rotate.copy()
        if original_rotate:
            self.pop_rotation(original_rotate, rotate)
        if self.text:
            trailing_space = self.text.endswith(' ')
        for child_element in element.iter_children():
            child = child_element.etree_element
            if child.tag in ('{http://www.w3.org/2000/svg}tref', 'tref'):
                child_node = Node(child_element, self._style)
                child_node._etree_node.tag = 'tspan'
                # Retrieve the referenced node and get its flattened text
                # and remove the node children.
                child = child_node._etree_node
                child._etree_node.text = child.flatten()
                child_element = ElementWrapper.from_xml_root(child)
            else:
                child_node = Node(child_element, self._style)
            child_preserve = child_node.get(space) == 'preserve'
            child_node._etree_node.text = self.handle_white_spaces(
                child.text, child_preserve)
            child_node.children, trailing_space = child_node.text_children(
                child_element, trailing_space)
            trailing_space = child_node.text.endswith(' ')
            if original_rotate and 'rotate' not in child_node:
                child_node.pop_rotation(original_rotate, rotate)
            children.append(child_node)
            if child.tail:
                anonymous_etree = ElementTree.Element(
                    '{http://www.w3.org/2000/svg}tspan')
                anonymous = Node(
                    ElementWrapper.from_xml_root(anonymous_etree), self._style)
                anonymous._etree_node.text = self.handle_white_spaces(
                    child.tail, preserve)
                if original_rotate:
                    anonymous.pop_rotation(original_rotate, rotate)
                if trailing_space and not preserve:
                    anonymous.text = anonymous.text.lstrip(' ')
                if anonymous.text:
                    trailing_space = anonymous.text.endswith(' ')
                children.append(anonymous)

        if text_root and not children and not preserve:
            self._etree_node.text = self.text.rstrip(' ')

        return children, trailing_space

    def flatten(self):
        flattened_text = [self.text or '']
        for child in list(self):
            flattened_text.append(child.flatten())
            flattened_text.append(child.tail or '')
            self.remove(child)
        return ''.join(flattened_text)

    def pop_rotation(self, original_rotate, rotate):
        self.attrib['rotate'] = ' '.join(
            str(rotate.pop(0) if rotate else original_rotate[-1])
            for i in range(len(self.text)))


class SVG:
    def __init__(self, bytestring_svg, url):
        tree = ElementTree.fromstring(bytestring_svg)
        wrapper = ElementWrapper.from_xml_root(tree)
        style = parse_stylesheets(wrapper, url)
        self.tree = Node(wrapper, style)
        self.url = url

        self.filters = {}
        self.gradients = {}
        self.images = {}
        self.markers = {}
        self.masks = {}
        self.patterns = {}
        self.paths = {}

        self.cursor_position = [0, 0]
        self.cursor_d_position = [0, 0]

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

    @staticmethod
    def paint(value):
        if not value or value == 'none':
            return None, None

        value = value.strip()
        match = re.compile(r'(url\(.+\)) *(.*)').search(value)
        if match:
            source = parse_url(match.group(1)).fragment
            color = match.group(2) or None
        else:
            source = None
            color = value or None

        return source, color

    def draw(self, stream, concrete_width, concrete_height, base_url,
             url_fetcher):
        self.stream = stream
        self.concrete_width = concrete_width
        self.concrete_height = concrete_height
        self.normalized_diagonal = (
            hypot(concrete_width, concrete_height) / sqrt(2))
        self.base_url = base_url
        self.url_fetcher = url_fetcher

        self.draw_node(self.tree, size('12pt'))

    def draw_node(self, node, font_size):
        if node.tag == 'defs':
            return

        font_size = size(node.get('font-size', '1em'), font_size, font_size)

        self.stream.push_state()

        filter_ = self.filters.get(parse_url(node.get('filter')).fragment)
        if filter_:
            apply_filters(self, node, filter_, font_size)

        opacity = float(node.get('opacity', 1))
        if 0 <= opacity < 1:
            original_stream = self.stream
            bounding_box = self.calculate_bounding_box(node, font_size)
            self.stream = self.stream.add_transparency_group([
                bounding_box[0], bounding_box[1],
                bounding_box[0] + bounding_box[2],
                bounding_box[1] + bounding_box[3]])

        x, y = self.point(node.get('x'), node.get('y'), font_size)
        self.stream.transform(1, 0, 0, 1, x, y)
        self.transform(node.get('transform'), font_size)

        if node.tag in TAGS:
            TAGS[node.tag](self, node, font_size)

        if node.tag not in DEF_TYPES:
            for child in node:
                self.draw_node(child, font_size)

        mask = self.masks.get(parse_url(node.get('mask')).fragment)
        if mask:
            paint_mask(self, node, mask, opacity)

        self.fill_stroke(node, font_size)

        self.draw_markers(node, font_size)

        if 0 <= opacity < 1:
            group_id = self.stream.id
            self.stream = original_stream
            self.stream.set_alpha(opacity, stroke=None)
            self.stream.draw_x_object(group_id)

        self.stream.pop_state()

    def draw_markers(self, node, font_size):
        if not node.vertices:
            return

        markers = {}
        common_marker = parse_url(node.get('marker')).fragment
        for position in ('start', 'mid', 'end'):
            attribute = f'marker-{position}'
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

            # Draw marker
            marker = markers[position]
            if marker:
                marker_node = self.markers.get(marker)

                # Calculate position, scale and clipping
                if 'viewBox' in node.attrib:
                    marker_width, marker_height = svg.point(
                        marker_node.get('markerWidth', 3),
                        marker_node.get('markerHeight', 3),
                        font_size)
                    scale_x, scale_y, translate_x, translate_y = (
                        preserve_ratio(
                            svg, marker_node, font_size,
                            marker_width, marker_height))

                    clip_x, clip_y, viewbox_width, viewbox_height = (
                        marker_node.get_viewbox())

                    align = marker_node.get(
                        'preserveAspectRatio', 'xMidYMid').split(' ')[0]
                    if align == 'none':
                        x_position = y_position = 'min'
                    else:
                        x_position = align[1:4].lower()
                        y_position = align[5:].lower()

                    if x_position == 'mid':
                        clip_x += (viewbox_width - marker_width / scale_x) / 2
                    elif x_position == 'max':
                        clip_x += viewbox_width - marker_width / scale_x

                    if y_position == 'mid':
                        clip_y += (
                            viewbox_height - marker_height / scale_y) / 2
                    elif y_position == 'max':
                        clip_y += viewbox_height - marker_height / scale_y

                    clip_box = (
                        clip_x, clip_y,
                        marker_width / scale_x, marker_height / scale_y)
                else:
                    marker_width, marker_height = self.point(
                        marker_node.get('markerWidth', 3),
                        marker_node.get('markerHeight', 3),
                        font_size)
                    bounding_box = self.calculate_bounding_box(
                        marker_node, font_size)
                    if is_valid_bounding_box(bounding_box):
                        scale_x = scale_y = min(
                            marker_width / bounding_box[2],
                            marker_height / bounding_box[3])
                    else:
                        scale_x = scale_y = 1
                    translate_x, translate_y = self.point(
                        marker_node.get('refX'), marker_node.get('refY'),
                        font_size)
                    clip_box = None

                # Scale
                if marker_node.get('markerUnits') != 'userSpaceOnUse':
                    scale = self.length(node.get('stroke-width', 1), font_size)
                    scale_x *= scale
                    scale_y *= scale

                # Override angle
                node_angle = marker_node.get('orient', 0)
                if node_angle not in ('auto', 'auto-start-reverse'):
                    angle = radians(float(node_angle))
                elif node_angle == 'auto-start-reverse':
                    if position == 'start':
                        angle += radians(180)

                # Draw marker path
                for child in marker_node:
                    self.stream.push_state()

                    self.stream.transform(
                        scale_x * cos(angle), scale_x * sin(angle),
                        -scale_y * sin(angle), scale_y * cos(angle),
                        *point)
                    self.stream.transform(
                        1, 0, 0, 1, -translate_x, -translate_y)

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
        fill_source, fill_color = self.paint(node.get('fill', 'black'))
        fill_drawn = draw_gradient_or_pattern(
            self, node, fill_source, font_size, stroke=False)
        if fill_color and not fill_drawn:
            fill_color = color(fill_color)[:3]
            self.stream.set_color_rgb(*fill_color)
        fill = fill_color or fill_drawn

        stroke_source, stroke_color = self.paint(node.get('stroke'))
        stroke_drawn = draw_gradient_or_pattern(
            self, node, stroke_source, font_size, stroke=True)
        if stroke_color and not stroke_drawn:
            stroke_color = color(stroke_color)[:3]
            self.stream.set_color_rgb(*stroke_color, stroke=True)
        stroke = stroke_color or stroke_drawn
        stroke_width = self.length(node.get('stroke-width', '1px'), font_size)
        if stroke_width:
            self.stream.set_line_width(stroke_width)

        dash_array = tuple(
            float(value) for value in
            normalize(node.get('stroke-dasharray')).split())
        offset = self.length(node.get('stroke-dashoffset'), font_size)
        if dash_array:
            if not all(value == 0 for value in dash_array):
                if not any(value < 0 for value in dash_array):
                    if offset < 0:
                        sum_dashes = sum(float(value) for value in dash_array)
                        offset = sum_dashes - abs(offset) % sum_dashes
                    self.stream.set_dash(dash_array, offset)

        line_cap = node.get('stroke-linecap', 'butt')
        if line_cap == 'round':
            line_cap = 1
        elif line_cap == 'square':
            line_cap = 2
        else:
            line_cap = 0
        self.stream.set_line_cap(line_cap)

        line_join = node.get('stroke-linejoin', 'miter')
        if line_join == 'round':
            line_join = 1
        elif line_join == 'bevel':
            line_join = 2
        else:
            line_join = 0
        self.stream.set_line_join(line_join)

        miter_limit = float(node.get('stroke-miterlimit', 4))
        if miter_limit < 0:
            miter_limit = 4
        self.stream.set_miter_limit(miter_limit)

        even_odd = node.get('fill-rule') == 'evenodd'
        if fill and stroke:
            self.stream.fill_and_stroke(even_odd)
        elif stroke:
            self.stream.stroke()
        elif fill:
            self.stream.fill(even_odd)

    def transform(self, transform_string, font_size):
        # TODO: merge with Page._gather_links_and_bookmarks and
        # css.validation.properties.transform
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


class Pattern(SVG):
    def __init__(self, tree, url):
        self.tree = tree
        self.url = url

        self.filters = {}
        self.gradients = {}
        self.images = {}
        self.markers = {}
        self.masks = {}
        self.patterns = {}
        self.paths = {}
