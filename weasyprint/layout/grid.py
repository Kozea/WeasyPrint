"""Layout for grid containers and grid-items."""

from itertools import count, cycle


def _intersect(position_1, size_1, position_2, size_2):
    return (
        position_1 < position_2 + size_2 and
        position_2 < position_1 + size_1)


def _intersect_with_children(x, y, width, height, positions):
    for full_x, full_y, full_width, full_height in positions:
        x_intersect = _intersect(x, width, full_x, full_width)
        y_intersect = _intersect(y, height, full_y, full_height)
        if x_intersect and y_intersect:
            return True
    return False


def _get_placement(start, end, lines):
    # Input coordinates are 1-indexed, returned coordinates are 0-indexed.
    if (start == end == 'auto' or
        start == 'auto' and end[0] == 'span' or
        end == 'auto' and start[0] == 'span' or
        start[0] == 'span' and end[0] == 'span'):
        return
    if start != 'auto':
        span, number, ident = start
        if ident and span is None and number is None:
            for coordinate, line in enumerate(lines):
                if f'{ident}-start' in line:
                    break
            else:
                number = 1
        if number is not None and span is None:
            if ident is None:
                coordinate = number - 1
            else:
                step = 1 if number > 0 else -1
                for coordinate, line in enumerate(lines[::step]):
                    if ident in line:
                        number -= step
                    if number == 0:
                        break
                else:
                    coordinate += abs(number)
                if step == -1:
                    coordinate = len(lines) - 1 - coordinate
        if span is not None:
            size = number or 1
            coordinate = None
            span_ident = ident
    else:
        size = 1
        span_ident = None
        coordinate = None
    if end != 'auto':
        span, number, ident = end
        if ident and span is None and number is None:
            for coordinate_end, line in enumerate(lines):
                if f'{ident}-end' in line:
                    break
            else:
                number = 1
        if number is not None and span is None:
            if ident is None:
                coordinate_end = number - 1
            else:
                step = 1 if number > 0 else -1
                for coordinate_end, line in enumerate(lines[::step]):
                    if ident in line:
                        number -= step
                    if number == 0:
                        break
                else:
                    coordinate_end += abs(number)
                if step == -1:
                    coordinate_end = len(lines) - 1 - coordinate_end
        if span is not None:
            size = span_number = number or 1
            span_ident = ident
            if span_ident is not None:
                for size, line in enumerate(lines[coordinate+1:], start=1):
                    if span_ident in line:
                        span_number -= 1
                    if span_number == 0:
                        break
                else:
                    size += span_number
        elif coordinate is not None:
            size = coordinate_end - coordinate
        if coordinate is None:
            if span_ident is None:
                coordinate = coordinate_end - size
            else:
                number = number or 1
                if coordinate_end > 0:
                    for coordinate, line in enumerate(lines[coordinate_end-1::-1]):
                        if span_ident in line:
                            number -= 1
                        if number == 0:
                            coordinate = coordinate_end - 1 - coordinate
                            break
                    else:
                        coordinate = -number
                else:
                    coordinate = -number
            size = coordinate_end - coordinate
    else:
        size = 1
    if size < 0:
        size = -size
        coordinate -= size
    if size == 0:
        size = 1
    return (coordinate, size)


def _get_span(place):
    # TODO: handle lines
    span = 1
    if place[0] == 'span':
        span = place[1] or 1
    return span


def _get_column_placement(row_placement, column_start, column_end,
                          columns, children_positions, dense):
    occupied_columns = set()
    for x, y, width, height in children_positions.values():
        # Test whether cells overlap.
        if _intersect(y, height, *row_placement):
            for x in range(x, x + width):
                occupied_columns.add(x)
    if dense:
        for x in count():
            if x in occupied_columns:
                continue
            if column_start == 'auto':
                placement = _get_placement(x + 1, column_end, columns)
            else:
                assert column_start[0] == 'span'
                # If the placement contains two spans, remove the one contributed
                # by the end grid-placement property.
                # https://drafts.csswg.org/css-grid/#grid-placement-errors
                assert column_start == 'auto' or column_start[1] == 'span'
                span = _get_span(column_start)
                placement = _get_placement(column_start, x + 1 + span, columns)
            columns = range(placement[0], placement[0] + placement[1])
            if not set(columns) & occupied_columns:
                return placement
    else:
        y = max(occupied_columns) + 1
        if column_start == 'auto':
            return _get_placement(y + 1, column_end, columns)
        else:
            assert column_start[0] == 'span'
            # If the placement contains two spans, remove the one contributed
            # by the end grid-placement property.
            # https://drafts.csswg.org/css-grid/#grid-placement-errors
            assert column_start == 'auto' or column_start[1] == 'span'
            for end_y in count(y + 1):
                placement = _get_placement(column_start, end_y + 1, columns)
                if placement[0] >= y:
                    return placement


