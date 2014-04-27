# coding: utf8
"""
    weasyprint.layout.preferred
    ---------------------------

    Preferred and minimum preferred width, aka. the shrink-to-fit algorithm.

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import weakref

from ..formatting_structure import boxes
from .. import text


def shrink_to_fit(context, box, available_width):
    """Return the shrink-to-fit width of ``box``.

    *Warning:* both available_outer_width and the return value are
    for width of the *content area*, not margin area.

    http://www.w3.org/TR/CSS21/visudet.html#float-width

    """
    return min(
        max(
            preferred_minimum_width(context, box, outer=False),
            available_width),
        preferred_width(context, box, outer=False))


def preferred_minimum_width(context, box, outer=True):
    """Return the preferred minimum width for ``box``.

    This is the width by breaking at every line-break opportunity.

    """
    if isinstance(box, boxes.BlockContainerBox):
        if box.is_table_wrapper:
            return table_preferred_minimum_width(context, box, outer)
        else:
            return block_preferred_minimum_width(context, box, outer)
    elif isinstance(box, (boxes.InlineBox, boxes.LineBox)):
        return inline_preferred_minimum_width(
            context, box, outer, is_line_start=True)
    elif isinstance(box, boxes.ReplacedBox):
        return replaced_preferred_width(box, outer)
    else:
        raise TypeError(
            'Preferred minimum width for %s not handled yet' %
            type(box).__name__)


def preferred_width(context, box, outer=True):
    """Return the preferred width for ``box``.

    This is the width by only breaking at forced line breaks.

    """
    if isinstance(box, boxes.BlockContainerBox):
        if box.is_table_wrapper:
            return table_preferred_width(context, box, outer)
        else:
            return block_preferred_width(context, box, outer)
    elif isinstance(box, (boxes.InlineBox, boxes.LineBox)):
        return inline_preferred_width(context, box, outer, is_line_start=True)
    elif isinstance(box, boxes.ReplacedBox):
        return replaced_preferred_width(box, outer)
    else:
        raise TypeError(
            'Preferred width for %s not handled yet' % type(box).__name__)


def _block_preferred_width(context, box, function, outer):
    """Helper to create ``block_preferred_*_width.``"""
    width = box.style.width
    if width == 'auto' or width.unit == '%':
        # "percentages on the following properties are treated instead as
        #  though they were the following: width: auto"
        # http://dbaron.org/css/intrinsic/#outer-intrinsic
        children_widths = [
            function(context, child, outer=True) for child in box.children
            if not child.is_absolutely_positioned()]
        width = max(children_widths) if children_widths else 0
    else:
        assert width.unit == 'px'
        width = width.value

    return adjust(box, outer, width)


def adjust(box, outer, width, left=True, right=True):
    """Add paddings, borders and margins to ``width`` when ``outer`` is set."""
    if not outer:
        return width

    min_width = box.style.min_width
    max_width = box.style.max_width
    min_width = min_width.value if min_width.unit != '%' else 0
    max_width = max_width.value if max_width.unit != '%' else float('inf')

    fixed = max(min_width, min(width, max_width))
    percentages = 0

    for value in (
        (['margin_left', 'padding_left'] if left else []) +
        (['margin_right', 'padding_right'] if right else [])
    ):
        # Padding and border are set on the table, not on the wrapper
        # http://www.w3.org/TR/CSS21/tables.html#model
        # TODO: clean this horrible hack!
        if box.is_table_wrapper and value == 'padding_left':
            box = box.get_wrapped_table()

        style_value = box.style[value]
        if style_value != 'auto':
            if style_value.unit == 'px':
                fixed += style_value.value
            else:
                assert style_value.unit == '%'
                percentages += style_value.value

    if left:
        fixed += box.style.border_left_width
    if right:
        fixed += box.style.border_right_width

    if percentages < 100:
        return fixed / (1 - percentages / 100.)
    else:
        # Pathological case, ignore
        return 0


def block_preferred_minimum_width(context, box, outer=True):
    """Return the preferred minimum width for a ``BlockBox``."""
    return _block_preferred_width(
        context, box, preferred_minimum_width, outer)


def block_preferred_width(context, box, outer=True):
    """Return the preferred width for a ``BlockBox``."""
    return _block_preferred_width(context, box, preferred_width, outer)


def table_cell_preferred_minimum_width(context, box, table,
                                       resolved_table_width, outer=True):
    """Return the preferred minimum width for a ``TableCellBox``."""
    # Try to solve the cell's width if it is a percentage
    width = box.style.width
    if (resolved_table_width and table.width != 'auto' and
            width != 'auto' and width.unit == '%'):
        return width.value / 100. * table.width

    # Else return standard block's preferred minimum width
    return _block_preferred_width(
        context, box, preferred_minimum_width, outer)


def table_cell_preferred_width(context, box, table, resolved_table_width,
                               outer=True):
    """Return the preferred width for a ``TableCellBox``."""
    # Try to solve the cell's width if it is a percentage
    width = box.style.width
    if (resolved_table_width and table.width != 'auto' and
            width != 'auto' and width.unit == '%'):
        return width.value / 100. * table.width

    # Else return standard block's preferred width
    return _block_preferred_width(context, box, preferred_width, outer)


def inline_preferred_minimum_width(context, box, outer=True, skip_stack=None,
                                   first_line=False, is_line_start=False):
    """Return the preferred minimum width for an ``InlineBox``.

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


