"""Preferred and minimum preferred width.

Also known as max-content and min-content width, also known as the
shrink-to-fit algorithm.

Terms used (max-content width, min-content width) are defined in David
Baron's unofficial draft (https://dbaron.org/css/intrinsic/).

"""

import sys
from functools import cache
from math import inf

from ..formatting_structure import boxes
from ..text.line_break import split_first_line
from .replaced import default_image_sizing


def shrink_to_fit(context, box, available_content_width):
    """Return the shrink-to-fit width of ``box``.

    *Warning:* both available_content_width and the return value are
    for width of the *content area*, not margin area.

    https://www.w3.org/TR/CSS21/visudet.html#float-width

    """
    return min(
        max(
            min_content_width(context, box, outer=False),
            available_content_width),
        max_content_width(context, box, outer=False))


def min_content_width(context, box, outer=True):
    """Return the min-content width for ``box``.

    This is the width by breaking at every line-break opportunity.

    """
    if box.is_table_wrapper:
        return table_and_columns_preferred_widths(context, box, outer)[0]
    elif isinstance(box, boxes.TableCellBox):
        return table_cell_min_content_width(context, box, outer)
    elif isinstance(box, (
            boxes.BlockContainerBox, boxes.TableColumnBox, boxes.FlexBox)):
        return block_min_content_width(context, box, outer)
    elif isinstance(box, boxes.TableColumnGroupBox):
        return column_group_content_width(context, box)
    elif isinstance(box, (boxes.InlineBox, boxes.LineBox)):
        return inline_min_content_width(
            context, box, outer, is_line_start=True)
    elif isinstance(box, boxes.ReplacedBox):
        return replaced_min_content_width(box, outer)
    elif isinstance(box, boxes.FlexContainerBox):
        return flex_min_content_width(context, box, outer)
    elif isinstance(box, boxes.GridContainerBox):
        # TODO: Get real grid size.
        return block_min_content_width(context, box, outer)
    else:
        raise TypeError(
            f'min-content width for {type(box).__name__} not handled yet')


def max_content_width(context, box, outer=True):
    """Return the max-content width for ``box``.

    This is the width by only breaking at forced line breaks.

    """
    if box.is_table_wrapper:
        return table_and_columns_preferred_widths(context, box, outer)[1]
    elif isinstance(box, boxes.TableCellBox):
        return table_cell_min_max_content_width(context, box, outer)[1]
    elif isinstance(box, (
            boxes.BlockContainerBox, boxes.TableColumnBox, boxes.FlexBox)):
        return block_max_content_width(context, box, outer)
    elif isinstance(box, boxes.TableColumnGroupBox):
        return column_group_content_width(context, box)
    elif isinstance(box, (boxes.InlineBox, boxes.LineBox)):
        return inline_max_content_width(
            context, box, outer, is_line_start=True)
    elif isinstance(box, boxes.ReplacedBox):
        return replaced_max_content_width(box, outer)
    elif isinstance(box, boxes.FlexContainerBox):
        return flex_max_content_width(context, box, outer)
    elif isinstance(box, boxes.GridContainerBox):
        # TODO: Get real grid size.
        return block_max_content_width(context, box, outer)
    else:
        raise TypeError(
            f'max-content width for {type(box).__name__} not handled yet')


def _block_content_width(context, box, function, outer):
    """Helper to create ``block_*_content_width.``"""
    width = box.style['width']
    if width == 'auto' or width.unit == '%':
        # "percentages on the following properties are treated instead as
        # though they were the following: width: auto"
        # https://dbaron.org/css/intrinsic/#outer-intrinsic
        children_widths = [
            function(context, child, outer=True) for child in box.children
            if not child.is_absolutely_positioned()]
        width = max(children_widths) if children_widths else 0
    else:
        assert width.unit == 'px'
        width = width.value

    return adjust(box, outer, width)


def min_max(box, width):
    """Get box width from given width and box min- and max-widths."""
    min_width = box.style['min_width']
    max_width = box.style['max_width']
    if min_width == 'auto' or min_width.unit == '%':
        min_width = 0
    else:
        min_width = min_width.value
    if max_width == 'auto' or max_width.unit == '%':
        max_width = inf
    else:
        max_width = max_width.value

    if isinstance(box, boxes.ReplacedBox):
        _, _, ratio = box.replacement.get_intrinsic_size(
            1, box.style['font_size'])
        if ratio is not None:
            min_height = box.style['min_height']
            if min_height != 'auto' and min_height.unit != '%':
                min_width = max(min_width, min_height.value * ratio)
            max_height = box.style['max_height']
            if max_height != 'auto' and max_height.unit != '%':
                max_width = min(max_width, max_height.value * ratio)

    return max(min_width, min(width, max_width))


