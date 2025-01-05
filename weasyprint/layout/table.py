"""Layout for tables and internal table boxes."""

from math import inf

import tinycss2.color4

from ..formatting_structure import boxes
from ..logger import LOGGER
from .percent import resolve_one_percentage, resolve_percentages
from .preferred import table_and_columns_preferred_widths


def table_layout(context, table, bottom_space, skip_stack, containing_block,
                 page_is_empty, absolute_boxes, fixed_boxes):
    """Layout for a table box."""
    from .block import (  # isort:skip
        avoid_page_break, block_container_layout, block_level_page_break,
        find_earlier_page_break, force_page_break, remove_placeholders)

    # Remove top and bottom decorations for split tables.
    has_header = table.children and table.children[0].is_header
    has_footer = table.children and table.children[-1].is_footer
    collapse = table.style['border_collapse'] == 'collapse'
    remove_start_decoration = skip_stack is not None and not has_header
    table.remove_decoration(remove_start_decoration, end=False)

    # Set border spacings.
    if collapse:
        border_spacing_x = border_spacing_y = 0
    else:
        border_spacing_x, border_spacing_y = table.style['border_spacing']

    # Define column positions.
    column_widths = table.column_widths
    column_positions = table.column_positions = []
    rows_left_x = table.content_box_x() + border_spacing_x
    if table.style['direction'] == 'ltr':
        position_x = table.content_box_x()
        rows_x = position_x + border_spacing_x
        for width in column_widths:
            position_x += border_spacing_x
            column_positions.append(position_x)
            position_x += width
        rows_width = position_x - rows_x
    else:
        position_x = table.content_box_x() + table.width
        rows_x = position_x - border_spacing_x
        for width in column_widths:
            position_x -= border_spacing_x
            position_x -= width
            column_positions.append(position_x)
        rows_width = rows_x - position_x

    # Set border top width on tables with collapsed borders and split cells.
    if collapse:
        table.skip_cell_border_top = False
        table.skip_cell_border_bottom = False
        split_cells = False
        if skip_stack:
            (skipped_groups, group_skip_stack), = skip_stack.items()
            if group_skip_stack:
                (skipped_rows, cells_skip_stack), = group_skip_stack.items()
                if cells_skip_stack:
                    split_cells = True
            else:
                skipped_rows = 0
            for group in table.children[:skipped_groups]:
                skipped_rows += len(group.children)
        else:
            skipped_rows = 0
        if not split_cells and not has_header:
            _, horizontal_borders = table.collapsed_border_grid
            if horizontal_borders:
                table.border_top_width = max(
                    width for _, (_, width, _)
                    in horizontal_borders[skipped_rows]) / 2

    # Make this a sub-function so that many local variables like rows_x
    # don't need to be passed as parameters.
    def group_layout(group, position_y, bottom_space, page_is_empty, skip_stack):
        resume_at = None
        next_page = {'break': 'any', 'page': None}
        original_page_is_empty = page_is_empty
        resolve_percentages(group, containing_block=table)
        group.position_x = rows_left_x
        group.position_y = position_y
        group.width = rows_width
        new_group_children = []
        # For each row, cells for which this is the last row (with rowspan).
        ending_cells_by_row = [[] for row in group.children]

        is_group_start = skip_stack is None
        if is_group_start:
            skip = 0
        else:
            (skip, skip_stack), = skip_stack.items()
        for index_row, row in enumerate(group.children[skip:], start=skip):
            row.index = index_row

            if new_group_children:
                page_break = block_level_page_break(
                    new_group_children[-1], row)
                if force_page_break(page_break, context):
                    next_page['break'] = page_break
                    resume_at = {index_row: None}
                    break

            resolve_percentages(row, containing_block=table)
            row.position_x = rows_left_x
            row.position_y = position_y
            row.width = rows_width
            # Place cells at the top of the row and layout their content.
            new_row_children = []
            for index_cell, cell in enumerate(row.children):
                spanned_widths = column_widths[cell.grid_x:][:cell.colspan]
                # In the fixed layout the grid width is set by cells in
                # the first row and column elements.
                # This may be less than the previous value of cell.colspan
                # if that would bring the cell beyond the grid width.
                cell.colspan = len(spanned_widths)
                if cell.colspan == 0:
                    # The cell is entierly beyond the grid width, remove it
                    # entierly. Subsequent cells in the same row have greater
                    # grid_x, so they are beyond too.
                    cell_index = row.children.index(cell)
                    ignored_cells = row.children[cell_index:]
                    LOGGER.warning(
                        'This table row has more columns than the table, '
                        f'ignored {len(ignored_cells)} cells: {ignored_cells}')
                    break
                resolve_percentages(cell, containing_block=table)
                if table.style['direction'] == 'ltr':
                    cell.position_x = column_positions[cell.grid_x]
                else:
                    cell.position_x = column_positions[cell.grid_x + cell.colspan - 1]
                cell.position_y = row.position_y
                cell.margin_top = 0
                cell.margin_left = 0
                cell.width = 0
                borders_plus_padding = cell.border_width()  # with width==0
                # TODO: we should remove the number of columns with no
                # originating cells to cell.colspan, see test_layout_table_auto_49.
                cell.width = (
                    sum(spanned_widths) +
                    border_spacing_x * (cell.colspan - 1) -
                    borders_plus_padding)
                if skip_stack:
                    if index_cell in skip_stack:
                        cell_skip_stack = skip_stack[index_cell]
                    else:
                        cell_skip_stack = {len(cell.children): None}
                else:
                    cell_skip_stack = None

                # Adapt cell and table collapsing borders when a row is split.
                if cell_skip_stack and collapse:
                    if has_header:
                        # We have a header, we have to adapt the position of
                        # the split cell to match the header’s bottom border.
                        header_rows = table.children[0].children
                        if header_rows and header_rows[-1].children:
                            cell.position_y += max(
                                header.border_bottom_width
                                for header in header_rows[-1].children)
                    else:
                        # We don’t have a header, we have to skip the
                        # decoration at the top of the table when it’s drawn.
                        table.skip_cell_border_top = True

                # First try to render content as if there was already something
                # on the page to avoid hitting block_level_layout’s TODO. Then
                # force to render something if the page is actually empty, or
                # just draw an empty cell otherwise. See
                # test_table_break_children_margin.
                # Pretend that height is not set, keeping computed height as a minimum.
                cell.computed_height = cell.height
                cell.height = 'auto'
                original_style = cell.style
                if cell.style['height'] != 'auto':
                    style_copy = cell.style.copy()
                    style_copy['height'] = 'auto'
                    cell.style = style_copy
                new_cell, cell_resume_at, _, _, _, _ = block_container_layout(
                    context, cell, bottom_space, cell_skip_stack,
                    page_is_empty=page_is_empty, absolute_boxes=absolute_boxes,
                    fixed_boxes=fixed_boxes, adjoining_margins=None,
                    discard=False, max_lines=None)
                cell.style = original_style
                if new_cell is None:
                    cell = cell.copy_with_children([])
                    cell, _, _, _, _, _ = block_container_layout(
                        context, cell, bottom_space, cell_skip_stack,
                        page_is_empty=True, absolute_boxes=[], fixed_boxes=[],
                        adjoining_margins=None, discard=False, max_lines=None)
                    cell_resume_at = {0: None}
                else:
                    cell = new_cell

                cell.remove_decoration(start=cell_skip_stack is not None, end=False)
                if cell_resume_at:
                    if resume_at is None:
                        resume_at = {index_row: {}}
                    resume_at[index_row][index_cell] = cell_resume_at
                cell.empty = not any(
                    child.is_floated() or child.is_in_normal_flow()
                    for child in cell.children)
                cell.content_height = cell.height
                if cell.computed_height != 'auto':
                    cell.height = max(cell.height, cell.computed_height)
                new_row_children.append(cell)

            if resume_at and not page_is_empty:
                # Avoid break when "break-inside: avoid" is set on row or any
                # on its cells.
                avoid_break = (
                    avoid_page_break(row.style['break_inside'], context) or any(
                        avoid_page_break(cell.style['break_inside'], context)
                        for cell in row.children))
                if avoid_break:
                    resume_at = {index_row: {}}
                    remove_placeholders(
                        context, new_row_children, absolute_boxes, fixed_boxes)
                    break

            if resume_at:
                # Remove bottom decoration if row is split.
                for cell in new_row_children:
                    cell.remove_decoration(start=False, end=True)

            row = row.copy_with_children(new_row_children)

            # Table height algorithm
            # https://www.w3.org/TR/CSS21/tables.html#height-layout

            # Set row baseline with cells with vertical-align: baseline.
            baseline_cells = []
            for cell in row.children:
                vertical_align = cell.style['vertical_align']
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
                    extra = row.baseline - cell.baseline
                    if cell.baseline != row.baseline and extra:
                        add_top_padding(cell, extra)

            # Set row height.
            for cell in row.children:
                ending_cells_by_row[cell.rowspan - 1].append(cell)
            ending_cells = ending_cells_by_row.pop(0)
            if ending_cells:  # in this row
                if row.height == 'auto':
                    row_bottom_y = max(
                        cell.position_y + cell.border_height()
                        for cell in ending_cells)
                    row.height = max(row_bottom_y - row.position_y, 0)
                else:
                    row.height = max(row.height, max(
                        row_cell.border_height() for row_cell in ending_cells))
                    row_bottom_y = row.position_y + row.height
            else:
                row_bottom_y = row.position_y
                row.height = 0

            if not baseline_cells:
                row.baseline = row_bottom_y

            # Add extra padding to make the cells the same height as the row
            # and honor vertical-align.
            for cell in ending_cells:
                cell_bottom_y = cell.position_y + cell.border_height()
                extra = row_bottom_y - cell_bottom_y
                if extra:
                    if cell.vertical_align == 'bottom':
                        add_top_padding(cell, extra)
                    elif cell.vertical_align == 'middle':
                        extra /= 2
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

            next_position_y = row.position_y + row.height
            if resume_at is None:
                next_position_y += border_spacing_y

            # Break if one cell was broken.
            break_cell = False
            if resume_at:
                if all(child.empty for child in row.children):
                    # No cell was displayed, give up row.
                    next_position_y = inf
                    page_is_empty = False
                    resume_at = None
                else:
                    break_cell = True

            # Break if this row overflows the page, unless there is no
            # other content on the page.
            overflow = context.overflows_page(bottom_space, next_position_y)
            if not page_is_empty and overflow:
                remove_placeholders(context, row.children, absolute_boxes, fixed_boxes)
                if new_group_children:
                    previous_row = new_group_children[-1]
                    page_break = block_level_page_break(previous_row, row)
                    if avoid_page_break(page_break, context):
                        earlier_page_break = find_earlier_page_break(
                            context, new_group_children, absolute_boxes, fixed_boxes)
                        if earlier_page_break:
                            new_group_children, resume_at = earlier_page_break
                            break
                    else:
                        resume_at = {index_row: None}
                        break
                if original_page_is_empty:
                    resume_at = {index_row: None}
                else:
                    return None, None, next_page
                break

            new_group_children.append(row)
            position_y = next_position_y
            page_is_empty = False
            skip_stack = None

            if break_cell and collapse and not has_footer:
                table.skip_cell_border_bottom = True

            if break_cell or resume_at:
                break

        # Do not keep the row group if we made a page break
        # before any of its rows or with 'avoid'.
        abort = (
            resume_at and
            not original_page_is_empty and (
                avoid_page_break(group.style['break_inside'], context) or
                not new_group_children))
        if abort:
            remove_placeholders(
                context, new_group_children, absolute_boxes, fixed_boxes)
            return None, None, next_page

        group = group.copy_with_children(new_group_children)
        group.remove_decoration(start=not is_group_start, end=resume_at is not None)

        # Set missing baselines in a second loop because of rowspan.
        for row in group.children:
            if row.baseline is None:
                if row.children:
                    # Set baseline to lowest bottom content edge.
                    row.baseline = max(
                        cell.content_box_y() + cell.height
                        for cell in row.children) - row.position_y
                else:
                    row.baseline = 0
        group.height = position_y - group.position_y
        if group.children:
            # The last border spacing is outside of the group.
            group.height -= border_spacing_y

        return group, resume_at, next_page

    def body_groups_layout(skip_stack, position_y, bottom_space, page_is_empty):
        if skip_stack is None:
            skip = 0
        else:
            (skip, skip_stack), = skip_stack.items()
        new_table_children = []
        resume_at = None
        next_page = {'break': 'any', 'page': None}

        for i, group in enumerate(table.children[skip:]):
            if group.is_header or group.is_footer:
                continue

            # Index is useless for headers and footers, as we never want to
            # break pages after the header or before the footer.
            index_group = i + skip
            group.index = index_group

            if new_table_children:
                page_break = block_level_page_break(new_table_children[-1], group)
                if force_page_break(page_break, context):
                    next_page['break'] = page_break
                    resume_at = {index_group: None}
                    break

            new_group, resume_at, next_page = group_layout(
                group, position_y, bottom_space, page_is_empty, skip_stack)
            skip_stack = None

            if new_group is None:
                if new_table_children:
                    previous_group = new_table_children[-1]
                    page_break = block_level_page_break(previous_group, group)
                    if avoid_page_break(page_break, context):
                        earlier_page_break = find_earlier_page_break(
                            context, new_table_children, absolute_boxes, fixed_boxes)
                        if earlier_page_break is not None:
                            new_table_children, resume_at = earlier_page_break
                            break
                    resume_at = {index_group: None}
                else:
                    return None, None, next_page, position_y
                break

            new_table_children.append(new_group)
            position_y += new_group.height + border_spacing_y
            page_is_empty = False

            if resume_at:
                resume_at = {index_group: resume_at}
                break

        return new_table_children, resume_at, next_page, position_y

    # Layout row groups, rows and cells.
    position_y = table.content_box_y()
    if skip_stack is None:
        position_y += border_spacing_y
    initial_position_y = position_y
    table_rows = [
        child for child in table.children
        if not child.is_header and not child.is_footer]

    def all_groups_layout():
        # If the page is not empty, we try to render the header and the footer
        # on it. If the table does not fit on the page, we try to render it on
        # the next page.

        # If the page is empty and the header and footer are too big, there
        # are not rendered. If no row can be rendered because of the header and
        # the footer, the header and/or the footer are not rendered.

        if page_is_empty:
            header_footer_bottom_space = bottom_space
        else:
            header_footer_bottom_space = -inf

        if has_header:
            header = table.children[0]
            header, resume_at, next_page = group_layout(
                header, position_y, header_footer_bottom_space,
                skip_stack=None, page_is_empty=False)
            if header and not resume_at:
                header_height = header.height + border_spacing_y
            else:
                # Header too big for the page.
                header = None
        else:
            header = None

        if has_footer:
            footer = table.children[-1]
            footer, resume_at, next_page = group_layout(
                footer, position_y, header_footer_bottom_space,
                skip_stack=None, page_is_empty=False)
            if footer and not resume_at:
                footer_height = footer.height + border_spacing_y
            else:
                # Footer too big for the page.
                footer = None
        else:
            footer = None

        # Don't remove headers and footers if breaks are avoided in line groups
        if skip_stack:
            skip, = skip_stack
        else:
            skip = 0
        avoid_breaks = False
        for group in table.children[skip:]:
            if not group.is_header and not group.is_footer:
                avoid_breaks = avoid_page_break(group.style['break_inside'], context)
                break

        if header and footer:
            # Try with both the header and footer.
            new_table_children, resume_at, next_page, end_position_y = (
                body_groups_layout(
                    skip_stack, position_y + header_height,
                    bottom_space + footer_height, page_is_empty=avoid_breaks))
            if new_table_children or not table_rows or not page_is_empty:
                footer.translate(dy=end_position_y - footer.position_y)
                end_position_y += footer_height
                return (
                    header, new_table_children, footer, end_position_y, resume_at,
                    next_page)
            else:
                # We could not fit any content, drop the footer.
                footer = None

        if header and not footer:
            # Try with just the header.
            new_table_children, resume_at, next_page, end_position_y = (
                body_groups_layout(
                    skip_stack, position_y + header_height, bottom_space,
                    page_is_empty=avoid_breaks))
            if new_table_children or not table_rows or not page_is_empty:
                return (
                    header, new_table_children, footer, end_position_y, resume_at,
                    next_page)
            else:
                # We could not fit any content, drop the header.
                header = None

        if footer and not header:
            # Try with just the footer.
            new_table_children, resume_at, next_page, end_position_y = (
                body_groups_layout(
                    skip_stack, position_y, bottom_space + footer_height,
                    page_is_empty=avoid_breaks))
            if new_table_children or not table_rows or not page_is_empty:
                footer.translate(dy=end_position_y - footer.position_y)
                end_position_y += footer_height
                return (
                    header, new_table_children, footer, end_position_y, resume_at,
                    next_page)
            else:
                # We could not fit any content, drop the footer.
                footer = None

        assert not (header or footer)
        new_table_children, resume_at, next_page, end_position_y = (
            body_groups_layout(skip_stack, position_y, bottom_space, page_is_empty))
        return header, new_table_children, footer, end_position_y, resume_at, next_page

    def get_column_cells(table, column):
        """Return closure getting the column cells."""
        return lambda: [
            cell
            for row_group in table.children
            for row in row_group.children
            for cell in row.children
            if cell.grid_x == column.grid_x]

    header, new_table_children, footer, position_y, resume_at, next_page = (
        all_groups_layout())

    if new_table_children is None:
        assert resume_at is None
        table = None
        adjoining_margins = []
        collapsing_through = False
        return table, resume_at, next_page, adjoining_margins, collapsing_through

    table = table.copy_with_children(
        ([header] if header is not None else []) +
        new_table_children +
        ([footer] if footer is not None else []))
    table.column_groups = tuple(
        column_group.deepcopy() for column_group in table.column_groups)
    remove_end_decoration = resume_at is not None and not has_footer
    table.remove_decoration(remove_start_decoration, remove_end_decoration)
    if collapse:
        table.skipped_rows = skipped_rows

    # If the height property has a bigger value, just add blank space
    # below the last row group.
    table.height = max(
        table.height if table.height != 'auto' else 0,
        position_y - table.content_box_y())

    # Layout column groups and columns.
    columns_height = position_y - initial_position_y
    if table.children:
        # The last border spacing is below the columns.
        columns_height -= border_spacing_y
    for group in table.column_groups:
        for column in group.children:
            resolve_percentages(column, containing_block=table)
            if column.grid_x < len(column_positions):
                column.position_x = column_positions[column.grid_x]
                column.position_y = initial_position_y
                column.width = column_widths[column.grid_x]
                column.height = columns_height
            else:
                # Ignore extra empty columns.
                column.position_x = 0
                column.position_y = 0
                column.width = 0
                column.height = 0
            resolve_percentages(group, containing_block=table)
            column.get_cells = get_column_cells(table, column)
        first = group.children[0]
        last = group.children[-1]
        group.position_x = first.position_x
        group.position_y = initial_position_y
        group.width = last.position_x + last.width - first.position_x
        group.height = columns_height

    # Invert columns for drawing.
    if table.style['direction'] == 'rtl':
        column_widths.reverse()
        column_positions.reverse()

    avoid_break = avoid_page_break(table.style['break_inside'], context)
    if resume_at and not page_is_empty and avoid_break:
        remove_placeholders(context, [table], absolute_boxes, fixed_boxes)
        table = None
        resume_at = None
    adjoining_margins = []
    collapsing_through = False

    return table, resume_at, next_page, adjoining_margins, collapsing_through


