# coding: utf8
"""
    weasyprint.css.values
    ---------------------

    Utility function to work with cssutils :class:`Value` and
    :class:`PropertyValue` objects.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

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
    return FakeValue('PERCENTAGE', value, '{0}%'.format(value))
