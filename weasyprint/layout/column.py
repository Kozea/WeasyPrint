"""Layout for columns."""

from math import floor, inf

from .absolute import absolute_layout
from .percent import percentage, resolve_percentages


def columns_layout(context, box, bottom_space, skip_stack, containing_block,
                   page_is_empty, absolute_boxes, fixed_boxes, adjoining_margins,
                   first_letter_style, first_line_style):
    """Lay out a multi-column ``box``."""
    from .block import (  # isort:skip
        block_box_layout, block_level_layout, block_level_width,
        collapse_margin, remove_placeholders)

    style = box.style
    width = style['column_width']
    count = style['column_count']
    height = style['height']
    original_bottom_space = bottom_space
    context.in_column = True

    if style['position'] == 'relative':
        # New containing block, use a new absolute list
        absolute_boxes = []

    box = box.copy_with_children(box.children)
    box.position_y += collapse_margin(adjoining_margins)

    # Set height if defined
    if height != 'auto' and height.unit != '%':
        assert height.unit.lower() == 'px'
        height_defined = True
        empty_space = context.page_bottom - box.content_box_y() - height.value
        bottom_space = max(bottom_space, empty_space)
    else:
        height_defined = False

    # TODO: the columns container width can be unknown if the containing block
    # needs the size of this block to know its own size
    block_level_width(box, containing_block)

    if style['column_gap'] == 'normal':
        # 1em because in column context
        gap = style['font_size']
    else:
        gap = percentage(style['column_gap'], box.style, box.width)

    # Define the number of columns and their widths
    if width == 'auto' and count != 'auto':
        width = max(0, box.width - (count - 1) * gap) / count
    elif width != 'auto' and count == 'auto':
        count = max(1, floor((box.width + gap) / (width + gap)))
        width = (box.width + gap) / count - gap
    else:  # overconstrained, with width != 'auto' and count != 'auto'
        count = max(1, min(count, floor((box.width + gap) / (width + gap))))
        width = (box.width + gap) / count - gap

    # Handle column-span property with the following structure:
    # columns_and_blocks = [
    #     [column_child_1, column_child_2],
    #     spanning_block,
    #     …
    # ]
    columns_and_blocks = []
    column_children = []
    skip, = skip_stack.keys() if skip_stack else (0,)
    for i, child in enumerate(box.children[skip:], start=skip):
        span = child.style['column_span']
        full_span = (
            span == 'all' or (isinstance(span, int) and span >= count))
        partial_span = (
            isinstance(span, int) and 1 < span < count and i == skip and
            not columns_and_blocks and not column_children)
        if full_span:
            if column_children:
                columns_and_blocks.append(
                    (i - len(column_children), column_children))
            columns_and_blocks.append((i, child.copy()))
            column_children = []
            continue
        if partial_span:
            # Integer column spans are underspecified in Multicol Level 2.
            # Keep the first implementation deliberately narrow: only a
            # leading direct child can reserve a subset of the columns.
            columns_and_blocks.append((i, (span, child.copy())))
            continue
        column_children.append(child.copy())
    if column_children:
        columns_and_blocks.append(
            (i + 1 - len(column_children), column_children))

    if skip_stack:
        skip_stack = {0: skip_stack[skip]}

    if not box.children:
        next_page = {'break': 'any', 'page': None}
        skip_stack = None

    # Find height and balance.
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
    last_loop = False
    break_page = False
    footnote_area_heights = [
        0 if context.current_footnote_area.height == 'auto'
        else context.current_footnote_area.margin_height()]
    last_footnotes_height = 0
    pending_column_positions = None
    for index, column_children_or_block in columns_and_blocks:
        if not isinstance(column_children_or_block, list):
            # We have a spanning block, we display it like other blocks
            block_start_y = current_position_y
            partial_span = isinstance(column_children_or_block, tuple)
            if partial_span:
                span, block = column_children_or_block
                span_width = span * width + (span - 1) * gap
                block_containing_block = box.copy()
                block_containing_block.width = span_width
                resolve_percentages(block, block_containing_block)
                if style['direction'] == 'rtl':
                    block.position_x = box.content_box_x() + box.width - span_width
                else:
                    block.position_x = box.content_box_x()
            else:
                block = column_children_or_block
                block_containing_block = containing_block
                resolve_percentages(block, block_containing_block)
                block.position_x = box.content_box_x()
            block.position_y = current_position_y
            new_child, resume_at, next_page, adjoining_margins, _, _ = (
                block_level_layout(
                    context, block, original_bottom_space, skip_stack,
                    block_containing_block, page_is_empty, absolute_boxes,
                    fixed_boxes, adjoining_margins, first_letter_style,
                    first_line_style))
            skip_stack = None
            if new_child is None:
                last_loop = True
                break_page = True
                break
            new_children.append(new_child)
            current_position_y = (
                new_child.border_height() + new_child.border_box_y())
            adjoining_margins.append(new_child.margin_bottom)
            if resume_at:
                last_loop = True
                break_page = True
                column_skip_stack = resume_at
                break
            page_is_empty = False
            if partial_span:
                # The spanner is an exclusion at the block-start edge of its
                # covered columns. Uncovered columns keep the original start,
                # so following content can continue there at full height.
                span_bottom = (
                    new_child.position_y + new_child.margin_height())
                pending_column_positions = (
                    [span_bottom] * span + [block_start_y] * (count - span))
                current_position_y = block_start_y
                adjoining_margins = []
                continue
            continue

        # We have a list of children that we have to balance between columns
        column_children = column_children_or_block

        # Find the total height available for the first run
        if pending_column_positions is None:
            current_position_y += collapse_margin(adjoining_margins)
            column_positions = [current_position_y] * count
        else:
            column_positions = pending_column_positions
            pending_column_positions = None
            current_position_y = min(column_positions)
        adjoining_margins = []
        max_heights = [
            context.page_bottom - position_y - original_bottom_space
            for position_y in column_positions]
        irregular_columns = len(set(column_positions)) > 1
        height = max_height = max_heights[0]

        # Try to render columns until the content fits, increase the column
        # height step by step
        column_skip_stack = skip_stack
        lost_space = inf
        original_excluded_shapes = context.excluded_shapes[:]
        original_page_is_empty = page_is_empty
        page_is_empty = stop_rendering = balancing = False
        while True:
            # Remove extra excluded shapes introduced during the previous loop
            while len(context.excluded_shapes) > len(original_excluded_shapes):
                context.excluded_shapes.pop()

            # Render the columns
            column_skip_stack = skip_stack
            consumed_heights = []
            new_boxes = []
            for i in range(count):
                # Render one column
                column_position_y = column_positions[i]
                column_height = max_heights[i] if irregular_columns else height
                column_box = _create_column_box(
                    box, containing_block, column_children, width,
                    column_position_y)
                new_box, resume_at, next_page, _, _, _ = block_box_layout(
                    context, column_box,
                    context.page_bottom - column_position_y - column_height,
                    column_skip_stack, containing_block,
                    page_is_empty or not balancing, [], [], [], first_letter_style,
                    first_line_style, discard=False, max_lines=None)
                if new_box is None:
                    # We didn't render anything, retry
                    column_skip_stack = {0: None}
                    break
                new_boxes.append(new_box)
                column_skip_stack = resume_at

                # Calculate consumed height, empty space and next box height
                in_flow_children = [
                    child for child in new_box.children
                    if child.is_in_normal_flow()]
                if in_flow_children:
                    # Get the empty space at the bottom of the column box
                    consumed_height = (
                        in_flow_children[-1].margin_height() +
                        in_flow_children[-1].position_y - column_position_y)
                    empty_space = column_height - consumed_height
                    consumed_height -= in_flow_children[-1].margin_bottom

                    # Get the minimum size needed to render the next box
                    next_box_height = 0
                    if column_skip_stack:
                        next_box = block_box_layout(
                            context, column_box, inf, column_skip_stack,
                            containing_block, True, [], [], [], first_letter_style,
                            first_line_style, discard=False, max_lines=None)[0]
                        for child in next_box.children:
                            if child.is_in_normal_flow():
                                next_box_height = child.margin_height()
                                break
                        remove_placeholders(context, [next_box], [], [])
                else:
                    consumed_height = empty_space = next_box_height = 0

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
                if next_box_height - empty_space > 1:
                    lost_space = min(lost_space, next_box_height - empty_space)

                # Stop if we already rendered the whole content
                if resume_at is None:
                    break

            # Remove placeholders but keep the current footnote area height
            last_footnotes_height = (
                0 if context.current_footnote_area.height == 'auto'
                else context.current_footnote_area.margin_height())
            remove_placeholders(context, new_boxes, [], [])

            if last_loop:
                break

            if irregular_columns:
                if last_footnotes_height not in footnote_area_heights:
                    # Keep every column's bottom edge aligned when footnotes
                    # reduce the page area available to the irregular row.
                    height_difference = (
                        last_footnotes_height - footnote_area_heights[-1])
                    max_heights = [
                        max_height - height_difference
                        for max_height in max_heights]
                    footnote_area_heights.append(last_footnotes_height)
                    continue
                if column_skip_stack is None:
                    break
                stop_rendering = True
                break

            if balancing:
                if column_skip_stack is None:
                    # We rendered the whole content, stop
                    break

                # Increase the column heights and render them again
                add_height = 1 if lost_space == inf else lost_space
                height += add_height

                if height > max_height:
                    # We reached max height, stop rendering
                    height = max_height
                    stop_rendering = True
                    break
            else:
                if last_footnotes_height not in footnote_area_heights:
                    # Footnotes have been rendered, try to re-render with the
                    # new footnote area height
                    height -= last_footnotes_height - footnote_area_heights[-1]
                    footnote_area_heights.append(last_footnotes_height)
                    continue

                everything_fits = (
                    not column_skip_stack and
                    max(consumed_heights) <= max_height)
                if everything_fits:
                    # Everything fits, start expanding columns at the average
                    # of the column heights
                    if (style['column_fill'] == 'balance' or
                            index < columns_and_blocks[-1][0]):
                        balancing = True
                        height = sum(consumed_heights) / count
                    else:
                        break
                else:
                    # Content overflows even at maximum height, stop now and
                    # let the columns continue on the next page
                    stop_rendering = True
                    break

        # TODO: check style['max']-height
        if irregular_columns:
            bottom_space = original_bottom_space
        else:
            bottom_space = max(
                bottom_space, context.page_bottom - current_position_y - height)

        # Replace the current box children with real columns
        i = 0
        max_column_height = 0
        columns = []
        column_heights = []
        while True:
            if i < count:
                column_position_y = column_positions[i]
                column_height = max_heights[i]
            else:
                # A constrained multicol container can create overflow columns
                # after its declared columns. They are not covered by a leading
                # partial spanner and therefore retain the full block size.
                column_position_y = min(column_positions)
                column_height = (
                    context.page_bottom - column_position_y -
                    original_bottom_space)
            column_box = _create_column_box(
                box, containing_block, column_children, width,
                column_position_y)
            if style['direction'] == 'rtl':
                column_box.position_x += box.width - (i + 1) * width - i * gap
            else:
                column_box.position_x += i * (width + gap)
            new_child, column_skip_stack, column_next_page, _, _, _ = (
                block_box_layout(
                    context, column_box,
                    original_bottom_space if irregular_columns else bottom_space,
                    skip_stack, containing_block,
                    original_page_is_empty, absolute_boxes, fixed_boxes, None,
                    first_letter_style, first_line_style, discard=False,
                    max_lines=None))
            if new_child is None:
                columns = []
                break_page = True
                break
            next_page = column_next_page
            skip_stack = column_skip_stack
            columns.append(new_child)
            column_heights.append(column_height)
            max_column_height = max(
                max_column_height, new_child.margin_height())
            if skip_stack is None:
                bottom_space = original_bottom_space
                break
            i += 1
            if i == count and not height_defined:
                # [If] a declaration that constrains the column height
                # (e.g., using height or max-height). In this case,
                # additional column boxes are created in the inline
                # direction.
                break

        # Update the current y position and set the columns’ height
        if irregular_columns:
            current_position_y = max(
                column.position_y + column_height
                for column, column_height in zip(columns, column_heights))
            for column, column_height in zip(columns, column_heights):
                column.height = column_height
                new_children.append(column)
        else:
            current_position_y += min(max_height, max_column_height)
            for column in columns:
                column.height = max_column_height
                new_children.append(column)

        skip_stack = None
        page_is_empty = False

        if stop_rendering:
            break

    # Report footnotes above the defined footnotes height
    _report_footnotes(context, footnote_area_heights[-1])

    if pending_column_positions is not None:
        # A partial spanner with no following column content still contributes
        # its own block size to an auto-height multicol container.
        current_position_y = max(pending_column_positions)

    if box.children and not new_children:
        # The box has children but none can be drawn, let's skip the whole box
        context.in_column = False
        return None, (0, None), {'break': 'any', 'page': None}, [], False

    # Set the height of the containing box
    box.children = new_children
    current_position_y += collapse_margin(adjoining_margins)
    height = current_position_y - box.content_box_y()
    if box.height == 'auto':
        box.height = height
        height_difference = 0
    else:
        height_difference = box.height - height

    # Update the latest columns’ height to respect min-height
    if box.min_height != 'auto' and box.min_height > box.height:
        height_difference += box.min_height - box.height
        box.height = box.min_height
    for child in new_children[::-1]:
        if child.is_column:
            child.height += height_difference
        else:
            break

    if style['position'] == 'relative':
        # New containing block, resolve the layout of the absolute descendants
        for absolute_box in absolute_boxes:
            absolute_layout(
                context, absolute_box, box, fixed_boxes, bottom_space,
                skip_stack=None)

    # Calculate skip stack
    if column_skip_stack:
        skip, = column_skip_stack.keys()
        skip_stack = {index + skip: column_skip_stack[skip]}
    elif break_page:
        skip_stack = {index: None}

    # Update page bottom according to the new footnotes
    if context.current_footnote_area.height != 'auto':
        context.page_bottom += footnote_area_heights[0]
        context.page_bottom -= context.current_footnote_area.margin_height()

    context.in_column = False
    return box, skip_stack, next_page, [], False


def _report_footnotes(context, footnotes_height):
    """Report footnotes above the defined footnotes height."""
    if not context.current_page_footnotes:
        return

    # Report and count footnotes
    reported_footnotes = 0
    while context.current_footnote_area.margin_height() > footnotes_height:
        context.report_footnote(context.current_page_footnotes[-1])
        reported_footnotes += 1

    # Revert reported footnotes, as they’ve been reported starting from the
    # last one
    if reported_footnotes >= 2:
        extra = context.reported_footnotes[-1:-reported_footnotes-1:-1]
        context.reported_footnotes[-reported_footnotes:] = extra


def _create_column_box(box, containing_block, children, width, position_y):
    """Create a column box including given children."""
    column_box = box.anonymous_from(box, children=children)
    resolve_percentages(column_box, containing_block)
    column_box.is_column = True
    column_box.width = width
    column_box.position_x = box.content_box_x()
    column_box.position_y = position_y
    return column_box
