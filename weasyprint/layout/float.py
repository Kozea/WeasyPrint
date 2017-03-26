# coding: utf-8
"""
    weasyprint.float
    ----------------

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from ..formatting_structure import boxes
from .markers import list_marker_layout
from .min_max import handle_min_max_width
from .percentages import resolve_percentages, resolve_position_percentages
from .preferred import shrink_to_fit
from .tables import table_wrapper_width


@handle_min_max_width
def float_width(box, context, containing_block):
    # Check that box.width is auto even if the caller does it too, because
    # the handle_min_max_width decorator can change the value
    if box.width == 'auto':
        box.width = shrink_to_fit(context, box, containing_block.width)


def float_layout(context, box, containing_block, device_size, absolute_boxes,
                 fixed_boxes):
    """Set the width and position of floating ``box``."""
    # avoid a circular imports
    from .blocks import block_container_layout
    from .inlines import inline_replaced_box_width_height

    cb_width, cb_height = (containing_block.width, containing_block.height)
    resolve_percentages(box, (cb_width, cb_height))

    # TODO: This is only handled later in blocks.block_container_layout
    # http://www.w3.org/TR/CSS21/visudet.html#normal-block
    if cb_height == 'auto':
        cb_height = (
            containing_block.position_y - containing_block.content_box_y())

    resolve_position_percentages(box, (cb_width, cb_height))

    if box.margin_left == 'auto':
        box.margin_left = 0
    if box.margin_right == 'auto':
        box.margin_right = 0
    if box.margin_top == 'auto':
        box.margin_top = 0
    if box.margin_bottom == 'auto':
        box.margin_bottom = 0

    clearance = get_clearance(context, box)
    if clearance is not None:
        box.position_y += clearance

    if isinstance(box, boxes.BlockReplacedBox):
        inline_replaced_box_width_height(box, device_size=None)
    elif box.width == 'auto':
        float_width(box, context, containing_block)

    if box.is_table_wrapper:
        table_wrapper_width(context, box, (cb_width, cb_height))

    if isinstance(box, boxes.BlockBox):
        context.create_block_formatting_context()
        box, _, _, _, _ = block_container_layout(
            context, box, max_position_y=float('inf'),
            skip_stack=None, device_size=device_size, page_is_empty=False,
            absolute_boxes=absolute_boxes, fixed_boxes=fixed_boxes,
            adjoining_margins=None)
        list_marker_layout(context, box)
        context.finish_block_formatting_context(box)
    else:
        assert isinstance(box, boxes.BlockReplacedBox)

    box = find_float_position(context, box, containing_block)

    context.excluded_shapes.append(box)

    return box


def find_float_position(context, box, containing_block):
    """Get the right position of the float ``box``."""
    # See http://www.w3.org/TR/CSS2/visuren.html#float-position

    # Point 4 is already handled as box.position_y is set according to the
    # containing box top position, with collapsing margins handled

    # Points 5 and 6, box.position_y is set to the highest position_y possible
    if context.excluded_shapes:
        highest_y = context.excluded_shapes[-1].position_y
        if box.position_y < highest_y:
            box.translate(0, highest_y - box.position_y)

    # Points 1 and 2
    position_x, position_y, available_width = avoid_collisions(
        context, box, containing_block)

    # Point 9
    # position_y is set now, let's define position_x
    # for float: left elements, it's already done!
    if box.style.float == 'right':
        position_x += available_width - box.margin_width()

    box.translate(position_x - box.position_x, position_y - box.position_y)

    return box


def get_clearance(context, box, collapsed_margin=0):
    """Return None if there is no clearance, otherwise the clearance value."""
    clearance = None
    hypothetical_position = box.position_y + collapsed_margin
    # Hypothetical position is the position of the top border edge
    for excluded_shape in context.excluded_shapes:
        if box.style['clear'] in (excluded_shape.style.float, 'both'):
            y, h = excluded_shape.position_y, excluded_shape.margin_height()
            if hypothetical_position < y + h:
                clearance = max(
                    (clearance or 0), y + h - hypothetical_position)
    return clearance


def avoid_collisions(context, box, containing_block, outer=True):
    excluded_shapes = context.excluded_shapes
    position_y = box.position_y if outer else box.border_box_y()

    box_width = box.margin_width() if outer else box.border_width()
    box_height = box.margin_height() if outer else box.border_height()

    if box.border_height() == 0 and box.is_floated():
        return 0, 0, containing_block.width

    while True:
        colliding_shapes = [
            shape for shape in excluded_shapes
            if (shape.position_y < position_y <
                shape.position_y + shape.margin_height()) or
            (shape.position_y < position_y + box_height <
                shape.position_y + shape.margin_height()) or
            (shape.position_y >= position_y and
                shape.position_y + shape.margin_height() <=
                position_y + box_height)
        ]
        left_bounds = [
            shape.position_x + shape.margin_width()
            for shape in colliding_shapes
            if shape.style.float == 'left']
        right_bounds = [
            shape.position_x
            for shape in colliding_shapes
            if shape.style.float == 'right']

        # Set the default maximum bounds
        max_left_bound = containing_block.content_box_x()
        max_right_bound = \
            containing_block.content_box_x() + containing_block.width

        if not outer:
            max_left_bound += box.margin_left
            max_right_bound -= box.margin_right

        # Set the real maximum bounds according to sibling float elements
        if left_bounds or right_bounds:
            if left_bounds:
                max_left_bound = max(max(left_bounds), max_left_bound)
            if right_bounds:
                max_right_bound = min(min(right_bounds), max_right_bound)

            # Points 3, 7 and 8
            if box_width > max_right_bound - max_left_bound:
                # The box does not fit here
                new_positon_y = min(
                    shape.position_y + shape.margin_height()
                    for shape in colliding_shapes)
                if new_positon_y > position_y:
                    # We can find a solution with a higher position_y
                    position_y = new_positon_y
                    continue
                # No solution, we must put the box here
        break

    position_x = max_left_bound
    available_width = max_right_bound - max_left_bound

    if not outer:
        position_x -= box.margin_left
        position_y -= box.margin_top

    return position_x, position_y, available_width
