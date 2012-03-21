# coding: utf8
"""
    weasyprint.layout.tables
    ------------------------

    Layout for tables and internal table boxes.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from ..compat import xrange
from ..logger import LOGGER
from ..formatting_structure import boxes
from .percentages import resolve_percentages, resolve_one_percentage


def table_layout(document, table, max_position_y, skip_stack,
                 containing_block, device_size, page_is_empty):
    """Layout for a table box.

    For now only the fixed layout and separate border model are supported.

    """
    # Avoid a circular import
    from .blocks import block_level_height

    column_widths = table.column_widths

    border_spacing_x, border_spacing_y = table.style.border_spacing
    # TODO: reverse this for direction: rtl
    column_positions = []
    position_x = table.content_box_x()
    rows_x = position_x + border_spacing_x
    for width in column_widths:
        position_x += border_spacing_x
        column_positions.append(position_x)
        position_x += width
    rows_width = position_x - rows_x

    if skip_stack is None:
        skip = 0
    else:
        skip, skip_stack = skip_stack

    resume_at = None

    # Layout for row groups, rows and cells
    position_y = table.content_box_y() + border_spacing_y
    initial_position_y = position_y
    new_table_children = []
    for index_group, group in table.enumerate_skip(skip):
        resolve_percentages(group, containing_block=table)
        group.position_x = rows_x
        group.position_y = position_y
        group.width = rows_width
        new_group_children = []
        # For each rows, cells for which this is the last row (with rowspan)
        ending_cells_by_row = [[] for row in group.children]

        if skip_stack is None:
            skip = 0
        else:
            skip, skip_stack = skip_stack
        for index_row, row in group.enumerate_skip(skip):
            resolve_percentages(row, containing_block=table)
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
                    LOGGER.warn('This table row has more columns than '
                                'the table, ignored %i cells: %r',
                                len(ignored_cells), ignored_cells)
                    break
                resolve_percentages(cell, containing_block=table)
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
                computed_cell_height = cell.height
                cell.height = 'auto'
                cell, _, _, _, _ = block_level_height(
                    document, cell,
                    max_position_y=float('inf'),
                    skip_stack=None,
                    device_size=device_size,
                    page_is_empty=True)
                if computed_cell_height != 'auto':
                    cell.height = max(cell.height, computed_cell_height)
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
                row.height = row_bottom_y - row.position_y
            else:
                row_bottom_y = row.position_y
                row.height = 0

            # Add extra padding to make the cells the same height as the row
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

            next_position_y = position_y + row.height + border_spacing_y
            # Break if this row overflows the page, unless there is no
            # other content on the page.
            if next_position_y > max_position_y and (
                    new_table_children or new_group_children
                    or not page_is_empty):
                resume_at = (index_row, None)
                break

            position_y = next_position_y
            new_group_children.append(row)

        skip_stack = None

        if resume_at and group.style.page_break_inside == 'avoid':
            resume_at = (index_group, None)
            break

        # Do not keep the row group if we made a page break
        # before any of its rows.
        if not (group.children and not new_group_children):
            group = group.copy_with_children(new_group_children)
            new_table_children.append(group)

            # Set missing baselines in a second loop because of rowspan
            for row in group.children:
                if row.baseline is None:
                    if row.children:
                        # lowest bottom content edge
                        row.baseline = row.position_y - max(
                            cell.content_box_y() + cell.height
                            for cell in row.children)
                    else:
                        row.baseline = 0
            group.height = position_y - group.position_y
            if group.children:
                # The last border spacing is outside of the group.
                group.height -= border_spacing_y

        if resume_at:
            resume_at = (index_group, resume_at)
            break

    table = table.copy_with_children(new_table_children)

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
            resolve_percentages(column, containing_block=table)
            column.position_x = column_positions[column.grid_x]
            column.position_y = initial_position_y
            column.width = column_widths[column.grid_x]
            column.height = columns_height
        resolve_percentages(group, containing_block=table)
        first = group.children[0]
        last = group.children[-1]
        group.position_x = first.position_x
        group.position_y = initial_position_y
        group.width = last.position_x + last.width - first.position_x
        group.height = columns_height

    if resume_at and not page_is_empty and (
            table.style.page_break_inside == 'avoid'):
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


def fixed_table_layout(table):
    """Run the fixed table layout and return a list of column widths

    http://www.w3.org/TR/CSS21/tables.html#fixed-table-layout

    """
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
        resolve_one_percentage(column, 'width', table.width, ['auto'])
        if column.width != 'auto':
            column_widths[i] = column.width

    # `width` on cells of the first row.
    border_spacing_x, border_spacing_y = table.style.border_spacing
    i = 0
    for cell in first_row_cells:
        resolve_percentages(cell, table)
        if cell.width != 'auto':
            width = cell.border_width()
            width -= border_spacing_x * (cell.colspan - 1)
            # In the general case, this width affects several columns (through
            # colspan) some of which already have a width. Subscract these
            # known widths and divide among remaining columns.
            columns_without_width = []  # and occupied by this cell
            for j in xrange(i, i + cell.colspan):
                if column_widths[j] is None:
                    columns_without_width.append(j)
                else:
                    width -= column_widths[j]
            width_per_column = width / len(columns_without_width)
            for j in columns_without_width:
                column_widths[j] = width_per_column
        i += cell.colspan

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
        column_widths = [w + extra_per_column for w in column_widths]

    # Now we have table.width == sum(column_widths) + all_border_spacing
    # with possible floating point rounding errors.
    # (unless there is zero column)
    table.column_widths = column_widths
    return column_widths


def cell_baseline(cell):
    """
    Return the y position of a cell’s baseline from the top of its border box.

    See http://www.w3.org/TR/CSS21/tables.html#height-layout

    """
    # Do not use cell.descendants() as we do not want to recurse into
    # out-of-flow children.
    stack = [iter(cell.children)]  # DIY recursion
    while stack:
        child = next(stack[-1], None)
        if child is None:
            stack.pop()
            continue
        if not child.is_in_normal_flow():
            continue
        if isinstance(child, (boxes.LineBox, boxes.TableRowBox)):
            # First in-flow line or row.
            return child.baseline + child.position_y - cell.position_y
        if isinstance(child, boxes.ParentBox):
            stack.append(iter(child.children))
    # Default to the bottom of the content area.
    return cell.border_top_width + cell.padding_top + cell.height
