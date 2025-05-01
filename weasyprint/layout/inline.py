"""Layout for inline-level boxes."""

import unicodedata
from math import inf

from ..css import computed_from_cascaded
from ..css.computed_values import character_ratio, strut_layout
from ..formatting_structure import boxes, build
from ..text.line_break import can_break_text, create_layout, split_first_line
from .absolute import AbsolutePlaceholder, absolute_layout
from .flex import flex_layout
from .float import avoid_collisions, float_layout
from .grid import grid_layout
from .leader import handle_leader
from .min_max import handle_min_max_width
from .percent import resolve_one_percentage, resolve_percentages
from .preferred import inline_min_content_width, shrink_to_fit, trailing_whitespace_size
from .replaced import inline_replaced_box_layout
from .table import find_in_flow_baseline, table_wrapper_width


def iter_line_boxes(context, box, position_y, bottom_space, skip_stack,
                    containing_block, absolute_boxes, fixed_boxes,
                    first_letter_style):
    """Return an iterator of ``(line, resume_at)``.

    ``line`` is a laid-out LineBox with as much content as possible that
    fits in the available width.

    """
    resolve_percentages(box, containing_block)
    if skip_stack is None:
        # TODO: wrong, see issue #679.
        resolve_one_percentage(box, 'text_indent', containing_block.width)
    else:
        box.text_indent = 0
    while True:
        line, resume_at = get_next_linebox(
            context, box, position_y, bottom_space, skip_stack,
            containing_block, absolute_boxes, fixed_boxes, first_letter_style)
        if line:
            handle_leader(context, line, containing_block)
            position_y = line.position_y + line.height
        if line is None:
            return
        yield line, resume_at
        if resume_at is None:
            return
        skip_stack = resume_at
        box.text_indent = 0
        first_letter_style = None


def get_next_linebox(context, linebox, position_y, bottom_space, skip_stack,
                     containing_block, absolute_boxes, fixed_boxes,
                     first_letter_style):
    """Return ``(line, resume_at)``."""
    skip_stack = skip_first_whitespace(linebox, skip_stack)
    if skip_stack == 'continue':
        return None, None

    skip_stack = first_letter_to_box(linebox, skip_stack, first_letter_style)

    linebox.position_y = position_y

    if context.excluded_shapes:
        # Width and height must be calculated to avoid floats
        linebox.width = inline_min_content_width(
            context, linebox, skip_stack=skip_stack, first_line=True)
        linebox.height, _ = strut_layout(linebox.style, context)
    else:
        # No float, width and height will be set by the lines
        linebox.width = linebox.height = 0
    position_x, position_y, available_width = avoid_collisions(
        context, linebox, containing_block, outer=False)

    candidate_height = linebox.height

    excluded_shapes = context.excluded_shapes.copy()

    while True:
        original_position_x = linebox.position_x = position_x
        original_position_y = linebox.position_y = position_y
        original_width = linebox.width
        max_x = position_x + available_width
        position_x += linebox.text_indent

        line_placeholders = []
        line_absolutes = []
        line_fixed = []
        waiting_floats = []
        line_children = []

        (line, resume_at, preserved_line_break, first_letter,
         last_letter, float_width) = split_inline_box(
             context, linebox, position_x, max_x, bottom_space, skip_stack,
             containing_block, line_absolutes, line_fixed, line_placeholders,
             waiting_floats, line_children)
        linebox.width, linebox.height = line.width, line.height

        if is_phantom_linebox(line) and not preserved_line_break:
            line.height = 0
            break

        remove_last_whitespace(context, line)

        new_position_x, _, new_available_width = avoid_collisions(
            context, linebox, containing_block, outer=False)
        offset_x = text_align(
            context, line, new_available_width,
            last=(resume_at is None or preserved_line_break))
        if containing_block.style['direction'] == 'rtl':
            offset_x *= -1
            offset_x -= line.width

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
        # See issue #583.
        line.position_y = position_y

        if line.height <= candidate_height:
            break
        candidate_height = line.height

        new_excluded_shapes = context.excluded_shapes
        context.excluded_shapes = excluded_shapes
        position_x, position_y, available_width = avoid_collisions(
            context, line, containing_block, outer=False)
        if containing_block.style['direction'] == 'ltr':
            condition = (position_x, position_y) == (
                original_position_x, original_position_y)
        else:
            condition = (position_x + line.width, position_y) == (
                original_position_x + original_width, original_position_y)
        if condition:
            context.excluded_shapes = new_excluded_shapes
            break

    absolute_boxes.extend(line_absolutes)
    fixed_boxes.extend(line_fixed)

    for placeholder in line_placeholders:
        if 'inline' in placeholder.style.specified['display']:
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
        new_waiting_float, waiting_float_resume_at = float_layout(
            context, waiting_float, containing_block, absolute_boxes,
            fixed_boxes, bottom_space, skip_stack=None)
        float_children.append(new_waiting_float)
        if waiting_float_resume_at:
            context.broken_out_of_flow[new_waiting_float] = (
                waiting_float, containing_block, waiting_float_resume_at)
    if float_children:
        line.children += tuple(float_children)

    return line, resume_at


