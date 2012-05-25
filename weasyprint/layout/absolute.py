# coding: utf8
"""
    weasyprint.absolute
    -------------------

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from .percentages import resolve_percentages, resolve_position_percentages
from .preferred import shrink_to_fit
from .markers import list_marker_layout
from .tables import table_wrapper_width
from ..formatting_structure import boxes


class AbsolutePlaceholder(object):
    """Left where an absolutely-positioned box was taken out of the flow."""
    def __init__(self, box):
        # Work around the overloaded __setattr__
        object.__setattr__(self, '_box', box)
        object.__setattr__(self, '_layout_done', False)

    def set_laid_out_box(self, new_box):
        object.__setattr__(self, '_box', new_box)
        object.__setattr__(self, '_layout_done', True)

    def translate(self, dx=0, dy=0):
        if self._layout_done:
            self._box.translate(dx, dy)
        else:
            # Descendants do not have a position yet.
            self._box.position_x += dx
            self._box.position_y += dy

    # Pretend to be the box itself
    def __getattr__(self, name):
        return getattr(self._box, name)

    def __setattr__(self, name, value):
        setattr(self._box, name, value)


def absolute_layout(document, placeholder, containing_block):
    """Set the width of absolute positioned ``box``."""
    # TODO: avoid this (circular import)
    from .blocks import block_container_layout

    box = placeholder._box
    resolve_percentages(box, containing_block)
    resolve_position_percentages(box, containing_block)

    # These names are waaay too long
    margin_l = box.margin_left
    margin_r = box.margin_right
    margin_t = box.margin_top
    margin_b = box.margin_bottom
    padding_l = box.padding_left
    padding_r = box.padding_right
    padding_t = box.padding_top
    padding_b = box.padding_bottom
    border_l = box.border_left_width
    border_r = box.border_right_width
    border_t = box.border_top_width
    border_b = box.border_bottom_width
    width = box.width
    height = box.height
    left = box.left
    right = box.right
    top = box.top
    bottom = box.bottom

    cb = containing_block
    # TODO: handle inline boxes (point 10.1.4.1)
    # http://www.w3.org/TR/CSS2/visudet.html#containing-block-details
    if isinstance(box, boxes.PageBox):
        cb_x = cb.content_box_x()
        cb_y = cb.content_box_y()
        cb_width = cb.padding_width()
        cb_height = cb.padding_height()
    else:
        cb_x = cb.padding_box_x()
        cb_y = cb.padding_box_y()
        cb_width = cb.padding_width()
        cb_height = cb.padding_height()

    # http://www.w3.org/TR/CSS2/visudet.html#abs-replaced-width

    # TODO: handle bidi
    paddings_plus_borders_x = padding_l + padding_r + border_l + border_r
    translate_x = translate_y = 0
    translate_box_width = translate_box_height = False
    default_translate_x = cb_x - box.position_x
    if left == right == width == 'auto':
        if margin_l == 'auto':
            box.margin_left = 0
        if margin_r == 'auto':
            box.margin_right = 0
        available_width = cb_width
        box.width = shrink_to_fit(box, available_width)
    elif left != 'auto' and right != 'auto' and width != 'auto':
        width_for_margins = cb_width - (
            right + left + paddings_plus_borders_x)
        if margin_l == margin_r == 'auto':
            if width + paddings_plus_borders_x + right + left <= cb_width:
                box.margin_left = box.margin_right = width_for_margins / 2
            else:
                box.margin_left = 0
                box.margin_right = width_for_margins
        elif margin_l == 'auto':
            box.margin_left = width_for_margins
        elif margin_r == 'auto':
            box.margin_right = width_for_margins
        else:
            box.margin_right = width_for_margins
        translate_x = left + default_translate_x
    else:
        if margin_l == 'auto':
            box.margin_left = 0
        if margin_r == 'auto':
            box.margin_right = 0
        spacing = paddings_plus_borders_x + box.margin_left + box.margin_right
        if left == width == 'auto':
            box.width = shrink_to_fit(box, cb_width - spacing - right)
            translate_x = cb_width - right - spacing + default_translate_x
            translate_box_width = True
        elif left == right == 'auto':
            pass  # Keep the static position
        elif width == right == 'auto':
            box.width = shrink_to_fit(box, cb_width - spacing - left)
            translate_x = left + default_translate_x
        elif left == 'auto':
            translate_x = (
                cb_width + default_translate_x - right - spacing - width)
        elif width == 'auto':
            box.width = cb_width - right - left - spacing
            translate_x = left + default_translate_x
        elif right == 'auto':
            translate_x = left + default_translate_x

    # http://www.w3.org/TR/CSS2/visudet.html#abs-non-replaced-height

    paddings_plus_borders_y = padding_t + padding_b + border_t + border_b
    default_translate_y = cb_y - box.position_y
    if top == bottom == height == 'auto':
        pass  # Keep the static position
    elif top != 'auto' and bottom != 'auto' and height != 'auto':
        height_for_margins = cb_height - (
            top + bottom + paddings_plus_borders_y)
        if margin_t == margin_b == 'auto':
            box.margin_top = box.margin_bottom = height_for_margins / 2
        elif margin_t == 'auto':
            box.margin_top = height_for_margins
        elif margin_b == 'auto':
            box.margin_bottom = height_for_margins
        else:
            box.margin_bottom = height_for_margins
        translate_y = top + default_translate_y
    else:
        if margin_t == 'auto':
            box.margin_top = 0
        if margin_b == 'auto':
            box.margin_bottom = 0
        spacing = paddings_plus_borders_y + box.margin_top + box.margin_bottom
        if top == height == 'auto':
            translate_y = cb_height - bottom - spacing + default_translate_y
            translate_box_height = True
        elif top == bottom == 'auto':
            pass  # Keep the static position
        elif height == bottom == 'auto':
            translate_y = top + default_translate_y
        elif top == 'auto':
            translate_y = (
                cb_height + default_translate_y - bottom - spacing - height)
        elif height == 'auto':
            box.height = cb_height - bottom - top - spacing
            translate_y = top + default_translate_y
        elif bottom == 'auto':
            translate_y = top + default_translate_y

    # TODO: handle absolute tables
    assert isinstance(box, boxes.BlockBox)

    # This box is the containing block for absolute descendants.
    absolute_boxes = []

    if box.is_table_wrapper:
        table_wrapper_width(box, containing_block, absolute_boxes)

    # TODO: remove device_size everywhere else
    new_box, _, _, _, _ = block_container_layout(
        document, box, max_position_y=float('inf'), skip_stack=None,
        device_size=None, page_is_empty=False,
        absolute_boxes=absolute_boxes, adjoining_margins=None)

    list_marker_layout(document, new_box)

    for child_placeholder in absolute_boxes:
        absolute_layout(document, child_placeholder, new_box)

    if translate_box_width:
        translate_x -= new_box.width
    if translate_box_height:
        translate_y -= new_box.height
    new_box.translate(translate_x, translate_y)

    placeholder.set_laid_out_box(new_box)
