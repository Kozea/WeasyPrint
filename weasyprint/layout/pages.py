"""
    weasyprint.layout.pages
    -----------------------

    Layout for pages and CSS3 margin boxes.

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import copy

from ..css import PageType, computed_from_cascaded
from ..formatting_structure import boxes, build
from ..logger import PROGRESS_LOGGER
from .absolute import absolute_layout
from .blocks import block_container_layout, block_level_layout
from .min_max import handle_min_max_height, handle_min_max_width
from .percentages import resolve_percentages
from .preferred import max_content_width, min_content_width


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


def _standardize_page_based_counters(style, pseudo_type):
    """Drop 'pages' counter from style in @page and @margin context.

    Ensure `counter-increment: page` for @page context if not otherwise
    manipulated by the style.

    """
    page_counter_touched = False
    # XXX 'counter-set` not yet supported
    for propname in ('counter_reset', 'counter_increment'):
        if style[propname] == 'auto':
            style[propname] = ()
            continue
        justified_values = []
        for name, value in style[propname]:
            if name == 'page':
                page_counter_touched = True
            if name != 'pages':
                justified_values.append((name, value))
        style[propname] = tuple(justified_values)

    if pseudo_type is None and not page_counter_touched:
        style['counter_increment'] = (
            ('page', 1),) + style['counter_increment']


def make_margin_boxes(context, page, state):
    """Yield laid-out margin boxes for this page.

    ``state`` is the actual, up-to-date page-state from
    ``context.page_maker[context.current_page]``.

    """
    # This is a closure only to make calls shorter
    def make_box(at_keyword, containing_block):
        """Return a margin box with resolved percentages.

        The margin box may still have 'auto' values.

        Return ``None`` if this margin box should not be generated.

        :param at_keyword: which margin box to return, eg. '@top-left'
        :param containing_block: as expected by :func:`resolve_percentages`.

        """
        style = context.style_for(page.page_type, at_keyword)
        if style is None:
            # doesn't affect counters
            style = computed_from_cascaded(
                element=None, cascaded={}, parent_style=page.style)
        _standardize_page_based_counters(style, at_keyword)
        box = boxes.MarginBox(at_keyword, style)
        # Empty boxes should not be generated, but they may be needed for
        # the layout of their neighbors.
        # TODO: should be the computed value.
        box.is_generated = style['content'] not in (
            'normal', 'inhibit', 'none')
        # TODO: get actual counter values at the time of the last page break
        if box.is_generated:
            # @margins mustn't manipulate page-context counters
            margin_state = copy.deepcopy(state)
            quote_depth, counter_values, counter_scopes = margin_state
            # TODO: check this, probably useless
            counter_scopes.append(set())
            build.update_counters(margin_state, box.style)
            box.children = build.content_to_boxes(
                box.style, box, quote_depth, counter_values,
                context.get_image_from_uri, context.target_collector, context,
                page)
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
        page_is_empty=True, absolute_boxes=[], fixed_boxes=[])
    assert resume_at is None

    vertical_align = box.style['vertical_align']
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


def make_page(context, root_box, page_type, resume_at, page_number,
              page_state):
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
    style['overflow'] = root_box.viewport_overflow
    page = boxes.PageBox(page_type, style)

    device_size = page.style['size']

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

    if page_type.blank:
        previous_resume_at = resume_at
        root_box = root_box.copy_with_children([])

    # TODO: handle cases where the root element is something else.
    # See http://www.w3.org/TR/CSS21/visuren.html#dis-pos-flo
    assert isinstance(root_box, (boxes.BlockBox, boxes.FlexContainerBox))
    context.create_block_formatting_context()
    context.current_page = page_number
    page_is_empty = True
    adjoining_margins = []
    positioned_boxes = []  # Mixed absolute and fixed
    root_box, resume_at, next_page, _, _ = block_level_layout(
        context, root_box, page_content_bottom, resume_at,
        initial_containing_block, page_is_empty, positioned_boxes,
        positioned_boxes, adjoining_margins)
    assert root_box

    page.fixed_boxes = [
        placeholder._box for placeholder in positioned_boxes
        if placeholder._box.style['position'] == 'fixed']
    for absolute_box in positioned_boxes:
        absolute_layout(context, absolute_box, page, positioned_boxes)
    context.finish_block_formatting_context(root_box)

    page.children = [root_box]
    descendants = page.descendants()

    # Update page counter values
    _standardize_page_based_counters(style, None)
    build.update_counters(page_state, style)
    page_counter_values = page_state[1]
    # page_counter_values will be cached in the page_maker

    target_collector = context.target_collector
    page_maker = context.page_maker

    # remake_state tells the make_all_pages-loop in layout_document()
    # whether and what to re-make.
    remake_state = page_maker[page_number - 1][-1]

    # Evaluate and cache page values only once (for the first LineBox)
    # otherwise we suffer endless loops when the target/pseudo-element
    # spans across multiple pages
    cached_anchors = []
    cached_lookups = []
    for (_, _, _, _, x_remake_state) in page_maker[:page_number - 1]:
        cached_anchors.extend(x_remake_state.get('anchors', []))
        cached_lookups.extend(x_remake_state.get('content_lookups', []))

    for child in descendants:
        # Cache target's page counters
        anchor = child.style['anchor']
        if anchor and anchor not in cached_anchors:
            remake_state['anchors'].append(anchor)
            cached_anchors.append(anchor)
            # Re-make of affected targeting boxes is inclusive
            target_collector.cache_target_page_counters(
                anchor, page_counter_values, page_number - 1, page_maker)

        # string-set and bookmark-labels don't create boxes, only `content`
        # requires another call to make_page. There is maximum one 'content'
        # item per box.
        # TODO: remove attribute or set a default value in Box class
        if hasattr(child, 'missing_link'):
            # A CounterLookupItem exists for the css-token 'content'
            counter_lookup = target_collector.counter_lookup_items.get(
                (child.missing_link, 'content'))
        else:
            counter_lookup = None

        # Resolve missing (page based) counters
        if counter_lookup is not None:
            call_parse_again = False

            # Prevent endless loops
            counter_lookup_id = id(counter_lookup)
            refresh_missing_counters = counter_lookup_id not in cached_lookups
            if refresh_missing_counters:
                remake_state['content_lookups'].append(counter_lookup_id)
                cached_lookups.append(counter_lookup_id)
                counter_lookup.page_maker_index = page_number - 1

            # Step 1: page based back-references
            # Marked as pending by target_collector.cache_target_page_counters
            if counter_lookup.pending:
                if (page_counter_values !=
                        counter_lookup.cached_page_counter_values):
                    counter_lookup.cached_page_counter_values = copy.deepcopy(
                        page_counter_values)
                counter_lookup.pending = False
                call_parse_again = True

            # Step 2: local counters
            # If the box mixed-in page counters changed, update the content
            # and cache the new values.
            missing_counters = counter_lookup.missing_counters
            if missing_counters:
                if 'pages' in missing_counters:
                    remake_state['pages_wanted'] = True
                if refresh_missing_counters and page_counter_values != \
                        counter_lookup.cached_page_counter_values:
                    counter_lookup.cached_page_counter_values = \
                        copy.deepcopy(page_counter_values)
                    for counter_name in missing_counters:
                        counter_value = page_counter_values.get(
                            counter_name, None)
                        if counter_value is not None:
                            call_parse_again = True
                            # no need to loop them all
                            break

            # Step 3: targeted counters
            target_missing = counter_lookup.missing_target_counters
            for anchor_name, missed_counters in target_missing.items():
                if 'pages' not in missed_counters:
                    continue
                # Adjust 'pages_wanted'
                item = target_collector.target_lookup_items.get(
                    anchor_name, None)
                page_maker_index = item.page_maker_index
                if page_maker_index >= 0 and anchor_name in cached_anchors:
                    page_maker[page_maker_index][-1]['pages_wanted'] = True
                # 'content_changed' is triggered in
                # targets.cache_target_page_counters()

            if call_parse_again:
                remake_state['content_changed'] = True
                counter_lookup.parse_again(page_counter_values)

    if page_type.blank:
        resume_at = previous_resume_at

    return page, resume_at, next_page


def set_page_type_computed_styles(page_type, html, style_for):
    """Set style for page types and pseudo-types matching ``page_type``."""
    style_for.add_page_declarations(page_type)

    # Apply style for page
    style_for.set_computed_styles(
        page_type,
        # @page inherits from the root element:
        # http://lists.w3.org/Archives/Public/www-style/2012Jan/1164.html
        root=html.etree_element, parent=html.etree_element,
        base_url=html.base_url)

    # Apply style for page pseudo-elements (margin boxes)
    for element, pseudo_type in style_for.get_cascaded_styles():
        if pseudo_type and element == page_type:
            style_for.set_computed_styles(
                element, pseudo_type=pseudo_type,
                # The pseudo-element inherits from the element.
                root=html.etree_element, parent=element,
                base_url=html.base_url)


def remake_page(index, context, root_box, html):
    """Return one laid out page without margin boxes.

    Start with the initial values from ``context.page_maker[index]``.
    The resulting values / initial values for the next page are stored in
    the ``page_maker``.

    As the function's name suggests: the plan is not to make all pages
    repeatedly when a missing counter was resolved, but rather re-make the
    single page where the ``content_changed`` happened.

    """
    page_maker = context.page_maker
    (initial_resume_at, initial_next_page, right_page, initial_page_state,
     remake_state) = page_maker[index]

    # PageType for current page, values for page_maker[index + 1].
    # Don't modify actual page_maker[index] values!
    # TODO: should we store (and reuse) page_type in the page_maker?
    page_state = copy.deepcopy(initial_page_state)
    next_page_name = initial_next_page['page']
    first = index == 0
    if initial_next_page['break'] in ('left', 'right'):
        next_page_side = initial_next_page['break']
    elif initial_next_page['break'] in ('recto', 'verso'):
        direction_ltr = root_box.style['direction'] == 'ltr'
        break_verso = initial_next_page['break'] == 'verso'
        next_page_side = 'right' if direction_ltr ^ break_verso else 'left'
    else:
        next_page_side = None
    blank = ((next_page_side == 'left' and right_page) or
             (next_page_side == 'right' and not right_page))
    if blank:
        next_page_name = ''
    side = 'right' if right_page else 'left'
    page_type = PageType(side, blank, first, index, name=next_page_name)
    set_page_type_computed_styles(page_type, html, context.style_for)

    context.forced_break = (
        initial_next_page['break'] != 'any' or initial_next_page['page'])
    context.margin_clearance = False

    # make_page wants a page_number of index + 1
    page_number = index + 1
    page, resume_at, next_page = make_page(
        context, root_box, page_type, initial_resume_at,
        page_number, page_state)
    assert next_page
    if blank:
        next_page['page'] = initial_next_page['page']
    right_page = not right_page

    # Check whether we need to append or update the next page_maker item
    if index + 1 >= len(page_maker):
        # New page
        page_maker_next_changed = True
    else:
        # Check whether something changed
        # TODO: Find what we need to compare. Is resume_at enough?
        (next_resume_at, next_next_page, next_right_page,
         next_page_state, _) = page_maker[index + 1]
        page_maker_next_changed = (
            next_resume_at != resume_at or
            next_next_page != next_page or
            next_right_page != right_page or
            next_page_state != page_state)

    if page_maker_next_changed:
        # Reset remake_state
        remake_state = {
            'content_changed': False,
            'pages_wanted': False,
            'anchors': [],
            'content_lookups': [],
        }
        # Setting content_changed to True ensures remake.
        # If resume_at is None (last page) it must be False to prevent endless
        # loops and list index out of range (see #794).
        remake_state['content_changed'] = resume_at is not None
        # page_state is already a deepcopy
        item = resume_at, next_page, right_page, page_state, remake_state
        if index + 1 >= len(page_maker):
            page_maker.append(item)
        else:
            page_maker[index + 1] = item

    return page, resume_at


def make_all_pages(context, root_box, html, pages):
    """Return a list of laid out pages without margin boxes.

    Re-make pages only if necessary.

    """
    i = 0
    while True:
        remake_state = context.page_maker[i][-1]
        if (len(pages) == 0 or
                remake_state['content_changed'] or
                remake_state['pages_wanted']):
            PROGRESS_LOGGER.info('Step 5 - Creating layout - Page %i', i + 1)
            # Reset remake_state
            remake_state['content_changed'] = False
            remake_state['pages_wanted'] = False
            remake_state['anchors'] = []
            remake_state['content_lookups'] = []
            page, resume_at = remake_page(i, context, root_box, html)
            yield page
        else:
            PROGRESS_LOGGER.info(
                'Step 5 - Creating layout - Page %i (up-to-date)', i + 1)
            resume_at = context.page_maker[i + 1][0]
            yield pages[i]

        i += 1
        if resume_at is None:
            # Throw away obsolete pages
            context.page_maker = context.page_maker[:i + 1]
            return
