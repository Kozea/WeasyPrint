"""Absolutely positioned boxes management."""

from ..formatting_structure import boxes
from .min_max import handle_min_max_width
from .percent import resolve_percentages, resolve_position_percentages
from .preferred import shrink_to_fit
from .replaced import inline_replaced_box_width_height
from .table import table_wrapper_width


class AbsolutePlaceholder:
    """Left where an absolutely-positioned box was taken out of the flow."""
    def __init__(self, box):
        assert not isinstance(box, AbsolutePlaceholder)
        # Work around the overloaded __setattr__
        object.__setattr__(self, '_box', box)
        object.__setattr__(self, '_layout_done', False)

    def set_laid_out_box(self, new_box):
        object.__setattr__(self, '_box', new_box)
        object.__setattr__(self, '_layout_done', True)

    def translate(self, dx=0, dy=0, ignore_floats=False):
        if dx == dy == 0:
            return
        if self._layout_done:
            self._box.translate(dx, dy, ignore_floats)
        else:
            # Descendants do not have a position yet.
            self._box.position_x += dx
            self._box.position_y += dy

    def copy(self):
        new_placeholder = AbsolutePlaceholder(self._box.copy())
        object.__setattr__(new_placeholder, '_layout_done', self._layout_done)
        return new_placeholder

    # Pretend to be the box itself
    def __getattr__(self, name):
        return getattr(self._box, name)

    def __setattr__(self, name, value):
        setattr(self._box, name, value)

    def __repr__(self):
        return '<Placeholder %r>' % self._box


@handle_min_max_width
def absolute_width(box, context, cb_x, cb_y, cb_width, cb_height):
    # https://www.w3.org/TR/CSS2/visudet.html#abs-replaced-width
    ltr = (
        box.style.parent_style is None or
        box.style.parent_style['direction'] == 'ltr')
    paddings_borders = (
        box.padding_left + box.padding_right +
        box.border_left_width + box.border_right_width)
    translate_x = 0
    translate_box_width = False
    default_translate_x = cb_x - box.position_x

    if box.left == box.right == box.width == 'auto':
        if box.margin_left == 'auto':
            box.margin_left = 0
        if box.margin_right == 'auto':
            box.margin_right = 0
        available_width = cb_width - (
            paddings_borders + box.margin_left + box.margin_right)
        box.width = shrink_to_fit(context, box, available_width)
        if not ltr:
            translate_box_width = True
            translate_x = default_translate_x + available_width
    elif box.left != 'auto' and box.right != 'auto' and box.width != 'auto':
        width_for_margins = cb_width - (
            box.right + box.left + box.width + paddings_borders)
        if box.margin_left == box.margin_right == 'auto':
            if box.width + paddings_borders + box.right + box.left <= cb_width:
                box.margin_left = box.margin_right = width_for_margins / 2
            else:
                box.margin_left = 0 if ltr else width_for_margins
                box.margin_right = width_for_margins if ltr else 0
        elif box.margin_left == 'auto':
            box.margin_left = width_for_margins
        elif box.margin_right == 'auto':
            box.margin_right = width_for_margins
        elif ltr:
            box.margin_right = width_for_margins
        else:
            box.margin_left = width_for_margins
        translate_x = box.left + default_translate_x
    else:
        if box.margin_left == 'auto':
            box.margin_left = 0
        if box.margin_right == 'auto':
            box.margin_right = 0
        spacing = paddings_borders + box.margin_left + box.margin_right
        if box.left == box.width == 'auto':
            box.width = shrink_to_fit(
                context, box, cb_width - spacing - box.right)
            translate_x = cb_width - box.right - spacing + default_translate_x
            translate_box_width = True
        elif box.left == box.right == 'auto':
            if not ltr:
                available_width = cb_width - (
                    paddings_borders + box.margin_left + box.margin_right)
                translate_box_width = True
                translate_x = default_translate_x + available_width
        elif box.width == box.right == 'auto':
            box.width = shrink_to_fit(
                context, box, cb_width - spacing - box.left)
            translate_x = box.left + default_translate_x
        elif box.left == 'auto':
            translate_x = cb_width + default_translate_x - (
                box.right + spacing + box.width)
        elif box.width == 'auto':
            box.width = cb_width - box.right - box.left - spacing
            translate_x = box.left + default_translate_x
        elif box.right == 'auto':
            translate_x = box.left + default_translate_x

    return translate_box_width, translate_x


