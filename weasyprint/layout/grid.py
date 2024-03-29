"""Layout for grid containers and grid-items."""

from itertools import cycle


def placement(start, end, lines):
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
        if number and span is None:
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
        if number and span is None:
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
            size = number or 1
            span_ident = ident
        else:
            size = coordinate_end - coordinate
        if coordinate is None:
            if coordinate_span is None:
                coordinate = coordinate_end - size
            else:
                number = coordinate_end
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
    return (coordinate, size)


def grid_layout(context, box, bottom_space, skip_stack, containing_block,
                page_is_empty, absolute_boxes, fixed_boxes):
    # Define explicit grid
    grid_areas = box.style['grid_template_areas']
    rows = box.style['grid_template_rows']
    columns = box.style['grid_template_columns']

    if grid_areas == 'none':
        grid_areas = ()
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
        rows_sizes = cycle(box.style['grid_auto_rows'])
        for _ in range(-rows_diff):
            rows.append(next(rows_sizes))
            rows.append([])

    # Adjust columns number
    columns_diff = int((len(columns) - 1) / 2) - grid_areas_columns
    if columns_diff > 0:
        for row in grid_areas:
            for _ in range(columns_diff):
                row.append(None)
    elif columns_diff < 0:
        columns_sizes = cycle(box.style['grid_auto_columns'])
        for _ in range(-columns_diff):
            columns.append(next(columns_sizes))
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

    # 1. Grid placement algorithm
    # 1. Position anything that’s not auto-positioned
    children_position = {}
    for child in box.children:
        column_start = child.style['grid_column_start']
        column_end = child.style['grid_column_end']
        row_start = child.style['grid_row_start']
        row_end = child.style['grid_row_end']
        column = (column_start, column_end)
        row = (row_start, row_end)

        column_placement = placement(column_start, column_end, columns[::2])
        row_placement = placement(row_start, row_end, rows[::2])

        if column_placement and row_placement:
            x, width = column_placement
            y, height = row_placement
            children_position[child] = (x, y, width, height)
