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
Functions resolving percentages.

"""

from __future__ import division

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
        # Not supported yet:
#        resolve_one_percentage(box, 'min_height', 0)
#        resolve_one_percentage(box, 'max_height', None, ['none'])
    else:
        resolve_one_percentage(box, 'height', cb_height, ['auto'])
        # Not supported yet:
#        resolve_one_percentage(box, 'min_height', cb_height)
#        resolve_one_percentage(box, 'max_height', cb_height, ['none'])

    # Used value == computed value
    for side in ['top', 'right', 'bottom', 'left']:
        prop = 'border_{}_width'.format(side)
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
