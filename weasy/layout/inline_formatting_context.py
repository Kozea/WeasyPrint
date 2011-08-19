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


from ..formatting_structure import boxes
from .percentages import resolve_percentages
from .. import text
from ..css.values import get_single_keyword

TEXT_FRAGMENT = text.TextLineFragment()

def get_new_lineboxes(linebox):
    containing_block_width = linebox.containing_block_size()[0]
    lines = list(breaking_linebox(linebox, containing_block_width))
    position_y = linebox.position_y
    position_x = linebox.position_x
    for line in lines:
        white_space_processing(line)
        compute_linebox_dimensions(line)
        compute_linebox_positions(line,position_x, position_y)
        vertical_align_processing(line)
        if not is_empty_line(line):
            position_y += line.height
            yield line


# Dimensions

def compute_linebox_dimensions(linebox):
    """Compute the height of the linebox """
    assert isinstance(linebox, boxes.LineBox)
    heights = [0]
    widths = [0]
    for child in linebox.children:
        widths.append(child.width)
        heights.append(child.height)
    linebox.width = sum(widths)
    linebox.height = max(heights)


def compute_inlinebox_dimensions(inlinebox):
    resolve_percentages(inlinebox)
    widths = [0]
    heights = [0]
    for child in inlinebox.children:
        widths.append(child.margin_width())
        heights.append(child.height)
    inlinebox.width = sum(widths)
    inlinebox.height = max(heights)


def compute_textbox_dimensions(textbox):
    assert isinstance(textbox, boxes.TextBox)
    TEXT_FRAGMENT.set_textbox(textbox)
    textbox.width, textbox.height = TEXT_FRAGMENT.get_size()


def compute_atomicbox_dimensions(atomicbox):
    assert isinstance(atomicbox, boxes.AtomicInlineLevelBox)
    from . import compute_dimensions
    compute_dimensions(atomicbox)


# Positions

def compute_linebox_positions(linebox,ref_x, ref_y):
    assert isinstance(linebox, boxes.LineBox)
    # Linebox have no margin/padding/border
    linebox.position_x = ref_x
    linebox.position_y = ref_y
    for child in linebox.children:
        if isinstance(child, boxes.InlineBox):
            compute_inlinebox_positions(child,ref_x, ref_y)
        elif isinstance(child, boxes.AtomicInlineLevelBox):
            compute_atomicbox_positions(child, ref_x, ref_y)
        elif isinstance(child, boxes.TextBox):
            compute_textbox_positions(child, ref_x, ref_y)
        ref_x += child.margin_width()


def compute_inlinebox_positions(box,ref_x, ref_y):
    assert isinstance(box, boxes.InlineBox)
    box.position_x = ref_x
    ignored_height = box.padding_top + box.border_top_width + box.margin_top
    box.position_y = ref_y - ignored_height
    inline_ref_y = box.position_y
    inline_ref_x = box.content_box_x()
    for child in box.children:
        if isinstance(child, boxes.InlineBox):
            compute_inlinebox_positions(child, inline_ref_x, inline_ref_y)
        elif isinstance(child, boxes.AtomicInlineLevelBox):
            compute_atomicbox_positions(child, inline_ref_x, inline_ref_y)
        elif isinstance(child, boxes.TextBox):
            compute_textbox_positions(child, inline_ref_x, inline_ref_y)
        inline_ref_x += child.margin_width()

def compute_textbox_positions(box,ref_x, ref_y):
    assert isinstance(box, boxes.TextBox)
    box.position_x = ref_x
    box.position_y = ref_y


def compute_atomicbox_positions(box,ref_x, ref_y):
    assert isinstance(box, boxes.AtomicInlineLevelBox)
    box.translate(ref_x, ref_y)


def is_empty_line(linebox):
    #TODO: complete this function
    if len(linebox.children) == 0:
        return linebox
    text = ""
    len_textbox = 0
    for child in linebox.descendants():
        if isinstance(child, boxes.TextBox):
            len_textbox += 1
            text += child.text.strip(" ")
    return text == "" and len_textbox == len(linebox.children)


