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

"""
Functions laying out the block boxes.

"""

from __future__ import division

from .inlines import get_new_lineboxes
from .markers import list_marker_layout
from .percentages import resolve_percentages
from ..css.values import get_single_keyword
from ..formatting_structure import boxes


def block_level_layout(box, max_position_y):
    """Lay out the block-level ``box``.

    :param max_position_y: the absolute vertical position (as in
                           ``some_box.position_y``) of the bottom of the
                           content box of the current page area.

    """
    if isinstance(box, boxes.BlockBox):
        return block_box_layout(box, max_position_y)
    elif isinstance(box, boxes.BlockLevelReplacedBox):
        return block_replaced_box_layout(box), True
    else:
        raise TypeError('Layout for %s not handled yet' % type(box).__name__)


def block_box_layout(box, max_position_y):
    """Lay out the block ``box``."""
    resolve_percentages(box)
    block_level_width(box)
    list_marker_layout(box)
    return block_level_height(box, max_position_y)


def block_replaced_box_layout(box):
    """Lay out the block :class:`boxes.ReplacedBox` ``box``."""
    assert isinstance(box, boxes.ReplacedBox)
    resolve_percentages(box)

    intrinsic_ratio = box.replacement.intrinsic_ratio()
    intrinsic_height = box.replacement.intrinsic_height()
    intrinsic_width = box.replacement.intrinsic_width()

    if box.width == 'auto':
        if intrinsic_width is not None:
            box.width = intrinsic_width
        elif intrinsic_height is not None and intrinsic_ratio is not None:
            box.width = intrinsic_ratio * intrinsic_height
        elif intrinsic_ratio is not None:
            block_level_width(box)
        else:
            raise NotImplementedError
            # Then the used value of 'width' becomes 300px. If 300px is too
            # wide to fit the device, UAs should use the width of the largest
            # rectangle that has a 2:1 ratio and fits the device instead.

    if box.height == 'auto' and box.width == 'auto':
        if intrinsic_height is not None:
            box.height = intrinsic_height
    elif intrinsic_ratio is not None and box.height == 'auto':
        box.height = box.width / intrinsic_ratio
    else:
        raise NotImplementedError
        # Then the used value of 'height' must be set to the height of
        # the largest rectangle that has a 2:1 ratio, has a height not
        # greater than 150px, and has a width not greater than the
        # device width.
    return box


def block_level_width(box):
    """Set the ``box`` width."""
    # 'cb' stands for 'containing block'
    cb_width = box.containing_block_size()[0]

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
        if get_single_keyword(box.parent.style.direction) == 'ltr':
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


def block_level_height(box, max_position_y):
    """Set the ``box`` height."""
    assert isinstance(box, boxes.BlockBox)

    if get_single_keyword(box.style.overflow) != 'visible':
        raise NotImplementedError

    if box.margin_top == 'auto':
        box.margin_top = 0
    if box.margin_bottom == 'auto':
        box.margin_bottom = 0

    position_x = box.content_box_x()
    position_y = box.content_box_y()
    initial_position_y = position_y

    new_box = box.copy()
    new_box.empty()
    while box.children:
        child = box.children.popleft()
        if not child.is_in_normal_flow():
            continue
        # TODO: collapse margins
        # See http://www.w3.org/TR/CSS21/visudet.html#normal-block
        child.position_x = position_x
        child.position_y = position_y
        if isinstance(child, boxes.LineBox):
            for line in get_new_lineboxes(child, max_position_y):
                new_box.add_child(line)
                position_y += line.height
            if child.children:
                box.children.appendleft(child)
                break
        else:
            new_child, finished = block_level_layout(child,
                max_position_y)
            new_position_y = position_y + new_child.margin_height()
            # TODO: find a way to break between blocks
#            if new_position_y <= max_position_y:
            new_box.add_child(new_child)
            position_y = new_position_y
#            else:
#                finished = False
            if not finished:
                box.children.appendleft(child)
                break

    if new_box.height == 'auto':
        new_box.height = position_y - initial_position_y

    # If there was a list marker, we kept it on `new_box`. Do not repeat on
    # `box` on the next page.
    box.outside_list_marker = None
    finished = not box.children
    return new_box, finished
