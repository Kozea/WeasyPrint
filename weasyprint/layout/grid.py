"""Layout for grid containers and grid-items."""

from itertools import count, cycle
from math import inf

from ..css.properties import Dimension
from ..formatting_structure import boxes
from .percent import percentage
from .preferred import max_content_width, min_content_width


def _is_length(sizing):
    return isinstance(sizing, Dimension) and sizing.unit != 'fr'


def _is_fr(sizing):
    return isinstance(sizing, Dimension) and sizing.unit == 'fr'


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


def _get_line(line, lines, side):
    span, number, ident = line
    if ident and span is None and number is None:
        for coord, line in enumerate(lines):
            if f'{ident}-{side}' in line:
                break
        else:
            number = 1
    if number is not None and span is None:
        if ident is None:
            coord = number - 1
        else:
            step = 1 if number > 0 else -1
            for coord, line in enumerate(lines[::step]):
                if ident in line:
                    number -= step
                if number == 0:
                    break
            else:
                coord += abs(number)
            if step == -1:
                coord = len(lines) - 1 - coord
    if span is not None:
        coord = None
    return span, number, ident, coord


def _get_placement(start, end, lines):
    # Input coordinates are 1-indexed, returned coordinates are 0-indexed.
    if start == 'auto' or start[0] == 'span':
        if end == 'auto' or end[0] == 'span':
            return
    if start != 'auto':
        span, number, ident, coord = _get_line(start, lines, 'start')
        if span is not None:
            size = number or 1
            span_ident = ident
    else:
        size = 1
        span_ident = coord = None
    if end != 'auto':
        span, number, ident, coord_end = _get_line(end, lines, 'end')
        if span is not None:
            size = span_number = number or 1
            span_ident = ident
            if span_ident is not None:
                for size, line in enumerate(lines[coord+1:], start=1):
                    if span_ident in line:
                        span_number -= 1
                    if span_number == 0:
                        break
                else:
                    size += span_number
        elif coord is not None:
            size = coord_end - coord
        if coord is None:
            if span_ident is None:
                coord = coord_end - size
            else:
                number = number or 1
                if coord_end > 0:
                    iterable = enumerate(lines[coord_end-1::-1])
                    for coord, line in iterable:
                        if span_ident in line:
                            number -= 1
                        if number == 0:
                            coord = coord_end - 1 - coord
                            break
                    else:
                        coord = -number
                else:
                    coord = -number
            size = coord_end - coord
    else:
        size = 1
    if size < 0:
        size = -size
        coord -= size
    if size == 0:
        size = 1
    return (coord, size)


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
                # If the placement contains two spans, remove the one
                # contributed by the end grid-placement property.
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


def _get_sizing_functions(size):
    min_sizing = max_sizing = size
    if size[0] == 'minmax()':
        min_sizing, max_sizing = size[1:]
    if min_sizing[0] == 'fit-content()':
        min_sizing = 'auto'
    elif _is_fr(min_sizing):
        min_sizing = 'auto'
    return (min_sizing, max_sizing)


