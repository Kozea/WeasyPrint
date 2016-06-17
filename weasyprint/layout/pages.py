# coding: utf-8
"""
    weasyprint.layout.pages
    -----------------------

    Layout for pages and CSS3 margin boxes.

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from ..formatting_structure import boxes, build
from .absolute import absolute_layout
from .blocks import block_level_layout, block_container_layout
from .percentages import resolve_percentages
from .preferred import min_content_width, max_content_width
from .min_max import handle_min_max_width, handle_min_max_height


class OrientedBox(object):
    @property
    def sugar(self):
        return self.padding_plus_border + self.margin_a + self.margin_b

    @property
    def outer(self):
        return self.sugar + self.inner

    @property
    def outer_min_content_size(self):
        return self.sugar + (
            self.min_content_size if self.inner == 'auto' else self.inner)

    @property
    def outer_max_content_size(self):
        return self.sugar + (
            self.max_content_size if self.inner == 'auto' else self.inner)

    def shrink_to_fit(self, available):
        self.inner = min(
            max(self.min_content_size, available), self.max_content_size)


class VerticalBox(OrientedBox):
    def __init__(self, context, box):
        self.context = context
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

    # TODO: Define what are the min-content and max-content heights
    @property
    def min_content_size(self):
        return 0

    @property
    def max_content_size(self):
        return 1e6


class HorizontalBox(OrientedBox):
    def __init__(self, context, box):
        self.context = context
        self.box = box
        self.inner = box.width
        self.margin_a = box.margin_left
        self.margin_b = box.margin_right
        self.padding_plus_border = (
            box.padding_left + box.padding_right +
            box.border_left_width + box.border_right_width)
        self._min_content_size = None
        self._max_content_size = None

    def restore_box_attributes(self):
        box = self.box
        box.width = self.inner
        box.margin_left = self.margin_a
        box.margin_right = self.margin_b

    @property
    def min_content_size(self):
        if self._min_content_size is None:
            self._min_content_size = min_content_width(
                self.context, self.box, outer=False)
        return self._min_content_size

    @property
    def max_content_size(self):
        if self._max_content_size is None:
            self._max_content_size = max_content_width(
                self.context, self.box, outer=False)
        return self._max_content_size


def compute_fixed_dimension(context, box, outer, vertical, top_or_left):
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
    box = (VerticalBox if vertical else HorizontalBox)(context, box)

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
            # http://lists.w3.org/Archives/Public/www-style/2012Jul/0006.html
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


def compute_variable_dimension(context, side_boxes, vertical, outer_sum):
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
    side_boxes = [box_class(context, box) for box in side_boxes]
    box_a, box_b, box_c = side_boxes

    for box in side_boxes:
        if box.margin_a == 'auto':
            box.margin_a = 0
        if box.margin_b == 'auto':
            box.margin_b = 0

    if box_b.box.is_generated:
        if box_b.inner == 'auto':
            ac_max_content_size = 2 * max(
                box_a.outer_max_content_size, box_c.outer_max_content_size)
            if outer_sum >= (
                    box_b.outer_max_content_size + ac_max_content_size):
                box_b.inner = box_b.max_content_size
            else:
                ac_min_content_size = 2 * max(
                    box_a.outer_min_content_size,
                    box_c.outer_min_content_size)
                box_b.inner = box_b.min_content_size
                available = outer_sum - box_b.outer - ac_min_content_size
                if available > 0:
                    weight_ac = ac_max_content_size - ac_min_content_size
                    weight_b = (
                        box_b.max_content_size - box_b.min_content_size)
                    weight_sum = weight_ac + weight_b
                    # By definition of max_content_size and min_content_size,
                    # weights can not be negative. weight_sum == 0 implies that
                    # max_content_size == min_content_size for each box, in
                    # which case the sum can not be both <= and > outer_sum
                    # Therefore, one of the last two 'if' statements would not
                    # have lead us here.
                    assert weight_sum > 0
                    box_b.inner += available * weight_b / weight_sum
        if box_a.inner == 'auto':
            box_a.shrink_to_fit((outer_sum - box_b.outer) / 2 - box_a.sugar)
        if box_c.inner == 'auto':
            box_c.shrink_to_fit((outer_sum - box_b.outer) / 2 - box_c.sugar)
    else:
        # Non-generated boxes get zero for every box-model property
        assert box_b.inner == 0
        if box_a.inner == box_c.inner == 'auto':
            if outer_sum >= (
                    box_a.outer_max_content_size +
                    box_c.outer_max_content_size):
                box_a.inner = box_a.max_content_size
                box_c.inner = box_c.max_content_size
            else:
                box_a.inner = box_a.min_content_size
                box_c.inner = box_c.min_content_size
                available = outer_sum - box_a.outer - box_c.outer
                if available > 0:
                    weight_a = (
                        box_a.max_content_size - box_a.min_content_size)
                    weight_c = (
                        box_c.max_content_size - box_c.min_content_size)
                    weight_sum = weight_a + weight_c
                    # By definition of max_content_size and min_content_size,
                    # weights can not be negative. weight_sum == 0 implies that
                    # max_content_size == min_content_size for each box, in
                    # which case the sum can not be both <= and > outer_sum
                    # Therefore, one of the last two 'if' statements would not
                    # have lead us here.
                    assert weight_sum > 0
                    box_a.inner += available * weight_a / weight_sum
                    box_c.inner += available * weight_c / weight_sum
        elif box_a.inner == 'auto':
            box_a.shrink_to_fit(outer_sum - box_c.outer - box_a.sugar)
        elif box_c.inner == 'auto':
            box_c.shrink_to_fit(outer_sum - box_a.outer - box_c.sugar)

    # And, we’re done!
    assert 'auto' not in [box.inner for box in side_boxes]
    # Set the actual attributes back.
    for box in side_boxes:
        box.restore_box_attributes()


def make_margin_boxes(context, page, counter_values):
    """Yield laid-out margin boxes for this page."""
    # This is a closure only to make calls shorter
    def make_box(at_keyword, containing_block):
        """
        Return a margin box with resolved percentages, but that may still
        have 'auto' values.

        Return ``None`` if this margin box should not be generated.

        :param at_keyword: which margin box to return, eg. '@top-left'
        :param containing_block: as expected by :func:`resolve_percentages`.

        """

        style = context.style_for(page.page_type, at_keyword)
        if style is None:
            style = page.style.inherit_from()
        box = boxes.MarginBox(at_keyword, style)
        # Empty boxes should not be generated, but they may be needed for
        # the layout of their neighbors.
        box.is_generated = style.content not in ('normal', 'none')
        # TODO: get actual counter values at the time of the last page break
        if box.is_generated:
            quote_depth = [0]
            children = build.content_to_boxes(
                box.style, box, quote_depth, counter_values,
                context.get_image_from_uri, context)
            box = box.copy_with_children(children)
            # content_to_boxes() only produces inline-level boxes, no need to
            # run other post-processors from build.build_formatting_structure()
            box = build.inline_in_block(box)
            build.process_whitespace(box)
        resolve_percentages(box, containing_block)
        if not box.is_generated:
            box.width = box.height = 0
            for side in ('top', 'right', 'bottom', 'left'):
                box._reset_spacing(side)
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
    generated_boxes = []

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
        if not any(box.is_generated for box in side_boxes):
            continue
        # We need the three boxes together for the variable dimension:
        compute_variable_dimension(
            context, side_boxes, vertical, variable_outer)
        for box, offset in zip(side_boxes, [0, 0.5, 1]):
            if not box.is_generated:
                continue
            box.position_x = position_x
            box.position_y = position_y
            if vertical:
                box.position_y += offset * (
                    variable_outer - box.margin_height())
            else:
                box.position_x += offset * (
                    variable_outer - box.margin_width())
            compute_fixed_dimension(
                context, box, fixed_outer, not vertical,
                prefix in ['top', 'left'])
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
        if not box.is_generated:
            continue
        box.position_x = position_x
        box.position_y = position_y
        compute_fixed_dimension(
            context, box, cb_height, True, 'top' in at_keyword)
        compute_fixed_dimension(
            context, box, cb_width, False, 'left' in at_keyword)
        generated_boxes.append(box)

    for box in generated_boxes:
        yield margin_box_content_layout(context, page, box)


def margin_box_content_layout(context, page, box):
    """Layout a margin box’s content once the box has dimensions."""
    box, resume_at, next_page, _, _ = block_container_layout(
        context, box,
        max_position_y=float('inf'), skip_stack=None,
        device_size=page.style.size, page_is_empty=True,
        absolute_boxes=[], fixed_boxes=[])
    assert resume_at is None

    vertical_align = box.style.vertical_align
    # Every other value is read as 'top', ie. no change.
    if vertical_align in ('middle', 'bottom') and box.children:
        first_child = box.children[0]
        last_child = box.children[-1]
        top = first_child.position_y
        # Not always exact because floating point errors
        # assert top == box.content_box_y()
        bottom = last_child.position_y + last_child.margin_height()
        content_height = bottom - top
        offset = box.height - content_height
        if vertical_align == 'middle':
            offset /= 2
        for child in box.children:
            child.translate(0, offset)
    return box


def page_width_or_height(box, containing_block_size):
    """Take a :class:`OrientedBox` object and set either width, margin-left
    and margin-right; or height, margin-top and margin-bottom.

    "The width and horizontal margins of the page box are then calculated
     exactly as for a non-replaced block element in normal flow. The height
     and vertical margins of the page box are calculated analogously (instead
     of using the block height formulas). In both cases if the values are
     over-constrained, instead of ignoring any margins, the containing block
     is resized to coincide with the margin edges of the page box."

    http://dev.w3.org/csswg/css3-page/#page-box-page-rule
    http://www.w3.org/TR/CSS21/visudet.html#blockwidth

    """
    remaining = containing_block_size - box.padding_plus_border
    if box.inner == 'auto':
        if box.margin_a == 'auto':
            box.margin_a = 0
        if box.margin_b == 'auto':
            box.margin_b = 0
        box.inner = remaining - box.margin_a - box.margin_b
    elif box.margin_a == box.margin_b == 'auto':
        box.margin_a = box.margin_b = (remaining - box.inner) / 2
    elif box.margin_a == 'auto':
        box.margin_a = remaining - box.inner - box.margin_b
    elif box.margin_b == 'auto':
        box.margin_b = remaining - box.inner - box.margin_a
    box.restore_box_attributes()


@handle_min_max_width
def page_width(box, context, containing_block_width):
    page_width_or_height(HorizontalBox(context, box), containing_block_width)


@handle_min_max_height
def page_height(box, context, containing_block_height):
    page_width_or_height(VerticalBox(context, box), containing_block_height)


def make_page(context, root_box, page_type, resume_at, content_empty,
              page_number=None):
    """Take just enough content from the beginning to fill one page.

    Return ``(page, finished)``. ``page`` is a laid out PageBox object
    and ``resume_at`` indicates where in the document to start the next page,
    or is ``None`` if this was the last page.

    :param page_number: integer, start at 1 for the first page
    :param resume_at: as returned by ``make_page()`` for the previous page,
                      or ``None`` for the first page.

    """
    style = context.style_for(page_type)
    # Propagated from the root or <body>.
    style.overflow = root_box.viewport_overflow
    page = boxes.PageBox(page_type, style)

    device_size = page.style.size

    resolve_percentages(page, device_size)

    page.position_x = 0
    page.position_y = 0
    cb_width, cb_height = device_size
    page_width(page, context, cb_width)
    page_height(page, context, cb_height)

    root_box.position_x = page.content_box_x()
    root_box.position_y = page.content_box_y()
    page_content_bottom = root_box.position_y + page.height
    initial_containing_block = page

    if content_empty:
        previous_resume_at = resume_at
        root_box = root_box.copy_with_children([])

    # TODO: handle cases where the root element is something else.
    # See http://www.w3.org/TR/CSS21/visuren.html#dis-pos-flo
    assert isinstance(root_box, boxes.BlockBox)
    context.create_block_formatting_context()
    page_is_empty = True
    adjoining_margins = []
    positioned_boxes = []  # Mixed absolute and fixed
    root_box, resume_at, next_page, _, _ = block_level_layout(
        context, root_box, page_content_bottom, resume_at,
        initial_containing_block, device_size, page_is_empty,
        positioned_boxes, positioned_boxes, adjoining_margins)
    assert root_box

    page.fixed_boxes = [
        placeholder._box for placeholder in positioned_boxes
        if placeholder._box.style.position == 'fixed']
    for absolute_box in positioned_boxes:
        absolute_layout(context, absolute_box, page, positioned_boxes)
    context.finish_block_formatting_context(root_box)

    page = page.copy_with_children([root_box])
    descendants = page.descendants()
    for child in descendants:
        string_sets = child.style.string_set
        if string_sets and string_sets != 'none':
            for string_set in string_sets:
                string_name, text = string_set
                context.string_set[string_name][page_number].append(text)
    if content_empty:
        resume_at = previous_resume_at
    return page, resume_at, next_page


def make_all_pages(context, root_box):
    """Return a list of laid out pages without margin boxes."""
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
    page_number = 0
    while True:
        page_number += 1
        content_empty = ((next_page == 'left' and right_page) or
                         (next_page == 'right' and not right_page))
        if content_empty:
            prefix += 'blank_'
        page_type = prefix + ('right_page' if right_page else 'left_page')
        page, resume_at, next_page = make_page(
            context, root_box, page_type, resume_at, content_empty,
            page_number)
        assert next_page
        yield page
        if resume_at is None:
            return
        prefix = ''
        right_page = not right_page
