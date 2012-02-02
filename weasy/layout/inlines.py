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

from __future__ import division

import cairo

from .markers import image_marker_layout
from .percentages import resolve_percentages, resolve_one_percentage
from ..text import TextFragment
from ..formatting_structure import boxes
from ..css.computed_values import used_line_height


def get_next_linebox(document, linebox, position_y, skip_stack,
                     containing_block, device_size):
    """Return ``(line, resume_at)``.

    ``line`` is a laid-out LineBox with as much content as possible that
    fits in the available width.

    :param linebox: a non-laid-out :class:`LineBox`
    :param position_y: vertical top position of the line box on the page
    :param skip_stack: ``None`` to start at the beginning of ``linebox``,
                       or a ``resume_at`` value to continue just after an
                       already laid-out line.
    :param containing_block: Containing block of the line box:
                             a :class:`BlockContainerBox`
    :param device_size: ``(width, height)`` of the current page.

    """
    position_x = linebox.position_x
    max_x = position_x + containing_block.width
    if skip_stack is None:
        # text-indent only at the start of the first line
        # Other percentages (margins, width, ...) do not apply.
        resolve_one_percentage(linebox, 'text_indent', containing_block.width)
        position_x += linebox.text_indent

    skip_stack = skip_first_whitespace(linebox, skip_stack)
    if skip_stack == 'continue':
        return None, None

    resolve_percentages(linebox, containing_block)
    line, resume_at, preserved_line_break = split_inline_box(
        document, linebox, position_x, max_x, skip_stack, containing_block,
        device_size)

    remove_last_whitespace(document, line)

    bottom, top = inline_box_verticality(line, baseline_y=0)
    last = resume_at is None or preserved_line_break
    offset_x = text_align(document, line, containing_block, last)
    if bottom is None:
        # No children at all
        line.position_y = position_y
        offset_y = 0
        if preserved_line_break:
            # Only the strut.
            line.baseline = line.margin_top
            line.height += line.margin_top + line.margin_bottom
        else:
            line.height = 0
            line.baseline = 0
    else:
        assert top is not None
        line.baseline = -top
        line.position_y = top
        line.height = bottom - top
        offset_y = position_y - top
    line.margin_top = 0
    line.margin_bottom = 0
    if offset_x != 0 or offset_y != 0:
        # This also translates children
        line.translate(offset_x, offset_y)
    return line, resume_at


def skip_first_whitespace(box, skip_stack):
    """Return the ``skip_stack`` to start just after the remove spaces
    at the beginning of the line.

    See http://www.w3.org/TR/CSS21/text.html#white-space-model
    """
    if skip_stack is None:
        index = 0
        next_skip_stack = None
    else:
        index, next_skip_stack = skip_stack

    if isinstance(box, boxes.TextBox):
        assert next_skip_stack is None
        white_space = box.style.white_space
        length = len(box.text)
        if index == length:
            # Starting a the end of the TextBox, no text to see: Continue
            return 'continue'
        if white_space in ('normal', 'nowrap', 'pre-line'):
            while index < length and box.text[index] == ' ':
                index += 1
        return index, None

    if isinstance(box, (boxes.LineBox, boxes.InlineBox)):
        if index == 0 and not box.children:
            return None
        result = skip_first_whitespace(box.children[index], next_skip_stack)
        if result == 'continue':
            index += 1
            if index >= len(box.children):
                return 'continue'
            result = skip_first_whitespace(box.children[index], None)
        return index, result

    assert skip_stack is None, 'unexpected skip inside %s' % box
    return None


