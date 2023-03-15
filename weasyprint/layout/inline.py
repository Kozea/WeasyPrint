"""Layout for inline-level boxes."""

from collections import namedtuple
import unicodedata
from math import inf

from ..css import computed_from_cascaded
from ..css.computed_values import character_ratio, strut_layout
from ..formatting_structure import boxes
from ..text.constants import PANGO_STRETCH, PANGO_STYLE
from ..text.ffi import (
    ffi, gobject, glist_to_list, harfbuzz, pango, PANGO_SCALE, pangoft2,
    unicode_to_char_p)
from ..text.line_break import (
    can_break_text, create_layout, pango_attrs_from_style, split_first_line,
    shape_string)
from .absolute import AbsolutePlaceholder, absolute_layout
from .flex import flex_layout
from .float import avoid_collisions, float_layout
from .leader import handle_leader
from .min_max import handle_min_max_width
from .percent import resolve_one_percentage, resolve_percentages
from .preferred import (
    inline_min_content_width, shrink_to_fit, trailing_whitespace_size)
from .replaced import inline_replaced_box_layout
from .table import find_in_flow_baseline, table_wrapper_width


AtomicBoxRecord = namedtuple('AtomicBoxRecord', 'position box')

LinePosition = namedtuple(
    'LinePosition',
    'char_index width_no_spaces child_index shaping_index glyph_index ' \
    'atomic_index is_glyph_start')


def iter_line_boxes(context, box, position_y, bottom_space, skip_stack,
                    containing_block, absolute_boxes, fixed_boxes,
                    first_letter_style):
    """Return an iterator of ``(line, resume_at)``.

    ``line`` is a laid-out LineBox with as much content as possible that
    fits in the available width.

    """
    resolve_percentages(box, containing_block)
    if skip_stack is None:
        # TODO: wrong, see https://github.com/Kozea/WeasyPrint/issues/679
        resolve_one_percentage(box, 'text_indent', containing_block.width)
    else:
        box.text_indent = 0
    while True:
        if not hasattr(box, 'shaping_string'):
            box.shaping_string = get_shaping_string(context, box)
            num_log_attrs = len(box.shaping_string) + 1
            box.log_attrs = ffi.new(f'PangoLogAttr[{num_log_attrs}]')

            shaping_utf8_ptr, shaping_utf8_length, _items, \
                box.shaping_results = shape_string(context, box.style, \
                box.shaping_string, box.pango_attrs)

            pango.pango_default_break(
                shaping_utf8_ptr, shaping_utf8_length, ffi.NULL,
                ffi.cast('PangoLogAttr *', box.log_attrs), num_log_attrs)

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
    # TODO: Given shaping_string, we should probably handle this separately
    # somehow:
    # skip_stack = skip_first_whitespace(linebox, skip_stack)
    # if skip_stack == 'continue':
    #     return None, None

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

        # TODO: Figure out how to handle this.
        # remove_last_whitespace(context, line)

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
        # See https://github.com/Kozea/WeasyPrint/issues/583
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
            context.broken_out_of_flow.append(
                (waiting_float, containing_block, waiting_float_resume_at))
    if float_children:
        line.children += tuple(float_children)

    return line, resume_at


def get_shaping_string(context, box, start_position = 0):
    """Returns a Unicode string containing the content from this LineBox.

    This largely relies on InlineLevelBoxes building their own Unicode strings
    and returning them, but it should assemble a string containing Unicode text
    representing the content that should be set as part of this line.

    Notably, atomic boxes (display: inline-block) or replaced boxes (<img>,
    etc.) do not have their content represented here as text, as they are set
    separately. Instead, their content should be represented here as a single
    U+FFFC, the Unicode "Object Replacement Character", to ensure that text on
    either side of such boxes does not get shaped together. This is also
    appropriate for line-breaking behavior (see
    http://www.w3.org/TR/css3-text/#line-break-details).
    """
    atomic_boxes = []
    pango_attrs = []

    if isinstance(box, boxes.TextBox):
        text = box.text
        pango_attrs = pango_attrs_from_style(
            context, box.style, start_position, start_position + len(text))
    elif not isinstance(box, boxes.AtomicInlineLevelBox):
        # Handle these recursively.
        strings = []
        position = start_position

        # TODO: add U+FFFC on the appropriate (bidi!) side if there is
        # padding/margin/border.

        for child in box.children:
            strings.append(get_shaping_string(context, child, position))
            atomic_boxes.extend(child.atomic_boxes)
            pango_attrs.extend(child.pango_attrs)
            position = child.shaping_range[1]

        text = ''.join(strings)
    else:
        text = '\ufffc'
        atomic_boxes.append(AtomicBoxRecord(start_position, box))

    box.shaping_range = (start_position, start_position + len(text))
    box.atomic_boxes = atomic_boxes
    box.pango_attrs = pango_attrs

    return text


