"""
    weasyprint.layout.columns
    -------------------------

    Layout for columns.

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from math import floor

from ..formatting_structure import boxes
from .absolute import absolute_layout
from .percentages import resolve_percentages


def columns_layout(context, box, max_position_y, skip_stack, containing_block,
                   device_size, page_is_empty, absolute_boxes, fixed_boxes,
                   adjoining_margins):
    """Lay out a multi-column ``box``."""
    # Avoid circular imports
    from .blocks import block_box_layout, block_level_width

    # Implementation of the multi-column pseudo-algorithm:
    # https://www.w3.org/TR/css3-multicol/#pseudo-algorithm
    count = None
    width = None
    style = box.style

    if box.style['position'] == 'relative':
        # New containing block, use a new absolute list
        absolute_boxes = []

    box = box.copy_with_children(box.children)

    height = box.style['height']
    if height != 'auto' and height.unit != '%':
        assert height.unit == 'px'
        known_height = True
        max_position_y = min(
            max_position_y, box.content_box_y() + height.value)
    else:
        known_height = False

    # TODO: the available width can be unknown if the containing block needs
    # the size of this block to know its own size.
    block_level_width(box, containing_block)
    available_width = box.width
    if count is None:
        if style['column_width'] == 'auto' and style['column_count'] != 'auto':
            count = style['column_count']
            width = max(
                0, available_width - (count - 1) * style['column_gap']) / count
        elif (style['column_width'] != 'auto' and
              style['column_count'] == 'auto'):
            count = max(1, int(floor(
                (available_width + style['column_gap']) /
                (style['column_width'] + style['column_gap']))))
            width = (
                (available_width + style['column_gap']) / count -
                style['column_gap'])
        else:
            count = min(style['column_count'], int(floor(
                (available_width + style['column_gap']) /
                (style['column_width'] + style['column_gap']))))
            width = (
                (available_width + style['column_gap']) / count -
                style['column_gap'])

    def create_column_box():
        column_box = box.anonymous_from(box, children=[
            child.copy() for child in box.children])
        resolve_percentages(column_box, containing_block)
        column_box.is_column = True
        column_box.width = width
        column_box.position_x = box.content_box_x()
        column_box.position_y = box.content_box_y()
        return column_box

    def column_descendants(box):
        # TODO: this filtering condition is probably wrong
        if isinstance(box, (boxes.TableBox, boxes.LineBox, boxes.ReplacedBox)):
            yield box
        if hasattr(box, 'descendants') and box.is_in_normal_flow():
            for child in box.children:
                if child.is_in_normal_flow():
                    yield child
                    for grand_child in column_descendants(child):
                        yield grand_child

    # Balance.
    #
    # The current algorithm starts from the ideal height (the total height
    # divided by the number of columns). We then iterate until the last column
    # is not the highest one. At the end of each loop, we add the minimal
    # height needed to make one direct child at the top of one column go to the
    # end of the previous column.
    #
    # We must probably rely on a real rendering for each loop, but with a
    # stupid algorithm like this it can last minutes.
    #
    # TODO: Rewrite this!
    # - We assume that the children are normal lines or blocks.
    # - We ignore the forced and avoided column breaks.

    # Find the total height of the content
    original_max_position_y = max_position_y
    column_box = create_column_box()
    new_child, _, _, _, _ = block_box_layout(
        context, column_box, float('inf'), skip_stack, containing_block,
        device_size, page_is_empty, [], [], [])
    height = new_child.margin_height()
    if style['column_fill'] == 'balance':
        height /= count
    box_column_descendants = list(column_descendants(new_child))

    # Increase the column height step by step.
    while True:
        # For each step, we try to find the empty height needed to make the top
        # element of column i+1 fit at the end of column i. We put this needed
        # space in lost_spaces.
        lost_spaces = []
        column_number = 0
        column_first_child = True
        column_top = new_child.content_box_y()
        for child in box_column_descendants:
            child_height = child.margin_height()
            child_bottom = child.position_y + child_height - column_top
            if child_bottom > height:
                # The child goes lower than the column height.
                if column_number < count - 1:
                    # We're not in the last column.
                    if column_first_child:
                        # It's the first child of the column and we're already
                        # below the bottom of the column. The column's height
                        # has to be at least the size of the child. Let's put
                        # the height difference into lost_spaces and continue
                        # the while loop.
                        lost_spaces = [child_bottom - height]
                        break
                    # Put the child at the top of the next column and put the
                    # extra empty space that would have allowed this child to
                    # fit into lost_spaces.
                    lost_spaces.append(child_bottom - height)
                    column_number += 1
                    column_first_child = True
                    column_top = child.position_y
                else:
                    # We're in the last column, there's no place left to put
                    # that child. We need to go for another round of the while
                    # loop.
                    break
            column_first_child = False
        else:
            # We've seen all the children and they all fit in their
            # columns. Balanced height has been found, quit the while loop.
            break
        height += min(lost_spaces)

    # TODO: check box.style['max']-height
    max_position_y = min(max_position_y, box.content_box_y() + height)

    # Replace the current box children with columns
    children = []
    if box.children:
        i = 0
        while True:
            if i == count - 1:
                max_position_y = original_max_position_y
            column_box = create_column_box()
            if style['direction'] == 'rtl':
                column_box.position_x += (
                    box.width - (i + 1) * width - i * style['column_gap'])
            else:
                column_box.position_x += i * (width + style['column_gap'])
            new_child, column_skip_stack, column_next_page, _, _ = (
                block_box_layout(
                    context, column_box, max_position_y, skip_stack,
                    containing_block, device_size, page_is_empty,
                    absolute_boxes, fixed_boxes, None))
            if new_child is None:
                break
            next_page = column_next_page
            skip_stack = column_skip_stack
            children.append(new_child)
            if skip_stack is None:
                break
            i += 1
            if i == count and not known_height:
                # [If] a declaration that constrains the column height (e.g.,
                # using height or max-height). In this case, additional column
                # boxes are created in the inline direction.
                break
    else:
        next_page = {'break': 'any', 'page': None}
        skip_stack = None

    if box.children and not children:
        # The box has children but none can be drawn, let's skip the whole box
        return None, (0, None), {'break': 'any', 'page': None}, [0], False

    # Set the height of box and the columns
    box.children = children
    if box.children:
        heights = [child.margin_height() for child in box.children]
        if box.height != 'auto':
            heights.append(box.height)
        if box.min_height != 'auto':
            heights.append(box.min_height)
        box.height = max(heights)
        for child in box.children:
            child.height = box.margin_height()
    else:
        box.height = 0

    if box.style['position'] == 'relative':
        # New containing block, resolve the layout of the absolute descendants
        for absolute_box in absolute_boxes:
            absolute_layout(context, absolute_box, box, fixed_boxes)

    return box, skip_stack, next_page, [0], False
