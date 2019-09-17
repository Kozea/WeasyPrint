"""
    weasyprint.layout.blocks
    ------------------------

    Page breaking and layout for block-level and block-container boxes.

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from ..formatting_structure import boxes
from .absolute import AbsolutePlaceholder, absolute_layout
from .columns import columns_layout
from .flex import flex_layout
from .float import avoid_collisions, float_layout, get_clearance
from .inlines import (
    iter_line_boxes, min_max_auto_replaced, replaced_box_height,
    replaced_box_width)
from .min_max import handle_min_max_width
from .percentages import resolve_percentages, resolve_position_percentages
from .tables import table_layout, table_wrapper_width


def block_level_layout(context, box, max_position_y, skip_stack,
                       containing_block, page_is_empty, absolute_boxes,
                       fixed_boxes, adjoining_margins):
    """Lay out the block-level ``box``.

    :param max_position_y: the absolute vertical position (as in
                           ``some_box.position_y``) of the bottom of the
                           content box of the current page area.

    """
    if not isinstance(box, boxes.TableBox):
        resolve_percentages(box, containing_block)

        if box.margin_top == 'auto':
            box.margin_top = 0
        if box.margin_bottom == 'auto':
            box.margin_bottom = 0

        if (context.current_page > 1 and page_is_empty):
            # TODO: we should take care of cases when this box doesn't have
            # collapsing margins with the first child of the page, see
            # test_margin_break_clearance.
            if box.style['margin_break'] == 'discard':
                box.margin_top = 0
            elif box.style['margin_break'] == 'auto':
                if not context.forced_break:
                    box.margin_top = 0

        collapsed_margin = collapse_margin(
            adjoining_margins + [box.margin_top])
        box.clearance = get_clearance(context, box, collapsed_margin)
        if box.clearance is not None:
            top_border_edge = box.position_y + collapsed_margin + box.clearance
            box.position_y = top_border_edge - box.margin_top
            adjoining_margins = []

    return block_level_layout_switch(
        context, box, max_position_y, skip_stack, containing_block,
        page_is_empty, absolute_boxes, fixed_boxes, adjoining_margins)


def block_level_layout_switch(context, box, max_position_y, skip_stack,
                              containing_block, page_is_empty, absolute_boxes,
                              fixed_boxes, adjoining_margins):
    """Call the layout function corresponding to the ``box`` type."""
    if isinstance(box, boxes.TableBox):
        return table_layout(
            context, box, max_position_y, skip_stack, containing_block,
            page_is_empty, absolute_boxes, fixed_boxes)
    elif isinstance(box, boxes.BlockBox):
        return block_box_layout(
            context, box, max_position_y, skip_stack, containing_block,
            page_is_empty, absolute_boxes, fixed_boxes, adjoining_margins)
    elif isinstance(box, boxes.BlockReplacedBox):
        box = block_replaced_box_layout(box, containing_block)
        # Don't collide with floats
        # http://www.w3.org/TR/CSS21/visuren.html#floats
        box.position_x, box.position_y, _ = avoid_collisions(
            context, box, containing_block, outer=False)
        resume_at = None
        next_page = {'break': 'any', 'page': None}
        adjoining_margins = []
        collapsing_through = False
        return box, resume_at, next_page, adjoining_margins, collapsing_through
    elif isinstance(box, boxes.FlexBox):
        return flex_layout(
            context, box, max_position_y, skip_stack, containing_block,
            page_is_empty, absolute_boxes, fixed_boxes)
    else:  # pragma: no cover
        raise TypeError('Layout for %s not handled yet' % type(box).__name__)


def block_box_layout(context, box, max_position_y, skip_stack,
                     containing_block, page_is_empty, absolute_boxes,
                     fixed_boxes, adjoining_margins):
    """Lay out the block ``box``."""
    if (box.style['column_width'] != 'auto' or
            box.style['column_count'] != 'auto'):
        result = columns_layout(
            context, box, max_position_y, skip_stack, containing_block,
            page_is_empty, absolute_boxes, fixed_boxes, adjoining_margins)

        resume_at = result[1]
        # TODO: this condition and the whole relayout are probably wrong
        if resume_at is None:
            new_box = result[0]
            bottom_spacing = (
                new_box.margin_bottom + new_box.padding_bottom +
                new_box.border_bottom_width)
            if bottom_spacing:
                max_position_y -= bottom_spacing
                result = columns_layout(
                    context, box, max_position_y, skip_stack,
                    containing_block, page_is_empty, absolute_boxes,
                    fixed_boxes, adjoining_margins)

        return result
    elif box.is_table_wrapper:
        table_wrapper_width(
            context, box, (containing_block.width, containing_block.height))
    block_level_width(box, containing_block)

    new_box, resume_at, next_page, adjoining_margins, collapsing_through = \
        block_container_layout(
            context, box, max_position_y, skip_stack, page_is_empty,
            absolute_boxes, fixed_boxes, adjoining_margins)
    if new_box and new_box.is_table_wrapper:
        # Don't collide with floats
        # http://www.w3.org/TR/CSS21/visuren.html#floats
        position_x, position_y, _ = avoid_collisions(
            context, new_box, containing_block, outer=False)
        new_box.translate(
            position_x - new_box.position_x, position_y - new_box.position_y)
    return new_box, resume_at, next_page, adjoining_margins, collapsing_through


@handle_min_max_width
def block_replaced_width(box, containing_block):
    # http://www.w3.org/TR/CSS21/visudet.html#block-replaced-width
    replaced_box_width.without_min_max(box, containing_block)
    block_level_width.without_min_max(box, containing_block)


def block_replaced_box_layout(box, containing_block):
    """Lay out the block :class:`boxes.ReplacedBox` ``box``."""
    box = box.copy()
    if box.style['width'] == 'auto' and box.style['height'] == 'auto':
        computed_margins = box.margin_left, box.margin_right
        block_replaced_width.without_min_max(
            box, containing_block)
        replaced_box_height.without_min_max(box)
        min_max_auto_replaced(box)
        box.margin_left, box.margin_right = computed_margins
        block_level_width.without_min_max(box, containing_block)
    else:
        block_replaced_width(box, containing_block)
        replaced_box_height(box)

    return box


@handle_min_max_width
def block_level_width(box, containing_block):
    """Set the ``box`` width."""
    # 'cb' stands for 'containing block'
    cb_width = containing_block.width

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
        # The equation is over-constrained.
        if containing_block.style['direction'] == 'rtl' and not box.is_column:
            box.position_x += (
                cb_width - paddings_plus_borders - width - margin_r - margin_l)
        # Do nothing in ltr.
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


def relative_positioning(box, containing_block):
    """Translate the ``box`` if it is relatively positioned."""
    if box.style['position'] == 'relative':
        resolve_position_percentages(box, containing_block)

        if box.left != 'auto' and box.right != 'auto':
            if box.style['direction'] == 'ltr':
                translate_x = box.left
            else:
                translate_x = -box.right
        elif box.left != 'auto':
            translate_x = box.left
        elif box.right != 'auto':
            translate_x = -box.right
        else:
            translate_x = 0

        if box.top != 'auto':
            translate_y = box.top
        elif box.style['bottom'] != 'auto':
            translate_y = -box.bottom
        else:
            translate_y = 0

        box.translate(translate_x, translate_y)

    if isinstance(box, (boxes.InlineBox, boxes.LineBox)):
        for child in box.children:
            relative_positioning(child, containing_block)


def block_container_layout(context, box, max_position_y, skip_stack,
                           page_is_empty, absolute_boxes, fixed_boxes,
                           adjoining_margins=None):
    """Set the ``box`` height."""
    # TODO: boxes.FlexBox is allowed here because flex_layout calls
    # block_container_layout, there's probably a better solution.
    assert isinstance(box, (boxes.BlockContainerBox, boxes.FlexBox))

    # TODO: this should make a difference, but that is currently neglected.
    # See http://www.w3.org/TR/CSS21/visudet.html#normal-block
    #     http://www.w3.org/TR/CSS21/visudet.html#root-height

    # if box.style['overflow'] != 'visible':
    #     ...

    # We have to work around floating point rounding errors here.
    # The 1e-9 value comes from PEP 485.
    allowed_max_position_y = max_position_y * (1 + 1e-9)

    # See http://www.w3.org/TR/CSS21/visuren.html#block-formatting
    if not isinstance(box, boxes.BlockBox):
        context.create_block_formatting_context()

    is_start = skip_stack is None
    if box.style['box_decoration_break'] == 'slice' and not is_start:
        # Remove top margin, border and padding:
        box._remove_decoration(start=True, end=False)

    if adjoining_margins is None:
        adjoining_margins = []

    if box.style['box_decoration_break'] == 'clone':
        max_position_y -= (
            box.padding_bottom + box.border_bottom_width +
            box.margin_bottom)

    adjoining_margins.append(box.margin_top)
    this_box_adjoining_margins = adjoining_margins

    collapsing_with_children = not (
        box.border_top_width or box.padding_top or box.is_flex_item or
        establishes_formatting_context(box) or box.is_for_root_element)
    if collapsing_with_children:
        # XXX not counting margins in adjoining_margins, if any
        # (There are not padding or borders, see above.)
        position_y = box.position_y
    else:
        box.position_y += collapse_margin(adjoining_margins) - box.margin_top
        adjoining_margins = []
        position_y = box.content_box_y()

    position_x = box.content_box_x()

    if box.style['position'] == 'relative':
        # New containing block, use a new absolute list
        absolute_boxes = []

    new_children = []
    next_page = {'break': 'any', 'page': None}

    last_in_flow_child = None

    if is_start:
        skip = 0
        first_letter_style = getattr(box, 'first_letter_style', None)
    else:
        skip, skip_stack = skip_stack
        first_letter_style = None
    for i, child in enumerate(box.children[skip:]):
        index = i + skip
        child.position_x = position_x
        # XXX does not count margins in adjoining_margins:
        child.position_y = position_y

        if not child.is_in_normal_flow():
            child.position_y += collapse_margin(adjoining_margins)
            if child.is_absolutely_positioned():
                placeholder = AbsolutePlaceholder(child)
                placeholder.index = index
                new_children.append(placeholder)
                if child.style['position'] == 'absolute':
                    absolute_boxes.append(placeholder)
                else:
                    fixed_boxes.append(placeholder)
            elif child.is_floated():
                new_child = float_layout(
                    context, child, box, absolute_boxes, fixed_boxes)
                # New page if overflow
                if (page_is_empty and not new_children) or not (
                        new_child.position_y + new_child.height >
                        allowed_max_position_y):
                    new_child.index = index
                    new_children.append(new_child)
                else:
                    for previous_child in reversed(new_children):
                        if previous_child.is_in_normal_flow():
                            last_in_flow_child = previous_child
                            break
                    page_break = block_level_page_break(
                        last_in_flow_child, child)
                    if new_children and page_break in ('avoid', 'avoid-page'):
                        result = find_earlier_page_break(
                            new_children, absolute_boxes, fixed_boxes)
                        if result:
                            new_children, resume_at = result
                            break
                    resume_at = (index, None)
                    break
            continue

        if isinstance(child, boxes.LineBox):
            assert len(box.children) == 1, (
                'line box with siblings before layout')
            if adjoining_margins:
                position_y += collapse_margin(adjoining_margins)
                adjoining_margins = []
            new_containing_block = box
            lines_iterator = iter_line_boxes(
                context, child, position_y, skip_stack,
                new_containing_block, absolute_boxes, fixed_boxes,
                first_letter_style)
            is_page_break = False
            for line, resume_at in lines_iterator:
                line.resume_at = resume_at
                new_position_y = line.position_y + line.height

                # Add bottom padding and border to the bottom position of the
                # box if needed
                if resume_at is None or (
                        box.style['box_decoration_break'] == 'clone'):
                    offset_y = box.border_bottom_width + box.padding_bottom
                else:
                    offset_y = 0

                # Allow overflow if the first line of the page is higher
                # than the page itself so that we put *something* on this
                # page and can advance in the context.
                if new_position_y + offset_y > allowed_max_position_y and (
                        new_children or not page_is_empty):
                    over_orphans = len(new_children) - box.style['orphans']
                    if over_orphans < 0 and not page_is_empty:
                        # Reached the bottom of the page before we had
                        # enough lines for orphans, cancel the whole box.
                        page = child.page_values()[0]
                        return (
                            None, None, {'break': 'any', 'page': page}, [],
                            False)
                    # How many lines we need on the next page to satisfy widows
                    # -1 for the current line.
                    needed = box.style['widows'] - 1
                    if needed:
                        for _ in lines_iterator:
                            needed -= 1
                            if needed == 0:
                                break
                    if needed > over_orphans and not page_is_empty:
                        # Total number of lines < orphans + widows
                        page = child.page_values()[0]
                        return (
                            None, None, {'break': 'any', 'page': page}, [],
                            False)
                    if needed and needed <= over_orphans:
                        # Remove lines to keep them for the next page
                        del new_children[-needed:]
                    # Page break here, resume before this line
                    resume_at = (index, skip_stack)
                    is_page_break = True
                    break
                # TODO: this is incomplete.
                # See http://dev.w3.org/csswg/css3-page/#allowed-pg-brk
                # "When an unforced page break occurs here, both the adjoining
                #  ‘margin-top’ and ‘margin-bottom’ are set to zero."
                # See https://github.com/Kozea/WeasyPrint/issues/115
                elif page_is_empty and new_position_y > allowed_max_position_y:
                    # Remove the top border when a page is empty and the box is
                    # too high to be drawn in one page
                    new_position_y -= box.margin_top
                    line.translate(0, -box.margin_top)
                    box.margin_top = 0
                new_children.append(line)
                position_y = new_position_y
                skip_stack = resume_at
            if new_children:
                resume_at = (index, new_children[-1].resume_at)
            if is_page_break:
                break
        else:
            for previous_child in reversed(new_children):
                if previous_child.is_in_normal_flow():
                    last_in_flow_child = previous_child
                    break
            else:
                last_in_flow_child = None
            if last_in_flow_child is not None:
                # Between in-flow siblings
                page_break = block_level_page_break(last_in_flow_child, child)
                page_name = block_level_page_name(last_in_flow_child, child)
                if page_name or page_break in (
                        'page', 'left', 'right', 'recto', 'verso'):
                    page_name = child.page_values()[0]
                    next_page = {'break': page_break, 'page': page_name}
                    resume_at = (index, None)
                    break
            else:
                page_break = 'auto'

            new_containing_block = box

            if not new_containing_block.is_table_wrapper:
                resolve_percentages(child, new_containing_block)
                if (child.is_in_normal_flow() and
                        last_in_flow_child is None and
                        collapsing_with_children):
                    # TODO: add the adjoining descendants' margin top to
                    # [child.margin_top]
                    old_collapsed_margin = collapse_margin(adjoining_margins)
                    if child.margin_top == 'auto':
                        child_margin_top = 0
                    else:
                        child_margin_top = child.margin_top
                    new_collapsed_margin = collapse_margin(
                        adjoining_margins + [child_margin_top])
                    collapsed_margin_difference = (
                        new_collapsed_margin - old_collapsed_margin)
                    for previous_new_child in new_children:
                        previous_new_child.translate(
                            dy=collapsed_margin_difference)
                    clearance = get_clearance(
                        context, child, new_collapsed_margin)
                    if clearance is not None:
                        for previous_new_child in new_children:
                            previous_new_child.translate(
                                dy=-collapsed_margin_difference)

                        collapsed_margin = collapse_margin(adjoining_margins)
                        box.position_y += collapsed_margin - box.margin_top
                        # Count box.margin_top as we emptied adjoining_margins
                        adjoining_margins = []
                        position_y = box.content_box_y()

            if adjoining_margins and box.is_table_wrapper:
                collapsed_margin = collapse_margin(adjoining_margins)
                child.position_y += collapsed_margin
                position_y += collapsed_margin
                adjoining_margins = []

            page_is_empty_with_no_children = page_is_empty and not any(
                child for child in new_children
                if not isinstance(child, AbsolutePlaceholder))

            if not getattr(child, 'first_letter_style', None):
                child.first_letter_style = first_letter_style
            (new_child, resume_at, next_page, next_adjoining_margins,
                collapsing_through) = block_level_layout(
                    context, child, max_position_y, skip_stack,
                    new_containing_block, page_is_empty_with_no_children,
                    absolute_boxes, fixed_boxes, adjoining_margins)
            skip_stack = None

            if new_child is not None:
                # index in its non-laid-out parent, not in future new parent
                # May be used in find_earlier_page_break()
                new_child.index = index

                # We need to do this after the child layout to have the
                # used value for margin_top (eg. it might be a percentage.)
                if not isinstance(
                        new_child, (boxes.BlockBox, boxes.TableBox)):
                    adjoining_margins.append(new_child.margin_top)
                    offset_y = (
                        collapse_margin(adjoining_margins) -
                        new_child.margin_top)
                    new_child.translate(0, offset_y)
                    adjoining_margins = []
                # else: blocks handle that themselves.

                adjoining_margins = next_adjoining_margins
                adjoining_margins.append(new_child.margin_bottom)

                if not collapsing_through:
                    new_position_y = (
                        new_child.border_box_y() + new_child.border_height())

                    if (new_position_y > allowed_max_position_y and
                            not page_is_empty_with_no_children):
                        # The child overflows the page area, put it on the
                        # next page. (But don’t delay whole blocks if eg.
                        # only the bottom border overflows.)
                        new_child = None
                    else:
                        position_y = new_position_y

                if new_child is not None and new_child.clearance is not None:
                    position_y = (
                        new_child.border_box_y() + new_child.border_height())

            if new_child is None:
                # Nothing fits in the remaining space of this page: break
                if page_break in ('avoid', 'avoid-page'):
                    # TODO: fill the blank space at the bottom of the page
                    result = find_earlier_page_break(
                        new_children, absolute_boxes, fixed_boxes)
                    if result:
                        new_children, resume_at = result
                        break
                    else:
                        # We did not find any page break opportunity
                        if not page_is_empty:
                            # The page has content *before* this block:
                            # cancel the block and try to find a break
                            # in the parent.
                            page = child.page_values()[0]
                            return (
                                None, None, {'break': 'any', 'page': page}, [],
                                False)
                        # else:
                        # ignore this 'avoid' and break anyway.

                if new_children:
                    resume_at = (index, None)
                    break
                else:
                    # This was the first child of this box, cancel the box
                    # completly
                    page = child.page_values()[0]
                    return (
                        None, None, {'break': 'any', 'page': page}, [], False)

            # Bottom borders may overflow here
            # TODO: back-track somehow when all lines fit but not borders
            new_children.append(new_child)
            if resume_at is not None:
                resume_at = (index, resume_at)
                break
    else:
        resume_at = None

    if (resume_at is not None and
            box.style['break_inside'] in ('avoid', 'avoid-page') and
            not page_is_empty):
        return (
            None, None, {'break': 'any', 'page': None}, [], False)

    if collapsing_with_children:
        box.position_y += (
            collapse_margin(this_box_adjoining_margins) - box.margin_top)

    for previous_child in reversed(new_children):
        if previous_child.is_in_normal_flow():
            last_in_flow_child = previous_child
            break
    else:
        last_in_flow_child = None
    collapsing_through = False
    if last_in_flow_child is None:
        collapsed_margin = collapse_margin(adjoining_margins)
        # top and bottom margin of this box
        if (box.height in ('auto', 0) and
            get_clearance(context, box, collapsed_margin) is None and
            all(v == 0 for v in [
                box.min_height, box.border_top_width, box.padding_top,
                box.border_bottom_width, box.padding_bottom])):
            collapsing_through = True
        else:
            position_y += collapsed_margin
            adjoining_margins = []
    else:
        # bottom margin of the last child and bottom margin of this box ...
        if box.height != 'auto':
            # not adjoining. (position_y is not used afterwards.)
            adjoining_margins = []

    if (box.border_bottom_width or
            box.padding_bottom or
            establishes_formatting_context(box) or
            box.is_for_root_element or
            box.is_table_wrapper):
        position_y += collapse_margin(adjoining_margins)
        adjoining_margins = []

    new_box = box.copy_with_children(
        new_children, is_start=is_start, is_end=resume_at is None)

    # TODO: See corner cases in
    # http://www.w3.org/TR/CSS21/visudet.html#normal-block
    # TODO: See float.float_layout
    if new_box.height == 'auto':
        if context.excluded_shapes and new_box.style['overflow'] != 'visible':
            max_float_position_y = max(
                float_box.position_y + float_box.margin_height()
                for float_box in context.excluded_shapes)
            position_y = max(max_float_position_y, position_y)
        new_box.height = position_y - new_box.content_box_y()

    if new_box.style['position'] == 'relative':
        # New containing block, resolve the layout of the absolute descendants
        for absolute_box in absolute_boxes:
            absolute_layout(context, absolute_box, new_box, fixed_boxes)

    for child in new_box.children:
        relative_positioning(child, (new_box.width, new_box.height))

    if not isinstance(new_box, boxes.BlockBox):
        context.finish_block_formatting_context(new_box)

    if resume_at is None:
        # After finish_block_formatting_context which may increment
        # new_box.height
        new_box.height = max(
            min(new_box.height, new_box.max_height),
            new_box.min_height)
    else:
        # Make the box fill the blank space at the bottom of the page
        # https://www.w3.org/TR/css-break-3/#box-splitting
        new_box.height = (
            max_position_y - new_box.position_y -
            (new_box.margin_height() - new_box.height))
        if box.style['box_decoration_break'] == 'clone':
            new_box.height += (
                box.padding_bottom + box.border_bottom_width +
                box.margin_bottom)

    if next_page['page'] is None:
        next_page['page'] = new_box.page_values()[1]

    return new_box, resume_at, next_page, adjoining_margins, collapsing_through


def collapse_margin(adjoining_margins):
    """Return the amount of collapsed margin for a list of adjoining margins.
    """
    # Add 0 to make sure that neither max() or min() get an empty list
    margins = [0]
    margins.extend(adjoining_margins)
    positives = (m for m in margins if m >= 0)
    negatives = (m for m in margins if m <= 0)
    return max(positives) + min(negatives)


def establishes_formatting_context(box):
    """Return wether a box establishes a block formatting context.

    See http://www.w3.org/TR/CSS2/visuren.html#block-formatting

    """
    return (
        box.is_floated()
    ) or (
        box.is_absolutely_positioned()
    ) or (
        # TODO: columns shouldn't be block boxes, this condition would then be
        # useless when this is fixed
        box.is_column
    ) or (
        isinstance(box, boxes.BlockContainerBox) and
        not isinstance(box, boxes.BlockBox)
    ) or (
        isinstance(box, boxes.BlockBox) and box.style['overflow'] != 'visible'
    )


def block_level_page_break(sibling_before, sibling_after):
    """Return the value of ``page-break-before`` or ``page-break-after``
    that "wins" for boxes that meet at the margin between two sibling boxes.

    For boxes before the margin, the 'page-break-after' value is considered;
    for boxes after the margin the 'page-break-before' value is considered.

    * 'avoid' takes priority over 'auto'
    * 'page' takes priority over 'avoid' or 'auto'
    * 'left' or 'right' take priority over 'always', 'avoid' or 'auto'
    * Among 'left' and 'right', later values in the tree take priority.

    See http://dev.w3.org/csswg/css3-page/#allowed-pg-brk

    """
    values = []
    # https://drafts.csswg.org/css-break-3/#possible-breaks
    block_parallel_box_types = (
        boxes.BlockLevelBox, boxes.TableRowGroupBox, boxes.TableRowBox)

    box = sibling_before
    while isinstance(box, block_parallel_box_types):
        values.append(box.style['break_after'])
        if not (isinstance(box, boxes.ParentBox) and box.children):
            break
        box = box.children[-1]
    values.reverse()  # Have them in tree order

    box = sibling_after
    while isinstance(box, block_parallel_box_types):
        values.append(box.style['break_before'])
        if not (isinstance(box, boxes.ParentBox) and box.children):
            break
        box = box.children[0]

    result = 'auto'
    for value in values:
        if value in ('left', 'right', 'recto', 'verso') or (value, result) in (
                ('page', 'auto'),
                ('page', 'avoid'),
                ('avoid', 'auto'),
                ('page', 'avoid-page'),
                ('avoid-page', 'auto')):
            result = value

    return result


def block_level_page_name(sibling_before, sibling_after):
    """Return the next page name when siblings don't have the same names."""
    before_page = sibling_before.page_values()[1]
    after_page = sibling_after.page_values()[0]
    if before_page != after_page:
        return after_page


