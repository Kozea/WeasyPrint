"""Page breaking and layout for block-level and block-container boxes."""

from math import inf

from ..formatting_structure import boxes
from .absolute import AbsolutePlaceholder, absolute_layout
from .column import columns_layout
from .flex import flex_layout
from .float import avoid_collisions, float_layout, get_clearance
from .grid import grid_layout
from .inline import iter_line_boxes
from .min_max import handle_min_max_width
from .percent import percentage, resolve_percentages, resolve_position_percentages
from .replaced import block_replaced_box_layout
from .table import table_layout, table_wrapper_width


def block_level_layout(context, box, bottom_space, skip_stack,
                       containing_block, page_is_empty=True,
                       absolute_boxes=None, fixed_boxes=None,
                       adjoining_margins=None, discard=False, max_lines=None):
    """Lay out the block-level ``box``."""
    absolute_boxes = [] if absolute_boxes is None else absolute_boxes
    fixed_boxes = [] if fixed_boxes is None else fixed_boxes
    adjoining_margins = [] if adjoining_margins is None else adjoining_margins

    if not isinstance(box, boxes.TableBox):
        resolve_percentages(box, containing_block)

        if box.margin_top == 'auto':
            box.margin_top = 0
        if box.margin_bottom == 'auto':
            box.margin_bottom = 0

        if context.current_page > 1 and page_is_empty:
            # When an unforced break occurs before or after a block-level box,
            # any margins adjoining the break are truncated to zero.
            # TODO: this condition is wrong, it only works for blocks whose
            # parent breaks collapsing margins. It should work for blocks whose
            # one of the ancestors breaks collapsing margins.
            # See test_margin_break_clearance.
            collapse_with_page = (
                containing_block.is_for_root_element or
                adjoining_margins)
            if collapse_with_page:
                if box.style['margin_break'] == 'discard':
                    box.margin_top = 0
                elif box.style['margin_break'] == 'auto':
                    if not context.forced_break:
                        box.margin_top = 0

        collapsed_margin = collapse_margin([*adjoining_margins, box.margin_top])
        box.clearance = get_clearance(context, box, collapsed_margin)
        if box.clearance is not None:
            top_border_edge = box.position_y + collapsed_margin + box.clearance
            box.position_y = top_border_edge - box.margin_top
            adjoining_margins = []

    return block_level_layout_switch(
        context, box, bottom_space, skip_stack, containing_block,
        page_is_empty, absolute_boxes, fixed_boxes, adjoining_margins, discard,
        max_lines)


def block_level_layout_switch(context, box, bottom_space, skip_stack,
                              containing_block, page_is_empty, absolute_boxes,
                              fixed_boxes, adjoining_margins, discard,
                              max_lines):
    """Call the layout function corresponding to the ``box`` type."""
    if isinstance(box, boxes.TableBox):
        result = table_layout(
            context, box, bottom_space, skip_stack, containing_block,
            page_is_empty, absolute_boxes, fixed_boxes)
    elif isinstance(box, boxes.BlockBox):
        return block_box_layout(
            context, box, bottom_space, skip_stack, containing_block,
            page_is_empty, absolute_boxes, fixed_boxes, adjoining_margins,
            discard, max_lines)
    elif isinstance(box, boxes.BlockReplacedBox):
        result = block_replaced_box_layout(context, box, containing_block)
    elif isinstance(box, boxes.FlexBox):
        result = flex_layout(
            context, box, bottom_space, skip_stack, containing_block,
            page_is_empty, absolute_boxes, fixed_boxes, discard)
    elif isinstance(box, boxes.GridBox):
        result = grid_layout(
            context, box, bottom_space, skip_stack, containing_block,
            page_is_empty, absolute_boxes, fixed_boxes)
    else:  # pragma: no cover
        raise TypeError(f'Layout for {type(box).__name__} not handled yet')
    return (*result, None)