def remove_last_whitespace(document, box):
    """Remove in place space characters at the end of a line.

    This also reduces the width of the inline parents of the modified text.

    """
    ancestors = []
    while isinstance(box, (boxes.LineBox, boxes.InlineBox)):
        ancestors.append(box)
        if not box.children:
            return
        box = box.children[-1]
    if not (isinstance(box, boxes.TextBox) and
            box.style.white_space in ('normal', 'nowrap', 'pre-line')):
        return
    new_text = box.text.rstrip(' ')
    if new_text:
        if len(new_text) == len(box.text):
            return
        new_box, resume, _ = split_text_box(document, box, box.width * 2, 0)
        assert new_box is not None
        assert resume is None
        space_width = box.width - new_box.width
        box.width = new_box.width
        box.show_line = new_box.show_line
    else:
        space_width = box.width
        box.width = 0
        box.show_line = lambda x: x  # No-op
    box.text = new_text

    for ancestor in ancestors:
        ancestor.width -= space_width

    # TODO: All tabs (U+0009) are rendered as a horizontal shift that
    # lines up the start edge of the next glyph with the next tab stop.
    # Tab stops occur at points that are multiples of 8 times the width
    # of a space (U+0020) rendered in the block's font from the block's
    # starting content edge.

    # TODO: If spaces (U+0020) or tabs (U+0009) at the end of a line have
    # 'white-space' set to 'pre-wrap', UAs may visually collapse them.


def inline_replaced_box_layout(box, containing_block, device_size):
    """Lay out an inline :class:`boxes.ReplacedBox` ``box``."""
    assert isinstance(box, boxes.ReplacedBox)

    # Compute width:
    # http://www.w3.org/TR/CSS21/visudet.html#inline-replaced-width
    if box.margin_left == 'auto':
        box.margin_left = 0
    if box.margin_right == 'auto':
        box.margin_right = 0
    replaced_box_width(box, device_size)

    # Compute height
    # http://www.w3.org/TR/CSS21/visudet.html#inline-replaced-height
    if box.margin_top == 'auto':
        box.margin_top = 0
    if box.margin_bottom == 'auto':
        box.margin_bottom = 0
    replaced_box_height(box, device_size)


def replaced_box_width(box, device_size):
    """
    Compute and set the used width for replaced boxes (inline- or block-level)
    """
    _surface, intrinsic_width, intrinsic_height = box.replacement
    intrinsic_ratio = intrinsic_width / intrinsic_height

    if box.height == 'auto' and box.width == 'auto':
        if intrinsic_width is not None:
            box.width = intrinsic_width
        elif intrinsic_height is not None and intrinsic_ratio is not None:
            box.width = intrinsic_ratio * intrinsic_height
        elif box.height != 'auto' and intrinsic_ratio is not None:
            box.width = intrinsic_ratio * box.height
        elif intrinsic_ratio is not None:
            pass
            # TODO: Intrinsic ratio only: undefined in CSS 2.1.
            # " It is suggested that, if the containing block's width does not
            #   itself depend on the replaced element's width, then the used
            #   value of 'width' is calculated from the constraint equation
            #   used for block-level, non-replaced elements in normal flow. "

    # Still no value
    if box.width == 'auto':
        if intrinsic_width is not None:
            box.width = intrinsic_width
        else:
            # Then the used value of 'width' becomes 300px. If 300px is too
            # wide to fit the device, UAs should use the width of the largest
            # rectangle that has a 2:1 ratio and fits the device instead.
            device_width, _device_height = device_size
            box.width = min(300, device_width)


def replaced_box_height(box, device_size):
    """
    Compute and set the used height for replaced boxes (inline- or block-level)
    """
    _surface, intrinsic_width, intrinsic_height = box.replacement
    intrinsic_ratio = intrinsic_width / intrinsic_height

    if box.height == 'auto' and box.width == 'auto':
        if intrinsic_height is not None:
            box.height = intrinsic_height
    elif intrinsic_ratio is not None and box.height == 'auto':
        box.height = box.width / intrinsic_ratio
    elif box.height == 'auto' and intrinsic_height is not None:
        box.height = intrinsic_height
    elif box.height == 'auto':
        device_width, _device_height = device_size
        box.height = min(150, device_width / 2)


def atomic_box(box, containing_block, device_size):
    """Compute the width and the height of the atomic ``box``."""
    if isinstance(box, boxes.ReplacedBox):
        if getattr(box, 'is_list_marker', False):
            image_marker_layout(box)
        else:
            inline_replaced_box_layout(box, containing_block, device_size)
    else:
        raise TypeError('Layout for %s not handled yet' % type(box).__name__)
    return box