def absolute_height(box, context, cb_x, cb_y, cb_width, cb_height):
    # https://www.w3.org/TR/CSS2/visudet.html#abs-non-replaced-height
    paddings_borders = (
        box.padding_top + box.padding_bottom +
        box.border_top_width + box.border_bottom_width)
    translate_y = 0
    translate_box_height = False
    default_translate_y = cb_y - box.position_y

    if box.top == box.bottom == box.height == 'auto':
        # Keep the static position
        if box.margin_top == 'auto':
            box.margin_top = 0
        if box.margin_bottom == 'auto':
            box.margin_bottom = 0
    elif 'auto' not in (box.top, box.bottom, box.height):
        height_for_margins = cb_height - (
            box.top + box.bottom + box.height + paddings_borders)
        if box.margin_top == box.margin_bottom == 'auto':
            box.margin_top = box.margin_bottom = height_for_margins / 2
        elif box.margin_top == 'auto':
            box.margin_top = height_for_margins
        elif box.margin_bottom == 'auto':
            box.margin_bottom = height_for_margins
        else:
            box.margin_bottom = height_for_margins
        translate_y = box.top + default_translate_y
    else:
        if box.margin_top == 'auto':
            box.margin_top = 0
        if box.margin_bottom == 'auto':
            box.margin_bottom = 0
        spacing = paddings_borders + box.margin_top + box.margin_bottom
        if box.top == box.height == 'auto':
            translate_y = (
                cb_height - box.bottom - spacing + default_translate_y)
            translate_box_height = True
        elif box.top == box.bottom == 'auto':
            pass  # Keep the static position
        elif box.height == box.bottom == 'auto':
            translate_y = box.top + default_translate_y
        elif box.top == 'auto':
            translate_y = cb_height + default_translate_y - (
                box.bottom + spacing + box.height)
        elif box.height == 'auto':
            box.height = cb_height - box.bottom - box.top - spacing
            translate_y = box.top + default_translate_y
        elif box.bottom == 'auto':
            translate_y = box.top + default_translate_y

    return translate_box_height, translate_y


def absolute_block(context, box, containing_block, fixed_boxes, bottom_space,
                   skip_stack, cb_x, cb_y, cb_width, cb_height):
    from .block import block_container_layout
    from .flex import flex_layout

    translate_box_width, translate_x = absolute_width(
        box, context, cb_x, cb_y, cb_width, cb_height)
    if skip_stack:
        translate_box_height, translate_y = False, 0
    else:
        translate_box_height, translate_y = absolute_height(
            box, context, cb_x, cb_y, cb_width, cb_height)

    bottom_space += -box.position_y if translate_box_height else translate_y

    # This box is the containing block for absolute descendants.
    absolute_boxes = []

    if box.is_table_wrapper:
        table_wrapper_width(context, box, (cb_width, cb_height))

    if isinstance(box, (boxes.BlockBox)):
        new_box, resume_at, _, _, _, _ = block_container_layout(
            context, box, bottom_space, skip_stack, page_is_empty=True,
            absolute_boxes=absolute_boxes, fixed_boxes=fixed_boxes,
            adjoining_margins=None, discard=False, max_lines=None)
    else:
        new_box, resume_at, _, _, _ = flex_layout(
            context, box, bottom_space, skip_stack, containing_block,
            page_is_empty=True, absolute_boxes=absolute_boxes,
            fixed_boxes=fixed_boxes)

    for child_placeholder in absolute_boxes:
        absolute_layout(
            context, child_placeholder, new_box, fixed_boxes, bottom_space,
            skip_stack)

    if translate_box_width:
        translate_x -= new_box.width
    if translate_box_height:
        translate_y -= new_box.height
    new_box.translate(translate_x, translate_y)

    return new_box, resume_at


def absolute_layout(context, placeholder, containing_block, fixed_boxes,
                    bottom_space, skip_stack):
    """Set the width of absolute positioned ``box``."""
    assert not placeholder._layout_done
    box = placeholder._box
    new_box, resume_at = absolute_box_layout(
        context, box, containing_block, fixed_boxes, bottom_space, skip_stack)
    placeholder.set_laid_out_box(new_box)
    if resume_at:
        context.broken_out_of_flow[placeholder] = (
            box, containing_block, resume_at)