def get_new_empty_line(linebox):
    """Return empty copy of `linebox`"""
    new_line = linebox.copy()
    new_line.empty()
    new_line.width = 0
    new_line.height = 0
    return new_line


def breaking_linebox(linebox, allocate_width):
    """
    Cut the `linebox` and return lineboxes that have a width greater than
    allocate_width
    Eg.

    LineBox[
        InlineBox[
            TextBox('Hello.'),
        ],
        InlineBox[
            InlineBox[TextBox('Word :D')],
            TextBox('This is a long long long text'),
        ]
    ]
    is turned into
    [
        LineBox[
            InlineBox[
                TextBox('Hello.'),
            ],
            InlineBox[
                InlineBox[TextBox('Word :D')],
                TextBox('This is a long'),
            ]
        ], LineBox[
            InlineBox[
                TextBox(' long long text'),
            ]
        ]
    ]
    """
    new_line = get_new_empty_line(linebox)
    while linebox.children:
        if not new_line.children:
            width = allocate_width
        child = linebox.children.popleft()
        if isinstance(child, boxes.TextBox):
            part1, part2 = breaking_textbox(child, width)
            compute_textbox_dimensions(part1)
        elif isinstance(child, boxes.InlineBox):
            resolve_percentages(child)
            part1, part2 = breaking_inlinebox(child, width)
            compute_inlinebox_dimensions(part1)
        elif isinstance(child, boxes.AtomicInlineLevelBox):
            part1 = child
            part2 = None
            compute_atomicbox_dimensions(part1)

        if part2:
            linebox.children.appendleft(part2)

        if part1:
            if part1.margin_width() <= width:
                width -= part1.margin_width()
                new_line.add_child(part1)
            else:
                if not new_line.children:
                    new_line.add_child(part1)
                else:
                    linebox.children.appendleft(part1)
                yield new_line
                new_line = get_new_empty_line(linebox)
        else:
            yield new_line
            new_line = get_new_empty_line(linebox)
    yield new_line


def breaking_inlinebox(inlinebox, allocate_width):
    """
    Cut `inlinebox` that sticks out the LineBox if possible

    >>> breaking_inlinebox(inlinebox, allocate_width)
    (first_inlinebox, second_inlinebox)

    Eg.
        InlineBox[
            InlineBox[TextBox('Word :D')],
            TextBox('This is a long long long text'),
        ]
    is turned into
        (
            InlineBox[
                InlineBox[TextBox('Word :D')],
                TextBox('This is a long'),
            ], InlineBox[
                TextBox(' long long text'),
            ]
        )
    """
    left_spacing = inlinebox.padding_left + inlinebox.margin_left + \
                   inlinebox.border_left_width
    right_spacing = inlinebox.padding_right + inlinebox.margin_right + \
                   inlinebox.border_right_width
    allocate_width -= left_spacing
    if allocate_width <= 0:
        return None, inlinebox

    new_inlinebox = inlinebox.copy()
    new_inlinebox.empty()

    while inlinebox.children:
        child = inlinebox.children.popleft()
        # if last child
        last_child = len(inlinebox.children) == 0

        if isinstance(child, boxes.TextBox):
            part1, part2 = breaking_textbox(child, allocate_width)
            compute_textbox_dimensions(part1)
        elif isinstance(child, boxes.InlineBox):
            resolve_percentages(child)
            part1, part2 = breaking_inlinebox(child,allocate_width)
            compute_inlinebox_dimensions(part1)
        elif isinstance(child, boxes.AtomicInlineLevelBox):
            part1 = child
            part2 = None
            compute_atomicbox_dimensions(part1)


        if part2 is not None:
            inlinebox.children.appendleft(part2)

        if part1:
            if part1.margin_width() <= allocate_width:
                if last_child:
                    if (part1.margin_width() + right_spacing) <= allocate_width:
                        allocate_width -= part1.margin_width()
                        new_inlinebox.add_child(part1)
                        break
                    else:
                        inlinebox.children.appendleft(part1)
                        break
                else:
                    allocate_width -= part1.margin_width()
                    new_inlinebox.add_child(part1)
                    if allocate_width == 0:
                        break
            else:
                new_inlinebox.add_child(part1)
                break
        else:
            break

    inlinebox.reset_spacing("left")
    if inlinebox.children:
        new_inlinebox.reset_spacing("right")

    if inlinebox.children:
        return new_inlinebox, inlinebox
    else:
        return new_inlinebox, None