def block_box_layout(context, box, bottom_space, skip_stack,
                     containing_block, page_is_empty, absolute_boxes,
                     fixed_boxes, adjoining_margins, discard, max_lines):
    """Lay out the block ``box``."""
    if (box.style['column_width'] != 'auto' or
            box.style['column_count'] != 'auto'):
        result = columns_layout(
            context, box, bottom_space, skip_stack, containing_block,
            page_is_empty, absolute_boxes, fixed_boxes, adjoining_margins)
        resume_at = result[1]
        # TODO: this condition and the whole relayout are probably wrong
        if resume_at is None:
            new_box = result[0]
            columns_bottom_space = (
                new_box.margin_bottom + new_box.padding_bottom +
                new_box.border_bottom_width)
            if columns_bottom_space:
                remove_placeholders(
                    context, [new_box], absolute_boxes, fixed_boxes)
                bottom_space += columns_bottom_space
                result = columns_layout(
                    context, box, bottom_space, skip_stack,
                    containing_block, page_is_empty, absolute_boxes,
                    fixed_boxes, adjoining_margins)
        return (*result, None)
    elif box.is_table_wrapper:
        table_wrapper_width(
            context, box, (containing_block.width, containing_block.height))
    block_level_width(box, containing_block)

    result = block_container_layout(
        context, box, bottom_space, skip_stack, page_is_empty,
        absolute_boxes, fixed_boxes, adjoining_margins, discard, max_lines)
    # TODO: columns and flex items shouldn't be block boxes, this condition
    # would then be useless when this is fixed.
    if not (new_box := result[0]) or new_box.is_column or new_box.is_flex_item:
        return result
    if new_box.is_table_wrapper or new_box.establishes_formatting_context():
        # Don't collide with floats
        # https://www.w3.org/TR/CSS21/visuren.html#floats
        position_x, position_y, _ = avoid_collisions(
            context, new_box, containing_block, outer=False)
        new_box.translate(
            position_x - new_box.position_x, position_y - new_box.position_y)
    return result


@handle_min_max_width
def block_level_width(box, containing_block):
    """Set the ``box`` width."""
    # 'cb' stands for 'containing block'
    if isinstance(containing_block, boxes.Box):
        cb_width = containing_block.width
        direction = containing_block.style['direction']
    else:
        cb_width = containing_block[0]
        # TODO: what is the real text direction?
        direction = 'ltr'

    # https://www.w3.org/TR/CSS21/visudet.html#blockwidth

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
        if direction == 'rtl' and not box.is_column:
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
    if margin_l == margin_r == 'auto':
        box.margin_left = margin_sum / 2
        box.margin_right = margin_sum / 2
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
        elif box.bottom != 'auto':
            translate_y = -box.bottom
        else:
            translate_y = 0

        box.translate(translate_x, translate_y)

    if isinstance(box, (boxes.InlineBox, boxes.LineBox)):
        for child in box.children:
            relative_positioning(child, containing_block)


def _out_of_flow_layout(context, box, index, child, new_children,
                        page_is_empty, absolute_boxes, fixed_boxes,
                        adjoining_margins, bottom_space):
    stop = False  # whether we should stop parent rendering after this layout
    resume_at = None  # where to resume in-flow rendering
    new_child = None  # child rendered by this layout
    out_of_flow_resume_at = None  # where to resume out-of-flow rendering

    # Add the parent’s collapsing margins to shift the child’s position. Don’t
    # include the out-of-flow child’s top margin because it doesn’t collapse
    # with its parent.
    child.position_y += collapse_margin(adjoining_margins)

    # Absolute child layout: create placeholder.
    if child.is_absolutely_positioned():
        new_child = placeholder = AbsolutePlaceholder(child)
        placeholder.index = index
        new_children.append(placeholder)
        if child.style['position'] == 'absolute':
            absolute_boxes.append(placeholder)
        else:
            fixed_boxes.append(placeholder)

    # Float child layout.
    elif child.is_floated():
        new_child, out_of_flow_resume_at = float_layout(
            context, child, box, absolute_boxes, fixed_boxes, bottom_space,
            skip_stack=None)

        # Check that child doesn’t overflow page.
        page_overflow = context.overflows_page(
            bottom_space, new_child.position_y + new_child.height)
        add_child = (
            (page_is_empty and not new_children) or
            not page_overflow or
            box.is_monolithic())
        if add_child:
            # Child fits or has to fit, add it.
            new_child.index = index
            new_children.append(new_child)
        else:
            # Child doesn’t fit and we can break, find where to break and stop
            # parent rendering.
            last_in_flow_child = find_last_in_flow_child(new_children)
            page_break = block_level_page_break(last_in_flow_child, child)
            resume_at = {index: None}
            out_of_flow_resume_at = None
            stop = True
            if new_children and avoid_page_break(page_break, context):
                # Can’t break inside float, find an earlier page break.
                result = find_earlier_page_break(
                    context, new_children, absolute_boxes, fixed_boxes)
                if result:
                    # Earlier page break found, drop whole child rendering.
                    new_children[:], resume_at = result
                    new_child = None

    # Running element layout.
    elif child.is_running():
        running_name = child.style['position'][1]
        page = context.current_page
        context.running_elements[running_name][page].append(child)

    return stop, resume_at, new_child, out_of_flow_resume_at


