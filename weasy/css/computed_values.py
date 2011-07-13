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
from cssutils.css import PropertyValue, DimensionValue, Value
from .initial_values import INITIAL_VALUES


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


class DummyPropertyValue(list):
    """
    A list that quacks like a PropertyValue.
    """

    @property
    def value(self):
        return ' '.join(value.cssText for value in self)


def compute_font_size(element):
    """
    Set the computed value for font-size, and return this value in pixels.
    """
    style = element.style
    parent = element.getparent()
    if parent is not None:
        parent_font_size = parent.style.font_size
        assert parent_font_size + 0 == parent_font_size, \
            'Got a non-pixel value for the parent font-size.'
    else:
        # root element, no parent
        parent_value_text = INITIAL_VALUES['font-size'].value
        # Initial is medium
        parent_font_size = FONT_SIZE_KEYWORDS[parent_value_text]

    assert len(style['font-size']) == 1
    value = style['font-size'][0]
    value_text = value.value

    # TODO: once we ignore invalid declarations, turn these ValueError’s into
    # assert False, 'Declaration should have been ignored'
    if value_text in FONT_SIZE_KEYWORDS:
        font_size = FONT_SIZE_KEYWORDS[value_text]
    elif value_text in ('smaller', 'larger'):
        # TODO: support 'smaller' and 'larger' font-size
        raise ValueError('font-size: smaller | larger are not supported yet.')
    elif value.type == 'PERCENTAGE':
        font_size = parent_font_size * value.value / 100.
    elif value.type == 'DIMENSION':
        if value.dimension == 'px':
            font_size = value.value
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

    style.font_size = font_size


def compute_length(value, font_size, page_context):
    """
    Convert a single length value to pixels.
    """
    # TODO: once we ignore invalid declarations, turn these ValueError’s into
    # assert False, 'Declaration should have been ignored'
    if value.type != 'DIMENSION' or value.value == 0:
        # No conversion needed.
        return value
    if value.dimension in LENGTHS_TO_PIXELS:
        # Convert absolute lengths to pixels
        factor = LENGTHS_TO_PIXELS[value.dimension]
        return DimensionValue(str(value.value * factor) + 'px')
    elif value.dimension == 'em':
        if page_context:
            raise ValueError('The em unit is not allowed in a page context.')
        else:
            return DimensionValue(str(value.value * font_size) + 'px')
    elif value.dimension == 'ex':
        # TODO: support ex
        raise ValueError('The ex unit is not supported yet.', value.cssText)
    elif value.dimension is not None:
        raise ValueError('Unknown length unit', value.value, repr(value.type))


def compute_lengths(element, page_context):
    """
    Convert other length units to pixels.
    """
    style = element.style
    if page_context:
        font_size = None
    else:
        font_size = style.font_size
    for name in style:
        # PropertyValue objects are not mutable, build a new DummyPropertyValue
        style[name] = DummyPropertyValue(
            compute_length(value, font_size, page_context)
            for value in style[name])


def compute_line_height(element):
    """
    Relative values of line-height are relative to font-size.
    """
    # TODO: test this
    style = element.style
    if style.line_height == 'normal':
        # a "reasonable" value
        # http://www.w3.org/TR/CSS21/visudet.html#line-height
        # TODO: use font metadata?
        style['line-height'] = PropertyValue('1.2')

    assert len(style['line-height']) == 1
    value = style['line-height'][0]

    # TODO: negative values are illegal
    if value.type == 'NUMBER':
        height = style.font_size * value.value
    elif value.type == 'PERCENTAGE':
        height = style.font_size * value.value / 100.
    else:
        return # as specified
    style.line_height = height


def compute_border_width(element):
    """
    Set border-*-width to zero if border-*-style is none or hidden.
    """
    style = element.style
    for side in ('top', 'right', 'bottom', 'left'):
        if style['border-%s-style' % side].value in ('none', 'hidden'):
            style['border-%s-width' % side] = PropertyValue('0')
        else:
            value = style['border-%s-width' % side].value
            if value in BORDER_WIDTH_KEYWORDS:
                width = BORDER_WIDTH_KEYWORDS[value]
                style['border-%s-width' % side] = PropertyValue(
                    str(width) + 'px')


def compute_outline_width(element):
    """
    Set outline-width to zero if outline-style is none.
    """
    # TODO: test this
    style = element.style
    if style.outline_style == 'none':
        style.outline_width = 0
    else:
        value = style.outline_width
        if value in BORDER_WIDTH_KEYWORDS:
            style.outline_width = BORDER_WIDTH_KEYWORDS[value]


