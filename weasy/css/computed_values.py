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
from .initial_values import get_value, INITIAL_VALUES


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


def handle_computed_font_size(element):
    """
    Set the computed value for font-size, and return this value in pixels.
    """
    parent = element.getparent()
    if parent is not None:
        assert len(parent.style['font-size']) == 1
        assert parent.style['font-size'][0].dimension == 'px'
        parent_font_size = parent.style['font-size'][0].value
    else:
        # root element, no parent
        parent_value_text = INITIAL_VALUES['font-size'].value
        # Initial is medium
        parent_font_size = FONT_SIZE_KEYWORDS[parent_value_text]

    assert len(element.style['font-size']) == 1
    value = element.style['font-size'][0]
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

    element.style['font-size'] = PropertyValue(str(font_size) + 'px')
    return font_size


def compute_length(value, font_size):
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
        return DimensionValue(str(value.value * font_size) + 'px')
    elif value.dimension == 'ex':
        # TODO: support ex
        raise ValueError('The ex unit is not supported yet.', value.cssText)
    elif value.dimension is not None:
        raise ValueError('Unknown length unit', value.value, repr(value.type))
    

def handle_computed_lengths(element, font_size):
    """
    Convert other length units to pixels.
    """
    element.style = dict(
        # PropertyValue objects are not mutable, build a new list
        (name, [compute_length(value, font_size) for value in values])
        for name, values in element.style.iteritems()
    )


def handle_computed_line_height(element, font_size):
    """
    Relative values of line-height are relative to font-size.
    """
    # TODO: test this
    style = element.style
    assert len(element.style['line-height']) == 1
    value = element.style['line-height'][0]
    
    # TODO: negative values are illegal
    if value.type == 'NUMBER':
        height = font_size * value.value
    elif value.type == 'PERCENTAGE':
        height = font_size * value.value / 100.
    else:
        return # as specified
    style['line-height'] = PropertyValue(str(height) + 'px')


def handle_computed_border_width(element):
    """
    Set border-*-width to zero if border-*-style is none or hidden.
    """
    style = element.style
    for side in ('top', 'right', 'bottom', 'left'):
        if get_value(style, 'border-%s-style' % side) in ('none', 'hidden'):
            style['border-%s-width' % side] = PropertyValue('0')
        else:
            value = get_value(style, 'border-%s-width' % side)
            if value in BORDER_WIDTH_KEYWORDS:
                width = BORDER_WIDTH_KEYWORDS[value]
                style['border-%s-width' % side] = PropertyValue(
                    str(width) + 'px')


def handle_computed_outline_width(element):
    """
    Set outline-width to zero if outline-style is none.
    """
    # TODO: test this
    style = element.style
    if get_value(style, 'outline-style') == 'none':
        style['outline-width'] = PropertyValue('0')
    else:
        value = get_value(style, 'outline-width')
        if value in BORDER_WIDTH_KEYWORDS:
            width = BORDER_WIDTH_KEYWORDS[value]
            style['outline-width'] = PropertyValue(str(width) + 'px')


def handle_computed_display_float(element):
    """
    Computed values of the display and float properties according to
    http://www.w3.org/TR/CSS21/visuren.html#dis-pos-flo
    """
    # TODO: test this
    style = element.style
    if get_value(style, 'display') == 'none':
        # Case 1
        return # position and float do not apply, but leave them
    elif get_value(style, 'position') in ('absolute', 'fixed'):
        # Case 2
        style['float'] = PropertyValue('none')
    elif get_value(style, 'float') == 'none' and element.getparent() is not None:
        # Case 5
        return
    
    # Cases 2, 3, 4
    display = get_value(style, 'display')
    if display == 'inline-table':
        style['display'] = PropertyValue('table')
    elif display in ('inline', 'table-row-group', 'table-column',
                     'table-column-group', 'table-header-group',
                     'table-footer-group', 'table-row', 'table-cell',
                     'table-caption', 'inline-block'):
        style['display'] = PropertyValue('block')
    # else: unchanged


def handle_computed_word_spacing(element):
    """
    word-spacing: normal means zero.
    """
    # TODO: test this
    style = element.style
    # CSS 2.1 says this for word-spacing but not letter-spacing. Why?
    if get_value(style, 'word-spacing') == 'normal':
        style['word-spacing'] = PropertyValue('0')


def handle_computed_font_weight(element):
    """
    Handle keyword values for font-weight.
    """
    # TODO: test this
    style = element.style
    value = get_value(style, 'font-weight')
    if value == 'normal':
        style['font-weight'] = PropertyValue('400')
    elif value == 'bold':
        style['font-weight'] = PropertyValue('700')
    elif value in ('bolder', 'lighter'):
        parent_values = element.getparent().style['font-weight']
        assert len(parent_values) == 1
        assert parent_values[0].type == 'NUMBER'
        parent_value = parent_values[0].value
        style['font-weight'] = PropertyValue(str(
            FONT_WEIGHT_RELATIVE[value] [parent_value]))


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


def handle_computed_content(element):
    # TODO: properly test this
    style = element.style
    if getattr(element, 'pseudo_element_type', '') in ('before', 'after'):
        if get_value(style, 'content') == 'normal':
            style['content'] = PropertyValue('none')
        else:
            parent = element.getparent()
            style['content'] = [compute_content_value(parent, value)
                                for value in style['content']]
    else:
        # CSS 2.1 says it computes to 'normal' for elements, but does not say
        # anything for pseudo-elements other than :before and :after
        # (ie. :first-line and :first-letter)
        # Assume the same as elements.
        style['content'] = PropertyValue('normal')
            

def handle_computed_values(element):
    """
    Normalize values as much as possible without rendering the document.
    """
    # em lengths depend on font-size, compute font-size first
    font_size = handle_computed_font_size(element)
    handle_computed_lengths(element, font_size)
    handle_computed_line_height(element, font_size)
    handle_computed_border_width(element)
    handle_computed_outline_width(element)
    handle_computed_display_float(element)
    handle_computed_word_spacing(element)
    handle_computed_font_weight(element)
    handle_computed_content(element)
    # Recent enough cssutils have a .absolute_uri on URIValue objects.
    # TODO: percentages for height?
    #       http://www.w3.org/TR/CSS21/visudet.html#propdef-height
    # TODO: percentages for vertical-align. What about line-height: normal?
    # TODO: clip

