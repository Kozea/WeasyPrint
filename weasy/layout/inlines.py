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
Functions laying out the inline boxes.

"""

import cairo

from .markers import image_marker_layout
from .percentages import resolve_percentages
from ..text import TextFragment
from ..formatting_structure import boxes
from ..css.values import get_single_keyword, get_single_pixel_value


def get_next_linebox(linebox, position_y, skip_stack):
    """Get the ``linebox`` lines until ``page_bottom`` is reached."""
    position_x = linebox.position_x
    containing_block_width = linebox.containing_block_size()[0]
    while 1:
        line, resume_at = layout_next_linebox(
            linebox, containing_block_width, skip_stack)
        white_space_processing(line)
        compute_linebox_dimensions(line)
        compute_linebox_positions(line, position_x, position_y)
        vertical_align_processing(line)
        if is_empty_line(line):
            if resume_at is None:
                return None, None
            skip_stack = resume_at
        else:
            return line, resume_at


def inline_replaced_box_layout(box):
    """Lay out an inline :class:`boxes.ReplacedBox` ``box``."""
    assert isinstance(box, boxes.ReplacedBox)
    resolve_percentages(box)

    # Compute width:
    # http://www.w3.org/TR/CSS21/visudet.html#inline-replaced-width
    if box.margin_left == 'auto':
        box.margin_left = 0
    if box.margin_right == 'auto':
        box.margin_right = 0
    replaced_box_width(box)

    # Compute height
    # http://www.w3.org/TR/CSS21/visudet.html#inline-replaced-height
    if box.margin_top == 'auto':
        box.margin_top = 0
    if box.margin_bottom == 'auto':
        box.margin_bottom = 0
    replaced_box_height(box)


def replaced_box_width(box):
    """
    Compute and set the used width for replaced boxes (inline- or block-level)
    """
    intrinsic_ratio = box.replacement.intrinsic_ratio()
    intrinsic_height = box.replacement.intrinsic_height()
    intrinsic_width = box.replacement.intrinsic_width()

    if box.height == 'auto' and box.width == 'auto':
        if intrinsic_width is not None:
            box.width = intrinsic_width
        elif intrinsic_height is not None and intrinsic_ratio is not None:
            box.width = intrinsic_ratio * intrinsic_height
        elif box.height != 'auto' and intrinsic_ratio is not None:
            box.width = intrinsic_ratio * box.height
        elif intrinsic_ratio is not None:
            pass
            # Intrinsic ratio only: undefined in CSS 2.1.
            # " It is suggested that, if the containing block's width does not
            #   itself depend on the replaced element's width, then the used
            #   value of 'width' is calculated from the constraint equation
            #   used for block-level, non-replaced elements in normal flow. "

    # Still no value
    if box.width == 'auto':
        if intrinsic_width is not None:
            box.width = intrinsic_width
            # Then the used value of 'width' becomes 300px. If 300px is too
            # wide to fit the device, UAs should use the width of the largest
            # rectangle that has a 2:1 ratio and fits the device instead.
        else:
            device_width = box.find_page_ancestor().outer_width
            box.width = min(300, device_width)


def replaced_box_height(box):
    """
    Compute and set the used height for replaced boxes (inline- or block-level)
    """
    intrinsic_ratio = box.replacement.intrinsic_ratio()
    intrinsic_height = box.replacement.intrinsic_height()

    if box.height == 'auto' and box.width == 'auto':
        if intrinsic_height is not None:
            box.height = intrinsic_height
    elif intrinsic_ratio is not None and box.height == 'auto':
        box.height = box.width / intrinsic_ratio
    elif box.height == 'auto' and intrinsic_height is not None:
        box.height = intrinsic_height
    elif box.height == 'auto':
        device_width = box.find_page_ancestor().outer_width
        box.height = min(150, device_width / 2)


def compute_linebox_dimensions(linebox):
    """Compute the width and the height of the ``linebox``."""
    assert isinstance(linebox, boxes.LineBox)
    heights = [0]
    widths = [0]
    for child in linebox.children:
        widths.append(child.width)
        heights.append(child.height)
    linebox.width = sum(widths)
    linebox.height = max(heights)


def compute_inlinebox_dimensions(inlinebox):
    """Compute the width and the height of the ``inlinebox``."""
    resolve_percentages(inlinebox)
    if inlinebox.margin_left == 'auto':
        inlinebox.margin_left = 0
    if inlinebox.margin_right == 'auto':
        inlinebox.margin_right = 0
    # Make sure sum() and max() don’t raise if there is no children.
    widths = [0]
    heights = [0]
    for child in inlinebox.children:
        widths.append(child.margin_width())
        heights.append(child.height)
    inlinebox.width = sum(widths)
    inlinebox.height = max(heights)


def compute_textbox_dimensions(textbox):
    """Compute the width, the height and the baseline of the ``textbox``."""
    assert isinstance(textbox, boxes.TextBox)
    font_size = get_single_pixel_value(textbox.style.font_size)
    if font_size == 0:
        # Pango crashes with font-size: 0 ...
        textbox.width, textbox.height = 0, 0
        textbox.baseline = 0
        textbox.extents = (0, 0, 0, 0)
        textbox.logical_extents = (0, 0, 0, 0)
    else:
        text_fragment = TextFragment(textbox.utf8_text, textbox.style,
            context=cairo.Context(textbox.document.surface))
        textbox.width, textbox.height = text_fragment.get_size()
        textbox.baseline = text_fragment.get_baseline()
        textbox.logical_extents, textbox.extents = text_fragment.get_extents()


def compute_atomicbox_dimensions(box):
    """Compute the width and the height of the atomic ``box``."""
    assert isinstance(box, boxes.AtomicInlineLevelBox)
    if isinstance(box, boxes.ImageMarkerBox):
        image_marker_layout(box)
    if isinstance(box, boxes.ReplacedBox):
        inline_replaced_box_layout(box)
    else:
        raise TypeError('Layout for %s not handled yet' % type(box).__name__)


def compute_linebox_positions(linebox, ref_x, ref_y):
    """Compute the x and y positions of ``linebox``."""
    assert isinstance(linebox, boxes.LineBox)
    # Linebox have no margin/padding/border
    linebox.position_x = ref_x
    linebox.position_y = ref_y
    for child in linebox.children:
        if isinstance(child, boxes.InlineBox):
            compute_inlinebox_positions(child, ref_x, ref_y)
        elif isinstance(child, boxes.AtomicInlineLevelBox):
            compute_atomicbox_positions(child, ref_x, ref_y)
        elif isinstance(child, boxes.TextBox):
            compute_textbox_positions(child, ref_x, ref_y)
        ref_x += child.margin_width()


def compute_inlinebox_positions(inlinebox, ref_x, ref_y):
    """Compute the x and y positions of ``inlinebox``."""
    assert isinstance(inlinebox, boxes.InlineBox)
    inlinebox.position_x = ref_x
    inlinebox.margin_top = 0  # Vertical margins do not apply
    ignored_height = inlinebox.padding_top + inlinebox.border_top_width
    inlinebox.position_y = ref_y - ignored_height
    inline_ref_y = inlinebox.position_y
    inline_ref_x = inlinebox.content_box_x()
    for child in inlinebox.children:
        if isinstance(child, boxes.InlineBox):
            compute_inlinebox_positions(child, inline_ref_x, inline_ref_y)
        elif isinstance(child, boxes.AtomicInlineLevelBox):
            compute_atomicbox_positions(child, inline_ref_x, inline_ref_y)
        elif isinstance(child, boxes.TextBox):
            compute_textbox_positions(child, inline_ref_x, inline_ref_y)
        inline_ref_x += child.margin_width()


def compute_textbox_positions(textbox, ref_x, ref_y):
    """Compute the x and y positions of ``textbox``."""
    assert isinstance(textbox, boxes.TextBox)
    textbox.position_x = ref_x
    textbox.position_y = ref_y


def compute_atomicbox_positions(box, ref_x, ref_y):
    """Compute the x and y positions of atomic ``box``."""
    assert isinstance(box, boxes.AtomicInlineLevelBox)
    box.translate(ref_x, ref_y)


def is_empty_line(linebox):
    """Return whether ``linebox`` has text."""
    # TODO: complete this function
    # XXX what does 'complete' mean?
    if len(linebox.children) == 0:
        return True
    num_textbox = 0
    for child in linebox.descendants():
        if isinstance(child, boxes.TextBox):
            if child.utf8_text.strip(' '):
                return False
            num_textbox += 1
    return num_textbox == len(linebox.children)


def layout_next_linebox(linebox, remaining_width, skip_stack):
    """Same as split_inline_level."""
    assert isinstance(linebox, boxes.LineBox)
    children = []

    if skip_stack is None:
        skip = 0
    else:
        skip, skip_stack = skip_stack

    for index, child in linebox.enumerate_skip(skip):
        new_child, resume_at = split_inline_level(
            child, remaining_width, skip_stack)
        skip_stack = None

        margin_width = new_child.margin_width()
        if margin_width > remaining_width and children:
            # too wide, and the inline is non-empty:
            # put child entirely on the next line.
            resume_at = (index, None)
            break
        else:
            remaining_width -= margin_width
            children.append(new_child)

        if resume_at is not None:
            resume_at = (index, resume_at)
            break
    else:
        resume_at = None

    return linebox.copy_with_children(children), resume_at


def split_inline_level(box, available_width, skip_stack):
    """Fit as much content as possible from an inline-level box in a width.

    Return ``(new_box, resume_at)``. ``resume_at`` is ``None`` if all of the
    content fits. Otherwise it can be passed as a ``skip_stack`` parameter
    to resume where we left off.

    ``new_box`` is non-empty (unless the box is empty) and as big as possible
    while being narrower than ``available_width``, if possible (may overflow
    is no split is possible.)

    """
    if isinstance(box, boxes.TextBox):
        new_box, resume_at = split_text_box(box, available_width, skip_stack)
        compute_textbox_dimensions(new_box)
    elif isinstance(box, boxes.InlineBox):
        resolve_percentages(box)
        if box.margin_left == 'auto':
            box.margin_left = 0
        if box.margin_right == 'auto':
            box.margin_right = 0
        new_box, resume_at = split_inline_box(box, available_width, skip_stack)
        compute_inlinebox_dimensions(new_box)
    elif isinstance(box, boxes.AtomicInlineLevelBox):
        compute_atomicbox_dimensions(box)
        new_box = box
        resume_at = None
    #else: unexpected box type here
    return new_box, resume_at


def split_inline_box(inlinebox, remaining_width, skip_stack):
    """Same behavior as split_inline_level."""
    assert isinstance(inlinebox, boxes.InlineBox)
    resolve_percentages(inlinebox)
    left_spacing = (inlinebox.padding_left + inlinebox.margin_left +
                    inlinebox.border_left_width)
    right_spacing = (inlinebox.padding_right + inlinebox.margin_right +
                     inlinebox.border_right_width)
    remaining_width -= left_spacing

    children = []
    reset_spacing = False

    if skip_stack is None:
        skip = 0
    else:
        skip, skip_stack = skip_stack

    for index, child in inlinebox.enumerate_skip(skip):
        new_child, resume_at = split_inline_level(
            child, remaining_width, skip_stack)
        skip_stack = None

        # TODO: this is non-optimal when last_child is True and
        #   width <= remaining_width < width + right_spacing
        # with
        #   width = part1.margin_width()

        # TODO: on the last child, take care of right_spacing

        margin_width = new_child.margin_width()

        if (margin_width > remaining_width and children):
            # too wide, and the inline is non-empty:
            # put child entirely on the next line.
            resume_at = (index, None)
            break
        else:
            remaining_width -= margin_width
            children.append(new_child)

        if resume_at is not None:
            reset_spacing = True
            resume_at = (index, resume_at)
            break
    else:
        resume_at = None

    new_inlinebox = inlinebox.copy_with_children(children)
    if reset_spacing:
        inlinebox.reset_spacing('left')
        new_inlinebox.reset_spacing('right')

    return new_inlinebox, resume_at


def split_text_box(textbox, available_width, skip):
    """Keep as much text as possible from a TextBox in a limitied width.
    Try not to overflow but always have some text in ``new_textbox``

    Return ``(new_textbox, skip)``. ``skip`` is the number of UTF-8 bytes
    to skip form the start of the TextBox for the next line, or ``None``
    if all of the text fits.

    Also break an preserved whitespace.

    """
    assert isinstance(textbox, boxes.TextBox)
    font_size = get_single_pixel_value(textbox.style.font_size)
    if font_size == 0:
        return textbox, None
    skip = skip or 0
    utf8_text = textbox.utf8_text[skip:]
    fragment = TextFragment(utf8_text, textbox.style,
        cairo.Context(textbox.document.surface), available_width)
    split = fragment.split_first_line()
    if split is None:
        if skip:
            textbox = textbox.copy_with_text(utf8_text)  # with skip
        return textbox, None
    first_end, second_start = split
    new_textbox = textbox.copy_with_text(utf8_text[:first_end])
    return new_textbox, skip + second_start


def white_space_processing(linebox):
    """Remove the first and the last white spaces in ``linebox``."""
    first_textbox = last_textbox = None

    for child in linebox.descendants():
        if isinstance(child, boxes.TextBox):
            if first_textbox is None:
                first_textbox = child
            last_textbox = child

    # If a space (U+0020) at the beginning or the end of a line has
    # 'white-space' set to 'normal', 'nowrap', or 'pre-line', it is removed.
    if first_textbox:
        white_space = get_single_keyword(first_textbox.style.white_space)
        if white_space in ('normal', 'nowrap', 'pre-line'):
            # "left" in "lstrip" actually means "start". It is on the right
            # in rtl text.
            first_textbox.utf8_text = first_textbox.utf8_text.lstrip(b' \t\n')
    if last_textbox:
        # The extents for the last element must ignore the last white space,
        # We use the logical extents instead of ink extents for this box.
        last_textbox.extents = last_textbox.logical_extents
        white_space = get_single_keyword(last_textbox.style.white_space)
        if white_space in ('normal', 'nowrap', 'pre-line'):
            # "right" in "rstrip" actually means "end". It is on the left
            # in rtl text.
            last_textbox.utf8_text = last_textbox.utf8_text.rstrip(b' \t\n')
    # TODO: All tabs (U+0009) are rendered as a horizontal shift that
    # lines up the start edge of the next glyph with the next tab stop.
    # Tab stops occur at points that are multiples of 8 times the width
    # of a space (U+0020) rendered in the block's font from the block's
    # starting content edge.

    # TODO: If spaces (U+0020) or tabs (U+0009) at the end of a line have
    # 'white-space' set to 'pre-wrap', UAs may visually collapse them.


def compute_baseline_positions(box):
    """Compute the relative position of the baseline of ``box``."""
    positions = [0]
    for child in box.children:
        if isinstance(child, boxes.InlineBox):
            if child.children:
                compute_baseline_positions(child)
            else:
                child.baseline = child.height
            positions.append(child.baseline)
        elif isinstance(child, boxes.AtomicInlineLevelBox):
            child.baseline = child.height
            positions.append(child.height)
        elif isinstance(child, boxes.TextBox):
            positions.append(child.baseline)
    box.baseline = max(positions)


def vertical_align_processing(linebox):
    """Compute the real positions of ``linebox``, using vertical-align."""
    compute_baseline_positions(linebox)
    absolute_baseline = linebox.baseline
    #TODO: implement other properties

    for box in linebox.descendants():
        box.position_y += absolute_baseline - box.baseline

    bottom_positions = [
        box.position_y + box.height for box in linebox.children]
    linebox.height = max(bottom_positions or [0]) - linebox.position_y
