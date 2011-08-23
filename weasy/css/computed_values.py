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
import functools

import cssutils.helper
from cssutils.css import PropertyValue, Value

from .properties import INITIAL_VALUES
from .values import (
    get_single_keyword, get_keyword, get_pixel_value, get_single_pixel_value,
    make_pixel_value, make_number, make_keyword)


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
    (name, make_pixel_value(16. * a / b))
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
    'thin': make_pixel_value(1),
    'medium': make_pixel_value(3),
    'thick': make_pixel_value(5),
}

# http://www.w3.org/TR/CSS21/fonts.html#propdef-font-weight
FONT_WEIGHT_RELATIVE = dict(
    bolder={
        100: make_number(400),
        200: make_number(400),
        300: make_number(400),
        400: make_number(700),
        500: make_number(700),
        600: make_number(900),
        700: make_number(900),
        800: make_number(900),
        900: make_number(900),
    },
    lighter={
        100: make_number(100),
        200: make_number(100),
        300: make_number(100),
        400: make_number(100),
        500: make_number(100),
        600: make_number(400),
        700: make_number(400),
        800: make_number(700),
        900: make_number(700),
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


class StyleDict(dict):
    """Allow attribute access to values.

    Allow eg. ``style.font_size`` instead of ``style['font-size']``.

    """
    def __getattr__(self, key):
        try:
            return self[key.replace('_', '-')]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key.replace('_', '-')] = value

    def copy(self):
        """Copy the ``StyleDict``.

        Same as ``dict.copy``, but return an object of the same class
        (``dict.copy()`` always returns a ``dict``).

        """
        return self.__class__(self)


class Computer(object):
    """Things that compute are computers, right?

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
        self.parent_style = parent_style
        self.computed = computed

        for name in INITIAL_VALUES:
            if name not in computed:
                self.get_computed(name)

    def get_computed(self, name):
        """Return the computed value for the ``name`` property.

        Call a "computer" function as needed and populate the `computed` dict
        before return the value.

        """
        if name in self.computed:
            # Already computed
            return self.computed[name]

        values = self.specified[name]
        if name in self.COMPUTER_FUNCTIONS:
            values = self.COMPUTER_FUNCTIONS[name](self, name, values)
        # else: same as specified

        assert isinstance(values, list)
        self.computed[name] = values
        return values

    # Maps property names to functions returning the computed values
    COMPUTER_FUNCTIONS = {}

    @classmethod
    def register(cls, name):
        """Decorator registering a property ``name`` for a function."""
        def decorator(function):
            """Register the property ``name`` for ``function``."""
            cls.COMPUTER_FUNCTIONS[name] = function
            return function
        return decorator


def single_value(function):
    """Decorator validating and computing the single-value properties."""
    @functools.wraps(function)
    def wrapper(computer, name, values):
        """Compute a single-value property."""
        assert len(values) == 1
        new_value = function(computer, name, values[0])
        assert new_value is not None
        return [new_value]
    return wrapper


# Let's be coherent, always use ``name`` as an argument even when it is useless
# pylint: disable=W0613

@Computer.register('background-color')
@Computer.register('border-top-color')
@Computer.register('border-right-color')
@Computer.register('border-bottom-color')
@Computer.register('border-left-color')
def other_color(computer, name, values):
    """Compute the ``*-color`` properties."""
    if get_single_keyword(values) == 'currentColor':
        return computer.get_computed('color')
    else:
        # As specified
        return values


@Computer.register('color')
def color(computer, name, values):
    """Compute the ``color`` property."""
    if get_single_keyword(values) == 'currentColor':
        if computer.parent_style is None:
            return INITIAL_VALUES['color']
        else:
            return computer.parent_style['color']
    else:
        # As specified
        return values


@Computer.register('background-position')
@Computer.register('border-spacing')
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
def lengths(computer, name, values):
    """Compute the properties with a list of lengths."""
    return [compute_length(computer, value) for value in values]


def compute_length(computer, value):
    """Compute a length ``value``."""
    if value.type != 'DIMENSION' or value.dimension == 'px':
        # No conversion needed.
        return value

    if value.dimension in LENGTHS_TO_PIXELS:
        # Convert absolute lengths to pixels
        factor = LENGTHS_TO_PIXELS[value.dimension]
    elif value.dimension in ('em', 'ex'):
        factor = get_single_pixel_value(computer.get_computed('font-size'))

    if value.dimension == 'ex':
        factor *= 0.5

    return make_pixel_value(value.value * factor)


@Computer.register('border-top-width')
@Computer.register('border-right-width')
@Computer.register('border-left-width')
@Computer.register('border-bottom-width')
@single_value
def border_width(computer, name, value):
    """Compute the ``border-*-width`` properties."""
    style = computer.get_computed(name.replace('width', 'style'))
    if get_single_keyword(style) in ('none', 'hidden'):
        return make_number(0)

    keyword = get_keyword(value)
    if keyword in BORDER_WIDTH_KEYWORDS:
        return BORDER_WIDTH_KEYWORDS[keyword]

    return compute_length(computer, value)


@Computer.register('content')
def content(computer, name, values):
    """Compute the ``content`` property."""
    if computer.pseudo_type in ('before', 'after'):
        keyword = get_single_keyword(values)
        if keyword == 'normal':
            return [make_keyword('none')]
        else:
            return [compute_content_value(computer, value) for value in values]
    else:
        # CSS 2.1 says it computes to 'normal' for elements, but does not say
        # anything for pseudo-elements other than :before and :after
        # (ie. :first-line and :first-letter)
        # Assume the same as elements.
        return [make_keyword('normal')]


def compute_content_value(computer, value):
    """Compute a content ``value``."""
    if value.type == 'FUNCTION':
        # value.seq is *NOT* part of the public API
        # TODO: patch cssutils to provide a public API for arguments
        # in CSSFunction objects
        assert value.value.startswith('attr(')
        args = [v.value for v in value.seq if isinstance(v.value, Value)]
        assert len(args) == 1
        attr_name = args[0].value
        content_value = computer.element.get(attr_name, '')
        # TODO: find a way to build a string Value without serializing
        # and re-parsing.
        value = PropertyValue(cssutils.helper.string(content_value))[0]
        assert value.type == 'STRING'
        assert value.value == content_value
    return value


@Computer.register('display')
def display(computer, name, values):
    """Compute the ``display`` property.

    See http://www.w3.org/TR/CSS21/visuren.html#dis-pos-flo

    """
    float_ = get_single_keyword(computer.specified['float'])
    position = get_single_keyword(computer.specified['position'])
    if position in ('absolute', 'fixed') or float_ != 'none' or \
            computer.parent_style is None:
        display_value = get_single_keyword(computer.specified['display'])
        if display_value == 'inline-table':
            return [make_keyword('table')]
        elif display_value in ('inline', 'table-row-group', 'table-column',
                               'table-column-group', 'table-header-group',
                               'table-footer-group', 'table-row', 'table-cell',
                               'table-caption', 'inline-block'):
            return [make_keyword('block')]
    return values


@Computer.register('float')
def compute_float(computer, name, values):
    """Compute the ``float`` property.

    See http://www.w3.org/TR/CSS21/visuren.html#dis-pos-flo

    """
    position_value = get_single_keyword(computer.specified['position'])
    if position_value in ('absolute', 'fixed'):
        return [make_keyword('none')]
    else:
        return values


@Computer.register('font-size')
@single_value
def font_size(computer, name, value):
    """Compute the ``font-size`` property."""
    keyword = get_keyword(value)
    if keyword in FONT_SIZE_KEYWORDS:
        return FONT_SIZE_KEYWORDS[keyword]

    if computer.parent_style is not None:
        parent_font_size = computer.parent_style.font_size[0]
    else:
        # root element, no parent
        parent_keyword = get_single_keyword(INITIAL_VALUES['font-size'])
        # Initial is 'medium', it’s a keyword.
        parent_font_size = FONT_SIZE_KEYWORDS[parent_keyword]
    parent_font_size = get_pixel_value(parent_font_size)

    if value.type == 'DIMENSION':
        if value.dimension == 'px':
            return value  # unchanged
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

    # Raise if `factor` is not defined. It should be, because of validation.
    return make_pixel_value(value.value * factor)


@Computer.register('font-weight')
@single_value
def font_weight(computer, name, value):
    """Compute the ``font-weight`` property."""
    keyword = get_keyword(value)
    if keyword == 'normal':
        return make_number(400)
    elif keyword == 'bold':
        return make_number(700)
    elif keyword in ('bolder', 'lighter'):
        if computer.parent_style is not None:
            parent_values = computer.parent_style['font-weight']
            assert len(parent_values) == 1
            assert parent_values[0].type == 'NUMBER'
            parent_value = parent_values[0].value
        else:
            initial = get_single_keyword(INITIAL_VALUES['font-weight'])
            assert initial == 'normal'
            parent_value = 400
        # Use a string here as StyleDict.__setattr__ turns integers into pixel
        # lengths. This is a number without unit.
        return FONT_WEIGHT_RELATIVE[keyword][parent_value]
    else:
        return value


@Computer.register('line-height')
@single_value
def line_height(computer, name, value):
    """Compute the ``line-height`` property."""
    if get_keyword(value) == 'normal':
        # a "reasonable" value
        # http://www.w3.org/TR/CSS21/visudet.html#line-height
        # TODO: use font metadata?
        factor = 1.2
    elif value.type == 'NUMBER':
        factor = value.value
    elif value.type == 'PERCENTAGE':
        factor = value.value / 100.
    elif value.type == 'DIMENSION':
        return compute_length(computer, value)
    font_size_value = get_single_pixel_value(
        computer.get_computed('font-size'))
    # Raise if `factor` is not defined. It should be, because of validation.
    return make_pixel_value(factor * font_size_value)


@Computer.register('size')
def size(computer, name, values):
    """Compute the ``size`` property.

    See CSS3 Paged Media.

    """
    if computer.element != '@page':
        return [None]

    values = [compute_length(computer, value) for value in values]

    keywords = map(get_keyword, values)
    if keywords == ['auto']:
        keywords = ['A4']  # Chosen by the UA. (That’s me!)

    if values[0].type == 'DIMENSION':
        assert values[0].dimension == 'px'
        if len(values) == 2:
            assert values[1].type == 'DIMENSION'
            assert values[1].dimension == 'px'
            return values
        else:
            # square page
            return values * 2  # list product, same as [values[0], values[0]]
    else:
        orientation = None
        size_value = None
        for keyword in keywords:
            if keyword in ('portrait', 'landscape'):
                orientation = keyword
            elif keyword in PAGE_SIZES:
                size_value = keyword
            else:
                raise ValueError("Illegal value for 'size': %r", keyword)
        if size_value is None:
            size_value = 'A4'
        width, height = PAGE_SIZES[size_value]
        if (orientation == 'portrait' and width > height) or \
               (orientation == 'landscape' and height > width):
            width, height = height, width
        return map(make_pixel_value, [width, height])


@Computer.register('text-align')
@single_value
def text_align(computer, name, value):
    """Compute the ``text-align`` property."""
    if get_keyword(value) == 'start':
        if get_single_keyword(computer.get_computed('direction')) == 'rtl':
            return make_keyword('right')
        else:
            return make_keyword('left')
    else:
        return value


@Computer.register('word-spacing')
@single_value
def word_spacing(computer, name, value):
    """Compute the ``word-spacing`` property."""
    if get_keyword(value) == 'normal':
        return make_number(0)

    return compute_length(computer, value)
