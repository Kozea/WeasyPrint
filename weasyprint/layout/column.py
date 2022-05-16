"""Layout for columns."""

from math import floor, inf

from .absolute import absolute_layout
from .percent import resolve_percentages


def columns_layout(context, box, bottom_space, skip_stack, containing_block,
                   page_is_empty, absolute_boxes, fixed_boxes,
                   adjoining_margins):
    """Lay out a multi-column ``box``."""
    from .block import (
        block_box_layout, block_level_layout, block_level_width,
        collapse_margin)

    # Implementation of the multi-column pseudo-algorithm:
    # https://www.w3.org/TR/css3-multicol/#pseudo-algorithm
    width = None
    style = box.style
    original_bottom_space = bottom_space
    context.in_column = True

    if box.style['position'] == 'relative':
        # New containing block, use a new absolute list
        absolute_boxes = []

    box = box.copy_with_children(box.children)
    box.position_y += collapse_margin(adjoining_margins) - box.margin_top

    height = box.style['height']
    if height != 'auto' and height.unit != '%':
        assert height.unit == 'px'
        known_height = True
        bottom_space = max(
            bottom_space,
            context.page_bottom - box.content_box_y() - height.value)
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

    # Handle column-span property.
    # We want to get the following structure:
    # columns_and_blocks = [
    #     [column_child_1, column_child_2],
    #     spanning_block,
    #     …
    # ]
    columns_and_blocks = []
    column_children = []

    if skip_stack:
        skip, = skip_stack.keys()
    else:
        skip = 0

    for index, child in enumerate(box.children[skip:], start=skip):
        if child.style['column_span'] == 'all':
            if column_children:
                columns_and_blocks.append(
                    (index - len(column_children), column_children))
            columns_and_blocks.append((index, child.copy()))
            column_children = []
            continue
        column_children.append(child.copy())
    if column_children:
        columns_and_blocks.append(
            (index + 1 - len(column_children), column_children))

    if skip_stack:
        skip_stack = {0: skip_stack[skip]}

    if not box.children:
        next_page = {'break': 'any', 'page': None}
        skip_stack = None

    # Balance.
    #
    # The current algorithm starts from the total available height, to check
    # whether the whole content can fit. If it doesn’t fit, we keep the partial
    # rendering. If it fits, we try to balance the columns starting from the
    # ideal height (the total height divided by the number of columns). We then
    # iterate until the last column is not the highest one. At the end of each
    # loop, we add the minimal height needed to make one direct child at the
    # top of one column go to the end of the previous column.
    #
    # We rely on a real rendering for each loop, and with a stupid algorithm
    # like this it can last minutes…

    adjoining_margins = []
    current_position_y = box.content_box_y()
    new_children = []
    column_skip_stack = None
    forced_end_probing = False
    break_page = False
    for index, column_children_or_block in columns_and_blocks:
        if not isinstance(column_children_or_block, list):
            # We get a spanning block, we display it like other blocks.
            block = column_children_or_block
            resolve_percentages(block, containing_block)
            block.position_x = box.content_box_x()
            block.position_y = current_position_y
            new_child, resume_at, next_page, adjoining_margins, _, _ = (
                block_level_layout(
                    context, block, original_bottom_space, skip_stack,
                    containing_block, page_is_empty, absolute_boxes,
                    fixed_boxes, adjoining_margins, discard=False,
                    max_lines=None))
            skip_stack = None
            if new_child is None:
                forced_end_probing = True
                break_page = True
                break
            new_children.append(new_child)
            current_position_y = (
                new_child.border_height() + new_child.border_box_y())
            adjoining_margins.append(new_child.margin_bottom)
            if resume_at:
                forced_end_probing = True
                break_page = True
                column_skip_stack = resume_at
                break
            page_is_empty = False
            continue

        excluded_shapes = context.excluded_shapes[:]

        # We have a list of children that we have to balance between columns.
        column_children = column_children_or_block

        # Find the total height available for the first run.
        current_position_y += collapse_margin(adjoining_margins)
        adjoining_margins = []
        column_box = create_column_box(column_children)
        column_box.position_y = current_position_y
        max_height = context.page_bottom - current_position_y
        height = max_height

        # Try to render columns until the content fits, increase the column
        # height step by step.
        column_skip_stack = skip_stack
        lost_space = inf
        first_probe_run = True
        original_page_is_empty = page_is_empty
        page_is_empty = False
        stop_rendering = False
        while True:
            column_skip_stack = skip_stack

            # Remove extra excluded shapes introduced during previous loop
            new_excluded_shapes = (
                len(context.excluded_shapes) - len(excluded_shapes))
            for i in range(new_excluded_shapes):
                context.excluded_shapes.pop()

            consumed_heights = []
            for i in range(count):
                # Render the column
                new_box, resume_at, next_page, _, _, _ = block_box_layout(
                    context, column_box,
                    context.page_bottom - current_position_y - height,
                    column_skip_stack, containing_block,
                    page_is_empty or first_probe_run, [], [], [],
                    discard=False, max_lines=None)
                if new_box is None:
                    # We didn't render anything, retry.
                    column_skip_stack = {0: None}
                    break
                column_skip_stack = resume_at

                in_flow_children = [
                    child for child in new_box.children
                    if child.is_in_normal_flow()]

                if in_flow_children:
                    # Get the empty space at the bottom of the column box
                    consumed_height = (
                        in_flow_children[-1].margin_height() +
                        in_flow_children[-1].position_y - current_position_y)
                    empty_space = height - consumed_height

                    # Get the minimum size needed to render the next box
                    next_box, _, _, _, _, _ = block_box_layout(
                        context, column_box,
                        context.page_bottom - box.content_box_y(),
                        column_skip_stack, containing_block, True, [], [], [],
                        discard=False, max_lines=None)
                    for child in next_box.children:
                        if child.is_in_normal_flow():
                            next_box_size = child.margin_height()
                            break
                else:
                    consumed_height = empty_space = next_box_size = 0

                consumed_heights.append(consumed_height)

                # Append the size needed to render the next box in this
                # column.
                #
                # The next box size may be smaller than the empty space, for
                # example when the next box can't be separated from its own
                # next box. In this case we don't try to find the real value
                # and let the workaround below fix this for us.
                #
                # We also want to avoid very small values that may have been
                # introduced by rounding errors. As the workaround below at
                # least adds 1 pixel for each loop, we can ignore lost spaces
                # lower than 1px.
                if next_box_size - empty_space > 1:
                    lost_space = min(lost_space, next_box_size - empty_space)

                # Stop if we already rendered the whole content
                if resume_at is None:
                    break

            if forced_end_probing:
                break

            if first_probe_run:
                # This is the first loop through, we might bail here.
                if column_skip_stack or max(consumed_heights) > max_height:
                    # Even at maximum height, not everything fits. Stop now and
                    # let the columns continue on the next page.
                    stop_rendering = True
                    break
                else:
                    # Everything fit, start expanding columns at the average of
                    # the column heights.
                    height = sum(consumed_heights)
                    if style['column_fill'] == 'balance':
                        height /= count
            else:
                if column_skip_stack is None:
                    # We rendered the whole content, stop
                    break
                else:
                    if lost_space == inf:
                        # We didn't find the extra size needed to render a
                        # child in the previous column, increase height by the
                        # minimal value.
                        add_height = 1
                    else:
                        # Increase the column heights and render them again
                        add_height = lost_space

                    if height + add_height > max_height:
                        height = max_height
                        stop_rendering = True
                        break

                    height += add_height
            first_probe_run = False

        # TODO: check box.style['max']-height
        bottom_space = max(
            bottom_space, context.page_bottom - current_position_y - height)

        # Replace the current box children with columns
        i = 0
        max_column_height = 0
        columns = []
        while True:
            if i == count - 1:
                bottom_space = original_bottom_space
            column_box = create_column_box(column_children)
            column_box.position_y = current_position_y
            if style['direction'] == 'rtl':
                column_box.position_x += (
                    box.width - (i + 1) * width - i * style['column_gap'])
            else:
                column_box.position_x += i * (width + style['column_gap'])
            new_child, column_skip_stack, column_next_page, _, _, _ = (
                block_box_layout(
                    context, column_box, bottom_space, skip_stack,
                    containing_block, original_page_is_empty, absolute_boxes,
                    fixed_boxes, None, discard=False, max_lines=None))
            if new_child is None:
                break_page = True
                break
            next_page = column_next_page
            skip_stack = column_skip_stack
            columns.append(new_child)
            max_column_height = max(
                max_column_height, new_child.margin_height())
            if skip_stack is None:
                bottom_space = original_bottom_space
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

        skip_stack = None
        page_is_empty = False

        if stop_rendering:
            break

    if box.children and not new_children:
        # The box has children but none can be drawn, let's skip the whole box
        context.in_column = False
        return None, (0, None), {'break': 'any', 'page': None}, [], False

    # Set the height of box and the columns
    box.children = new_children
    current_position_y += collapse_margin(adjoining_margins)
    height = current_position_y - box.content_box_y()
    if box.height == 'auto':
        box.height = height
        height_difference = 0
    else:
        height_difference = box.height - height
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
            absolute_layout(
                context, absolute_box, box, fixed_boxes, bottom_space,
                skip_stack=None)

    if column_skip_stack:
        skip, = column_skip_stack.keys()
        skip_stack = {index + skip: column_skip_stack[skip]}
    elif break_page:
        skip_stack = {index: None}
    context.in_column = False
    return box, skip_stack, next_page, [], False
