"""
    weasyprint.layout.inline
    ------------------------

    Line breaking and layout for inline-level boxes.

    :copyright: Copyright 2011-2018 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import unicodedata

from ..css import computed_from_cascaded
from ..css.computed_values import ex_ratio, strut_layout
from ..formatting_structure import boxes
from ..text import can_break_text, split_first_line
from .absolute import AbsolutePlaceholder, absolute_layout
from .flex import flex_layout
from .float import avoid_collisions, float_layout
from .min_max import handle_min_max_height, handle_min_max_width
from .percentages import resolve_one_percentage, resolve_percentages
from .preferred import (
    inline_min_content_width, shrink_to_fit, trailing_whitespace_size)
from .replaced import image_marker_layout
from .tables import find_in_flow_baseline, table_wrapper_width


def iter_line_boxes(context, box, position_y, skip_stack, containing_block,
                    device_size, absolute_boxes, fixed_boxes,
                    first_letter_style):
    """Return an iterator of ``(line, resume_at)``.

    ``line`` is a laid-out LineBox with as much content as possible that
    fits in the available width.

    :param box: a non-laid-out :class:`LineBox`
    :param position_y: vertical top position of the line box on the page
    :param skip_stack: ``None`` to start at the beginning of ``linebox``,
                       or a ``resume_at`` value to continue just after an
                       already laid-out line.
    :param containing_block: Containing block of the line box:
                             a :class:`BlockContainerBox`
    :param device_size: ``(width, height)`` of the current page.

    """
    resolve_percentages(box, containing_block)
    if skip_stack is None:
        # TODO: wrong, see https://github.com/Kozea/WeasyPrint/issues/679
        resolve_one_percentage(box, 'text_indent', containing_block.width)
    else:
        box.text_indent = 0
    while 1:
        line, resume_at = get_next_linebox(
            context, box, position_y, skip_stack, containing_block,
            device_size, absolute_boxes, fixed_boxes, first_letter_style)
        if line:
            position_y = line.position_y + line.height
        if line is None:
            return
        yield line, resume_at
        if resume_at is None:
            return
        skip_stack = resume_at
        box.text_indent = 0
        first_letter_style = None


def get_next_linebox(context, linebox, position_y, skip_stack,
                     containing_block, device_size, absolute_boxes,
                     fixed_boxes, first_letter_style):
    """Return ``(line, resume_at)``."""
    skip_stack = skip_first_whitespace(linebox, skip_stack)
    if skip_stack == 'continue':
        return None, None

    skip_stack = first_letter_to_box(linebox, skip_stack, first_letter_style)

    linebox.width = inline_min_content_width(
        context, linebox, skip_stack=skip_stack, first_line=True)

    linebox.height, _ = strut_layout(linebox.style, context)
    linebox.position_y = position_y
    position_x, position_y, available_width = avoid_collisions(
        context, linebox, containing_block, outer=False)
    candidate_height = linebox.height

    excluded_shapes = context.excluded_shapes[:]

    while 1:
        linebox.position_x = position_x
        linebox.position_y = position_y
        max_x = position_x + available_width
        position_x += linebox.text_indent

        line_placeholders = []
        line_absolutes = []
        line_fixed = []
        waiting_floats = []

        (line, resume_at, preserved_line_break, first_letter,
         last_letter, float_width) = split_inline_box(
             context, linebox, position_x, max_x, skip_stack, containing_block,
             device_size, line_absolutes, line_fixed, line_placeholders,
             waiting_floats, line_children=[])

        if is_phantom_linebox(line) and not preserved_line_break:
            line.height = 0
            break

        remove_last_whitespace(context, line)

        new_position_x, _, new_available_width = avoid_collisions(
            context, linebox, containing_block, outer=False)
        # TODO: handle rtl
        new_available_width -= float_width['right']
        alignment_available_width = (
            new_available_width + new_position_x - linebox.position_x)
        offset_x = text_align(
            context, line, alignment_available_width,
            last=(resume_at is None or preserved_line_break))

        bottom, top = line_box_verticality(line)
        assert top is not None
        assert bottom is not None
        line.baseline = -top
        line.position_y = top
        line.height = bottom - top
        offset_y = position_y - top
        line.margin_top = 0
        line.margin_bottom = 0

        line.translate(offset_x, offset_y)
        # Avoid floating point errors, as position_y - top + top != position_y
        # Removing this line breaks the position == linebox.position test below
        # See https://github.com/Kozea/WeasyPrint/issues/583
        line.position_y = position_y

        if line.height <= candidate_height:
            break
        candidate_height = line.height

        new_excluded_shapes = context.excluded_shapes
        context.excluded_shapes = excluded_shapes
        position_x, position_y, available_width = avoid_collisions(
            context, line, containing_block, outer=False)
        if (position_x, position_y) == (
                linebox.position_x, linebox.position_y):
            context.excluded_shapes = new_excluded_shapes
            break

    absolute_boxes.extend(line_absolutes)
    fixed_boxes.extend(line_fixed)

    for placeholder in line_placeholders:
        if placeholder.style['_weasy_specified_display'].startswith('inline'):
            # Inline-level static position:
            placeholder.translate(0, position_y - placeholder.position_y)
        else:
            # Block-level static position: at the start of the next line
            placeholder.translate(
                line.position_x - placeholder.position_x,
                position_y + line.height - placeholder.position_y)

    float_children = []
    waiting_floats_y = line.position_y + line.height
    for waiting_float in waiting_floats:
        waiting_float.position_y = waiting_floats_y
        waiting_float = float_layout(
            context, waiting_float, containing_block, device_size,
            absolute_boxes, fixed_boxes)
        float_children.append(waiting_float)
    if float_children:
        line.children += tuple(float_children)

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
        white_space = box.style['white_space']
        length = len(box.text)
        if index == length:
            # Starting a the end of the TextBox, no text to see: Continue
            return 'continue'
        if white_space in ('normal', 'nowrap', 'pre-line'):
            while index < length and box.text[index] == ' ':
                index += 1
        return (index, None) if index else None

    if isinstance(box, (boxes.LineBox, boxes.InlineBox)):
        if index == 0 and not box.children:
            return None
        result = skip_first_whitespace(box.children[index], next_skip_stack)
        if result == 'continue':
            index += 1
            if index >= len(box.children):
                return 'continue'
            result = skip_first_whitespace(box.children[index], None)
        return (index, result) if (index or result) else None

    assert skip_stack is None, 'unexpected skip inside %s' % box
    return None


def remove_last_whitespace(context, box):
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
            box.style['white_space'] in ('normal', 'nowrap', 'pre-line')):
        return
    new_text = box.text.rstrip(' ')
    if new_text:
        if len(new_text) == len(box.text):
            return
        box.text = new_text
        new_box, resume, _ = split_text_box(context, box, None, 0)
        assert new_box is not None
        assert resume is None
        space_width = box.width - new_box.width
        box.width = new_box.width
    else:
        space_width = box.width
        box.width = 0
        box.text = ''

    for ancestor in ancestors:
        ancestor.width -= space_width

    # TODO: All tabs (U+0009) are rendered as a horizontal shift that
    # lines up the start edge of the next glyph with the next tab stop.
    # Tab stops occur at points that are multiples of 8 times the width
    # of a space (U+0020) rendered in the block's font from the block's
    # starting content edge.

    # TODO: If spaces (U+0020) or tabs (U+0009) at the end of a line have
    # 'white-space' set to 'pre-wrap', UAs may visually collapse them.


def first_letter_to_box(box, skip_stack, first_letter_style):
    """Create a box for the ::first-letter selector."""
    if first_letter_style and box.children:
        first_letter = ''
        child = box.children[0]
        if isinstance(child, boxes.TextBox):
            letter_style = computed_from_cascaded(
                cascaded={}, parent_style=first_letter_style, element=None)
            if child.element_tag.endswith('::first-letter'):
                letter_box = boxes.InlineBox(
                    '%s::first-letter' % box.element_tag, letter_style,
                    [child])
                box.children = (
                    (letter_box,) + tuple(box.children[1:]))
            elif child.text:
                character_found = False
                if skip_stack:
                    child_skip_stack = skip_stack[1]
                    if child_skip_stack:
                        index = child_skip_stack[0]
                        child.text = child.text[index:]
                        skip_stack = None
                while child.text:
                    next_letter = child.text[0]
                    category = unicodedata.category(next_letter)
                    if category not in ('Ps', 'Pe', 'Pi', 'Pf', 'Po'):
                        if character_found:
                            break
                        character_found = True
                    first_letter += next_letter
                    child.text = child.text[1:]
                if first_letter.lstrip('\n'):
                    # "This type of initial letter is similar to an
                    # inline-level element if its 'float' property is 'none',
                    # otherwise it is similar to a floated element."
                    if first_letter_style['float'] == 'none':
                        letter_box = boxes.InlineBox(
                            '%s::first-letter' % box.element_tag,
                            first_letter_style, [])
                        text_box = boxes.TextBox(
                            '%s::first-letter' % box.element_tag, letter_style,
                            first_letter)
                        letter_box.children = (text_box,)
                        box.children = (letter_box,) + tuple(box.children)
                    else:
                        letter_box = boxes.BlockBox(
                            '%s::first-letter' % box.element_tag,
                            first_letter_style, [])
                        letter_box.first_letter_style = None
                        line_box = boxes.LineBox(
                            '%s::first-letter' % box.element_tag, letter_style,
                            [])
                        letter_box.children = (line_box,)
                        text_box = boxes.TextBox(
                            '%s::first-letter' % box.element_tag, letter_style,
                            first_letter)
                        line_box.children = (text_box,)
                        box.children = (letter_box,) + tuple(box.children)
                    if skip_stack and child_skip_stack:
                        skip_stack = (skip_stack[0], (
                            child_skip_stack[0] + 1, child_skip_stack[1]))
        elif isinstance(child, boxes.ParentBox):
            if skip_stack:
                child_skip_stack = skip_stack[1]
            else:
                child_skip_stack = None
            child_skip_stack = first_letter_to_box(
                child, child_skip_stack, first_letter_style)
            if skip_stack:
                skip_stack = (skip_stack[0], child_skip_stack)
    return skip_stack


@handle_min_max_width
def replaced_box_width(box, device_size):
    """
    Compute and set the used width for replaced boxes (inline- or block-level)
    """
    intrinsic_width, intrinsic_height = box.replacement.get_intrinsic_size(
        box.style['image_resolution'], box.style['font_size'])

    # This algorithm simply follows the different points of the specification:
    # http://www.w3.org/TR/CSS21/visudet.html#inline-replaced-width
    if box.height == 'auto' and box.width == 'auto':
        if intrinsic_width is not None:
            # Point #1
            box.width = intrinsic_width
        elif box.replacement.intrinsic_ratio is not None:
            if intrinsic_height is not None:
                # Point #2 first part
                box.width = intrinsic_height * box.replacement.intrinsic_ratio
            else:
                # Point #3
                # " It is suggested that, if the containing block's width does
                #   not itself depend on the replaced element's width, then the
                #   used value of 'width' is calculated from the constraint
                #   equation used for block-level, non-replaced elements in
                #   normal flow. "
                # Whaaaaat? Let's not do this and use a value that may work
                # well at least with inline blocks.
                box.width = (
                    box.style['font_size'] * box.replacement.intrinsic_ratio)

    if box.width == 'auto':
        if box.replacement.intrinsic_ratio is not None:
            # Point #2 second part
            box.width = box.height * box.replacement.intrinsic_ratio
        elif intrinsic_width is not None:
            # Point #4
            box.width = intrinsic_width
        else:
            # Point #5
            device_width, _device_height = device_size
            box.width = min(300, device_width)


@handle_min_max_height
def replaced_box_height(box, device_size):
    """
    Compute and set the used height for replaced boxes (inline- or block-level)
    """
    # http://www.w3.org/TR/CSS21/visudet.html#inline-replaced-height
    intrinsic_width, intrinsic_height = box.replacement.get_intrinsic_size(
        box.style['image_resolution'], box.style['font_size'])
    intrinsic_ratio = box.replacement.intrinsic_ratio

    # Test 'auto' on the computed width, not the used width
    if box.height == 'auto' and box.width == 'auto':
        box.height = intrinsic_height
    elif box.height == 'auto' and intrinsic_ratio:
        box.height = box.width / intrinsic_ratio

    if (box.height == 'auto' and box.width == 'auto' and
            intrinsic_height is not None):
        box.height = intrinsic_height
    elif intrinsic_ratio is not None and box.height == 'auto':
        box.height = box.width / intrinsic_ratio
    elif box.height == 'auto' and intrinsic_height is not None:
        box.height = intrinsic_height
    elif box.height == 'auto':
        device_width, _device_height = device_size
        box.height = min(150, device_width / 2)


def inline_replaced_box_layout(box, device_size):
    """Lay out an inline :class:`boxes.ReplacedBox` ``box``."""
    for side in ['top', 'right', 'bottom', 'left']:
        if getattr(box, 'margin_' + side) == 'auto':
            setattr(box, 'margin_' + side, 0)
    inline_replaced_box_width_height(box, device_size)


def inline_replaced_box_width_height(box, device_size):
    if box.style['width'] == 'auto' and box.style['height'] == 'auto':
        replaced_box_width.without_min_max(box, device_size)
        replaced_box_height.without_min_max(box, device_size)
        min_max_auto_replaced(box)
    else:
        replaced_box_width(box, device_size)
        replaced_box_height(box, device_size)


def min_max_auto_replaced(box):
    """Resolve {min,max}-{width,height} constraints on replaced elements
    that have 'auto' width and heights.
    """
    width = box.width
    height = box.height
    min_width = box.min_width
    min_height = box.min_height
    max_width = max(min_width, box.max_width)
    max_height = max(min_height, box.max_height)

    # (violation_width, violation_height)
    violations = (
        'min' if width < min_width else 'max' if width > max_width else '',
        'min' if height < min_height else 'max' if height > max_height else '')

    # Work around divisions by zero. These are pathological cases anyway.
    # TODO: is there a cleaner way?
    if width == 0:
        width = 1e-6
    if height == 0:
        height = 1e-6

    # ('', ''): nothing to do
    if violations == ('max', ''):
        box.width = max_width
        box.height = max(max_width * height / width, min_height)
    elif violations == ('min', ''):
        box.width = min_width
        box.height = min(min_width * height / width, max_height)
    elif violations == ('', 'max'):
        box.width = max(max_height * width / height, min_width)
        box.height = max_height
    elif violations == ('', 'min'):
        box.width = min(min_height * width / height, max_width)
        box.height = min_height
    elif violations == ('max', 'max'):
        if max_width / width <= max_height / height:
            box.width = max_width
            box.height = max(min_height, max_width * height / width)
        else:
            box.width = max(min_width, max_height * width / height)
            box.height = max_height
    elif violations == ('min', 'min'):
        if min_width / width <= min_height / height:
            box.width = min(max_width, min_height * width / height)
            box.height = min_height
        else:
            box.width = min_width
            box.height = min(max_height, min_width * height / width)
    elif violations == ('min', 'max'):
        box.width = min_width
        box.height = max_height
    elif violations == ('max', 'min'):
        box.width = max_width
        box.height = min_height


def atomic_box(context, box, position_x, skip_stack, containing_block,
               device_size, absolute_boxes, fixed_boxes):
    """Compute the width and the height of the atomic ``box``."""
    if isinstance(box, boxes.ReplacedBox):
        if getattr(box, 'is_list_marker', False):
            image_marker_layout(box)
        else:
            inline_replaced_box_layout(box, device_size)
        box.baseline = box.margin_height()
    elif isinstance(box, boxes.InlineBlockBox):
        if box.is_table_wrapper:
            table_wrapper_width(
                context, box,
                (containing_block.width, containing_block.height))
        box = inline_block_box_layout(
            context, box, position_x, skip_stack, containing_block,
            device_size, absolute_boxes, fixed_boxes)
    else:  # pragma: no cover
        raise TypeError('Layout for %s not handled yet' % type(box).__name__)
    return box


def inline_block_box_layout(context, box, position_x, skip_stack,
                            containing_block, device_size, absolute_boxes,
                            fixed_boxes):
    # Avoid a circular import
    from .blocks import block_container_layout

    resolve_percentages(box, containing_block)

    # http://www.w3.org/TR/CSS21/visudet.html#inlineblock-width
    if box.margin_left == 'auto':
        box.margin_left = 0
    if box.margin_right == 'auto':
        box.margin_right = 0
    # http://www.w3.org/TR/CSS21/visudet.html#block-root-margin
    if box.margin_top == 'auto':
        box.margin_top = 0
    if box.margin_bottom == 'auto':
        box.margin_bottom = 0

    inline_block_width(box, context, containing_block)

    box.position_x = position_x
    box.position_y = 0
    box, _, _, _, _ = block_container_layout(
        context, box, max_position_y=float('inf'), skip_stack=skip_stack,
        device_size=device_size, page_is_empty=True,
        absolute_boxes=absolute_boxes, fixed_boxes=fixed_boxes)
    box.baseline = inline_block_baseline(box)
    return box


def inline_block_baseline(box):
    """
    Return the y position of the baseline for an inline block
    from the top of its margin box.

    http://www.w3.org/TR/CSS21/visudet.html#propdef-vertical-align

    """
    if box.style['overflow'] == 'visible':
        result = find_in_flow_baseline(box, last=True)
        if result:
            return result
    return box.position_y + box.margin_height()


@handle_min_max_width
def inline_block_width(box, context, containing_block):
    if box.width == 'auto':
        box.width = shrink_to_fit(context, box, containing_block.width)


def split_inline_level(context, box, position_x, max_x, skip_stack,
                       containing_block, device_size, absolute_boxes,
                       fixed_boxes, line_placeholders, waiting_floats,
                       line_children):
    """Fit as much content as possible from an inline-level box in a width.

    Return ``(new_box, resume_at, preserved_line_break, first_letter,
    last_letter)``. ``resume_at`` is ``None`` if all of the content
    fits. Otherwise it can be passed as a ``skip_stack`` parameter to resume
    where we left off.

    ``new_box`` is non-empty (unless the box is empty) and as big as possible
    while being narrower than ``available_width``, if possible (may overflow
    is no split is possible.)

    """
    resolve_percentages(box, containing_block)
    float_widths = {'left': 0, 'right': 0}
    if isinstance(box, boxes.TextBox):
        box.position_x = position_x
        if skip_stack is None:
            skip = 0
        else:
            skip, skip_stack = skip_stack
            skip = skip or 0
            assert skip_stack is None

        new_box, skip, preserved_line_break = split_text_box(
            context, box, max_x - position_x, skip)

        if skip is None:
            resume_at = None
        else:
            resume_at = (skip, None)
        if box.text:
            first_letter = box.text[0]
            if skip is None:
                last_letter = box.text[-1]
            else:
                last_letter = box.text[skip - 1]
        else:
            first_letter = last_letter = None
    elif isinstance(box, boxes.InlineBox):
        if box.margin_left == 'auto':
            box.margin_left = 0
        if box.margin_right == 'auto':
            box.margin_right = 0
        (new_box, resume_at, preserved_line_break, first_letter,
         last_letter, float_widths) = split_inline_box(
            context, box, position_x, max_x, skip_stack, containing_block,
            device_size, absolute_boxes, fixed_boxes, line_placeholders,
            waiting_floats, line_children)
    elif isinstance(box, boxes.AtomicInlineLevelBox):
        new_box = atomic_box(
            context, box, position_x, skip_stack, containing_block,
            device_size, absolute_boxes, fixed_boxes)
        new_box.position_x = position_x
        resume_at = None
        preserved_line_break = False
        # See https://www.w3.org/TR/css-text-3/#line-breaking
        # Atomic inlines behave like ideographic characters.
        first_letter = '\u2e80'
        last_letter = '\u2e80'
    elif isinstance(box, boxes.InlineFlexBox):
        box.position_x = position_x
        box.position_y = 0
        for side in ['top', 'right', 'bottom', 'left']:
            if getattr(box, 'margin_' + side) == 'auto':
                setattr(box, 'margin_' + side, 0)
        new_box, resume_at, _, _, _ = flex_layout(
            context, box, float('inf'), skip_stack, containing_block,
            device_size, False, absolute_boxes, fixed_boxes)
        preserved_line_break = False
        first_letter = '\u2e80'
        last_letter = '\u2e80'
    else:  # pragma: no cover
        raise TypeError('Layout for %s not handled yet' % type(box).__name__)
    return (
        new_box, resume_at, preserved_line_break, first_letter, last_letter,
        float_widths)


def split_inline_box(context, box, position_x, max_x, skip_stack,
                     containing_block, device_size, absolute_boxes,
                     fixed_boxes, line_placeholders, waiting_floats,
                     line_children):
    """Same behavior as split_inline_level."""

    # In some cases (shrink-to-fit result being the preferred width)
    # max_x is coming from Pango itself,
    # but floating point errors have accumulated:
    #   width2 = (width + X) - X   # in some cases, width2 < width
    # Increase the value a bit to compensate and not introduce
    # an unexpected line break. The 1e-9 value comes from PEP 485.
    max_x *= 1 + 1e-9

    is_start = skip_stack is None
    initial_position_x = position_x
    initial_skip_stack = skip_stack
    assert isinstance(box, (boxes.LineBox, boxes.InlineBox))
    left_spacing = (box.padding_left + box.margin_left +
                    box.border_left_width)
    right_spacing = (box.padding_right + box.margin_right +
                     box.border_right_width)
    content_box_left = position_x

    children = []
    waiting_children = []
    preserved_line_break = False
    first_letter = last_letter = None
    float_widths = {'left': 0, 'right': 0}
    float_resume_at = 0

    if box.style['position'] == 'relative':
        absolute_boxes = []

    if is_start:
        skip = 0
    else:
        skip, skip_stack = skip_stack

    box_children = list(box.enumerate_skip(skip))
    for i, (index, child) in enumerate(box_children):
        child.position_y = box.position_y
        if child.is_absolutely_positioned():
            child.position_x = position_x
            placeholder = AbsolutePlaceholder(child)
            line_placeholders.append(placeholder)
            waiting_children.append((index, placeholder))
            if child.style['position'] == 'absolute':
                absolute_boxes.append(placeholder)
            else:
                fixed_boxes.append(placeholder)
            continue
        elif child.is_floated():
            child.position_x = position_x
            float_width = shrink_to_fit(
                context, child, containing_block.width)

            # To retrieve the real available space for floats, we must remove
            # the trailing whitespaces from the line
            non_floating_children = [
                child_ for _, child_ in (children + waiting_children)
                if not child_.is_floated()]
            if non_floating_children:
                float_width -= trailing_whitespace_size(
                    context, non_floating_children[-1])

            if float_width > max_x - position_x or waiting_floats:
                # TODO: the absolute and fixed boxes in the floats must be
                # added here, and not in iter_line_boxes
                waiting_floats.append(child)
            else:
                child = float_layout(
                    context, child, containing_block, device_size,
                    absolute_boxes, fixed_boxes)
                waiting_children.append((index, child))

                # Translate previous line children
                dx = max(child.margin_width(), 0)
                float_widths[child.style['float']] += dx
                if child.style['float'] == 'left':
                    if isinstance(box, boxes.LineBox):
                        # The parent is the line, update the current position
                        # for the next child. When the parent is not the line
                        # (it is an inline block), the current position of the
                        # line is updated by the box itself (see next
                        # split_inline_level call).
                        position_x += dx
                elif child.style['float'] == 'right':
                    # Update the maximum x position for the next children
                    max_x -= dx
                for _, old_child in line_children:
                    if not old_child.is_in_normal_flow():
                        continue
                    if ((child.style['float'] == 'left' and
                            box.style['direction'] == 'ltr') or
                        (child.style['float'] == 'right' and
                            box.style['direction'] == 'rtl')):
                        old_child.translate(dx=dx)
            float_resume_at = index + 1
            continue

        last_child = (i == len(box_children) - 1)
        available_width = max_x
        child_waiting_floats = []
        new_child, resume_at, preserved, first, last, new_float_widths = (
            split_inline_level(
                context, child, position_x, available_width, skip_stack,
                containing_block, device_size, absolute_boxes, fixed_boxes,
                line_placeholders, child_waiting_floats, line_children))
        if last_child and right_spacing and resume_at is None:
            # TODO: we should take care of children added into absolute_boxes,
            # fixed_boxes and other lists.
            if box.style['direction'] == 'rtl':
                available_width -= left_spacing
            else:
                available_width -= right_spacing
            new_child, resume_at, preserved, first, last, new_float_widths = (
                split_inline_level(
                    context, child, position_x, available_width, skip_stack,
                    containing_block, device_size, absolute_boxes, fixed_boxes,
                    line_placeholders, child_waiting_floats, line_children))

        if box.style['direction'] == 'rtl':
            max_x -= new_float_widths['left']
        else:
            max_x -= new_float_widths['right']

        skip_stack = None
        if preserved:
            preserved_line_break = True

        can_break = None
        if last_letter is True:
            last_letter = ' '
        elif last_letter is False:
            last_letter = ' '  # no-break space
        elif box.style['white_space'] in ('pre', 'nowrap'):
            can_break = False
        if can_break is None:
            if None in (last_letter, first):
                can_break = False
            else:
                can_break = can_break_text(
                    last_letter + first, child.style['lang'])

        if can_break:
            children.extend(waiting_children)
            waiting_children = []

        if first_letter is None:
            first_letter = first
        if child.trailing_collapsible_space:
            last_letter = True
        else:
            last_letter = last

        if new_child is None:
            # May be None where we have an empty TextBox.
            assert isinstance(child, boxes.TextBox)
        else:
            if isinstance(box, boxes.LineBox):
                line_children.append((index, new_child))
            # TODO: we should try to find a better condition here.
            trailing_whitespace = (
                isinstance(new_child, boxes.TextBox) and
                not new_child.text.strip())

            margin_width = new_child.margin_width()
            new_position_x = new_child.position_x + margin_width

            if new_position_x > max_x and not trailing_whitespace:
                if waiting_children:
                    # Too wide, let's try to cut inside waiting children,
                    # starting from the end.
                    # TODO: we should take care of children added into
                    # absolute_boxes, fixed_boxes and other lists.
                    waiting_children_copy = waiting_children[:]
                    break_found = False
                    while waiting_children_copy:
                        child_index, child = waiting_children_copy.pop()
                        # TODO: should we also accept relative children?
                        if (child.is_in_normal_flow() and
                                can_break_inside(child)):
                            # We break the waiting child at its last possible
                            # breaking point.
                            # TODO: The dirty solution chosen here is to
                            # decrease the actual size by 1 and render the
                            # waiting child again with this constraint. We may
                            # find a better way.
                            max_x = child.position_x + child.margin_width() - 1
                            child_new_child, child_resume_at, _, _, _, _ = (
                                split_inline_level(
                                    context, child, child.position_x, max_x,
                                    None, box, device_size,
                                    absolute_boxes, fixed_boxes,
                                    line_placeholders, waiting_floats,
                                    line_children))

                            # As PangoLayout and PangoLogAttr don't always
                            # agree, we have to rely on the actual split to
                            # know whether the child was broken.
                            # https://github.com/Kozea/WeasyPrint/issues/614
                            break_found = child_resume_at is not None
                            if child_resume_at is None:
                                # PangoLayout decided not to break the child
                                child_resume_at = (0, None)
                            # TODO: use this when Pango is always 1.40.13+:
                            # break_found = True

                            children = children + waiting_children_copy
                            if child_new_child is None:
                                # May be None where we have an empty TextBox.
                                assert isinstance(child, boxes.TextBox)
                            else:
                                children += [(child_index, child_new_child)]

                            # We have to check whether the child we're breaking
                            # is the one broken by the initial skip stack.
                            broken_child = bool(
                                initial_skip_stack and
                                initial_skip_stack[0] == child_index and
                                initial_skip_stack[1])
                            if broken_child:
                                # As this child has already been broken
                                # following the original skip stack, we have to
                                # add the original skip stack to the partial
                                # skip stack we get after the new rendering.

                                # We have to do:
                                # child_resume_at += initial_skip_stack[1]
                                # but adding skip stacks is a bit complicated
                                current_skip_stack = initial_skip_stack[1]
                                current_resume_at = child_resume_at
                                stack = []
                                while current_skip_stack and current_resume_at:
                                    skip_stack, current_skip_stack = (
                                        current_skip_stack)
                                    resume_at, current_resume_at = (
                                        current_resume_at)
                                    stack.append(skip_stack + resume_at)
                                child_resume_at = (
                                    current_skip_stack or current_resume_at)
                                while stack:
                                    child_resume_at = (
                                        stack.pop(), child_resume_at)

                            resume_at = (child_index, child_resume_at)
                            break
                    if break_found:
                        break
                if children:
                    # Too wide, can't break waiting children and the inline is
                    # non-empty: put child entirely on the next line.
                    resume_at = (children[-1][0] + 1, None)
                    child_waiting_floats = []
                    break

            position_x = new_position_x
            waiting_children.append((index, new_child))

        waiting_floats.extend(child_waiting_floats)
        if resume_at is not None:
            children.extend(waiting_children)
            resume_at = (index, resume_at)
            break
    else:
        children.extend(waiting_children)
        resume_at = None

    is_end = resume_at is None
    new_box = box.copy_with_children(
        [box_child for index, box_child in children],
        is_start=is_start, is_end=is_end)
    if isinstance(box, boxes.LineBox):
        # Line boxes already have a position_x which may not be the same
        # as content_box_left when text-indent is non-zero.
        # This is important for justified text.
        new_box.width = position_x - new_box.position_x
    else:
        new_box.position_x = initial_position_x
        if (is_start and box.style['direction'] == 'ltr') or (
                is_end and box.style['direction'] == 'rtl'):
            for child in new_box.children:
                child.translate(dx=left_spacing)
        new_box.width = position_x - content_box_left
        new_box.translate(dx=float_widths['left'], ignore_floats=True)

    line_height, new_box.baseline = strut_layout(box.style, context)
    new_box.height = box.style['font_size']
    half_leading = (line_height - new_box.height) / 2.
    # Set margins to the half leading but also compensate for borders and
    # paddings. We want margin_height() == line_height
    new_box.margin_top = (half_leading - new_box.border_top_width -
                          new_box.padding_top)
    new_box.margin_bottom = (half_leading - new_box.border_bottom_width -
                             new_box.padding_bottom)

    if new_box.style['position'] == 'relative':
        for absolute_box in absolute_boxes:
            absolute_layout(context, absolute_box, new_box, fixed_boxes)

    if resume_at is not None:
        if resume_at[0] < float_resume_at:
            resume_at = (float_resume_at, None)

    return (
        new_box, resume_at, preserved_line_break, first_letter, last_letter,
        float_widths)


def split_text_box(context, box, available_width, skip):
    """Keep as much text as possible from a TextBox in a limited width.

    Try not to overflow but always have some text in ``new_box``

    Return ``(new_box, skip, preserved_line_break)``. ``skip`` is the number of
    UTF-8 bytes to skip form the start of the TextBox for the next line, or
    ``None`` if all of the text fits.

    Also break on preserved line breaks.

    """
    assert isinstance(box, boxes.TextBox)
    font_size = box.style['font_size']
    text = box.text[skip:]
    if font_size == 0 or not text:
        return None, None, False
    layout, length, resume_at, width, height, baseline = split_first_line(
        text, box.style, context, available_width, box.justification_spacing)
    assert resume_at != 0

    # Convert ``length`` and ``resume_at`` from UTF-8 indexes in text
    # to Unicode indexes.
    # No need to encode what’s after resume_at (if set) or length (if
    # resume_at is not set). One code point is one or more byte, so
    # UTF-8 indexes are always bigger or equal to Unicode indexes.
    new_text = layout.text_bytes.decode('utf8')
    encoded = text.encode('utf8')
    if resume_at is not None:
        between = encoded[length:resume_at].decode('utf8')
        resume_at = len(encoded[:resume_at].decode('utf8'))
    length = len(encoded[:length].decode('utf8'))

    if length > 0:
        box = box.copy_with_text(new_text)
        box.width = width
        box.pango_layout = layout
        # "The height of the content area should be based on the font,
        #  but this specification does not specify how."
        # http://www.w3.org/TR/CSS21/visudet.html#inline-non-replaced
        # We trust Pango and use the height of the LayoutLine.
        box.height = height
        # "only the 'line-height' is used when calculating the height
        #  of the line box."
        # Set margins so that margin_height() == line_height
        line_height, _ = strut_layout(box.style, context)
        half_leading = (line_height - height) / 2.
        box.margin_top = half_leading
        box.margin_bottom = half_leading
        # form the top of the content box
        box.baseline = baseline
        # form the top of the margin box
        box.baseline += box.margin_top
    else:
        box = None

    if resume_at is None:
        preserved_line_break = False
    else:
        preserved_line_break = (length != resume_at) and between.strip(' ')
        if preserved_line_break:
            # See http://unicode.org/reports/tr14/
            # \r is already handled by process_whitespace
            line_breaks = ('\n', '\t', '\f', '\u0085', '\u2028', '\u2029')
            assert between in line_breaks, (
                'Got %r between two lines. '
                'Expected nothing or a preserved line break' % (between,))
        resume_at += skip

    return box, resume_at, preserved_line_break


def line_box_verticality(box):
    """Handle ``vertical-align`` within an :class:`LineBox` (or of a
    non-align sub-tree).

    Place all boxes vertically assuming that the baseline of ``box``
    is at `y = 0`.

    Return ``(max_y, min_y)``, the maximum and minimum vertical position
    of margin boxes.

    """
    top_bottom_subtrees = []
    max_y, min_y = aligned_subtree_verticality(
        box, top_bottom_subtrees, baseline_y=0)
    subtrees_with_min_max = [
        (subtree, sub_max_y, sub_min_y)
        for subtree in top_bottom_subtrees
        for sub_max_y, sub_min_y in [
            (None, None) if subtree.is_floated()
            else aligned_subtree_verticality(
                subtree, top_bottom_subtrees, baseline_y=0)
        ]
    ]

    if subtrees_with_min_max:
        sub_positions = [
            sub_max_y - sub_min_y
            for subtree, sub_max_y, sub_min_y in subtrees_with_min_max
            if not subtree.is_floated()]
        if sub_positions:
            highest_sub = max(sub_positions)
            max_y = max(max_y, min_y + highest_sub)

    for subtree, sub_max_y, sub_min_y in subtrees_with_min_max:
        if subtree.is_floated():
            dy = min_y - subtree.position_y
        elif subtree.style['vertical_align'] == 'top':
            dy = min_y - sub_min_y
        else:
            assert subtree.style['vertical_align'] == 'bottom'
            dy = max_y - sub_max_y
        translate_subtree(subtree, dy)
    return max_y, min_y


def translate_subtree(box, dy):
    if isinstance(box, boxes.InlineBox):
        box.position_y += dy
        if box.style['vertical_align'] in ('top', 'bottom'):
            for child in box.children:
                translate_subtree(child, dy)
    else:
        # Text or atomic boxes
        box.translate(dy=dy)


def aligned_subtree_verticality(box, top_bottom_subtrees, baseline_y):
    max_y, min_y = inline_box_verticality(box, top_bottom_subtrees, baseline_y)
    # Account for the line box itself:
    top = baseline_y - box.baseline
    bottom = top + box.margin_height()
    if min_y is None or top < min_y:
        min_y = top
    if max_y is None or bottom > max_y:
        max_y = bottom

    return max_y, min_y


def inline_box_verticality(box, top_bottom_subtrees, baseline_y):
    """Handle ``vertical-align`` within an :class:`InlineBox`.

    Place all boxes vertically assuming that the baseline of ``box``
    is at `y = baseline_y`.

    Return ``(max_y, min_y)``, the maximum and minimum vertical position
    of margin boxes.

    """
    max_y = None
    min_y = None
    if not isinstance(box, (boxes.LineBox, boxes.InlineBox)):
        return max_y, min_y

    for child in box.children:
        if not child.is_in_normal_flow():
            if child.is_floated():
                top_bottom_subtrees.append(child)
            continue
        vertical_align = child.style['vertical_align']
        if vertical_align == 'baseline':
            child_baseline_y = baseline_y
        elif vertical_align == 'middle':
            one_ex = box.style['font_size'] * ex_ratio(box.style)
            top = baseline_y - (one_ex + child.margin_height()) / 2.
            child_baseline_y = top + child.baseline
        # TODO: actually implement vertical-align: top and bottom
        elif vertical_align == 'text-top':
            # align top with the top of the parent’s content area
            top = (baseline_y - box.baseline + box.margin_top +
                   box.border_top_width + box.padding_top)
            child_baseline_y = top + child.baseline
        elif vertical_align == 'text-bottom':
            # align bottom with the bottom of the parent’s content area
            bottom = (baseline_y - box.baseline + box.margin_top +
                      box.border_top_width + box.padding_top + box.height)
            child_baseline_y = bottom - child.margin_height() + child.baseline
        elif vertical_align in ('top', 'bottom'):
            # Later, we will assume for this subtree that its baseline
            # is at y=0.
            child_baseline_y = 0
        else:
            # Numeric value: The child’s baseline is `vertical_align` above
            # (lower y) the parent’s baseline.
            child_baseline_y = baseline_y - vertical_align

        # the child’s `top` is `child.baseline` above (lower y) its baseline.
        top = child_baseline_y - child.baseline
        if isinstance(child, (boxes.InlineBlockBox, boxes.InlineFlexBox)):
            # This also includes table wrappers for inline tables.
            child.translate(dy=top - child.position_y)
        else:
            child.position_y = top
            # grand-children for inline boxes are handled below

        if vertical_align in ('top', 'bottom'):
            # top or bottom are special, they need to be handled in
            # a later pass.
            top_bottom_subtrees.append(child)
            continue

        bottom = top + child.margin_height()
        if min_y is None or top < min_y:
            min_y = top
        if max_y is None or bottom > max_y:
            max_y = bottom
        if isinstance(child, boxes.InlineBox):
            children_max_y, children_min_y = inline_box_verticality(
                child, top_bottom_subtrees, child_baseline_y)
            if children_min_y is not None and children_min_y < min_y:
                min_y = children_min_y
            if children_max_y is not None and children_max_y > max_y:
                max_y = children_max_y
    return max_y, min_y


def text_align(context, line, available_width, last):
    """Return how much the line should be moved horizontally according to
    the `text-align` property.

    """
    align = line.style['text_align']
    space_collapse = line.style['white_space'] in (
        'normal', 'nowrap', 'pre-line')
    if align in ('-weasy-start', '-weasy-end'):
        if (align == '-weasy-start') ^ (line.style['direction'] == 'rtl'):
            align = 'left'
        else:
            align = 'right'
    if align == 'justify' and last:
        align = 'right' if line.style['direction'] == 'rtl' else 'left'
    if align == 'left':
        return 0
    offset = available_width - line.width
    if align == 'justify':
        if space_collapse:
            # Justification of texts where white space is not collapsing is
            # - forbidden by CSS 2, and
            # - not required by CSS 3 Text.
            justify_line(context, line, offset)
        return 0
    if align == 'center':
        offset /= 2.
    else:
        assert align == 'right'
    return offset


def justify_line(context, line, extra_width):
    # TODO: We should use a better alorithm here, see
    # https://www.w3.org/TR/css-text-3/#justify-algos
    nb_spaces = count_spaces(line)
    if nb_spaces == 0:
        return
    add_word_spacing(context, line, extra_width / nb_spaces, 0)


def count_spaces(box):
    if isinstance(box, boxes.TextBox):
        # TODO: remove trailing spaces correctly
        return box.text.count(' ')
    elif isinstance(box, (boxes.LineBox, boxes.InlineBox)):
        return sum(count_spaces(child) for child in box.children)
    else:
        return 0


def add_word_spacing(context, box, justification_spacing, x_advance):
    if isinstance(box, boxes.TextBox):
        box.justification_spacing = justification_spacing
        box.position_x += x_advance
        nb_spaces = count_spaces(box)
        if nb_spaces > 0:
            layout, _, resume_at, width, _, _ = split_first_line(
                box.text, box.style, context, float('inf'),
                box.justification_spacing)
            assert resume_at is None
            # XXX new_box.width - box.width is always 0???
            # x_advance +=  new_box.width - box.width
            x_advance += justification_spacing * nb_spaces
            box.width = width
            box.pango_layout = layout
    elif isinstance(box, (boxes.LineBox, boxes.InlineBox)):
        box.position_x += x_advance
        previous_x_advance = x_advance
        for child in box.children:
            if child.is_in_normal_flow():
                x_advance = add_word_spacing(
                    context, child, justification_spacing, x_advance)
        box.width += x_advance - previous_x_advance
    else:
        # Atomic inline-level box
        box.translate(x_advance, 0)
    return x_advance


def is_phantom_linebox(linebox):
    """http://www.w3.org/TR/CSS21/visuren.html#phantom-line-box"""
    for child in linebox.children:
        if isinstance(child, boxes.InlineBox):
            if not is_phantom_linebox(child):
                return False
            for side in ('top', 'right', 'bottom', 'left'):
                if (getattr(child.style['margin_%s' % side], 'value', None) or
                        child.style['border_%s_width' % side] or
                        child.style['padding_%s' % side].value):
                    return False
        elif child.is_in_normal_flow():
            return False
    return True


def can_break_inside(box):
    # See https://www.w3.org/TR/css-text-3/#white-space-property
    text_wrap = box.style['white_space'] in ('normal', 'pre-wrap', 'pre-line')
    if isinstance(box, boxes.AtomicInlineLevelBox):
        return False
    elif isinstance(box, boxes.TextBox):
        if text_wrap:
            return can_break_text(box.text, box.style['lang'])
        else:
            return False
    elif isinstance(box, boxes.ParentBox):
        if text_wrap:
            return any(can_break_inside(child) for child in box.children)
        else:
            return False
    return False