def add_top_padding(box, extra_padding):
    """Increase the top padding of a box.

    This also translates the children.

    """
    box.padding_top += extra_padding
    for child in box.children:
        child.translate(dy=extra_padding)


def fixed_table_layout(box):
    """Run the fixed table layout and return a list of column widths.

    https://www.w3.org/TR/CSS21/tables.html#fixed-table-layout

    """
    table = box.get_wrapped_table()
    assert table.width != 'auto'

    all_columns = [
        column for column_group in table.column_groups
        for column in column_group.children]
    if table.children and table.children[0].children:
        first_rowgroup = table.children[0]
        first_row_cells = first_rowgroup.children[0].children
    else:
        first_row_cells = []
    num_columns = max(len(all_columns), sum(cell.colspan for cell in first_row_cells))
    # ``None`` means not know yet.
    column_widths = [None] * num_columns

    # Set width on column boxes.
    for i, column in enumerate(all_columns):
        resolve_one_percentage(column, 'width', table.width)
        if column.width != 'auto':
            column_widths[i] = column.width

    if table.style['border_collapse'] == 'separate':
        border_spacing_x, _ = table.style['border_spacing']
    else:
        border_spacing_x = 0

    # Set width on cells of the first row.
    i = 0
    for cell in first_row_cells:
        resolve_percentages(cell, table)
        if cell.width != 'auto':
            width = cell.border_width()
            width -= border_spacing_x * (cell.colspan - 1)
            # In the general case, this width affects several columns (through
            # colspan) some of which already have a width. Subtract these
            # known widths and divide among remaining columns.
            columns_without_width = []  # and occupied by this cell
            for j in range(i, i + cell.colspan):
                if column_widths[j] is None:
                    columns_without_width.append(j)
                else:
                    width -= column_widths[j]
            if columns_without_width:
                width_per_column = width / len(columns_without_width)
                for j in columns_without_width:
                    column_widths[j] = width_per_column
        i += cell.colspan

    # Distribute the remaining space equally on columns that do not have
    # a width yet.
    all_border_spacing = border_spacing_x * (num_columns + 1)
    min_table_width = (sum(w for w in column_widths if w is not None) +
                       all_border_spacing)
    columns_without_width = [i for i, w in enumerate(column_widths)
                             if w is None]
    if columns_without_width and table.width >= min_table_width:
        remaining_width = table.width - min_table_width
        width_per_column = remaining_width / len(columns_without_width)
        for i in columns_without_width:
            column_widths[i] = width_per_column
    else:
        # This is bad, but we were given a broken table.
        for i in columns_without_width:
            column_widths[i] = 0

    # If the sum is less than the table width, distribute the remaining space
    # equally.
    extra_width = table.width - sum(column_widths) - all_border_spacing
    if extra_width <= 0:
        # Substract a negative: widen the table.
        table.width -= extra_width
    elif num_columns:
        extra_per_column = extra_width / num_columns
        column_widths = [w + extra_per_column for w in column_widths]

    # Now we have table.width == sum(column_widths) + all_border_spacing
    # with possible floating point rounding errors (unless there is zero column).
    table.column_widths = column_widths


