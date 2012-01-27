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
Functions laying out the block boxes.

"""

from __future__ import division

from .inlines import get_next_linebox, replaced_box_width, replaced_box_height
from .markers import list_marker_layout
from .tables import table_layout, fixed_table_layout
from .percentages import resolve_percentages
from ..formatting_structure import boxes


def block_level_layout(document, box, max_position_y, skip_stack,
                       containing_block, device_size, page_is_empty):
    """Lay out the block-level ``box``.

    :param max_position_y: the absolute vertical position (as in
                           ``some_box.position_y``) of the bottom of the
                           content box of the current page area.

    """
    if isinstance(box, boxes.TableBox):
        return table_layout(document, box, max_position_y, containing_block,
                            device_size, page_is_empty)
    elif isinstance(box, boxes.BlockBox):
        if box.is_table_wrapper:
            return block_table_wrapper(document, box, max_position_y,
                skip_stack, containing_block, device_size, page_is_empty)
        else:
            return block_box_layout(document, box, max_position_y, skip_stack,
                containing_block, device_size, page_is_empty)
    elif isinstance(box, boxes.BlockReplacedBox):
        box = block_replaced_box_layout(
            box, containing_block, device_size)
        return box, None, 'any'
    else:
        raise TypeError('Layout for %s not handled yet' % type(box).__name__)


def block_box_layout(document, box, max_position_y, skip_stack,
                     containing_block, device_size, page_is_empty):
    """Lay out the block ``box``."""
    resolve_percentages(box, containing_block)
    block_level_width(box, containing_block)
    list_marker_layout(document, box, containing_block)
    return block_level_height(document, box, max_position_y, skip_stack,
        device_size, page_is_empty)


def block_replaced_box_layout(box, containing_block, device_size):
    """Lay out the block :class:`boxes.ReplacedBox` ``box``."""
    assert isinstance(box, boxes.ReplacedBox)
    resolve_percentages(box, containing_block)

    # http://www.w3.org/TR/CSS21/visudet.html#block-replaced-width
    replaced_box_width(box, device_size)
    block_level_width(box, containing_block)

    # http://www.w3.org/TR/CSS21/visudet.html#inline-replaced-height
    replaced_box_height(box, device_size)
    if box.margin_top == 'auto':
        box.margin_top = 0
    if box.margin_bottom == 'auto':
        box.margin_bottom = 0

    return box


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


# TODO: rename this to block_container_something
def block_level_height(document, box, max_position_y, skip_stack,
                       device_size, page_is_empty):
    """Set the ``box`` height."""
    assert isinstance(box, boxes.BlockContainerBox)

    if box.style.overflow != 'visible':
        raise NotImplementedError

    if box.margin_top == 'auto':
        box.margin_top = 0
    if box.margin_bottom == 'auto':
        box.margin_bottom = 0

    position_x = box.content_box_x()
    position_y = box.content_box_y()
    initial_position_y = position_y

    new_children = []
    next_page = 'any'

    if skip_stack is None:
        skip = 0
    else:
        skip, skip_stack = skip_stack

    for index, child in box.enumerate_skip(skip):
        if not child.is_in_normal_flow():
            continue
        # TODO: collapse margins
        # See http://www.w3.org/TR/CSS21/visudet.html#normal-block
        child.position_x = position_x
        child.position_y = position_y
        if isinstance(child, boxes.LineBox):
            assert len(box.children) == 1, (
                'line box with siblings before layout')
            is_page_break = False
            while 1:
                new_containing_block = box
                line, resume_at = get_next_linebox(
                    document, child, position_y, skip_stack,
                    new_containing_block, device_size)
                if line is None:
                    break
                new_position_y = position_y + line.height
                # Allow overflow if the first line of the page is higher
                # than the page itself so that we put *something* on this
                # page and can advance in the document.
                if new_position_y > max_position_y and not page_is_empty:
                    if not new_children:
                        # Page break before any content, cancel the whole box.
                        return None, None, 'any'
                    # Page break here, resume before this line
                    resume_at = (index, skip_stack)
                    is_page_break = True
                    break
                new_children.append(line)
                page_is_empty = False
                position_y = new_position_y
                if resume_at is None:
                    break
                skip_stack = resume_at
            if is_page_break:
                break
        else:
            page_break = child.style.page_break_before
            if page_break in ('always', 'left', 'right'):
                next_page = 'any' if page_break == 'always' else page_break
                resume_at = (index, None)
                # Force break only once
                # TODO: refactor to avoid doing this?
                child.style.page_break_before = 'auto'
                break

            new_containing_block = box
            new_child, resume_at, next_page = block_level_layout(
                document, child, max_position_y, skip_stack,
                new_containing_block, device_size, page_is_empty)
            skip_stack = None
            if new_child is None:
                if new_children:
                    resume_at = (index, None)
                    break
                else:
                    # This was the first child of this box, cancel the box
                    # completly
                    return None, None, 'any'
            new_position_y = position_y + new_child.margin_height()
            # Bottom borders may overflow here
            # TODO: back-track somehow when all lines fit but not borders
            new_children.append(new_child)
            page_is_empty = False
            position_y = new_position_y
            if resume_at is not None:
                resume_at = (index, resume_at)
                break

            page_break = child.style.page_break_after
            if page_break in ('always', 'left', 'right'):
                next_page = 'any' if page_break == 'always' else page_break
                # Resume after this
                resume_at = (index + 1, None)
                break
    else:
        resume_at = None

    new_box = box.copy_with_children(new_children)

    if new_box.height == 'auto':
        new_box.height = position_y - initial_position_y

    if resume_at is not None:
        # If there was a list marker, we kept it on `new_box`.
        # Do not repeat it on `box` on the next page.
        # TODO: Do this non-destructively
        box.outside_list_marker = None
        box.reset_spacing('top')
        new_box.reset_spacing('bottom')
    return new_box, resume_at, next_page


def block_table_wrapper(document, wrapper, max_position_y, skip_stack,
                        containing_block, device_size, page_is_empty):
    """Layout for the wrapper of a block-level table wrapper."""
    for child in wrapper.children:
        if isinstance(child, boxes.TableBox):
            table = child
            break
    else:
        raise ValueError('Table wrapper without a table')
    resolve_percentages(wrapper, containing_block)
    resolve_percentages(table, containing_block)
    # Count the wrapper margins in case of `width: auto`
    table.margin_left = wrapper.margin_left
    table.margin_right = wrapper.margin_right
    block_level_width(table, containing_block)
    # The table margins are on the table wrapper box, not on the table box
    table.margin_left = 0
    table.margin_right = 0

    fixed_table_layout(table)
    wrapper.width = wrapper.style.width = table.border_width()
    return block_box_layout(document, wrapper, max_position_y, skip_stack,
                            containing_block, device_size, page_is_empty)
