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
Layout for page boxes and margin boxes.

"""

from __future__ import division

from .blocks import block_level_layout, block_level_height
from .percentages import resolve_percentages
from ..formatting_structure import boxes, build


MARGIN_BOXES = (
    # Order recommended on http://dev.w3.org/csswg/css3-page/#painting
    # center/middle on top (last in tree order), then corner, ther others
    '@top-left',
    '@top-right',
    '@bottom-left',
    '@bottom-right',
    '@left-top',
    '@right-bottom',
    '@right-top',
    '@right-bottom'

    '@top-left-corner',
    '@top-right-corner',
    '@bottom-left-corner',
    '@bottom-right-corner',

    '@bottom-center',
    '@top-center',
    '@left-middle',
    '@right-middle',
)


def empty_margin_boxes(document, page, page_type):
    for at_keyword in MARGIN_BOXES:
        style = document.style_for(page_type, at_keyword)
        if style is not None and style.content not in ('normal', 'none'):
            box = boxes.MarginBox(at_keyword, style)
            # TODO: Actual layout
            box.position_x = 0
            box.position_y = 0
            containing_block = 0, 0
            resolve_percentages(box, containing_block)
            for name in ['width', 'height', 'margin_top', 'margin_bottom',
                         'margin_left', 'margin_right']:
                if getattr(box, name) == 'auto':
                    setattr(box, name, 0)
            yield box


def make_margin_boxes(document, page, page_type):
    for box in empty_margin_boxes(document, page, page_type):
        # TODO: get actual counter values at the time of the last page break
        counter_values = {}
        quote_depth = [0]
        children = build.content_to_boxes(
            document, box.style, page, quote_depth, counter_values)
        box = box.copy_with_children(children)
        # content_to_boxes() only produces inline-level boxes
        box = build.inline_in_block(box)
        box, resume_at = block_level_height(document, box,
            max_position_y=float('inf'), skip_stack=None,
            device_size=page.style.size, page_is_empty=True)
        assert resume_at is None
        yield box


def page_type_for_number(page_number):
    """Return a page type such as ``'first_right_page'`` from a page number."""
    # First page is a right page.
    # TODO: this "should depend on the major writing direction of the
    # document".
    first_is_right = True

    is_right = (page_number % 2) == (1 if first_is_right else 0)
    page_type = 'right_page' if is_right else 'left_page'
    if page_number == 1:
        page_type = 'first_' + page_type
    return page_type


def make_page(document, page_number, resume_at):
    """Take just enough content from the beginning to fill one page.

    Return ``page, finished``. ``page`` is a laid out Page object, ``finished``
    is ``True`` if there is no more content, this was the last page.

    """
    root_box = document.formatting_structure
    page_type = page_type_for_number(page_number)
    style = document.style_for(page_type)
    page = boxes.PageBox(page_number, style, root_box.style.direction)

    device_size = page.style.size
    page.outer_width, page.outer_height = device_size

    resolve_percentages(page, device_size)

    page.position_x = 0
    page.position_y = 0
    page.width = page.outer_width - page.horizontal_surroundings()
    page.height = page.outer_height - page.vertical_surroundings()

    root_box.position_x = page.content_box_x()
    root_box.position_y = page.content_box_y()
    page_content_bottom = root_box.position_y + page.height
    initial_containing_block = page

    # TODO: handle cases where the root element is something else.
    # See http://www.w3.org/TR/CSS21/visuren.html#dis-pos-flo
    assert isinstance(root_box, boxes.BlockBox)
    root_box, resume_at = block_level_layout(
        document, root_box, page_content_bottom, resume_at,
        initial_containing_block, device_size, page_is_empty=True)
    assert root_box

    children = [root_box]
    children.extend(make_margin_boxes(document, page, page_type))

    page = page.copy_with_children(children)

    return page, resume_at
