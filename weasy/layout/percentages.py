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


from ..css.utils import get_single_keyword
from ..formatting_structure import boxes


def pixel_value(value):
    """
    Return the numeric value of a pixel length or None.
    """
    if len(value) == 1 and value[0].type == 'DIMENSION' \
            and value[0].dimension == 'px':
        # cssutils promises that `DimensionValue.value` is an int or float
        assert isinstance(value[0].value, (int, float))
        return value[0].value
    # 0 may not have a units
    elif len(value) == 1 and value[0].value == 0:
        return 0
    else:
        # Not a pixel length
        return None


def percentage_value(value):
    """
    Return the numeric value of a percentage or None.
    """
    if len(value) == 1 and value[0].type == 'PERCENTAGE': \
        # cssutils promises that `DimensionValue.value` is an int or float
        assert isinstance(value[0].value, (int, float))
        return value[0].value
    else:
        # Not a percentage
        return None


def resolve_one_percentage(box, property_name, refer_to):
    """
    Set a used length value from a computed length value.
    `refer_to` is the length for 100%.
    """
    # box.style has computed values
    values = box.style[property_name]
    pixels = pixel_value(values)
    if pixels is not None:
        # Absolute length (was converted to pixels in "computed values")
        result = pixels
    else:
        percentage = percentage_value(values)
        if percentage is not None:
            # A percentage
            result = percentage * refer_to / 100.
        else:
            result = get_single_keyword(values)
            # Other than that, only 'auto' is allowed
            # TODO: it is only allowed on some properties. Check this here?
            assert result == 'auto'
    # box attributes are used values
    setattr(box, property_name.replace('-', '_'), result)


def resolve_percentages(box):
    """
    Set used values as attributes of the box object.
    """
    # cb = containing block
    cb_width, cb_height = box.containing_block_size()
    # TODO: background-position?
    for prop in ['margin-left', 'margin-right',
                 'padding-left', 'padding-right',
                 'text-indent', 'width', 'min-width']:
        resolve_one_percentage(box, prop, cb_width)
    # XXX later: top, bottom, left and right on positioned elements

    for prop in ['margin-top', 'margin-bottom',
                 'padding-top', 'padding-bottom']:
        if isinstance(box, boxes.PageBox):
            resolve_one_percentage(box, prop, cb_height)
        else:
            resolve_one_percentage(box, prop, cb_width)

    if box.style.max_width == 'none':
        box.max_width = None
    else:
        resolve_one_percentage(box, 'max-width', cb_width)

    if cb_height is None:
        # Special handling when the height of the containing block is not
        # known yet.
        box.min_height = 0
        box.max_height = None
        box.height = 'auto'
    else:
        if box.style.max_height == 'none':
            box.max_height = None
        else:
            resolve_one_percentage(box, 'max-height', cb_height)
        resolve_one_percentage(box, 'min-height', cb_height)
        resolve_one_percentage(box, 'height', cb_height)

    # Used value == computed value
    box.border_top_width = box.style.border_top_width
    box.border_right_width = box.style.border_right_width
    box.border_bottom_width = box.style.border_bottom_width
    box.border_left_width = box.style.border_left_width