def skip_first_whitespace(box, skip_stack):
    """Return ``skip_stack`` to start just after removable leading spaces.

    See https://www.w3.org/TR/CSS21/text.html#white-space-model

    """
    if skip_stack is None:
        index = 0
        next_skip_stack = None
    else:
        (index, next_skip_stack), = skip_stack.items()

    if isinstance(box, boxes.TextBox):
        assert next_skip_stack is None
        white_space = box.style['white_space']
        text = box.text.encode()
        if index == len(text):
            # Starting a the end of the TextBox, no text to see: Continue
            return 'continue'
        if white_space in ('normal', 'nowrap', 'pre-line'):
            text = text[index:]
            while text and text.startswith(b' '):
                index += 1
                text = text[1:]
        return {index: None} if index else None

    if isinstance(box, (boxes.LineBox, boxes.InlineBox)):
        if index == 0 and not box.children:
            return None
        result = skip_first_whitespace(box.children[index], next_skip_stack)
        if result == 'continue':
            index += 1
            if index >= len(box.children):
                return 'continue'
            result = skip_first_whitespace(box.children[index], None)
        return {index: result} if (index or result) else None

    assert skip_stack is None, f'unexpected skip inside {box}'
    return None


def remove_last_whitespace(context, line):
    """Remove in place space characters at the end of a line.

    This also reduces the width and position of the inline parents of the
    modified text.

    """
    ancestors = []
    box = line
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

    # RTL line, the trailing space is at the left of the box. We have to translate the
    # box to align the stripped text with the right edge of the box.
    if box.pango_layout.first_line_direction % 2:
        for child in line.children:
            child.translate(dx=-space_width, ignore_floats=True)

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
        # Some properties must be ignored in first-letter boxes.
        # https://drafts.csswg.org/selectors-3/#application-in-css
        # At least, position is ignored to avoid layout troubles.
        first_letter_style['position'] = 'static'

        first_letter = ''
        child = box.children[0]
        if isinstance(child, boxes.TextBox):
            letter_style = computed_from_cascaded(
                cascaded={}, parent_style=first_letter_style, element=None)
            if child.element_tag.endswith('::first-letter'):
                letter_box = boxes.InlineBox(
                    f'{box.element_tag}::first-letter', letter_style,
                    box.element, [child])
                box.children = ((letter_box, *box.children[1:]))
            elif child.text:
                character_found = False
                if skip_stack:
                    child_skip_stack, = skip_stack.values()
                    if child_skip_stack:
                        index, = child_skip_stack
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
                            f'{box.element_tag}::first-letter',
                            first_letter_style, box.element, [])
                        text_box = boxes.TextBox(
                            f'{box.element_tag}::first-letter', letter_style,
                            box.element, first_letter)
                        letter_box.children = (text_box,)
                        box.children = (letter_box, *box.children)
                    else:
                        letter_box = boxes.BlockBox(
                            f'{box.element_tag}::first-letter',
                            first_letter_style, box.element, [])
                        letter_box.first_letter_style = None
                        line_box = boxes.LineBox(
                            f'{box.element_tag}::first-letter', letter_style,
                            box.element, [])
                        letter_box.children = (line_box,)
                        text_box = boxes.TextBox(
                            f'{box.element_tag}::first-letter', letter_style,
                            box.element, first_letter)
                        line_box.children = (text_box,)
                        box.children = (letter_box, *box.children)
                    build.process_text_transform(text_box)
                    if skip_stack and child_skip_stack:
                        index, = skip_stack
                        (child_index, grandchild_skip_stack), = (
                            child_skip_stack.items())
                        skip_stack = {
                            index: {child_index + 1: grandchild_skip_stack}}
        elif isinstance(child, boxes.ParentBox):
            if skip_stack:
                child_skip_stack, = skip_stack.values()
            else:
                child_skip_stack = None
            child_skip_stack = first_letter_to_box(
                child, child_skip_stack, first_letter_style)
            if skip_stack:
                index, = skip_stack
                skip_stack = {index: child_skip_stack}
    return skip_stack


