# coding: utf8
"""
    weasyprint.layout.blocks
    ------------------------

    Page breaking and layout for block-level and block-container boxes.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from .inlines import (iter_line_boxes, replaced_box_width, replaced_box_height,
                      handle_min_max_width, min_max_replaced_height,
                      min_max_auto_replaced)
from .markers import list_marker_layout
from .tables import table_layout, table_wrapper_width
from .percentages import resolve_percentages
from ..formatting_structure import boxes


def block_level_layout(document, box, max_position_y, skip_stack,
                       containing_block, device_size, page_is_empty,
                       adjoining_margins=None):
    """Lay out the block-level ``box``.

    :param max_position_y: the absolute vertical position (as in
                           ``some_box.position_y``) of the bottom of the
                           content box of the current page area.

    """
    if isinstance(box, boxes.TableBox):
        return table_layout(document, box, max_position_y, skip_stack,
                            containing_block, device_size, page_is_empty)
    elif isinstance(box, boxes.BlockBox):
        if box.is_table_wrapper:
            table_wrapper_width(box, containing_block)
        return block_box_layout(document, box, max_position_y, skip_stack,
            containing_block, device_size, page_is_empty,
            adjoining_margins)
    elif isinstance(box, boxes.BlockReplacedBox):
        box = block_replaced_box_layout(
            box, containing_block, device_size)
        resume_at = None
        next_page = 'any'
        adjoining_margins = []
        collapsing_through = False
        return box, resume_at, next_page, adjoining_margins, collapsing_through
    else:  # pragma: no cover
        raise TypeError('Layout for %s not handled yet' % type(box).__name__)


def block_box_layout(document, box, max_position_y, skip_stack,
                     containing_block, device_size, page_is_empty,
                     adjoining_margins=None):
    """Lay out the block ``box``."""
    resolve_percentages(box, containing_block)
    block_level_width(box, containing_block)
    new_box, resume_at, next_page, adjoining_margins, collapsing_through = \
        block_container_layout(
            document, box, max_position_y, skip_stack,
            device_size, page_is_empty, adjoining_margins)
    list_marker_layout(document, new_box, containing_block)
    return new_box, resume_at, next_page, adjoining_margins, collapsing_through


def block_replaced_width(box, containing_block, device_size):
    # http://www.w3.org/TR/CSS21/visudet.html#block-replaced-width
    replaced_box_width(box, device_size)
    block_level_width(box, containing_block)

min_max_block_replaced_width = handle_min_max_width(block_replaced_width)


def block_replaced_box_layout(box, containing_block, device_size):
    """Lay out the block :class:`boxes.ReplacedBox` ``box``."""
    resolve_percentages(box, containing_block)
    if box.margin_top == 'auto':
        box.margin_top = 0
    if box.margin_bottom == 'auto':
        box.margin_bottom = 0

    if box.style.width == 'auto' and box.style.height == 'auto':
        block_replaced_width(box, containing_block, device_size)
        replaced_box_height(box, device_size)
        min_max_auto_replaced(box)
    else:
        min_max_block_replaced_width(box, containing_block, device_size)
        min_max_replaced_height(box, device_size)

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
        # The equation is over-constrained
        margin_sum = cb_width - paddings_plus_borders - width
        if containing_block.style.direction == 'ltr':
            margin_r = box.margin_right = margin_sum - margin_l
        else:
            margin_l = box.margin_left = margin_sum - margin_r
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


def block_container_layout(document, box, max_position_y, skip_stack,
                       device_size, page_is_empty, adjoining_margins=None):
    """Set the ``box`` height."""
    assert isinstance(box, boxes.BlockContainerBox)

    # TODO: this should make a difference, but that is currently neglected.
    # See http://www.w3.org/TR/CSS21/visudet.html#normal-block
    #     http://www.w3.org/TR/CSS21/visudet.html#root-height

    #if box.style.overflow != 'visible':
    #    ...

    if box.margin_top == 'auto':
        box.margin_top = 0
    if box.margin_bottom == 'auto':
        box.margin_bottom = 0

    if adjoining_margins is None:
        adjoining_margins = []

    adjoining_margins.append(box.margin_top)
    this_box_adjoining_margins = adjoining_margins

    collapsing_with_children = not (box.border_top_width or box.padding_top
        or establishes_formatting_context(box) or box.is_for_root_element)
    if collapsing_with_children:
        # XXX not counting margins in adjoining_margins, if any
        position_y = box.position_y
    else:
        box.position_y += collapse_margin(adjoining_margins) - box.margin_top
        adjoining_margins = []
        position_y = box.content_box_y()

    position_x = box.content_box_x()

    new_children = []
    next_page = 'any'

    if skip_stack is None:
        skip = 0
    else:
        skip, skip_stack = skip_stack

    for index, child in box.enumerate_skip(skip):
        if not child.is_in_normal_flow():
            continue

        child.position_x = position_x
        # XXX does not count margins in adjoining_margins:
        child.position_y = position_y

        if isinstance(child, boxes.LineBox):
            assert len(box.children) == 1, (
                'line box with siblings before layout')
            if adjoining_margins:
                position_y += collapse_margin(adjoining_margins)
                adjoining_margins = []
            new_containing_block = box
            lines_iterator = iter_line_boxes(
                document, child, position_y, skip_stack,
                new_containing_block, device_size)
            new_lines = []
            is_page_break = False
            for line, resume_at in lines_iterator:
                new_position_y = position_y + line.height
                # Allow overflow if the first line of the page is higher
                # than the page itself so that we put *something* on this
                # page and can advance in the document.
                if new_position_y > max_position_y and (
                        new_lines or not page_is_empty):
                    over_orphans = len(new_lines) - box.style.orphans
                    if over_orphans < 0 and not page_is_empty:
                        # Reached the bottom of the page before we had
                        # enough lines for orphans, cancel the whole box.
                        return None, None, 'any', [], False
                    # How many lines we need on the next page to satisfy widows
                    # -1 for the current line.
                    needed = box.style.widows - 1
                    if needed:
                        for _ in lines_iterator:
                            needed -= 1
                            if needed == 0:
                                break
                    if needed > over_orphans and not page_is_empty:
                        # Total number of lines < orphans + widows
                        return None, None, 'any', [], False
                    if needed and needed <= over_orphans:
                        # Remove lines to keep them for the next page
                        del new_lines[-needed:]
                    # Page break here, resume before this line
                    resume_at = (index, skip_stack)
                    is_page_break = True
                    break
                new_lines.append((line, resume_at))
                position_y = new_position_y
                skip_stack = resume_at
            new_children = [line for line, resume_at in new_lines]
            if new_lines:
                _, resume_at = new_lines[-1]
                resume_at = (index, resume_at)
            if is_page_break:
                break
        else:
            if new_children:
                # between siblings, but not before the first child
                # or after the last child.
                break_here, next_page = forced_page_break(
                    new_children[-1], child)
                if break_here:
                    resume_at = (index, None)
                    break

            new_containing_block = box
            (new_child, resume_at, next_page, next_adjoining_margins,
                collapsing_through) = block_level_layout(
                    document, child, max_position_y, skip_stack,
                    new_containing_block, device_size,
                    page_is_empty and not new_children,
                    adjoining_margins)
            skip_stack = None

            if new_child is not None:
                # We need to do this after the child layout to have the
                # used value for margin_top (eg. it might be a percentage.)
                if not isinstance(new_child, boxes.BlockBox):
                    adjoining_margins.append(new_child.margin_top)
                    offset_y = (collapse_margin(adjoining_margins)
                                 - new_child.margin_top)
                    new_child.translate(0, offset_y)
                    adjoining_margins = []
                #else: blocks handle that themselves.

                adjoining_margins = next_adjoining_margins
                adjoining_margins.append(new_child.margin_bottom)

                if not collapsing_through:
                    new_position_y = (
                        new_child.border_box_y() + new_child.border_height())

                    if (new_position_y > max_position_y and (
                                new_children or not page_is_empty)
                            and not isinstance(child, boxes.BlockBox)):
                        # The child overflows the page area, put it on the
                        # next page. (But don’t delay whole blocks if eg.
                        # only the bottom border overflows.)
                        new_child = None
                    else:
                        position_y = new_position_y

            if new_child is None:
                if new_children:
                    resume_at = (index, None)
                    break
                else:
                    # This was the first child of this box, cancel the box
                    # completly
                    return None, None, 'any', [], False

            # Bottom borders may overflow here
            # TODO: back-track somehow when all lines fit but not borders
            new_children.append(new_child)
            if resume_at is not None:
                resume_at = (index, resume_at)
                break

    else:
        resume_at = None

    if resume_at is not None and box.style.page_break_inside == 'avoid' \
            and not page_is_empty:
        return None, None, 'any', [], False


    if collapsing_with_children:
        if new_children and not isinstance(
                # margins are used for something else on line boxes
                new_children[0], boxes.LineBox):
            border_box_y = new_children[0].border_box_y()
        else:
            # this_adjoining_margins contains box.margin_top
            border_box_y = box.position_y + collapse_margin(
                this_box_adjoining_margins)
        box.position_y = border_box_y - box.margin_top

    collapsing_through = False
    if new_children:
        # bottom margin of the last child and bottom margin of this box ...
        if box.height != 'auto':
            # not adjoining. (position_y is not used afterwards.)
            adjoining_margins = []
    else:
        # top and bottom margin of this box
        if box.height in ('auto', 0) and box.min_height == 0:
            collapsing_through = True
        else:
            # not adjoining. (position_y is not used afterwards.)
            adjoining_margins = []

    if box.border_bottom_width or box.padding_bottom or (
            establishes_formatting_context(box) or box.is_for_root_element):
        position_y += collapse_margin(adjoining_margins)
        adjoining_margins = []

    new_box = box.copy_with_children(new_children)

    # TODO: See corner cases in
    # http://www.w3.org/TR/CSS21/visudet.html#normal-block
    if new_box.height == 'auto':
        new_box.height = position_y - new_box.content_box_y()
    new_box.height = max(
        min(new_box.height, new_box.max_height),
        new_box.min_height)

    if resume_at is not None:
        # If there was a list marker, we kept it on `new_box`.
        # Do not repeat it on `box` on the next page.
        # TODO: Do this non-destructively
        box.outside_list_marker = None
        box.reset_spacing('top')
        new_box.reset_spacing('bottom')

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
    return box.is_floated() or box.is_absolutely_positioned() or (
        isinstance(box, boxes.BlockContainerBox)
        and not isinstance(box, boxes.BlockBox)
    ) or (
        isinstance(box, boxes.BlockBox) and box.style.overflow != 'visible'
    )


def forced_page_break(sibling_before, sibling_after):
    """Return the value of ``page-break-before`` or ``page-break-after``
    that "wins" for boxes that meet at the margin between two sibling boxes.

    For boxes before the margin, the 'page-break-after' value is considered;
    for boxes after the margin the 'page-break-before' value is considered.

    Return (break_here, next_page) where break_here is a boolean, and
    next_page the side the next page should be on: 'left', 'right', or 'any'

    """
    counts = dict(
        avoid=False,
        auto=False,
        left=False,
        right=False,
        always=False,
    )
    for box, index, property_name in [
            (sibling_before, -1, 'page_break_after'),
            (sibling_after, 0, 'page_break_before')]:
        while 1:
            counts[box.style[property_name]] = True
            if not getattr(box, 'children', None):
                break
            box = box.children[index]
            if not isinstance(box, boxes.BlockLevelBox):
                break
    left = counts['left']
    right = counts['right']
    if left and right:
        # Nonsense. Just do a single page break
        return True, 'any'
    if left:
        return True, 'left'
    if right:
        return True, 'right'
    if counts['always']:
        return True, 'any'
    return False, 'any'
    # TODO: support 'avoid'
