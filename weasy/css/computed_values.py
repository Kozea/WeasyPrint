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

import cssutils.helper
from cssutils.css import PropertyValue, Value

from .initial_values import INITIAL_VALUES
from .utils import (get_single_keyword, get_keyword, get_single_pixel_value,
                    make_pixel_value, make_number, make_keyword)


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
FONT_SIZE_KEYWORDS = collections.OrderedDict(
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


def compute_font_size(style, parent_style):
    """
    Set the computed value for font-size, and return this value in pixels.
    """
    if parent_style is not None:
        parent_font_size = get_single_pixel_value(parent_style.font_size)
        assert parent_font_size + 0 == parent_font_size, \
            'Got a non-pixel value for the parent font-size.'
    else:
        # root element, no parent
        parent_value_text = INITIAL_VALUES['font-size'][0].cssText
        # Initial is medium
        parent_font_size = FONT_SIZE_KEYWORDS[parent_value_text].value

    assert len(style['font-size']) == 1
    value = style['font-size'][0]
    value_text = value.value

    # TODO: once we ignore invalid declarations, turn these ValueError’s into
    # assert False, 'Declaration should have been ignored'
    if value_text in FONT_SIZE_KEYWORDS:
        font_size = FONT_SIZE_KEYWORDS[value_text]
        style.font_size = [font_size]
        return font_size.value
    elif value_text in ('smaller', 'larger'):
        # TODO: support 'smaller' and 'larger' font-size
        raise ValueError('font-size: smaller | larger are not supported yet.')
    elif value.type == 'PERCENTAGE':
        font_size = parent_font_size * value.value / 100.
    elif value.type == 'DIMENSION':
        if value.dimension == 'px':
            return value.value  # unchanged
        elif value.dimension == 'em':
            font_size = parent_font_size * value.value
        elif value.dimension == 'ex':
            # TODO: support ex unit
            raise ValueError('The ex unit is not supported yet.')
        elif value.dimension in LENGTHS_TO_PIXELS:
            factor = LENGTHS_TO_PIXELS[value.dimension]
            font_size = value.value * factor
        else:
            raise ValueError('Unknown length unit for font-size:', value_text)
    else:
        raise ValueError('Invalid value for font-size:', value_text)

    style.font_size = [make_pixel_value(font_size)]
    return font_size


def compute_length(value, font_size):
    """
    Convert a single length value to pixels.
    """
    # TODO: once we ignore invalid declarations, turn these ValueError’s into
    # assert False, 'Declaration should have been ignored'
    if value.type != 'DIMENSION' or value.value == 0 or \
            value.dimension == 'px':
        # No conversion needed.
        return value
    if value.dimension in LENGTHS_TO_PIXELS:
        # Convert absolute lengths to pixels
        factor = LENGTHS_TO_PIXELS[value.dimension]
        return make_pixel_value(value.value * factor)
    elif value.dimension == 'em':
        return make_pixel_value(value.value * font_size)
    elif value.dimension == 'ex':
        # TODO: support ex
        raise ValueError('The ex unit is not supported yet.', value.cssText)
    elif value.dimension is not None:
        raise ValueError('Unknown length unit', value.value, repr(value.type))


def compute_lengths(style, font_size):
    """
    Convert other length units to pixels.
    """
    for name, values in style.iteritems():
        style[name] = [compute_length(value, font_size) for value in values]


def compute_line_height(style, font_size):
    """
    Relative values of line-height are relative to font-size.
    """
    # TODO: test this
    line_height = style['line-height']
    if get_single_keyword(line_height) == 'normal':
        # a "reasonable" value
        # http://www.w3.org/TR/CSS21/visudet.html#line-height
        # TODO: use font metadata?
        style['line-height'] = [make_pixel_value(1.2 * font_size)]
        return

    assert len(line_height) == 1
    value = line_height[0]

    # TODO: negative values are illegal
    if value.type == 'NUMBER':
        height = font_size * value.value
    elif value.type == 'PERCENTAGE':
        height = font_size * value.value / 100.
    else:
        return # as specified
    style['line-height'] = [make_pixel_value(height)]


def compute_border_width(style):
    """
    Set border-*-width to zero if border-*-style is none or hidden.
    """
    for side in ('top', 'right', 'bottom', 'left'):
        values = style['border-%s-style' % side]
        if get_single_keyword(values) in ('none', 'hidden'):
            style['border-%s-width' % side] = [make_number(0)]
        else:
            values = style['border-%s-width' % side]
            if len(values) != 1:
                return
            value = get_single_keyword(values)
            if value in BORDER_WIDTH_KEYWORDS:
                width = BORDER_WIDTH_KEYWORDS[value]
                style['border-%s-width' % side] = [width]


def compute_outline_width(style):
    """
    Set outline-width to zero if outline-style is none.
    """
    # TODO: test this
    keyword = get_single_keyword(style.outline_style)
    if keyword == 'none':
        style.outline_width = [make_number(0)]
    else:
        if keyword in BORDER_WIDTH_KEYWORDS:
            style.outline_width = [BORDER_WIDTH_KEYWORDS[keyword]]


def compute_display_float(style, parent_style):
    """
    Computed values of the display and float properties according to
    http://www.w3.org/TR/CSS21/visuren.html#dis-pos-flo
    """
    # TODO: test this
    display = get_single_keyword(style.display)
    position = get_single_keyword(style.position)
    float_ = get_single_keyword(style.float)
    if display == 'none':
        # Case 1
        return # position and float do not apply, but leave them
    elif position in ('absolute', 'fixed'):
        # Case 2
        style.float = [make_keyword('none')]
    elif float_ == 'none' and parent_style is not None:
        # Case 5
        return

    # Cases 2, 3, 4
    if display == 'inline-table':
        style.display = [make_keyword('table')]
    elif display in ('inline', 'table-row-group', 'table-column',
                     'table-column-group', 'table-header-group',
                     'table-footer-group', 'table-row', 'table-cell',
                     'table-caption', 'inline-block'):
        style.display = [make_keyword('block')]
    # else: unchanged


def compute_word_spacing(style):
    """
    word-spacing: normal means zero.
    """
    # TODO: test this
    # CSS 2.1 says this for word-spacing but not letter-spacing. Why?
    if get_single_keyword(style.word_spacing) == 'normal':
        style.word_spacing = [make_pixel_value(0)]


def compute_font_weight(style, parent_style):
    """
    Handle keyword values for font-weight.
    """
    # TODO: test this
    keyword = get_single_keyword(style.font_weight)
    if keyword == 'normal':
        style.font_weight = [make_number(400)]
    elif keyword == 'bold':
        style.font_weight = [make_number(700)]
    elif keyword in ('bolder', 'lighter'):
        if parent_style is not None:
            parent_values = parent_style['font-weight']
            assert len(parent_values) == 1
            assert parent_values[0].type == 'NUMBER'
            parent_value = parent_values[0].value
        else:
            initial = get_single_keyword(INITIAL_VALUES['font-weight'])
            assert initial == 'normal'
            parent_value = 400
        # Use a string here as StyleDict.__setattr__ turns integers into pixel
        # lengths. This is a number without unit.
        style.font_weight = [FONT_WEIGHT_RELATIVE[keyword][parent_value]]


def compute_content_value(element, value):
    if value.type == 'FUNCTION':
        # value.seq is *NOT* part of the public API
        # TODO: patch cssutils to provide a public API for arguments
        # in CSSFunction objects
        assert value.value.startswith('attr(')
        args = [v.value for v in value.seq if isinstance(v.value, Value)]
        assert len(args) == 1
        attr_name = args[0].value
        content = element.get(attr_name, '')
        # TODO: find a way to build a string Value without serializing
        # and re-parsing.
        value = PropertyValue(cssutils.helper.string(content))[0]
        assert value.type == 'STRING'
        assert value.value == content
    return value


def compute_content(element, pseudo_type, style):
    # TODO: properly test this
    values = style.content
    keyword = get_single_keyword(values)
    if pseudo_type in ('before', 'after'):
        if keyword == 'normal':
            style.content = [make_keyword('none')]
        else:
            style.content = [compute_content_value(element, value)
                             for value in values]
    else:
        # CSS 2.1 says it computes to 'normal' for elements, but does not say
        # anything for pseudo-elements other than :before and :after
        # (ie. :first-line and :first-letter)
        # Assume the same as elements.
        style.content = [make_keyword('normal')]


def compute_size(element, style):
    if element != '@page':
        return

    values = style['size'] # PropertyValue object
    if len(values) == 0 or len(values) > 2:
        raise ValueError('size takes one or two values, got %r' % values)

    keywords = map(get_keyword, values)
    if keywords == ['auto']:
        keywords = ['A4'] # Chosen by the UA. (That’s me!)

    if values[0].type == 'DIMENSION' and values[0].dimension == 'px':
        if len(values) == 2:
            assert values[1].type == 'DIMENSION'
            assert values[1].dimension == 'px'
            width = values[0].value
            height = values[1].value
            assert isinstance(width, (int, float))
            assert isinstance(height, (int, float))
        else:
            # square page
            width = height = values[0].value
            assert isinstance(width, (int, float))
    else:
        orientation = None
        size = None
        for keyword in keywords:
            if keyword in ('portrait', 'landscape'):
                orientation = keyword
            elif keyword in PAGE_SIZES:
                size = keyword
            else:
                raise ValueError("Illegal value for 'size': %r", keyword)
        if size is None:
            size = 'A4'
        width, height = PAGE_SIZES[size]
        if (orientation == 'portrait' and width > height) or \
               (orientation == 'landscape' and height > width):
            width, height = height, width
    style._weasy_page_width = width
    style._weasy_page_height = height


def compute_current_color(style, parent_style):
    """
    Replace occurences of currentColor by the current color.

    http://www.w3.org/TR/css3-color/#currentcolor
    """
    # Handle 'color' first
    if get_single_keyword(style['color']) == 'currentColor':
        if parent_style is None:
            values = INITIAL_VALUES['color']
        else:
            values = parent_style['color']
        style['color'] = values

    for name, values in style.iteritems():
        if get_single_keyword(values) == 'currentColor' and name != 'color':
            style[name] = style['color']


def compute_text_align(style):
    """
    Replace the 'start' keyword for text-align that we borrowed from CSS3
    to implement the initial value.
    """
    if get_single_keyword(style['text-align']) == 'start':
        if get_single_keyword(style['direction']) == 'rtl':
            style['text-align'] = [make_keyword('right')]
        else:
            style['text-align'] = [make_keyword('left')]


def compute_values(element, pseudo_type, style, parent_style):
    """
    Normalize values as much as possible without rendering the document.
    """
    # em lengths depend on font-size, compute font-size first
    font_size = compute_font_size(style, parent_style)
    compute_lengths(style, font_size)
    compute_line_height(style, font_size)
    compute_display_float(style, parent_style)
    compute_word_spacing(style)
    compute_font_weight(style, parent_style)
    compute_content(element, pseudo_type, style)
    compute_border_width(style)
    compute_outline_width(style)
    compute_current_color(style, parent_style)
    compute_text_align(style)
    compute_size(element, style)
    # Recent enough cssutils have a .absoluteUri on URIValue objects.
    # TODO: percentages for height?
    #       http://www.w3.org/TR/CSS21/visudet.html#propdef-height
    # TODO: percentages for vertical-align. What about line-height: normal?
    # TODO: clip
