"""Resolve percentages into fixed values."""

from math import inf

from ..css import resolve_math
from ..css.functions import check_math
from ..formatting_structure import boxes


def percentage(value, computed, refer_to):
    """Return the percentage of the reference value, or the value unchanged.

    ``refer_to`` is the length for 100%.

    """
    if check_math(value):
        value = resolve_math(value, computed, refer_to=refer_to)
    if value is None or value == 'auto':
        return value
    elif value.unit.lower() == 'px':
        return value.value
    else:
        assert value.unit == '%'
        return refer_to * value.value / 100


def resolve_one_percentage(box, property_name, refer_to):
    """Set a used length value from a computed length value.

    ``refer_to`` is the length for 100%. If ``refer_to`` is not a number, it
    just replaces percentages.

    """
    # box.style has computed values
    value = box.style[property_name]
    # box attributes are used values
    percent = percentage(value, box.style, refer_to)
    setattr(box, property_name, percent)
    if property_name in ('min_width', 'min_height') and percent == 'auto':
        setattr(box, property_name, 0)


def resolve_position_percentages(box, containing_block):
    cb_width, cb_height = containing_block
    resolve_one_percentage(box, 'left', cb_width)
    resolve_one_percentage(box, 'right', cb_width)
    resolve_one_percentage(box, 'top', cb_height)
    resolve_one_percentage(box, 'bottom', cb_height)


def resolve_percentages(box, containing_block):
    """Set used values as attributes of the box object."""
    if isinstance(containing_block, boxes.Box):
        # cb is short for containing block
        cb_width = containing_block.width
        cb_height = containing_block.height
    else:
        cb_width, cb_height = containing_block
    if isinstance(box, boxes.PageBox):
        maybe_height = cb_height
    else:
        maybe_height = cb_width
    resolve_one_percentage(box, 'margin_left', cb_width)
    resolve_one_percentage(box, 'margin_right', cb_width)
    resolve_one_percentage(box, 'margin_top', maybe_height)
    resolve_one_percentage(box, 'margin_bottom', maybe_height)
    resolve_one_percentage(box, 'padding_left', cb_width)
    resolve_one_percentage(box, 'padding_right', cb_width)
    resolve_one_percentage(box, 'padding_top', maybe_height)
    resolve_one_percentage(box, 'padding_bottom', maybe_height)
    resolve_one_percentage(box, 'width', cb_width)
    resolve_one_percentage(box, 'min_width', cb_width)
    resolve_one_percentage(box, 'max_width', cb_width)

    # XXX later: top, bottom, left and right on positioned elements

    if cb_height == 'auto':
        # Special handling when the height of the containing block
        # depends on its content.
        height = box.style['height']
        if height == 'auto' or check_math(height) or height.unit == '%':
            box.height = 'auto'
        else:
            assert height.unit.lower() == 'px'
            box.height = height.value
        resolve_one_percentage(box, 'min_height', 0)
        resolve_one_percentage(box, 'max_height', inf)
    else:
        resolve_one_percentage(box, 'height', cb_height)
        resolve_one_percentage(box, 'min_height', cb_height)
        resolve_one_percentage(box, 'max_height', cb_height)

    collapse = box.style['border_collapse'] == 'collapse'
    # Used value == computed value
    for side in ('top', 'right', 'bottom', 'left'):
        prop = f'border_{side}_width'
        # border-{side}-width would have been resolved
        # during border conflict resolution for collapsed-borders
        if not (collapse and hasattr(box, prop)):
            setattr(box, prop, box.style[prop])

    # Shrink *content* widths and heights according to box-sizing
    adjust_box_sizing(box, 'width')
    adjust_box_sizing(box, 'height')


def resolve_radii_percentages(box):
    for corner in ('top_left', 'top_right', 'bottom_right', 'bottom_left'):
        property_name = f'border_{corner}_radius'
        computed = box.style[property_name]
        rx, ry = computed

        # Short track for common case
        if (0, 'px') in (rx, ry):
            setattr(box, property_name, (0, 0))
            continue

        for side in corner.split('_'):
            if side in box.remove_decoration_sides:
                setattr(box, property_name, (0, 0))
                break
        else:
            rx = percentage(rx, box.style, box.border_width())
            ry = percentage(ry, box.style, box.border_height())
            setattr(box, property_name, (rx, ry))


def adjust_box_sizing(box, axis):
    if box.style['box_sizing'] == 'border-box':
        if axis == 'width':
            delta = (
                box.padding_left + box.padding_right +
                box.border_left_width + box.border_right_width)
        else:
            delta = (
                box.padding_top + box.padding_bottom +
                box.border_top_width + box.border_bottom_width)
    elif box.style['box_sizing'] == 'padding-box':
        if axis == 'width':
            delta = box.padding_left + box.padding_right
        else:
            delta = box.padding_top + box.padding_bottom
    else:
        assert box.style['box_sizing'] == 'content-box'
        delta = 0

    # Keep at least min_* >= 0 to prevent funny output in case box.width or
    # box.height become negative.
    # Restricting max_* seems reasonable, too.
    if delta > 0:
        if getattr(box, axis) != 'auto':
            setattr(box, axis, max(0, getattr(box, axis) - delta))
        setattr(box, f'max_{axis}', max(0, getattr(box, f'max_{axis}') - delta))
        if getattr(box, f'min_{axis}') != 'auto':
            setattr(box, f'min_{axis}', max(0, getattr(box, f'min_{axis}') - delta))
