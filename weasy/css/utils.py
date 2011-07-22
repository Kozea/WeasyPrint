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


import os.path

from cssutils import parseFile


HTML4_DEFAULT_STYLESHEET = parseFile(os.path.join(os.path.dirname(__file__),
    'html4_default.css'))


# Pseudo-classes and pseudo-elements are the same to lxml.cssselect.parse().
# List the identifiers for all CSS3 pseudo elements here to distinguish them.
PSEUDO_ELEMENTS = ('before', 'after', 'first-line', 'first-letter')


# Selectors for @page rules can have a pseudo-class, one of :first, :left
# or :right. This maps pseudo-classes to lists of "page types" selected.
PAGE_PSEUDOCLASS_TARGETS = {
    None: ['left', 'right', 'first_left', 'first_right'], # No pseudo-class
    ':left': ['left', 'first_left'],
    ':right': ['right', 'first_right'],
    ':first': ['first_left', 'first_right'],
}


# Specificity of @page pseudo-classes for the cascade.
PAGE_PSEUDOCLASS_SPECIFICITY = {
    None: 0,
    ':left': 1,
    ':right': 1,
    ':first': 10,
}


def get_keyword(value):
    """
    If the given Value object is a keyword (identifier in cssutils), return its
    name. Otherwise return None.
    """
    if value.type == 'IDENT':
        return value.value


def get_single_keyword(values):
    """
    If the given list of Value object is a single keyword (identifier in
    cssutils), return its name. Otherwise return None.
    """
    if len(values) == 1:
        return get_keyword(values[0])
