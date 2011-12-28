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


def compute_fixed_dimension(box, outer, vertical, top_or_left):
    """
    Compute and set a margin box fixed dimension on ``box``, as described in:
    http://dev.w3.org/csswg/css3-page/#margin-constraints

    :param box:
        The margin box to work on
    :param outer:
        The target outer dimension (value of a page margin)
    :param vertical:
        True to set height, margin-top and margin-bottom; False for width,
        margin-left and margin-right
    :param top_or_left:
        True if the margin box in if the top half (for vertical==True) or
        left half (for vertical==False) of the page.
        This determines which margin should be 'auto' if the values are
        over-constrained. (Rule 3 of the algorithm.)
    """
    if vertical:
        margin_a = box.margin_top
        margin_b = box.margin_bottom
        padding_a = box.padding_top
        padding_b = box.padding_bottom
        border_a = box.style.border_top_width
        border_b = box.style.border_bottom_width
        inner = box.height
    else:
        margin_a = box.margin_left
        margin_b = box.margin_right
        padding_a = box.padding_left
        padding_b = box.padding_right
        border_a = box.style.border_left_width
        border_b = box.style.border_right_width
        inner = box.width
    padding_plus_border = padding_a + padding_b + border_a + border_b

    # Rule 2
    total = padding_plus_border + sum(
        value for value in [margin_a, margin_b, inner]
        if value != 'auto')
    if total > outer:
        if margin_a == 'auto':
            margin_a = 0
        if margin_b == 'auto':
            margin_a = 0
    # Rule 3
    if 'auto' not in [margin_a, margin_b, inner]:
        # Over-constrained
        if top_or_left:
            margin_a = 'auto'
        else:
            margin_b = 'auto'
    # Rule 4
    if [margin_a, margin_b, inner].count('auto') == 1:
        if inner == 'auto':
            inner = outer - padding_plus_border - margin_a - margin_b
        elif margin_a == 'auto':
            margin_a = outer - padding_plus_border - margin_b - inner
        elif margin_b == 'auto':
            margin_b = outer - padding_plus_border - margin_a - inner
    # Rule 5
    if inner == 'auto':
        if margin_a == 'auto':
            margin_a = 0
        if margin_b == 'auto':
            margin_a = 0
        inner = outer - padding_plus_border - margin_a - margin_b

    assert 'auto' not in [margin_a, margin_b, inner]
    # This should also be true, but may not be exact due to
    # floating point errors:
    #assert inner + padding_plus_border + margin_a + margin_b == outer
    if vertical:
        box.margin_top = margin_a
        box.margin_bottom = margin_b
        box.height = inner
    else:
        box.margin_left = margin_a
        box.margin_right = margin_b
        box.width = inner


def dummy_layout(box):
    """Dummy layout so that boxes can be generated without exceptions."""
    for name in ['width', 'height', 'margin_top', 'margin_bottom',
                 'margin_left', 'margin_right']:
        if getattr(box, name) == 'auto':
            setattr(box, name, 0)


