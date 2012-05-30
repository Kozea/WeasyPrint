# coding: utf8
"""
    weasyprint.float
    ----------------

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from .absolute import absolute_layout
from .percentages import resolve_percentages, resolve_position_percentages
from .preferred import shrink_to_fit
from ..formatting_structure import boxes


class FloatPlaceholder(object):
    """Left where an float box was taken out of the flow."""
    def __init__(self, box):
        assert not isinstance(box, FloatPlaceholder)
        # Work around the overloaded __setattr__
        object.__setattr__(self, '_box', box)
        object.__setattr__(self, '_layout_done', False)

    def set_laid_out_box(self, new_box):
        object.__setattr__(self, '_box', new_box)
        object.__setattr__(self, '_layout_done', True)

    def translate(self, dx=0, dy=0):
        if self._layout_done:
            self._box.translate(dx, dy)
        else:
            # Descendants do not have a position yet.
            self._box.position_x += dx
            self._box.position_y += dy

    def copy(self):
        new_placeholder = FloatPlaceholder(self._box.copy())
        object.__setattr__(new_placeholder, '_layout_done', self._layout_done)
        return new_placeholder

    # Pretend to be the box itself
    def __getattr__(self, name):
        return getattr(self._box, name)

    def __setattr__(self, name, value):
        setattr(self._box, name, value)


def float_layout(document, placeholder, containing_block, absolute_boxes):
    """Set the width and position of floating ``box``."""
    box = placeholder._box

    cb = containing_block
    cb_width = cb.width
    cb_height = cb.height

    resolve_percentages(box, (cb_width, cb_height))
    resolve_position_percentages(box, (cb_width, cb_height))

    if box.margin_left == 'auto':
        box.margin_left = 0
    if box.margin_right == 'auto':
        box.margin_right = 0

    # avoid a circular import
    from .inlines import replaced_box_width, replaced_box_height

    if box.width == 'auto':
        if isinstance(box, boxes.BlockReplacedBox):
            replaced_box_width(box, None)
            replaced_box_height(box, None)
        else:
            box.width = shrink_to_fit(box, containing_block.width)

    # avoid a circular import
    from .blocks import block_container_layout

    if isinstance(box, boxes.BlockBox):
        box, _, _, _, _ = block_container_layout(
            document, box, max_position_y=float('inf'),
            skip_stack=None, device_size=None, page_is_empty=False,
            absolute_boxes=absolute_boxes, adjoining_margins=None)

    for child_placeholder in absolute_boxes:
        absolute_layout(document, child_placeholder, box)

    find_float_position(document, box, containing_block)

    document.excluded_shapes.append(box)

    placeholder.set_laid_out_box(box)


def find_float_position(document, box, containing_block):
    """Get the right position of the float ``box``."""
    # See http://www.w3.org/TR/CSS2/visuren.html#dis-pos-flo

    position_x, position_y = box.position_x, box.position_y

    # Point 4 is already handled as box.position_y is set according to the
    # containing box top position, with collapsing margins handled
    # TODO: are the collapsing margins *really* handled?

    # Handle clear
    for excluded_shape in document.excluded_shapes:
        x, y, w, h = (
            excluded_shape.position_x, excluded_shape.position_y,
            excluded_shape.margin_width(), excluded_shape.margin_height())
        if box.style.clear in (excluded_shape.style.float, 'both'):
            position_y = max(position_y, y + h)

    # Points 5 and 6, box.position_y is set to the highest position_y possible
    if document.excluded_shapes:
        position_y = max(position_y, document.excluded_shapes[-1].position_y)

    # Points 1 and 2
    while True:
        left_bounds = [
            shape.position_x + shape.margin_width()
            for shape in document.excluded_shapes
            if shape.style.float == 'left'
            and (shape.position_y <= position_y <
                 shape.position_y + shape.margin_height())]
        right_bounds = [
            shape.position_x
            for shape in document.excluded_shapes
            if shape.style.float == 'right'
            and (shape.position_y <= position_y <
                 shape.position_y + shape.margin_height())]
        max_left_bound = containing_block.content_box_x()
        max_right_bound = \
            containing_block.content_box_x() + containing_block.width
        if left_bounds or right_bounds:
            if left_bounds:
                max_left_bound = max(left_bounds)
            if right_bounds:
                max_right_bound = min(right_bounds)
            # Points 3, 7 and 8
            if box.margin_width() > max_right_bound - max_left_bound:
                new_positon_y = min(
                    shape.position_y + shape.margin_height()
                    for shape in document.excluded_shapes
                    if (shape.position_y <= position_y <
                        shape.position_y + shape.margin_height()))
                if new_positon_y > position_y:
                    position_y = new_positon_y
                    continue
        break

    # Point 9
    # position_y is set now, let's define position_x
    if box.style.float == 'left':
        position_x = max_left_bound
    else:
        assert box.style.float == 'right'
        position_x = max_right_bound - box.margin_width()

    box.translate(position_x - box.position_x, position_y - box.position_y)