def skip_first_whitespace(box, skip_stack):
    """Return ``skip_stack`` to start just after removable leading spaces.

    See http://www.w3.org/TR/CSS21/text.html#white-space-model

    """
    if skip_stack is None:
        index = 0
        next_skip_stack = None
    else:
        (index, next_skip_stack), = skip_stack.items()

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


def remove_last_whitespace(context, box):
    """Remove in place space characters at the end of a line.

    This also reduces the width and position of the inline parents of the
    modified text.

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

        # RTL line, the trailing space is at the left of the box. We have to
        # translate the box to align the stripped text with the right edge of
        # the box.
        if new_box.pango_layout.first_line_direction % 2:
            box.position_x -= space_width
            for ancestor in ancestors:
                ancestor.position_x -= space_width
    else:
        space_width = box.width
        box.width = 0
        box.text = ''

        # RTL line, the textbox with a trailing space is now empty at the left
        # of the line. We have to translate the line to align it with the right
        # edge of the box.
        line = ancestors[0]
        if line.style['direction'] == 'rtl':
            line.translate(dx=-space_width, ignore_floats=True)

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
                box.children = (
                    (letter_box,) + tuple(box.children[1:]))
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
                        box.children = (letter_box,) + tuple(box.children)
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
                        box.children = (letter_box,) + tuple(box.children)
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
        box = inline_block_box_layout(
            context, box, position_x, skip_stack, containing_block,
            absolute_boxes, fixed_boxes)
    else:  # pragma: no cover
        raise TypeError(f'Layout for {type(box).__name__} not handled yet')
    return box


def inline_block_box_layout(context, box, position_x, skip_stack,
                            containing_block, absolute_boxes, fixed_boxes):
    from .block import block_container_layout

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

    http://www.w3.org/TR/CSS21/visudet.html#propdef-vertical-align

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
        #box.width = shrink_to_fit(context, box, available_content_width)
        # TODO: Fix layout/preferred.py's inline_min_content_width to not
        # eventually call split_first_line, and use the line above instead.
        box.width = 33


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
        for side in ['top', 'right', 'bottom', 'left']:
            if getattr(box, f'margin_{side}') == 'auto':
                setattr(box, f'margin_{side}', 0)
        new_box, resume_at, _, _, _ = flex_layout(
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
                context.broken_out_of_flow.append(
                    (child, containing_block, float_resume_at))
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


def slice_box_tree(box, start, end, parent_linebox, position_x, widths,
    replaced_atomic_boxes, width_offset):
    """
    Returns a tree of elements cut to the specified range of shaping ranges.
    """
    assert box.shaping_range[0] <= start
    assert box.shaping_range[1] >= end

    # TextBoxes can't be manipulated in many of the normal ways.
    if isinstance(box, boxes.TextBox):
        new_box = box.copy()
        if start == width_offset:
            start_width = 0
        else:
            start_width = widths[start - width_offset]
        new_box.width = widths[end - width_offset] - start_width
    elif isinstance(box, boxes.AtomicInlineLevelBox):
        # We don't have to copy here, as this is regenerated each time we might
        # possibly call this function.
        # print(box, replaced_atomic_boxes)
        new_box = replaced_atomic_boxes[start]
    else:
        new_box = box.copy_with_children([])
        new_box.remove_decoration(
            start=not (box.shaping_range[0] == start),
            end=not box.shaping_range[1] == end)

    new_box.parent_linebox = parent_linebox
    new_box.translate(position_x, 0)
    new_box.render_range = (
        max(start, box.shaping_range[0]),
        min(end, box.shaping_range[1]))

    if isinstance(box, (boxes.AtomicInlineLevelBox, boxes.TextBox)):
        return new_box

    # Trim all sub-ranges, as appropriate.
    new_box.children = []
    next_x = position_x
    for child in box.children:
        if child.shaping_range[1] <= start:
            continue
        if child.shaping_range[0] > end:
            break

        child_start = max(start, child.shaping_range[0])
        child_end = min(end, child.shaping_range[1])

        new_child = slice_box_tree(
                child, child_start, child_end, parent_linebox, next_x, widths,
                replaced_atomic_boxes, width_offset)

        new_box.children.append(new_child)

        next_x = new_child.position_x + new_child.width

    new_box.width = next_x - position_x

    return new_box


def apply_inline_box_sizes(context, box):
    """Sets position and size attributes on boxes in a LineBox."""
    if isinstance(box, boxes.TextBox):
        # TODO: actually calculate these values
        box.border_top_width = box.border_bottom_width = 0
        box.border_left_width = box.border_right_width = 0
        # TODO: should we be setting these here?
        box.padding_top = box.padding_bottom = 0
        box.padding_left = box.padding_right = 0
        box.margin_top = box.margin_bottom = 0
        box.margin_left = box.margin_right = 0

        line_height, box.baseline = strut_layout(box.style, context)
        box.height = box.style['font_size']
        half_leading = (line_height - box.height) / 2
        # Set margins to the half leading but also compensate for borders and
        # paddings. We want margin_height() == line_height
        box.margin_top = (
            half_leading - box.border_top_width - box.padding_top)
        box.margin_bottom = (
            half_leading - box.border_bottom_width - box.padding_bottom)

    elif isinstance(box, boxes.AtomicInlineLevelBox):
        # TODO: process the child here
        for child in box.children:
            apply_inline_box_sizes(context, child)
        # TODO: surely this is incorrect / could be faster
        box.baseline = max(child.baseline for child in box.children)
        box.height = max(child.height for child in box.children)
        # TODO: should we be setting these here?
        box.padding_top = box.padding_bottom = 0
        box.padding_left = box.padding_right = 0
        box.border_top_width = box.border_bottom_width = 0
        box.border_left_width = box.border_right_width = 0
        box.margin_top = box.margin_bottom = 0
        box.margin_left = box.margin_right = 0
    else:
        for child in box.children:
            apply_inline_box_sizes(context, child)
        # TODO: surely this is incorrect / could be faster
        box.baseline = max(child.baseline for child in box.children)
        box.height = max(child.height for child in box.children)
        # box.width = sum(child.width if hasattr(child, 'width') else 0 for child in box.children)

        if not isinstance(box, boxes.LineBox):
            # TODO: should we be setting these here?
            box.padding_top = box.padding_bottom = 0
            box.padding_left = box.padding_right = 0
            box.border_top_width = box.border_bottom_width = 0
            box.border_left_width = box.border_right_width = 0
            box.margin_top = box.margin_bottom = 0
            box.margin_left = box.margin_right = 0


def split_inline_box(context, box, position_x, max_x, bottom_space, skip_stack,
                     containing_block, absolute_boxes, fixed_boxes,
                     line_placeholders, waiting_floats, line_children):
    """Same behavior as split_inline_level."""

    # TODO: use pango_tailor_break and pango_attr_break as well.

    # In some cases (shrink-to-fit result being the preferred width)
    # max_x is coming from Pango itself,
    # but floating point errors have accumulated:
    #   width2 = (width + X) - X   # in some cases, width2 < width
    # Increase the value a bit to compensate and not introduce
    # an unexpected line break. The 1e-9 value comes from PEP 485.
    max_x *= 1 + 1e-9
    log_attrs = box.log_attrs
    first_char = 0 if skip_stack is None else skip_stack[0]
    first_glyph = 0 if skip_stack is None else skip_stack[1]
    first_child_index = 0 if skip_stack is None else skip_stack[2]
    first_shaping_index = 0 if skip_stack is None else skip_stack[3]
    atomic_index = 0 if skip_stack is None else skip_stack[4]
    if atomic_index < len(box.atomic_boxes):
        next_atomic_char = box.atomic_boxes[atomic_index].position
    else:
        next_atomic_char = None
    last_break = None
    is_start = skip_stack is None
    is_end = False
    max_width = (max_x - position_x) * PANGO_SCALE
    char_index = first_char # The *character* position in the shaping string.
    glyph_index = first_glyph # The *glyph* position in the shaping result
    width = 0           # The width of this line, in Pango units
    width_no_spaces = 0 # Width of this line without ignorable trailing space
    line_positions = [] # Some LinePosition objects on this line
    wrap_opportunity = False # The line_positions index we can wrap at
    child_index = first_child_index
    current_child = box.children[child_index]
    shaping_index = first_shaping_index
    shaping = box.shaping_results[shaping_index]
    cumulative_widths = []
    replaced_atomic_boxes = {}

    # Loop over positions in this string trying to find the next position to
    # break at.

    # This iteration is tricky: to determine width, we have to iterate over
    # glyphs from Harfbuzz, but we also need to know if we can break at a given
    # location, and that information comes from Pango and is based on
    # characters. Harfbuzz may produce more than one glyph per character (via a
    # substitution, for example), or may produce one glyph for several
    # characters (like a ligature).

    # Harfbuzz tracks the lowest character index it used in a glyph, which we
    # can use to determine which characters created a glyph (namely, those with
    # the index of the "cluster" identifier on the glyph, through those with
    # the index of the cluster identifier from the glyph with the next highest
    # one, or the end of the string if there is no such glyph). However, we
    # can't just check Pango when we *finish* a glyph (or cluster thereof with
    # the same cluster index): we may want to break in the middle of a
    # ligature, for example a ligature for "hello world" could be split at the
    # space. If that happens, we need to re-shape with the break and try again.
    # On the other hand, even if a character is composed of several glyphs, we
    # can't really split it between them, so all we really need to track are
    # character locations. Additionally, we only have to track character
    # positions that we could break at without extra trouble. Therefore, we
    # could add entries to line_positions when we are at a character that is
    # breakable without additional complications (where we don't have to look
    # for a hyphenation point or add extra characters, which we'll handle in a
    # separate process).

    # TODO: For now, we actually add *every* "end of character/glyph" position
    # to line_positions, which is wasteful and makes it harder to backtrack to
    # the last word break position.
    while True:
        # print('Shaping range:', char_index, current_child.shaping_range,
        #     f'starting "{box.shaping_string[char_index]}"')
        # TODO: check for atomic inlines

        # When we reach the top of this loop, we're at the beginning of both a
        # new character and a new glyph.

        # Add this glyph to the width.
        glyphs_start_cluster = char_index
        prev_glyph_index = glyph_index
        while glyph_index < len(shaping.glyph_infos) and \
            shaping.glyph_infos[glyph_index].cluster == glyphs_start_cluster:

            # If this is an atomic box, set it and use its width data.
            # Because this can depend on its horizontal position, we have to do
            # it here, although in some cases that means we may calculate the
            # width of the atomic inline multiple times (if it is near the end
            # of a line).
            if next_atomic_char == char_index:
                old_box = box.atomic_boxes[atomic_index].box
                new_box = atomic_box(context, old_box, 0, None,
                    containing_block, absolute_boxes, fixed_boxes)
                replaced_atomic_boxes[char_index] = new_box

                atomic_index += 1
                if atomic_index < len(box.atomic_boxes):
                    next_atomic_char = box.atomic_boxes[atomic_index].position
                else:
                    next_atomic_char = None

                glyph_width = new_box.width * PANGO_SCALE
                char_index += 1
            else:
                glyph_width = shaping.glyph_positions[glyph_index].x_advance

            width += glyph_width
            glyph_index += 1

        if glyph_index == len(shaping.glyph_infos):
            glyphs_end_cluster = shaping.end + 1
        else:
            glyphs_end_cluster = shaping.glyph_infos[glyph_index].cluster

        while char_index < glyphs_end_cluster:
            # TODO: handle cases where we must preserve whitespace
            if log_attrs[char_index].is_white == 0:
                width_no_spaces = width
                if char_index > 0 and log_attrs[char_index - 1].is_white == 1 \
                    and char_index > first_char:
                    wrap_opportunity = len(line_positions)

            # TODO: theoretically, a Pango-approved line breaking opportunity
            # could occur in the middle of a ligature'd glyph. This is
            # unlikely, but we should consider handling it.
            cumulative_widths.append(width / PANGO_SCALE)
            char_index += 1

        # We subtract 1 from char_index here because the loop above has
        # incremented it past the end of the current cluster. (And we don't do
        # this inside the loop because we don't currently support splitting a
        # line inside a glyph cluster, even if it is multiple characters.)
        line_positions.append(LinePosition(
            char_index - 1, width_no_spaces, child_index, shaping_index,
            glyph_index - 1, atomic_index,
            glyphs_start_cluster == char_index - 1))

        # TODO: handle hyphenation (including soft hyphens)

        # TODO: handle text-overflow: ellipsis / block-ellipsis != none
        # https://www.w3.org/TR/css-overflow-3/

        # TODO: handle cases where ellipsis / hyphen isn't in the current font
        # (may have to go back to Pango to shape it? may always have to, to
        # figure out the ideal font for it given the current style?)

        # TODO: handle character-by-character breaking (both cases!)
        if width > max_width:
            if not wrap_opportunity:
                wrap_opportunity = len(line_positions) - 1
            break

        if char_index >= len(box.shaping_string):
            is_end = True
            break

        if char_index >= shaping.end:
            shaping_index += 1
            shaping = box.shaping_results[shaping_index]
            char_index = shaping.start
            glyph_index = 0

        if char_index >= current_child.shaping_range[1]:
            child_index += 1
            current_child = box.children[child_index]

        # TODO: What about break_removes_preceding or break_inserts_hyphen?

    if is_end:
        break_pos = line_positions[-1]
    else:
        break_pos = line_positions[wrap_opportunity]
    last_char = break_pos.char_index

    # TODO: It's not okay to just arbitrarily slice glyphs apart here, they may
    # require reshaping. See HB_GLYPH_FLAG_UNSAFE_TO_CONCAT in
    # https://harfbuzz.github.io/harfbuzz-hb-buffer.html#hb-glyph-flags-t for a
    # reasonable algorithm for handling the splitting, but we theoretically
    # should handle any reshaping, then check the width to make sure we haven't
    # gone over our maximum width (and fall back to hyphenating or cutting off
    # this word if we did).

    new_box = slice_box_tree(
        box, first_char, last_char, box, position_x, cumulative_widths,
        replaced_atomic_boxes, first_char)

    apply_inline_box_sizes(context, new_box)

    new_box.position_x = 0

    # Returns (new_box, resume_at, preserved_line_break, first_letter,
    #     last_letter, float_widths)
    # ``resume_at`` is ``None`` if all of the content fits. Otherwise it can be
    # passed as a ``skip_stack`` parameter to resume where we left off.
    # TODO: Calculate float widths
    if last_char < len(box.shaping_string):# and last_char < 100:
        resume_at = (break_pos.char_index, break_pos.glyph_index,
            break_pos.child_index, break_pos.shaping_index,
            break_pos.atomic_index)
    else:
        resume_at = None
    return (new_box, resume_at, False, None, None, {'left': 0, 'right': 0})


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
    text = box.text[skip:]
    if font_size == 0 or not text:
        return None, None, False
    layout, length, resume_index, width, height, baseline = split_first_line(
        text, box.style, context, available_width, box.justification_spacing,
        is_line_start=is_line_start)
    assert resume_index != 0

    # Convert ``length`` and ``resume_at`` from UTF-8 indexes in text
    # to Unicode indexes.
    # No need to encode what’s after resume_at (if set) or length (if
    # resume_at is not set). One code point is one or more byte, so
    # UTF-8 indexes are always bigger or equal to Unicode indexes.
    new_text = layout.text
    encoded = text.encode()
    if resume_index is not None:
        between = encoded[length:resume_index].decode()
        resume_index = len(encoded[:resume_index].decode())
    length = len(encoded[:length].decode())

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
        preserved_line_break = (
            (length != resume_index) and between.strip(' '))
        if preserved_line_break:
            # See http://unicode.org/reports/tr14/
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
    # See http://www.w3.org/TR/CSS21/visuren.html#phantom-line-box
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
