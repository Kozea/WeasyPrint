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


from .utils import get_keyword
from .inheritance import is_inherit


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
    """
    Expand to one or more of *-width, *-style and *-color.
    """
    if is_inherit(values):
        for suffix in ['-width', '-color', '-style']:
            yield name + suffix, values
        return

    results = {}
    for value in values:
        keyword = get_keyword(value)
        if value.type == 'COLOR_VALUE' or (name == 'outline' and
                                           keyword == 'invert'):
            results['-color'] = value
        elif value.type == 'DIMENSION' or keyword in ('thin', 'medium',
                                                      'thick'):
            results['-width'] = value
        elif keyword in ('none', 'hidden', 'dotted', 'dashed', 'solid',
                         'double', 'groove', 'ridge', 'inset', 'outset'):
            results['-style'] = value
        else:
            raise ValueError('Invalid value for %s: %s' % (name, value.value))
    assert results, 'Expected at least one of color, width, style.'
    for suffix, value in results.iteritems():
        yield name + suffix, [value]


def expand_border(name, values):
    """
    Expand the 'border' shorthand.
    """
    for suffix in ('-top', '-right', '-bottom', '-left'):
        for new_prop in expand_border_side(name + suffix, values):
            yield new_prop


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
    'outline': expand_border_side,
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


def expand_name_values(name, values):
    expander = SHORTHANDS.get(name, expand_noop)
    for new_name, new_values in expander(name, list(values)):
        yield new_name, new_values


def expand_shorthand(prop):
    """
    Take a Property object and return an iterable of expanded
    (property_name, property_value) tuples.
    """
    return expand_name_values(prop.name, prop.propertyValue)