def empty_margin_boxes(document, page, page_type):
    """
    Yield margin boxes for this page that have their own dimensions and
    position set, but still need their content.

    Parameters: same as :func:`make_margin_boxes`.

    """
    # This is a closure only to make calls shorter
    def make_box(at_keyword, containing_block):
        """
        Return a margin box with resolved percentages, but that may still
        have 'auto' values.

        Return ``None`` if this margin box should not be generated.

        :param at_keyword: which margin box to return, eg. '@top-left'
        :param containing_block: as expected by :func:`resolve_percentages`.

        """
        style = document.style_for(page_type, at_keyword)
        if style is not None and style.content not in ('normal', 'none'):
            box = boxes.MarginBox(at_keyword, style)
            resolve_percentages(box, containing_block)
            return box

    page_style = page.style
    margin_top = page_style.margin_top
    margin_bottom = page_style.margin_bottom
    margin_left = page_style.margin_left
    margin_right = page_style.margin_right
    max_box_width = page.border_width()
    max_box_height = page.border_height()

    # bottom right corner of the border box
    page_end_x = margin_left + max_box_width
    page_end_y = margin_top + max_box_height

    # Margin box dimensions, described in
    # http://dev.w3.org/csswg/css3-page/#margin-box-dimensions

    # Order recommended on http://dev.w3.org/csswg/css3-page/#painting
    # center/middle on top (last in tree order), then corner, ther others
    box = make_box('@top-left', (max_box_width, margin_top))
    if box is not None:
        box.position_x = 0  # TODO
        box.position_y = 0
        # TODO: actual layout
        dummy_layout(box)
        yield box

    # First, boxes that are neither cornen nor center/middle

    box = make_box('@top-right', (max_box_width, margin_top))
    if box is not None:
        box.position_x = 0  # TODO
        box.position_y = 0
        # TODO: actual layout
        dummy_layout(box)
        yield box

    box = make_box('@bottom-left', (max_box_width, margin_bottom))
    if box is not None:
        box.position_x = 0  # TODO
        box.position_y = page_end_y
        # TODO: actual layout
        dummy_layout(box)
        yield box

    box = make_box('@bottom-right', (max_box_width, margin_bottom))
    if box is not None:
        box.position_x = 0  # TODO
        box.position_y = page_end_y
        # TODO: actual layout
        dummy_layout(box)
        yield box

    box = make_box('@left-top', (margin_left, max_box_height))
    if box is not None:
        box.position_x = 0
        box.position_y = 0  # TODO
        # TODO: actual layout
        dummy_layout(box)
        yield box

    box = make_box('@left-bottom', (margin_left, max_box_height))
    if box is not None:
        box.position_x = 0
        box.position_y = 0  # TODO
        # TODO: actual layout
        dummy_layout(box)
        yield box

    box = make_box('@right-top', (margin_right, max_box_height))
    if box is not None:
        box.position_x = page_end_x
        box.position_y = 0  # TODO
        # TODO: actual layout
        dummy_layout(box)
        yield box

    box = make_box('@right-bottom', (margin_right, max_box_height))
    if box is not None:
        box.position_x = page_end_x
        box.position_y = 0  # TODO
        # TODO: actual layout
        dummy_layout(box)
        yield box

    # Corner boxes

    box = make_box('@top-left-corner', (margin_left, margin_top))
    if box is not None:
        box.position_x = 0
        box.position_y = 0
        compute_fixed_dimension(box, margin_top, True, True)
        compute_fixed_dimension(box, margin_left, False, True)
        yield box

    box = make_box('@top-right-corner', (margin_right, margin_top))
    if box is not None:
        box.position_x = page_end_x
        box.position_y = 0
        compute_fixed_dimension(box, margin_top, True, True)
        compute_fixed_dimension(box, margin_right, False, False)
        yield box

    box = make_box('@bottom-left-corner', (margin_left, margin_bottom))
    if box is not None:
        box.position_x = 0
        box.position_y = page_end_y
        compute_fixed_dimension(box, margin_bottom, True, False)
        compute_fixed_dimension(box, margin_left, False, True)
        yield box

    box = make_box('@bottom-right-corner', (margin_right, margin_bottom))
    if box is not None:
        box.position_x = page_end_x
        box.position_y = page_end_y
        compute_fixed_dimension(box, margin_bottom, True, False)
        compute_fixed_dimension(box, margin_right, False, False)
        yield box

    # Center and middle boxes

    box = make_box('@bottom-center', (max_box_width, margin_bottom))
    if box is not None:
        box.position_x = 0  # TODO
        box.position_y = page_end_y
        # TODO: actual layout
        dummy_layout(box)
        yield box

    box = make_box('@top-center', (max_box_width, margin_top))
    if box is not None:
        box.position_x = 0  # TODO
        box.position_y = 0
        # TODO: actual layout
        dummy_layout(box)
        yield box

    box = make_box('@left-middle', (margin_left, max_box_height))
    if box is not None:
        box.position_x = 0
        box.position_y = 0  # TODO
        # TODO: actual layout
        dummy_layout(box)
        yield box

    box = make_box('@right-middle', (margin_right, max_box_height))
    if box is not None:
        box.position_x = page_end_x
        box.position_y = 0  # TODO
        # TODO: actual layout
        dummy_layout(box)
        yield box


def make_margin_boxes(document, page, page_type):
    """Yield laid-out margin boxes for this page.

    :param document: a :class:`Document` object
    :param page: a :class:`PageBox` object
    :param page_type: as returned by :func:`page_type_for_number`

    """
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