def auto_table_layout(context, box, containing_block):
    """Run the auto table layout and return a list of column widths.

    https://www.w3.org/TR/CSS21/tables.html#auto-table-layout

    """
    table = box.get_wrapped_table()
    (table_min_content_width, table_max_content_width,
     column_min_content_widths, column_max_content_widths,
     column_intrinsic_percentages, constrainedness,
     total_horizontal_border_spacing, grid) = table_and_columns_preferred_widths(
         context, box, outer=False)

    margins = 0
    if box.margin_left != 'auto':
        margins += box.margin_left
    if box.margin_right != 'auto':
        margins += box.margin_right
    paddings = table.padding_left + table.padding_right
    borders = table.border_left_width + table.border_right_width

    cb_width, _ = containing_block
    available_width = cb_width - margins - paddings - borders

    if table.width == 'auto':
        if available_width <= table_min_content_width:
            table.width = table_min_content_width
        elif available_width < table_max_content_width:
            table.width = available_width
        else:
            table.width = table_max_content_width
    else:
        if table.width < table_min_content_width:
            table.width = table_min_content_width

    if not grid:
        table.column_widths = []
        return

    assignable_width = table.width - total_horizontal_border_spacing
    min_content_guess = column_min_content_widths[:]
    min_content_percentage_guess = column_min_content_widths[:]
    min_content_specified_guess = column_min_content_widths[:]
    max_content_guess = column_max_content_widths[:]
    guesses = (
        min_content_guess, min_content_percentage_guess,
        min_content_specified_guess, max_content_guess)
    # See https://www.w3.org/TR/css-tables-3/#width-distribution-algorithm.
    for i in range(len(grid)):
        if column_intrinsic_percentages[i]:
            min_content_percentage_guess[i] = max(
                column_intrinsic_percentages[i] / 100 * assignable_width,
                column_min_content_widths[i])
            min_content_specified_guess[i] = min_content_percentage_guess[i]
            max_content_guess[i] = min_content_percentage_guess[i]
        elif constrainedness[i]:
            # Any other column that is constrained is assigned its max-content
            # width.
            min_content_specified_guess[i] = column_max_content_widths[i]

    if assignable_width < sum(max_content_guess):
        # Default values shouldn't be used, but we never know.
        # See https://github.com/Kozea/WeasyPrint/issues/770
        lower_guess = guesses[0]
        upper_guess = guesses[-1]

        # We have to work around floating point rounding errors here.
        # The 1e-9 value comes from PEP 485.
        for guess in guesses:
            if sum(guess) <= assignable_width * (1 + 1e-9):
                lower_guess = guess
            else:
                break
        for guess in guesses[::-1]:
            if sum(guess) >= assignable_width * (1 - 1e-9):
                upper_guess = guess
            else:
                break
        if upper_guess == lower_guess:
            table.column_widths = upper_guess
        else:
            added_widths = [
                upper_guess[i] - lower_guess[i] for i in range(len(grid))]
            available_ratio = (assignable_width - sum(lower_guess)) / sum(added_widths)
            table.column_widths = [
                lower_guess[i] + added_widths[i] * available_ratio
                for i in range(len(grid))]
    else:
        table.column_widths = max_content_guess
        excess_width = assignable_width - sum(max_content_guess)
        distribute_excess_width(
            context, grid, excess_width, table.column_widths, constrainedness,
            column_intrinsic_percentages, column_max_content_widths)


