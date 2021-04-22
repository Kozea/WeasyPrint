"""
    weasyprint.svg
    --------------

    Render SVG images.

"""

import re
from math import cos, hypot, pi, radians, sin, sqrt
from xml.etree import ElementTree

from cssselect2 import ElementWrapper

from .bounding_box import BOUNDING_BOX_METHODS, is_valid_bounding_box
from .css import parse_declarations, parse_stylesheets
from .defs import apply_filters, draw_gradient_or_pattern, paint_mask, use
from .images import image, svg
from .path import path
from .shapes import circle, ellipse, line, polygon, polyline, rect
from .text import text
from .utils import color, normalize, parse_url, preserve_ratio, size, transform

# TODO: clipPath
TAGS = {
    'a': text,
    'circle': circle,
    'ellipse': ellipse,
    'image': image,
    'line': line,
    'path': path,
    'polyline': polyline,
    'polygon': polygon,
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
    """An SVG document node."""

    def __init__(self, wrapper, style):
        self._wrapper = wrapper
        self._etree_node = wrapper.etree_element
        self._style = style

        self.attrib = wrapper.etree_element.attrib
        self.get = wrapper.etree_element.get

        self.vertices = []
        self.bounding_box = None

    @property
    def tag(self):
        """XML tag name with no namespace."""
        return self._etree_node.tag.split('}', 1)[-1]

    @property
    def text(self):
        """XML node text."""
        return self._etree_node.text

    @property
    def tail(self):
        """Text after the XML node."""
        return self._etree_node.tail

    def __iter__(self):
        """Yield node children, handling cascade."""
        for wrapper in self._wrapper:
            child = Node(wrapper, self._style)

            # Cascade
            for key, value in self.attrib.items():
                if key not in NOT_INHERITED_ATTRIBUTES:
                    if key not in child.attrib:
                        child.attrib[key] = value

            # Apply style attribute
            style_attr = child.get('style')
            if style_attr:
                normal_attr, important_attr = parse_declarations(style_attr)
            else:
                normal_attr, important_attr = [], []
            normal_matcher, important_matcher = self._style
            normal = [rule[-1] for rule in normal_matcher.match(wrapper)]
            important = [rule[-1] for rule in important_matcher.match(wrapper)]
            declarations_lists = (
                normal, [normal_attr], important, [important_attr])
            for declarations_list in declarations_lists:
                for declarations in declarations_list:
                    for name, value in declarations:
                        self.attrib[name] = value.strip()

            # Replace 'currentColor' value
            for key in COLOR_ATTRIBUTES:
                if child.get(key) == 'currentColor':
                    child.attrib[key] = child.get('color', 'black')

            # Handle 'inherit' values
            for key, value in child.attrib.items():
                if value == 'inherit':
                    child.attrib[key] = self.get(key)

            # Fix text in text tags
            if child.tag in ('text', 'textPath', 'a'):
                child._wrapper.etree_children, _ = child.text_children(
                    wrapper, trailing_space=True, text_root=True)

            yield child

    def get_viewbox(self):
        """Get node viewBox as a tuple of floats."""
        viewbox = self.get('viewBox')
        if viewbox:
            return tuple(
                float(number) for number in normalize(viewbox).split())

    def get_href(self):
        """Get the href attribute, with or without a namespace."""
        return self.get('{http://www.w3.org/1999/xlink}href', self.get('href'))

    @staticmethod
    def process_whitespace(string, preserve):
        """Replace newlines by spaces, and merge spaces if not preserved."""
        # TODO: should be merged with build.process_whitespace
        if not string:
            return ''
        if preserve:
            return re.sub('[\n\r\t]', ' ', string)
        else:
            string = re.sub('[\n\r]', '', string)
            string = re.sub('\t', ' ', string)
            return re.sub(' +', ' ', string)

    def get_child(self, id_):
        """Get a child with given id in the whole child tree."""
        for child in self:
            if child.get('id') == id_:
                return child
            grandchild = child.get_child(id_)
            if grandchild:
                return grandchild

    def text_children(self, element, trailing_space, text_root=False):
        """Handle text node by fixing whitespaces and flattening tails."""
        children = []
        space = '{http://www.w3.org/XML/1998/namespace}space'
        preserve = self.get(space) == 'preserve'
        self._etree_node.text = self.process_whitespace(
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
            child_node._etree_node.text = self.process_whitespace(
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
                anonymous._etree_node.text = self.process_whitespace(
                    child.tail, preserve)
                if original_rotate:
                    anonymous.pop_rotation(original_rotate, rotate)
                if trailing_space and not preserve:
                    anonymous._etree_node.text = anonymous.text.lstrip(' ')
                if anonymous.text:
                    trailing_space = anonymous.text.endswith(' ')
                children.append(anonymous)

        if text_root and not children and not preserve:
            self._etree_node.text = self.text.rstrip(' ')

        return children, trailing_space

    def flatten(self):
        """Flatten text in node and in its children."""
        flattened_text = [self.text or '']
        for child in list(self):
            flattened_text.append(child.flatten())
            flattened_text.append(child.tail or '')
            self.remove(child)
        return ''.join(flattened_text)

    def pop_rotation(self, original_rotate, rotate):
        """Merge nested letter rotations."""
        self.attrib['rotate'] = ' '.join(
            str(rotate.pop(0) if rotate else original_rotate[-1])
            for i in range(len(self.text)))


class SVG:
    """An SVG document."""

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
        self.text_path_width = 0

        self.parse_defs(self.tree)

    def get_intrinsic_size(self, font_size):
        """Get intrinsic size of the image."""
        intrinsic_width = self.tree.get('width', '100%')
        if '%' in intrinsic_width:
            intrinsic_width = None
        else:
            intrinsic_width = size(intrinsic_width, font_size)

        intrinsic_height = self.tree.get('height', '100%')
        if '%' in intrinsic_height:
            intrinsic_height = None
        else:
            intrinsic_height = size(intrinsic_height, font_size)

        return intrinsic_width, intrinsic_height

    def get_viewbox(self):
        """Get document viewBox as a tuple of floats."""
        return self.tree.get_viewbox()

    def point(self, x, y, font_size):
        """Compute size of an x/y or width/height couple."""
        return (
            size(x, font_size, self.concrete_width),
            size(y, font_size, self.concrete_height))

    def length(self, length, font_size):
        """Compute size of an arbirtary attribute."""
        return size(length, font_size, self.normalized_diagonal)

    def draw(self, stream, concrete_width, concrete_height, base_url,
             url_fetcher, context):
        """Draw image on a stream."""
        self.stream = stream
        self.concrete_width = concrete_width
        self.concrete_height = concrete_height
        self.normalized_diagonal = (
            hypot(concrete_width, concrete_height) / sqrt(2))
        self.base_url = base_url
        self.url_fetcher = url_fetcher
        self.context = context

        self.draw_node(self.tree, size('12pt'))

    def draw_node(self, node, font_size):
        """Draw a node."""
        if node.tag == 'defs':
            return

        # Update font size
        font_size = size(node.get('font-size', '1em'), font_size, font_size)

        self.stream.push_state()

        # Apply filters
        filter_ = self.filters.get(parse_url(node.get('filter')).fragment)
        if filter_:
            apply_filters(self, node, filter_, font_size)

        # Create substream for opacity
        opacity = float(node.get('opacity', 1))
        if 0 <= opacity < 1:
            original_stream = self.stream
            bounding_box = self.calculate_bounding_box(node, font_size)
            if is_valid_bounding_box(bounding_box):
                self.stream = self.stream.add_transparency_group([
                    bounding_box[0], bounding_box[1],
                    bounding_box[0] + bounding_box[2],
                    bounding_box[1] + bounding_box[3]])
            else:
                opacity = 1

        # Apply transformations
        x, y = self.point(node.get('x'), node.get('y'), font_size)
        self.stream.transform(1, 0, 0, 1, x, y)
        self.transform(node.get('transform'), font_size)

        # Draw node
        if node.tag in TAGS:
            TAGS[node.tag](self, node, font_size)

        # Draw node children
        if node.tag not in DEF_TYPES:
            for child in node:
                self.draw_node(child, font_size)

        # Apply mask
        mask = self.masks.get(parse_url(node.get('mask')).fragment)
        if mask:
            paint_mask(self, node, mask, opacity)

        # Fill and stroke
        self.fill_stroke(node, font_size)

        # Draw markers
        self.draw_markers(node, font_size)

        # Apply opacity stream and restore original stream
        if 0 <= opacity < 1:
            group_id = self.stream.id
            self.stream = original_stream
            self.stream.set_alpha(opacity, stroke=None)
            self.stream.draw_x_object(group_id)

        # Clean text tag
        if node.tag == 'text':
            self.cursor_position = [0, 0]
            self.cursor_d_position = [0, 0]
            self.text_path_width = 0

        self.stream.pop_state()

    def draw_markers(self, node, font_size):
        """Draw markers defined in a node."""
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
            if not marker:
                position = 'mid' if angles else 'start'
                continue

            marker_node = self.markers.get(marker)

            # Calculate position, scale and clipping
            if 'viewBox' in node.attrib:
                marker_width, marker_height = svg.point(
                    marker_node.get('markerWidth', 3),
                    marker_node.get('markerHeight', 3),
                    font_size)
                scale_x, scale_y, translate_x, translate_y = preserve_ratio(
                    svg, marker_node, font_size, marker_width, marker_height)

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
            elif node_angle == 'auto-start-reverse' and position == 'start':
                angle += radians(180)

            # Draw marker path
            for child in marker_node:
                self.stream.push_state()

                self.stream.transform(
                    scale_x * cos(angle), scale_x * sin(angle),
                    -scale_y * sin(angle), scale_y * cos(angle),
                    *point)
                self.stream.transform(1, 0, 0, 1, -translate_x, -translate_y)

                overflow = marker_node.get('overflow', 'hidden')
                if clip_box and overflow in ('hidden', 'scroll'):
                    self.stream.push_state()
                    self.stream.rectangle(*clip_box)
                    self.stream.pop_state()
                    self.stream.clip()

                self.draw_node(child, font_size)
                self.stream.pop_state()

        position = 'mid' if angles else 'start'

    @staticmethod
    def paint(value):
        """Paint fill or stroke attribute with a color or a URL."""
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

    def fill_stroke(self, node, font_size, text=False):
        """Paint fill and stroke for a node."""
        if node.tag in ('text', 'textPath', 'a') and not text:
            return

        # Get fill data
        fill_source, fill_color = self.paint(node.get('fill', 'black'))
        fill_drawn = draw_gradient_or_pattern(
            self, node, fill_source, font_size, stroke=False)
        if fill_color and not fill_drawn:
            red, green, blue, alpha = color(fill_color)
            self.stream.set_color_rgb(red, green, blue)
            self.stream.set_alpha(alpha)
        fill = fill_color or fill_drawn

        # Get stroke data
        stroke_source, stroke_color = self.paint(node.get('stroke'))
        stroke_drawn = draw_gradient_or_pattern(
            self, node, stroke_source, font_size, stroke=True)
        if stroke_color and not stroke_drawn:
            red, green, blue, alpha = color(stroke_color)
            self.stream.set_color_rgb(red, green, blue, stroke=True)
            self.stream.set_alpha(alpha, stroke=True)
        stroke = stroke_color or stroke_drawn
        stroke_width = self.length(node.get('stroke-width', '1px'), font_size)
        if stroke_width:
            self.stream.set_line_width(stroke_width)

        # Apply dash array
        dash_array = tuple(
            float(value) for value in
            normalize(node.get('stroke-dasharray')).split())
        dash_condition = (
            dash_array and
            not all(value == 0 for value in dash_array) and
            not any(value < 0 for value in dash_array))
        if dash_condition:
            offset = self.length(node.get('stroke-dashoffset'), font_size)
            if offset < 0:
                sum_dashes = sum(float(value) for value in dash_array)
                offset = sum_dashes - abs(offset) % sum_dashes
            self.stream.set_dash(dash_array, offset)

        # Apply line cap
        line_cap = node.get('stroke-linecap', 'butt')
        if line_cap == 'round':
            line_cap = 1
        elif line_cap == 'square':
            line_cap = 2
        else:
            line_cap = 0
        self.stream.set_line_cap(line_cap)

        # Apply line join
        line_join = node.get('stroke-linejoin', 'miter')
        if line_join == 'round':
            line_join = 1
        elif line_join == 'bevel':
            line_join = 2
        else:
            line_join = 0
        self.stream.set_line_join(line_join)

        # Apply miter limit
        miter_limit = float(node.get('stroke-miterlimit', 4))
        if miter_limit < 0:
            miter_limit = 4
        self.stream.set_miter_limit(miter_limit)

        # Fill and stroke
        even_odd = node.get('fill-rule') == 'evenodd'
        if text:
            if stroke and fill:
                text_rendering = 2
            elif stroke:
                text_rendering = 1
            elif fill:
                text_rendering = 0
            else:
                text_rendering = 3
            self.stream.set_text_rendering(text_rendering)
        else:
            if fill and stroke:
                self.stream.fill_and_stroke(even_odd)
            elif stroke:
                self.stream.stroke()
            elif fill:
                self.stream.fill(even_odd)
            else:
                self.stream.end()

    def transform(self, transform_string, font_size):
        """Apply a transformation string to the node."""
        if not transform_string:
            return

        matrix = transform(
            transform_string, font_size, self.normalized_diagonal)
        if matrix.determinant:
            self.stream.transform(
                matrix[0][0], matrix[0][1],
                matrix[1][0], matrix[1][1],
                matrix[2][0], matrix[2][1])

    def parse_defs(self, node):
        """Parse defs included in a tree."""
        for def_type in DEF_TYPES:
            if def_type in node.tag.lower() and 'id' in node.attrib:
                getattr(self, f'{def_type}s')[node.attrib['id']] = node
        for child in node:
            self.parse_defs(child)

    def calculate_bounding_box(self, node, font_size):
        """Calculate the bounding box of a node."""
        if node.bounding_box is None and node.tag in BOUNDING_BOX_METHODS:
            box = BOUNDING_BOX_METHODS[node.tag](self, node, font_size)
            if is_valid_bounding_box(box) and 0 not in box[2:]:
                node.bounding_box = box
        return node.bounding_box


class Pattern(SVG):
    """SVG node applied as a pattern."""
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