def _distribute_extra_space(affected_sizes, affected_tracks_types,
                            size_contribution, tracks_children,
                            sizing_functions, tracks_sizes, span, direction,
                            context, containing_block):
    assert affected_sizes in ('min', 'max')
    assert affected_tracks_types in (
        'intrinsic', 'content-based', 'max-content')
    assert size_contribution in ('mininum', 'min-content', 'max-content')
    assert direction in 'xy'

    # 1. Maintain separately for each affected track a planned increase.
    planned_increases = [0] * len(tracks_sizes)

    # 2. Distribute space.
    affected_tracks = []
    affected_size_index = 0 if affected_sizes == 'min' else 1
    for functions in sizing_functions:
        function = functions[affected_size_index]
        if affected_tracks_types == 'intrinsic':
            if (function in ('min-content', 'max-content', 'auto') or
                    function[0] == 'fit-content()'):
                affected_tracks.append(True)
                continue
        elif affected_tracks_types == 'content-based':
            if function in ('min-content', 'max-content'):
                affected_tracks.append(True)
                continue
        elif affected_tracks_types == 'max-content':
            if function in ('max-content', 'auto'):
                affected_tracks.append(True)
                continue
        affected_tracks.append(False)
    for i, children in enumerate(tracks_children):
        if not children:
            continue
        for item in children:
            # 2.1 Find the space distribution.
            # TODO: Differenciate minimum and min-content values.
            # TODO: Find a better way to get height.
            if direction == 'x':
                if size_contribution in ('minimum', 'min-content'):
                    space = min_content_width(context, item)
                else:
                    space = max_content_width(context, item)
            else:
                from .block import block_level_layout
                item = item.deepcopy()
                item.position_x = 0
                item.position_y = 0
                item, _, _, _, _, _ = block_level_layout(
                    context, item, bottom_space=-inf, skip_stack=None,
                    containing_block=containing_block, page_is_empty=True,
                    absolute_boxes=[], fixed_boxes=[])
                space = item.margin_height()
            for sizes in tracks_sizes[i:i+span]:
                space -= sizes[affected_size_index]
            space = max(0, space)
            # 2.2 Distribute space up to limits.
            tracks_numbers = list(
                enumerate(affected_tracks[i:i+span], start=i))
            item_incurred_increases = [0] * len(sizing_functions)
            affected_tracks_numbers = [
                j for j, affected in tracks_numbers if affected]
            distributed_space = space / (len(affected_tracks_numbers) or 1)
            for track_number in affected_tracks_numbers:
                base_size, growth_limit = tracks_sizes[track_number]
                item_incurred_increase = distributed_space
                affected_size = tracks_sizes[track_number][affected_size_index]
                limit = tracks_sizes[track_number][1]
                if affected_size + item_incurred_increase >= limit:
                    extra = (
                        item_incurred_increase + affected_size_index - limit)
                    item_incurred_increase -= extra
                space -= item_incurred_increase
                item_incurred_increases[track_number] = item_incurred_increase
            # 2.3 Distribute space to non-affected tracks.
            if space and affected_tracks_numbers:
                unaffected_tracks_numbers = [
                    j for j, affected in tracks_numbers if not affected]
                distributed_space = (
                    space / (len(unaffected_tracks_numbers) or 1))
                for track_number in unaffected_tracks_numbers:
                    base_size, growth_limit = tracks_sizes[track_number]
                    item_incurred_increase = distributed_space
                    affected_size = (
                        tracks_sizes[track_number][affected_size_index])
                    limit = tracks_sizes[track_number][1]
                    if affected_size + item_incurred_increase >= limit:
                        extra = (
                            item_incurred_increase +
                            affected_size_index - limit)
                        item_incurred_increase -= extra
                    space -= item_incurred_increase
                    item_incurred_increases[track_number] = (
                        item_incurred_increase)
            # 2.4 Distribute space beyond limits.
            if space:
                # TODO
                pass
            # 2.5. Set the track’s planned increase.
            for k, extra in enumerate(item_incurred_increases):
                if extra > planned_increases[k]:
                    planned_increases[k] = extra
    # 3. Update the tracks’ affected size.
    for i, increase in enumerate(planned_increases):
        if affected_sizes == 'max' and tracks_sizes[i][1] is inf:
            tracks_sizes[i][1] = tracks_sizes[i][0] + increase
        else:
            tracks_sizes[i][affected_size_index] += increase