def breaking_textbox(textbox, allocate_width):
    """
    Cut the `textbox` that sticks out the LineBox only if `textbox` can be cut
    by a line break

    >>> breaking_textbox(textbox, allocate_width)
    (first_textbox, second_textbox)

    Eg.
        TextBox('This is a long long long long text')
    is turned into

        (
            TextBox('This is a long long'),
            TextBox(' long long text')
        )
    but
        TextBox('Thisisalonglonglonglongtext')
    is turned into
        (
            TextBox('Thisisalonglonglonglongtext'),
            None
        )
    """
    TEXT_FRAGMENT.set_textbox(textbox)
    TEXT_FRAGMENT.set_width(allocate_width)
    # We create a new TextBox with the first part of the cutting text
    first_tb = textbox.copy()
    first_tb.text = TEXT_FRAGMENT.get_text()
    # And we check the remaining text
    second_tb = None
    if TEXT_FRAGMENT.get_remaining_text() != "":
        second_tb = textbox.copy()
        second_tb.text = TEXT_FRAGMENT.get_remaining_text()
    return first_tb, second_tb


def white_space_processing(linebox):
    """Remove firsts and last white space in the `linebox`"""
    def get_first_textbox(linebox):
        for child in linebox.descendants():
            if isinstance(child, boxes.TextBox):
                return child

    def get_last_textbox(linebox):
        last_child = None
        for child in linebox.descendants():
            if isinstance(child, boxes.TextBox):
                last_child = child
        return last_child
    first_textbox = get_first_textbox(linebox)
    last_textbox = get_last_textbox(linebox)
    # If a space (U+0020) at the beginning or the end of a line has
    # 'white-space' set to 'normal', 'nowrap', or 'pre-line', it is removed.
    if first_textbox:
        white_space = get_single_keyword(first_textbox.style.white_space)
        if white_space in ('normal', 'nowrap', 'pre-line'):
            if get_single_keyword(first_textbox.style.direction) == "rtl":
                first_textbox.text = first_textbox.text.rstrip(' \t')
            else:
                first_textbox.text = first_textbox.text.lstrip(' \t')
    if last_textbox:
        white_space = get_single_keyword(last_textbox.style.white_space)
        if white_space in ('normal', 'nowrap', 'pre-line'):
            if get_single_keyword(last_textbox.style.direction) == "rtl":
                last_textbox.text = last_textbox.text.lstrip(' \t')
            else:
                last_textbox.text = last_textbox.text.rstrip(' \t')

    # TODO: All tabs (U+0009) are rendered as a horizontal shift that
    # lines up the start edge of the next glyph with the next tab stop.
    # Tab stops occur at points that are multiples of 8 times the width
    # of a space (U+0020) rendered in the block's font from the block's
    # starting content edge.

    # TODO: If spaces (U+0020) or tabs (U+0009) at the end of a line have
    # 'white-space' set to 'pre-wrap', UAs may visually collapse them.

def compute_baseline_position(box):
    """Compute the relative position of baseline"""
    max_position = 0
    positions = []
    for child in box.children:
        if isinstance(child, boxes.InlineBox):
            compute_baseline_positions(child)
            positions.append(child.baseline)
        elif isinstance(child, boxes.AtomicInlineLevelBox):
            positions.append(child.height)
        elif isinstance(child, boxes.TextBox):
            positions.append(child.baseline)
    box.baseline = max(positions)

def vertical_align_processing(box):
    top = box.position_y
    bottom = top+box.height
    #TODO: implement this

