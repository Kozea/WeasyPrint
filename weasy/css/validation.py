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
    """Invalid or unsupported values for a known CSS property."""


# Validators

def validator(property_name=None):
    """Decorator adding a function to the ``VALIDATORS``.

    The name of the property covered by the decorated function is set to
    ``property_name`` if given, or is inferred from the function name
    (replacing underscores by hyphens).

    """
    def decorator(function):
        """Add ``function`` to the ``VALIDATORS``."""
        if property_name is None:
            name = function.__name__.replace('_', '-')
        else:
            name = property_name
        assert name in INITIAL_VALUES, name
        assert name not in VALIDATORS, name

        VALIDATORS[name] = function
        return function
    return decorator


def single_keyword(function):
    """Decorator for validators that only accept a single keyword."""
    @functools.wraps(function)
    def keyword_validator(values):
        """Wrap a validator to call get_single_keyword on values."""
        return function(get_single_keyword(values))
    return keyword_validator


def single_value(function):
    """Decorator for validators that only accept a single value."""
    @functools.wraps(function)
    def single_value_validator(values):
        """Validate a property whose value is single."""
        if len(values) != 1:
            return False
        else:
            return function(values[0])
    return single_value_validator


def is_dimension(value, negative=True):
    """Get if ``value`` is a dimension.

    The ``negative`` argument sets wether negative values are allowed.

    """
    type_ = value.type
    # Units may be ommited on zero lenghts.
    return (
        type_ == 'DIMENSION' and (negative or value.value >= 0) and (
            value.dimension in computed_values.LENGTHS_TO_PIXELS or
            value.dimension in ('em', 'ex'))
        ) or (type_ == 'NUMBER' and value.value == 0)


def is_dimension_or_percentage(value, negative=True):
    """Get if ``value`` is a dimension or a percentage.

    The ``negative`` argument sets wether negative values are allowed.

    """
    return is_dimension(value, negative) or (
        value.type == 'PERCENTAGE' and (negative or value.value >= 0))


@validator()
@single_keyword
def background_attachment(keyword):
    """``background-attachment`` property validation."""
    return keyword in ('scroll', 'fixed')


@validator('background-color')
@validator('border-top-color')
@validator('border-right-color')
@validator('border-bottom-color')
@validator('border-left-color')
@validator('color')
@single_value
def color(value):
    """``*-color`` and ``color`` properties validation."""
    return value.type == 'COLOR_VALUE' or get_keyword(value) == 'currentColor'


@validator('background-image')
@validator('list-style-image')
@single_value
def image(value):
    """``*-image`` properties validation."""
    return get_keyword(value) == 'none' or value.type == 'URI'


@validator()
def background_position(values):
    """``background-position`` property validation.

    See http://www.w3.org/TR/CSS21/colors.html#propdef-background-position

    """
    if len(values) == 1:
        value = values[0]
        return (
            is_dimension_or_percentage(value) or
            get_keyword(value) in ('left', 'right', 'top', 'bottom', 'center'))
    if len(values) == 2:
        value_1, value_2 = values
        if is_dimension_or_percentage(value_1):
            return (
                is_dimension_or_percentage(value_2) or
                get_keyword(value_2) in ('top', 'center', 'bottom'))
        elif is_dimension_or_percentage(value_2):
            return get_keyword(value_1) in ('left', 'center', 'right')
        else:
            keyword_1, keyword_2 = map(get_keyword, values)
            return (
                keyword_1 in ('left', 'center', 'right') and
                keyword_2 in ('top', 'center', 'bottom')
            ) or (
                keyword_1 in ('top', 'center', 'bottom') and
                keyword_2 in ('left', 'center', 'right'))
    else:
        return False


@validator()
@single_keyword
def background_repeat(keyword):
    """``background-repeat`` property validation."""
    return keyword in ('repeat', 'repeat-x', 'repeat-y', 'no-repeat')


@validator('border-top-style')
@validator('border-right-style')
@validator('border-left-style')
@validator('border-bottom-style')
@single_keyword
def border_style(keyword):
    """``border-*-style`` properties validation."""
    return keyword in ('none', 'hidden', 'dotted', 'dashed', 'solid',
                       'double', 'groove', 'ridge', 'inset', 'outset')


