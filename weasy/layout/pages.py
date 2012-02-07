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

import itertools

from ..logging import LOGGER
from ..formatting_structure import boxes, build
from .blocks import block_level_layout, block_level_height
from .percentages import resolve_percentages
from .preferred import inline_preferred_minimum_width, inline_preferred_width
from .variable_margin_dimension import with_rule_2


class VerticalBox(object):
    def __init__(self, box):
        self.box = box
        # Inner dimension: that of the content area, as opposed to the
        # outer dimension: that of the margin area.
        self.inner = box.height
        self.margin_a = box.margin_top
        self.margin_b = box.margin_bottom
        self.padding_plus_border = (
            box.padding_top + box.padding_bottom +
            box.border_top_width + box.border_bottom_width)

    def restore_box_attributes(self):
        box = self.box
        box.height = self.inner
        box.margin_top = self.margin_a
        box.margin_bottom = self.margin_b

    # TODO: preferred (minimum) height???
    @property
    def minimum(self):
        return 0

    @property
    def preferred(self):
        return float('inf')


class HorizontalBox(object):
    def __init__(self, box):
        self.box = box
        self.inner = box.width
        self.margin_a = box.margin_left
        self.margin_b = box.margin_right
        self.padding_plus_border = (
            box.padding_left + box.padding_right +
            box.border_left_width + box.border_right_width)
        self._minimum = None
        self._preferred = None

    def restore_box_attributes(self):
        box = self.box
        box.width = self.inner
        box.margin_left = self.margin_a
        box.margin_right = self.margin_b

    @property
    def minimum(self):
        if self._minimum is None:
            self._minimum = inline_preferred_minimum_width(self.box)
        return self._minimum

    @property
    def preferred(self):
        if self._preferred is None:
            self._preferred = inline_preferred_width(self.box)
        return self._preferred


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
    box = (VerticalBox if vertical else HorizontalBox)(box)

    # Rule 2
    total = box.padding_plus_border + sum(
        value for value in [box.margin_a, box.margin_b, box.inner]
        if value != 'auto')
    if total > outer:
        if box.margin_a == 'auto':
            box.margin_a = 0
        if box.margin_b == 'auto':
            box.margin_b = 0
        if box.inner == 'auto':
            # XXX this is not in the spec, but without it box.inner
            # would end up with a negative value.
            # Instead, this will trigger rule 3 below.
            box.inner = 0
    # Rule 3
    if 'auto' not in [box.margin_a, box.margin_b, box.inner]:
        # Over-constrained
        if top_or_left:
            box.margin_a = 'auto'
        else:
            box.margin_b = 'auto'
    # Rule 4
    if [box.margin_a, box.margin_b, box.inner].count('auto') == 1:
        if box.inner == 'auto':
            box.inner = (outer - box.padding_plus_border -
                         box.margin_a - box.margin_b)
        elif box.margin_a == 'auto':
            box.margin_a = (outer - box.padding_plus_border -
                            box.margin_b - box.inner)
        elif box.margin_b == 'auto':
            box.margin_b = (outer - box.padding_plus_border -
                            box.margin_a - box.inner)
    # Rule 5
    if box.inner == 'auto':
        if box.margin_a == 'auto':
            box.margin_a = 0
        if box.margin_b == 'auto':
            box.margin_b = 0
        box.inner = (outer - box.padding_plus_border -
                     box.margin_a - box.margin_b)
    # Rule 6
    if box.margin_a == 'auto' and box.margin_b == 'auto':
        box.margin_a = box.margin_b = (
            outer - box.padding_plus_border - box.inner) / 2

    assert 'auto' not in [box.margin_a, box.margin_b, box.inner]
    # This should also be true, but may not be exact due to
    # floating point errors:
    # assert (box.inner + box.padding_plus_border +
    #         box.margin_a + box.margin_b) == outer
    box.restore_box_attributes()