def split_inline_level(document, box, position_x, max_x, skip_stack,
                       containing_block, device_size):
    """Fit as much content as possible from an inline-level box in a width.

    Return ``(new_box, resume_at)``. ``resume_at`` is ``None`` if all of the
    content fits. Otherwise it can be passed as a ``skip_stack`` parameter
    to resume where we left off.

    ``new_box`` is non-empty (unless the box is empty) and as big as possible
    while being narrower than ``available_width``, if possible (may overflow
    is no split is possible.)

    """
    resolve_percentages(box, containing_block)
    if isinstance(box, boxes.TextBox):
        box.position_x = position_x
        if skip_stack is None:
            skip = 0
        else:
            skip, skip_stack = skip_stack
            skip = skip or 0
            assert skip_stack is None

        new_box, skip, preserved_line_break = split_text_box(
            document, box, max_x - position_x, skip)

        if skip is None:
            resume_at = None
        else:
            resume_at = (skip, None)
    elif isinstance(box, boxes.InlineBox):
        if box.margin_left == 'auto':
            box.margin_left = 0
        if box.margin_right == 'auto':
            box.margin_right = 0
        new_box, resume_at, preserved_line_break = split_inline_box(
            document, box, position_x, max_x, skip_stack, containing_block,
            device_size)
    elif isinstance(box, boxes.AtomicInlineLevelBox):
        new_box = atomic_box(box, containing_block, device_size)
        new_box.position_x = position_x
        new_box.baseline = new_box.margin_height()
        resume_at = None
        preserved_line_break = False
    #else: unexpected box type here
    return new_box, resume_at, preserved_line_break


def split_inline_box(document, box, position_x, max_x, skip_stack,
                     containing_block, device_size):
    """Same behavior as split_inline_level."""
    initial_position_x = position_x
    assert isinstance(box, (boxes.LineBox, boxes.InlineBox))
    left_spacing = (box.padding_left + box.margin_left +
                    box.border_left_width)
    right_spacing = (box.padding_right + box.margin_right +
                     box.border_right_width)
    position_x += left_spacing
    content_box_left = position_x

    children = []
    preserved_line_break = False

    if skip_stack is None:
        skip = 0
    else:
        skip, skip_stack = skip_stack

    for index, child in box.enumerate_skip(skip):
        assert child.is_in_normal_flow(), '"Abnormal" flow not supported yet.'
        new_child, resume_at, preserved = split_inline_level(
            document, child, position_x, max_x, skip_stack,
            containing_block, device_size)
        skip_stack = None
        if preserved:
            preserved_line_break = True

        # TODO: this is non-optimal when last_child is True and
        #   width <= remaining_width < width + right_spacing
        # with
        #   width = part1.margin_width()

        # TODO: on the last child, take care of right_spacing

        if new_child is None:
            # may be None where we would have an empty TextBox
            assert isinstance(child, boxes.TextBox)
        else:
            margin_width = new_child.margin_width()
            new_position_x = position_x + margin_width

            if (new_position_x > max_x and children):
                # too wide, and the inline is non-empty:
                # put child entirely on the next line.
                resume_at = (index, None)
                break
            else:
                position_x = new_position_x
                children.append(new_child)

        if resume_at is not None:
            resume_at = (index, resume_at)
            break
    else:
        resume_at = None

    new_box = box.copy_with_children(children)
    if isinstance(box, boxes.LineBox):
        # Line boxes already have a position_x which may not be the same
        # as content_box_left when text-indent is non-zero.
        # This is important for justified text.
        new_box.width = position_x - new_box.position_x
    else:
        new_box.position_x = initial_position_x
        new_box.width = position_x - content_box_left

    # Create a "strut":
    # http://www.w3.org/TR/CSS21/visudet.html#strut
    # TODO: cache these results for a given set of styles?
    fragment = TextFragment(
        b'', box.style, cairo.Context(document.surface))
    _, _, _, height, baseline, _ = fragment.split_first_line()
    leading = used_line_height(box.style) - height
    half_leading = leading / 2.
    # Set margins to the half leading but also compensate for borders and
    # paddings. We want margin_height() == line_height
    new_box.margin_top = (half_leading - new_box.border_top_width -
                          new_box.padding_bottom)
    new_box.margin_bottom = (half_leading - new_box.border_bottom_width -
                             new_box.padding_bottom)
    # form the top of the content box
    new_box.baseline = baseline
    # form the top of the margin box
    new_box.baseline += half_leading
    new_box.height = height

    if resume_at is not None:
        # There is a line break inside this box.
        box.reset_spacing('left')
        new_box.reset_spacing('right')
    return new_box, resume_at, preserved_line_break


