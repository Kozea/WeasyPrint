# coding: utf-8
"""
    weasyprint.formatting_structure
    -------------------------------

    The formatting structure is a tree of boxes. It is either "before layout",
    close to the element tree is it built from, or "after layout", with
    line breaks and page breaks.

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals
