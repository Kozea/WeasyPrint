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
from ..formatting_structure import boxes


def make_page(document, page_number, resume_at):
    """Take just enough content from the beginning to fill one page.

    Return ``page, finished``. ``page`` is a laid out Page object, ``finished``
    is ``True`` if there is no more content, this was the last page.

    """
    page = boxes.PageBox(document, page_number)

    device_size = page.style.size
    page.outer_width, page.outer_height = device_size

    sheet = lambda: 1  # dummy object holding attributes.
    sheet.width, sheet.height = device_size
    resolve_percentages(page, sheet)

    page.position_x = 0
    page.position_y = 0
    page.width = page.outer_width - page.horizontal_surroundings()
    page.height = page.outer_height - page.vertical_surroundings()

    root_box = document.formatting_structure

    # This box is not laid-out yet, but it may be needed during layout
    # eg. for ``page.direction``.
    page.root_box = root_box

    root_box.position_x = page.content_box_x()
    root_box.position_y = page.content_box_y()
    page_content_bottom = root_box.position_y + page.height
    initial_containing_block = page

    # TODO: handle cases where the root element is something else.
    # See http://www.w3.org/TR/CSS21/visuren.html#dis-pos-flo
    assert isinstance(root_box, boxes.BlockBox)
    page.root_box, resume_at = block_box_layout(
        root_box, page_content_bottom, resume_at,
        initial_containing_block, device_size, page_is_empty=True)
    assert page.root_box

    return page, resume_at


def layout(document):
    """Lay out the whole document.

    This includes line breaks, page breaks, absolute size and position for all
    boxes.

    :param document: a Document object.
    :returns: a list of laid out Page objects.

    """
    pages = []
    page_number = 1
    resume_at = None
    while True:
        page, resume_at = make_page(document, page_number, resume_at)
        pages.append(page)
        if resume_at is None:
            return pages
        page_number += 1