def absolute_box_layout(context, box, containing_block, fixed_boxes,
                        bottom_space, skip_stack):
    # TODO: handle inline boxes (point 10.1.4.1)
    # https://www.w3.org/TR/CSS2/visudet.html#containing-block-details
    if isinstance(containing_block, boxes.PageBox):
        cb_x = containing_block.content_box_x()
        cb_y = containing_block.content_box_y()
        cb_width = containing_block.width
        cb_height = containing_block.height
    else:
        cb_x = containing_block.padding_box_x()
        cb_y = containing_block.padding_box_y()
        cb_width = containing_block.padding_width()
        cb_height = containing_block.padding_height()

    resolve_percentages(box, (cb_width, cb_height))
    resolve_position_percentages(box, (cb_width, cb_height))

    context.create_block_formatting_context()
    # Absolute tables are wrapped into block boxes
    if isinstance(box, (boxes.BlockBox, boxes.FlexContainerBox)):
        new_box, resume_at = absolute_block(
            context, box, containing_block, fixed_boxes, bottom_space,
            skip_stack, cb_x, cb_y, cb_width, cb_height)
    else:
        assert isinstance(box, boxes.BlockReplacedBox)
        new_box = absolute_replaced(
            context, box, cb_x, cb_y, cb_width, cb_height)
        resume_at = None
    context.finish_block_formatting_context(new_box)
    return new_box, resume_at


def absolute_replaced(context, box, cb_x, cb_y, cb_width, cb_height):
    inline_replaced_box_width_height(box, (cb_x, cb_y, cb_width, cb_height))
    ltr = (
        box.style.parent_style is None or
        box.style.parent_style['direction'] == 'ltr')

    # https://www.w3.org/TR/CSS21/visudet.html#abs-replaced-width
    if box.left == box.right == 'auto':
        # static position:
        if ltr:
            box.left = box.position_x - cb_x
        else:
            box.right = cb_x + cb_width - box.position_x
    if 'auto' in (box.left, box.right):
        if box.margin_left == 'auto':
            box.margin_left = 0
        if box.margin_right == 'auto':
            box.margin_right = 0
        remaining = cb_width - box.margin_width()
        if box.left == 'auto':
            box.left = remaining - box.right
        if box.right == 'auto':
            box.right = remaining - box.left
    elif 'auto' in (box.margin_left, box.margin_right):
        remaining = cb_width - (box.border_width() + box.left + box.right)
        if box.margin_left == box.margin_right == 'auto':
            if remaining >= 0:
                box.margin_left = box.margin_right = remaining // 2
            else:
                box.margin_left = 0 if ltr else remaining
                box.margin_right = remaining if ltr else 0
        elif box.margin_left == 'auto':
            box.margin_left = remaining
        else:
            box.margin_right = remaining
    else:
        # Over-constrained
        if ltr:
            box.right = cb_width - (box.margin_width() + box.left)
        else:
            box.left = cb_width - (box.margin_width() + box.right)

    # https://www.w3.org/TR/CSS21/visudet.html#abs-replaced-height
    if box.top == box.bottom == 'auto':
        box.top = box.position_y - cb_y
    if 'auto' in (box.top, box.bottom):
        if box.margin_top == 'auto':
            box.margin_top = 0
        if box.margin_bottom == 'auto':
            box.margin_bottom = 0
        remaining = cb_height - box.margin_height()
        if box.top == 'auto':
            box.top = remaining - box.bottom
        if box.bottom == 'auto':
            box.bottom = remaining - box.top
    elif 'auto' in (box.margin_top, box.margin_bottom):
        remaining = cb_height - (box.border_height() + box.top + box.bottom)
        if box.margin_top == box.margin_bottom == 'auto':
            box.margin_top = box.margin_bottom = remaining // 2
        elif box.margin_top == 'auto':
            box.margin_top = remaining
        else:
            box.margin_bottom = remaining
    else:
        # Over-constrained
        box.bottom = cb_height - (box.margin_height() + box.top)

    # No children for replaced boxes, no need to .translate()
    box.position_x = cb_x + box.left
    box.position_y = cb_y + box.top
    return box
