# coding: utf-8
"""
    weasyprint.layout.flex
    ------------------------

    Layout for flex containers and flex-items.

    :copyright: Copyright 2017 Lucien Deleu and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from math import log10

from . import blocks
from .percentages import resolve_percentages
from .preferred import max_content_width, min_content_width
from .tables import find_in_flow_baseline


class FlexLine(list):
    pass


def flex_layout(context, box, max_position_y, skip_stack, containing_block,
                device_size, page_is_empty, absolute_boxes, fixed_boxes):

    # Step 1 is done in formatting_structure.boxes

    # Step 2
    if box.style.width != 'auto':
        available_main_space = box.style.width.value
    else:
        available_main_space = (
            containing_block.width - (box.margin_left - box.margin_right) -
            (box.padding_left - box.padding_right) -
            (box.border_left_width - box.border_right_width))

    if box.style.height != 'auto':
        available_cross_space = box.style.height.value
    else:
        available_cross_space = (
            max_position_y - box.position_y -
            (box.margin_top - box.margin_bottom) -
            (box.padding_top - box.padding_bottom) -
            (box.border_top_width - box.border_bottom_width))

    # Step 3
    for child in box.children:
        if not child.is_flex_item:
            continue

        child.sytle = child.style.copy()
        resolve_percentages(box, containing_block)

        flex_basis = 'auto'

        # "If a value would resolve to auto for width, it instead resolves
        # to content for flex-basis."
        # See https://www.w3.org/TR/css-flexbox-1/#propdef-flex-basis
        if flex_basis == 'auto':
            flex_basis = 'content'

        # TODO: Step 3.A
        # TODO: Step 3.B
        # TODO: Step 3.C

        # Step 3.D is useless, as we never have infinite sizes on paged media

        # Step 3.E
        if flex_basis == 'content':
            child.style.width = 'max-content'
        else:
            child.style.width = flex_basis

        # TODO: the flex base size shouldn't take care of min and max sizes
        # TODO: don't set style width to auto, support *-content values instead
        if child.style.width == 'max-content':
            child.style.width = 'auto'
            child.flex_base_size = max_content_width(context, child)
            child.hypothetical_main_size = max_content_width(context, child)
        elif child.style.width == 'min-content':
            child.style.width = 'auto'
            child.flex_base_size = min_content_width(context, child)
            child.hypothetical_main_size = min_content_width(context, child)
        else:
            assert child.style.width.unit == 'px'
            child.flex_base_size = child.style.width.value
            child.hypothetical_main_size = child.style.width.value

    # Step 4
    blocks.block_level_width(box, containing_block)

    # Step 5
    flex_lines = []

    line = []
    line_width = 0
    for child in box.children:
        if not child.is_flex_item:
            continue
        line_width += child.hypothetical_main_size
        if box.style['flex_wrap'] == 'nowrap' or line_width > box.width:
            if line:
                flex_lines.append(FlexLine(line))
                line = [child]
            else:
                line.append(child)
                flex_lines.append(FlexLine(line))
                line = []
        else:
            line.append(child)
    if line:
        flex_lines.append(FlexLine(line))

    # Step 6
    for line in flex_lines:
        for child in line:
            child.grow = 0
            child.shrink = 1

        # Step 6.1
        hypothetical_main_size = sum(
            child.hypothetical_main_size for child in line)
        if hypothetical_main_size < available_main_space:
            flex_factor_type = 'grow'
        else:
            flex_factor_type = 'shrink'

        # Step 6.2
        for child in line:
            child.flex_factor = (
                child.grow if flex_factor_type == 'grow' else child.shrink)
            if (child.flex_factor == 0 or
                    (flex_factor_type == 'grow' and
                        child.flex_base_size > child.hypothetical_main_size) or
                    (flex_factor_type == 'shrink' and
                        child.flex_base_size < child.hypothetical_main_size)):
                child.target_main_size = child.hypothetical_main_size
                child.frozen = True
            else:
                # TODO: do we need to set target main size here?
                child.target_main_size = child.hypothetical_main_size
                child.frozen = False

        # Step 6.3
        initial_free_space = available_main_space
        for child in line:
            if child.frozen:
                initial_free_space -= child.target_main_size
            else:
                initial_free_space -= child.flex_base_size

        # Step 6.4
        while not all(child.frozen for child in line):
            unfrozen_factor_sum = 0
            remaining_free_space = available_main_space

            # Step 6.4.b
            for child in line:
                if child.frozen:
                    remaining_free_space -= child.target_main_size
                else:
                    remaining_free_space -= child.flex_base_size
                    unfrozen_factor_sum += child.flex_factor

            if unfrozen_factor_sum < 1:
                initial_free_space *= unfrozen_factor_sum

            initial_magnitude = (
                int(log10(initial_free_space)) if initial_free_space > 0
                else -float('inf'))
            remaining_magnitude = (
                int(log10(remaining_free_space)) if initial_free_space > 0
                else -float('inf'))
            if initial_magnitude < remaining_magnitude:
                remaining_free_space = initial_free_space

            # Step 6.4.c
            if remaining_free_space == 0:
                pass
            elif flex_factor_type == 'grow':
                for child in line:
                    if not child.frozen:
                        ratio = child.grow / unfrozen_factor_sum
                        child.target_main_size = (
                            child.flex_base_size +
                            remaining_free_space * ratio)
            elif flex_factor_type == 'shrink':
                for child in line:
                    if not child.frozen:
                        scaled_flex_shrink_factor = (
                            child.flex_base_size * child.shrink)
                        ratio = scaled_flex_shrink_factor / unfrozen_factor_sum
                        child.target_main_size = (
                            child.flex_base_size - remaining_free_space * ratio
                        )

            # Step 6.4.d
            # TODO: First part of this step is useless until 3.E is correct
            for child in line:
                child.adjustment = 0
                if not child.frozen and child.target_main_size < 0:
                    child.adjustment = -child.target_main_size
                    child.target_main_size = 0

            # Step 6.4.e
            adjustments = sum(child.adjustment for child in line)
            for child in line:
                if adjustments == 0:
                    child.frozen = True
                elif adjustments > 0 and child.adjustment > 0:
                    child.frozen = True
                elif adjustments < 0 and child.adjustment < 0:
                    child.frozen = True
                # Step 6.5
                child.width = child.target_main_size

    # Step 7
    for line in flex_lines:
        for child in line:
            child.position_x = box.position_x
            child.position_y = box.position_y
    flex_lines = [FlexLine(
        blocks.block_level_layout(
            context, child, max_position_y, skip_stack, box, device_size,
            page_is_empty, absolute_boxes, fixed_boxes,
            adjoining_margins=[])[0]
        for child in line) for line in flex_lines]

    # Step 8
    flex_direction = 'row'
    if len(flex_lines) == 1 and box.height != 'auto':
        flex_lines[0].height = box.height
    else:
        for line in flex_lines:
            collected_items = []
            not_collected_items = []
            for child in line:
                align_self = 'baseline'
                if (flex_direction == 'row' and
                        align_self == 'baseline' and
                        child.margin_top != 'auto' and
                        child.margin_bottom != 'auto'):
                    collected_items.append(child)
                else:
                    not_collected_items.append(child)
            cross_start_distance = 0
            cross_end_distance = 0
            for child in collected_items:
                baseline = find_in_flow_baseline(child) or 0
                cross_start_distance = max(cross_start_distance, baseline)
                cross_end_distance = max(
                    cross_end_distance, child.margin_height() - baseline)
            collected_height = cross_start_distance + cross_end_distance
            non_collected_height = 0
            if not_collected_items:
                non_collected_height = max(
                    child.margin_height() for child in not_collected_items)
            line.height = max(collected_height, non_collected_height)
        # TODO: handle min/max height for single-line containers

    # TODO: Step 9
    # TODO: Step 10

    # Step 11

    for line in flex_lines:
        line.align_items = 'stretch'
        for child in line:
            child.align_self = 'auto'
            if child.align_self == 'auto':
                child.align_self = 'stretch'

            if child.align_self == 'stretch' and child.style.height == 'auto':
                if 'auto' not in (child.margin_top, child.margin_bottom):
                    child.height = line.height
                    # TODO: redo layout
            # else: Cross size has been set by step 7

    # Step 12

    free_space = available_main_space - sum(
        child.width for line in flex_lines for child in line)

    if free_space:
        margins = 0
        for line in flex_lines:
            for child in line:
                if child.margin_left == 'auto':
                    margins += 1
                if child.margin_right == 'auto':
                    margins += 1
        if margins:
            free_space /= margins
        else:
            free_space = 0

    for line in flex_lines:
        position_x = box.position_x
        for child in line:
            if child.margin_left == 'auto':
                child.margin_left = free_space
            if child.margin_right == 'auto':
                child.margin_right = free_space
            child.position_x = position_x
            position_x += child.margin_width()

    # TODO: align according to justify-content

    # Step 13

    for line in flex_lines:
        for child in line:
            auto_margins = sum([
                margin == 'auto' for margin in (
                    child.margin_top, child.margin_bottom)])
            if auto_margins:
                # TODO: take care of margins insead of using margin height
                extra_height = available_cross_space - child.margin_height()
                if extra_height > 0:
                    extra_height /= auto_margins
                    if child.margin_top == 'auto':
                        child.margin_top = extra_height
                    if child.margin_bottom == 'auto':
                        child.margin_bottom = extra_height
                else:
                    if child.margin_top == 'auto':
                        child.margin_top = 0
                    child.margin_bottom = extra_height

    # TODO: Step 14

    # Step 15

    if box.style.height == 'auto':
        # TODO: handle min-max
        box.height = sum(line.height for line in flex_lines)

    # TODO: Step 16

    position_y = box.position_y
    for line in flex_lines:
        for child in line:
            child.position_y = position_y
        position_y += line.height

    box.children = [
        blocks.block_container_layout(
            context, child, max_position_y, skip_stack, device_size,
            page_is_empty, absolute_boxes, fixed_boxes)[0]
        for line in flex_lines for child in line if child.is_flex_item]

    # TODO: check these returned values
    return box, None, {'break': 'any', 'page': None}, [], False
