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


from __future__ import division
from ..formatting_structure import boxes
from ..utils import MultiFunction
from .percentages import resolve_percentages
from . import block_formatting_context


# TODO: remove this if it is not needed?
@MultiFunction
def compute_dimensions(box):
    """
    Computes width, height and absolute position for all boxes in a box tree.
    """

compute_dimensions.register(boxes.BlockBox)(
    block_formatting_context.block_dimensions)

@compute_dimensions.register(boxes.ReplacedBox)
def replacedbox_dimensions(box):
    assert isinstance(box, boxes.ReplacedBox)
    resolve_percentages(box)
    # width
    if box.margin_left == 'auto':
        box.margin_left = 0
    if box.margin_right == 'auto':
        box.margin_right = 0

    intrinsic_ratio = box.replacement.intrinsic_ratio()
    intrinsic_height = box.replacement.intrinsic_height()
    intrinsic_width = box.replacement.intrinsic_width()

    if box.width == 'auto':
        if not intrinsic_width is None:
            box.width = intrinsic_width
        elif not intrinsic_height is None and not intrinsic_ratio is None:
            box.width = intrinsic_ratio * intrinsic_height
        elif not intrinsic_ratio is None:
            block_level_width(box)
        else:
            raise NotImplementedError
            # then the used value of 'width' becomes 300px. If 300px is too
            # wide to fit the device, UAs should use the width of the largest
            # rectangle that has a 2:1 ratio and fits the device instead.

    # height
    if box.margin_top == 'auto':
        box.margin_top = 0
    if box.margin_bottom == 'auto':
        box.margin_bottom = 0

    if box.height == 'auto' and box.width == 'auto':
        if not intrinsic_height is None:
            box.height = intrinsic_height
    elif intrinsic_ratio is not None and box.height == 'auto':
        box.height = box.width / intrinsic_ratio
    else:
        raise NotImplementedError
        # then the used value of 'height' must be set to the height of
        # the largest rectangle that has a 2:1 ratio, has a height not
        # greater than 150px, and has a width not greater than the
        # device width


@compute_dimensions.register(boxes.InlineBox)
def inlinebox_dimensions(box):
    resolve_percentages(box)

def page_dimensions(box):
    box.outer_height = box.style._weasy_page_height
    box.outer_width = box.style._weasy_page_width

    resolve_percentages(box)

    box.position_x = 0
    box.position_y = 0
    box.width = box.outer_width - box.horizontal_surroundings()
    box.height = box.outer_height - box.vertical_surroundings()

    box.root_box.width = box.width
    box.root_box.height = box.height
    box.root_box.outer_height = box.outer_height
    box.root_box.outer_width = box.outer_width

    box.root_box.position_x = box.content_box_x()
    box.root_box.position_y = box.content_box_y()

    compute_dimensions(box.root_box)


def layout(document):
    """
    Do the layout for the whole document: line breaks, page breaks,
    absolute size and position for all boxes.
    """
    pages = []
    page = boxes.PageBox(document, document.formatting_structure, 1)
    page_dimensions(page)
    pages.append(page)

    # TODO: do page breaks, split boxes into multiple pages
    return pages

