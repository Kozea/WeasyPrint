# coding: utf8

#  WeasyPrint converts web documents (HTML, CSS, ...) to PDF.
#  Copyright (C) 2011  Simon Sapin
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.


from ..formatting_structure import boxes
from .percentages import resolve_percentages
from .inline_formatting_contex import breaking_linebox

def block_dimensions(box):
    resolve_percentages(box)
    block_level_width(box)
    block_level_height(box)


def block_level_width(box):
    # cb = containing block
    cb_width, cb_height = box.containing_block_size()

    # http://www.w3.org/TR/CSS21/visudet.html#blockwidth

    # These names are waaay too long
    margin_l = box.margin_left
    margin_r = box.margin_right
    padding_l = box.padding_left
    padding_r = box.padding_right
    border_l = box.border_left_width
    border_r = box.border_right_width
    width = box.width

    # Only margin-left, margin-right and width can be 'auto'.
    # We want:  width of containing block ==
    #               margin-left + border-left-width + padding-left + width
    #               + padding-right + border-right-width + margin-right

    paddings_plus_borders = padding_l + padding_r + border_l + border_r
    if box.width != 'auto':
        total = paddings_plus_borders + width
        if margin_l != 'auto':
            total += margin_l
        if margin_r != 'auto':
            total += margin_r
        if total > cb_width:
            if margin_l == 'auto':
                margin_l = box.margin_left = 0
            if margin_r == 'auto':
                margin_r = box.margin_right = 0
    if width != 'auto' and margin_l != 'auto' and margin_r != 'auto':
        # The equation is over-constrained
        margin_sum = cb_width - paddings_plus_borders - width
        # This is the direction of the containing block, but the containing
        # block for block-level boxes in normal flow is always the parent.
        # TODO: is it?
        if box.parent.style.direction == 'ltr':
            margin_r = box.margin_right = margin_sum - margin_l
        else:
            margin_l = box.margin_left = margin_sum - margin_r
    if width == 'auto':
        if margin_l == 'auto':
            margin_l = box.margin_left = 0
        if margin_r == 'auto':
            margin_r = box.margin_right = 0
        width = box.width = cb_width - (
            paddings_plus_borders + margin_l + margin_r)
    margin_sum = cb_width - paddings_plus_borders - width
    if margin_l == 'auto' and margin_r == 'auto':
        box.margin_left = margin_sum / 2.
        box.margin_right = margin_sum / 2.
    elif margin_l == 'auto' and margin_r != 'auto':
        box.margin_left = margin_sum - margin_r
    elif margin_l != 'auto' and margin_r == 'auto':
        box.margin_right = margin_sum - margin_l

    # Sanity check
    #TODO: Why we have this error ?
    # AssertionError
    # (777.7007874020001 == 793.700787402)
#    assert round(box.margin_width()*1000000000) == round(cb_width * 1000000000)
#    assert box.margin_width() == cb_width


def block_level_height(box):
    if box.style.overflow != 'visible':
        raise NotImplementedError

    if isinstance(box, boxes.ReplacedBox):
        raise NotImplementedError

    assert isinstance(box, boxes.BlockBox)

    if box.margin_top == 'auto':
        box.margin_top = 0
    if box.margin_bottom == 'auto':
        box.margin_bottom = 0

    from . import compute_dimensions  # Avoid circular import

    position_x = box.content_box_x()
    position_y = box.content_box_y()
    initial_position_y = position_y

    children = list(box.children)
    box.empty()
    for child in children:
        if not child.is_in_normal_flow():
            continue
        # TODO: collapse margins:
        # http://www.w3.org/TR/CSS21/visudet.html#normal-block
        child.position_x = position_x
        child.position_y = position_y
        compute_dimensions(child)
        if isinstance(child, boxes.LineBox):
            lines = breaking_linebox(child)
            for line in lines:
                box.add_child(line)
                position_y += line.height
        else:
            position_y += child.margin_height()
            box.add_child(child)

    if box.height == 'auto':
        box.height = position_y - initial_position_y