def split_text_box(document, box, available_width, skip):
    """Keep as much text as possible from a TextBox in a limitied width.
    Try not to overflow but always have some text in ``new_box``

    Return ``(new_box, skip)``. ``skip`` is the number of UTF-8 bytes
    to skip form the start of the TextBox for the next line, or ``None``
    if all of the text fits.

    Also break an preserved whitespace.

    """
    assert isinstance(box, boxes.TextBox)
    font_size = box.style.font_size
    text = box.text[skip:]
    if font_size == 0 or not text:
        return None, None, False
    fragment = TextFragment(text, box.style,
        cairo.Context(document.surface), available_width)

    # XXX ``resume_at`` is an index in UTF-8 bytes, not unicode codepoints.
    show_line, length, width, height, baseline, resume_at = \
        fragment.split_first_line()

    # Convert ``length`` and ``resume_at`` from UTF-8 indexes in text
    # to Unicode indexes.
    # No need to encode what’s after resume_at (if set) or length (if
    # resume_at is not set). One code point is one or more byte, so
    # UTF-8 indexes are always bigger or equal to Unicode indexes.
    partial_text = text[:resume_at or length]
    utf8_text = partial_text.encode('utf8')
    new_text = utf8_text[:length].decode('utf8')
    new_length = len(new_text)
    if resume_at is not None:
        between = utf8_text[length:resume_at].decode('utf8')
        resume_at = new_length + len(between)
    length = new_length

    if length > 0:
        box = box.copy_with_text(new_text)
        box.width = width
        box.show_line = show_line
        # "The height of the content area should be based on the font,
        #  but this specification does not specify how."
        # http://www.w3.org/TR/CSS21/visudet.html#inline-non-replaced
        # We trust Pango and use the height of the LayoutLine.
        # It is based on font_size (slightly larger), but I’m not sure how.
        # TODO: investigate this
        box.height = height
        # "only the 'line-height' is used when calculating the height
        #  of the line box."
        # Set margins so that margin_height() == line_height
        leading = used_line_height(box.style) - height
        half_leading = leading / 2.
        box.margin_top = half_leading
        box.margin_bottom = half_leading
        # form the top of the content box
        box.baseline = baseline
        # form the top of the margin box
        box.baseline += box.margin_top + box.border_top_width + box.padding_top
    else:
        box = None

    if resume_at is None:
        preserved_line_break = False
    else:
        preserved_line_break = (length != resume_at)
        if preserved_line_break:
            assert between == '\n', ('Got %r between two lines. '
                'Expected nothing or a preserved line break' % (between,))
        resume_at += skip

    return box, resume_at, preserved_line_break


