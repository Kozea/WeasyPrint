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
    from .blocks import (
        block_box_layout, block_level_layout, block_level_width,
        collapse_margin)

    # Implementation of the multi-column pseudo-algorithm:
    # https://www.w3.org/TR/css3-multicol/#pseudo-algorithm
    width = None
    style = box.style
    original_max_position_y = max_position_y

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

    def create_column_box(children):
        column_box = box.anonymous_from(box, children=children)
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

    # Handle column-span property.
    # We want to get the following structure:
    # columns_and_blocks = [
    #     [column_child_1, column_child_2],
    #     spanning_block,
    #     …
    # ]
    columns_and_blocks = []
    column_children = []
    for child in box.children:
        if child.style['column_span'] == 'all':
            if column_children:
                columns_and_blocks.append(column_children)
            columns_and_blocks.append(child.copy())
            column_children = []
            continue
        column_children.append(child.copy())
    if column_children:
        columns_and_blocks.append(column_children)

    if not box.children:
        next_page = {'break': 'any', 'page': None}
        skip_stack = None

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

    adjoining_margins = []
    current_position_y = box.content_box_y()
    new_children = []
    for column_children_or_block in columns_and_blocks:
        if not isinstance(column_children_or_block, list):
            # We get a spanning block, we display it like other blocks.
            block = column_children_or_block
            resolve_percentages(block, containing_block)
            block.position_x = box.content_box_x()
            block.position_y = current_position_y
            new_child, _, _, adjoining_margins, _ = block_level_layout(
                context, block, original_max_position_y, skip_stack,
                containing_block, device_size, page_is_empty, absolute_boxes,
                fixed_boxes, adjoining_margins)
            new_children.append(new_child)
            current_position_y = (
                new_child.border_height() + new_child.border_box_y())
            adjoining_margins.append(new_child.margin_bottom)
            continue

        # We have a list of children that we have to balance between columns.
        column_children = column_children_or_block

        # Find the total height of the content
        current_position_y += collapse_margin(adjoining_margins)
        adjoining_margins = []
        column_box = create_column_box(column_children)
        new_child, _, _, _, _ = block_box_layout(
            context, column_box, float('inf'), skip_stack, containing_block,
            device_size, page_is_empty, [], [], [])
        height = new_child.margin_height()
        if style['column_fill'] == 'balance':
            height /= count
        box_column_descendants = list(column_descendants(new_child))

        # Increase the column height step by step.
        while True:
            # For each step, we try to find the empty height needed to make the
            # top element of column i+1 fit at the end of column i. We put this
            # needed space in lost_spaces.
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
                            # It's the first child of the column and we're
                            # already below the bottom of the column. The
                            # column's height has to be at least the size of
                            # the child. Let's put the height difference into
                            # lost_spaces and continue the while loop.
                            lost_spaces = [child_bottom - height]
                            break
                        # Put the child at the top of the next column and put
                        # the extra empty space that would have allowed this
                        # child to fit into lost_spaces.
                        lost_spaces.append(child_bottom - height)
                        column_number += 1
                        column_first_child = True
                        column_top = child.position_y
                    else:
                        # We're in the last column, there's no place left to
                        # put that child. We need to go for another round of
                        # the while loop.
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
        i = 0
        max_column_height = 0
        columns = []
        while True:
            if i == count - 1:
                max_position_y = original_max_position_y
            column_box = create_column_box(column_children)
            column_box.position_y = current_position_y
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
            columns.append(new_child)
            max_column_height = max(
                max_column_height, new_child.margin_height())
            if skip_stack is None:
                break
            i += 1
            if i == count and not known_height:
                # [If] a declaration that constrains the column height
                # (e.g., using height or max-height). In this case,
                # additional column boxes are created in the inline
                # direction.
                break

        current_position_y += max_column_height
        for column in columns:
            column.height = max_column_height
            new_children.append(column)

    if box.children and not new_children:
        # The box has children but none can be drawn, let's skip the whole box
        return None, (0, None), {'break': 'any', 'page': None}, [], False

    # Set the height of box and the columns
    box.children = new_children
    current_position_y += collapse_margin(adjoining_margins)
    if box.height == 'auto':
        box.height = current_position_y - box.position_y
        height_difference = 0
    else:
        height_difference = box.height - (current_position_y - box.position_y)
    if box.min_height != 'auto' and box.min_height > box.height:
        height_difference += box.min_height - box.height
        box.height = box.min_height
    for child in new_children[::-1]:
        if child.is_column:
            child.height += height_difference
        else:
            break

    if box.style['position'] == 'relative':
        # New containing block, resolve the layout of the absolute descendants
        for absolute_box in absolute_boxes:
            absolute_layout(context, absolute_box, box, fixed_boxes)

    return box, skip_stack, next_page, [], False
