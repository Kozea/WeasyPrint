# coding: utf8
"""
    weasyprint.layout.tables
    ------------------------

    Layout for tables and internal table boxes.

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from ..compat import xrange
from ..logger import LOGGER
from ..formatting_structure import boxes
from ..css.properties import Dimension
from .percentages import resolve_percentages, resolve_one_percentage
from .preferred import table_and_columns_preferred_widths


def table_layout(context, table, max_position_y, skip_stack,
                 containing_block, device_size, page_is_empty, absolute_boxes,
                 fixed_boxes):
    """Layout for a table box.

    For now only the fixed layout and separate border model are supported.

    """
    # Avoid a circular import
    from .blocks import block_container_layout

    column_widths = table.column_widths

    if table.style.border_collapse == 'separate':
        border_spacing_x, border_spacing_y = table.style.border_spacing
    else:
        border_spacing_x = 0
        border_spacing_y = 0

    # TODO: reverse this for direction: rtl
    column_positions = table.column_positions = []
    position_x = table.content_box_x()
    rows_x = position_x + border_spacing_x
    for width in column_widths:
        position_x += border_spacing_x
        column_positions.append(position_x)
        position_x += width
    rows_width = position_x - rows_x

    if table.style.border_collapse == 'collapse':
        if skip_stack:
            skipped_groups, group_skip_stack = skip_stack
            if group_skip_stack:
                skipped_rows, _ = group_skip_stack
            else:
                skipped_rows = 0
            for group in table.children[:skipped_groups]:
                skipped_rows += len(group.children)
        else:
            skipped_rows = 0
        _, horizontal_borders = table.collapsed_border_grid
        if horizontal_borders:
            table.style.border_top_width = table.border_top_width = max(
                width for _, (_, width, _)
                in horizontal_borders[skipped_rows]) / 2

    # Make this a sub-function so that many local variables like rows_x
    # need not be passed as parameters.
    def group_layout(group, position_y, max_position_y,
                     page_is_empty, skip_stack):
        resume_at = None
        resolve_percentages(group, table, context)
        group.position_x = rows_x
        group.position_y = position_y
        group.width = rows_width
        new_group_children = []
        # For each rows, cells for which this is the last row (with rowspan)
        ending_cells_by_row = [[] for row in group.children]

        is_group_start = skip_stack is None
        if is_group_start:
            skip = 0
        else:
            skip, skip_stack = skip_stack
            assert not skip_stack  # No breaks inside rows for now
        for index_row, row in group.enumerate_skip(skip):
            resolve_percentages(row, table, context)
            row.position_x = rows_x
            row.position_y = position_y
            row.width = rows_width
            # Place cells at the top of the row and layout their content
            new_row_children = []
            for cell in row.children:
                spanned_widths = column_widths[cell.grid_x:][:cell.colspan]
                # In the fixed layout the grid width is set by cells in
                # the first row and column elements.
                # This may be less than the previous value  of cell.colspan
                # if that would bring the cell beyond the grid width.
                cell.colspan = len(spanned_widths)
                if cell.colspan == 0:
                    # The cell is entierly beyond the grid width, remove it
                    # entierly. Subsequent cells in the same row have greater
                    # grid_x, so they are beyond too.
                    cell_index = row.children.index(cell)
                    ignored_cells = row.children[cell_index:]
                    LOGGER.warning('This table row has more columns than '
                                   'the table, ignored %i cells: %r',
                                   len(ignored_cells), ignored_cells)
                    break
                resolve_percentages(cell, table, context)
                cell.position_x = column_positions[cell.grid_x]
                cell.position_y = row.position_y
                cell.margin_top = 0
                cell.margin_left = 0
                cell.width = 0
                borders_plus_padding = cell.border_width()  # with width==0
                cell.width = (
                    sum(spanned_widths)
                    + border_spacing_x * (cell.colspan - 1)
                    - borders_plus_padding)
                # The computed height is a minimum
                cell.computed_height = cell.height
                cell.height = 'auto'
                cell, _, _, _, _ = block_container_layout(
                    context, cell,
                    max_position_y=float('inf'),
                    skip_stack=None,
                    device_size=device_size,
                    page_is_empty=True,
                    absolute_boxes=absolute_boxes,
                    fixed_boxes=fixed_boxes)
                cell.content_height = cell.height
                if cell.computed_height != 'auto':
                    cell.height = max(cell.height, cell.computed_height)
                new_row_children.append(cell)

            row = row.copy_with_children(new_row_children)

            # Table height algorithm
            # http://www.w3.org/TR/CSS21/tables.html#height-layout

            # cells with vertical-align: baseline
            baseline_cells = []
            for cell in row.children:
                vertical_align = cell.style.vertical_align
                if vertical_align in ('top', 'middle', 'bottom'):
                    cell.vertical_align = vertical_align
                else:
                    # Assume 'baseline' for any other value
                    cell.vertical_align = 'baseline'
                    cell.baseline = cell_baseline(cell)
                    baseline_cells.append(cell)
            if baseline_cells:
                row.baseline = max(cell.baseline for cell in baseline_cells)
                for cell in baseline_cells:
                    if cell.baseline != row.baseline:
                        add_top_padding(cell, row.baseline - cell.baseline)
            else:
                row.baseline = None

            # row height
            for cell in row.children:
                ending_cells_by_row[cell.rowspan - 1].append(cell)
            ending_cells = ending_cells_by_row.pop(0)
            if ending_cells:  # in this row
                row_bottom_y = max(
                    cell.position_y + cell.border_height()
                    for cell in ending_cells)
                if row.height == 'auto':
                    row.height = row_bottom_y - row.position_y
                else:
                    row.height = max(row.height, max(
                        row_cell.height for row_cell in ending_cells))
            else:
                row_bottom_y = row.position_y
                row.height = 0

            # Add extra padding to make the cells the same height as the row
            # and honor vertical-align
            for cell in ending_cells:
                cell_bottom_y = cell.position_y + cell.border_height()
                extra = row_bottom_y - cell_bottom_y
                if cell.vertical_align == 'bottom':
                    add_top_padding(cell, extra)
                elif cell.vertical_align == 'middle':
                    extra /= 2.
                    add_top_padding(cell, extra)
                    cell.padding_bottom += extra
                else:
                    cell.padding_bottom += extra
                if cell.computed_height != 'auto':
                    vertical_align_shift = 0
                    if cell.vertical_align == 'middle':
                        vertical_align_shift = (
                            cell.computed_height - cell.content_height) / 2
                    elif cell.vertical_align == 'bottom':
                        vertical_align_shift = (
                            cell.computed_height - cell.content_height)
                    if vertical_align_shift > 0:
                        for child in cell.children:
                            child.translate(dy=vertical_align_shift)

            next_position_y = position_y + row.height + border_spacing_y
            # Break if this row overflows the page, unless there is no
            # other content on the page.
            if next_position_y > max_position_y and not page_is_empty:
                resume_at = (index_row, None)
                break

            position_y = next_position_y
            new_group_children.append(row)
            page_is_empty = False

        # Do not keep the row group if we made a page break
        # before any of its rows or with 'avoid'
        if resume_at and (group.style.page_break_inside == 'avoid'
                          or not new_group_children):
            return None, None

        group = group.copy_with_children(
            new_group_children,
            is_start=is_group_start, is_end=resume_at is None)

        # Set missing baselines in a second loop because of rowspan
        for row in group.children:
            if row.baseline is None:
                if row.children:
                    # lowest bottom content edge
                    row.baseline = max(
                        cell.content_box_y() + cell.height
                        for cell in row.children) - row.position_y
                else:
                    row.baseline = 0
        group.height = position_y - group.position_y
        if group.children:
            # The last border spacing is outside of the group.
            group.height -= border_spacing_y

        return group, resume_at

    def body_groups_layout(skip_stack, position_y, max_position_y,
                           page_is_empty):
        if skip_stack is None:
            skip = 0
        else:
            skip, skip_stack = skip_stack
        new_table_children = []
        resume_at = None
        for index_group, group in table.enumerate_skip(skip):
            if group.is_header or group.is_footer:
                continue
            new_group, resume_at = group_layout(
                group, position_y, max_position_y, page_is_empty, skip_stack)
            skip_stack = None

            if new_group is None:
                resume_at = (index_group, None)
                break

            new_table_children.append(new_group)
            position_y += new_group.height + border_spacing_y
            page_is_empty = False

            if resume_at:
                resume_at = (index_group, resume_at)
                break
        return new_table_children, resume_at, position_y

    # Layout for row groups, rows and cells
    position_y = table.content_box_y() + border_spacing_y
    initial_position_y = position_y

    def all_groups_layout():
        if table.children and table.children[0].is_header:
            header = table.children[0]
            header, resume_at = group_layout(
                header, position_y, max_position_y,
                skip_stack=None, page_is_empty=False)
            if header and not resume_at:
                header_height = header.height + border_spacing_y
            else:  # Header too big for the page
                header = None
        else:
            header = None

        if table.children and table.children[-1].is_footer:
            footer = table.children[-1]
            footer, resume_at = group_layout(
                footer, position_y, max_position_y,
                skip_stack=None, page_is_empty=False)
            if footer and not resume_at:
                footer_height = footer.height + border_spacing_y
            else:  # Footer too big for the page
                footer = None
        else:
            footer = None

        if header and footer:
            # Try with both the header and footer
            new_table_children, resume_at, end_position_y = body_groups_layout(
                skip_stack,
                position_y=position_y + header_height,
                max_position_y=max_position_y - footer_height,
                page_is_empty=False)
            if new_table_children or not page_is_empty:
                footer.translate(dy=end_position_y - footer.position_y)
                end_position_y += footer_height
                return (header, new_table_children, footer,
                        end_position_y, resume_at)
            else:
                # We could not fit any content, drop the footer
                footer = None

        if header and not footer:
            # Try with just the header
            new_table_children, resume_at, end_position_y = body_groups_layout(
                skip_stack,
                position_y=position_y + header_height,
                max_position_y=max_position_y,
                page_is_empty=False)
            if new_table_children or not page_is_empty:
                return (header, new_table_children, footer,
                        end_position_y, resume_at)
            else:
                # We could not fit any content, drop the footer
                header = None

        if footer and not header:
            # Try with just the footer
            new_table_children, resume_at, end_position_y = body_groups_layout(
                skip_stack,
                position_y=position_y,
                max_position_y=max_position_y - footer_height,
                page_is_empty=False)
            if new_table_children or not page_is_empty:
                footer.translate(dy=end_position_y - footer.position_y)
                end_position_y += footer_height
                return (header, new_table_children, footer,
                        end_position_y, resume_at)
            else:
                # We could not fit any content, drop the footer
                footer = None

        assert not (header or footer)
        new_table_children, resume_at, end_position_y = body_groups_layout(
            skip_stack, position_y, max_position_y, page_is_empty)
        return header, new_table_children, footer, end_position_y, resume_at

    header, new_table_children, footer, position_y, resume_at = \
        all_groups_layout()
    table = table.copy_with_children(
        ([header] if header is not None else []) +
        new_table_children +
        ([footer] if footer is not None else []),
        is_start=skip_stack is None, is_end=resume_at is None)
    if table.style.border_collapse == 'collapse':
        table.skipped_rows = skipped_rows

    # If the height property has a bigger value, just add blank space
    # below the last row group.
    table.height = max(
        table.height if table.height != 'auto' else 0,
        position_y - table.content_box_y())

    # Layout for column groups and columns
    columns_height = position_y - initial_position_y
    if table.children:
        # The last border spacing is below the columns.
        columns_height -= border_spacing_y
    for group in table.column_groups:
        for column in group.children:
            resolve_percentages(column, table, context)
            column.position_x = column_positions[column.grid_x]
            column.position_y = initial_position_y
            column.width = column_widths[column.grid_x]
            column.height = columns_height
        resolve_percentages(group, table, context)
        first = group.children[0]
        last = group.children[-1]
        group.position_x = first.position_x
        group.position_y = initial_position_y
        group.width = last.position_x + last.width - first.position_x
        group.height = columns_height

    if resume_at and not page_is_empty and (
            table.style.page_break_inside == 'avoid'
            or not new_table_children):
        table = None
        resume_at = None
    next_page = 'any'
    adjoining_margins = []
    collapsing_through = False
    return table, resume_at, next_page, adjoining_margins, collapsing_through


def add_top_padding(box, extra_padding):
    """Increase the top padding of a box. This also translates the children.
    """
    box.padding_top += extra_padding
    for child in box.children:
        child.translate(dy=extra_padding)


def fixed_table_layout(context, box):
    """Run the fixed table layout and return a list of column widths

    http://www.w3.org/TR/CSS21/tables.html#fixed-table-layout

    """
    table = box.get_wrapped_table()
    assert table.width != 'auto'

    all_columns = [column for column_group in table.column_groups
                   for column in column_group.children]
    if table.children and table.children[0].children:
        first_rowgroup = table.children[0]
        first_row_cells = first_rowgroup.children[0].children
    else:
        first_row_cells = []
    num_columns = max(
        len(all_columns),
        sum(cell.colspan for cell in first_row_cells)
    )
    # ``None`` means not know yet.
    column_widths = [None] * num_columns

    # `width` on column boxes
    for i, column in enumerate(all_columns):
        resolve_one_percentage(column, 'width', table.width, context)
        if column.width != 'auto':
            column_widths[i] = column.width

    if table.style.border_collapse == 'separate':
        border_spacing_x, _ = table.style.border_spacing
    else:
        border_spacing_x = 0

    # `width` on cells of the first row.
    i = 0
    for cell in first_row_cells:
        resolve_percentages(cell, table, context)
        if cell.width != 'auto':
            width = cell.border_width()
            width -= border_spacing_x * (cell.colspan - 1)
            # In the general case, this width affects several columns (through
            # colspan) some of which already have a width. Subtract these
            # known widths and divide among remaining columns.
            columns_without_width = []  # and occupied by this cell
            for j in xrange(i, i + cell.colspan):
                if column_widths[j] is None:
                    columns_without_width.append(j)
                else:
                    width -= column_widths[j]
            if columns_without_width:
                width_per_column = width / len(columns_without_width)
                for j in columns_without_width:
                    column_widths[j] = width_per_column
            del width
        i += cell.colspan
    del i

    # Distribute the remaining space equally on columns that do not have
    # a width yet.
    all_border_spacing = border_spacing_x * (num_columns + 1)
    min_table_width = (sum(w for w in column_widths if w is not None)
                       + all_border_spacing)
    columns_without_width = [i for i, width in enumerate(column_widths)
                             if width is None]
    if columns_without_width and table.width >= min_table_width:
        remaining_width = table.width - min_table_width
        width_per_column = remaining_width / len(columns_without_width)
        for i in columns_without_width:
            column_widths[i] = width_per_column
    else:
        # XXX this is bad, but we were given a broken table to work with...
        for i in columns_without_width:
            column_widths[i] = 0

    # If the sum is less than the table width,
    # distribute the remaining space equally
    extra_width = table.width - sum(column_widths) - all_border_spacing
    if extra_width <= 0:
        # substract a negative: widen the table
        table.width -= extra_width
    elif num_columns:
        extra_per_column = extra_width / num_columns
        column_widths = [width + extra_per_column for width in column_widths]

    # Now we have table.width == sum(column_widths) + all_border_spacing
    # with possible floating point rounding errors.
    # (unless there is zero column)
    table.column_widths = column_widths


def auto_table_layout(context, box, containing_block):
    """Run the auto table layout and return a list of column widths.

    http://www.w3.org/TR/CSS21/tables.html#auto-table-layout

    """
    table = box.get_wrapped_table()
    (table_preferred_minimum_width, table_preferred_width,
     column_preferred_minimum_widths, column_preferred_widths) = \
        table_and_columns_preferred_widths(
            context, box, resolved_table_width=table.width != 'auto')

    if table.style.border_collapse == 'separate':
        border_spacing_x, _ = table.style.border_spacing
    else:
        border_spacing_x = 0

    all_border_spacing = (
        border_spacing_x * (len(column_preferred_widths) + 1))

    margins = 0
    if box.margin_left != 'auto':
        margins += box.margin_left
    if box.margin_right != 'auto':
        margins += box.margin_right

    cb_width, cb_height = containing_block
    available_width = cb_width - margins
    if table.width == 'auto':
        if available_width < table_preferred_minimum_width:
            table.width = table_preferred_minimum_width
            table.column_widths = column_preferred_minimum_widths
        elif available_width < table_preferred_width:
            table.width = available_width
            table.column_widths = column_preferred_minimum_widths
        else:
            table.width = table_preferred_width
            table.column_widths = column_preferred_widths
    else:
        if table.width < table_preferred_minimum_width:
            table.width = table_preferred_minimum_width
            table.column_widths = column_preferred_minimum_widths
        elif table.width < table_preferred_width:
            table.column_widths = column_preferred_minimum_widths
        else:
            table.column_widths = column_preferred_widths

    lost_width = table.width - sum(table.column_widths) - all_border_spacing
    if lost_width > 0:
        sum_column_preferred_widths = sum(column_preferred_widths)
        if sum_column_preferred_widths:
            table.column_widths = [
                (column_width + lost_width * preferred_column_width /
                 sum_column_preferred_widths)
                for (preferred_column_width, column_width)
                in zip(column_preferred_widths, table.column_widths)]
        else:
            table.column_widths = [
                column_width + lost_width / len(table.column_widths)
                for column_width in table.column_widths]


def table_wrapper_width(context, wrapper, containing_block):
    """Find the width of each column and derive the wrapper width."""
    table = wrapper.get_wrapped_table()
    resolve_percentages(table, containing_block, context)

    if table.style.table_layout == 'fixed' and table.width != 'auto':
        fixed_table_layout(context, wrapper)
    else:
        auto_table_layout(context, wrapper, containing_block)

    wrapper.width = table.border_width()
    wrapper.style.width = Dimension(wrapper.width, 'px')


def cell_baseline(cell):
    """
    Return the y position of a cell’s baseline from the top of its border box.

    See http://www.w3.org/TR/CSS21/tables.html#height-layout

    """
    result = find_in_flow_baseline(
        cell, baseline_types=(boxes.LineBox, boxes.TableRowBox))
    if result is not None:
        return result - cell.position_y
    else:
        # Default to the bottom of the content area.
        return cell.border_top_width + cell.padding_top + cell.height


def find_in_flow_baseline(box, last=False, baseline_types=(boxes.LineBox,)):
    """
    Return the absolute Y position for the first (or last) in-flow baseline
    if any, or None.
    """
    if isinstance(box, baseline_types):
        return box.position_y + box.baseline
    if isinstance(box, boxes.ParentBox) and not isinstance(
            box, boxes.TableCaptionBox):
        children = reversed(box.children) if last else box.children
        for child in children:
            if child.is_in_normal_flow():
                result = find_in_flow_baseline(child, last, baseline_types)
                if result is not None:
                    return result
