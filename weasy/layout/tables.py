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
Functions laying out tables.

"""

from __future__ import division

from .percentages import resolve_percentages, resolve_one_percentage


def table_layout(table, containing_block, device_size):
    """Layout for a table box.

    For now only the fixed layout and separate border model are supported.

    """
    # Avoid a circular import
    from .blocks import block_level_height

#    assert table.style.table_layout == 'fixed'
#    assert table.style.border_collapse == 'separate'

    assert table.width != 'auto'

    all_columns = [column for column_group in table.column_groups
                          for column in column_group.children]
    first_row_group = table.children[0]
    first_row = first_row_group.children[0]
    num_columns = max(
        len(all_columns),
        sum(cell.colspan for cell in first_row.children)
    )
    # ``None`` means not know yet.
    column_widths = [None] * num_columns

    # http://www.w3.org/TR/CSS21/tables.html#fixed-table-layout
    for i, column in enumerate(all_columns):
        resolve_one_percentage(column, 'width', table.width, ['auto'])
        if column.width != 'auto':
            column_widths[i] = column.width

    border_spacing_x, border_spacing_y = table.style.border_spacing
    i = 0
    for cell in first_row.children:
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
        # XXX this is bad, we were given a broken table to work with...
        for i in columns_without_width:
            column_widths[i] = 0

    extra_width = table.width - sum(column_widths) - all_border_spacing
    if extra_width <= 0:
        # substract a negative: widen the table
        table.width -= extra_width
    else:
        extra_per_column = extra_width / num_columns
        column_widths = [w + extra_per_column for w in column_widths]

    # Now we have table.width == sum(column_widths) + all_border_spacing
    # with possible floating point rounding errors.

    column_positions = []
    position_x = 0
    for width in column_widths:
        position_x += border_spacing_x
        column_positions.append(position_x)
        position_x += width

    # Layout for row groups, rows and cells
    # positions are relative to the table for now.
    for group in table.children:
        group.position_x = 0
        group.position_y = 0
        group.width = table.width
        group.height = 0
        for row in group.children:
            row.position_x = 0
            row.position_y = 0
            row.width = table.width
            row.height = 0
            new_row_children = []
            for cell in row.children:
                cell.position_x = column_positions[cell.grid_x]
                cell.position_y = 0
                resolve_percentages(cell, containing_block)
                cell.width = 0
                borders_plus_padding = cell.border_width()
                cell.width = (
                    sum(column_widths[cell.grid_x:cell.grid_x + cell.colspan])
                    + border_spacing_x * (cell.colspan - 1)
                    - borders_plus_padding)
                new_cell, _ = block_level_height(cell,
                    max_position_y=None,
                    skip_stack=None,
                    device_size=device_size,
                    page_is_empty=True)
                new_row_children.append(new_cell)
            # XXX mutating immutable objects! bad!
            row.children = tuple(new_row_children)

    table.height = 0  # XXX

    # Layout for column groups and columns
    for group in table.column_groups:
        for column in group.children:
            column.position_x = column_positions[column.grid_x]
            column.position_y = 0
            column.width = column_widths[column.grid_x]
            column.height = table.height
        first = group.children[0]
        last = group.children[-1]
        group.position_x = first.position_x
        group.position_y = 0
        group.width = last.position_x + last.width - first.position_x
        group.height = table.height