def atomic_box(context, box, position_x, skip_stack, containing_block,
               absolute_boxes, fixed_boxes):
    """Compute the width and the height of the atomic ``box``."""
    if isinstance(box, boxes.ReplacedBox):
        box = box.copy()
        inline_replaced_box_layout(box, containing_block)
        box.baseline = box.margin_height()
    elif isinstance(box, boxes.InlineBlockBox):
        if box.is_table_wrapper:
            containing_size = (containing_block.width, containing_block.height)
            table_wrapper_width(context, box, containing_size)
            width, min_width, max_width = box.width, box.min_width, box.max_width
        box = inline_block_box_layout(
            context, box, position_x, skip_stack, containing_block,
            absolute_boxes, fixed_boxes)
        if box.is_table_wrapper:
            box.width, box.min_width, box.max_width = width, min_width, max_width
    else:  # pragma: no cover
        raise TypeError(f'Layout for {type(box).__name__} not handled yet')
    return box


def inline_block_box_layout(context, box, position_x, skip_stack,
                            containing_block, absolute_boxes, fixed_boxes):
    from .block import block_container_layout

    resolve_percentages(box, containing_block)

    # https://www.w3.org/TR/CSS21/visudet.html#inlineblock-width
    if box.margin_left == 'auto':
        box.margin_left = 0
    if box.margin_right == 'auto':
        box.margin_right = 0
    # https://www.w3.org/TR/CSS21/visudet.html#block-root-margin
    if box.margin_top == 'auto':
        box.margin_top = 0
    if box.margin_bottom == 'auto':
        box.margin_bottom = 0

    inline_block_width(box, context, containing_block)

    box.position_x = position_x
    box.position_y = 0
    box, _, _, _, _, _ = block_container_layout(
        context, box, bottom_space=-inf, skip_stack=skip_stack,
        page_is_empty=True, absolute_boxes=absolute_boxes,
        fixed_boxes=fixed_boxes, adjoining_margins=None, discard=False,
        max_lines=None)
    box.baseline = inline_block_baseline(box)
    return box


def inline_block_baseline(box):
    """Return the y position of the baseline for an inline block.

    Position is taken from the top of its margin box.

    https://www.w3.org/TR/CSS21/visudet.html#propdef-vertical-align

    """
    if box.is_table_wrapper:
        # Inline table's baseline is its first row's baseline
        for child in box.children:
            if isinstance(child, boxes.TableBox):
                if child.children and child.children[0].children:
                    first_row = child.children[0].children[0]
                    return first_row.baseline
    elif box.style['overflow'] == 'visible':
        result = find_in_flow_baseline(box, last=True)
        if result:
            return result
    return box.position_y + box.margin_height()


@handle_min_max_width
def inline_block_width(box, context, containing_block):
    available_content_width = containing_block.width - (
        box.margin_left + box.margin_right +
        box.border_left_width + box.border_right_width +
        box.padding_left + box.padding_right)
    if box.width == 'auto':
        box.width = shrink_to_fit(context, box, available_content_width)