@validator('border-top-width')
@validator('border-right-width')
@validator('border-left-width')
@validator('border-bottom-width')
@single_value
def border_width(value):
    """``border-*-width`` properties validation."""
    return is_dimension(value, negative=False) or get_keyword(value) in (
        'thin', 'medium', 'thick')


#@validator('top')
#@validator('right')
#@validator('left')
#@validator('bottom')
@validator('margin-top')
@validator('margin-right')
@validator('margin-bottom')
@validator('margin-left')
@single_value
def lenght_precentage_or_auto(value):
    """``margin-*`` properties validation."""
    return (
        is_dimension_or_percentage(value) or
        get_keyword(value) == 'auto')


@validator('height')
@validator('width')
@single_value
def positive_lenght_precentage_or_auto(value):
    """``width`` and ``height`` properties validation."""
    return (
        is_dimension_or_percentage(value, negative=False) or
        get_keyword(value) == 'auto')


@validator()
@single_keyword
def direction(keyword):
    """``direction`` property validation."""
    return keyword in ('ltr', 'rtl')


@validator()
def display(values):
    """``display`` property validation."""
    display_keyword = get_single_keyword(values)
    if display_keyword in (
            'inline-block', 'table', 'inline-table',
            'table-row-group', 'table-header-group', 'table-footer-group',
            'table-row', 'table-column-group', 'table-column', 'table-cell',
            'table-caption'):
        raise InvalidValues('value not supported yet')
    return display_keyword in ('inline', 'block', 'list-item', 'none')


@validator()
def font_family(values):
    """``font-family`` property validation."""
    return all(value.type in ('IDENT', 'STRING') for value in values)


@validator()
@single_value
def font_size(value):
    """``font-size`` property validation."""
    if is_dimension_or_percentage(value):
        return True
    font_size_keyword = get_keyword(value)
    if font_size_keyword in ('smaller', 'larger'):
        raise InvalidValues('value not supported yet')
    return (
        font_size_keyword in computed_values.FONT_SIZE_KEYWORDS #or
        #keyword in ('smaller', 'larger')
    )


@validator()
@single_keyword
def font_style(keyword):
    """``font-style`` property validation."""
    return keyword in ('normal', 'italic', 'oblique')


@validator()
@single_keyword
def font_variant(keyword):
    """``font-variant`` property validation."""
    return keyword in ('normal', 'small-caps')


@validator()
@single_value
def font_weight(value):
    """``font-weight`` property validation."""
    return (
        get_keyword(value) in ('normal', 'bold', 'bolder', 'lighter') or (
            value.type == 'NUMBER' and
            value.value in (100, 200, 300, 400, 500, 600, 700, 800, 900)))


@validator()
@single_value
def letter_spacing(value):
    """``letter-spacing`` property validation."""
    return get_keyword(value) == 'normal' or is_dimension(value)


@validator()
@single_value
def line_height(value):
    """``line-height`` property validation."""
    return get_keyword(value) == 'normal' or (
        value.type in ('NUMBER', 'DIMENSION', 'PERCENTAGE') and
        value.value >= 0)


@validator()
@single_keyword
def list_style_position(keyword):
    """``list-style-position`` property validation."""
    return keyword in ('inside', 'outside')


@validator()
def list_style_type(values):
    """``list-style-type`` property validation."""
    font_size_keyword = get_single_keyword(values)
    if font_size_keyword in ('decimal', 'decimal-leading-zero',
            'lower-roman', 'upper-roman', 'lower-greek', 'lower-latin',
            'upper-latin', 'armenian', 'georgian', 'lower-alpha',
            'upper-alpha'):
        raise InvalidValues('value not supported yet')
    return font_size_keyword in ('disc', 'circle', 'square', 'none')


@validator('padding-top')
@validator('padding-right')
@validator('padding-bottom')
@validator('padding-left')
@single_value
def length_or_precentage(value):
    """``padding-*`` properties validation."""
    return is_dimension_or_percentage(value, negative=False)


