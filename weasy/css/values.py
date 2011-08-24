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
Utility functions and methods used by various modules in the css package.

"""

from cssutils.css import Value, DimensionValue


def get_keyword(value):
    """If ``value`` is a keyword, return its name.

    Otherwise return ``None``.

    """
    if value.type == 'IDENT':
        return value.value


def get_single_keyword(values):
    """If ``values`` is a 1-element list of keywords, return its name.

    Otherwise return ``None``.

    """
    # Fast but unsafe, as it depends on private attributes
    if len(values) == 1:
        value = values[0]
        if value._type == 'IDENT':
            return value._value


def get_pixel_value(value):
    """If ``value`` is a pixel length, return its value.

    Otherwise return ``None``.

    """
    value_type = value.type
    value_value = value.value
    if ((value_type == 'DIMENSION' and value.dimension == 'px') or
            # Units may be ommited on 0
            (value_type == 'NUMBER' and value_value == 0)):
        # cssutils promises that `DimensionValue.value` is an int or float
        assert isinstance(value_value, (int, float))
        return value_value
    else:
        # Not a pixel length
        return None


def get_single_pixel_value(values):
    """If ``values`` is a 1-element list of pixel lengths, return its value.

    Otherwise return ``None``.

    """
    if len(values) == 1:
        return get_pixel_value(values[0])


def get_percentage_value(value):
    """If ``value`` is a percentage, return its value.

    Otherwise return ``None``.

    """
    if value.type == 'PERCENTAGE':
        # cssutils promises that `DimensionValue.value` is an int or float
        assert isinstance(value.value, (int, float))
        return value.value
    else:
        # Not a percentage
        return None


def get_single_percentage_value(values):
    """If ``values`` is a 1-element list of percentages, return its value.

    Otherwise return ``None``.

    """
    if len(values) == 1:
        return get_percentage_value(values[0])


def make_pixel_value(pixels):
    """Make a pixel :class:`DimensionValue`.

    Reverse of :func:`get_single_pixel_value`.

    """
    value = DimensionValue()
    value._value = pixels
    value._dimension = 'px'
    value._type = 'DIMENSION'
    return value


def make_number(number):
    """Make a number :class:`DimensionValue`."""
    value = DimensionValue()
    value._value = number
    value._type = 'NUMBER'
    return value


def make_keyword(keyword):
    """Make a keyword :class:`Value`.

    Reverse of :func:`get_keyword`.

    """
    value = Value()
    value._value = keyword
    value._type = 'IDENT'
    return value


def as_css(values):
    """Return the string reperesentation of the ``values`` list."""
    return ' '.join(value.cssText for value in values)
