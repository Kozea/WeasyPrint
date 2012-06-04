# coding: utf8
"""
    weasyprint.float
    ----------------

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from .markers import list_marker_layout
from .min_max import handle_min_max_width
from .percentages import resolve_percentages, resolve_position_percentages
from .preferred import shrink_to_fit
from .tables import table_wrapper_width
from ..formatting_structure import boxes


@handle_min_max_width
def float_width(box, document, containing_block):
    box.width = shrink_to_fit(document, box, containing_block.width)


def float_layout(document, box, containing_block, absolute_boxes):
    """Set the width and position of floating ``box``."""
    resolve_percentages(box, (containing_block.width, containing_block.height))
    resolve_position_percentages(
        box, (containing_block.width, containing_block.height))

    if box.margin_left == 'auto':
        box.margin_left = 0
    if box.margin_right == 'auto':
        box.margin_right = 0

    clearance = get_clearance(document, box)
    if clearance:
        box.position_y += clearance

    # avoid a circular import
    from .inlines import min_max_replaced_width, min_max_replaced_height

    if box.width == 'auto':
        if isinstance(box, boxes.BlockReplacedBox):
            min_max_replaced_width(box, None)
            min_max_replaced_height(box, None)
        else:
            float_width(box, document, containing_block)

    # avoid a circular import
    from .blocks import block_container_layout

    if box.is_table_wrapper:
        table_wrapper_width(
            document, box, (containing_block.width, containing_block.height),
            absolute_boxes)

    if isinstance(box, boxes.BlockBox):
        document.create_block_formatting_context()
        box, _, _, _, _ = block_container_layout(
            document, box, max_position_y=float('inf'),
            skip_stack=None, device_size=None, page_is_empty=False,
            absolute_boxes=absolute_boxes, adjoining_margins=None)
        list_marker_layout(document, box)
        document.finish_block_formatting_context(box)
    else:
        assert isinstance(box, boxes.BlockReplacedBox)

    box = find_float_position(document, box, containing_block)

    document.excluded_shapes.append(box)

    return box


def find_float_position(document, box, containing_block):
    """Get the right position of the float ``box``."""
    # See http://www.w3.org/TR/CSS2/visuren.html#dis-pos-flo

    # Point 4 is already handled as box.position_y is set according to the
    # containing box top position, with collapsing margins handled
    # TODO: are the collapsing margins *really* handled?

    # Points 5 and 6, box.position_y is set to the highest position_y possible
    if document.excluded_shapes:
        highest_y = document.excluded_shapes[-1].position_y
        if box.position_y < highest_y:
            box.translate(0, highest_y - box.position_y)

    # Points 1 and 2
    position_x, position_y, available_width = avoid_collisions(
        document, box, containing_block)

    # Point 9
    # position_y is set now, let's define position_x
    # for float: left elements, it's already done!
    if box.style.float == 'right':
        position_x = position_x + available_width - box.margin_width()

    box.translate(position_x - box.position_x, position_y - box.position_y)

    return box


def get_clearance(document, box):
    clearance = 0
    for excluded_shape in document.excluded_shapes:
        if box.style.clear in (excluded_shape.style.float, 'both'):
            y, h = excluded_shape.position_y, excluded_shape.margin_height()
            clearance = max(clearance, y + h - box.position_y)
    return clearance


def avoid_collisions(document, box, containing_block, outer=True):
    excluded_shapes = document.excluded_shapes
    position_y = box.position_y

    box_width = box.margin_width() if outer else box.width

    while True:
        left_bounds = [
            shape.position_x + shape.margin_width()
            for shape in excluded_shapes
            if shape.style.float == 'left'
            and (shape.position_y <= position_y <
                 shape.position_y + shape.margin_height())]
        right_bounds = [
            shape.position_x
            for shape in excluded_shapes
            if shape.style.float == 'right'
            and (shape.position_y <= position_y <
                 shape.position_y + shape.margin_height())]

        # Set the default maximum bounds
        max_left_bound = containing_block.content_box_x()
        max_right_bound = \
            containing_block.content_box_x() + containing_block.width

        # Set the real maximum bounds according to sibling float elements
        if left_bounds or right_bounds:
            if left_bounds:
                max_left_bound = max(left_bounds)
            if right_bounds:
                max_right_bound = min(right_bounds)
            # Points 3, 7 and 8
            if box_width > max_right_bound - max_left_bound:
                # The box does not fit here
                new_positon_y = min(
                    shape.position_y + shape.margin_height()
                    for shape in excluded_shapes
                    if (shape.position_y <= position_y <
                        shape.position_y + shape.margin_height()))
                if new_positon_y > position_y:
                    # We can find a solution with a higher position_y
                    position_y = new_positon_y
                    continue
                # No solution, we must put the box here
        break

    position_x = max_left_bound
    available_width = max_right_bound - max_left_bound

    return position_x, position_y, available_width
