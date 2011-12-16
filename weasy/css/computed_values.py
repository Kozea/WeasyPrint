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
Normalize values as much as possible without rendering the document.

"""

import collections

from .properties import INITIAL_VALUES
from .values import get_single_keyword, get_keyword


# How many CSS pixels is one <unit>?
# http://www.w3.org/TR/CSS21/syndata.html#length-units
LENGTHS_TO_PIXELS = {
    'px': 1,
    'pt': 1. / 0.75,
    'pc': 16.,  # LENGTHS_TO_PIXELS['pt'] * 12
    'in': 96.,  # LENGTHS_TO_PIXELS['pt'] * 72
    'cm': 96. / 2.54,  # LENGTHS_TO_PIXELS['in'] / 2.54
    'mm': 96. / 25.4,  # LENGTHS_TO_PIXELS['in'] / 25.4
}

# Value in pixels of font-size for <absolute-size> keywords: 12pt (16px) for
# medium, and scaling factors given in CSS3 for others:
# http://www.w3.org/TR/css3-fonts/#font-size-prop
# This dict has to be ordered to implement 'smaller' and 'larger'
FONT_SIZE_KEYWORDS = collections.OrderedDict(
    # medium is 16px, others are a ratio of medium
    (name, INITIAL_VALUES['font_size'] * a / b)
    for name, a, b in [
        ('xx-small', 3, 5),
        ('x-small', 3, 4),
        ('small', 8, 9),
        ('medium', 1, 1),
        ('large', 6, 5),
        ('x-large', 3, 2),
        ('xx-large', 2, 1),
    ]
)

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

# http://www.w3.org/TR/css3-page/#size
# name=(width in pixels, height in pixels)
PAGE_SIZES = dict(
    A5=(
        148 * LENGTHS_TO_PIXELS['mm'],
        210 * LENGTHS_TO_PIXELS['mm'],
    ),
    A4=(
        210 * LENGTHS_TO_PIXELS['mm'],
        297 * LENGTHS_TO_PIXELS['mm'],
    ),
    A3=(
        297 * LENGTHS_TO_PIXELS['mm'],
        420 * LENGTHS_TO_PIXELS['mm'],
    ),
    B5=(
        176 * LENGTHS_TO_PIXELS['mm'],
        250 * LENGTHS_TO_PIXELS['mm'],
    ),
    B4=(
        250 * LENGTHS_TO_PIXELS['mm'],
        353 * LENGTHS_TO_PIXELS['mm'],
    ),
    letter=(
        8.5 * LENGTHS_TO_PIXELS['in'],
        11 * LENGTHS_TO_PIXELS['in'],
    ),
    legal=(
        8.5 * LENGTHS_TO_PIXELS['in'],
        14 * LENGTHS_TO_PIXELS['in'],
    ),
    ledger=(
        11 * LENGTHS_TO_PIXELS['in'],
        17 * LENGTHS_TO_PIXELS['in'],
    ),
)
for w, h in PAGE_SIZES.values():
    assert w < h

INITIAL_VALUES['size'] = PAGE_SIZES['A4']


class Computer(object):
    """Things that compute are computers, right? Handle `computed values`.

    Some computed values depend on other computed values. This object allow
    to request them without worrying about which is computed first.

    :param element: The HTML element these style apply to
    :param pseudo_type: The type of pseudo-element, eg 'before', None
    :param specified: a :class:`StyleDict` of specified values. Should contain
                      values for all properties.
    :param computed: a :class:`StyleDict` of already known computed values.
                     Only contains some properties (or none).
    :param parent_values: a :class:`StyleDict` of computed values of the parent
                          element (should contain values for all properties),
                          or ``None`` if ``element`` is the root element.

    Once instanciated, this object will have completed the ``computed`` dict
    so that is has values for all properties.

    """
    def __init__(self, element, pseudo_type, specified, computed,
                 parent_style):
        self.element = element
        self.pseudo_type = pseudo_type
        self.specified = specified
        if parent_style is None:
            self.parent_style = INITIAL_VALUES
        else:
            self.parent_style = parent_style
        self.computed = computed

        for name in INITIAL_VALUES:
            self.get_computed(name)

    def get_computed(self, name):
        """Return the computed value for the ``name`` property.

        Call a "computer" function as needed and populate the `computed` dict
        before return the value.

        """
        if name in self.computed:
            # Already computed
            return self.computed[name]

        value = self.specified[name]
        if name in self.COMPUTER_FUNCTIONS:
            value = self.COMPUTER_FUNCTIONS[name](self, name, value)
        # else: same as specified

        assert value is not None
        self.computed[name] = value
        return value

    # Maps property names to functions returning the computed values
    COMPUTER_FUNCTIONS = {}

    @classmethod
    def register(cls, name):
        """Decorator registering a property ``name`` for a function."""
        name = name.replace('-', '_')
        def decorator(function):
            """Register the property ``name`` for ``function``."""
            cls.COMPUTER_FUNCTIONS[name] = function
            return function
        return decorator


# Let's be coherent, always use ``name`` as an argument even when it is useless
# pylint: disable=W0613

@Computer.register('background-color')
@Computer.register('border-top-color')
@Computer.register('border-right-color')
@Computer.register('border-bottom-color')
@Computer.register('border-left-color')
def other_color(computer, name, value):
    """Compute the ``*-color`` properties."""
    if value == 'currentColor':
        return computer.get_computed('color')
    else:
        # As specified
        return value


@Computer.register('background-position')
@Computer.register('border-spacing')
@Computer.register('size')
def length_list(computer, name, values):
    """Compute the properties with a list of lengths."""
    return [length(computer, name, value) for value in values]


@Computer.register('top')
@Computer.register('right')
@Computer.register('left')
@Computer.register('bottom')
@Computer.register('margin-top')
@Computer.register('margin-right')
@Computer.register('margin-bottom')
@Computer.register('margin-left')
@Computer.register('height')
@Computer.register('width')
@Computer.register('letter-spacing')
@Computer.register('padding-top')
@Computer.register('padding-right')
@Computer.register('padding-bottom')
@Computer.register('padding-left')
@Computer.register('text-indent')
@Computer.register('word-spacing')
def length(computer, name, value):
    """Compute a length ``value``."""
    if getattr(value, 'type', 'other') == 'NUMBER' and value.value == 0:
        return 0

    if getattr(value, 'type', 'other') != 'DIMENSION':
        # No conversion needed.
        return value

    if value.dimension in LENGTHS_TO_PIXELS:
        # Convert absolute lengths to pixels
        factor = LENGTHS_TO_PIXELS[value.dimension]
    elif value.dimension in ('em', 'ex'):
        factor = computer.get_computed('font_size')

    if value.dimension == 'ex':
        factor *= 0.5

    return value.value * factor


@Computer.register('border-top-width')
@Computer.register('border-right-width')
@Computer.register('border-left-width')
@Computer.register('border-bottom-width')
def border_width(computer, name, value):
    """Compute the ``border-*-width`` properties."""
    style = computer.get_computed(name.replace('width', 'style'))
    if style in ('none', 'hidden'):
        return 0

    if value in BORDER_WIDTH_KEYWORDS:
        return BORDER_WIDTH_KEYWORDS[value]

    return length(computer, name, value)


@Computer.register('content')
def content(computer, name, values):
    """Compute the ``content`` property."""
    if computer.pseudo_type in ('before', 'after'):
        if values in ('normal', 'none'):
            return 'none'
        else:
            return [('STRING', computer.element.get(value, ''))
                    if type_ == 'attr' else (type_, value)
                    for type_, value in values]
    else:
        return 'normal'


@Computer.register('display')
def display(computer, name, value):
    """Compute the ``display`` property.

    See http://www.w3.org/TR/CSS21/visuren.html#dis-pos-flo

    """
    float_ = computer.specified.float
    position = computer.specified.position
    if position in ('absolute', 'fixed') or float_ != 'none' or \
            getattr(computer.element, 'getparent', lambda: None)() is None:
        if value == 'inline-table':
            return'table'
        elif value in ('inline', 'table-row-group', 'table-column',
                       'table-column-group', 'table-header-group',
                       'table-footer-group', 'table-row', 'table-cell',
                       'table-caption', 'inline-block'):
            return 'block'
    return value


@Computer.register('float')
def compute_float(computer, name, value):
    """Compute the ``float`` property.

    See http://www.w3.org/TR/CSS21/visuren.html#dis-pos-flo

    """
    if computer.specified.position in ('absolute', 'fixed'):
        return 'none'
    else:
        return value


@Computer.register('font-size')
def font_size(computer, name, value):
    """Compute the ``font-size`` property."""
    if isinstance(value, (int, float)):
        return value
    if value in FONT_SIZE_KEYWORDS:
        return FONT_SIZE_KEYWORDS[value]

    parent_font_size = computer.parent_style['font_size']

    if value.type == 'DIMENSION':
        if value.dimension == 'px':
            factor = 1
        elif value.dimension == 'em':
            factor = parent_font_size
        elif value.dimension == 'ex':
            # TODO: find a better way to measure ex, see
            # http://www.w3.org/TR/CSS21/syndata.html#length-units
            factor = parent_font_size * 0.5
        elif value.dimension in LENGTHS_TO_PIXELS:
            factor = LENGTHS_TO_PIXELS[value.dimension]
    elif value.type == 'PERCENTAGE':
        factor = parent_font_size / 100.
    elif value.type == 'NUMBER' and value.value == 0:
        return 0

    # Raise if `factor` is not defined. It should be, because of validation.
    return value.value * factor


@Computer.register('font-weight')
def font_weight(computer, name, value):
    """Compute the ``font-weight`` property."""
    if value == 'normal':
        return 400
    elif value == 'bold':
        return 700
    elif value in ('bolder', 'lighter'):
        parent_value = computer.parent_style['font_weight']
        # Use a string here as StyleDict.__setattr__ turns integers into pixel
        # lengths. This is a number without unit.
        return FONT_WEIGHT_RELATIVE[value][parent_value]
    else:
        return value


@Computer.register('line-height')
def line_height(computer, name, value):
    """Compute the ``line-height`` property."""
    if value == 'normal':
        # a "reasonable" value
        # http://www.w3.org/TR/CSS21/visudet.html#line-height
        # TODO: use font metadata?
        factor = 1.2
    elif value.type == 'NUMBER':
        factor = value.value
    elif value.type == 'PERCENTAGE':
        factor = value.value / 100.
    elif value.type == 'DIMENSION':
        return length(computer, name, value)
    font_size_value = computer.get_computed('font_size')
    # Raise if `factor` is not defined. It should be, because of validation.
    return factor * font_size_value


@Computer.register('text-align')
def text_align(computer, name, value):
    """Compute the ``text-align`` property."""
    if value == 'start':
        if computer.get_computed('direction') == 'rtl':
            return 'right'
        else:
            return 'left'
    else:
        return value


@Computer.register('vertical_align')
def vertical_align(computer, name, value):
    """Compute the ``word-spacing`` property."""
    # Use +/- half an em for super and sub, same as Pango.
    # (See the SUPERSUB_RISE constant in pango-markup.c)
    if value == 'super':
        return computer.get_computed('font_size') * 0.5
    if value == 'sub':
        return computer.get_computed('font_size') * -0.5
    if getattr(value, 'type', 'other') == 'PERCENTAGE':
        return computer.get_computed('line_height') * value.value / 100.
    return length(computer, name, value)
