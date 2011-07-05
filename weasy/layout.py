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


from .formatting_structure import boxes
from .utils import MultiFunction
from .css import computed_values


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


@MultiFunction
def compute_dimensions(box):
    """
    Computes width, height and absolute position for all boxes in a box tree.
    """


@compute_dimensions.register(boxes.PageBox)
def page_dimensions(box, width=None, height=None):
    # Page size is fixed to A4 for now. TODO: implement the size property.
    if width is None:
        box.outer_width = 210 * computed_values.LENGTHS_TO_PIXELS['mm']
    else:
        box.outer_width = width

    if height is None:
        box.outer_height = 297 * computed_values.LENGTHS_TO_PIXELS['mm']
    else:
        box.outer_height = height

    for sides, hundred_percent in [(['top', 'bottom'], box.outer_height),
                                   (['left', 'right'], box.outer_width)]:
        for side in sides:
            value = box.style['margin-' + side]
            pixels = pixel_value(value)
            if pixels is None:
                percentage = percentage_value(value)
                if percentage is None:
                    assert value.value == 'auto'
                    pixels = 0
                else:
                    pixels = percentage * hundred_percent / 100.
            setattr(box, 'margin_' + side, pixels)

    box.position_x = box.margin_left
    box.position_y = box.margin_top
    box.width = box.outer_width - box.margin_left - box.margin_right
    box.height = box.outer_height - box.margin_top - box.margin_bottom

    for child in box.children:
        compute_dimensions(child)


@compute_dimensions.register(boxes.BlockBox)
def block_dimensions(box):
    pass
