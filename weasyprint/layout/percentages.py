# coding: utf-8
"""
    weasyprint.layout.percentages
    -----------------------------

    Resolve percentages into fixed values.

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from ..formatting_structure import boxes


def _percentage(value, refer_to):
    """Get the value corresponding to the value/percentage and the reference

    ``refer_to`` is the length for 100%. If ``refer_to`` is not a number, it
    just replaces percentages.

    """
    if value == 'auto':
        result = value
    elif value.unit == 'px':
        result = value.value
    else:
        assert value.unit == '%'
        result = value.value * refer_to / 100.
    return result


def resolve_one_percentage(box, property_name, refer_to):
    """Set a used length value from a computed length value.

    ``refer_to`` is the length for 100%. If ``refer_to`` is not a number, it
    just replaces percentages.

    """
    # box.style has computed values
    value = box.style[property_name]
    # box attributes are used values
    setattr(box, property_name, _percentage(value, refer_to))


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
        height = box.style.height
        if height == 'auto' or height.unit == '%':
            box.height = 'auto'
        else:
            assert height.unit == 'px'
            box.height = height.value
        resolve_one_percentage(box, 'min_height', 0)
        resolve_one_percentage(box, 'max_height', float('inf'))
    else:
        resolve_one_percentage(box, 'height', cb_height)
        resolve_one_percentage(box, 'min_height', cb_height)
        resolve_one_percentage(box, 'max_height', cb_height)

    # Used value == computed value
    for side in ['top', 'right', 'bottom', 'left']:
        prop = 'border_{0}_width'.format(side)
        setattr(box, prop, box.style[prop])

    if box.style.box_sizing == 'border-box':
        if box.width != 'auto':
            box.width -= (box.padding_left + box.padding_right +
                          box.border_left_width + box.border_right_width)
        if box.height != 'auto':
            box.height -= (box.padding_top + box.padding_bottom +
                           box.border_top_width + box.border_bottom_width)
    elif box.style.box_sizing == 'padding-box':
        if box.width != 'auto':
            box.width -= box.padding_left + box.padding_right
        if box.height != 'auto':
            box.height -= box.padding_top + box.padding_bottom
    else:
        assert box.style.box_sizing == 'content-box'


def resolve_radii_percentages(box):
    corners = ('top_left', 'top_right', 'bottom_right', 'bottom_left')
    for corner in corners:
        property_name = 'border_%s_radius' % corner
        rx, ry = box.style[property_name]
        rx = _percentage(rx, box.border_width())
        ry = _percentage(ry, box.border_height())
        setattr(box, property_name, (rx, ry))