def _break_line(context, box, line, new_children, next_lines, page_is_empty, index,
                skip_stack, resume_at, absolute_boxes, fixed_boxes):
    """Break line where allowed by orphans and widows.

    Return (abort, stop, resume_at).

    """
    over_orphans = len(new_children) - box.style['orphans']
    if over_orphans < 0 and not page_is_empty:
        # Reached the bottom of the page before we had
        # enough lines for orphans, cancel the whole box.
        remove_placeholders(context, line.children, absolute_boxes, fixed_boxes)
        return True, False, resume_at
    # How many lines we need on the next page to satisfy widows
    # -1 for the current line.
    needed = max(box.style['widows'] - 1 - next_lines, 0)
    if needed > over_orphans and not page_is_empty:
        # Total number of lines < orphans + widows
        remove_placeholders(context, line.children, absolute_boxes, fixed_boxes)
        return True, False, resume_at
    if needed and needed <= over_orphans:
        # Remove lines to keep them for the next page
        for child in new_children[-needed:]:
            remove_placeholders(
                context, child.children, absolute_boxes, fixed_boxes)
        del new_children[-needed:]
    # Page break here, resume before this line
    remove_placeholders(context, line.children, absolute_boxes, fixed_boxes)
    return False, True, {index: skip_stack}


def _linebox_layout(context, box, index, child, new_children, page_is_empty,
                    absolute_boxes, fixed_boxes, adjoining_margins,
                    bottom_space, position_y, skip_stack, first_letter_style,
                    draw_bottom_decoration, max_lines):
    abort = stop = False
    resume_at = None
    new_footnotes = []

    assert len(box.children) == 1, 'line box with siblings before layout'

    if adjoining_margins:
        position_y += collapse_margin(adjoining_margins)
    new_containing_block = box
    lines_iterator = iter_line_boxes(
        context, child, position_y, bottom_space, skip_stack,
        new_containing_block, absolute_boxes, fixed_boxes, first_letter_style)
    for i, (line, resume_at) in enumerate(lines_iterator):
        # Break box if we reached max-lines
        if max_lines is not None:
            if max_lines == 0:
                new_children[-1].block_ellipsis = box.style['block_ellipsis']
                break
            max_lines -= 1

        # Update line resume_at and position_y
        line.resume_at = resume_at
        new_position_y = line.position_y + line.height

        # Add bottom padding and border to the bottom position of the
        # box if needed
        draw_bottom_decoration |= resume_at is None
        if draw_bottom_decoration:
            offset_y = box.border_bottom_width + box.padding_bottom
        else:
            offset_y = 0

        # Allow overflow if the first line of the page is higher than the page itself so
        # that we put *something* on this page and can advance in the context.
        overflow = (
            (new_children or not page_is_empty) and
            context.overflows_page(bottom_space, new_position_y + offset_y))
        if overflow:
            # If we couldn’t break the line before but can break now, first try to
            # report footnotes and see if we don’t overflow.
            could_break_before = can_break_now = True
            next_lines = len(tuple(lines_iterator))
            if len(new_children) + 1 < box.style['orphans']:
                can_break_now = False
            elif next_lines < box.style['widows']:
                can_break_now = False
            if len(new_children) < box.style['orphans']:
                could_break_before = False
            elif next_lines + 1 < box.style['widows']:
                could_break_before = False
            report = not context.in_column and can_break_now and not could_break_before
            reported_footnotes = 0
            while report and context.current_page_footnotes:
                context.report_footnote(context.current_page_footnotes[-1])
                reported_footnotes += 1
                if not context.overflows_page(bottom_space, new_position_y + offset_y):
                    new_children.append(line)
                    stop = True
                    break
            else:
                abort, stop, resume_at = _break_line(
                    context, box, line, new_children, next_lines,
                    page_is_empty, index, skip_stack, resume_at, absolute_boxes,
                    fixed_boxes)

            # Revert reported footnotes, as they’ve been reported starting from the last
            # one.
            if reported_footnotes >= 2:
                extra = context.reported_footnotes[-1:-reported_footnotes-1:-1]
                context.reported_footnotes[-reported_footnotes:] = extra

            break

        # TODO: this is incomplete.
        # See https://drafts.csswg.org/css-page-3/#allowed-pg-brk
        # "When an unforced page break occurs here, both the adjoining
        #  ‘margin-top’ and ‘margin-bottom’ are set to zero."
        # See issue #115.
        elif page_is_empty and context.overflows_page(
                bottom_space, new_position_y):
            # Remove the top border when a page is empty and the box is
            # too high to be drawn in one page
            new_position_y -= box.margin_top
            line.translate(0, -box.margin_top)
            box.margin_top = 0

        if context.footnotes:
            break_linebox = False
            footnotes = (
                descendant.footnote for descendant in line.descendants()
                if descendant.footnote in context.footnotes)
            for footnote in footnotes:
                overflow = context.layout_footnote(footnote)
                new_footnotes.append(footnote)
                overflow = (
                    overflow or
                    context.reported_footnotes or
                    context.overflows_page(
                        bottom_space, new_position_y + offset_y))
                if overflow:
                    context.report_footnote(footnote)
                    # If we've put other content on this page, then we may want
                    # to push this line or block to the next page. Otherwise,
                    # we can't (and would loop forever if we tried), so don't
                    # even try.
                    if new_children or not page_is_empty:
                        if footnote.style['footnote_policy'] == 'line':
                            next_lines = len(tuple(lines_iterator))
                            abort, stop, resume_at = _break_line(
                                context, box, line, new_children,
                                next_lines, page_is_empty, index,
                                skip_stack, resume_at, absolute_boxes,
                                fixed_boxes)
                            break_linebox = True
                            break
                        elif footnote.style['footnote_policy'] == 'block':
                            abort = break_linebox = True
                            break
            if break_linebox:
                break

        new_children.append(line)
        position_y = new_position_y
        skip_stack = resume_at

    if new_children:
        resume_at = {index: new_children[-1].resume_at}

    return abort, stop, resume_at, position_y, new_footnotes, max_lines


