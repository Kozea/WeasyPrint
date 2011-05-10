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


from cssutils.css import PropertyValue, DimensionValue
from . import properties


def get_value(style, name):
    """
    Return the value of a property as a string, defaulting to 'initial'.
    """
    if name not in style:
        return 'initial'
    values = style[name]
    if hasattr(values, 'value'):
        return values.value
    else:
        return ' '.join(value.cssText for value in values)


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
        parent_value_text = properties.INITIAL_VALUES['font-size'].value
        # Initial is medium
        parent_font_size = properties.FONT_SIZE_KEYWORDS[parent_value_text]

    assert len(element.style['font-size']) == 1
    value = element.style['font-size'][0]
    value_text = value.value
    
    # TODO: once we ignore invalid declarations, turn these ValueError’s into
    # assert False, 'Declaration should have been ignored'
    if value_text in properties.FONT_SIZE_KEYWORDS:
        font_size = properties.FONT_SIZE_KEYWORDS[value_text]
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
        elif value.dimension in properties.LENGTHS_TO_PIXELS:
            factor = properties.LENGTHS_TO_PIXELS[value.dimension]
            font_size = value.value * factor
        else:
            raise ValueError('Unknown length unit for font-size:', values_text)
    else:
        raise ValueError('Invalid value for font-size:', values_text)

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
    if value.dimension in properties.LENGTHS_TO_PIXELS:
        # Convert absolute lengths to pixels
        factor = properties.LENGTHS_TO_PIXELS[value.dimension]
        return DimensionValue(str(value.value * factor) + 'px')
    elif value.dimension == 'em':
        return DimensionValue(str(value.value * font_size) + 'px')
    elif value.dimension == 'ex':
        # TODO: support ex
        raise ValueError('The ex unit is not supported yet.', name,
            values.value)
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
            if value in properties.BORDER_WIDTH_KEYWORDS:
                width = properties.BORDER_WIDTH_KEYWORDS[value]
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
        if value in properties.BORDER_WIDTH_KEYWORDS:
            width = properties.BORDER_WIDTH_KEYWORDS[value]
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
            properties.FONT_WEIGHT_RELATIVE[value] [parent_value]))


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
    # TODO: percentages for height?
    #       http://www.w3.org/TR/CSS21/visudet.html#propdef-height
    # TODO: percentages for vertical-align. What about line-height: normal?
    # TODO: clip, content

