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


@compute_dimensions.register(boxes.LineBox)
def line_dimensions(box):
    resolve_percentages(box)

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
