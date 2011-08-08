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


import functools

from .utils import get_keyword
from .inheritance import is_inherit
from .initial_values import INITIAL_VALUES


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


def generic_expander(*suffixes):
    """
    Wrap an expander so that it does not have to handle the 'inherit' case,
    can just yield name suffixes, and missing suffixes get the initial value.
    """
    def decorator(wrapped):
        @functools.wraps(wrapped)
        def wrapper(name, values):
            if is_inherit(values):
                for suffix in suffixes:
                    yield name + suffix, values
                return

            results = {}
            for suffix, values in wrapped(name, values):
                if suffix is None:
                    raise ValueError('Invalid value for %s: %s' %
                                     (name, values))
                assert suffix in suffixes
                assert suffix not in results
                results[suffix] = values

            for suffix in suffixes:
                yield name + suffix, results.get(suffix,
                    INITIAL_VALUES[name + suffix])
        return wrapper
    return decorator


@generic_expander('-type', '-position', '-image')
def expand_list_style(name, values):
    """
    Expand the 'list-style' shorthand property.

    http://www.w3.org/TR/CSS21/generate.html#propdef-list-style
    """
    for value in values:
        keyword = get_keyword(value)
        # TODO: how do we disambiguate -style: none and -image: none?
        if keyword in ('disc', 'circle', 'square', 'decimal',
                       'decimal-leading-zero', 'lower-roman', 'upper-roman',
                       'lower-greek', 'lower-latin', 'upper-latin', 'armenian',
                       'georgian', 'lower-alpha', 'upper-alpha', 'none'):
            suffix = '-type'
        elif keyword in ('inside', 'outside'):
            suffix = '-position'
        elif keyword == 'none' or value.type == 'URI':
            suffix = '-image'
        else:
            suffix = None
        yield suffix, [value]


@generic_expander('-width', '-color', '-style')
def expand_border_side(name, values):
    """
    Expand 'border-top' and such.

    http://www.w3.org/TR/CSS21/box.html#propdef-border-top
    """
    for value in values:
        keyword = get_keyword(value)
        if value.type == 'COLOR_VALUE' or \
                (name == 'outline' and keyword == 'invert'):
            suffix = '-color'
        elif value.type == 'DIMENSION' or \
                keyword in ('thin', 'medium', 'thick'):
            suffix = '-width'
        elif keyword in ('none', 'hidden', 'dotted', 'dashed', 'solid',
                         'double', 'groove', 'ridge', 'inset', 'outset'):
            suffix = '-style'
        else:
            suffix = None
        yield suffix, [value]


def expand_border(name, values):
    """
    Expand the 'border' shorthand.

    http://www.w3.org/TR/CSS21/box.html#propdef-border
    """
    for suffix in ('-top', '-right', '-bottom', '-left'):
        for new_prop in expand_border_side(name + suffix, values):
            yield new_prop


def is_valid_background_positition(value):
    """
    Tell whether the value a valid background-position.
    """
    return (
        value.type in ('DIMENSION', 'PERCENTAGE') or
        (value.type == 'NUMBER' and value.value == 0) or
        get_keyword(value) in ('left', 'right', 'top', 'bottom', 'center')
    )


@generic_expander('-color', '-image', '-repeat', '-attachment', '-position')
def expand_background(name, values):
    """
    Expand the 'background' shorthand.

    http://www.w3.org/TR/CSS21/colors.html#propdef-background
    """
    # Make `values` a stack
    values = list(reversed(values))
    while values:
        value = values.pop()
        keyword = get_keyword(value)
        if value.type == 'COLOR_VALUE':
            suffix = '-color'
        elif keyword == 'none' or value.type == 'URI':
            suffix = '-image'
        elif keyword in ('repeat', 'repeat-x', 'repeat-y', 'no-repeat'):
            suffix = '-repeat'
        elif keyword in ('scroll', 'fixed'):
            suffix = '-attachment'
        elif is_valid_background_positition(value):
            if values:
                next_value = values.pop()
                if is_valid_background_positition(next_value):
                    # Two consecutive '-position' values, yield them together
                    yield '-position', [value, next_value]
                    continue
                else:
                    # The next value is not a '-position', put it back
                    # for the next loop iteration
                    values.append(next_value)
            # A single '-position' value
            suffix = '-position'
        else:
            suffix = None
        yield suffix, [value]


def expand_before_after(name, values):
    if len(values) == 1:
        values *= 2
    elif len(values) != 2:
        raise ValueError('Expected 2 values for %s, got %r.' % (name, values))
    for suffix, value in zip(('-before', '-after'), values):
        yield (name + suffix, value)


def expand_font(name, values):
    # TODO
    # [ [ <'font-style'> || <'font-variant'> || <'font-weight'> ]? <'font-size'> [ / <'line-height'> ]? <'font-family'> ] | caption | icon | menu | message-box | small-caption | status-bar | inherit
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