def _in_flow_layout(context, box, index, child, new_children, page_is_empty,
                    absolute_boxes, fixed_boxes, adjoining_margins,
                    bottom_space, position_y, skip_stack, first_letter_style,
                    draw_bottom_decoration, collapsing_with_children, discard,
                    next_page, max_lines):
    abort = stop = False

    last_in_flow_child = find_last_in_flow_child(new_children)
    if last_in_flow_child is not None:
        # Between in-flow siblings
        page_break = block_level_page_break(last_in_flow_child, child)
        page_name = block_level_page_name(last_in_flow_child, child)
        if page_name or force_page_break(page_break, context):
            page_name = child.page_values()[0]
            next_page = {'break': page_break, 'page': page_name}
            resume_at = {index: None}
            stop = True
            return (
                abort, stop, resume_at, position_y, adjoining_margins,
                next_page, new_children, max_lines)
    else:
        page_break = 'auto'

    new_containing_block = box

    if not new_containing_block.is_table_wrapper:
        resolve_percentages(child, new_containing_block)
        if last_in_flow_child is None and collapsing_with_children:
            # TODO: add the adjoining descendants' margin top to
            # [child.margin_top]
            old_collapsed_margin = collapse_margin(adjoining_margins)
            # TODO: the margin-top value is set afterwards in
            # block_level_layout, we shouldn’t duplicate this code
            child_margin_top = child.margin_top
            if child_margin_top == 'auto':
                child_margin_top = 0
            elif context.current_page > 1 and page_is_empty:
                if box.style['margin_break'] == 'discard':
                    child_margin_top = 0
                elif box.style['margin_break'] == 'auto':
                    if not context.forced_break:
                        child_margin_top = 0
            new_collapsed_margin = collapse_margin(
                [*adjoining_margins, child_margin_top])
            collapsed_margin_difference = (
                new_collapsed_margin - old_collapsed_margin)
            for previous_new_child in new_children:
                previous_new_child.translate(dy=collapsed_margin_difference)
            clearance = get_clearance(context, child, new_collapsed_margin)
            if clearance is not None:
                for previous_new_child in new_children:
                    previous_new_child.translate(
                        dy=-collapsed_margin_difference)

                collapsed_margin = collapse_margin(adjoining_margins)
                box.position_y += collapsed_margin - box.margin_top
                # Count box.margin_top as we emptied adjoining_margins
                adjoining_margins = []
                position_y = box.content_box_y()

    # TODO: Merge this with block_container_layout, block_level_layout, _in_flow_layout,
    # and check code above.
    if adjoining_margins:
        if box.is_table_wrapper:  # should not be a special case
            collapsed_margin = collapse_margin(adjoining_margins)
            child.position_y += collapsed_margin
            adjoining_margins = []
        elif not isinstance(child, boxes.BlockBox):  # blocks handle that themselves
            if child.style['margin_top'] == 'auto':
                margin_top = 0
            else:
                margin_top = percentage(child.style['margin_top'], box.width)
            adjoining_margins.append(margin_top)
            offset_y = collapse_margin(adjoining_margins) - margin_top
            child.position_y += offset_y
            adjoining_margins = []

    page_is_empty_with_no_children = page_is_empty and not any(
        child for child in new_children
        if not isinstance(child, AbsolutePlaceholder))

    if not getattr(child, 'first_letter_style', None):
        child.first_letter_style = first_letter_style
    (new_child, resume_at, next_page, next_adjoining_margins,
     collapsing_through, max_lines) = block_level_layout(
         context, child, bottom_space, skip_stack,
         new_containing_block, page_is_empty_with_no_children, absolute_boxes,
         fixed_boxes, adjoining_margins, discard, max_lines)

    if new_child is not None:
        if not collapsing_through:
            new_content_position_y = (
                new_child.content_box_y() + new_child.height)
            new_position_y = (
                new_child.border_box_y() + new_child.border_height())
            content_page_overflow = context.overflows_page(
                bottom_space, new_content_position_y)
            border_page_overflow = context.overflows_page(
                bottom_space, new_position_y)
            can_break = not (
                page_is_empty_with_no_children or box.is_monolithic())
            if can_break and content_page_overflow:
                # The child content overflows the page area, display it on the
                # next page.
                remove_placeholders(
                    context, [new_child], absolute_boxes, fixed_boxes)
                new_child = None
            elif can_break and border_page_overflow:
                # The child border/padding overflows the page area, do the
                # layout again with a higher bottom_space value.
                remove_placeholders(
                    context, [new_child], absolute_boxes, fixed_boxes)
                bottom_space += (
                    new_child.padding_bottom + new_child.border_bottom_width)
                (new_child, resume_at, next_page, next_adjoining_margins,
                 collapsing_through, max_lines) = block_level_layout(
                     context, child, bottom_space, skip_stack,
                     new_containing_block, page_is_empty_with_no_children,
                     absolute_boxes, fixed_boxes, adjoining_margins, discard,
                     max_lines)
                if new_child:
                    position_y = (
                        new_child.border_box_y() + new_child.border_height())
            else:
                position_y = new_position_y

        adjoining_margins = next_adjoining_margins
        if new_child:
            adjoining_margins.append(new_child.margin_bottom)

        if new_child and new_child.clearance:
            position_y = new_child.border_box_y() + new_child.border_height()

    skip_stack = None

    if new_child is None:
        # Nothing fits in the remaining space of this page: break
        if avoid_page_break(page_break, context):
            # TODO: fill the blank space at the bottom of the page
            result = find_earlier_page_break(
                context, new_children, absolute_boxes, fixed_boxes)
            if result:
                new_children, resume_at = result
                stop = True
                return (
                    abort, stop, resume_at, position_y, adjoining_margins,
                    next_page, new_children, max_lines)
            else:
                # We did not find any page break opportunity
                if not page_is_empty:
                    # The page has content *before* this block:
                    # cancel the block and try to find a break
                    # in the parent.
                    abort = True
                    return (
                        abort, stop, resume_at, position_y, adjoining_margins,
                        next_page, new_children, max_lines)
                # else:
                # ignore this 'avoid' and break anyway.

        if all(child.is_absolutely_positioned() for child in new_children):
            # This box has only rendered absolute children, keep them
            # for the next page. This is for example useful for list
            # markers.
            remove_placeholders(
                context, new_children, absolute_boxes, fixed_boxes)
            new_children = []

        if new_children:
            resume_at = {index: None}
            stop = True
        else:
            # This was the first child of this box, cancel the box completly
            abort = True
        return (
            abort, stop, resume_at, position_y, adjoining_margins, next_page,
            new_children, max_lines)

    # index in its non-laid-out parent, not in future new parent
    # May be used in find_earlier_page_break()
    new_child.index = index
    new_children.append(new_child)
    if resume_at is not None:
        resume_at = {index: resume_at}
        stop = True

    return (
        abort, stop, resume_at, position_y, adjoining_margins, next_page,
        new_children, max_lines)


