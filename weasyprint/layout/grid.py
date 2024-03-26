"""Layout for grid containers and grid-items."""

from itertools import cycle


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
    rows = list(rows)

    if columns == 'none':
        columns = ((),)
    columns = list(columns)

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
            rows.append(())

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
            columns.append(())

    # 1. Position anything that’s not auto-positioned.
    pass
