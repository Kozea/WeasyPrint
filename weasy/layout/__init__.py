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
Module managing the layout creation before drawing a document.

"""

from __future__ import division

from .blocks import block_box_layout
from .percentages import resolve_percentages
from ..css.values import get_pixel_value
from ..formatting_structure import boxes


def page_dimensions(box):
    """Set the page dimensions of the given :class:`boxes.PageBox`."""
    box.outer_width, box.outer_height = map(get_pixel_value, box.style.size)

    resolve_percentages(box)

    box.position_x = 0
    box.position_y = 0
    box.width = box.outer_width - box.horizontal_surroundings()
    box.height = box.outer_height - box.vertical_surroundings()

    box.root_box.width = box.width
    box.root_box.height = box.height

    box.root_box.position_x = box.content_box_x()
    box.root_box.position_y = box.content_box_y()

    # TODO: handle cases where the root element is something else.
    # See http://www.w3.org/TR/CSS21/visuren.html#dis-pos-flo
    assert isinstance(box.root_box, boxes.BlockBox)
    block_box_layout(box.root_box)


def layout(document):
    """Create the layout of the whole document.

    This includes line breaks, page breaks, absolute size and position for all
    boxes.

    """
    pages = []
    page = boxes.PageBox(document, document.formatting_structure, 1)
    page_dimensions(page)
    pages.append(page)

    # TODO: do page breaks, split boxes into multiple pages
    return pages