def block_container_layout(context, box, bottom_space, skip_stack,
                           page_is_empty, absolute_boxes, fixed_boxes,
                           adjoining_margins, discard, max_lines):
    """Set the ``box`` height."""
    assert isinstance(box, boxes.BlockContainerBox)

    if box.establishes_formatting_context():
        context.create_block_formatting_context()

    # TODO: merge this with _in_flow_layout, flex_layout…
    is_start = skip_stack is None
    box.remove_decoration(start=not is_start, end=False)

    discard |= box.style['continue'] == 'discard'
    draw_bottom_decoration = (
        discard or box.style['box_decoration_break'] == 'clone')

    if adjoining_margins is None:
        adjoining_margins = []

    if draw_bottom_decoration:
        bottom_space += (
            box.padding_bottom + box.border_bottom_width + box.margin_bottom)

    adjoining_margins.append(box.margin_top)
    this_box_adjoining_margins = adjoining_margins

    collapsing_with_children = not (
        box.border_top_width or box.padding_top or box.is_flex_item or
        box.is_grid_item or box.establishes_formatting_context() or
        box.is_for_root_element)
    if collapsing_with_children:
        # Not counting margins in adjoining_margins, if any
        # (there are not padding or borders, see above)
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
    broken_out_of_flow = []

    last_in_flow_child = None

    if box.style['max_lines'] != 'none':
        max_lines = min(box.style['max_lines'], max_lines or inf)

    if is_start:
        skip = 0
        first_letter_style = getattr(box, 'first_letter_style', None)
    else:
        (skip, skip_stack), = skip_stack.items()
        first_letter_style = None
    for index, child in enumerate(box.children[skip:], start=(skip or 0)):
        child.position_x = position_x
        child.position_y = position_y  # doesn’t count adjoining_margins
        new_footnotes = []

        if not child.is_in_normal_flow():
            abort = False
            stop, resume_at, new_child, out_of_flow_resume_at = (
                _out_of_flow_layout(
                    context, box, index, child, new_children, page_is_empty,
                    absolute_boxes, fixed_boxes, adjoining_margins,
                    bottom_space))
            if out_of_flow_resume_at:
                context.broken_out_of_flow[new_child] = (
                    child, box, out_of_flow_resume_at)
                broken_out_of_flow.append(new_child)
            if child.is_outside_marker:
                new_child.position_x = box.border_box_x()
                if child.style['direction'] == 'rtl':
                    new_child.position_x += box.width + box.padding_right

        elif isinstance(child, boxes.LineBox):
            (abort, stop, resume_at, position_y,
             new_footnotes, max_lines) = _linebox_layout(
                context, box, index, child, new_children, page_is_empty,
                absolute_boxes, fixed_boxes, adjoining_margins, bottom_space,
                position_y, skip_stack, first_letter_style,
                draw_bottom_decoration, max_lines)
            draw_bottom_decoration |= resume_at is None
            adjoining_margins = []

        else:
            (abort, stop, resume_at, position_y, adjoining_margins,
             next_page, new_children, new_max_lines) = _in_flow_layout(
                 context, box, index, child, new_children, page_is_empty,
                 absolute_boxes, fixed_boxes, adjoining_margins, bottom_space,
                 position_y, skip_stack, first_letter_style,
                 draw_bottom_decoration, collapsing_with_children, discard,
                 next_page, max_lines)
            skip_stack = None

            if None not in (new_max_lines, max_lines):
                max_lines = new_max_lines
                if max_lines <= 0:
                    stop = True
                    last_child = (child == box.children[-1])
                    if not last_child:
                        children = new_children
                        while children:
                            last_child = children[-1]
                            if isinstance(last_child, boxes.LineBox):
                                last_child.block_ellipsis = (
                                    box.style['block_ellipsis'])
                            elif isinstance(last_child, boxes.ParentBox):
                                children = last_child.children
                                continue
                            break

        if abort:
            page = child.page_values()[0]
            remove_placeholders(
                context, box.children[skip:], absolute_boxes, fixed_boxes)
            for footnote in new_footnotes:
                context.unlayout_footnote(footnote)
            return (
                None, None, {'break': 'any', 'page': page}, [], False,
                max_lines)
        elif stop:
            if box.height != 'auto':
                if context.overflows(box.position_y + box.border_height(), position_y):
                    # Box heigh is fixed and it doesn’t overflow page, forget
                    # overflowing children.
                    resume_at = None
            adjoining_margins = []
            break

    else:
        resume_at = None

    box_is_fragmented = resume_at is not None or box.force_fragmentation
    if box.style['continue'] == 'discard':
        resume_at = None

    if (box_is_fragmented and
            avoid_page_break(box.style['break_inside'], context) and
            not page_is_empty):
        remove_placeholders(
            context, [*new_children, *box.children[skip:]], absolute_boxes, fixed_boxes)
        for child in broken_out_of_flow:
            del context.broken_out_of_flow[child]
        return None, None, {'break': 'any', 'page': None}, [], False, max_lines

    if collapsing_with_children:
        box.position_y += (
            collapse_margin(this_box_adjoining_margins) - box.margin_top)

    last_in_flow_child = find_last_in_flow_child(new_children)
    collapsing_through = False
    if last_in_flow_child is None:
        collapsed_margin = collapse_margin(adjoining_margins)
        # Top and bottom margins of this box
        if (box.height in ('auto', 0) and
            get_clearance(context, box, collapsed_margin) is None and
            all(value == 0 for value in (
                box.min_height, box.border_top_width, box.padding_top,
                box.border_bottom_width, box.padding_bottom))):
            collapsing_through = True
        else:
            position_y += collapsed_margin
            adjoining_margins = []
    else:
        # Bottom margin of the last child and bottom margin of this box
        if box.height != 'auto':
            # Not adjoining (position_y is not used afterwards)
            adjoining_margins = []

    if (box.border_bottom_width or
            box.padding_bottom or
            box.establishes_formatting_context() or
            box.is_for_root_element or
            box.is_table_wrapper):
        position_y += collapse_margin(adjoining_margins)
        adjoining_margins = []

    # Add block ellipsis
    if box_is_fragmented and new_children:
        last_child = new_children[-1]
        if isinstance(last_child, boxes.LineBox):
            last_child.block_ellipsis = box.style['block_ellipsis']

    new_box = box.copy_with_children(new_children)
    new_box.remove_decoration(
        start=not is_start, end=box_is_fragmented and not discard)

    # TODO: See corner cases in
    # https://www.w3.org/TR/CSS21/visudet.html#normal-block
    # TODO: See float.float_layout
    if new_box.height == 'auto':
        if context.excluded_shapes and new_box.style['overflow'] != 'visible':
            max_float_position_y = max(
                float_box.position_y + float_box.margin_height()
                for float_box in context.excluded_shapes)
            position_y = max(max_float_position_y, position_y)
        if position_y == new_box.content_box_y() == inf:
            new_box.height = 0
        else:
            new_box.height = position_y - new_box.content_box_y()

    if new_box.style['position'] == 'relative':
        # New containing block, resolve the layout of the absolute descendants
        for absolute_box in absolute_boxes:
            absolute_layout(
                context, absolute_box, new_box, fixed_boxes, bottom_space,
                skip_stack=None)

    for child in new_box.children:
        relative_positioning(child, (new_box.width, new_box.height))

    if new_box.establishes_formatting_context():
        context.finish_block_formatting_context(new_box)

    if discard or not box_is_fragmented:
        # After finish_block_formatting_context which may increment
        # new_box.height
        new_box.height = max(
            min(new_box.height, new_box.max_height), new_box.min_height)
    elif bottom_space > -inf and not new_box.is_column:
        # Make the box fill the blank space at the bottom of the page
        # https://www.w3.org/TR/css-break-3/#box-splitting
        new_box_height = (
            context.page_bottom - bottom_space - new_box.position_y -
            (new_box.margin_height() - new_box.height))
        if new_box_height > new_box.height:
            new_box.height = new_box_height
            if draw_bottom_decoration:
                new_box.height += (
                    box.padding_bottom + box.border_bottom_width +
                    box.margin_bottom)

    if next_page['page'] is None:
        next_page['page'] = new_box.page_values()[1]

    return (
        new_box, resume_at, next_page, adjoining_margins, collapsing_through,
        max_lines)


