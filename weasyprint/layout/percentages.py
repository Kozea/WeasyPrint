# coding: utf8
"""
    weasyprint.layout.percentages
    -----------------------------

    Resolve percentages into fixed values.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from ..formatting_structure import boxes
from ..css.values import get_percentage_value


def resolve_one_percentage(box, property_name, refer_to,
                           allowed_keywords=None):
    """Set a used length value from a computed length value.

    ``refer_to`` is the length for 100%. If ``refer_to`` is not a number, it
    just replaces percentages.

    """
    # box.style has computed values
    values = box.style[property_name]
    if isinstance(values, (int, float)):
        # Absolute length (was converted to pixels in "computed values")
        result = values
    else:
        percentage = get_percentage_value(values)
        if percentage is not None:
            if isinstance(refer_to, (int, float)):
                # A percentage
                result = percentage * refer_to / 100.
            else:
                # Replace percentages when we have no refer_to that
                # makes sense.
                result = refer_to
        else:
            # Some other values such as 'auto' may be allowed
            result = values
            assert allowed_keywords and result in allowed_keywords
    # box attributes are used values
    setattr(box, property_name, result)


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
    resolve_one_percentage(box, 'margin_left', cb_width, ['auto'])
    resolve_one_percentage(box, 'margin_right', cb_width, ['auto'])
    resolve_one_percentage(box, 'margin_top', maybe_height, ['auto'])
    resolve_one_percentage(box, 'margin_bottom', maybe_height, ['auto'])
    resolve_one_percentage(box, 'padding_left', cb_width)
    resolve_one_percentage(box, 'padding_right', cb_width)
    resolve_one_percentage(box, 'padding_top', maybe_height)
    resolve_one_percentage(box, 'padding_bottom', maybe_height)
    resolve_one_percentage(box, 'width', cb_width, ['auto'])
    # Not supported yet:
#    resolve_one_percentage(box, 'min_width', cb_width)
#    resolve_one_percentage(box, 'max_width', cb_width, ['none'])

    # XXX later: top, bottom, left and right on positioned elements

    if cb_height == 'auto':
        # Special handling when the height of the containing block
        # depends on its content.
        resolve_one_percentage(box, 'height', 'auto', ['auto'])
        # Not supported yet, but min_height is used for margin collapsing.
        resolve_one_percentage(box, 'min_height', 0)
#        resolve_one_percentage(box, 'max_height', None, ['none'])
    else:
        resolve_one_percentage(box, 'height', cb_height, ['auto'])
        # Not supported yet, but min_height is used for margin collapsing.
        resolve_one_percentage(box, 'min_height', cb_height)
#        resolve_one_percentage(box, 'max_height', cb_height, ['none'])

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
    else:
        assert box.style.box_sizing == 'content-box'
