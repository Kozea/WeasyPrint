# coding: utf-8
"""
    weasyprint.layout.flex
    ------------------------

    Layout for flex containers and flex-items.

    :copyright: Copyright 2017 Lucien Deleu and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from math import log10

from .percentages import resolve_percentages
from .preferred import max_content_width, min_content_width


def flex_layout(context, box, max_position_y, skip_stack, containing_block,
                device_size, page_is_empty, absolute_boxes, fixed_boxes):
    # Step 2
    if box.style.width != 'auto':
        available_main_space = box.style.width
    else:
        available_main_space = (
            containing_block.width - (box.margin_left - box.margin_right) -
            (box.padding_left - box.padding_right) -
            (box.border_left_width - box.border_right_width))

    if box.style.height != 'auto':
        available_cross_space = box.style.height
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

        # TODO: Step A
        # TODO: Step B
        # TODO: Step C

        # Step D is useless, as we never have infinite sizes on paged media

        # Step E
        if flex_basis == 'content':
            child.style.width = 'max-content'
        else:
            child.style.width = flex_basis

        # TODO: the flex base size shouldn't take care of min and max sizes
        if child.style.width == 'max-content':
            child.flex_base_size = max_content_width(context, box)
            child.hypothetical_main_size = max_content_width(context, box)
        elif child.style.width == 'min-content':
            child.flex_base_size = min_content_width(context, box)
            child.hypothetical_main_size = min_content_width(context, box)
        else:
            assert child.style.width.unit == 'px'
            child.flex_base_size = child.style.width.value
            child.hypothetical_main_size = child.style.width.value

    # TODO: Step 4

    # Step 5
    flex_lines = []
    flex_wrap = 'nowrap'

    if flex_wrap == 'nowrap':
        flex_lines.append([
            child for child in box.children
            if not child.is_flex_item])

    # Step 6

    for line in flex_lines:
        for child in line:
            child.grow = 0
            child.shrink = 1
        # Part 1
        hypothetical_main_size = sum(
            child.hypothetical_main_size for child in line)
        if hypothetical_main_size < available_main_space:
            flex_factor_type = 'grow'
        else:
            flex_factor_type = 'shrink'

        # Part 2
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
                child.frozen = False

        # Part 3
        initial_free_space = available_main_space
        for child in line:
            if child.frozen:
                initial_free_space -= child.target_main_size
            else:
                initial_free_space -= child.flex_base_size

        # Part 4
        while not all(child.frozen for child in line):
            unfrozen_factor_sum = 0
            remaining_free_space = available_main_space
            for child in line:
                if child.frozen:
                    remaining_free_space -= child.target_main_size
                else:
                    remaining_free_space -= child.flex_base_size
                    unfrozen_factor_sum += child.flex_factor
            if unfrozen_factor_sum < 1:
                initial_free_space *= unfrozen_factor_sum
            if (int(log10(initial_free_space)) <
                    int(log10(remaining_free_space))):
                remaining_free_space = initial_free_space
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