def collapse_margin(adjoining_margins):
    """Get the amount of collapsed margin for a list of adjoining margins."""
    margins = [0]  # add 0 to make sure that max/min don’t get an empty list
    margins.extend(adjoining_margins)
    positives = (m for m in margins if m >= 0)
    negatives = (m for m in margins if m <= 0)
    return max(positives) + min(negatives)


def block_level_page_break(sibling_before, sibling_after):
    """Get the correct page break value between siblings.

    Return the value of ``page-break-before`` or ``page-break-after`` that
    "wins" for boxes that meet at the margin between two sibling boxes.

    For boxes before the margin, the 'page-break-after' value is considered;
    for boxes after the margin the 'page-break-before' value is considered.

    * 'avoid' takes priority over 'auto'
    * 'page' takes priority over 'avoid' or 'auto'
    * 'left' or 'right' take priority over 'always', 'avoid' or 'auto'
    * Among 'left' and 'right', later values in the tree take priority.

    See https://drafts.csswg.org/css-page-3/#allowed-pg-brk

    """
    values = []
    # https://drafts.csswg.org/css-break-3/#possible-breaks
    block_parallel_box_types = (
        boxes.BlockLevelBox, boxes.TableRowGroupBox, boxes.TableRowBox)

    box = sibling_before
    while isinstance(box, block_parallel_box_types):
        values.append(box.style['break_after'])
        if not box.children:
            break
        box = box.children[-1]
    values.reverse()  # Have them in tree order

    box = sibling_after
    while isinstance(box, block_parallel_box_types):
        values.append(box.style['break_before'])
        if not box.children:
            break
        box = box.children[0]

    result = 'auto'
    for value in values:
        if value in ('left', 'right', 'recto', 'verso') or (value, result) in (
                ('page', 'auto'),
                ('page', 'avoid'),
                ('page', 'avoid-page'),
                ('page', 'avoid-column'),
                ('column', 'auto'),
                ('column', 'avoid'),
                ('column', 'avoid-page'),
                ('column', 'avoid-column'),
                ('avoid', 'auto'),
                ('avoid-page', 'auto'),
                ('avoid-column', 'auto')):
            result = value

    return result