def _resolve_tracks_sizes(sizing_functions, box_size, children_positions,
                          implicit_start, direction, context,
                          containing_block):
    assert direction in 'xy'
    tracks_sizes = []
    # 1.1 initialize track sizes.
    for min_function, max_function in sizing_functions:
        base_size = None
        if _is_length(max_function):
            base_size = percentage(min_function, box_size)
        elif (min_function in ('min-content', 'max-content', 'auto') or
              min_function[0] == 'fit-content()'):
            base_size = 0
        growth_limit = None
        if _is_length(max_function):
            growth_limit = percentage(min_function, box_size)
        elif (max_function in ('max-content', 'max-content', 'auto') or
              max_function[0] == 'fit-content()' or _is_fr(max_function)):
            growth_limit = inf
        if None not in (base_size, growth_limit):
            growth_limit = max(base_size, growth_limit)
        tracks_sizes.append([base_size, growth_limit])

    # 1.2 Resolve intrinsic track sizes.
    # 1.2.1 Shim baseline-aligned items.
    # TODO: Shim items.
    # 1.2.2 Size tracks to fit non-spanning items.
    tracks_children = [[] for _ in range(len(tracks_sizes))]
    for child, (x, y, width, height) in children_positions.items():
        coord, size = (x, width) if direction == 'x' else (y, height)
        if size != 1:
            continue
        tracks_children[coord + implicit_start].append(child)
    iterable = zip(tracks_children, sizing_functions, tracks_sizes)
    for children, (min_function, max_function), sizes in iterable:
        if not children:
            continue
        if direction == 'y':
            # TODO: Find a better way to get height.
            from .block import block_level_layout
            height = 0
            for child in children:
                child = child.deepcopy()
                child.position_x = 0
                child.position_y = 0
                child, _, _, _, _, _ = block_level_layout(
                    context, child, bottom_space=-inf, skip_stack=None,
                    containing_block=containing_block, page_is_empty=True,
                    absolute_boxes=[], fixed_boxes=[])
                height = max(height, child.margin_height())
            if min_function in ('min-content', 'max_content', 'auto'):
                sizes[0] = height
            if max_function in ('min-content', 'max_content'):
                sizes[1] = height
            if None not in sizes:
                sizes[1] = max(sizes)
            continue
        if min_function == 'min-content':
            sizes[0] = max(0, *(
                min_content_width(context, child) for child in children))
        elif min_function == 'max-content':
            sizes[0] = max(0, *(
                max_content_width(context, child) for child in children))
        elif min_function == 'auto':
            # TODO: Handle min-/max-content constrained parents.
            # TODO: Use real "minimum contributions".
            sizes[0] = max(0, *(
                min_content_width(context, child) for child in children))
        if max_function == 'min-content':
            sizes[1] = max(
                min_content_width(context, child) for child in children)
        elif (max_function in ('auto', 'max-content') or
              max_function[0] == 'fit_content()'):
            sizes[1] = max(
                max_content_width(context, child) for child in children)
        if None not in sizes:
            sizes[1] = max(sizes)
    # 1.2.3 Increase sizes to accommodate items spanning content-sized tracks.
    spans = sorted({
        width if direction == 'x' else height
        for (_, _, width, height) in children_positions.values()
        if (width if direction == 'x' else height) >= 2})
    for span in spans:
        tracks_children = [[] for _ in range(len(sizing_functions))]
        iterable = enumerate(children_positions.items())
        for i, (child, (x, y, width, height)) in iterable:
            coord, size = (x, width) if direction == 'x' else (y, height)
            if size != span:
                continue
            for _, max_function in sizing_functions[i:i+span+1]:
                if _is_fr(max_function):
                    break
            else:
                tracks_children[coord + implicit_start].append(child)
        # 1.2.3.1 For intrinsic minimums.
        # TODO: Respect min-/max-content constraint.
        _distribute_extra_space(
            'min', 'intrinsic', 'mininum', tracks_children,
            sizing_functions, tracks_sizes, span, direction, context,
            containing_block)
        # 1.2.3.2 For content-based minimums.
        _distribute_extra_space(
            'min', 'content-based', 'min-content', tracks_children,
            sizing_functions, tracks_sizes, span, direction, context,
            containing_block)
        # 1.2.3.3 For max-content minimums.
        # TODO: Respect max-content constraint.
        _distribute_extra_space(
            'min', 'max-content', 'max-content', tracks_children,
            sizing_functions, tracks_sizes, span, direction, context,
            containing_block)
        # 1.2.3.4 Increase growth limit.
        for sizes in tracks_sizes:
            if None not in sizes:
                sizes[1] = max(sizes)
        iterable = enumerate(children_positions.items())
        for i, (child, (x, y, width, height)) in iterable:
            coord, size = (x, width) if direction == 'x' else (y, height)
            if size != span:
                continue
            for _, max_function in sizing_functions[i:i+span+1]:
                if _is_fr(max_function):
                    break
            else:
                tracks_children[coord + implicit_start].append(child)
        # 1.2.3.5 For intrinsic maximums.
        _distribute_extra_space(
            'max', 'intrinsic', 'min-content', tracks_children,
            sizing_functions, tracks_sizes, span, direction, context,
            containing_block)
        # 1.2.3.6 For max-content maximums.
        _distribute_extra_space(
            'max', 'max-content', 'max-content', tracks_children,
            sizing_functions, tracks_sizes, span, direction, context,
            containing_block)
    # 1.2.4 Increase sizes to accommodate items spanning flexible tracks.
    # TODO
    # 1.2.5 Fix infinite growth limits.
    for sizes in tracks_sizes:
        if sizes[1] is inf:
            sizes[1] = sizes[0]
    # 1.3 Maximize tracks.
    # TODO: Include gutters.
    if box_size == 'auto':
        free_space = 0
    else:
        free_space = box_size - sum(size[0] for size in tracks_sizes)
    if free_space > 0:
        distributed_free_space = free_space / len(tracks_sizes)
        for i, sizes in enumerate(tracks_sizes):
            base_size, growth_limit = sizes
            if base_size + distributed_free_space > growth_limit:
                sizes[0] = growth_limit
                free_space -= growth_limit - base_size
            else:
                sizes[0] += distributed_free_space
                free_space -= distributed_free_space
    # TODO: Respect max-width/-height.
    # 1.4 Expand flexible tracks.
    if free_space <= 0:
        # TODO: Respect min-content constraint.
        flex_fraction = 0
    else:
        # TODO: Take care of indefinite free space (!).
        stop = False
        while not stop:
            leftover_space = free_space
            flex_factor_sum = 0
            inflexible_tracks = set()
            iterable = enumerate(zip(tracks_sizes, sizing_functions))
            for i, (sizes, (_, max_function)) in iterable:
                if i not in inflexible_tracks and _is_fr(max_function):
                    flex_factor_sum += max_function.value
            flex_factor_sum = max(1, flex_factor_sum)
            hypothetical_fr_size = leftover_space / flex_factor_sum
            stop = True
            iterable = enumerate(zip(tracks_sizes, sizing_functions))
            for i, (sizes, (_, max_function)) in iterable:
                if i not in inflexible_tracks and _is_fr(max_function):
                    if hypothetical_fr_size * max_function.value < sizes[0]:
                        inflexible_tracks.add(i)
                        stop = False
        flex_fraction = hypothetical_fr_size
        iterable = enumerate(zip(tracks_sizes, sizing_functions))
        for i, (sizes, (_, max_function)) in iterable:
            if _is_fr(max_function):
                if flex_fraction * max_function.value > sizes[0]:
                    free_space -= flex_fraction * max_function.value
                    sizes[0] += flex_fraction * max_function.value
    # 1.5 Expand stretched auto tracks.
    x_stretch = (
        direction == 'x' and
        containing_block.style['justify_content'] in ('normal', 'stretch'))
    y_stretch = (
        direction == 'y' and
        containing_block.style['align_content'] in ('normal', 'stretch'))
    if (x_stretch or y_stretch) and free_space > 0:
        auto_tracks_sizes = [
            sizes for sizes, (min_function, _)
            in zip(tracks_sizes, sizing_functions)
            if min_function == 'auto']
        if auto_tracks_sizes:
            distributed_free_space = free_space / len(auto_tracks_sizes)
            for sizes in auto_tracks_sizes:
                sizes[0] += distributed_free_space

    return tracks_sizes


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
    columns = [
        column if i % 2 else list(column) for i, column in enumerate(columns)]

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
            names = [name for row in rows[::2] for name in row]
            if start_name not in names:
                rows[2*y].append(start_name)
            names = [name for column in columns[::2] for name in column]
            if start_name not in names:
                columns[2*x].append(start_name)
    for y, row in enumerate(grid_areas[::-1]):
        for x, area_name in enumerate(row[::-1]):
            if area_name is None:
                continue
            end_name = f'{area_name}-end'
            names = [name for row in rows[::2] for name in row]
            if end_name not in names:
                rows[-2*y-1].append(end_name)
            names = [name for column in columns[::2] for name in column]
            if end_name not in names:
                columns[-2*x-1].append(end_name)

    # 1. Run the grid placement algorithm.

    # 1.1 Position anything that’s not auto-positioned.
    children_positions = {}
    for child in box.children:
        column_start = child.style['grid_column_start']
        column_end = child.style['grid_column_end']
        row_start = child.style['grid_row_start']
        row_end = child.style['grid_row_end']

        column_placement = _get_placement(
            column_start, column_end, columns[::2])
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
                        y, height = _get_placement(
                            (None, y + 1, None), row_end, rows[::2])
                    else:
                        assert row_start[0] == 'span'
                        assert row_start == 'auto' or row_start[1] == 'span'
                        span = _get_span(row_start)
                        y, height = _get_placement(
                            row_start, (None, y + 1 + span, None), rows[::2])
                    if y < cursor_y:
                        continue
                    for row in range(y, y + height):
                        intersect = _intersect_with_children(
                            x, y, width, height, children_positions.values())
                        if intersect:
                            # Child intersects with a positioned child on
                            # current row.
                            break
                    else:
                        # Child doesn’t intersect with any positioned child on
                        # any row.
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
                            y, height = _get_placement(
                                (None, y + 1, None), row_end, rows[::2])
                        else:
                            span = _get_span(row_start)
                            y, height = _get_placement(
                                row_start, (None, y + 1 + span, None),
                                rows[::2])
                        if column_start == 'auto':
                            x, width = _get_placement(
                                (None, x + 1, None), column_end, columns[::2])
                        else:
                            span = _get_span(column_start)
                            x, width = _get_placement(
                                column_start, (None, x + 1 + span, None),
                                columns[::2])
                        intersect = _intersect_with_children(
                            x, y, width, height, children_positions.values())
                        if intersect:
                            # Child intersects with a positioned child.
                            continue
                        else:
                            # Free place found.
                            # 3. Set the item’s row-/column-start lines.
                            children_positions[child] = (x, y, width, height)
                            y_diff = cursor_y + height - 1 - implicit_y2
                            if y_diff > 0:
                                for _ in range(y_diff):
                                    rows.append(next(auto_rows))
                                    rows.append([])
                                implicit_y2 = cursor_y + height - 1
                            break
                    else:
                        # No room found.
                        # 2. Return to the previous step.
                        cursor_y += 1
                        y_diff = cursor_y + 1 - implicit_y2
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
                        y, height = _get_placement(
                            (None, y + 1, None), row_end, rows[::2])
                    else:
                        assert row_start[0] == 'span'
                        assert row_start == 'auto' or row_start[1] == 'span'
                        span = _get_span(row_start)
                        y, height = _get_placement(
                            row_start, (None, y + 1 + span, None), rows[::2])
                    if y < cursor_y:
                        continue
                    for row in range(y, y + height):
                        intersect = _intersect_with_children(
                            x, y, width, height, children_positions.values())
                        if intersect:
                            # Child intersects with a positioned child on
                            # current row.
                            break
                    else:
                        # Child doesn’t intersect with any positioned child on
                        # any row.
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
                            y, height = _get_placement(
                                (None, y + 1, None), row_end, rows[::2])
                        else:
                            span = _get_span(row_start)
                            y, height = _get_placement(
                                row_start, (None, y + 1 + span, None),
                                rows[::2])
                        if column_start == 'auto':
                            x, width = _get_placement(
                                (None, x + 1, None), column_end, columns[::2])
                        else:
                            span = _get_span(column_start)
                            x, width = _get_placement(
                                column_start, (None, x + 1 + span, None),
                                columns[::2])
                        intersect = _intersect_with_children(
                            x, y, width, height, children_positions.values())
                        if intersect:
                            # Child intersects with a positioned child.
                            continue
                        else:
                            # Free place found.
                            # 2. Set the item’s row-/column-start lines.
                            children_positions[child] = (x, y, width, height)
                            break
                    else:
                        # No room found.
                        # 2. Return to the previous step.
                        cursor_y += 1
                        y_diff = cursor_y + 1 - implicit_y2
                        if y_diff > 0:
                            for _ in range(y_diff):
                                rows.append(next(auto_rows))
                                rows.append([])
                            implicit_y2 = cursor_y
                        cursor_x = implicit_x1
                        continue
                    break

    # 2. Find the size of the grid container.

    if isinstance(box, boxes.GridBox):
        from .block import block_level_width
        block_level_width(box, containing_block)
    else:
        assert isinstance(box, boxes.InlineGridBox)
        from .inline import inline_block_width
        inline_block_width(box, context, containing_block)
    if box.width == 'auto':
        # TODO: calculate max-width
        box.width = containing_block.width

    # 3. Run the grid sizing algorithm.

    # 3.0 List min/max sizing functions.
    row_sizing_functions = [_get_sizing_functions(row) for row in rows[1::2]]
    column_sizing_functions = [
        _get_sizing_functions(column) for column in columns[1::2]]

    # 3.1 Resolve the sizes of the grid columns.
    columns_sizes = _resolve_tracks_sizes(
        column_sizing_functions, box.width, children_positions, implicit_x1,
        'x', context, box)

    # 3.2 Resolve the sizes of the grid rows.
    rows_sizes = _resolve_tracks_sizes(
        row_sizing_functions, box.height, children_positions, implicit_y1, 'y',
        context, box)

    # 3.3 Re-resolve the sizes of the grid columns with min-/max-content.
    # TODO: Re-resolve.
    # 3.4 Re-re-resolve the sizes of the grid columns with min-/max-content.
    # TODO: Re-re-resolve.
    # 3.5 Align the tracks within the grid container.
    # TODO: Align.

    # 4. Lay out the grid items into their respective containing blocks.
    new_children = []
    for child in children:
        from .block import block_level_layout
        x, y, width, height = children_positions[child]
        # TODO: Include gutters, margins, borders, paddings.
        child.position_x = box.content_box_x() + sum(
            size for size, _ in columns_sizes[:x])
        child.position_y = box.content_box_y() + sum(
            size for size, _ in rows_sizes[:y])
        width = sum(size for size, _ in columns_sizes[x:x+width])
        height = sum(size for size, _ in rows_sizes[y:y+height])
        new_child, resume_at, next_page, _, _, _ = block_level_layout(
            context, child, bottom_space, skip_stack, (width, height),
            page_is_empty, absolute_boxes, fixed_boxes)
        new_child.width = max(width, new_child.width)
        new_child.height = max(height, new_child.height)
        # TODO: Take care of page fragmentation.
        new_children.append(new_child)

    # TODO: Include gutters, margins, borders, paddings.
    box.height = sum(size for size, _ in rows_sizes)
    box.children = new_children
    return box, None, {'break': 'any', 'page': None}, [], False