def split_inline_level(context, box, position_x, max_x, bottom_space,
                       skip_stack, containing_block, absolute_boxes,
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
            (skip, skip_stack), = skip_stack.items()
            skip = skip or 0
            assert skip_stack is None

        is_line_start = len(line_children) == 0
        new_box, skip, preserved_line_break = split_text_box(
            context, box, max_x - position_x, skip,
            is_line_start=is_line_start)

        if skip is None:
            resume_at = None
        else:
            resume_at = {skip: None}
        if box.text:
            first_letter = box.text[0]
            if skip is None:
                last_letter = box.text[-1]
            else:
                last_letter = box.text.encode()[:skip].decode()[-1]
        else:
            first_letter = last_letter = None
    elif isinstance(box, boxes.InlineBox):
        if box.margin_left == 'auto':
            box.margin_left = 0
        if box.margin_right == 'auto':
            box.margin_right = 0
        (new_box, resume_at, preserved_line_break, first_letter,
         last_letter, float_widths) = split_inline_box(
             context, box, position_x, max_x, bottom_space, skip_stack,
             containing_block, absolute_boxes, fixed_boxes, line_placeholders,
             waiting_floats, line_children)
    elif isinstance(box, boxes.AtomicInlineLevelBox):
        new_box = atomic_box(
            context, box, position_x, skip_stack, containing_block,
            absolute_boxes, fixed_boxes)
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
        for side in ('top', 'right', 'bottom', 'left'):
            if getattr(box, f'margin_{side}') == 'auto':
                setattr(box, f'margin_{side}', 0)
        new_box, resume_at, _, _, _ = flex_layout(
            context, box, -inf, skip_stack, containing_block, False,
            absolute_boxes, fixed_boxes, False)
        preserved_line_break = False
        first_letter = '\u2e80'
        last_letter = '\u2e80'
    elif isinstance(box, boxes.InlineGridBox):
        box.position_x = position_x
        box.position_y = 0
        for side in ('top', 'right', 'bottom', 'left'):
            if getattr(box, f'margin_{side}') == 'auto':
                setattr(box, f'margin_{side}', 0)
        new_box, resume_at, _, _, _ = grid_layout(
            context, box, -inf, skip_stack, containing_block, False,
            absolute_boxes, fixed_boxes)
        preserved_line_break = False
        first_letter = '\u2e80'
        last_letter = '\u2e80'
    else:  # pragma: no cover
        raise TypeError(f'Layout for {type(box).__name__} not handled yet')
    return (
        new_box, resume_at, preserved_line_break, first_letter, last_letter,
        float_widths)


def _out_of_flow_layout(context, box, containing_block, index, child,
                        children, line_children, waiting_children,
                        waiting_floats, absolute_boxes, fixed_boxes,
                        line_placeholders, float_widths, max_x, position_x,
                        bottom_space):
    if child.is_absolutely_positioned():
        child.position_x = position_x
        placeholder = AbsolutePlaceholder(child)
        line_placeholders.append(placeholder)
        waiting_children.append((index, placeholder, child))
        if child.style['position'] == 'absolute':
            absolute_boxes.append(placeholder)
        else:
            fixed_boxes.append(placeholder)

    elif child.is_floated():
        child.position_x = position_x
        float_width = shrink_to_fit(context, child, containing_block.width)

        # To retrieve the real available space for floats, we must remove
        # the trailing whitespaces from the line
        non_floating_children = [
            child_ for _, child_, _ in (children + waiting_children)
            if not child_.is_floated()]
        if non_floating_children:
            float_width -= trailing_whitespace_size(
                context, non_floating_children[-1])

        if float_width > max_x - position_x or waiting_floats:
            # TODO: the absolute and fixed boxes in the floats must be
            # added here, and not in iter_line_boxes
            waiting_floats.append(child)
        else:
            new_child, float_resume_at = float_layout(
                context, child, containing_block, absolute_boxes, fixed_boxes,
                bottom_space, skip_stack=None)
            if float_resume_at:
                context.broken_out_of_flow[child] = (
                    child, containing_block, float_resume_at)
            waiting_children.append((index, new_child, child))
            child = new_child

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

    elif child.is_running():
        running_name = child.style['position'][1]
        page = context.current_page
        context.running_elements[running_name][page].append(child)


def _break_waiting_children(context, box, max_x, bottom_space,
                            initial_skip_stack, absolute_boxes, fixed_boxes,
                            line_placeholders, waiting_floats, line_children,
                            children, waiting_children):
    if waiting_children:
        # Too wide, try to cut inside waiting children, starting from the end.
        # TODO: we should take care of children added into absolute_boxes,
        # fixed_boxes and other lists.
        waiting_children_copy = waiting_children.copy()
        while waiting_children_copy:
            child_index, child, original_child = waiting_children_copy.pop()
            if not child.is_in_normal_flow() or not can_break_inside(child):
                continue

            if initial_skip_stack and child_index in initial_skip_stack:
                child_skip_stack = initial_skip_stack[child_index]
            else:
                child_skip_stack = None

            # Break the waiting child at its last possible breaking point.
            # TODO: The dirty solution chosen here is to decrease the
            # actual size by 1 and render the waiting child again with this
            # constraint. We may find a better way.
            max_x = child.position_x + child.margin_width() - 1
            while max_x > child.position_x:
                new_child, child_resume_at, _, _, _, _ = split_inline_level(
                    context, original_child, child.position_x, max_x,
                    bottom_space, child_skip_stack, box, absolute_boxes,
                    fixed_boxes, line_placeholders, waiting_floats,
                    line_children)
                if child_resume_at:
                    break
                max_x -= 1
            else:
                # No line break found
                continue

            children.extend(waiting_children_copy)
            if new_child is None:
                # May be None where we have an empty TextBox.
                assert isinstance(child, boxes.TextBox)
            else:
                children.append((child_index, new_child, child))

            return {child_index: child_resume_at}

    if children:
        # Too wide, can't break waiting children and the inline is
        # non-empty: put child entirely on the next line.
        return {children[-1][0] + 1: None}


def split_inline_box(context, box, position_x, max_x, bottom_space, skip_stack,
                     containing_block, absolute_boxes, fixed_boxes,
                     line_placeholders, waiting_floats, line_children):
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
    left_spacing = (
        box.padding_left + box.margin_left + box.border_left_width)
    right_spacing = (
        box.padding_right + box.margin_right + box.border_right_width)
    content_box_left = position_x

    children = []
    waiting_children = []
    preserved_line_break = False
    first_letter = last_letter = None
    float_widths = {'left': 0, 'right': 0}
    float_resume_index = 0

    if box.style['position'] == 'relative':
        absolute_boxes = []

    if is_start:
        skip = 0
    else:
        (skip, skip_stack), = skip_stack.items()

    for i, child in enumerate(box.children[skip:]):
        index = i + skip
        child.position_y = box.position_y

        if not child.is_in_normal_flow():
            _out_of_flow_layout(
                context, box, containing_block, index, child, children,
                line_children, waiting_children, waiting_floats,
                absolute_boxes, fixed_boxes, line_placeholders, float_widths,
                max_x, position_x, bottom_space)
            if child.is_floated():
                float_resume_index = index + 1
                if child not in waiting_floats:
                    max_x -= child.margin_width()
            continue

        is_last_child = (index == len(box.children) - 1)
        available_width = max_x
        child_waiting_floats = []
        new_child, resume_at, preserved, first, last, new_float_widths = (
            split_inline_level(
                context, child, position_x, available_width, bottom_space,
                skip_stack, containing_block, absolute_boxes, fixed_boxes,
                line_placeholders, child_waiting_floats, line_children))
        if box.style['direction'] == 'rtl':
            end_spacing = left_spacing
            max_x -= new_float_widths['left']
        else:
            end_spacing = right_spacing
            max_x -= new_float_widths['right']
        if is_last_child and end_spacing and resume_at is None:
            # TODO: we should take care of children added into absolute_boxes,
            # fixed_boxes and other lists.
            available_width -= end_spacing
            new_child, resume_at, preserved, first, last, new_float_widths = (
                split_inline_level(
                    context, child, position_x, available_width, bottom_space,
                    skip_stack, containing_block, absolute_boxes, fixed_boxes,
                    line_placeholders, child_waiting_floats, line_children))

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
            elif first in (True, False):
                can_break = first
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
            # Store lines to get previous break points.
            if isinstance(box, boxes.LineBox):
                line_children.append((index, new_child))

            # Check that text doesn’t overflow.
            new_position_x = new_child.position_x + new_child.margin_width()
            if new_position_x - trailing_whitespace_size(context, new_child) > max_x:
                # Text overflows, find previous break point.
                previous_resume_at = _break_waiting_children(
                    context, containing_block, max_x, bottom_space, initial_skip_stack,
                    absolute_boxes, fixed_boxes, line_placeholders,
                    waiting_floats, line_children, children, waiting_children)
                if previous_resume_at:
                    resume_at = previous_resume_at
                    break

            position_x = new_position_x
            waiting_children.append((index, new_child, child))

        waiting_floats.extend(child_waiting_floats)
        if resume_at is not None:
            children.extend(waiting_children)
            resume_at = {index: resume_at}
            break
    else:
        children.extend(waiting_children)
        resume_at = None

    # Reorder inline blocks when direction is rtl
    if box.style['direction'] == 'rtl' and len(children) > 1:
        in_flow_children = [
            box_child for _, box_child, _ in children
            if box_child.is_in_normal_flow()]
        position_x = in_flow_children[0].position_x
        for child in in_flow_children[::-1]:
            child.translate(
                dx=(position_x - child.position_x), ignore_floats=True)
            position_x += child.margin_width()

    is_end = resume_at is None
    new_box = box.copy_with_children(
        [box_child for index, box_child, _ in children])
    new_box.remove_decoration(start=not is_start, end=not is_end)
    if isinstance(box, boxes.LineBox):
        # We must reset line box width according to its new children
        new_box.width = 0
        children = new_box.children
        if new_box.style['direction'] == 'ltr':
            children = children[::-1]
        for child in children:
            if child.is_in_normal_flow():
                new_box.width = (
                    child.position_x + child.margin_width() -
                    new_box.position_x)
                break
    else:
        new_box.position_x = initial_position_x
        if box.style['box_decoration_break'] == 'clone':
            translation_needed = True
        else:
            translation_needed = (
                is_start if box.style['direction'] == 'ltr' else is_end)
        if translation_needed:
            for child in new_box.children:
                child.translate(dx=left_spacing)
        new_box.width = position_x - content_box_left
        new_box.translate(dx=float_widths['left'], ignore_floats=True)

    line_height, new_box.baseline = strut_layout(box.style, context)
    new_box.height = box.style['font_size']
    half_leading = (line_height - new_box.height) / 2
    # Set margins to the half leading but also compensate for borders and
    # paddings. We want margin_height() == line_height
    new_box.margin_top = (
        half_leading - new_box.border_top_width - new_box.padding_top)
    new_box.margin_bottom = (
        half_leading - new_box.border_bottom_width - new_box.padding_bottom)

    if new_box.style['position'] == 'relative':
        for absolute_box in absolute_boxes:
            absolute_layout(
                context, absolute_box, new_box, fixed_boxes, bottom_space,
                skip_stack=None)

    if resume_at is not None:
        index = next(iter(resume_at))
        if index < float_resume_index:
            resume_at = {float_resume_index: None}

    if box.is_leader:
        first_letter = True
        last_letter = False

    return (
        new_box, resume_at, preserved_line_break, first_letter, last_letter,
        float_widths)


def split_text_box(context, box, available_width, skip, is_line_start=True):
    """Keep as much text as possible from a TextBox in a limited width.

    Try not to overflow but always have some text in ``new_box``.

    Return ``(new_box, skip, preserved_line_break)``. ``skip`` is the number of
    UTF-8 bytes to skip form the start of the TextBox for the next line, or
    ``None`` if all of the text fits.

    Also break on preserved line breaks.

    """
    assert isinstance(box, boxes.TextBox)
    font_size = box.style['font_size']
    text = box.text.encode()[skip:]
    if font_size == 0 or not text:
        return None, None, False
    layout, length, resume_index, width, height, baseline = split_first_line(
        text.decode(), box.style, context, available_width,
        box.justification_spacing, is_line_start=is_line_start)
    assert resume_index != 0

    if length > 0:
        box = box.copy_with_text(layout.text)
        box.width = width
        box.pango_layout = layout
        # "The height of the content area should be based on the font,
        #  but this specification does not specify how."
        # https://www.w3.org/TR/CSS21/visudet.html#inline-non-replaced
        # We trust Pango and use the height of the LayoutLine.
        box.height = height
        # "only the 'line-height' is used when calculating the height
        #  of the line box."
        # Set margins so that margin_height() == line_height
        line_height, _ = strut_layout(box.style, context)
        half_leading = (line_height - height) / 2
        box.margin_top = half_leading
        box.margin_bottom = half_leading
        # form the top of the content box
        box.baseline = baseline
        # form the top of the margin box
        box.baseline += box.margin_top
    else:
        box = None

    if resume_index is None:
        preserved_line_break = False
    else:
        between = text[length:resume_index].decode()
        preserved_line_break = (
            (length != resume_index) and between.strip(' '))
        if preserved_line_break:
            # See https://unicode.org/reports/tr14/
            # \r is already handled by process_whitespace
            line_breaks = ('\n', '\t', '\f', '\u0085', '\u2028', '\u2029')
            assert between in line_breaks, (
                'Got %r between two lines. '
                'Expected nothing or a preserved line break' % (between,))
        resume_index += skip

    return box, resume_index, preserved_line_break


def line_box_verticality(box):
    """Handle ``vertical-align`` within a :class:`LineBox`.

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
                subtree, top_bottom_subtrees, baseline_y=0)]]

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
            one_ex = box.style['font_size'] * character_ratio(box.style, 'x')
            top = baseline_y - (one_ex + child.margin_height()) / 2
            child_baseline_y = top + child.baseline
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
            # TODO: actually implement vertical-align: top and bottom
            # Later, we will assume for this subtree that its baseline
            # is at y=0.
            child_baseline_y = 0
        else:
            # Numeric value: The child’s baseline is `vertical_align` above
            # (lower y) the parent’s baseline.
            child_baseline_y = baseline_y - vertical_align

        # the child’s `top` is `child.baseline` above (lower y) its baseline.
        top = child_baseline_y - child.baseline
        box_types = (boxes.InlineBlockBox, boxes.InlineFlexBox, boxes.InlineGridBox)
        if isinstance(child, box_types):
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
    """Return the line horizontal offset according to ``text-align``."""

    # "When the total width of the inline-level boxes on a line is less than
    # the width of the line box containing them, their horizontal distribution
    # within the line box is determined by the 'text-align' property."
    if line.width >= available_width:
        return 0

    align = line.style['text_align_all']
    if last:
        align_last = line.style['text_align_last']
        align = align if align_last == 'auto' else align_last
    space_collapse = line.style['white_space'] in (
        'normal', 'nowrap', 'pre-line')
    if align in ('left', 'right'):
        if (align == 'left') ^ (line.style['direction'] == 'rtl'):
            align = 'start'
        else:
            align = 'end'
    if align == 'start':
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
        return offset / 2
    else:
        assert align == 'end'
        return offset


def justify_line(context, line, extra_width):
    # TODO: We should use a better algorithm here, see
    # https://www.w3.org/TR/css-text-3/#justify-algos
    if (nb_spaces := count_expandable_spaces(line)):
        add_word_spacing(context, line, extra_width / nb_spaces, 0)


def count_expandable_spaces(box):
    """Count expandable spaces (space and nbsp) for justification."""
    if isinstance(box, boxes.TextBox):
        # TODO: remove trailing spaces correctly
        return box.text.count(' ') + box.text.count('\u00a0')
    elif isinstance(box, (boxes.LineBox, boxes.InlineBox)):
        return sum(count_expandable_spaces(child) for child in box.children)
    else:
        return 0


def add_word_spacing(context, box, justification_spacing, x_advance):
    if isinstance(box, boxes.TextBox):
        box.justification_spacing = justification_spacing
        box.position_x += x_advance
        nb_spaces = count_expandable_spaces(box)
        if nb_spaces > 0:
            layout = create_layout(
                box.text, box.style, context, max_width=None,
                justification_spacing=box.justification_spacing)
            layout.deactivate()
            extra_space = justification_spacing * nb_spaces
            x_advance += extra_space
            box.width += extra_space
            box.pango_layout = layout
    elif isinstance(box, (boxes.LineBox, boxes.InlineBox)):
        box.position_x += x_advance
        previous_x_advance = x_advance
        children = box.children
        if box.style['direction'] == 'rtl':
            children = children[::-1]
        for child in children:
            if child.is_in_normal_flow():
                x_advance = add_word_spacing(
                    context, child, justification_spacing, x_advance)
        box.width += x_advance - previous_x_advance
    else:
        # Atomic inline-level box
        box.translate(x_advance, 0)
    return x_advance


def is_phantom_linebox(linebox):
    # See https://www.w3.org/TR/CSS21/visuren.html#phantom-line-box
    for child in linebox.children:
        if isinstance(child, boxes.InlineBox):
            if not is_phantom_linebox(child):
                return False
            for side in ('top', 'right', 'bottom', 'left'):
                if (getattr(child.style[f'margin_{side}'], 'value', None) or
                        child.style[f'border_{side}_width'] or
                        child.style[f'padding_{side}'].value):
                    return False
        elif child.is_in_normal_flow():
            return False
    return True


def can_break_inside(box):
    # See https://www.w3.org/TR/css-text-3/#white-space-property
    text_wrap = box.style['white_space'] in ('normal', 'pre-wrap', 'pre-line')
    if isinstance(box, boxes.AtomicInlineLevelBox):
        return False
    elif text_wrap and isinstance(box, boxes.TextBox):
        return can_break_text(box.text, box.style['lang'])
    elif text_wrap and isinstance(box, boxes.ParentBox):
        return any(can_break_inside(child) for child in box.children)
    return False
