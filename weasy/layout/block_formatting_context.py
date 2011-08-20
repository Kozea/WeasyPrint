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


import sys

from ..css.values import get_single_keyword
from ..formatting_structure import boxes
from .. import text
from .percentages import resolve_percentages
from .inline_formatting_context import get_new_lineboxes

def block_dimensions(box):
    resolve_percentages(box)
    block_level_width(box)
    block_level_height(box)
    list_marker_layout(box)


def list_marker_layout(box):
    # List markers can be either 'inside' or 'outside'.
    # Inside markers are layed out just like normal inline content, but
    # outside markers need specific layout.
    # TODO: implement outside markers in terms of absolute positioning,
    # see CSS3 lists.
    marker_box = getattr(box, 'outside_list_marker', None)
    if marker_box:
        text_fragment = text.TextFragment.from_textbox(marker_box)
        marker_box.width, marker_box.height = text_fragment.get_size()

        # Align the top of the marker box with the top of its list-item’s
        # content-box.
        # TODO: align the baselines of the first lines instead?
        marker_box.position_y = box.content_box_y()
        # ... and its right with the left of its list-item’s padding box.
        # (Swap left and right for right-to-left text.)
        marker_box.position_x = box.padding_box_x()
        direction = get_single_keyword(box.style.direction)
        if direction == 'ltr':
            marker_box.position_x -=  marker_box.width
        else:
            marker_box.position_x += box.padding_width()


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


def block_level_height(box):
    if get_single_keyword(box.style.overflow) != 'visible':
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
        if isinstance(child, boxes.LineBox):
            for line in get_new_lineboxes(child):
                box.add_child(line)
                position_y += line.height
        else:
            compute_dimensions(child)
            position_y += child.margin_height()
            box.add_child(child)

    if box.height == 'auto':
        box.height = position_y - initial_position_y
