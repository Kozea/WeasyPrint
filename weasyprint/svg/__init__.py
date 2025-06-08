"""Render SVG images."""

import re
from contextlib import suppress
from math import cos, hypot, pi, radians, sin, sqrt
from xml.etree import ElementTree

from cssselect2 import ElementWrapper

from ..urls import get_url_attribute
from .css import parse_declarations, parse_stylesheets
from .defs import apply_filters, clip_path, draw_gradient_or_pattern, paint_mask, use
from .images import image, svg
from .path import path
from .shapes import circle, ellipse, line, polygon, polyline, rect
from .text import text

from .bounding_box import (  # isort:skip
    EMPTY_BOUNDING_BOX, bounding_box, extend_bounding_box, is_valid_bounding_box)
from .utils import (  # isort:skip
    PointError, alpha_value, color, normalize, parse_url, preserve_ratio, size,
    transform)

TAGS = {
    'a': text,
    'circle': circle,
    'clipPath': clip_path,
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
    'clipPath',
    'filter',
    'gradient',
    'image',
    'marker',
    'mask',
    'path',
    'pattern',
    'symbol',
))


class Node:
    """An SVG document node."""

    def __init__(self, wrapper, style):
        self._wrapper = wrapper
        self._etree_node = wrapper.etree_element
        self._style = style
        self._children = None

        self.attrib = wrapper.etree_element.attrib.copy()

        self.vertices = []
        self.bounding_box = None

    def copy(self):
        """Create a deep copy of the node as it was when first created."""
        return Node(self._wrapper, self._style)

    def get(self, key, default=None):
        """Get attribute."""
        return self.attrib.get(key, default)

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

    @property
    def display(self):
        """Whether node should be displayed."""
        return self.get('display') != 'none'

    @property
    def visible(self):
        """Whether node is visible."""
        return self.display and self.get('visibility') != 'hidden'

    def cascade(self, child):
        """Apply CSS cascade and other related operations to given child."""
        wrapper = child._wrapper

        # Cascade
        for key, value in self.attrib.items():
            if key not in NOT_INHERITED_ATTRIBUTES:
                if key not in child.attrib:
                    child.attrib[key] = value

        # Apply style attribute
        if style_attr := child.get('style'):
            normal_attr, important_attr = parse_declarations(style_attr)
        else:
            normal_attr, important_attr = [], []
        normal_matcher, important_matcher = self._style
        normal = [rule[-1] for rule in normal_matcher.match(wrapper)]
        important = [rule[-1] for rule in important_matcher.match(wrapper)]
        for declarations_list in (normal, [normal_attr], important, [important_attr]):
            for declarations in declarations_list:
                for name, value in declarations:
                    child.attrib[name] = value.strip()

        # Replace 'currentColor' value
        for key in COLOR_ATTRIBUTES:
            if child.get(key) == 'currentColor':
                child.attrib[key] = child.get('color', 'black')

        # Handle 'inherit' values
        for key, value in child.attrib.copy().items():
            if value == 'inherit':
                value = self.get(key)
                if value is None:
                    del child.attrib[key]
                else:
                    child.attrib[key] = value

        # Fix text in text tags
        if child.tag in ('text', 'textPath', 'a'):
            children, _ = child.text_children(
                wrapper, trailing_space=True, text_root=True)
            child._wrapper.etree_children = [
                child._etree_node for child in children]


    def __iter__(self):
        """Yield node children, handling cascade."""
        if self._children is None:
            children = []
            for wrapper in self._wrapper:
                child = Node(wrapper, self._style)
                self.cascade(child)
                children.append(child)
            self._children = children
        return iter(self._children)

    def get_viewbox(self):
        """Get node viewBox as a tuple of floats."""
        viewbox = self.get('viewBox')
        if viewbox:
            return tuple(float(number) for number in normalize(viewbox).split())

    def get_href(self, base_url):
        """Get the href attribute, with or without a namespace."""
        for attr_name in ('{http://www.w3.org/1999/xlink}href', 'href'):
            if url := get_url_attribute(self, attr_name, base_url, allow_relative=True):
                return url

    def del_href(self):
        """Remove the href attributes, with or without a namespace."""
        for attr_name in ('{http://www.w3.org/1999/xlink}href', 'href'):
            self.attrib.pop(attr_name, None)

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
        element_children = tuple(element.iter_children())
        for child_element in element_children:
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
            tail = self.process_whitespace(child.tail, preserve)
            if text_root and child_element is element_children[-1]:
                if not preserve:
                    tail = tail.rstrip(' ')
            if tail:
                anonymous_etree = ElementTree.Element(
                    '{http://www.w3.org/2000/svg}tspan')
                anonymous = Node(
                    ElementWrapper.from_xml_root(anonymous_etree), self._style)
                anonymous._etree_node.text = tail
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

    def override_iter(self, iterator):
        """Override node’s children iterator."""
        # As special methods are bound to classes and not instances, we have to
        # create and assign a new type.
        self.__class__ = type(
            'Node', (Node,), {'__iter__': lambda _: iterator})

    def set_svg_size(self, svg, concrete_width, concrete_height):
        """"Set SVG concrete and inner widths and heights from svg node."""
        svg.concrete_width = concrete_width
        svg.concrete_height = concrete_height
        svg.normalized_diagonal = hypot(concrete_width, concrete_height) / sqrt(2)

        if viewbox := self.get_viewbox():
            svg.inner_width, svg.inner_height = viewbox[2], viewbox[3]
        else:
            svg.inner_width, svg.inner_height = svg.concrete_width, svg.concrete_height
        svg.inner_diagonal = hypot(svg.inner_width, svg.inner_height) / sqrt(2)