def inline_box_verticality(box, baseline_y):
    """Handle ``vertical-align`` within an :class:`InlineBox`.

    Place all boxes vertically assuming that the baseline of ``box``
    is at `y = baseline_y`.

    Return ``(max_y, min_y)``, the maximum and minimum vertical position
    of margin boxes.

    """
    max_y = None
    min_y = None
    for child in box.children:
        vertical_align = child.style.vertical_align
        if vertical_align == 'baseline':
            child_baseline_y = baseline_y
        elif vertical_align == 'middle':
            # TODO: find ex from font metrics
            one_ex = box.style.font_size * 0.5
            top = baseline_y - (one_ex + child.margin_height()) / 2.
            child_baseline_y = top + child.baseline
        # TODO: actually implement vertical-align: top and bottom
        elif vertical_align in ('text-top', 'top'):
            # align top with the top of the parent’s content area
            top = (baseline_y - box.baseline + box.margin_top +
                   box.border_top_width + box.padding_top)
            child_baseline_y = top + child.baseline
        elif vertical_align in ('text-bottom', 'bottom'):
            # align bottom with the bottom of the parent’s content area
            bottom = (baseline_y - box.baseline + box.margin_top +
                      box.border_top_width + box.padding_top + box.height)
            child_baseline_y = bottom - child.margin_height() + child.baseline
        else:
            # Numeric value: The child’s baseline is `vertical_align` above
            # (lower y) the parent’s baseline.
            child_baseline_y = baseline_y - vertical_align
        # the child’s `top` is `child.baseline` above (lower y) its baseline.
        top = child_baseline_y - child.baseline
        child.position_y = top
        bottom = top + child.margin_height()
        if min_y is None or top < min_y:
            min_y = top
        if max_y is None or bottom > max_y:
            max_y = bottom
        if isinstance(child, boxes.InlineBox):
            children_max_y, children_min_y = inline_box_verticality(
                child, child_baseline_y)
            if children_max_y is None:
                if (
                    child.margin_width() == 0
                    # Guard against the case where a negative margin
                    # compensates something else.
                    and child.margin_left == 0
                    and child.margin_right == 0
                ):
                    # No content, ignore this box’s line-height.
                    # See http://www.w3.org/TR/CSS21/visuren.html#phantom-line-box
                    child.position_y = child_baseline_y
                    child.height = 0
                    continue
            else:
                assert children_min_y is not None
                if children_min_y < min_y:
                    min_y = children_min_y
                if children_max_y > max_y:
                    max_y = children_max_y
    return max_y, min_y


def text_align(document, line, containing_block, last):
    """Return how much the line should be moved horizontally according to
    the `text-align` property.

    """
    align = line.style.text_align
    if align in ('-weasy-start', '-weasy-end'):
        if (align == '-weasy-start') ^ (line.style.direction == 'rtl'):
            align = 'left'
        else:
            align = 'right'
    if align == 'justify' and last:
        align = 'right' if line.style.direction == 'rtl' else 'left'
    if align == 'left':
        return 0
    offset = containing_block.width - line.width
    if align == 'justify':
        justify_line(document, line, offset)
        return 0
    if align == 'center':
        offset /= 2.
    else:
        assert align == 'right'
    return offset


def justify_line(document, line, extra_width):
    nb_spaces = count_spaces(line)
    if nb_spaces == 0:
        # TODO: what should we do with single-word lines?
        return
    add_word_spacing(document, line, extra_width / nb_spaces, 0)


def count_spaces(box):
    if isinstance(box, boxes.TextBox):
        # TODO: remove trailing spaces correctly
        return box.text.count(' ')
    elif isinstance(box, (boxes.LineBox, boxes.InlineBox)):
        return sum(count_spaces(child) for child in box.children)
    else:
        return 0


def add_word_spacing(document, box, extra_word_spacing, x_advance):
    if isinstance(box, boxes.TextBox):
        box.position_x += x_advance
        box.style.word_spacing += extra_word_spacing
        nb_spaces = count_spaces(box)
        if nb_spaces > 0:
            new_box, resume_at, _ = split_text_box(
                document, box, 1e10, 0)
            assert new_box is not None
            assert resume_at is None
            # XXX new_box.width - box.width is always 0???
            #x_advance +=  new_box.width - box.width
            x_advance += extra_word_spacing * nb_spaces
            box.width = new_box.width
            box.show_line = new_box.show_line
    elif isinstance(box, (boxes.LineBox, boxes.InlineBox)):
        box.position_x += x_advance
        previous_x_advance = x_advance
        for child in box.children:
            x_advance = add_word_spacing(
                document, child, extra_word_spacing, x_advance)
        box.width += x_advance - previous_x_advance
    else:
        # Atomic inline-level box
        box.translate(x_advance, 0)
    return x_advance