@validator()
def position(values):
    """``position`` property validation."""
    position_keyword = get_single_keyword(values)
    if position_keyword in ('relative', 'absolute', 'fixed'):
        raise InvalidValues('value not supported yet')
    return position_keyword in ('static',)


@validator()
def text_align(values):
    """``text-align`` property validation."""
    text_align_keyword = get_single_keyword(values)
    if text_align_keyword in ('right', 'center', 'justify'):
        raise InvalidValues('value not supported yet')
    return text_align_keyword in ('left',)


@validator()
def text_decoration(values):
    """``text-decoration`` property validation."""
    return (
        get_single_keyword(values) == 'none' or
        all(
            get_keyword(value) in (
                'underline', 'overline', 'line-through', 'blink')
            for value in values))


@validator()
@single_keyword
def white_space(keyword):
    """``white-space`` property validation."""
    return keyword in ('normal', 'pre', 'nowrap', 'pre-wrap', 'pre-line')


@validator()
def size(values):
    """``size`` property validation.

    See http://www.w3.org/TR/css3-page/#page-size-prop

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


# Expanders

# Let's be coherent, always use ``name`` as an argument even when it is useless
# pylint: disable=W0613

def expander(property_name):
    """Decorator adding a function to the ``EXPANDERS``."""
    def expander_decorator(function):
        """Add ``function`` to the ``EXPANDERS``."""
        assert property_name not in EXPANDERS, property_name
        EXPANDERS[property_name] = function
        return function
    return expander_decorator


@expander('border-color')
@expander('border-style')
@expander('border-width')
@expander('margin')
@expander('padding')
def expand_four_sides(name, values):
    """Expand properties setting a value for the four sides of a box."""
    # Make sure we have 4 values
    if len(values) == 1:
        values *= 4
    elif len(values) == 2:
        values *= 2  # (bottom, left) defaults to (top, right)
    elif len(values) == 3:
        values.append(values[1])  # left defaults to right
    elif len(values) != 4:
        raise InvalidValues(
            'Expected 1 to 4 value components got %i' % len(values))
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
    """Decorator helping expanders to handle ``inherit`` and ``initial``.

    Wrap an expander so that it does not have to handle the 'inherit' and
    'initial' cases, and can just yield name suffixes. Missing suffixes
    get the initial value.

    """
    def generic_expander_decorator(wrapped):
        """Decorate the ``wrapped`` expander."""
        @functools.wraps(wrapped)
        def generic_expander_wrapper(name, values):
            """Wrap the expander."""
            if get_single_keyword(values) in ('inherit', 'initial'):
                results = dict.fromkeys(expanded_names, values)
            else:
                results = {}
                for new_name, new_values in wrapped(name, values):
                    assert new_name in expanded_names, new_name
                    assert new_name not in results, new_name
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
        return generic_expander_wrapper
    return generic_expander_decorator


@expander('list-style')
@generic_expander('-type', '-position', '-image')
def expand_list_style(name, values):
    """Expand the ``list-style`` shorthand property.

    See http://www.w3.org/TR/CSS21/generate.html#propdef-list-style

    """
    type_specified = image_specified = False
    none_count = 0
    for value in values:
        if get_keyword(value) == 'none':
            # Can be either -style or -image, see at the end which is not
            # otherwise specified.
            none_count += 1
            none_value = value
            continue

        if list_style_type([value]):
            suffix = '-type'
            type_specified = True
        elif list_style_position([value]):
            suffix = '-position'
        elif image([value]):
            suffix = '-image'
            image_specified = True
        else:
            raise InvalidValues
        yield suffix, [value]

    if not type_specified and none_count:
        yield '-type', [none_value]
        none_count -= 1

    if not image_specified and none_count:
        yield '-image', [none_value]
        none_count -= 1

    if none_count:
        # Too many none values.
        raise InvalidValues


@expander('border')
def expand_border(name, values):
    """Expand the ``border`` shorthand property.

    See http://www.w3.org/TR/CSS21/box.html#propdef-border

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
    """Expand the ``border-*`` shorthand properties.

    See http://www.w3.org/TR/CSS21/box.html#propdef-border-top

    """
    for value in values:
        if color([value]):
            suffix = '-color'
        elif border_width([value]):
            suffix = '-width'
        elif border_style([value]):
            suffix = '-style'
        else:
            raise InvalidValues
        yield suffix, [value]


