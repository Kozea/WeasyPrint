# coding: utf8
"""
    weasyprint.css.values
    ---------------------

    Utility function to work with tinycss tokens.

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
        if value.type == 'IDENT':
            return value.value


def get_percentage_value(value):
    """If ``value`` is a percentage, return its value.

    Otherwise return ``None``.

    """
    if getattr(value, 'type', 'other') == 'PERCENTAGE':
        return value.value
    else:
        # Not a percentage
        return None


class FakePercentage(object):
    type = 'PERCENTAGE'

    def __init__(self, value):
        self.value = value
        self.as_css = '{}%'.format(value)

make_percentage_value = FakePercentage