def inline_preferred_width(context, box, outer=True, is_line_start=False):
    """Return the preferred width for an ``InlineBox``."""
    widths = list(
        inline_line_widths(context, box, outer, is_line_start, minimum=False))
    widths[-1] -= trailing_whitespace_size(context, box)
    return adjust(box, outer, max(widths))


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
            if skip_stack is None:
                skip = 0
            else:
                skip, skip_stack = skip_stack
                assert skip_stack is None
            child_text = child.text[(skip or 0):]
            if is_line_start:
                child_text = child_text.lstrip(' ')
            if minimum and child_text == ' ':
                lines = [0, 0]
            else:
                lines = list(text.line_widths(
                    child_text, child.style, context.enable_hinting,
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
                lines = [0, preferred_width(context, child), 0]
            else:
                lines = [preferred_width(context, child)]
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


def table_and_columns_preferred_widths(context, box, outer=True,
                                       resolved_table_width=False):
    """Return preferred widths for the table and its columns.

    If ``resolved_table_width`` is ``True``, the resolved width (instead of the
    one given in ``box.style``) is used to get the preferred widths.

    The tuple returned is
    ``(table_preferred_minimum_width, table_preferred_width,
    column_preferred_minimum_widths, column_preferred_widths)``

    http://www.w3.org/TR/CSS21/tables.html#auto-table-layout

    """
    table = box.get_wrapped_table()
    result = TABLE_CACHE.get(table)
    if result:
        return result

    if table.style.border_collapse == 'separate':
        border_spacing_x, _ = table.style.border_spacing
    else:
        border_spacing_x = 0

    nb_columns = 0
    if table.column_groups:
        last_column_group = table.column_groups[-1]
        # Column groups always have at least one child column.
        last_column = last_column_group.children[-1]
        # +1 as the grid starts at 0
        nb_columns = last_column.grid_x + 1

    rows = []
    for i, row_group in enumerate(table.children):
        for j, row in enumerate(row_group.children):
            rows.append(row)
            if row.children:
                last_cell = row.children[-1]
                row_grid_width = last_cell.grid_x + last_cell.colspan
                nb_columns = max(nb_columns, row_grid_width)
    nb_rows = len(rows)

    colspan_cells = []
    grid = [[None] * nb_columns for i in range(nb_rows)]
    for i, row in enumerate(rows):
        for cell in row.children:
            if cell.colspan == 1:
                grid[i][cell.grid_x] = cell
            else:
                cell.grid_y = i
                colspan_cells.append(cell)

    # Point #1
    column_preferred_widths = [[0] * nb_rows for i in range(nb_columns)]
    column_preferred_minimum_widths = [
        [0] * nb_rows for i in range(nb_columns)]
    for i, row in enumerate(grid):
        for j, cell in enumerate(row):
            if cell:
                column_preferred_widths[j][i] = \
                    table_cell_preferred_width(
                        context, cell, table, resolved_table_width)
                column_preferred_minimum_widths[j][i] = \
                    table_cell_preferred_minimum_width(
                        context, cell, table, resolved_table_width)

    column_preferred_widths = [
        max(widths) if widths else 0
        for widths in column_preferred_widths]
    column_preferred_minimum_widths = [
        max(widths) if widths else 0
        for widths in column_preferred_minimum_widths]

    # Point #2
    column_groups_widths = []
    column_widths = [None] * nb_columns
    for column_group in table.column_groups:
        assert isinstance(column_group, boxes.TableColumnGroupBox)
        column_groups_widths.append((column_group, column_group.style.width))
        for column in column_group.children:
            assert isinstance(column, boxes.TableColumnBox)
            column_widths[column.grid_x] = column.style.width

    if column_widths:
        for widths in (column_preferred_widths,
                       column_preferred_minimum_widths):
            for i, width in enumerate(widths):
                column_width = column_widths[i]
                if column_width and column_width != 'auto':
                    if column_width.unit == '%' and resolved_table_width:
                        # TODO: If resolved_table_width is false, we should try
                        # to use this percentage as a constraint
                        widths[i] = max(
                            column_width.value / 100. * table.width, widths[i])
                    elif column_width.unit != '%':
                        widths[i] = max(column_width.value, widths[i])

    # Point #3
    for cell in colspan_cells:
        column_slice = slice(cell.grid_x, cell.grid_x + cell.colspan)

        cell_width = (
            table_cell_preferred_width(
                context, cell, table, resolved_table_width) -
            border_spacing_x * (cell.colspan - 1))
        columns_width = sum(column_preferred_widths[column_slice])
        if cell_width > columns_width:
            added_space = (cell_width - columns_width) / cell.colspan
            for i in range(cell.grid_x, cell.grid_x + cell.colspan):
                column_preferred_widths[i] += added_space

        cell_minimum_width = (
            table_cell_preferred_minimum_width(
                context, cell, table, resolved_table_width) -
            border_spacing_x * (cell.colspan - 1))
        columns_minimum_width = sum(
            column_preferred_minimum_widths[column_slice])
        if cell_minimum_width > columns_minimum_width:
            added_space = (
                (cell_minimum_width - columns_minimum_width) / cell.colspan)
            for i in range(cell.grid_x, cell.grid_x + cell.colspan):
                column_preferred_minimum_widths[i] += added_space

    # Point #4
    for column_group, column_group_width in column_groups_widths:
        if (column_group_width and column_group_width != 'auto' and
                (column_group_width.unit != '%' or resolved_table_width)):
            column_indexes = [
                column.grid_x for column in column_group.children]
            columns_width = sum(
                column_preferred_minimum_widths[index]
                for index in column_indexes)
            if column_group_width.unit == '%':
                column_group_width = (
                    column_group_width.value / 100. * table.width)
            else:
                column_group_width = column_group_width.value
            if column_group_width > columns_width:
                added_space = (
                    (column_group_width - columns_width) / len(column_indexes))
                for i in column_indexes:
                    column_preferred_minimum_widths[i] += added_space
                    # The spec seems to say that the colgroup's width is just a
                    # hint for column group's columns minimum width, but if the
                    # sum of the preferred maximum width of the colums is lower
                    # or greater than the colgroup's one, then the columns
                    # don't follow the hint. These lines make the preferred
                    # width equal or greater than the minimum preferred width.
                    if (column_preferred_widths[i] <
                            column_preferred_minimum_widths[i]):
                        column_preferred_widths[i] = \
                            column_preferred_minimum_widths[i]

    total_border_spacing = (nb_columns + 1) * border_spacing_x
    table_preferred_minimum_width = (
        sum(column_preferred_minimum_widths) + total_border_spacing)
    table_preferred_width = sum(column_preferred_widths) + total_border_spacing

    captions = [child for child in box.children
                if child is not table and not child.is_absolutely_positioned()]

    if captions:
        caption_width = max(
            preferred_minimum_width(context, caption) for caption in captions)
    else:
        caption_width = 0

    if table.style.width != 'auto':
        # Take care of the table width
        if resolved_table_width:
            if table.width > table_preferred_minimum_width:
                table_preferred_minimum_width = table.width
        else:
            if (table.style.width.unit != '%' and
                    table.style.width.value > table_preferred_minimum_width):
                table_preferred_minimum_width = table.style.width.value

    if table_preferred_minimum_width < caption_width:
        table_preferred_minimum_width = caption_width

    if table_preferred_minimum_width > table_preferred_width:
        table_preferred_width = table_preferred_minimum_width

    result = (
        table_preferred_minimum_width, table_preferred_width,
        column_preferred_minimum_widths, column_preferred_widths)
    TABLE_CACHE[table] = result
    return result


def table_preferred_minimum_width(context, box, outer=True):
    """Return the preferred minimum width for a ``TableBox``. wrapper"""
    resolved_table_width = box.style.width != 'auto'
    minimum_width, _, _, _ = table_and_columns_preferred_widths(
        context, box, resolved_table_width)
    return adjust(box, outer, minimum_width)


def table_preferred_width(context, box, outer=True):
    """Return the preferred width for a ``TableBox`` wrapper."""
    resolved_table_width = box.style.width != 'auto'
    _, width, _, _ = table_and_columns_preferred_widths(
        context, box, resolved_table_width)
    return adjust(box, outer, width)


def replaced_preferred_width(box, outer=True):
    """Return the preferred minimum width for an ``InlineReplacedBox``."""
    width = box.style.width
    if width == 'auto' or width.unit == '%':
        width, _ = box.replacement.get_intrinsic_size(
            box.style.image_resolution)
        # TODO: handle the images with no intinsic width
        assert width is not None
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
            box.text, box.style, context.enable_hinting,
            None, None)
        return width
