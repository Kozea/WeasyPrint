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
    Expand shorthand properties.
    eg. margin becomes margin-top, margin-right, margin-bottom and margin-left.
"""


class DummyPropertyValue(list):
    """
    A list that quacks like a PropertyValue.
    """

    @property
    def value(self):
        return ' '.join(value.cssText for value in self)


def expand_four_sides(name, values):
    """
    Expand properties that set a value for each of the four sides of a box.
    """
    # Make sure we have 4 values
    if len(values) == 1:
        values *= 4
    elif len(values) == 2:
        values *= 2 # (bottom, left) defaults to (top, right)
    elif len(values) == 3:
        values.append(values[1]) # left defaults to right
    elif len(values) != 4:
        raise ValueError('Expected 1 to 4 value components for %s, got "%s"'
            % (name, values))
    for suffix, value in zip(('-top', '-right', '-bottom', '-left'), values):
        i = name.rfind('-')
        if i == -1:
            new_name = name + suffix
        else:
            # eg. border-color becomes border-*-color, not border-color-*
            new_name = name[:i] + suffix + name[i:]
        yield (new_name, [value])


def expand_border_side(name, values):
    # TODO
    # http://www.w3.org/TR/CSS21/box.html#border-shorthand-properties
    # Defined as:
    # 	[ <border-width> || <border-style> || <'border-top-color'> ] | inherit
    # With || meaning 'one or more of them, in any order' so we need to actuylly
    # look at the values to decide which is which
    # http://www.w3.org/TR/CSS21/about.html#value-defs
    raise NotImplementedError


def expand_border(name, values):
    for suffix in ('-top', '-right', '-bottom', '-left'):
        for new_prop in expand_border_side(name + suffix, values):
            yield new_prop


def expand_outline(name, values):
    # TODO. See expand_border_side
    # 	[ <'outline-color'> || <'outline-style'> || <'outline-width'> ] | inherit
    raise NotImplementedError


def expand_before_after(name, values):
    if len(values) == 1:
        values *= 2
    elif len(values) != 2:
        raise ValueError('Expected 2 values for %s, got %r.' % (name, values))
    for suffix, value in zip(('-before', '-after'), values):
        yield (name + suffix, value)


def expand_background(name, values):
    # TODO
    # 	[<'background-color'> || <'background-image'> || <'background-repeat'> || <'background-attachment'> || <'background-position'>] | inherit
    raise NotImplementedError


def expand_font(name, values):
    # TODO
    # [ [ <'font-style'> || <'font-variant'> || <'font-weight'> ]? <'font-size'> [ / <'line-height'> ]? <'font-family'> ] | caption | icon | menu | message-box | small-caption | status-bar | inherit
    raise NotImplementedError


def expand_list_style(name, values):
    # TODO
    # 	[ <'list-style-type'> || <'list-style-position'> || <'list-style-image'> ] | inherit
    raise NotImplementedError


SHORTHANDS = {
    'margin': expand_four_sides,
    'padding': expand_four_sides,
    'border-color': expand_four_sides,
    'border-width': expand_four_sides,
    'border-style': expand_four_sides,
    'border-top': expand_border_side,
    'border-right': expand_border_side,
    'border-bottom': expand_border_side,
    'border-left': expand_border_side,
    'border': expand_border,
    'outline': expand_outline,
    'cue': expand_before_after,
    'pause': expand_before_after,
    'background': expand_background,
    'font': expand_font,
    'list-style': expand_list_style,
}


def expand_noop(name, values):
    """
    The expander for non-shorthand properties: returns the input unmodified.
    """
    yield name, values


def expand_shorthand(prop):
    """
    Take a Property object and return an iterable of expanded
    (property_name, property_value) tuples.
    """
    expander = SHORTHANDS.get(prop.name, expand_noop)
    for name, value_list in expander(prop.name, list(prop.propertyValue)):
        yield name, DummyPropertyValue(value_list)