def compute_variable_dimension(document, side_boxes, vertical, outer_sum):
    """
    Compute and set a margin box fixed dimension on ``box``, as described in:
    http://dev.w3.org/csswg/css3-page/#margin-dimension

    :param side_boxes: Three boxes on a same side (as opposed to a corner.)
        A list of:
        - A @*-left or @*-top margin box
        - A @*-center or @*-middle margin box
        - A @*-right or @*-bottom margin box
    :param vertical:
        True to set height, margin-top and margin-bottom; False for width,
        margin-left and margin-right
    :param outer_sum:
        The target total outer dimension (max box width or height)

    """
    box_class = VerticalBox if vertical else HorizontalBox
    side_boxes = map(box_class, side_boxes)
    box_a, box_b, box_c =  side_boxes

    num_auto_margins = sum(
        value == 'auto'  # boolean as int
        for box in side_boxes
        for value in (box.margin_a, box.margin_b)
    )

    if box_b.box.exists:
        # TODO: remove this when Margin boxes variable dimension is correct
        if not document._auto_margin_boxes_warning_shown and (
                any('auto' in [box.margin_a, box.margin_b]
                    for box in side_boxes)):
            LOGGER.warn("Margin boxes with 'auto' margins are not supported. "
                        "You may get unexpected results.")
            document._auto_margin_boxes_warning_shown = True

        # Rule 2:  outer(box_a) == outer(box_b)
        with_rule_2(side_boxes, outer_sum)
    else:
        # Rule 2 does not apply
        # Rule 1: Target sum of all 'auto' values
        remaining = outer_sum - sum(
            value
            for box in side_boxes
            for value in [box.margin_a, box.margin_b, box.inner,
                          box.padding_plus_border]
            if value != 'auto')

        # Not empty because box_b does not "exist", box_b.inner == 'auto'
        auto_inner_boxes = [box for box in side_boxes if box.inner == 'auto']
        min_inners = [box.minimum for box in auto_inner_boxes]
        max_inners = [box.preferred for box in auto_inner_boxes]
        sum_min_inners = sum(min_inners)
        sum_max_inners = sum(max_inners)
        # Minimize margins while keeping inner dimensions within bounds
        if remaining < sum_min_inners:
            # minimum widths are bigger than the target sum for
            # 'auto' values.
            # Use that, and 'auto' margins will be negative
            # Content will most likely overlap.
            for box, min_inner in zip(auto_inner_boxes, min_inners):
                # Rule 5
                box.inner = min_inner
            sum_margins = remaining - sum_min_inners
        # If remaining is not within range and the number of auto margins
        # is zero the problem is over-constrained.
        # The maximum constraints are the first to be dropped in this
        # case: only keep them if there are auto margins.
        elif remaining > sum_max_inners and num_auto_margins > 0:
            for box, max_inner in zip(auto_inner_boxes, max_inners):
                # Rule 6
                box.inner = max_inner
            sum_margins = remaining - sum_max_inners
        else:
            sum_margins = 0
            sum_inners = remaining

            weights = [
                (max_inner / sum_max_inners
                    if max_inner != float('inf') and sum_max_inners != 0
                    else 1 / len(auto_inner_boxes))
                for box, max_inner in zip(auto_inner_boxes, max_inners)
            ]
            # sum(weights) == 1, with some floating point error

            if remaining > sum_max_inners:
                # num_auto_margins == 0
                max_inners = [float('inf')] * 3
                sum_max_inners = float('inf')

            # Choose the inner dimension for all boxes with 'auto'
            # but the last
            for box, max_inner, min_inner, weight in zip(
                auto_inner_boxes, max_inners, min_inners, weights
            )[:-1]:
                # Ideal inner for A, to balance contents
                target = sum_inners * weight
                # The ranges for other boxes combined with the sum
                # constraint restrict the range for this box:
                if sum_max_inners != float('inf'):
                    others_sum_max = sum_max_inners - max_inner
                    min_inner = max(min_inner, sum_inners - others_sum_max)
                others_sum_min = sum_min_inners - min_inner
                max_inner = min(max_inner, sum_inners - others_sum_min)
                # As close as possible to target, but within bounds
                box.inner = min(max_inner, max(min_inner, target))
            # The dimension for the last box is resolved with the
            # target sum
            auto_inner_boxes[-1].inner = sum_inners - sum(
                box.inner for box in auto_inner_boxes[:-1])

        if sum_margins == 0:
            # Valid even if there is no 'auto' margin
            each_auto_margin = 0
        else:
            if num_auto_margins == 0:
                # Over-constrained: ignore the computed values of these margins
                box_a.margin_b = 'auto'
                box_c.margin_a = 'auto'
                num_auto_margins = 2
            each_auto_margin = sum_margins / num_auto_margins
        for box in side_boxes:
            if box.margin_a == 'auto':
                box.margin_a = each_auto_margin
            if box.margin_b == 'auto':
                box.margin_b = each_auto_margin


    # And, we’re done!
    assert all(
        value != 'auto'
        for box in side_boxes
        for value in [box.margin_a, box.margin_b, box.inner])
    # Set the actual attributes back.
    for box in side_boxes:
        box.restore_box_attributes()


