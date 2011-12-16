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


import collections


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


def get_percentage_value(value):
    """If ``value`` is a percentage, return its value.

    Otherwise return ``None``.

    """
    if getattr(value, 'type', 'other') == 'PERCENTAGE':
        # cssutils promises that `DimensionValue.value` is an int or float
        assert isinstance(value.value, (int, float))
        return value.value
    else:
        # Not a percentage
        return None


def as_css(values):
    """Return the string reperesentation of the ``values`` list."""
    return ' '.join(getattr(value, 'cssText', value) for value in values)


FakeValue = collections.namedtuple('FakeValue', ('type', 'value', 'cssText'))


def make_percentage_value(value):
    """Return an object that ``get_percentage_value()`` will accept."""
    return FakeValue('PERCENTAGE', value, '{}%'.format(value))