class SVG:
    """An SVG document."""

    def __init__(self, tree, url):
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
        self.symbols = {}

        self.use_cache = {}

        self.cursor_position = [0, 0]
        self.cursor_d_position = [0, 0]
        self.text_path_width = 0

        self.tree.cascade(self.tree)
        self.parse_defs(self.tree)
        self.inherit_defs()

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
            size(x, font_size, self.inner_width),
            size(y, font_size, self.inner_height))

    def length(self, length, font_size):
        """Compute size of an arbirtary attribute."""
        return size(length, font_size, self.inner_diagonal)

    def draw(self, stream, concrete_width, concrete_height, base_url,
             url_fetcher, context):
        """Draw image on a stream."""
        self.stream = stream

        self.tree.set_svg_size(self, concrete_width, concrete_height)

        self.base_url = base_url
        self.url_fetcher = url_fetcher
        self.context = context

        self.draw_node(self.tree, size('12pt'))

    def draw_node(self, node, font_size, fill_stroke=True):
        """Draw a node."""
        if node.tag == 'defs':
            return

        # Update font size
        font_size = size(node.get('font-size', '1em'), font_size, font_size)

        original_streams = []

        if fill_stroke:
            self.stream.push_state()

        # Apply filters
        filter_ = self.filters.get(parse_url(node.get('filter')).fragment)
        if filter_:
            apply_filters(self, node, filter_, font_size)

        # Apply transform attribute
        self.transform(node, font_size)

        # Create substream for opacity
        opacity = alpha_value(node.get('opacity', 1))
        if fill_stroke and 0 <= opacity < 1:
            original_streams.append(self.stream)
            self.stream = self.stream.add_group(0, 0, 0, 0)  # BBox set after drawing

        # Clip
        clip_path = parse_url(node.get('clip-path')).fragment
        if clip_path and clip_path in self.paths:
            old_ctm = self.stream.ctm
            clip_path = self.paths[clip_path]
            if clip_path.get('clipPathUnits') == 'objectBoundingBox':
                x, y = self.point(node.get('x'), node.get('y'), font_size)
                width, height = self.point(
                    node.get('width'), node.get('height'), font_size)
                self.stream.transform(a=width, d=height, e=x, f=y)
            original_tag = clip_path._etree_node.tag
            clip_path._etree_node.tag = 'g'
            self.draw_node(clip_path, font_size, fill_stroke=False)
            clip_path._etree_node.tag = original_tag
            # At least set the clipping area to an empty path, so that it’s
            # totally clipped when the clipping path is empty.
            self.stream.rectangle(0, 0, 0, 0)
            self.stream.clip()
            self.stream.end()
            new_ctm = self.stream.ctm
            if new_ctm.determinant:
                self.stream.transform(*(old_ctm @ new_ctm.invert).values)

        # Handle text anchor and set text bounding box
        text_anchor_shift = False
        if node.display and TAGS.get(node.tag) == text:
            if (text_anchor := node.get('text-anchor')) in ('middle', 'end'):
                text_anchor_shift = True
                group = self.stream.add_group(0, 0, 0, 0)  # BBox set after drawing
                original_streams.append(self.stream)
                self.stream = group
            node.text_bounding_box = EMPTY_BOUNDING_BOX

        # Save concrete size of root svg tag
        if node.tag == 'svg':
            concrete_width = self.concrete_width
            concrete_height = self.concrete_height

        # Draw node
        if node.visible and node.tag in TAGS:
            with suppress(PointError):
                TAGS[node.tag](self, node, font_size)

        # Draw node children
        if node.display and node.tag not in DEF_TYPES:
            for child in node:
                new_chunk = text_anchor_shift and (
                    child.tag == 'text' or 'x' in child.attrib or 'y' in child.attrib)
                if new_chunk:
                    new_stream = self.stream
                    self.stream = original_streams[-1]
                self.draw_node(child, font_size, fill_stroke)
                if new_chunk:
                    self.stream = new_stream
                visible_text_child = (
                    TAGS.get(node.tag) == text and
                    TAGS.get(child.tag) == text and
                    child.visible)
                if visible_text_child:
                    if not is_valid_bounding_box(child.text_bounding_box):
                        continue
                    x1, y1 = child.text_bounding_box[:2]
                    x2 = x1 + child.text_bounding_box[2]
                    y2 = y1 + child.text_bounding_box[3]
                    node.text_bounding_box = extend_bounding_box(
                        node.text_bounding_box, ((x1, y1), (x2, y2)))

        # Restore concrete and inner size of root svg tag
        if node.tag == 'svg':
            self.tree.set_svg_size(svg, concrete_width, concrete_height)

        # Handle text anchor
        if text_anchor_shift:
            group_id = self.stream.id
            self.stream = original_streams.pop()
            self.stream.push_state()
            if is_valid_bounding_box(node.text_bounding_box):
                x, y, width, height = node.text_bounding_box
                # Add extra space to include ink extents
                group.extra['BBox'][:] = (
                    x - font_size, y - font_size,
                    x + width + font_size, y + height + font_size)
                x_align = width / 2 if text_anchor == 'middle' else width
                if node.tag == 'text' or 'x' in node.attrib or 'y' in node.attrib:
                    self.stream.transform(e=-x_align)
            self.stream.draw_x_object(group_id)
            self.stream.pop_state()

        # Apply mask
        mask = self.masks.get(parse_url(node.get('mask')).fragment)
        if mask:
            paint_mask(self, node, mask, opacity)

        # Fill and stroke
        if fill_stroke:
            self.fill_stroke(node, font_size)

        # Draw markers
        self.draw_markers(node, font_size, fill_stroke)

        # Apply opacity stream and restore original stream
        if fill_stroke and 0 <= opacity < 1:
            box = self.calculate_bounding_box(node, font_size)
            if not is_valid_bounding_box(box):
                box = (0, 0, self.inner_width, self.inner_height)
            x, y, width, height = box
            self.stream.extra['BBox'][:] = x, y, x + width, y + height

            group_id = self.stream.id
            self.stream = original_streams.pop()
            self.stream.set_alpha(opacity, stroke=True, fill=True)
            self.stream.draw_x_object(group_id)

        # Clean text tag
        if node.tag == 'text':
            self.cursor_position = [0, 0]
            self.cursor_d_position = [0, 0]
            self.text_path_width = 0

        if fill_stroke:
            self.stream.pop_state()

    def draw_markers(self, node, font_size, fill_stroke):
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
            if not (marker_node := self.markers.get(markers[position])):
                position = 'mid' if angles else 'start'
                continue

            # Calculate position, scale and clipping
            translate_x, translate_y = self.point(
                marker_node.get('refX'), marker_node.get('refY'),
                font_size)
            marker_width, marker_height = self.point(
                marker_node.get('markerWidth', 3),
                marker_node.get('markerHeight', 3),
                font_size)
            if 'viewBox' in marker_node.attrib:
                scale_x, scale_y, _, _ = preserve_ratio(
                    self, marker_node, font_size, marker_width, marker_height)

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
                scale_x = scale_y = 1
                clip_box = (0, 0, marker_width, marker_height)

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
                self.stream.transform(e=-translate_x, f=-translate_y)

                overflow = marker_node.get('overflow', 'hidden')
                if overflow in ('hidden', 'scroll'):
                    self.stream.rectangle(*clip_box)
                    self.stream.clip()
                    self.stream.end()

                self.draw_node(child, font_size, fill_stroke)
                self.stream.pop_state()

            position = 'mid' if angles else 'start'

    @staticmethod
    def get_paint(value):
        """Get paint fill or stroke attribute with a color or a URL."""
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
        fill_source, fill_color = self.get_paint(node.get('fill', 'black'))
        fill_opacity = alpha_value(node.get('fill-opacity', 1))
        fill_drawn = draw_gradient_or_pattern(
            self, node, fill_source, font_size, fill_opacity, stroke=False)
        if fill_color and not fill_drawn:
            stream_color = color(fill_color)
            stream_color.alpha *= fill_opacity
            self.stream.set_color(stream_color)
        fill = fill_color or fill_drawn

        # Get stroke data
        stroke_source, stroke_color = self.get_paint(node.get('stroke'))
        stroke_opacity = alpha_value(node.get('stroke-opacity', 1))
        stroke_drawn = draw_gradient_or_pattern(
            self, node, stroke_source, font_size, stroke_opacity, stroke=True)
        if stroke_color and not stroke_drawn:
            stream_color = color(stroke_color)
            stream_color.alpha *= stroke_opacity
            self.stream.set_color(stream_color, stroke=True)
        stroke = stroke_color or stroke_drawn
        stroke_width = self.length(node.get('stroke-width', '1px'), font_size)
        if stroke_width:
            self.stream.set_line_width(stroke_width)
        else:
            stroke = None

        # Apply dash array
        dash_array = tuple(
            self.length(value, font_size) for value in
            normalize(node.get('stroke-dasharray')).split() if value != 'none')
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

    def transform(self, node, font_size):
        """Apply a transformation string to the node."""
        transform_origin = node.get('transform-origin')
        transform_string = node.get('transform')
        if not transform_string:
            return

        matrix = transform(
            transform_string, transform_origin, font_size, self.inner_diagonal)
        if matrix.determinant:
            self.stream.transform(*matrix.values)

    def parse_defs(self, node):
        """Parse defs included in a tree."""
        for def_type in DEF_TYPES:
            if def_type in node.tag.lower() and 'id' in node.attrib:
                getattr(self, f'{def_type}s')[node.attrib['id']] = node
        for child in node:
            self.parse_defs(child)

    def inherit_defs(self):
        """Handle inheritance of different defined elements lists."""
        for defs in (self.gradients, self.patterns):
            for element in defs.values():
                self.inherit_element(element, defs)

    def inherit_element(self, element, defs):
        """Recursively handle inheritance of defined element."""
        href = element.get_href(self.url)
        if not href:
            return
        element.del_href()
        parent = defs.get(parse_url(href).fragment)
        if not parent:
            return
        self.inherit_element(parent, defs)
        for key, value in parent.attrib.items():
            if key not in element.attrib:
                element.attrib[key] = value
        if next(iter(element), None) is None:
            element.override_iter(parent.__iter__())

    def calculate_bounding_box(self, node, font_size, stroke=True):
        """Calculate the bounding box of a node."""
        if stroke or node.bounding_box is None:
            box = bounding_box(self, node, font_size, stroke)
            if is_valid_bounding_box(box) and 0 not in box[2:]:
                if stroke:
                    return box
                node.bounding_box = box
        return node.bounding_box


class Pattern(SVG):
    """SVG node applied as a pattern."""
    def __init__(self, tree, svg):
        super().__init__(tree._etree_node, svg.url)
        self.svg = svg
        self.tree = tree

    def draw_node(self, node, font_size, fill_stroke=True):
        # Store the original tree in self.tree when calling draw(), so that we
        # can reach defs outside the pattern
        if node == self.tree:
            self.tree = self.svg.tree
        super().draw_node(node, font_size, fill_stroke=True)
