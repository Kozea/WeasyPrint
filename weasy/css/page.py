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
Everything specific to paged media and @page rules.
"""


from . import shorthands


# Selectors for @page rules can have a pseudo-class, one of :first, :left
# or :right. This maps pseudo-classes to lists of "page types" selected.
PAGE_PSEUDOCLASS_TARGETS = {
    '': ['left', 'right', 'first_left', 'first_right'], # No pseudo-class
    ':left': ['left', 'first_left'],
    ':right': ['right', 'first_right'],
    ':first': ['first_left', 'first_right'],
}


# Specificity of @page pseudo-classes for the cascade.
PAGE_PSEUDOCLASS_SPECIFICITY = {
    '': 0,
    ':left': 1,
    ':right': 1,
    ':first': 10,
}


# Only some properties are allowed in the page context:
# http://www.w3.org/TR/css3-page/#page-properties
# These do not include shorthand properties.
PAGE_CONTEXT_PROPERTIES = set("""
    background-attachment
    background-color
    background-image
    background-position
    background-repeat

    border-bottom-color
    border-bottom-style
    border-bottom-width
    border-left-color
    border-left-style
    border-left-width
    border-right-color
    border-right-style
    border-right-width
    border-top-color
    border-top-style
    border-top-width

    counter-increment
    counter-reset

    margin-bottom
    margin-left
    margin-right
    margin-top

    padding-bottom
    padding-left
    padding-right
    padding-top

    size
""".split())
