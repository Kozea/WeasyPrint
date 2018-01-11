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

from ..css.properties import Dimension
from .percentages import resolve_percentages
from .preferred import max_content_width, min_content_width
from .tables import find_in_flow_baseline


class FlexLine(list):
    pass


def flex_layout(context, box, max_position_y, skip_stack, containing_block,
                device_size, page_is_empty, absolute_boxes, fixed_boxes):
    # Avoid a circular import
    from . import blocks

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

        flex_basis = child.style['flex_basis']

        # "If a value would resolve to auto for width, it instead resolves
        # to content for flex-basis."
        # See https://www.w3.org/TR/css-flexbox-1/#propdef-flex-basis
        if flex_basis == 'auto':
            if child.style['width'] == 'auto':
                flex_basis = 'content'
            else:
                flex_basis = child.style['width']

        # Step 3.A
        # TODO: handle percentages
        if flex_basis != 'content':
            assert flex_basis.unit == 'px'
            child.flex_base_size = flex_basis.value

        # TODO: Step 3.B
        # TODO: Step 3.C

        # Step 3.D is useless, as we never have infinite sizes on paged media

        # Step 3.E
        else:
            if flex_basis == 'content':
                child.style['width'] = 'max-content'
            else:
                child.style['width'] = flex_basis

            # TODO: don't set style width, support *-content values instead
            if child.style['width'] == 'max-content':
                child.style['width'] = 'auto'
                child.flex_base_size = max_content_width(context, child)
            elif child.style['width'] == 'min-content':
                child.style['width'] = 'auto'
                child.flex_base_size = min_content_width(context, child)
            else:
                assert child.style['width'].unit == 'px'
                child.flex_base_size = child.style['width'].value

        # TODO: the flex base size shouldn't take care of min and max sizes
        child.hypothetical_main_size = child.flex_base_size

    # Step 4
    # TODO: don't use block_level_width, see TODO in build.flex_children.
    blocks.block_level_width(box, containing_block)

    # Step 5
    flex_lines = []

    line = []
    line_width = 0
    for child in sorted(box.children, key=lambda item: item.style['order']):
        if not child.is_flex_item:
            continue
        line_width += child.hypothetical_main_size
        if box.style['flex_wrap'] != 'nowrap' and line_width > box.width:
            if line:
                flex_lines.append(FlexLine(line))
                line = [child]
            else:
                line.append(child)
                flex_lines.append(FlexLine(line))
                line = []
            line_width = 0
        else:
            line.append(child)
    if line:
        flex_lines.append(FlexLine(line))

    # TODO: handle *-reverse using the terminology from the specification
    if box.style['flex_wrap'] == 'wrap-reverse':
        flex_lines.reverse()
    if box.style['flex_direction'].endswith('-reverse'):
        for line in flex_lines:
            line.reverse()

    # Step 6
    # See https://www.w3.org/TR/css-flexbox-1/#resolve-flexible-lengths
    for line in flex_lines:
        # Step 6.1
        hypothetical_main_size = sum(
            child.hypothetical_main_size for child in line)
        if hypothetical_main_size < available_main_space:
            flex_factor_type = 'grow'
        else:
            flex_factor_type = 'shrink'

        # Step 6.2
        for child in line:
            if flex_factor_type == 'grow':
                child.flex_factor = child.style['flex_grow']
            else:
                child.flex_factor = child.style['flex_shrink']
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
            if remaining_free_space != 0:
                scaled_flex_shrink_factors_sum = 0
                for child in line:
                    if not child.frozen:
                        child.scaled_flex_shrink_factor = (
                            child.flex_base_size * child.style['flex_shrink'])
                        scaled_flex_shrink_factors_sum += (
                            child.scaled_flex_shrink_factor)
                for child in line:
                    if not child.frozen:
                        if flex_factor_type == 'grow':
                            ratio = (
                                child.style['flex_grow'] /
                                scaled_flex_shrink_factors_sum)
                            child.target_main_size = (
                                child.flex_base_size +
                                remaining_free_space * ratio)
                        elif flex_factor_type == 'shrink':
                            ratio = (
                                child.scaled_flex_shrink_factor /
                                scaled_flex_shrink_factors_sum)
                            child.target_main_size = (
                                child.flex_base_size + remaining_free_space *
                                ratio)

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
        # TODO: don't set style width, find a way to avoid width
        # re-calculation in Step 7
        for child in line:
            child.style['width'] = Dimension(child.target_main_size, 'px')

    # Step 7
    for line in flex_lines:
        for child in line:
            child.position_x = box.content_box_x()
            child.position_y = box.content_box_y()
    # TODO: don't use block_level_layout, see TODOs in Step 6.5 and
    # build.flex_children.
    flex_lines = [FlexLine(
        blocks.block_level_layout(
            context, child, max_position_y, skip_stack, box, device_size,
            page_is_empty, absolute_boxes, fixed_boxes,
            adjoining_margins=[])[0]
        for child in line) for line in flex_lines]
    # TODO: Handle breaks, skip_stack and resume_at instead of excluding Nones
    flex_lines = [
        FlexLine([child for child in line if child is not None])
        for line in flex_lines]
    flex_lines = [line for line in flex_lines if line]

    # Step 8
    if len(flex_lines) == 1 and box.height != 'auto':
        flex_lines[0].height = box.height
    else:
        for line in flex_lines:
            collected_items = []
            not_collected_items = []
            for child in line:
                align_self = 'baseline'
                if (box.style['flex_direction'] == 'row' and
                        align_self == 'baseline' and
                        child.margin_top != 'auto' and
                        child.margin_bottom != 'auto'):
                    collected_items.append(child)
                else:
                    not_collected_items.append(child)
            cross_start_distance = 0
            cross_end_distance = 0
            for child in collected_items:
                baseline = find_in_flow_baseline(child)
                if baseline is None:
                    baseline = 0
                else:
                    baseline -= child.position_y
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
        for child in line:
            align_self = child.style['align_self']
            if align_self == 'auto':
                align_self = box.style['align_items']
            if align_self == 'stretch' and child.style['height'] == 'auto':
                if 'auto' not in (child.margin_top, child.margin_bottom):
                    child.height = line.height
                    # TODO: redo layout
            # else: Cross size has been set by step 7

    # Step 12
    free_space = available_main_space - sum(
        child.margin_width() for line in flex_lines for child in line)

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
            for line in flex_lines:
                for child in line:
                    if child.margin_left == 'auto':
                        child.margin_left = free_space
                    if child.margin_right == 'auto':
                        child.margin_right = free_space
            free_space = 0

    for line in flex_lines:
        # TODO: handle rtl
        position_x = box.content_box_x()
        if box.style['justify_content'] == 'flex-end':
            position_x += free_space
        elif box.style['justify_content'] == 'center':
            position_x += free_space / 2
        elif box.style['justify_content'] == 'space-around':
            position_x += free_space / len(line) / 2
        for child in line:
            child.position_x = position_x
            position_x += child.margin_width()
            if box.style['justify_content'] == 'space-around':
                position_x += free_space / len(line)
            elif box.style['justify_content'] == 'space-between':
                if len(line) > 1:
                    position_x += free_space / (len(line) - 1)

    # Step 13
    position_y = box.content_box_y()
    for line in flex_lines:
        lower_baseline = 0
        # TODO: don't duplicate this loop
        for child in line:
            align_self = child.style['align_self']
            if align_self == 'auto':
                align_self = box.style['align_items']
            if align_self == 'baseline':
                baseline = find_in_flow_baseline(child)
                if baseline is None:
                    # TODO: "If the item does not have a baseline in the
                    # necessary axis, then one is synthesized from the flex
                    # item’s border box."
                    child.baseline = 0
                else:
                    child.baseline = baseline - position_y
                lower_baseline = max(lower_baseline, child.baseline)
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
            else:
                # Step 14
                align_self = child.style['align_self']
                if align_self == 'auto':
                    align_self = box.style['align_items']
                child.position_y = position_y
                if align_self == 'flex-end':
                    child.position_y += line.height - child.margin_height()
                elif align_self == 'center':
                    child.position_y += (
                        line.height - child.margin_height()) / 2
                elif align_self == 'baseline':
                    child.position_y += lower_baseline - child.baseline
                elif align_self == 'stretch':
                    # TODO: don't set style width, find a way to avoid width
                    # re-calculation after Step 16
                    # TODO: take care of margins, borders and padding
                    child.style['height'] = Dimension(line.height, 'px')
        position_y += line.height

    # Step 15
    if box.style['height'] == 'auto':
        # TODO: handle min-max
        box.height = sum(line.height for line in flex_lines)

    # TODO: Step 16

    # TODO: don't use block_level_layout, see TODOs in Step 14 and
    # build.flex_children.
    box.children = [
        blocks.block_level_layout(
            context, child, max_position_y, skip_stack, box, device_size,
            page_is_empty, absolute_boxes, fixed_boxes,
            adjoining_margins=[])[0]
        for line in flex_lines for child in line if child.is_flex_item]

    # TODO: check these returned values
    return box, None, {'break': 'any', 'page': None}, [], False
