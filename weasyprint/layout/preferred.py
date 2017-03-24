# coding: utf-8
"""
    weasyprint.layout.preferred
    ---------------------------

    Preferred and minimum preferred width, aka. max-content and min-content
    width, aka. the shrink-to-fit algorithm.

    Terms used (max-content width, min-content width) are defined in David
    Baron's unofficial draft (http://dbaron.org/css/intrinsic/).

    :copyright: Copyright 2011-2016 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import sys
import weakref

from .. import text
from ..formatting_structure import boxes
from .replaced import default_image_sizing


def shrink_to_fit(context, box, available_width):
    """Return the shrink-to-fit width of ``box``.

    *Warning:* both available_outer_width and the return value are
    for width of the *content area*, not margin area.

    http://www.w3.org/TR/CSS21/visudet.html#float-width

    """
    return min(
        max(
            min_content_width(context, box, outer=False),
            available_width),
        max_content_width(context, box, outer=False))


def min_content_width(context, box, outer=True):
    """Return the min-content width for ``box``.

    This is the width by breaking at every line-break opportunity.

    """
    if isinstance(box, (boxes.BlockContainerBox, boxes.TableColumnBox)):
        if box.is_table_wrapper:
            return table_and_columns_preferred_widths(context, box, outer)[0]
        else:
            return block_min_content_width(context, box, outer)
    elif isinstance(box, boxes.TableColumnGroupBox):
        return column_group_content_width(context, box)
    elif isinstance(box, (boxes.InlineBox, boxes.LineBox)):
        return inline_min_content_width(
            context, box, outer, is_line_start=True)
    elif isinstance(box, boxes.ReplacedBox):
        return replaced_min_content_width(box, outer)
    else:
        raise TypeError(
            'min-content width for %s not handled yet' %
            type(box).__name__)


def max_content_width(context, box, outer=True):
    """Return the max-content width for ``box``.

    This is the width by only breaking at forced line breaks.

    """
    if isinstance(box, (boxes.BlockContainerBox, boxes.TableColumnBox)):
        if box.is_table_wrapper:
            return table_and_columns_preferred_widths(context, box, outer)[1]
        else:
            return block_max_content_width(context, box, outer)
    elif isinstance(box, boxes.TableColumnGroupBox):
        return column_group_content_width(context, box)
    elif isinstance(box, (boxes.InlineBox, boxes.LineBox)):
        return inline_max_content_width(
            context, box, outer, is_line_start=True)
    elif isinstance(box, boxes.ReplacedBox):
        return replaced_min_content_width(box, outer)
    else:
        raise TypeError(
            'max-content width for %s not handled yet' % type(box).__name__)


def _block_content_width(context, box, function, outer):
    """Helper to create ``block_*_content_width.``"""
    width = box.style.width
    if width == 'auto' or width.unit == '%':
        # "percentages on the following properties are treated instead as
        # though they were the following: width: auto"
        # http://dbaron.org/css/intrinsic/#outer-intrinsic
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
    min_width = box.style.min_width
    max_width = box.style.max_width
    min_width = min_width.value if min_width.unit != '%' else 0
    max_width = max_width.value if max_width.unit != '%' else float('inf')
    return max(min_width, min(width, max_width))


def margin_width(box, width, left=True, right=True):
    """Add box paddings, borders and margins to ``width``."""
    percentages = 0

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

    if left:
        width += box.style.border_left_width
    if right:
        width += box.style.border_right_width

    if percentages < 100:
        return width / (1 - percentages / 100.)
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
    widths = list(inline_line_widths(
        context, box, outer, is_line_start, minimum=True,
        skip_stack=skip_stack))

    if first_line and len(widths) > 1:
        del widths[1:]
    else:
        widths[-1] -= trailing_whitespace_size(context, box)
    return adjust(box, outer, max(widths))


def inline_max_content_width(context, box, outer=True, is_line_start=False):
    """Return the max-content width for an ``InlineBox``."""
    widths = list(
        inline_line_widths(context, box, outer, is_line_start, minimum=False))
    widths[-1] -= trailing_whitespace_size(context, box)
    return adjust(box, outer, max(widths))


def column_group_content_width(context, box):
    """Return the *-content width for an ``TableColumnGroupBox``."""
    width = box.style.width
    if width == 'auto' or width.unit == '%':
        width = 0
    else:
        assert width.unit == 'px'
        width = width.value

    return adjust(box, False, width)


def inline_line_widths(context, box, outer, is_line_start, minimum,
                       skip_stack=None):
    current_line = 0
    if skip_stack is None:
        skip = 0
    else:
        skip, skip_stack = skip_stack
    for index, child in box.enumerate_skip(skip):
        if child.is_absolutely_positioned():
            continue  # Skip

        if isinstance(child, boxes.InlineBox):
            lines = list(inline_line_widths(
                context, child, outer, is_line_start, minimum, skip_stack))
            if len(lines) == 1:
                lines[0] = adjust(child, outer, lines[0])
            else:
                lines[0] = adjust(child, outer, lines[0], right=False)
                lines[-1] = adjust(child, outer, lines[-1], left=False)
        elif isinstance(child, boxes.TextBox):
            space_collapse = child.style.white_space in (
                'normal', 'nowrap', 'pre-line')
            if skip_stack is None:
                skip = 0
            else:
                skip, skip_stack = skip_stack
                assert skip_stack is None
            child_text = child.text[(skip or 0):]
            if is_line_start and space_collapse:
                child_text = child_text.lstrip(' ')
            if minimum and child_text == ' ':
                lines = [0, 0]
            else:
                lines = list(text.line_widths(
                    child_text, child.style, context,
                    width=0 if minimum else None))
        else:
            # http://www.w3.org/TR/css3-text/#line-break-details
            # "The line breaking behavior of a replaced element
            #  or other atomic inline is equivalent to that
            #  of the Object Replacement Character (U+FFFC)."
            # http://www.unicode.org/reports/tr14/#DescriptionOfProperties
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
            yield current_line
            if len(lines) > 2:
                for line in lines[1:-1]:
                    yield line
            current_line = lines[-1]
        is_line_start = lines[-1] == 0
        skip_stack = None
    yield current_line


TABLE_CACHE = weakref.WeakKeyDictionary()


def _percentage_contribution(box):
    """Return the percentage contribution of a cell, column or column group.

    http://dbaron.org/css/intrinsic/#pct-contrib

    """
    min_width = (
        box.style.min_width.value if box.style.min_width != 'auto' and
        box.style.min_width.unit == '%' else 0)
    max_width = (
        box.style.max_width.value if box.style.max_width != 'auto' and
        box.style.max_width.unit == '%' else float('inf'))
    width = (
        box.style.width.value if box.style.width != 'auto' and
        box.style.width.unit == '%' else 0)
    return max(min_width, min(width, max_width))


def table_and_columns_preferred_widths(context, box, outer=True):
    """Return content widths for the auto layout table and its columns.

    The tuple returned is
    ``(table_min_content_width, table_max_content_width,
       column_min_content_widths, column_max_content_widths,
       column_intrinsic_percentages, constrainedness,
       total_horizontal_border_spacing, grid)``

    http://dbaron.org/css/intrinsic/

    """
    table = box.get_wrapped_table()
    result = TABLE_CACHE.get(table)
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
    if table.style.border_collapse == 'separate' and grid_width > 0:
        total_horizontal_border_spacing = (
            table.style.border_spacing[0] *
            (1 + len([column for column in zipped_grid if any(column)])))
    else:
        total_horizontal_border_spacing = 0

    if grid_width == 0 or grid_height == 0:
        table.children = []
        min_width = block_min_content_width(context, table, outer=False)
        max_width = block_max_content_width(context, table, outer=False)
        outer_min_width = adjust(
            box, outer=True, width=block_min_content_width(
                context, table, outer=True))
        outer_max_width = adjust(
            box, outer=True, width=block_max_content_width(
                context, table, outer=True))
        result = ([], [], [], [], total_horizontal_border_spacing, [])
        TABLE_CACHE[table] = result = {
            False: (min_width, max_width) + result,
            True: (outer_min_width, outer_max_width) + result,
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

    # Define the intermediate content widths
    min_content_widths = [0 for i in range(grid_width)]
    max_content_widths = [0 for i in range(grid_width)]
    intrinsic_percentages = [0 for i in range(grid_width)]

    # Intermediate content widths for span 1
    for i in range(grid_width):
        for groups in (column_groups, columns):
            if groups[i]:
                min_content_widths[i] = max(
                    min_content_widths[i],
                    min_content_width(context, groups[i]))
                max_content_widths[i] = max(
                    max_content_widths[i],
                    max_content_width(context, groups[i]))
                intrinsic_percentages[i] = max(
                    intrinsic_percentages[i],
                    _percentage_contribution(groups[i]))
        for cell in zipped_grid[i]:
            if cell and cell.colspan == 1:
                min_content_widths[i] = max(
                    min_content_widths[i], min_content_width(context, cell))
                max_content_widths[i] = max(
                    max_content_widths[i], max_content_width(context, cell))
                intrinsic_percentages[i] = max(
                    intrinsic_percentages[i],
                    _percentage_contribution(cell))

    # Intermediate content widths for span N
    for span in range(1, grid_width):
        min_contributions = []
        max_contributions = []
        percentage_contributions = []
        for i in range(grid_width):
            min_contribution = min_content_widths[i]
            max_contribution = max_content_widths[i]
            percentage_contribution = intrinsic_percentages[i]
            for j, cell in enumerate(zipped_grid[i]):
                indexes = [k for k in range(i + 1) if grid[j][k]]
                if not indexes:
                    continue
                origin = max(indexes)
                origin_cell = grid[j][origin]
                if origin_cell.colspan - 1 != span:
                    continue
                cell_slice = slice(origin, origin + origin_cell.colspan)
                baseline_border_spacing = (
                    (origin_cell.colspan - 1) *
                    table.style.border_spacing[0])
                baseline_min_content = sum(min_content_widths[cell_slice])
                baseline_max_content = sum(max_content_widths[cell_slice])
                baseline_percentage = sum(
                    intrinsic_percentages[cell_slice])

                # Cell contributiion to min- and max-content widths
                content_width_diff = (
                    max_content_widths[i] - min_content_widths[i])
                baseline_diff = baseline_max_content - baseline_min_content
                if baseline_diff:
                    diff_ratio = content_width_diff / baseline_diff
                else:
                    diff_ratio = 0

                cell_min_width = max(
                    0,
                    min_content_width(context, grid[j][origin]) -
                    baseline_max_content - baseline_border_spacing)

                cell_max_width = max(
                    0,
                    max_content_width(context, grid[j][origin]) -
                    baseline_max_content - baseline_border_spacing)

                clamped_cell_width = min(
                    cell_min_width,
                    baseline_max_content - baseline_min_content)

                if baseline_max_content:
                    ratio = max_content_widths[i] / baseline_max_content
                else:
                    ratio = 0

                min_contribution = max(
                    min_contribution,
                    min_content_widths[i] +
                    diff_ratio * clamped_cell_width +
                    (1 - ratio) * cell_min_width)

                max_contribution = max(
                    max_contribution,
                    max_content_widths[i] + (1 - ratio) * cell_max_width)

                # Cell contributiion to intrinsic percentage width
                if intrinsic_percentages[i] == 0:
                    diff = max(
                        0,
                        _percentage_contribution(origin_cell) -
                        baseline_percentage)
                    other_columns_contributions = [
                        max_content_widths[j]
                        for j in range(
                            origin, origin + origin_cell.colspan)
                        if intrinsic_percentages[j] == 0]
                    other_columns_contributions_sum = sum(
                        other_columns_contributions)
                    if other_columns_contributions_sum == 0:
                        ratio = 1 / len(other_columns_contributions)
                    else:
                        ratio = (
                            max_content_widths[i] /
                            other_columns_contributions_sum)
                    percentage_contribution = diff * ratio

            min_contributions.append(min_contribution)
            max_contributions.append(max_contribution)
            percentage_contributions.append(percentage_contribution)

        min_content_widths = min_contributions
        max_content_widths = max_contributions
        intrinsic_percentages = percentage_contributions

    intrinsic_percentages = [
        min(percentage, 100 - sum(intrinsic_percentages[:i]))
        for i, percentage in enumerate(intrinsic_percentages)]

    # Calculate the max- and min-content widths of table and columns
    small_percentage_contributions = [
        max_content_widths[i] /
        (intrinsic_percentages[i] / 100. or float('inf'))
        for i in range(grid_width)
        if intrinsic_percentages[i]]
    large_percentage_contribution_numerator = sum(
        max_content_widths[i] for i in range(grid_width)
        if intrinsic_percentages[i] == 0)
    large_percentage_contribution_denominator = (
        (100 - sum(intrinsic_percentages)) / 100.)
    if large_percentage_contribution_denominator == 0:
        if large_percentage_contribution_numerator == 0:
            large_percentage_contribution = 0
        else:
            # "the large percentage contribution of the table [is] an
            # infinitely large number if the numerator is nonzero [and] the
            # denominator of that ratio is 0."
            #
            # http://dbaron.org/css/intrinsic/#autotableintrinsic
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
        total_horizontal_border_spacing + max(
            [sum(max_content_widths), large_percentage_contribution] +
            small_percentage_contributions))

    # Define constrainedness
    constrainedness = [False for i in range(grid_width)]
    for i in range(grid_width):
        if (column_groups[i] and column_groups[i].style.width != 'auto' and
                column_groups[i].style.width.unit != '%'):
            constrainedness[i] = True
            continue
        if (columns[i] and columns[i].style.width != 'auto' and
                columns[i].style.width.unit != '%'):
            constrainedness[i] = True
            continue
        for cell in zipped_grid[i]:
            if (cell and cell.colspan == 1 and cell.style.width != 'auto' and
                    cell.style.width.unit != '%'):
                constrainedness[i] = True
                break

    if table.style.width != 'auto' and table.style.width.unit == 'px':
        # "percentages on the following properties are treated instead as
        # though they were the following: width: auto"
        # http://dbaron.org/css/intrinsic/#outer-intrinsic
        table_min_width = table_max_width = table.style.width.value
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
    TABLE_CACHE[table] = result = {
        False: (table_min_content_width, table_max_content_width) + result,
        True: (
            (table_outer_min_content_width, table_outer_max_content_width) +
            result),
    }
    return result[outer]


def replaced_min_content_width(box, outer=True):
    """Return the min-content width for an ``InlineReplacedBox``."""
    width = box.style.width
    if width == 'auto' or width.unit == '%':
        height = box.style.height
        if height == 'auto' or height.unit == '%':
            height = 'auto'
        else:
            assert height.unit == 'px'
            height = height.value
        image = box.replacement
        iwidth, iheight = image.get_intrinsic_size(
            box.style.image_resolution, box.style.font_size)
        width, _ = default_image_sizing(
            iwidth, iheight, image.intrinsic_ratio, 'auto', height,
            default_width=300, default_height=150)
    else:
        assert width.unit == 'px'
        width = width.value
    return adjust(box, outer, width)


def trailing_whitespace_size(context, box):
    """Return the size of the trailing whitespace of ``box``."""
    from .inlines import split_text_box, split_first_line

    while isinstance(box, (boxes.InlineBox, boxes.LineBox)):
        if not box.children:
            return 0
        box = box.children[-1]
    if not (isinstance(box, boxes.TextBox) and box.text and
            box.style.white_space in ('normal', 'nowrap', 'pre-line')):
        return 0
    stripped_text = box.text.rstrip(' ')
    if box.style.font_size == 0 or len(stripped_text) == len(box.text):
        return 0
    if stripped_text:
        old_box, _, _ = split_text_box(context, box, None, None, 0)
        assert old_box
        stripped_box = box.copy_with_text(stripped_text)
        stripped_box, resume, _ = split_text_box(
            context, stripped_box, None, None, 0)
        assert stripped_box is not None
        assert resume is None
        return old_box.width - stripped_box.width
    else:
        _, _, _, width, _, _ = split_first_line(
            box.text, box.style, context, None, None)
        return width
