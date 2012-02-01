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
assert INITIAL_VALUES['border_top_width'] == BORDER_WIDTH_KEYWORDS['medium']

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


def _computing_order():
    """Some computed values are required by others, so order matters."""
    first = ['font_size', 'line_height', 'color']
    order = sorted(INITIAL_VALUES)
    for name in first:
        order.remove(name)
    return tuple(first + order)
COMPUTING_ORDER = _computing_order()

# Maps property names to functions returning the computed values
COMPUTER_FUNCTIONS = {}


def register_computer(name):
    """Decorator registering a property ``name`` for a function."""
    name = name.replace('-', '_')
    def decorator(function):
        """Register the property ``name`` for ``function``."""
        COMPUTER_FUNCTIONS[name] = function
        return function
    return decorator


def compute(element, pseudo_type, specified, computed, parent_style):
    """
    Return a StyleDict of computed values.

    :param element: The HTML element these style apply to
    :param pseudo_type: The type of pseudo-element, eg 'before', None
    :param specified: a :class:`StyleDict` of specified values. Should contain
                      values for all properties.
    :param computed: a :class:`StyleDict` of already known computed values.
                     Only contains some properties (or none).
    :param parent_values: a :class:`StyleDict` of computed values of the parent
                          element (should contain values for all properties),
                          or ``None`` if ``element`` is the root element.
    """
    if parent_style is None:
        parent_style = INITIAL_VALUES

    computer = lambda: 0  # Dummy object that holds attributes
    computer.element = element
    computer.pseudo_type = pseudo_type
    computer.specified = specified
    computer.computed = computed
    computer.parent_style = parent_style

    getter = COMPUTER_FUNCTIONS.get

    for name in COMPUTING_ORDER:
        if name in computed:
            # Already computed
            continue

        value = specified[name]
        function = getter(name)
        if function is not None:
            value = function(computer, name, value)
        # else: same as specified

        assert value is not None
        computed[name] = value

    return computed


# Let's be coherent, always use ``name`` as an argument even when it is useless
# pylint: disable=W0613

@register_computer('background-color')
@register_computer('border-top-color')
@register_computer('border-right-color')
@register_computer('border-bottom-color')
@register_computer('border-left-color')
def other_color(computer, name, value):
    """Compute the ``*-color`` properties."""
    if value == 'currentColor':
        return computer.computed.color
    else:
        # As specified
        return value


@register_computer('background-position')
@register_computer('border-spacing')
@register_computer('size')
def length_list(computer, name, values):
    """Compute the properties with a list of lengths."""
    return [length(computer, name, value) for value in values]


@register_computer('top')
@register_computer('right')
@register_computer('left')
@register_computer('bottom')
@register_computer('margin-top')
@register_computer('margin-right')
@register_computer('margin-bottom')
@register_computer('margin-left')
@register_computer('height')
@register_computer('width')
@register_computer('letter-spacing')
@register_computer('padding-top')
@register_computer('padding-right')
@register_computer('padding-bottom')
@register_computer('padding-left')
@register_computer('text-indent')
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
        factor = computer.computed.font_size

    if value.dimension == 'ex':
        factor *= 0.5

    return value.value * factor


@register_computer('background-size')
def border_width(computer, name, value):
    """Compute the ``background-size`` properties."""
    if value in ('contain', 'cover'):
        return value
    else:
        return length_list(computer, name, value)


@register_computer('border-top-width')
@register_computer('border-right-width')
@register_computer('border-left-width')
@register_computer('border-bottom-width')
def border_width(computer, name, value):
    """Compute the ``border-*-width`` properties."""
    style = computer.computed[name.replace('width', 'style')]
    if style in ('none', 'hidden'):
        return 0

    if value in BORDER_WIDTH_KEYWORDS:
        return BORDER_WIDTH_KEYWORDS[value]

    return length(computer, name, value)


@register_computer('content')
def content(computer, name, values):
    """Compute the ``content`` property."""
    if values in ('normal', 'none'):
        return values
    else:
        return [('STRING', computer.element.get(value, ''))
                if type_ == 'attr' else (type_, value)
                for type_, value in values]


@register_computer('display')
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


@register_computer('float')
def compute_float(computer, name, value):
    """Compute the ``float`` property.

    See http://www.w3.org/TR/CSS21/visuren.html#dis-pos-flo

    """
    if computer.specified.position in ('absolute', 'fixed'):
        return 'none'
    else:
        return value


@register_computer('font-size')
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


@register_computer('font-weight')
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


@register_computer('line-height')
def line_height(computer, name, value):
    """Compute the ``line-height`` property."""
    # No .type attribute: already computed
    if value == 'normal' or not hasattr(value, 'type'):
        return value
    elif value.type == 'NUMBER':
        return ('NUMBER', value.value)
    elif value.type == 'PERCENTAGE':
        factor = value.value / 100.
        font_size_value = computer.computed.font_size
        pixels = factor * font_size_value
    else:
        assert value.type == 'DIMENSION'
        pixels = length(computer, name, value)
    return ('PIXELS', pixels)


@register_computer('vertical-align')
def vertical_align(computer, name, value):
    """Compute the ``vertical-align`` property."""
    # Use +/- half an em for super and sub, same as Pango.
    # (See the SUPERSUB_RISE constant in pango-markup.c)
    if value == 'super':
        return computer.computed.font_size * 0.5
    elif value == 'sub':
        return computer.computed.font_size * -0.5
    elif getattr(value, 'type', 'other') == 'PERCENTAGE':
        height = used_line_height({
            'line_height': computer.computed.line_height,
            'font_size': computer.computed.font_size
        })
        return height * value.value / 100.
    else:
        return length(computer, name, value)


@register_computer('word-spacing')
def word_spacing(computer, name, value):
    """Compute the ``word-spacing`` property."""
    if value == 'normal':
        return 0
    else:
        return length(computer, name, value)


def used_line_height(style):
    """Return the used value for the ``line-height`` property."""
    height = style['line_height']
    if height == 'normal':
        # a "reasonable" value
        # http://www.w3.org/TR/CSS21/visudet.html#line-height
        # TODO: use font metrics?
        height = ('NUMBER', 1.2)
    type_, value = height
    if type_ == 'NUMBER':
        return value * style['font_size']
    else:
        return value