def grid_layout(context, box, bottom_space, skip_stack, containing_block,
                page_is_empty, absolute_boxes, fixed_boxes):
    # Define explicit grid
    grid_areas = box.style['grid_template_areas']
    rows = box.style['grid_template_rows']
    columns = box.style['grid_template_columns']
    flow = box.style['grid_auto_flow']
    auto_rows = cycle(box.style['grid_auto_rows'])
    auto_columns = cycle(box.style['grid_auto_columns'])
    auto_rows_back = cycle(box.style['grid_auto_rows'][::-1])
    auto_columns_back = cycle(box.style['grid_auto_columns'][::-1])

    if grid_areas == 'none':
        grid_areas = ((None,),)
    grid_areas = [list(row) for row in grid_areas]

    if rows == 'none':
        rows = ((),)
    rows = [row if i % 2 else list(row) for i, row in enumerate(rows)]

    if columns == 'none':
        columns = ((),)
    columns = [column if i % 2 else list(column) for i, column in enumerate(columns)]

    # Adjust rows number
    grid_areas_columns = len(grid_areas[0]) if grid_areas else 0
    rows_diff = int((len(rows) - 1) / 2) - len(grid_areas)
    if rows_diff > 0:
        for _ in range(rows_diff):
            grid_areas.append([None] * grid_areas_columns)
    elif rows_diff < 0:
        for _ in range(-rows_diff):
            rows.append(next(auto_rows))
            rows.append([])

    # Adjust columns number
    columns_diff = int((len(columns) - 1) / 2) - grid_areas_columns
    if columns_diff > 0:
        for row in grid_areas:
            for _ in range(columns_diff):
                row.append(None)
    elif columns_diff < 0:
        for _ in range(-columns_diff):
            columns.append(next(auto_columns))
            columns.append([])

    # Add implicit line names
    for y, row in enumerate(grid_areas):
        for x, area_name in enumerate(row):
            if area_name is None:
                continue
            start_name = f'{area_name}-start'
            if start_name not in [name for row in rows[::2] for name in row]:
                rows[2*y].append(start_name)
            if start_name not in [name for column in columns[::2] for name in column]:
                columns[2*x].append(start_name)
    for y, row in enumerate(grid_areas[::-1]):
        for x, area_name in enumerate(row[::-1]):
            if area_name is None:
                continue
            end_name = f'{area_name}-end'
            if end_name not in [name for row in rows[::2] for name in row]:
                rows[-2*y-1].append(end_name)
            if end_name not in [name for column in columns[::2] for name in column]:
                columns[-2*x-1].append(end_name)

    # 1. Run the grid placement algorithm.

    # 1.1 Position anything that’s not auto-positioned.
    children_positions = {}
    for child in box.children:
        column_start = child.style['grid_column_start']
        column_end = child.style['grid_column_end']
        row_start = child.style['grid_row_start']
        row_end = child.style['grid_row_end']

        column_placement = _get_placement(column_start, column_end, columns[::2])
        row_placement = _get_placement(row_start, row_end, rows[::2])

        if column_placement and row_placement:
            x, width = column_placement
            y, height = row_placement
            children_positions[child] = (x, y, width, height)

    # 1.2 Process the items locked to a given row.
    children = sorted(box.children, key=lambda item: item.style['order'])
    for child in children:
        if child in children_positions:
            continue
        row_start = child.style['grid_row_start']
        row_end = child.style['grid_row_end']
        row_placement = _get_placement(row_start, row_end, rows[::2])
        if not row_placement:
            continue
        y, height = row_placement
        column_start = child.style['grid_column_start']
        column_end = child.style['grid_column_end']
        x, width = _get_column_placement(
            row_placement, column_start, column_end, columns,
            children_positions, 'dense' in flow)
        children_positions[child] = (x, y, width, height)

    # 1.3 Determine the columns in the implicit grid.
    # 1.3.1 Start with the columns from the explicit grid.
    implicit_x1 = 0
    implicit_x2 = len(grid_areas[0]) if grid_areas else 0
    # 1.3.2 Add columns to the beginning and end of the implicit grid.
    remaining_grid_items = []
    for child in children:
        if child in children_positions:
            x, _, width, _ = children_positions[child]
        else:
            column_start = child.style['grid_column_start']
            column_end = child.style['grid_column_end']
            column_placement = _get_placement(
                column_start, column_end, columns[::2])
            if column_placement:
                x, width = column_placement
            else:
                remaining_grid_items.append(child)
                continue
        implicit_x1 = min(x, implicit_x1)
        implicit_x2 = max(x + width, implicit_x2)
    # 1.3.3 Add columns to accommodate max column span.
    for child in remaining_grid_items:
        column_start = child.style['grid_column_start']
        column_end = child.style['grid_column_end']
        if column_start == column_end == 'auto':
            span = 1
        elif column_start != 'auto':
            is_span, span, _ = column_start
            assert is_span
        else:
            is_span, span, _ = column_end
            assert is_span
        implicit_x2 = max(implicit_x1 + (span or 1), implicit_x2)

    # 1.4 Position the remaining grid items.
    implicit_y1 = 0
    implicit_y2 = len(grid_areas)
    for position in children_positions.values():
        _, y, _, height = position
        implicit_y1 = min(y, implicit_y1)
        implicit_y2 = max(y + height, implicit_y2)
    for _ in range(0 - implicit_x1):
        columns.insert(0, next(auto_columns_back))
        columns.insert(0, [])
    for _ in range(len(grid_areas[0]) if grid_areas else 0, implicit_x2):
        columns.append(next(auto_columns))
        columns.append([])
    for _ in range(0 - implicit_y1):
        rows.insert(0, next(auto_rows_back))
        rows.insert(0, [])
    for _ in range(len(grid_areas), implicit_y2):
        rows.append(next(auto_rows))
        rows.append([])
    cursor_x, cursor_y = implicit_x1, implicit_y1
    if 'dense' in flow:
        for child in remaining_grid_items:
            column_start = child.style['grid_column_start']
            column_end = child.style['grid_column_end']
            column_placement = _get_placement(
                column_start, column_end, columns[::2])
            if column_placement:
                # 1. Set the row position of the cursor.
                cursor_y = implicit_y1
                x, width = column_placement
                cursor_x = x
                # 2. Increment the cursor’s row position.
                row_start = child.style['grid_row_start']
                row_end = child.style['grid_row_end']
                for y in count(cursor_y):
                    if row_start == 'auto':
                        y, height = _get_placement((None, y + 1, None), row_end, rows[::2])
                    else:
                        assert row_start[0] == 'span'
                        assert row_start == 'auto' or row_start[1] == 'span'
                        span = _get_span(row_start)
                        y, height = _get_placement(row_start, (None, y + 1 + span, None), rows[::2])
                    if y < cursor_y:
                        continue
                    for row in range(y, y + height):
                        if _intersect_with_children(x, y, width, height, children_positions.values()):
                            # Child intersects with a positioned child on current row.
                            break
                    else:
                        # Child doesn’t intersect with any positioned child on any row.
                        break
                y_diff = y + height - implicit_y2
                if y_diff > 0:
                    for _ in range(y_diff):
                        rows.append(next(auto_rows))
                        rows.append([])
                    implicit_y2 = y + height
                # 3. Set the item’s row-start line.
                children_positions[child] = (x, y, width, height)
            else:
                # 1. Set the cursor’s row and column positions.
                cursor_x, cursor_y = implicit_x1, implicit_y1
                while True:
                    # 2. Increment the column position of the cursor.
                    y = cursor_y
                    row_start = child.style['grid_row_start']
                    row_end = child.style['grid_row_end']
                    column_start = child.style['grid_column_start']
                    column_end = child.style['grid_column_end']
                    for x in range(cursor_x, implicit_x2):
                        if row_start == 'auto':
                            y, height = _get_placement((None, y + 1, None), row_end, rows[::2])
                        else:
                            span = _get_span(row_start)
                            y, height = _get_placement(row_start, (None, y + 1 + span, None), rows[::2])
                        if column_start == 'auto':
                            x, width = _get_placement((None, x + 1, None), column_end, columns[::2])
                        else:
                            span = _get_span(column_start)
                            x, width = _get_placement(column_start, (None, x + 1 + span, None), columns[::2])
                        if _intersect_with_children(x, y, width, height, children_positions.values()):
                            # Child intersects with a positioned child.
                            continue
                        else:
                            # Free place found.
                            # 3. Set the item’s row-start and column-start lines.
                            children_positions[child] = (x, y, width, height)
                            break
                    else:
                        # No room found.
                        # 2. Return to the previous step.
                        cursor_y += 1
                        y_diff = cursor_y - implicit_y2
                        if y_diff > 0:
                            for _ in range(y_diff):
                                rows.append(next(auto_rows))
                                rows.append([])
                            implicit_y2 = cursor_y
                        cursor_x = implicit_x1
                        continue
                    break
    else:
        for child in remaining_grid_items:
            column_start = child.style['grid_column_start']
            column_end = child.style['grid_column_end']
            column_placement = _get_placement(
                column_start, column_end, columns[::2])
            if column_placement:
                # 1. Set the column position of the cursor.
                x, width = column_placement
                if x < cursor_x:
                    cursor_y += 1
                cursor_x = x
                # 2. Increment the cursor’s row position.
                row_start = child.style['grid_row_start']
                row_end = child.style['grid_row_end']
                for y in count(cursor_y):
                    if row_start == 'auto':
                        y, height = _get_placement((None, y + 1, None), row_end, rows[::2])
                    else:
                        assert row_start[0] == 'span'
                        assert row_start == 'auto' or row_start[1] == 'span'
                        span = _get_span(row_start)
                        y, height = _get_placement(row_start, (None, y + 1 + span, None), rows[::2])
                    if y < cursor_y:
                        continue
                    for row in range(y, y + height):
                        if _intersect_with_children(x, y, width, height, children_positions.values()):
                            # Child intersects with a positioned child on current row.
                            break
                    else:
                        # Child doesn’t intersect with any positioned child on any row.
                        break
                implicit_y2 = max(y + height, implicit_y2)
                y_diff = y + height - implicit_y2
                if y_diff > 0:
                    for _ in range(y_diff):
                        rows.append(next(auto_rows))
                        rows.append([])
                    implicit_y2 = y + height
                # 3. Set the item’s row-start line.
                children_positions[child] = (x, y, width, height)
            else:
                while True:
                    # 1. Increment the column position of the cursor.
                    y = cursor_y
                    row_start = child.style['grid_row_start']
                    row_end = child.style['grid_row_end']
                    column_start = child.style['grid_column_start']
                    column_end = child.style['grid_column_end']
                    for x in range(cursor_x, implicit_x2):
                        if row_start == 'auto':
                            y, height = _get_placement((None, y + 1, None), row_end, rows[::2])
                        else:
                            span = _get_span(row_start)
                            y, height = _get_placement(row_start, (None, y + 1 + span, None), rows[::2])
                        if column_start == 'auto':
                            x, width = _get_placement((None, x + 1, None), column_end, columns[::2])
                        else:
                            span = _get_span(column_start)
                            x, width = _get_placement(column_start, (None, x + 1 + span, None), columns[::2])
                        if _intersect_with_children(x, y, width, height, children_positions.values()):
                            # Child intersects with a positioned child.
                            continue
                        else:
                            # Free place found.
                            # 2. Set the item’s row-start and column-start lines.
                            children_positions[child] = (x, y, width, height)
                            break
                    else:
                        # No room found.
                        # 2. Return to the previous step.
                        cursor_y += 1
                        y_diff = cursor_y - implicit_y2
                        if y_diff > 0:
                            for _ in range(y_diff):
                                rows.append(next(auto_rows))
                                rows.append([])
                            implicit_y2 = cursor_y
                        cursor_x = implicit_x1
                        continue
                    break
