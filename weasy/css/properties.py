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
``SHORTHANDS`` is a dict of prop_name: expander_function pairs for all known
shorthand properties. For example, `margin` is a shorthand for all of
margin-top, margin-right, margin-bottom and margin-left.

Expander functions take a Property and yield expanded Property objects.


``INITIAL_VALUES`` is a CSSStyleDeclaration with the initial values of CSS 2.1
properties. The initial value is the specified value when no other values was
found in the stylesheets for an element.

"""

import collections


# How many CSS pixels is one <unit> ?
# http://www.w3.org/TR/CSS21/syndata.html#length-units
LENGTHS_TO_PIXELS = {
    'px': 1,
    'pt': 1. / 0.75,
    'pc': 16., # LENGTHS_TO_PIXELS['pt'] * 12
    'in': 96., # LENGTHS_TO_PIXELS['pt'] * 72
    'cm': 96. / 2.54, # LENGTHS_TO_PIXELS['in'] / 2.54
    'mm': 96. / 25.4, # LENGTHS_TO_PIXELS['in'] / 25.4
}


# Value in pixels of font-size for <absolute-size> keywords: 12pt (16px) for
# medium, and scaling factors given in CSS3 for others:
# http://www.w3.org/TR/css3-fonts/#font-size-prop
# This dict has to be ordered to implement 'smaller' and 'larger'
FONT_SIZE_MEDIUM = 16.
FONT_SIZE_KEYWORDS = collections.OrderedDict([
    ('xx-small', FONT_SIZE_MEDIUM * 3/5),
    ('x-small', FONT_SIZE_MEDIUM * 3/4),
    ('small', FONT_SIZE_MEDIUM * 8/9),
    ('medium', FONT_SIZE_MEDIUM),
    ('large', FONT_SIZE_MEDIUM * 6/5),
    ('x-large', FONT_SIZE_MEDIUM * 3/2),
    ('xx-large', FONT_SIZE_MEDIUM * 2),
])
del FONT_SIZE_MEDIUM


# These are unspecified, other than 'thin' <='medium' <= 'thick'.
# Values are in pixels.
BORDER_WIDTH_KEYWORDS = {
    'thin': 1,
    'medium': 3,
    'thick': 5,
}


# http://www.w3.org/TR/CSS21/fonts.html#propdef-font-weight
FONT_WEIGHT_RELATIVE = dict(
    bolder={
        100: 400,
        200: 400,
        300: 400,
        400: 700,
        500: 700,
        600: 900,
        700: 900,
        800: 900,
        900: 900,
    },
    lighter={
        100: 100,
        200: 100,
        300: 100,
        400: 100,
        500: 100,
        600: 400,
        700: 400,
        800: 700,
        900: 700,
    },
)