def compute_display_float(element):
    """
    Computed values of the display and float properties according to
    http://www.w3.org/TR/CSS21/visuren.html#dis-pos-flo
    """
    # TODO: test this
    style = element.style
    if style.display == 'none':
        # Case 1
        return # position and float do not apply, but leave them
    elif style.position in ('absolute', 'fixed'):
        # Case 2
        style.float = 'none'
    elif style.float == 'none' and element.getparent() is not None:
        # Case 5
        return

    # Cases 2, 3, 4
    display = style.display
    if display == 'inline-table':
        style.display = 'table'
    elif display in ('inline', 'table-row-group', 'table-column',
                     'table-column-group', 'table-header-group',
                     'table-footer-group', 'table-row', 'table-cell',
                     'table-caption', 'inline-block'):
        style.display = 'block'
    # else: unchanged


def compute_word_spacing(element):
    """
    word-spacing: normal means zero.
    """
    # TODO: test this
    style = element.style
    # CSS 2.1 says this for word-spacing but not letter-spacing. Why?
    if style.word_spacing == 'normal':
        style.word_spacing = 0


def compute_font_weight(element):
    """
    Handle keyword values for font-weight.
    """
    # TODO: test this
    style = element.style
    value = style.font_weight
    if value == 'normal':
        # Use a string here as StyleDict.__setattr__ turns integers into pixel
        # lengths. This is a number without unit.
        style.font_weight = '400'
    elif value == 'bold':
        # Use a string here as StyleDict.__setattr__ turns integers into pixel
        # lengths. This is a number without unit.
        style.font_weight = '700'
    elif value in ('bolder', 'lighter'):
        parent_values = element.getparent().style['font-weight']
        assert len(parent_values) == 1
        assert parent_values[0].type == 'NUMBER'
        parent_value = parent_values[0].value
        # Use a string here as StyleDict.__setattr__ turns integers into pixel
        # lengths. This is a number without unit.
        style.font_weight = str(FONT_WEIGHT_RELATIVE[value][parent_value])


def compute_content_value(parent, value):
    if value.type == 'FUNCTION':
        # value.seq is *NOT* part of the public API
        # TODO: patch cssutils to provide a public API for arguments
        # in CSSFunction objects
        assert value.value.startswith('attr(')
        args = [v.value for v in value.seq if isinstance(v.value, Value)]
        assert len(args) == 1
        attr_name = args[0].value
        # The 'content' property can only be something else than 'normal'
        # on :before or :after, so attr() applies to the parent, the actual
        # element.
        content = parent.get(attr_name, '')
        # TODO: find a way to build a string Value without serializing
        # and re-parsing.
        value = PropertyValue(cssutils.helper.string(content))[0]
        assert value.type == 'STRING'
        assert value.value == content
    return value


def compute_content(element):
    # TODO: properly test this
    style = element.style
    if getattr(element, 'pseudo_element_type', '') in ('before', 'after'):
        if style.content == 'normal':
            style.content = 'none'
        else:
            parent = element.getparent()
            style.content = DummyPropertyValue(
                compute_content_value(parent, value)
                for value in style['content'])
    else:
        # CSS 2.1 says it computes to 'normal' for elements, but does not say
        # anything for pseudo-elements other than :before and :after
        # (ie. :first-line and :first-letter)
        # Assume the same as elements.
        style.content = 'normal'


def compute_size(element, page_context):
    if not page_context:
        return
    style = element.style
    if style.size == 'auto':
        style.size = 'A4' # Chosen by the UA. (That’s me!)
    values = style['size'] # PropertyValue object
    if len(values) == 0 or len(values) > 2:
        raise ValueError('size takes one or two values, got %r' % values)
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
        for value in values:
            value = value.cssText
            if value in ('portrait', 'landscape'):
                orientation = value
            elif value in PAGE_SIZES:
                size = value
            else:
                raise ValueError("Illegal value for 'size': %r", value)
        if size is None:
            size = 'A4'
        width, height = PAGE_SIZES[size]
        if (orientation == 'portrait' and width > height) or \
               (orientation == 'landscape' and height > width):
            width, height = height, width
    style._weasy_page_width = width
    style._weasy_page_height = height


def compute_values(element, page_context):
    """
    Normalize values as much as possible without rendering the document.
    """
    # em lengths depend on font-size, compute font-size first
    compute_font_size(element)
    compute_lengths(element, page_context)
    compute_line_height(element)
    compute_display_float(element)
    compute_word_spacing(element)
    compute_font_weight(element)
    compute_content(element)
    compute_border_width(element)
    compute_outline_width(element)
    compute_size(element, page_context)
    # Recent enough cssutils have a .absoluteUri on URIValue objects.
    # TODO: percentages for height?
    #       http://www.w3.org/TR/CSS21/visudet.html#propdef-height
    # TODO: percentages for vertical-align. What about line-height: normal?
    # TODO: clip
