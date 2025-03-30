"""Layout for flex containers and flex-items."""

import sys
from math import inf, log10

from ..css.properties import Dimension
from ..formatting_structure import boxes
from . import percent
from .absolute import AbsolutePlaceholder, absolute_layout
from .preferred import max_content_width, min_content_width, min_max
from .table import find_in_flow_baseline, table_wrapper_width


class FlexLine(list):
    """Flex container line."""


def flex_layout(context, box, bottom_space, skip_stack, containing_block, page_is_empty,
                absolute_boxes, fixed_boxes, discard):
    from . import block

    # TODO: merge this with block_container_layout.
    context.create_flex_formatting_context()
    resume_at = None

    is_start = skip_stack is None
    box.remove_decoration(start=not is_start, end=False)

    discard |= box.style['continue'] == 'discard'
    draw_bottom_decoration = discard or box.style['box_decoration_break'] == 'clone'

    row_gap, column_gap = box.style['row_gap'], box.style['column_gap']

    if draw_bottom_decoration:
        bottom_space += box.padding_bottom + box.border_bottom_width + box.margin_bottom

    if box.style['position'] == 'relative':
        # New containing block, use a new absolute list
        absolute_boxes = []

    # References are to: https://www.w3.org/TR/css-flexbox-1/#layout-algorithm.

    # 1 Initial setup, done in formatting_structure.build.

    # 2 Determine the available main and cross space for the flex items.
    if box.style['flex_direction'].startswith('row'):
        main, cross = 'width', 'height'
    else:
        main, cross = 'height', 'width'

    margin_left = 0 if box.margin_left == 'auto' else box.margin_left
    margin_right = 0 if box.margin_right == 'auto' else box.margin_right

    # Define available main space.
    # TODO: min- and max-content not implemented.
    if getattr(box, main) != 'auto':
        # If that dimension of the flex container’s content box is a definite size…
        available_main_space = getattr(box, main)
    else:
        # Otherwise, subtract the flex container’s margin, border, and padding…
        if main == 'width':
            available_main_space = (
                containing_block.width -
                margin_left - margin_right -
                box.padding_left - box.padding_right -
                box.border_left_width - box.border_right_width)
        else:
            available_main_space = inf

    # Same as above for available cross space.
    # TODO: min- and max-content not implemented.
    if getattr(box, cross) != 'auto':
        available_cross_space = getattr(box, cross)
    else:
        if cross == 'width':
            available_cross_space = (
                containing_block.width -
                margin_left - margin_right -
                box.padding_left - box.padding_right -
                box.border_left_width - box.border_right_width)
        else:
            available_cross_space = inf

    # 3 Determine the flex base size and hypothetical main size of each item.
    parent_box = box.copy()
    percent.resolve_percentages(parent_box, containing_block)
    block.block_level_width(parent_box, containing_block)
    children = sorted(box.children, key=lambda item: item.style['order'])
    original_skip_stack = skip_stack
    if skip_stack is not None:
        (skip, skip_stack), = skip_stack.items()
        if box.style['flex_direction'].endswith('-reverse'):
            children = children[:skip + 1]
        else:
            children = children[skip:]
        skip_stack = skip_stack
    else:
        skip, skip_stack = 0, None
    child_skip_stack = skip_stack

    if row_gap == 'normal':
        row_gap = 0
    elif row_gap.unit == '%':
        if box.height == 'auto':
            row_gap = 0
        else:
            row_gap = row_gap.value / 100 * box.height
    else:
        row_gap = row_gap.value
    if column_gap == 'normal':
        column_gap = 0
    elif column_gap.unit == '%':
        if box.width == 'auto':
            column_gap = 0
        else:
            column_gap = column_gap.value / 100 * box.width
    else:
        column_gap = column_gap.value
    if main == 'width':
        main_gap, cross_gap = column_gap, row_gap
    else:
        main_gap, cross_gap = row_gap, column_gap

    position_x = (
        parent_box.position_x + parent_box.border_left_width + parent_box.padding_left)
    if parent_box.margin_left != 'auto':
        position_x += parent_box.margin_left
    position_y = (
        parent_box.position_y + parent_box.border_top_width + parent_box.padding_top)
    if parent_box.margin_top != 'auto':
        position_y += parent_box.margin_top
    for index, child in enumerate(children):
        if not child.is_flex_item:
            # Absolute child layout: create placeholder.
            if child.is_absolutely_positioned():
                child.position_x = position_x
                child.position_y = position_y
                new_child = placeholder = AbsolutePlaceholder(child)
                placeholder.index = index
                children[index] = placeholder
                if child.style['position'] == 'absolute':
                    absolute_boxes.append(placeholder)
                else:
                    fixed_boxes.append(placeholder)
            elif child.is_running():
                running_name = child.style['position'][1]
                page = context.current_page
                context.running_elements[running_name][page].append(child)
            continue
        # See https://www.w3.org/TR/css-flexbox-1/#min-size-auto.
        if main == 'width':
            child_containing_block = (available_main_space, parent_box.height)
        else:
            child_containing_block = (parent_box.width, available_main_space)
        percent.resolve_percentages(child, child_containing_block)
        if child.is_table_wrapper:
            table_wrapper_width(context, child, child_containing_block)
        child.position_x = position_x
        child.position_y = position_y
        if child.style['min_width'] == 'auto':
            specified_size = child.width
            new_child = child.copy()
            new_child.style = child.style.copy()
            new_child.style['width'] = 'auto'
            new_child.style['min_width'] = Dimension(0, 'px')
            new_child.style['max_width'] = Dimension(inf, 'px')
            content_size = min_content_width(context, new_child, outer=False)
            transferred_size = None
            if isinstance(child, boxes.ReplacedBox):
                image = child.replacement
                _, intrinsic_height, intrinsic_ratio = image.get_intrinsic_size(
                    child.style['image_resolution'], child.style['font_size'])
                if intrinsic_ratio and intrinsic_height:
                    transferred_size = intrinsic_height * intrinsic_ratio
            if specified_size != 'auto':
                child.min_width = min(specified_size, content_size)
            elif transferred_size is not None:
                child.min_width = min(transferred_size, content_size)
            else:
                child.min_width = content_size
        if child.style['min_height'] == 'auto':
            # TODO: avoid calling block_level_layout, write min_content_height instead.
            specified_size = child.height
            new_child = child.copy()
            new_child.style = child.style.copy()
            if new_child.style['width'] == 'auto':
                new_child_width = max_content_width(context, new_child)
                new_child.style['width'] = Dimension(new_child_width, 'px')
            new_child.style['height'] = 'auto'
            new_child.style['min_height'] = Dimension(0, 'px')
            new_child.style['max_height'] = Dimension(inf, 'px')
            new_child = block.block_level_layout(
                context, new_child, bottom_space, child_skip_stack, parent_box,
                page_is_empty)[0]
            content_size = new_child.height if new_child else 0
            transferred_size = None
            if isinstance(child, boxes.ReplacedBox):
                image = child.replacement
                intrinsic_width, _, intrinsic_ratio = image.get_intrinsic_size(
                    child.style['image_resolution'], child.style['font_size'])
                if intrinsic_ratio and intrinsic_width:
                    transferred_size = intrinsic_width / intrinsic_ratio
            if specified_size != 'auto':
                child.min_height = min(specified_size, content_size)
            elif transferred_size is not None:
                child.min_height = min(transferred_size, content_size)
            else:
                child.min_height = content_size

        if child.style['flex_basis'] == 'content':
            flex_basis = 'content'
        else:
            flex_basis = percent.percentage(
                child.style['flex_basis'], available_main_space)
            if flex_basis == 'auto':
                if (flex_basis := getattr(child, main)) == 'auto':
                    flex_basis = 'content'

        # 3.A If the item has a definite used flex basis…
        if flex_basis != 'content':
            child.flex_base_size = flex_basis
            if main == 'width':
                child.main_outer_extra = (
                    child.border_left_width + child.border_right_width +
                    child.padding_left + child.padding_right)
                if child.margin_left != 'auto':
                    child.main_outer_extra += child.margin_left
                if child.margin_right != 'auto':
                    child.main_outer_extra += child.margin_right
            else:
                child.main_outer_extra = (
                    child.border_top_width + child.border_bottom_width +
                    child.padding_top + child.padding_bottom)
                if child.margin_top != 'auto':
                    child.main_outer_extra += child.margin_top
                if child.margin_bottom != 'auto':
                    child.main_outer_extra += child.margin_bottom
        elif False:
            # TODO: 3.B If the flex item has an intrinsic aspect ratio…
            # TODO: 3.C If the used flex basis is 'content'…
            # TODO: 3.D Otherwise, if the used flex basis is 'content'…
            pass
        else:
            # 3.E Otherwise…
            if main == 'width':
                child.flex_base_size = max_content_width(context, child, outer=False)
                child.main_outer_extra = (
                    max_content_width(context, child) - child.flex_base_size)
            else:
                new_child = child.copy()
                new_child.width = inf
                new_child = block.block_level_layout(
                    context, new_child, bottom_space, child_skip_stack, parent_box,
                    page_is_empty, absolute_boxes, fixed_boxes)[0]
                if new_child:
                    child.flex_base_size = new_child.height
                    child.main_outer_extra = (
                        new_child.margin_height() - new_child.height)
                else:
                    child.flex_base_size = child.main_outer_extra = 0

        if main == 'width':
            position_x += child.flex_base_size + child.main_outer_extra
        else:
            position_y += child.flex_base_size + child.main_outer_extra

        min_size = getattr(child, f'min_{main}')
        max_size = getattr(child, f'max_{main}')
        child.hypothetical_main_size = max(
            min_size, min(child.flex_base_size, max_size))

        # Skip stack is only for the first child.
        child_skip_stack = None

    # 4 Determine the main size of the flex container using the rules of the formatting
    # context in which it participates.
    if main == 'width':
        block.block_level_width(box, containing_block)
    else:
        if box.height == 'auto':
            box.height = 0
            flex_items = (child for child in children if child.is_flex_item)
            for i, child in enumerate(flex_items):
                box.height += child.hypothetical_main_size + child.main_outer_extra
                if i:
                    box.height += main_gap
        box.height = max(box.min_height, min(box.height, box.max_height))

    # 5 If the flex container is single-line, collect all the flex items into a single
    # flex line.
    flex_lines = []
    line = []
    line_size = 0
    main_size = getattr(box, main)
    for i, child in enumerate(children, start=skip):
        if not child.is_flex_item:
            continue
        line_size += child.hypothetical_main_size + child.main_outer_extra
        if i > skip:
            line_size += main_gap
        if box.style['flex_wrap'] != 'nowrap' and line_size > main_size:
            if line:
                flex_lines.append(FlexLine(line))
                line = [(i, child)]
                line_size = child.hypothetical_main_size + child.main_outer_extra
            else:
                line.append((i, child))
                flex_lines.append(FlexLine(line))
                line = []
                line_size = 0
        else:
            line.append((i, child))
    if line:
        flex_lines.append(FlexLine(line))

    # TODO: Handle *-reverse using the terminology from the specification.
    if box.style['flex_wrap'] == 'wrap-reverse':
        flex_lines.reverse()
    if box.style['flex_direction'].endswith('-reverse'):
        for line in flex_lines:
            line.reverse()

    # 6 Resolve the flexible lengths of all the flex items to find their used main size.
    available_main_space = getattr(box, main)
    for line in flex_lines:
        # 9.7.1 Determine the used flex factor.
        hypothetical_main_size = sum(
            child.hypothetical_main_size + child.main_outer_extra
            for index, child in line)
        if hypothetical_main_size < available_main_space:
            flex_factor_type = 'grow'
        else:
            flex_factor_type = 'shrink'

        # 9.7.3 Size inflexible items.
        for index, child in line:
            if flex_factor_type == 'grow':
                child.flex_factor = child.style['flex_grow']
                flex_condition = child.flex_base_size > child.hypothetical_main_size
            else:
                child.flex_factor = child.style['flex_shrink']
                flex_condition = child.flex_base_size < child.hypothetical_main_size
            if child.flex_factor == 0 or flex_condition:
                child.target_main_size = child.hypothetical_main_size
                child.frozen = True
            else:
                child.frozen = False

        # 9.7.4 Calculate initial free space.
        initial_free_space = available_main_space
        for i, (index, child) in enumerate(line):
            if child.frozen:
                initial_free_space -= child.target_main_size + child.main_outer_extra
            else:
                initial_free_space -= child.flex_base_size + child.main_outer_extra
            if i:
                initial_free_space -= main_gap

        # 9.7.5.a Check for flexible items.
        while not all(child.frozen for index, child in line):
            unfrozen_factor_sum = 0
            remaining_free_space = available_main_space

            # 9.7.5.b Calculate the remaining free space.
            for i, (index, child) in enumerate(line):
                if child.frozen:
                    remaining_free_space -= (
                        child.target_main_size + child.main_outer_extra)
                else:
                    remaining_free_space -= (
                        child.flex_base_size + child.main_outer_extra)
                    unfrozen_factor_sum += child.flex_factor
                if i:
                    remaining_free_space -= main_gap

            if unfrozen_factor_sum < 1:
                initial_free_space *= unfrozen_factor_sum

            if initial_free_space == inf:
                initial_free_space = sys.maxsize
            if remaining_free_space == inf:
                remaining_free_space = sys.maxsize

            initial_magnitude = (
                int(log10(initial_free_space)) if initial_free_space > 0 else -inf)
            remaining_magnitude = (
                int(log10(remaining_free_space)) if remaining_free_space > 0 else -inf)
            if initial_magnitude < remaining_magnitude:
                remaining_free_space = initial_free_space

            # 9.7.5.c Distribute free space proportional to the flex factors.
            if remaining_free_space == 0:
                # If the remaining free space is zero: "Do nothing", but we at least set
                # the flex_base_size as target_main_size for next step.
                for index, child in line:
                    if not child.frozen:
                        child.target_main_size = child.flex_base_size
            else:
                scaled_flex_shrink_factors_sum = 0
                flex_grow_factors_sum = 0
                for index, child in line:
                    if not child.frozen:
                        child.scaled_flex_shrink_factor = (
                            child.flex_base_size * child.style['flex_shrink'])
                        scaled_flex_shrink_factors_sum += (
                            child.scaled_flex_shrink_factor)
                        flex_grow_factors_sum += child.style['flex_grow']
                for index, child in line:
                    if not child.frozen:
                        # If using the flex grow factor…
                        if flex_factor_type == 'grow':
                            ratio = child.style['flex_grow'] / flex_grow_factors_sum
                            child.target_main_size = (
                                child.flex_base_size + remaining_free_space * ratio)
                        # If using the flex shrink factor…
                        elif flex_factor_type == 'shrink':
                            if scaled_flex_shrink_factors_sum == 0:
                                child.target_main_size = child.flex_base_size
                            else:
                                ratio = (
                                    child.scaled_flex_shrink_factor /
                                    scaled_flex_shrink_factors_sum)
                                child.target_main_size = (
                                    child.flex_base_size + remaining_free_space * ratio)
                        child.target_main_size = min_max(child, child.target_main_size)

            # 9.7.5.d Fix min/max violations.
            for index, child in line:
                child.adjustment = 0
                if not child.frozen:
                    min_size = getattr(child, f'min_{main}')
                    max_size = getattr(child, f'max_{main}')
                    min_size = max(min_size , min(child.target_main_size, max_size))
                    if child.target_main_size < min_size:
                        child.adjustment = min_size - child.target_main_size
                        child.target_main_size = min_size

            # 9.7.5.e Freeze over-flexed items.
            adjustments = sum(child.adjustment for index, child in line)
            for index, child in line:
                # Zero: Freeze all items.
                if adjustments == 0:
                    child.frozen = True
                # Positive: Freeze all the items with min violations.
                elif adjustments > 0 and child.adjustment > 0:
                    child.frozen = True
                # Negative: Freeze all the items with max violations.
                elif adjustments < 0 and child.adjustment < 0:
                    child.frozen = True

        # 9.7.6 Set each item’s used main size to its target main size.
        for index, child in line:
            if main == 'width':
                child.width = child.target_main_size
            else:
                child.height = child.target_main_size

    # 7 Determine the hypothetical cross size of each item.
    # TODO: Handle breaks.
    new_flex_lines = []
    child_skip_stack = skip_stack
    for line in flex_lines:
        new_flex_line = FlexLine()
        for index, child in line:
            # TODO: Fix this value, see test_flex_item_auto_margin_cross.
            if child.margin_top == 'auto':
                child.margin_top = 0
            if child.margin_bottom == 'auto':
                child.margin_bottom = 0
            # TODO: Find another way than calling block_level_layout_switch.
            new_child = child.copy()
            new_child, _, _, adjoining_margins, _, _ = block.block_level_layout_switch(
                context, new_child, -inf, child_skip_stack, parent_box, page_is_empty,
                absolute_boxes, fixed_boxes, [], discard, None)
            child._baseline = find_in_flow_baseline(new_child) or 0
            if cross == 'height':
                child.height = new_child.height
                # As flex items margins never collapse (with other flex items or
                # with the flex container), we can add the adjoining margins to the
                # child bottom margin.
                child.margin_bottom += block.collapse_margin(adjoining_margins)
            else:
                if child.width == 'auto':
                    min_width = min_content_width(context, child, outer=False)
                    max_width = max_content_width(context, child, outer=False)
                    child.width = min(max(min_width, new_child.width), max_width)
                else:
                    child.width = new_child.width

            new_flex_line.append((index, child))

            # Skip stack is only for the first child.
            child_skip_stack = None

        if new_flex_line:
            new_flex_lines.append(new_flex_line)
    flex_lines = new_flex_lines

    # 8 Calculate the cross size of each flex line.
    cross_size = getattr(box, cross)
    if len(flex_lines) == 1 and cross_size != 'auto':
        # If the flex container is single-line…
        flex_lines[0].cross_size = cross_size
    else:
        # Otherwise, for each flex line…
        # 8.1 Collect all the flex items whose inline-axis is parallel to the main-axis…
        for line in flex_lines:
            collected_items = []
            not_collected_items = []
            for index, child in line:
                align_self = child.style['align_self']
                collect = (
                    box.style['flex_direction'].startswith('row') and
                    'baseline' in align_self and
                    'auto' not in (child.margin_top, child.margin_bottom))
                (collected_items if collect else not_collected_items).append(child)
            cross_start_distance = cross_end_distance = 0
            for child in collected_items:
                baseline = child._baseline - child.position_y
                cross_start_distance = max(cross_start_distance, baseline)
                cross_end_distance = max(
                    cross_end_distance, child.margin_height() - baseline)
            collected_cross_size = cross_start_distance + cross_end_distance
            non_collected_cross_size = 0
            # 8.2 Find the largest outer hypothetical cross size.
            if not_collected_items:
                non_collected_cross_size = -inf
                for child in not_collected_items:
                    if cross == 'height':
                        child_cross_size = child.border_height()
                        if child.margin_top != 'auto':
                            child_cross_size += child.margin_top
                        if child.margin_bottom != 'auto':
                            child_cross_size += child.margin_bottom
                    else:
                        child_cross_size = child.border_width()
                        if child.margin_left != 'auto':
                            child_cross_size += child.margin_left
                        if child.margin_right != 'auto':
                            child_cross_size += child.margin_right
                    non_collected_cross_size = max(
                        child_cross_size, non_collected_cross_size)
            # 8.3 Set the used cross-size of the flex line.
            line.cross_size = max(collected_cross_size, non_collected_cross_size)

    # 8.3 If the flex container is single-line…
    if len(flex_lines) == 1:
        line, = flex_lines
        min_cross_size = getattr(box, f'min_{cross}')
        if min_cross_size == 'auto':
            min_cross_size = -inf
        max_cross_size = getattr(box, f'max_{cross}')
        if max_cross_size == 'auto':
            max_cross_size = inf
        line.cross_size = max(min_cross_size, min(line.cross_size, max_cross_size))

    # 9 Handle 'align-content: stretch'.
    align_content = box.style['align_content']
    if 'normal' in align_content:
        align_content = ('stretch',)
    if 'stretch' in align_content:
        definite_cross_size = None
        if cross == 'height' and box.height != 'auto':
            definite_cross_size = box.height
        elif cross == 'width':
            if isinstance(box, boxes.FlexBox):
                if box.width == 'auto':
                    definite_cross_size = available_cross_space
                else:
                    definite_cross_size = box.width
        if definite_cross_size is not None:
            extra_cross_size = definite_cross_size
            extra_cross_size -= sum(line.cross_size for line in flex_lines)
            extra_cross_size -= (len(flex_lines) - 1) * cross_gap
            if extra_cross_size:
                for line in flex_lines:
                    line.cross_size += extra_cross_size / len(flex_lines)

    # TODO: 10 Collapse 'visibility: collapse' items.

    # 11 Determine the used cross size of each flex item.
    align_items = box.style['align_items']
    if 'normal' in align_items:
        align_items = ('stretch',)
    for line in flex_lines:
        for index, child in line:
            align_self = child.style['align_self']
            if 'normal' in align_self:
                align_self = ('stretch',)
            elif 'auto' in align_self:
                align_self = align_items
            if 'stretch' in align_self and child.style[cross] == 'auto':
                cross_margins = (
                    (child.margin_top, child.margin_bottom)
                    if cross == 'height'
                    else (child.margin_left, child.margin_right))
                if 'auto' not in cross_margins:
                    cross_size = line.cross_size
                    if cross == 'height':
                        cross_size -= (
                            child.margin_top + child.margin_bottom +
                            child.padding_top + child.padding_bottom +
                            child.border_top_width +
                            child.border_bottom_width)
                    else:
                        cross_size -= (
                            child.margin_left + child.margin_right +
                            child.padding_left + child.padding_right +
                            child.border_left_width +
                            child.border_right_width)
                    setattr(child, cross, cross_size)
            # else: Cross size has been set by step 7.

    # 12 Distribute any remaining free space.
    original_position_main = (
        box.content_box_x() if main == 'width'
        else box.content_box_y())
    justify_content = box.style['justify_content']
    if 'normal' in justify_content:
        justify_content = ('flex-start',)
    if box.style['flex_direction'].endswith('-reverse'):
        if 'flex-start' in justify_content:
            justify_content = ('flex-end',)
        elif 'flex-end' in justify_content:
            justify_content = ('flex-start',)
        elif 'start' in justify_content:
            justify_content = ('end',)
        elif 'end' in justify_content:
            justify_content = ('start',)

    for line in flex_lines:
        position_main = original_position_main
        if main == 'width':
            free_space = box.width
            for index, child in line:
                free_space -= child.border_width()
                if child.margin_left != 'auto':
                    free_space -= child.margin_left
                if child.margin_right != 'auto':
                    free_space -= child.margin_right
        else:
            free_space = box.height
            for index, child in line:
                free_space -= child.border_height()
                if child.margin_top != 'auto':
                    free_space -= child.margin_top
                if child.margin_bottom != 'auto':
                    free_space -= child.margin_bottom
        free_space -= (len(line) - 1) * main_gap

        # 12.1 If the remaining free space is positive…
        margins = 0
        for index, child in line:
            if main == 'width':
                if child.margin_left == 'auto':
                    margins += 1
                if child.margin_right == 'auto':
                    margins += 1
            else:
                if child.margin_top == 'auto':
                    margins += 1
                if child.margin_bottom == 'auto':
                    margins += 1
        if margins:
            free_space /= margins
            for index, child in line:
                if main == 'width':
                    if child.margin_left == 'auto':
                        child.margin_left = free_space
                    if child.margin_right == 'auto':
                        child.margin_right = free_space
                else:
                    if child.margin_top == 'auto':
                        child.margin_top = free_space
                    if child.margin_bottom == 'auto':
                        child.margin_bottom = free_space
            free_space = 0

        if box.style['direction'] == 'rtl' and main == 'width':
            free_space *= -1

        # 12.2 Align the items along the main-axis per justify-content.
        if {'end', 'flex-end', 'right'} & set(justify_content):
            position_main += free_space
        elif 'center' in justify_content:
            position_main += free_space / 2
        elif 'space-around' in justify_content:
            position_main += free_space / len(line) / 2
        elif 'space-evenly' in justify_content:
            position_main += free_space / (len(line) + 1)

        growths = sum(child.style['flex_grow'] for child in children)
        for i, (index, child) in enumerate(line):
            if i:
                position_main += main_gap
            if main == 'width':
                child.position_x = position_main
                if 'stretch' in justify_content and growths:
                    child.width += free_space * child.style['flex_grow'] / growths
            else:
                child.position_y = position_main
            margin_main = (
                child.margin_width() if main == 'width' else child.margin_height())
            if box.style['direction'] == 'rtl' and main == 'width':
                margin_main *= -1
            position_main += margin_main
            if 'space-around' in justify_content:
                position_main += free_space / len(line)
            elif 'space-between' in justify_content:
                if len(line) > 1:
                    position_main += free_space / (len(line) - 1)
            elif 'space-evenly' in justify_content:
                position_main += free_space / (len(line) + 1)

    # 13 Resolve cross-axis auto margins.
    if cross == 'width':
        # Make sure width/margins are no longer "auto", as we did not do it above in
        # step 4.
        block.block_level_width(box, containing_block)
    position_cross = box.content_box_y() if cross == 'height' else box.content_box_x()
    for line in flex_lines:
        line.lower_baseline = -inf
        # TODO: Don't duplicate this loop.
        for index, child in line:
            align_self = child.style['align_self']
            if 'auto' in align_self:
                align_self = align_items
            if 'baseline' in align_self and main == 'width':
                # TODO: handle vertical text.
                child.baseline = child._baseline - position_cross
                line.lower_baseline = max(line.lower_baseline, child.baseline)
        if line.lower_baseline == -inf:
            line.lower_baseline = line[0][1]._baseline if line else 0
        for index, child in line:
            cross_margins = (
                (child.margin_top, child.margin_bottom) if cross == 'height'
                else (child.margin_left, child.margin_right))
            auto_margins = sum([margin == 'auto' for margin in cross_margins])
            # If a flex item has auto cross-axis margins…
            if auto_margins:
                extra_cross = line.cross_size
                if cross == 'height':
                    extra_cross -= child.border_height()
                    if child.margin_top != 'auto':
                        extra_cross -= child.margin_top
                    if child.margin_bottom != 'auto':
                        extra_cross -= child.margin_bottom
                else:
                    extra_cross -= child.border_width()
                    if child.margin_left != 'auto':
                        extra_cross -= child.margin_left
                    if child.margin_right != 'auto':
                        extra_cross -= child.margin_right
                if extra_cross > 0:
                    # If its outer cross size is less than the cross size…
                    extra_cross /= auto_margins
                    if cross == 'height':
                        if child.margin_top == 'auto':
                            child.margin_top = extra_cross
                        if child.margin_bottom == 'auto':
                            child.margin_bottom = extra_cross
                    else:
                        if child.margin_left == 'auto':
                            child.margin_left = extra_cross
                        if child.margin_right == 'auto':
                            child.margin_right = extra_cross
                else:
                    # Otherwise…
                    if cross == 'height':
                        if child.margin_top == 'auto':
                            child.margin_top = 0
                        child.margin_bottom = extra_cross
                    else:
                        if child.margin_left == 'auto':
                            child.margin_left = 0
                        child.margin_right = extra_cross
            else:
                # 14 Align all flex items along the cross-axis.
                align_self = child.style['align_self']
                if 'normal' in align_self:
                    align_self = ('stretch',)
                elif 'auto' in align_self:
                    align_self = align_items
                position = 'position_y' if cross == 'height' else 'position_x'
                setattr(child, position, position_cross)
                if {'end', 'self-end', 'flex-end'} & set(align_self):
                    if cross == 'height':
                        child.position_y += line.cross_size - child.margin_height()
                    else:
                        child.position_x += line.cross_size - child.margin_width()
                elif 'center' in align_self:
                    if cross == 'height':
                        child.position_y += (
                            line.cross_size - child.margin_height()) / 2
                    else:
                        child.position_x += (line.cross_size - child.margin_width()) / 2
                elif 'baseline' in align_self:
                    if cross == 'height':
                        child.position_y += line.lower_baseline - child.baseline
                    else:
                        # TODO: Handle vertical text.
                        pass
                elif 'stretch' in align_self:
                    if child.style[cross] == 'auto':
                        if cross == 'height':
                            margins = child.margin_top + child.margin_bottom
                        else:
                            margins = child.margin_left + child.margin_right
                        if child.style['box_sizing'] == 'content-box':
                            if cross == 'height':
                                margins += (
                                    child.border_top_width + child.border_bottom_width +
                                    child.padding_top + child.padding_bottom)
                            else:
                                margins += (
                                    child.border_left_width + child.border_right_width +
                                    child.padding_left + child.padding_right)
                        # TODO: Don't set style width, find a way to avoid width
                        # re-calculation after 16.
                        child.style[cross] = Dimension(line.cross_size - margins, 'px')
        position_cross += line.cross_size

    # 15 Determine the flex container’s used cross size.
    # TODO: Use the updated algorithm.
    if getattr(box, cross) == 'auto':
        # Otherwise, use the sum of the flex lines' cross sizes…
        # TODO: Handle min-max.
        # TODO: What about align-content here?
        cross_size = sum(line.cross_size for line in flex_lines)
        cross_size += (len(flex_lines) - 1) * cross_gap
        setattr(box, cross, cross_size)

    if len(flex_lines) > 1:
        # 15 If the cross size property is a definite size, use that…
        extra_cross_size = getattr(box, cross)
        extra_cross_size -= sum(line.cross_size for line in flex_lines)
        extra_cross_size -= (len(flex_lines) - 1) * cross_gap
        # 16 Align all flex lines per align-content.
        cross_translate = 0
        direction = 'position_y' if cross == 'height' else 'position_x'
        for i, line in enumerate(flex_lines):
            flex_items = tuple(child for _, child in line if child.is_flex_item)
            if i:
                cross_translate += cross_gap
            for child in flex_items:
                current_value = getattr(child, direction) + cross_translate
                setattr(child, direction, current_value)
            if extra_cross_size == 0:
                continue
            for child in flex_items:
                if {'flex-end', 'end'} & set(align_content):
                    setattr(child, direction, current_value + extra_cross_size)
                elif 'center' in align_content:
                    setattr(child, direction, current_value + extra_cross_size / 2)
                elif 'space-around' in align_content:
                    setattr(
                        child, direction,
                        current_value + extra_cross_size / len(flex_lines) / 2)
                elif 'space-evenly' in align_content:
                    setattr(
                        child, direction,
                        current_value + extra_cross_size / (len(flex_lines) + 1))
            if 'space-between' in align_content:
                cross_translate += extra_cross_size / (len(flex_lines) - 1)
            elif 'space-around' in align_content:
                cross_translate += extra_cross_size / len(flex_lines)
            elif 'space-evenly' in align_content:
                cross_translate += extra_cross_size / (len(flex_lines) + 1)

    # Now we are no longer in the flex algorithm.
    box = box.copy_with_children(
        [child for child in children if child.is_absolutely_positioned()])
    child_skip_stack = skip_stack
    for line in flex_lines:
        for index, child in line:
            if child.is_flex_item:
                # TODO: Don't use block_level_layout_switch.
                new_child, child_resume_at = block.block_level_layout_switch(
                    context, child, bottom_space, child_skip_stack, box, page_is_empty,
                    absolute_boxes, fixed_boxes, adjoining_margins=[], discard=discard,
                    max_lines=None)[:2]
                if new_child is None:
                    if resume_at:
                        resume_index, = resume_at
                        resume_index -= 1
                    else:
                        resume_index = 0
                    resume_at = {resume_index + index: None}
                else:
                    page_is_empty = False
                    box.children.append(new_child)
                    if child_resume_at is not None:
                        if original_skip_stack:
                            first_level_skip, = original_skip_stack
                        else:
                            first_level_skip = 0
                        if resume_at:
                            resume_index, = resume_at
                            first_level_skip += resume_index
                        resume_at = {first_level_skip + index: child_resume_at}
                if resume_at:
                    break

            # Skip stack is only for the first child.
            child_skip_stack = None
        if resume_at:
            break

    if box.style['position'] == 'relative':
        # New containing block, resolve the layout of the absolute descendants.
        for absolute_box in absolute_boxes:
            absolute_layout(
                context, absolute_box, box, fixed_boxes, bottom_space, skip_stack=None)

    # TODO: Use real algorithm, see https://www.w3.org/TR/css-flexbox-1/#flex-baselines.
    if isinstance(box, boxes.InlineFlexBox):
        if main == 'width':  # and main text direction is horizontal
            box.baseline = flex_lines[0].lower_baseline if flex_lines else 0
        else:
            for child in box.children:
                if child.is_in_normal_flow():
                    box.baseline = find_in_flow_baseline(child) or 0
                    break
            else:
                box.baseline = 0

    box.remove_decoration(start=False, end=resume_at and not discard)

    context.finish_flex_formatting_context(box)

    # TODO: Check these returned values.
    return box, resume_at, {'break': 'any', 'page': None}, [], False