def margin_width(box, width, left=True, right=True):
    """Add box paddings, borders and margins to ``width``."""
    percentages = 0

    # See https://drafts.csswg.org/css-tables-3/#cell-intrinsic-offsets
    # It is a set of computed values for border-left-width, padding-left,
    # padding-right, and border-right-width (along with zero values for
    # margin-left and margin-right)
    for value in (
        (['margin_left', 'padding_left'] if left else []) +
        (['margin_right', 'padding_right'] if right else [])
    ):
        style_value = box.style[value]
        if style_value != 'auto':
            if style_value.unit == 'px':
                width += style_value.value
            else:
                assert style_value.unit == '%'
                percentages += style_value.value

    collapse = box.style['border_collapse'] == 'collapse'
    if left:
        if collapse and hasattr(box, 'border_left_width'):
            # In collapsed-borders mode: the computed horizontal padding of the
            # cell and, for border values, the used border-width values of the
            # cell (half the winning border-width)
            width += box.border_left_width
        else:
            # In separated-borders mode: the computed horizontal padding and
            # border of the table-cell
            width += box.style['border_left_width']
    if right:
        if collapse and hasattr(box, 'border_right_width'):
            # [...] the used border-width values of the cell
            width += box.border_right_width
        else:
            # [...] the computed border of the table-cell
            width += box.style['border_right_width']

    if percentages < 100:
        return width / (1 - percentages / 100)
    else:
        # Pathological case, ignore
        return 0


def adjust(box, outer, width, left=True, right=True):
    """Respect min/max and adjust width depending on ``outer``.

    If ``outer`` is set to ``True``, return margin width, else return content
    width.

    """
    fixed = min_max(box, width)

    if outer:
        return margin_width(box, fixed, left, right)
    else:
        return fixed


def block_min_content_width(context, box, outer=True):
    """Return the min-content width for a ``BlockBox``."""
    return _block_content_width(
        context, box, min_content_width, outer)


def block_max_content_width(context, box, outer=True):
    """Return the max-content width for a ``BlockBox``."""
    return _block_content_width(context, box, max_content_width, outer)


def inline_min_content_width(context, box, outer=True, skip_stack=None,
                             first_line=False, is_line_start=False):
    """Return the min-content width for an ``InlineBox``.

    The width is calculated from the lines from ``skip_stack``. If
    ``first_line`` is ``True``, only the first line minimum width is
    calculated.

    """
    widths = inline_line_widths(
        context, box, outer, is_line_start, minimum=True,
        skip_stack=skip_stack, first_line=first_line)
    width = next(widths) if first_line else max(widths)
    return adjust(box, outer, width)


def inline_max_content_width(context, box, outer=True, is_line_start=False):
    """Return the max-content width for an ``InlineBox``."""
    widths = list(
        inline_line_widths(context, box, outer, is_line_start, minimum=False))
    # Remove trailing space, as split_first_line keeps trailing spaces when
    # max_width is not set.
    widths[-1] -= trailing_whitespace_size(context, box)
    return adjust(box, outer, max(widths))


def column_group_content_width(context, box):
    """Return the *-content width for a ``TableColumnGroupBox``."""
    width = box.style['width']
    if width == 'auto' or width.unit == '%':
        width = 0
    else:
        assert width.unit == 'px'
        width = width.value

    return adjust(box, False, width)


def table_cell_min_content_width(context, box, outer):
    """Return the min-content width for a ``TableCellBox``."""
    # See https://www.w3.org/TR/css-tables-3/#outer-min-content
    # The outer min-content width of a table-cell is
    # max(min-width, min-content width) adjusted by
    # the cell intrinsic offsets.
    children_widths = [
        min_content_width(context, child)
        for child in box.children
        if not child.is_absolutely_positioned()]
    children_min_width = adjust(
        box,
        outer,
        max(children_widths) if children_widths else 0)

    return children_min_width


def table_cell_min_max_content_width(context, box, outer=True):
    """Return the min- and max-content width for a ``TableCellBox``."""
    # This is much faster than calling min and max separately.
    min_width = table_cell_min_content_width(context, box, outer)
    max_width = max(min_width, block_max_content_width(context, box, outer))
    return min_width, max_width