def block_level_page_name(sibling_before, sibling_after):
    """Return the next page name when siblings don't have the same names."""
    before_page = sibling_before.page_values()[1]
    after_page = sibling_after.page_values()[0]
    if before_page != after_page:
        return after_page


def find_earlier_page_break(context, children, absolute_boxes, fixed_boxes):
    """Find the last possible page break in ``children``.

    Because of a `page-break-before: avoid` or a `page-break-after: avoid` we
    need to find an earlier page break opportunity inside `children`.

    Absolute or fixed placeholders removed from children should also be
    removed from `absolute_boxes` or `fixed_boxes`.

    Return (new_children, resume_at).

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
        resume_at = {0: new_children[-1].resume_at}
        remove_placeholders(
            context, children[index:], absolute_boxes, fixed_boxes)
        return new_children, resume_at

    previous_in_flow = None
    for index, child in reversed_enumerate(children):
        if isinstance(child, boxes.TableRowGroupBox) and (
                child.is_header or child.is_footer):
            # We don’t want to break pages before table headers or footers.
            continue
        elif child.is_column:
            # We don’t want to break pages between columns.
            continue

        if child.is_in_normal_flow():
            page_break = block_level_page_break(child, previous_in_flow)
            if previous_in_flow is not None and (
                    not avoid_page_break(page_break, context)):
                index += 1  # break after child
                new_children = children[:index]
                # Get the index in the original parent
                resume_at = {children[index].index: None}
                break
            previous_in_flow = child

        if child.is_in_normal_flow() and (
                not avoid_page_break(child.style['break_inside'], context)):
            breakable_box_types = (
                boxes.BlockBox, boxes.TableBox, boxes.TableRowGroupBox)
            if isinstance(child, breakable_box_types):
                result = find_earlier_page_break(
                    context, child.children, absolute_boxes, fixed_boxes)
                if result:
                    new_grand_children, resume_at = result
                    new_child = child.copy_with_children(new_grand_children)
                    new_children = [*children[:index], new_child]

                    # Re-add footer at the end of split table
                    # TODO: fix table height and footer position
                    if isinstance(child, boxes.TableRowGroupBox):
                        for next_child in children[index:]:
                            if next_child.is_footer:
                                new_children.append(next_child)

                    # Index in the original parent
                    resume_at = {new_child.index: resume_at}
                    index += 1  # Remove placeholders after child
                    break
    else:
        return None

    # TODO: don’t remove absolute and fixed placeholders found in table footers
    remove_placeholders(context, children[index:], absolute_boxes, fixed_boxes)
    return new_children, resume_at


def find_last_in_flow_child(children):
    """Find and return the last in-flow child of given ``children``."""
    for child in reversed(children):
        if child.is_in_normal_flow():
            return child


def reversed_enumerate(seq):
    """Like reversed(list(enumerate(seq))) without copying the whole seq."""
    return zip(reversed(range(len(seq))), reversed(seq))


def remove_placeholders(context, box_list, absolute_boxes, fixed_boxes):
    """Remove placeholders from absolute and fixed lists.

    For boxes that have been removed in find_earlier_page_break(), remove the
    matching placeholders in absolute_boxes and fixed_boxes.

    Also takes care of removed footnotes and floats.

    """
    for box in box_list:
        if isinstance(box, boxes.ParentBox):
            remove_placeholders(
                context, box.children, absolute_boxes, fixed_boxes)
        if box.style['position'] == 'absolute' and box in absolute_boxes:
            absolute_boxes.remove(box)
        elif box.style['position'] == 'fixed' and box in fixed_boxes:
            fixed_boxes.remove(box)
        if box.footnote:
            context.unlayout_footnote(box.footnote)
        if box in context.broken_out_of_flow:
            context.broken_out_of_flow.pop(box)


def avoid_page_break(page_break, context):
    """Test whether we should avoid breaks."""
    if context.in_column:
        return page_break in ('avoid', 'avoid-page', 'avoid-column')
    return page_break in ('avoid', 'avoid-page')


def force_page_break(page_break, context):
    """Test whether we should force breaks."""
    if context.in_column:
        return page_break in (
            'page', 'left', 'right', 'recto', 'verso', 'column')
    return page_break in ('page', 'left', 'right', 'recto', 'verso')