def find_earlier_page_break(children, absolute_boxes, fixed_boxes):
    """Because of a `page-break-before: avoid` or a `page-break-after: avoid`
    we need to find an earlier page break opportunity inside `children`.

    Absolute or fixed placeholders removed from children should also be
    removed from `absolute_boxes` or `fixed_boxes`.

    Return (new_children, resume_at)

    """
    if children and isinstance(children[0], boxes.LineBox):
        # Normally `orphans` and `widows` apply to the block container, but
        # line boxes inherit them.
        orphans = children[0].style['orphans']
        widows = children[0].style['widows']
        index = len(children) - widows  # how many lines we keep
        if index < orphans:
            return None
        new_children = children[:index]
        resume_at = (0, new_children[-1].resume_at)
        remove_placeholders(children[index:], absolute_boxes, fixed_boxes)
        return new_children, resume_at

    previous_in_flow = None
    for index, child in reversed_enumerate(children):
        if child.is_in_normal_flow():
            if previous_in_flow is not None and (
                    block_level_page_break(child, previous_in_flow) not in
                    ('avoid', 'avoid-page')):
                index += 1  # break after child
                new_children = children[:index]
                # Get the index in the original parent
                resume_at = (children[index].index, None)
                break
            previous_in_flow = child
        if child.is_in_normal_flow() and (
                child.style['break_inside'] not in ('avoid', 'avoid-page')):
            breakable_box_types = (
                boxes.BlockBox, boxes.TableBox, boxes.TableRowGroupBox)
            if isinstance(child, breakable_box_types):
                result = find_earlier_page_break(
                    child.children, absolute_boxes, fixed_boxes)
                if result:
                    new_grand_children, resume_at = result
                    new_child = child.copy_with_children(new_grand_children)
                    new_children = list(children[:index]) + [new_child]
                    # Index in the original parent
                    resume_at = (new_child.index, resume_at)
                    index += 1  # Remove placeholders after child
                    break
    else:
        return None

    remove_placeholders(children[index:], absolute_boxes, fixed_boxes)
    return new_children, resume_at


def reversed_enumerate(seq):
    """Like reversed(list(enumerate(seq))) without copying the whole seq."""
    return zip(reversed(range(len(seq))), reversed(seq))


def remove_placeholders(box_list, absolute_boxes, fixed_boxes):
    """For boxes that have been removed in find_earlier_page_break(),
    also remove the matching placeholders in absolute_boxes and fixed_boxes.

    """
    for box in box_list:
        if isinstance(box, boxes.ParentBox):
            remove_placeholders(box.children, absolute_boxes, fixed_boxes)
        if box.style['position'] == 'absolute' and box in absolute_boxes:
            # box is not in absolute_boxes if its parent has position: relative
            absolute_boxes.remove(box)
        elif box.style['position'] == 'fixed':
            fixed_boxes.remove(box)