def inline_line_widths(context, box, outer, is_line_start, minimum, skip_stack=None,
                       first_line=False):
    if isinstance(box, boxes.LineBox) and box.style['text_indent'].unit != '%':
        text_indent = box.style['text_indent'].value
    else:
        text_indent = 0

    current_line = 0
    if skip_stack is None:
        skip = 0
    else:
        (skip, skip_stack), = skip_stack.items()
    for child in box.children[skip:]:
        if child.is_absolutely_positioned():
            continue  # Skip

        if isinstance(child, boxes.InlineBox):
            lines = inline_line_widths(
                context, child, outer, is_line_start, minimum, skip_stack,
                first_line)
            if first_line:
                lines = [next(lines)]
            else:
                lines = list(lines)
            if len(lines) == 1:
                lines[0] = adjust(child, outer, lines[0])
            else:
                lines[0] = adjust(child, outer, lines[0], right=False)
                lines[-1] = adjust(child, outer, lines[-1], left=False)
        elif isinstance(child, boxes.TextBox):
            space_collapse = child.style['white_space'] in (
                'normal', 'nowrap', 'pre-line')
            if skip_stack is None:
                skip = 0
            else:
                (skip, skip_stack), = skip_stack.items()
                assert skip_stack is None
            child_text = child.text.encode()[(skip or 0):]
            if is_line_start and space_collapse:
                child_text = child_text.lstrip(b' ')
            if minimum and child_text == b' ':
                lines = [0, 0]
            else:
                max_width = 0 if minimum else None
                lines = []
                resume_index = new_resume_index = 0
                while new_resume_index is not None:
                    resume_index += new_resume_index
                    _, _, new_resume_index, width, _, _ = (
                        split_first_line(
                            child_text[resume_index:].decode(), child.style,
                            context, max_width, child.justification_spacing,
                            is_line_start=is_line_start, minimum=True))
                    lines.append(width)
                    if first_line:
                        break
                if first_line and new_resume_index:
                    current_line += lines[0]
                    break
        else:
            # https://www.w3.org/TR/css-text-3/#overflow-wrap
            # "The line breaking behavior of a replaced element
            #  or other atomic inline is equivalent to that
            #  of the Object Replacement Character (U+FFFC)."
            # https://www.unicode.org/reports/tr14/#DescriptionOfProperties
            # "By default, there is a break opportunity
            #  both before and after any inline object."
            if minimum:
                lines = [0, max_content_width(context, child), 0]
            else:
                lines = [max_content_width(context, child)]
        # The first text line goes on the current line
        current_line += lines[0]
        if len(lines) > 1:
            # Forced line break
            yield current_line + text_indent
            text_indent = 0
            if len(lines) > 2:
                for line in lines[1:-1]:
                    yield line
            current_line = lines[-1]
        is_line_start = lines[-1] == 0
        skip_stack = None
    yield current_line + text_indent


def _percentage_contribution(box):
    """Return the percentage contribution of a cell, column or column group.

    https://dbaron.org/css/intrinsic/#pct-contrib

    """
    min_width = (
        box.style['min_width'].value if box.style['min_width'] != 'auto' and
        box.style['min_width'].unit == '%' else 0)
    max_width = (
        box.style['max_width'].value if box.style['max_width'] != 'auto' and
        box.style['max_width'].unit == '%' else inf)
    width = (
        box.style['width'].value if box.style['width'] != 'auto' and
        box.style['width'].unit == '%' else 0)
    return max(min_width, min(width, max_width))


