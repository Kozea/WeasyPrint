# coding: utf-8
"""
    weasyprint.layout.flex
    ------------------------

    Layout for flex containers and flex-items.

    :copyright: Copyright 2017 Lucien Deleu and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from .preferred import min_max, max_content_width


def flex_layout(context, box, max_position_y, skip_stack, containing_block,
                device_size, page_is_empty, absolute_boxes, fixed_boxes):
    # Step 2
    if box.style.width != 'auto':
        available_main_space = box.style.width
    else:
        available_main_space = (
            containing_block.width - (box.margin_left - box.margin_right) -
            (box.padding_left - box.padding_right) -
            (box.border_left_width - box.border_right_width)
        )

    if box.style.height != 'auto':
        available_cross_space = box.style.height
    else:
        available_cross_space = (
            max_position_y - box.position_y -
            (box.margin_top - box.margin_bottom) -
            (box.padding_top - box.padding_bottom) -
            (box.border_top_width - box.border_bottom_width)
        )

    # Step 3
    for child in box.children:
        if child.is_flex_item:
            flex_basis = 'auto'
            # TODO: Step A
            # TODO Step B
            # TODO Step C
            # TODO Step D
            if flex_basis == 'auto':
                flex_basis = 'content'
            if flex_basis == 'content':
                flex_basis = max_content_width(context, child)
            # Step E
            main_size = flex_basis
            flex_base_size = main_size
            hypothetical_main_size = min_max(child, flex_base_size)