def make_margin_boxes(document, page, counter_values):
    """Yield laid-out margin boxes for this page.

    :param document: a :class:`Document` object
    :param page: a :class:`PageBox` object

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
        style = document.style_for(page.page_type, at_keyword)
        if style is None:
            style = page.style.inherit_from()
        box = boxes.MarginBox(at_keyword, style)
        # TODO: get actual counter values at the time of the last page break
        quote_depth = [0]
        if style.content not in ('normal', 'none'):
            children = build.content_to_boxes(
                document, box.style, box, quote_depth, counter_values)
            box = box.copy_with_children(children)
            box = build.process_whitespace(box)
        resolve_percentages(box, containing_block)
        # Empty boxes should not be generated, but they may be needed for
        # the layout of their neighbors.
        box.exists = (
            style.content not in ('normal', 'none') or style.width != 'auto')
        return box

    margin_top = page.margin_top
    margin_bottom = page.margin_bottom
    margin_left = page.margin_left
    margin_right = page.margin_right
    max_box_width = page.border_width()
    max_box_height = page.border_height()

    # bottom right corner of the border box
    page_end_x = margin_left + max_box_width
    page_end_y = margin_top + max_box_height

    # Margin box dimensions, described in
    # http://dev.w3.org/csswg/css3-page/#margin-box-dimensions

    # Order recommended on http://dev.w3.org/csswg/css3-page/#painting
    # center/middle on top (last in tree order), then corner, then others

    # First, boxes that are neither corner nor center/middle
    # Delay center/middle boxes
    generated_boxes = []
    delayed_boxes = []

    for prefix, vertical, containing_block, position_x, position_y in [
        ('top', False, (max_box_width, margin_top),
            margin_left, 0),
        ('bottom', False, (max_box_width, margin_bottom),
            margin_left, page_end_y),
        ('left', True, (margin_left, max_box_height),
            0, margin_top),
        ('right', True, (margin_right, max_box_height),
            page_end_x, margin_top),
    ]:
        if vertical:
            suffixes = ['top', 'middle', 'bottom']
            fixed_outer, variable_outer = containing_block
        else:
            suffixes = ['left', 'center', 'right']
            variable_outer, fixed_outer = containing_block
        side_boxes = [make_box('@%s-%s' % (prefix, suffix), containing_block)
                      for suffix in suffixes]
        if not any(box.exists for box in side_boxes):
            continue
        # We need the three boxes together for the variable dimension:
        compute_variable_dimension(
            document, side_boxes, vertical, variable_outer)
        for box, delay in zip(side_boxes, [False, True, False]):
            if not box.exists:
                continue
            compute_fixed_dimension(
                box, fixed_outer, not vertical, prefix in ['top', 'left'])
            box.position_x = position_x
            box.position_y = position_y
            if vertical:
                position_y += box.margin_height()
            else:
                position_x += box.margin_width()
            if delay:
                delayed_boxes.append(box)
            else:
                generated_boxes.append(box)

    # Corner boxes

    for at_keyword, cb_width, cb_height, position_x, position_y in [
        ('@top-left-corner', margin_left, margin_top, 0, 0),
        ('@top-right-corner', margin_right, margin_top, page_end_x, 0),
        ('@bottom-left-corner', margin_left, margin_bottom, 0, page_end_y),
        ('@bottom-right-corner', margin_right, margin_bottom,
            page_end_x, page_end_y),
    ]:
        box = make_box(at_keyword, (cb_width, cb_height))
        if not box.exists:
            continue
        box.position_x = position_x
        box.position_y = position_y
        compute_fixed_dimension(box, cb_height, True, 'top' in at_keyword)
        compute_fixed_dimension(box, cb_width, False, 'left' in at_keyword)
        generated_boxes.append(box)

    generated_boxes.extend(delayed_boxes)

    for box in generated_boxes:
        yield margin_box_content_layout(document, page, box)


def margin_box_content_layout(document, page, box):
    """Layout a margin box’s content once the box has dimensions."""
    # content_to_boxes() only produces inline-level boxes, no need to
    # run other post-processors from build.build_formatting_structure()
    box = build.inline_in_block(box)
    box, resume_at, next_page = block_level_height(document, box,
        max_position_y=float('inf'), skip_stack=None,
        device_size=page.style.size, page_is_empty=True)
    assert resume_at is None

    vertical_align = box.style.vertical_align
    # Every other value is read as 'top', ie. no change.
    if vertical_align in ('middle', 'bottom') and box.children:
        first_child = box.children[0]
        last_child = box.children[-1]
        top = first_child.position_y
        assert top == box.content_box_y()
        bottom = last_child.position_y + last_child.margin_height()
        content_height = bottom - top
        offset = box.height - content_height
        if vertical_align == 'middle':
            offset /= 2
        for child in box.children:
            child.translate(0, offset)
    return box


def make_empty_page(document, page_type):
    style = document.style_for(page_type)
    page = boxes.PageBox(page_type, style)

    device_size = page.style.size
    page.outer_width, page.outer_height = device_size

    resolve_percentages(page, device_size)

    page.position_x = 0
    page.position_y = 0
    page.width = page.outer_width - page.horizontal_surroundings()
    page.height = page.outer_height - page.vertical_surroundings()
    return page


def make_page(document, page_type, resume_at):
    """Take just enough content from the beginning to fill one page.

    Return ``(page, finished)``. ``page`` is a laid out PageBox object
    and ``resume_at`` indicates where in the document to start the next page,
    or is ``None`` if this was the last page.

    :param document: a Document object
    :param page_number: integer, start at 1 for the first page
    :param resume_at: as returned by ``make_page()`` for the previous page,
                      or ``None`` for the first page.

    """
    page = make_empty_page(document, page_type)
    root_box = document.formatting_structure
    device_size = page.style.size

    root_box.position_x = page.content_box_x()
    root_box.position_y = page.content_box_y()
    page_content_bottom = root_box.position_y + page.height
    initial_containing_block = page

    # TODO: handle cases where the root element is something else.
    # See http://www.w3.org/TR/CSS21/visuren.html#dis-pos-flo
    assert isinstance(root_box, boxes.BlockBox)
    root_box, resume_at, next_page = block_level_layout(
        document, root_box, page_content_bottom, resume_at,
        initial_containing_block, device_size, page_is_empty=True)
    assert root_box

    page = page.copy_with_children([root_box])

    return page, resume_at, next_page


def make_all_pages(document):
    """Return a list of laid out pages without margin boxes."""
    root_box = document.formatting_structure
    prefix = 'first_'

    # Special case the root box
    page_break = root_box.style.page_break_before
    if page_break == 'right':
        right_page = True
    if page_break == 'left':
        right_page = False
    else:
        right_page = root_box.style.direction == 'ltr'

    resume_at = None
    next_page = 'any'
    while True:
        page_type = prefix + ('right_page' if right_page else 'left_page')
        if ((next_page == 'left' and right_page) or
            (next_page == 'right' and not right_page)):
            page = make_empty_page(document, page_type)
        else:
            page, resume_at, next_page = make_page(
                document, page_type, resume_at)
            assert next_page
        yield page
        if resume_at is None:
            return
        prefix = ''
        right_page = not right_page


def add_margin_boxes(document, pages):
    """Take a list of pages and return a new list with margin boxes added
    to each PageBox object.

    This is a later step as the total number of pages is needed for
    the pages counter.

    """
    page_counter = [1]
    counter_values = {'page': page_counter, 'pages': [len(pages)]}
    for page in pages:
        yield page.copy_with_children(itertools.chain(
            page.children,
            make_margin_boxes(document, page, counter_values)))
        page_counter[0] += 1