def table_wrapper_width(context, wrapper, containing_block):
    """Find the width of each column and derive the wrapper width."""
    table = wrapper.get_wrapped_table()
    resolve_percentages(table, containing_block)

    if table.style['table_layout'] == 'fixed' and table.width != 'auto':
        fixed_table_layout(wrapper)
    else:
        auto_table_layout(context, wrapper, containing_block)

    wrapper.width = table.border_width()


def cell_baseline(cell):
    """Return the y position of a cell baseline from the top of its border box.

    See https://www.w3.org/TR/CSS21/tables.html#height-layout

    """
    baseline_types = (boxes.LineBox, boxes.TableRowBox)
    result = find_in_flow_baseline(cell, baseline_types=baseline_types)
    if result is not None:
        return result - cell.position_y
    else:
        # Default to the bottom of the content area.
        return cell.border_top_width + cell.padding_top + cell.height


def find_in_flow_baseline(box, last=False, baseline_types=(boxes.LineBox,)):
    """Return the absolute y position for the first (or last) in-flow baseline.

    If there’s no in-flow baseline, return None.

    """
    # TODO: synthetize baseline when needed.
    # See https://www.w3.org/TR/css-align-3/#synthesize-baseline.
    if isinstance(box, baseline_types):
        return box.position_y + box.baseline
    elif isinstance(box, boxes.TableCaptionBox):
        return
    children = reversed(box.children) if last else box.children
    for child in children:
        if child.is_in_normal_flow():
            result = find_in_flow_baseline(child, last, baseline_types)
            if result is not None:
                return result