def table_and_columns_preferred_widths(context, box, outer=True):
    """Return content widths for the auto layout table and its columns.

    The tuple returned is
    ``(table_min_content_width, table_max_content_width,
       column_min_content_widths, column_max_content_widths,
       column_intrinsic_percentages, constrainedness,
       total_horizontal_border_spacing, grid)``

    https://dbaron.org/css/intrinsic/

    """
    from .table import distribute_excess_width

    table = box.get_wrapped_table()
    result = context.tables.get(table)
    if result:
        return result[outer]

    # Create the grid
    grid_width, grid_height = 0, 0
    row_number = 0
    for row_group in table.children:
        for row in row_group.children:
            for cell in row.children:
                grid_width = max(cell.grid_x + cell.colspan, grid_width)
                grid_height = max(row_number + cell.rowspan, grid_height)
            row_number += 1
    grid = [[None] * grid_width for i in range(grid_height)]
    row_number = 0
    for row_group in table.children:
        for row in row_group.children:
            for cell in row.children:
                grid[row_number][cell.grid_x] = cell
            row_number += 1

    zipped_grid = list(zip(*grid))

    # Define the total horizontal border spacing
    if table.style['border_collapse'] == 'separate' and grid_width > 0:
        total_horizontal_border_spacing = (
            table.style['border_spacing'][0] *
            (1 + len([column for column in zipped_grid if any(column)])))
    else:
        total_horizontal_border_spacing = 0

    if grid_width == 0 or grid_height == 0:
        table.children = []
        min_width = block_min_content_width(context, table, outer=False)
        max_width = block_max_content_width(context, table, outer=False)
        outer_min_width = adjust(
            box, outer=True, width=block_min_content_width(context, table))
        outer_max_width = adjust(
            box, outer=True, width=block_max_content_width(context, table))
        result = ([], [], [], [], total_horizontal_border_spacing, [])
        context.tables[table] = result = {
            False: (min_width, max_width, *result),
            True: (outer_min_width, outer_max_width, *result),
        }
        return result[outer]

    column_groups = [None] * grid_width
    columns = [None] * grid_width
    column_number = 0
    for column_group in table.column_groups:
        for column in column_group.children:
            column_groups[column_number] = column_group
            columns[column_number] = column
            column_number += 1
            if column_number == grid_width:
                break
        else:
            continue
        break

    colspan_cells = []
    colspans = set()

    # Define the intermediate content widths
    min_content_widths = [0] * grid_width
    max_content_widths = [0] * grid_width
    intrinsic_percentages = [0] * grid_width

    # Intermediate content widths for span 1
    for i in range(grid_width):
        for groups in (column_groups, columns):
            if group := groups[i]:
                min_content_widths[i] = max(
                    min_content_widths[i], min_content_width(context, group))
                max_content_widths[i] = max(
                    max_content_widths[i], max_content_width(context, group))
                intrinsic_percentages[i] = max(
                    intrinsic_percentages[i], _percentage_contribution(group))
        for cell in zipped_grid[i]:
            if not cell:
                continue
            if cell.colspan == 1:
                min_width, max_width = table_cell_min_max_content_width(context, cell)
                min_content_widths[i] = max(min_content_widths[i], min_width)
                max_content_widths[i] = max(max_content_widths[i], max_width)
                intrinsic_percentages[i] = max(
                    intrinsic_percentages[i], _percentage_contribution(cell))
            else:
                colspan_cells.append(cell)
                colspans.add(cell.colspan - 1)

    # Intermediate content widths for span > 1 is wrong in the 4.1 section, as
    # explained in its third issue. Min- and max-content widths are handled by
    # the excess width distribution method, and percentages do not distribute
    # widths to columns that have originating cells.

    # Intermediate intrinsic percentage widths for span > 1
    rows_origins = []
    for y, row in enumerate(grid):
        origin = None
        rows_origins.append(row_origins := [])
        for x, cell in enumerate(row):
            if cell:
                origin = x
            row_origins.append(origin)

    @cache
    def get_percentage_contribution(origin_cell, origin, max_content_width):
        # Cached for big colspan values, see #1155.
        cell_slice = slice(origin, origin + origin_cell.colspan)
        baseline_percentage = sum(intrinsic_percentages[cell_slice])
        cell_percentage_contribution = _percentage_contribution(origin_cell)
        diff = max(0, cell_percentage_contribution - baseline_percentage)
        other_columns_contributions = [
            max_content_widths[j]
            for j in range(origin, origin + origin_cell.colspan)
            if intrinsic_percentages[j] == 0]
        other_columns_contributions_sum = sum(other_columns_contributions)
        if other_columns_contributions_sum == 0:
            ratio = 1 / (len(other_columns_contributions) or 1)
        else:
            ratio = max_content_width / other_columns_contributions_sum
        return diff * ratio

    for span in sorted(colspans):
        percentage_contributions = []
        for i in range(grid_width):
            if percentage_contribution := intrinsic_percentages[i]:
                percentage_contributions.append(percentage_contribution)
                continue
            for row, row_origins in zip(grid, rows_origins):
                if (origin := row_origins[i]) is None:
                    continue
                origin_cell = row[origin]
                if origin_cell.colspan - 1 != span:
                    continue
                cell_percentage_contribution = get_percentage_contribution(
                    origin_cell, origin, max_content_widths[i])
                percentage_contribution = max(
                    percentage_contribution, cell_percentage_contribution)

            percentage_contributions.append(percentage_contribution)

        intrinsic_percentages = percentage_contributions

    # Define constrainedness
    constrainedness = [False for i in range(grid_width)]
    for i in range(grid_width):
        if (column_groups[i] and column_groups[i].style['width'] != 'auto' and
                column_groups[i].style['width'].unit != '%'):
            constrainedness[i] = True
            continue
        if (columns[i] and columns[i].style['width'] != 'auto' and
                columns[i].style['width'].unit != '%'):
            constrainedness[i] = True
            continue
        for cell in zipped_grid[i]:
            if (cell and cell.colspan == 1 and
                    cell.style['width'] != 'auto' and
                    cell.style['width'].unit != '%'):
                constrainedness[i] = True
                break

    intrinsic_percentages = [
        min(percentage, 100 - sum(intrinsic_percentages[:i]))
        for i, percentage in enumerate(intrinsic_percentages)]

    # Max- and min-content widths for span > 1
    for cell in colspan_cells:
        min_content = min_content_width(context, cell)
        max_content = max_content_width(context, cell)
        column_slice = slice(cell.grid_x, cell.grid_x + cell.colspan)
        columns_min_content = sum(min_content_widths[column_slice])
        columns_max_content = sum(max_content_widths[column_slice])
        if table.style['border_collapse'] == 'separate':
            spacing = (cell.colspan - 1) * table.style['border_spacing'][0]
        else:
            spacing = 0

        if min_content > columns_min_content + spacing:
            excess_width = min_content - (columns_min_content + spacing)
            distribute_excess_width(
                context, zipped_grid, excess_width, min_content_widths,
                constrainedness, intrinsic_percentages, max_content_widths,
                column_slice)

        if max_content > columns_max_content + spacing:
            excess_width = max_content - (columns_max_content + spacing)
            distribute_excess_width(
                context, zipped_grid, excess_width, max_content_widths,
                constrainedness, intrinsic_percentages, max_content_widths,
                column_slice)

    # Calculate the max- and min-content widths of table and columns
    small_percentage_contributions = [
        max_content_widths[i] / (intrinsic_percentages[i] / 100)
        for i in range(grid_width)
        if intrinsic_percentages[i]]
    large_percentage_contribution_numerator = sum(
        max_content_widths[i] for i in range(grid_width)
        if intrinsic_percentages[i] == 0)
    large_percentage_contribution_denominator = (
        (100 - sum(intrinsic_percentages)) / 100)
    if large_percentage_contribution_denominator == 0:
        if large_percentage_contribution_numerator == 0:
            large_percentage_contribution = 0
        else:
            # "the large percentage contribution of the table [is] an
            # infinitely large number if the numerator is nonzero [and] the
            # denominator of that ratio is 0."
            #
            # https://dbaron.org/css/intrinsic/#autotableintrinsic
            #
            # Please note that "an infinitely large number" is not "infinite",
            # and that's probably not a coincindence: putting 'inf' here breaks
            # some cases (see #305).
            large_percentage_contribution = sys.maxsize
    else:
        large_percentage_contribution = (
            large_percentage_contribution_numerator /
            large_percentage_contribution_denominator)

    table_min_content_width = (
        total_horizontal_border_spacing + sum(min_content_widths))
    table_max_content_width = (
        total_horizontal_border_spacing + max([
            sum(max_content_widths), large_percentage_contribution,
            *small_percentage_contributions]))

    if table.style['width'] != 'auto' and table.style['width'].unit == 'px':
        # "percentages on the following properties are treated instead as
        # though they were the following: width: auto"
        # https://dbaron.org/css/intrinsic/#outer-intrinsic
        table_min_width = table_max_width = table.style['width'].value
    else:
        table_min_width = table_min_content_width
        table_max_width = table_max_content_width

    table_min_content_width = max(
        table_min_content_width, adjust(
            table, outer=False, width=table_min_width))
    table_max_content_width = max(
        table_max_content_width, adjust(
            table, outer=False, width=table_max_width))
    table_outer_min_content_width = margin_width(
        table, margin_width(box, table_min_content_width))
    table_outer_max_content_width = margin_width(
        table, margin_width(box, table_max_content_width))

    result = (
        min_content_widths, max_content_widths, intrinsic_percentages,
        constrainedness, total_horizontal_border_spacing, zipped_grid)
    context.tables[table] = result = {
        False: (table_min_content_width, table_max_content_width, *result),
        True: (table_outer_min_content_width, table_outer_max_content_width, *result),
    }
    return result[outer]


