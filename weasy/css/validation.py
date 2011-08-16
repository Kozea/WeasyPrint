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
Validator for all supported properties.

See http://www.w3.org/TR/CSS21/propidx.html for allowed values.

"""
# TODO: unit-test these validators


import functools
import logging

from .values import get_keyword, get_single_keyword, as_css
from .properties import INITIAL_VALUES, NOT_PRINT_MEDIA
from . import computed_values


LOGGER = logging.getLogger('WEASYPRINT')


# yes/no validators for non-shorthand properties
# Maps property names to functions taking a property name and a value list,
# returning True for valid, False for invalid.
VALIDATORS = {}


EXPANDERS = {}


class InvalidValues(ValueError):
    """
    Exception for invalid or unsupported values for a known CSS property.
    """

class NotSupportedYet(InvalidValues):
    def __init__(self):
        super(NotSupportedYet, self).__init__('property not supported yet')


def validator(property_name=None):
    """
    Decorator to add a function to the VALIDATORS dict.
    """
    def decorator(function):
        if property_name is None:
            name = function.__name__.replace('_', '-')
        else:
            name = property_name
        assert name in INITIAL_VALUES, name
        assert name not in VALIDATORS, name

        VALIDATORS[name] = function
        return function
    return decorator


def keyword(function):
    valid_keywords = function()

    @functools.wraps(function)
    def validator(values):
        if get_single_keyword(values) in valid_keywords:
            yield name, values
        else:
            raise InvalidValues
    return validator


def single_value(function):
    @functools.wraps(function)
    def validator(values):
        if len(values) != 1:
            return False
        else:
            return function(values[0])
    return validator


def is_dimension(value):
    type_ = value.type
    # Units may be ommited on zero lenghts.
    return type_ == 'DIMENSION' or (type_ == 'NUMBER' and value.value == 0)


def is_dimension_or_percentage(value):
    type_ = value.type
    return type_ in ('DIMENSION', 'PERCENTAGE') or (
        # Units may be ommited on zero lenghts.
        type_ == 'NUMBER' and value.value == 0)


@validator()
@keyword
def background_attachment():
    return 'scroll', 'fixed'


@validator('background-color')
@validator('border-top-color')
@validator('border-right-color')
@validator('border-bottom-color')
@validator('border-left-color')
@validator('color')
@single_value
def color(value):
    return value.type == 'COLOR_VALUE' or get_keyword(value) == 'currentColor'


@validator('background-image')
@validator('list-style-image')
@single_value
def image(value):
    return get_keyword(value) == 'none' or value.type == 'URI'


@validator()
def background_position(values):
    """
    http://www.w3.org/TR/CSS21/colors.html#propdef-background-position
    """
    if len(values) == 1:
        value = values[0]
        if is_dimension_or_percentage(value):
            return True
        keyword = get_keyword(value)
        return keyword in ('left', 'right', 'top', 'bottom', 'center')
    if len(values) == 2:
        value_1, value_2 = values
        if is_dimension_or_percentage(value_1):
            return (
                is_dimension_or_percentage(value_2) or
                get_keyword(value_2) in ('top', 'center', 'bottom')
            )
        elif is_dimension_or_percentage(value_2):
            return get_keyword(value_1) in ('left', 'center', 'right')
        else:
            keyword_1, keyword_2 = map(get_keyword, values)
            return (
                keyword_1 in ('left', 'center', 'right') and
                keyword_2 in ('top', 'center', 'bottom')
            ) or (
                keyword_1 in ('top', 'center', 'bottom') and
                keyword_2 in ('left', 'center', 'right')
            )
    else:
        return False


@validator()
@keyword
def background_repeat():
    return 'repeat', 'repeat-x', 'repeat-y', 'no-repeat'


@validator('border-top-style')
@validator('border-right-style')
@validator('border-left-style')
@validator('border-bottom-style')
@keyword
def border_style():
    return ('none', 'hidden', 'dotted', 'dashed', 'solid',
            'double', 'groove', 'ridge', 'inset', 'outset')


@validator('border-top-width')
@validator('border-right-width')
@validator('border-left-width')
@validator('border-bottom-width')
@single_value
def border_width(value):
    return is_dimension(value) or get_keyword(value) in (
        'thin', 'medium', 'thick')


@validator()
def content(values):
    # TODO: implement validation for 'content'
    return True


#@validator('top')
#@validator('right')
#@validator('left')
#@validator('bottom')
@validator('height')
@validator('width')
@validator('margin-top')
@validator('margin-right')
@validator('margin-bottom')
@validator('margin-left')
@single_value
def lenght_precentage_or_auto(value):
    return (
        is_dimension_or_percentage(value) or
        get_keyword(value) == 'auto'
    )


@validator()
@keyword
def direction():
    return 'ltr', 'rtl'


@validator()
def display(values):
    keyword = get_single_keyword(values)
    if keyword in (
        'list-item', 'table', 'inline-table',
        'table-row-group', 'table-header-group', 'table-footer-group',
        'table-row', 'table-column-group', 'table-column', 'table-cell',
        'table-caption'
    ):
        raise InvalidValues
    return keyword in ('inline', 'block', 'inline-block', 'none')


@validator()
def font_family(values):
    return all(value.type in ('IDENT', 'STRING') for value in values)


@validator()
@single_value
def font_size(value):
    if is_dimension_or_percentage(value):
        return True
    keyword = get_keyword(value)
    return (
        keyword in computed_values.FONT_SIZE_KEYWORDS or
        keyword in ('smaller', 'larger')
    )


@validator()
@keyword
def font_style():
    return 'normal', 'italic', 'oblique'


@validator()
@keyword
def font_variant():
    return 'normal', 'small-caps'


@validator()
@single_value
def font_weight(value):
    return (
        get_keyword(value) in ('normal', 'bold', 'bolder', 'lighter') or
        value.type == 'NUMBER' and value.value in (100, 200, 300, 400, 500,
                                                   600, 700, 800, 900)
    )


@validator('letter-spacing')
@single_value
def letter_spacing(value):
    return get_keyword(value) == 'normal' or is_dimension(value)


@validator()
@single_value
def line_height(value):
    return get_keyword(value) == 'normal' or value.type in (
        'NUMBER', 'DIMENSION', 'PERCENTAGE')


@validator()
@keyword
def list_style_position():
    return 'inside', 'outside'


@validator()
@keyword
def list_style_type():
    return ('disc', 'circle', 'square', 'decimal', 'decimal-leading-zero',
            'lower-roman', 'upper-roman', 'lower-greek', 'lower-latin',
            'upper-latin', 'armenian', 'georgian', 'lower-alpha',
            'upper-alpha', 'none')


@validator('padding-top')
@validator('padding-right')
@validator('padding-bottom')
@validator('padding-left')
@single_value
def lenght_or_precentage(value):
    return is_dimension_or_percentage(value)


@validator()
def position(values):
    keyword = get_single_keyword(values)
    if keyword in ('relative', 'absolute', 'fixed'):
        raise InvalidValues
    return keyword in ('static',)


@validator()
def text_align(values):
    keyword = get_single_keyword(values)
    if keyword in ('right', 'center', 'justify'):
        raise InvalidValues
    return keyword in ('left',)


@validator()
def text_decoration(values):
    return (
        get_single_keyword(values) == 'none' or
        all(
            get_keyword(value) in ('underline', 'overline', 'line-through',
                                   'blink')
            for value in values
        )
    )


@validator()
@keyword
def white_space():
    return 'normal', 'pre', 'nowrap', 'pre-wrap', 'pre-line'


@validator()
def size(values):
    """
    http://www.w3.org/TR/css3-page/#page-size-prop
    """
    return (
        len(values) == 1 and (
            is_dimension(values[0]) or
            get_single_keyword(values) in ('auto', 'portrait', 'landscape') or
            get_single_keyword(values) in computed_values.PAGE_SIZES
        )
    ) or (
        len(values) == 2 and (
            all(is_dimension(value) for value in values) or (
                get_keyword(values[0]) in ('portrait', 'landscape') and
                get_keyword(values[1]) in computed_values.PAGE_SIZES
            ) or (
                get_keyword(values[0]) in computed_values.PAGE_SIZES and
                get_keyword(values[1]) in ('portrait', 'landscape')
            )
        )
    )


def expander(property_name):
    """
    Decorator to add a function to the EXPANDERS dict.
    """
    def decorator(function):
        assert property_name not in EXPANDERS, property_name
        EXPANDERS[property_name] = function
        return function
    return decorator


@expander('border-color')
@expander('border-style')
@expander('border-width')
@expander('margin')
@expander('padding')
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
        raise InvalidValues('Expected 1 to 4 value components got %i'
            % len(values))
    for suffix, value in zip(('-top', '-right', '-bottom', '-left'), values):
        i = name.rfind('-')
        if i == -1:
            new_name = name + suffix
        else:
            # eg. border-color becomes border-*-color, not border-color-*
            new_name = name[:i] + suffix + name[i:]

        values = [value]
        validate_non_shorthand(new_name, values, required=True)
        yield new_name, values


def generic_expander(*expanded_names):
    """
    Wrap an expander so that it does not have to handle the 'inherit' and
    'initial' cases, and can just yield name suffixes. Missing suffixes
    get the initial value.
    """
    def decorator(wrapped):
        @functools.wraps(wrapped)
        def wrapper(name, values):
            if get_single_keyword(values) in ('inherit', 'initial'):
                results = dict.fromkeys(expanded_names, values)
            else:
                results = {}
                for new_name, new_values in wrapped(name, values):
                    if new_name is None:
                        raise ValueError('Invalid value for %s: %s' %
                                         (name, values))
                    assert new_name in expanded_names
                    assert new_name not in results
                    results[new_name] = new_values

            for new_name in expanded_names:
                if new_name.startswith('-'):
                    # new_name is a suffix
                    actual_new_name = name + new_name
                else:
                    actual_new_name = new_name

                if new_name in results:
                    values = results[new_name]
                else:
                    values = INITIAL_VALUES[actual_new_name]
                validate_non_shorthand(actual_new_name, values, required=True)
                yield actual_new_name, values
        return wrapper
    return decorator


@expander('list-style')
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


@expander('border')
def expand_border(name, values):
    """
    Expand the 'border' shorthand.

    http://www.w3.org/TR/CSS21/box.html#propdef-border
    """
    for suffix in ('-top', '-right', '-bottom', '-left'):
        for new_prop in expand_border_side(name + suffix, values):
            yield new_prop


@expander('border-top')
@expander('border-right')
@expander('border-bottom')
@expander('border-left')
@generic_expander('-width', '-color', '-style')
def expand_border_side(name, values):
    """
    Expand 'border-top' and such.

    http://www.w3.org/TR/CSS21/box.html#propdef-border-top
    """
    for value in values:
        keyword = get_keyword(value)
        if value.type == 'COLOR_VALUE':
            suffix = '-color'
        elif value.type == 'DIMENSION' or \
                value.type == 'NUMBER' and value.value == 0 or \
                keyword in ('thin', 'medium', 'thick'):
            suffix = '-width'
        elif keyword in ('none', 'hidden', 'dotted', 'dashed', 'solid',
                         'double', 'groove', 'ridge', 'inset', 'outset'):
            suffix = '-style'
        else:
            suffix = None
        yield suffix, [value]


def is_valid_background_positition(value):
    """
    Tell whether the value a valid background-position.
    """
    return (
        value.type in ('DIMENSION', 'PERCENTAGE') or
        (value.type == 'NUMBER' and value.value == 0) or
        get_keyword(value) in ('left', 'right', 'top', 'bottom', 'center')
    )


@expander('background')
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


@expander('font')
@generic_expander('-style', '-variant', '-weight', '-size',
                  'line-height', '-family')  # line-height is not a suffix
def expand_font(name, values):
    """
    Expand the 'font' shorthand.

    http://www.w3.org/TR/CSS21/fonts.html#font-shorthand
    """
    keyword = get_single_keyword(values)
    if keyword in ('caption', 'icon', 'menu', 'message-box',
                   'small-caption', 'status-bar'):
        # System fonts are not supported, use initial values
        # TODO: warn?
        return

    # Make `values` a stack
    values = list(reversed(values))
    # Values for font-style font-variant and font-weight can come in any
    # order and are all optional.
    while values:
        value = values.pop()
        keyword = get_keyword(value)
        # TODO: how do we decide which suffix is 'normal'?
        if keyword in ('normal', 'italic', 'oblique'):
            suffix = '-style'
        elif keyword in ('normal', 'small-caps'):
            suffix = '-variant'
        elif keyword in ('normal', 'bold', 'bolder', 'lighter') or \
                value.type == 'NUMBER':
            suffix = '-weight'
        else:
            break
        yield suffix, [value]

    # Then font-size is mandatory

    # Import here to avoid a circular dependency
    from .computed_values import FONT_SIZE_KEYWORDS

    # Latest `value` and `keyword` from the loop.
    assert (
        value.type in ('DIMENSION', 'PERCENTAGE') or
        keyword in FONT_SIZE_KEYWORDS or
        keyword in ('smaller', 'larger')
    )
    yield '-size', [value]

    # Then line-height is optional, but font-family is not so the list
    # must not be empty yet

    value = values.pop()
    if get_keyword(value) == 'normal' or value.type in (
            'DIMENSION', 'NUMBER', 'PERCENTAGE'):
        yield 'line-height', [value]
    else:
        # We pop()ed a font-family, add it back
        values.append(value)

    # Just assume that everything else is a valid font-family.
    # TODO: we should split on commas only. Eg. a sequence of
    # space-separated keywords is only one family-name.
    # See http://www.w3.org/TR/CSS21/fonts.html#propdef-font-family

    # Reverse the stack to get normal list
    values.reverse()
    yield '-family', values


def validate_non_shorthand(name, values, required=False):
    if not required and name not in INITIAL_VALUES:
        raise InvalidValues('unknown property')

    if not required and name not in VALIDATORS:
        raise InvalidValues('property not supported yet')

    if (
        get_single_keyword(values) in ('initial', 'inherit') or
        # TODO: refuse negative values for some properties.
        VALIDATORS[name](values)
    ):
        return [(name, values)]
    else:
        raise InvalidValues


def validate_and_expand(name, values):
    """
    Ignore and log invalid or unsupported declarations, and expand shorthand
    properties.

    Return a iterable of (name, values) tuples.
    """
    # Defaults
    level = 'warn'
    reason = 'invalid value'

    if name in NOT_PRINT_MEDIA:
        level = 'info'
        reason = 'the property does not apply for the print media'
    else:
        try:
            expander = EXPANDERS.get(name, validate_non_shorthand)
            results = expander(name, values)
            # Use list() to consume any generator now,
            # so that InvalidValues is caught.
            return list(results)
        except InvalidValues, exc:
            if exc.args and exc.args[0]:
                reason = exc.args[0]
    getattr(LOGGER, level)('The declaration `%s: %s` was ignored: %s.',
        name, as_css(values), reason)
    return []