def distribute_excess_width(context, grid, excess_width, column_widths, constrainedness,
                            column_intrinsic_percentages, column_max_content_widths,
                            column_slice=slice(0, None)):
    """Distribute available width to columns.

    See https://www.w3.org/TR/css-tables-3/#distributing-width-to-columns

    """
    # First group.
    columns = [
        i for i, _ in enumerate(grid[column_slice], start=column_slice.start)
        if not constrainedness[i] and
        column_intrinsic_percentages[i] == 0 and
        column_max_content_widths[i] > 0]
    if columns:
        sum_max_content_widths = sum(column_max_content_widths[i] for i in columns)
        ratio = excess_width / sum_max_content_widths
        for i in columns:
            column_widths[i] += column_max_content_widths[i] * ratio
        return

    # Second group.
    columns = [
        i for i, _ in enumerate(grid[column_slice], start=column_slice.start)
        if not constrainedness[i] and column_intrinsic_percentages[i] == 0]
    if columns:
        for i in columns:
            column_widths[i] += excess_width / len(columns)
        return

    # Third group.
    columns = [
        i for i, _ in enumerate(grid[column_slice], start=column_slice.start)
        if constrainedness[i] and
        column_intrinsic_percentages[i] == 0 and
        column_max_content_widths[i] > 0]
    if columns:
        sum_max_content_widths = sum(column_max_content_widths[i] for i in columns)
        ratio = excess_width / sum_max_content_widths
        for i in columns:
            column_widths[i] += column_max_content_widths[i] * ratio
        return

    # Fourth group.
    columns = [
        i for i, _ in enumerate(grid[column_slice], start=column_slice.start)
        if column_intrinsic_percentages[i] > 0 and column_max_content_widths[i] > 0]
    if columns:
        sum_intrinsic_percentages = sum(
            column_intrinsic_percentages[i] for i in columns)
        ratio = excess_width / sum_intrinsic_percentages
        for i in columns:
            column_widths[i] += column_intrinsic_percentages[i] * ratio
        return

    # Fifth group.
    columns = [
        i for i, column in enumerate(grid[column_slice], start=column_slice.start)
        if column]
    if columns:
        for i in columns:
            column_widths[i] += excess_width / len(columns)
        return

    # Sixth group.
    columns = [i for i, _ in enumerate(grid[column_slice], start=column_slice.start)]
    for i in columns:
        column_widths[i] += excess_width / len(columns)