def replaced_min_content_width(box, outer=True):
    """Return the min-content width for an ``InlineReplacedBox``."""
    width = box.style['width']
    if width == 'auto':
        height = box.style['height']
        if height == 'auto' or height.unit == '%':
            height = 'auto'
        else:
            assert height.unit == 'px'
            height = height.value
        if (box.style['max_width'] != 'auto' and
                box.style['max_width'].unit == '%'):
            # See https://drafts.csswg.org/css-sizing/#intrinsic-contribution
            width = 0
        else:
            image = box.replacement
            intrinsic_width, intrinsic_height, intrinsic_ratio = (
                image.get_intrinsic_size(
                    box.style['image_resolution'], box.style['font_size']))
            width, _ = default_image_sizing(
                intrinsic_width, intrinsic_height, intrinsic_ratio, 'auto',
                height, default_width=300, default_height=150)
    elif box.style['width'].unit == '%':
        # See https://drafts.csswg.org/css-sizing/#intrinsic-contribution
        width = 0
    else:
        assert width.unit == 'px'
        width = width.value
    return adjust(box, outer, width)


def replaced_max_content_width(box, outer=True):
    """Return the max-content width for an ``InlineReplacedBox``."""
    width = box.style['width']
    if width == 'auto':
        height = box.style['height']
        if height == 'auto' or height.unit == '%':
            height = 'auto'
        else:
            assert height.unit == 'px'
            height = height.value
        image = box.replacement
        intrinsic_width, intrinsic_height, intrinsic_ratio = (
            image.get_intrinsic_size(
                box.style['image_resolution'], box.style['font_size']))
        width, _ = default_image_sizing(
            intrinsic_width, intrinsic_height, intrinsic_ratio, 'auto', height,
            default_width=300, default_height=150)
    elif box.style['width'].unit == '%':
        # See https://drafts.csswg.org/css-sizing/#intrinsic-contribution
        width = 0
    else:
        assert width.unit == 'px'
        width = width.value
    return adjust(box, outer, width)