def is_valid_background_positition(value):
    """Tell whether the value is valid for ``background-position``."""
    return (
        value.type in ('DIMENSION', 'PERCENTAGE') or
        (value.type == 'NUMBER' and value.value == 0) or
        get_keyword(value) in ('left', 'right', 'top', 'bottom', 'center'))


@expander('background')
@generic_expander('-color', '-image', '-repeat', '-attachment', '-position')
def expand_background(name, values):
    """Expand the ``background`` shorthand property.

    See http://www.w3.org/TR/CSS21/colors.html#propdef-background

    """
    # Make `values` a stack
    values = list(reversed(values))
    while values:
        value = values.pop()
        if color([value]):
            suffix = '-color'
        elif image([value]):
            suffix = '-image'
        elif background_repeat([value]):
            suffix = '-repeat'
        elif background_attachment([value]):
            suffix = '-attachment'
        elif background_position([value]):
            if values:
                next_value = values.pop()
                if background_position([value, next_value]):
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
            raise InvalidValues
        yield suffix, [value]


@expander('font')
@generic_expander('-style', '-variant', '-weight', '-size',
                  'line-height', '-family')  # line-height is not a suffix
def expand_font(name, values):
    """Expand the ``font`` shorthand property.

    http://www.w3.org/TR/CSS21/fonts.html#font-shorthand
    """
    expand_font_keyword = get_single_keyword(values)
    if expand_font_keyword in ('caption', 'icon', 'menu', 'message-box',
                               'small-caption', 'status-bar'):
        LOGGER.warn(
            'System fonts are not supported, `font: %s` ignored.',
            expand_font_keyword)
        return

    # Make `values` a stack
    values = list(reversed(values))
    # Values for font-style font-variant and font-weight can come in any
    # order and are all optional.
    while values:
        value = values.pop()
        if get_keyword(value) == 'normal':
            # Just ignore 'normal' keywords. Unspecified properties will get
            # their initial value, which is 'normal' for all three here.
            continue

        if font_style([value]):
            suffix = '-style'
        elif font_variant([value]):
            suffix = '-variant'
        elif font_weight([value]):
            suffix = '-weight'
        else:
            # We’re done with these three, continue with font-size
            break
        yield suffix, [value]

    # Then font-size is mandatory
    # Latest `value` from the loop.
    if not font_size([value]):
        raise InvalidValues
    yield '-size', [value]

    # Then line-height is optional, but font-family is not so the list
    # must not be empty yet

    value = values.pop()
    if line_height([value]):
        yield 'line-height', [value]
    else:
        # We pop()ed a font-family, add it back
        values.append(value)

    # Reverse the stack to get normal list
    values.reverse()
    if not font_family(values):
        raise InvalidValues
    yield '-family', values


def validate_non_shorthand(name, values, required=False):
    """Default validator for non-shorthand properties."""
    if not required and name not in INITIAL_VALUES:
        raise InvalidValues('unknown property')

    if not required and name not in VALIDATORS:
        raise InvalidValues('property not supported yet')

    if (get_single_keyword(values) in ('initial', 'inherit') or
            VALIDATORS[name](values)):
        return [(name, values)]
    else:
        raise InvalidValues


def validate_and_expand(name, values):
    """Expand and validate shorthand properties.

    The invalid or unsupported declarations are ignored and logged.

    Return a iterable of ``(name, values)`` tuples.

    """
    # Defaults
    level = 'warn'
    reason = 'invalid value'

    if name in NOT_PRINT_MEDIA:
        level = 'info'
        reason = 'the property does not apply for the print media'
    else:
        expander_ = EXPANDERS.get(name, validate_non_shorthand)
        try:
            results = expander_(name, values)
            # Use list() to consume any generator now,
            # so that InvalidValues is caught.
            return list(results)
        except InvalidValues, exc:
            if exc.args and exc.args[0]:
                reason = exc.args[0]
    getattr(LOGGER, level)('The declaration `%s: %s` was ignored: %s.',
        name, as_css(values), reason)
    return []