TRANSPARENT = tinycss2.color4.parse_color('transparent')


def collapse_table_borders(table, grid_width, grid_height):
    """Resolve border conflicts for a table in the collapsing border model.

    Take a :class:`TableBox`; set appropriate border widths on the table,
    column group, column, row group, row, and cell boxes; and return
    a data structure for the resolved collapsed border grid.

    """
    if not (grid_width and grid_height):
        # Don’t bother with empty tables.
        return [], []

    styles = reversed([
        'hidden', 'double', 'solid', 'dashed', 'dotted', 'ridge', 'outset',
        'groove', 'inset', 'none'])
    style_scores = {style: score for score, style in enumerate(styles)}
    style_map = {'inset': 'ridge', 'outset': 'groove'}
    weak_null_border = ((0, 0, style_scores['none']), ('none', 0, TRANSPARENT))

    # Borders are always stored left to right, top to bottom.
    vertical_borders = [
        [weak_null_border] * (grid_width + 1) for _ in range(grid_height)]
    horizontal_borders = [
        [weak_null_border] * grid_width for _ in range(grid_height + 1)]

    def set_one_border(border_grid, box_style, side, grid_x, grid_y):
        from ..draw.color import get_color

        style = box_style[f'border_{side}_style']
        width = box_style[f'border_{side}_width']
        color = get_color(box_style, f'border_{side}_color')

        # See https://www.w3.org/TR/CSS21/tables.html#border-conflict-resolution.
        score = ((1 if style == 'hidden' else 0), width, style_scores[style])

        style = style_map.get(style, style)
        previous_score, _ = border_grid[grid_y][grid_x]
        # Strict < so that the earlier call wins in case of a tie.
        if previous_score < score:
            border_grid[grid_y][grid_x] = (score, (style, width, color))

    def set_borders(box, x, y, w, h):
        style = box.style

        # x and y are logical (possibly rtl), but borders are graphical (always ltr).
        if table.style['direction'] == 'ltr':
            for yy in range(y, y + h):
                set_one_border(vertical_borders, style, 'left', x, yy)
                set_one_border(vertical_borders, style, 'right', x + w, yy)
            for xx in range(x, x + w):
                set_one_border(horizontal_borders, style, 'top', xx, y)
                set_one_border(horizontal_borders, style, 'bottom', xx, y + h)
        else:
            for yy in range(y, y + h):
                set_one_border(vertical_borders, style, 'left', -1 - w - x, yy)
                set_one_border(vertical_borders, style, 'right', -1 - x, yy)
            for xx in range(-1 - x, -1 - x - w, -1):
                set_one_border(horizontal_borders, style, 'top', xx, y)
                set_one_border(horizontal_borders, style, 'bottom', xx, y + h)

    # Set cell borders. The order is important here:
    # "A style set on a cell wins over one on a row, which wins over a
    #  row group, column, column group and, lastly, table"
    # See https://www.w3.org/TR/CSS21/tables.html#border-conflict-resolution.
    strong_null_border = ((1, 0, style_scores['hidden']), ('hidden', 0, TRANSPARENT))
    grid_y = 0
    for row_group in table.children:
        for row in row_group.children:
            for cell in row.children:
                # Force null border inside of a cell with rowspan or colspan.
                grid_x, colspan, rowspan = cell.grid_x, cell.colspan, cell.rowspan
                if table.style['direction'] == 'ltr':
                    vertical_x_range = range(grid_x + 1, grid_x + colspan)
                    horizontal_x_range = range(grid_x, grid_x + colspan)
                else:
                    vertical_x_range = range(-2 - grid_x, -1 - grid_x - colspan, -1)
                    horizontal_x_range = range(-1 - grid_x, -1 - grid_x - colspan, -1)
                for xx in vertical_x_range:
                    for yy in range(grid_y, grid_y + rowspan):
                        vertical_borders[yy][xx] = strong_null_border
                for xx in horizontal_x_range:
                    for yy in range(grid_y + 1, grid_y + rowspan):
                        horizontal_borders[yy][xx] = strong_null_border
                # Set cell border.
                set_borders(cell, grid_x, grid_y, colspan, rowspan)
            grid_y += 1

    # Set row borders.
    grid_y = 0
    for row_group in table.children:
        for row in row_group.children:
            set_borders(row, 0, grid_y, grid_width, 1)
            grid_y += 1

    # Set row group borders.
    grid_y = 0
    for row_group in table.children:
        rowspan = len(row_group.children)
        set_borders(row_group, 0, grid_y, grid_width, rowspan)
        grid_y += rowspan

    # Set column borders.
    for column_group in table.column_groups:
        for column in column_group.children:
            set_borders(column, column.grid_x, 0, 1, grid_height)

    # Set column group group borders.
    for column_group in table.column_groups:
        set_borders(
            column_group, column_group.grid_x, 0, column_group.span, grid_height)

    # Set table borders.
    set_borders(table, 0, 0, grid_width, grid_height)

    # Now that all conflicts are resolved, set transparent borders of the
    # correct widths on each box. The actual border grid will be painted
    # separately.
    def set_border_used_width(box, side, twice_width):
        prop = f'border_{side}_width'
        setattr(box, prop, twice_width / 2)

    def remove_borders(box):
        set_border_used_width(box, 'top', 0)
        set_border_used_width(box, 'right', 0)
        set_border_used_width(box, 'bottom', 0)
        set_border_used_width(box, 'left', 0)

    def max_vertical_width(x, y1, y2):
        return max(grid_row[x][1][1] for grid_row in vertical_borders[y1:y2])

    def max_horizontal_width(x1, y, x2):
        return max(width for _, (_, width, _) in horizontal_borders[y][x1:x2])

    grid_y = 0
    for row_group in table.children:
        remove_borders(row_group)
        for row in row_group.children:
            remove_borders(row)
            for cell in row.children:
                x, y = cell.grid_x, grid_y
                colspan, rowspan = cell.colspan, cell.rowspan
                if table.style['direction'] == 'ltr':
                    top = max_horizontal_width(x, y, x + colspan)
                    bottom = max_horizontal_width(x, y + rowspan, x + colspan)
                    left = max_vertical_width(x, y, y + rowspan)
                    right = max_vertical_width(x + colspan, y, y + rowspan)
                else:
                    top = max_horizontal_width(-colspan - x, y, -x or None)
                    bottom = max_horizontal_width(-colspan - x, y + rowspan, -x or None)
                    left = max_vertical_width(-1 - colspan - x, y, y + rowspan)
                    right = max_vertical_width(-1 - x, y, y + rowspan)
                set_border_used_width(cell, 'top', top)
                set_border_used_width(cell, 'bottom', bottom)
                set_border_used_width(cell, 'left', left)
                set_border_used_width(cell, 'right', right)
            grid_y += 1

    for column_group in table.column_groups:
        remove_borders(column_group)
        for column in column_group.children:
            remove_borders(column)

    set_border_used_width(table, 'top', max_horizontal_width(0, 0, grid_width))
    set_border_used_width(
        table, 'bottom', max_horizontal_width(0, grid_height, grid_width))
    # "UAs must compute an initial left and right border width for the table
    #  by examining the first and last cells in the first row of the table."
    # https://www.w3.org/TR/CSS21/tables.html#collapsing-borders
    # ... so h=1, not grid_height:
    set_border_used_width(table, 'left', max_vertical_width(0, 0, 1))
    set_border_used_width(table, 'right', max_vertical_width(grid_width, 0, 1))

    return vertical_borders, horizontal_borders