def flex_min_content_width(context, box, outer=True):
    """Return the min-content width for an ``FlexContainerBox``."""
    # TODO: use real values, see
    # https://www.w3.org/TR/css-flexbox-1/#intrinsic-sizes
    min_contents = [
        min_content_width(context, child)
        for child in box.children if child.is_flex_item]
    if not min_contents:
        return adjust(box, outer, 0)
    if (box.style['flex_direction'].startswith('row') and
            box.style['flex_wrap'] == 'nowrap'):
        return adjust(box, outer, sum(min_contents))
    else:
        return adjust(box, outer, max(min_contents))


def flex_max_content_width(context, box, outer=True):
    """Return the max-content width for an ``FlexContainerBox``."""
    # TODO: use real values, see
    # https://www.w3.org/TR/css-flexbox-1/#intrinsic-sizes
    max_contents = [
        max_content_width(context, child)
        for child in box.children if child.is_flex_item]
    if not max_contents:
        return adjust(box, outer, 0)
    if box.style['flex_direction'].startswith('row'):
        return adjust(box, outer, sum(max_contents))
    else:
        return adjust(box, outer, max(max_contents))


def trailing_whitespace_size(context, box):
    """Return the size of the trailing whitespace of ``box``."""
    from .inline import split_first_line, split_text_box

    while isinstance(box, (boxes.InlineBox, boxes.LineBox)):
        if not box.children:
            return 0
        box = box.children[-1]
    if not (isinstance(box, boxes.TextBox) and box.text and
            box.style['white_space'] in ('normal', 'nowrap', 'pre-line')):
        return 0
    stripped_text = box.text.rstrip(' ')
    if box.style['font_size'] == 0 or len(stripped_text) == len(box.text):
        return 0
    if stripped_text:
        resume = 0
        while resume is not None:
            old_resume = resume
            old_box, resume, _ = split_text_box(context, box, None, resume)
        assert old_box
        stripped_box = box.copy_with_text(stripped_text)
        stripped_box, resume, _ = split_text_box(
            context, stripped_box, None, old_resume)
        if stripped_box is None:
            # old_box split just before the trailing spaces
            return old_box.width
        else:
            assert resume is None
            return old_box.width - stripped_box.width
    else:
        _, _, _, width, _, _ = split_first_line(
            box.text, box.style, context, None, box.justification_spacing)
        return width
