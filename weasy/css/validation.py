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
# returning a value or None for invalid.
# Also transform values: keyword and URLs are returned as strings.
# For properties that take a single value, that value is returned by itself
# instead of a list.
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
            name = function.__name__
        else:
            name = property_name.replace('-', '_')
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
        keyword = get_single_keyword(values)
        if function(keyword):
            return keyword
    return keyword_validator


def single_value(function):
    """Decorator for validators that only accept a single value."""
    @functools.wraps(function)
    def single_value_validator(values):
        """Validate a property whose value is single."""
        if len(values) == 1:
            return function(values[0])
    single_value_validator.__func__ = function
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
    if value.type == 'COLOR_VALUE':
        return value
    if get_keyword(value) == 'currentColor':
        return 'currentColor'


@validator('background-image')
@validator('list-style-image')
@single_value
def image(value):
    """``*-image`` properties validation."""
    if get_keyword(value) == 'none':
        return 'none'
    if value.type == 'URI':
        return value.absoluteUri


@validator()
def background_position(values):
    """``background-position`` property validation.

    See http://www.w3.org/TR/CSS21/colors.html#propdef-background-position

    """
    if len(values) == 1:
        value = values[0]
        keyword = get_keyword(value)
        if keyword in ('left', 'right', 'top', 'bottom', 'center'):
            return keyword, 'center'
        elif is_dimension_or_percentage(value):
            return value, 'center'

    elif len(values) == 2:
        value_1, value_2 = values
        keyword_1, keyword_2 = map(get_keyword, values)
        if is_dimension_or_percentage(value_1):
            if keyword_2 in ('top', 'center', 'bottom'):
                return value_1, keyword_2
            elif is_dimension_or_percentage(value_2):
                return value_1, value_2
        elif is_dimension_or_percentage(value_2):
            if keyword_1 in ('left', 'center', 'right'):
                return keyword_1, value_2
        elif (
                    keyword_1 in ('left', 'center', 'right') and
                    keyword_2 in ('top', 'center', 'bottom')
                ) or (
                    keyword_1 in ('top', 'center', 'bottom') and
                    keyword_2 in ('left', 'center', 'right')
                ):
            return keyword_1, keyword_2
    #else: invalid


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
    if keyword in ('double', 'groove', 'ridge', 'inset', 'outset'):
        raise InvalidValues('value not supported yet')
    return keyword in ('none', 'hidden', 'dotted', 'dashed', 'solid')


@validator('border-top-width')
@validator('border-right-width')
@validator('border-left-width')
@validator('border-bottom-width')
@single_value
def border_width(value):
    """``border-*-width`` properties validation."""
    if is_dimension(value, negative=False):
        return value
    keyword = get_keyword(value)
    if keyword in ('thin', 'medium', 'thick'):
        return keyword


#@validator('top')
#@validator('right')
#@validator('left')
#@validator('bottom')
@validator('margin-top')
@validator('margin-right')
@validator('margin-bottom')
@validator('margin-left')
@single_value
def lenght_precentage_or_auto(value, negative=True):
    """``margin-*`` properties validation."""
    if is_dimension_or_percentage(value, negative):
        return value
    if get_keyword(value) == 'auto':
        return 'auto'


@validator('height')
@validator('width')
@single_value
def positive_lenght_precentage_or_auto(value):
    return lenght_precentage_or_auto.__func__(value, negative=False)


@validator()
@single_keyword
def direction(keyword):
    """``direction`` property validation."""
    return keyword in ('ltr', 'rtl')


@validator()
@single_keyword
def display(keyword):
    """``display`` property validation."""
    if keyword in (
            'inline-block', 'table', 'inline-table',
            'table-row-group', 'table-header-group', 'table-footer-group',
            'table-row', 'table-column-group', 'table-column', 'table-cell',
            'table-caption'):
        raise InvalidValues('value not supported yet')
    return keyword in ('inline', 'block', 'list-item', 'none')


@validator()
def font_family(values):
    """``font-family`` property validation."""
    # TODO: we should split on commas only.
    # " If a sequence of identifiers is given as a font family name, the
    #   computed value is the name converted to a string by joining all the
    #   identifiers in the sequence by single spaces. "
    # http://www.w3.org/TR/CSS21/fonts.html#font-family-prop
    # eg. `font-family: Foo  bar, "baz
    if all(value.type in ('IDENT', 'STRING') for value in values):
        return [value.value for value in values]


@validator()
@single_value
def font_size(value):
    """``font-size`` property validation."""
    if is_dimension_or_percentage(value):
        return value
    font_size_keyword = get_keyword(value)
    if font_size_keyword in ('smaller', 'larger'):
        raise InvalidValues('value not supported yet')
    if (
        font_size_keyword in computed_values.FONT_SIZE_KEYWORDS #or
        #keyword in ('smaller', 'larger')
    ):
        return font_size_keyword


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
    keyword = get_keyword(value)
    if keyword in ('normal', 'bold', 'bolder', 'lighter'):
        return keyword
    if value.type == 'NUMBER':
        value = value.value
        if value in [100, 200, 300, 400, 500, 600, 700, 800, 900]:
            return value


#@validator()  XXX not supported yet
@single_value
def letter_spacing(value):
    """``letter-spacing`` property validation."""
    if get_keyword(value) == 'normal':
        return 'normal'
    if is_dimension(value):
        return value


@validator()
@single_value
def line_height(value):
    """``line-height`` property validation."""
    if get_keyword(value) == 'normal':
        return 'normal'
    if (value.type in ('NUMBER', 'DIMENSION', 'PERCENTAGE') and
            value.value >= 0):
        return value


@validator()
@single_keyword
def list_style_position(keyword):
    """``list-style-position`` property validation."""
    return keyword in ('inside', 'outside')


@validator()
@single_keyword
def list_style_type(keyword):
    """``list-style-type`` property validation."""
    if keyword in ('decimal', 'decimal-leading-zero',
            'lower-roman', 'upper-roman', 'lower-greek', 'lower-latin',
            'upper-latin', 'armenian', 'georgian', 'lower-alpha',
            'upper-alpha'):
        raise InvalidValues('value not supported yet')
    return keyword in ('disc', 'circle', 'square', 'none')


@validator('padding-top')
@validator('padding-right')
@validator('padding-bottom')
@validator('padding-left')
@single_value
def length_or_precentage(value):
    """``padding-*`` properties validation."""
    if is_dimension_or_percentage(value, negative=False):
        return value


@validator()
@single_keyword
def position(keyword):
    """``position`` property validation."""
    if keyword in ('relative', 'absolute', 'fixed'):
        raise InvalidValues('value not supported yet')
    return keyword in ('static',)


@validator()
@single_keyword
def text_align(keyword):
    """``text-align`` property validation."""
    if keyword in ('justify',):
        raise InvalidValues('value not supported yet')
    return keyword in ('left', 'right', 'center')


@validator()
def text_decoration(values):
    """``text-decoration`` property validation."""
    keywords = map(get_keyword, values)
    if keywords == ['none']:
        return 'none'
    if all(keyword in ('underline', 'overline', 'line-through', 'blink')
            for keyword in keywords):
        unique = frozenset(keywords)
        if len(unique) == len(keywords):
            # No duplicate
            return unique


@validator()
@single_value
def text_indent(value):
    """``text-indent`` property validation."""
    if is_dimension_or_percentage(value, negative=True):
        return value


@validator()
@single_keyword
def text_transform(keyword):
    """``text-align`` property validation."""
    return keyword in ('none', 'uppercase', 'lowercase', 'capitalize')


@validator()
@single_value
def vertical_align(value):
    if is_dimension_or_percentage(value, negative=True):
        return value
    keyword = get_keyword(value)
    if keyword in ('middle', 'sub', 'sup', 'text-top', 'text-bottom',
                   'top', 'bottom'):
        raise InvalidValues('value not supported yet')
    if keyword in ('baseline',):
        return keyword


@validator()
@single_keyword
def visibility(keyword):
    """``white-space`` property validation."""
    return keyword in ('visible', 'hidden', 'collapse')


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
    if len(values) == 1:
        if is_dimension(values[0]):
            return values
        keyword = get_single_keyword(values)
        if (keyword in ('auto', 'portrait', 'landscape') or
                keyword in computed_values.PAGE_SIZES):
            return values
    if len(values) == 2:
        if all(is_dimension(value) for value in values):
            return values
        keywords = map(get_keyword, values)
        if (
            keywords[0] in ('portrait', 'landscape') and
            keywords[1] in computed_values.PAGE_SIZES
        ) or (
            keywords[0] in computed_values.PAGE_SIZES and
            keywords[1] in ('portrait', 'landscape')
        ):
            return values


# Expanders

# Let's be consistent, always use ``name`` as an argument even
# when it is useless.
# pylint: disable=W0613

def expander(property_name):
    """Decorator adding a function to the ``EXPANDERS``."""
    property_name = property_name.replace('-', '_')
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
    for suffix, value in zip(('_top', '_right', '_bottom', '_left'), values):
        i = name.rfind('_')
        if i == -1:
            new_name = name + suffix
        else:
            # eg. border-color becomes border-*-color, not border-color-*
            new_name = name[:i] + suffix + name[i:]

        # validate_non_shorthand returns [(name, value)], we want
        # to yield (name, value)
        result, = validate_non_shorthand(new_name, [value], required=True)
        yield result


def generic_expander(*expanded_names):
    """Decorator helping expanders to handle ``inherit`` and ``initial``.

    Wrap an expander so that it does not have to handle the 'inherit' and
    'initial' cases, and can just yield name suffixes. Missing suffixes
    get the initial value.

    """
    expanded_names = [name.replace('-', '_') for name in expanded_names]
    def generic_expander_decorator(wrapped):
        """Decorate the ``wrapped`` expander."""
        @functools.wraps(wrapped)
        def generic_expander_wrapper(name, values):
            """Wrap the expander."""
            keyword = get_single_keyword(values)
            if keyword in ('inherit', 'initial'):
                results = dict.fromkeys(expanded_names, keyword)
                skip_validation = True
            else:
                skip_validation = False
                results = {}
                for new_name, new_values in wrapped(name, values):
                    assert new_name in expanded_names, new_name
                    assert new_name not in results, new_name
                    results[new_name] = new_values

            for new_name in expanded_names:
                if new_name.startswith('_'):
                    # new_name is a suffix
                    actual_new_name = name + new_name
                else:
                    actual_new_name = new_name

                if new_name in results:
                    values = results[new_name]
                    if not skip_validation:
                        # validate_non_shorthand returns [(name, value)]
                        (actual_new_name, values), = validate_non_shorthand(
                            actual_new_name, values, required=True)
                else:
                    values = INITIAL_VALUES[actual_new_name]

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

        if list_style_type([value]) is not None:
            suffix = '_type'
            type_specified = True
        elif list_style_position([value]) is not None:
            suffix = '_position'
        elif image([value]) is not None:
            suffix = '_image'
            image_specified = True
        else:
            raise InvalidValues
        yield suffix, [value]

    if not type_specified and none_count:
        yield '_type', [none_value]
        none_count -= 1

    if not image_specified and none_count:
        yield '_image', [none_value]
        none_count -= 1

    if none_count:
        # Too many none values.
        raise InvalidValues


@expander('border')
def expand_border(name, values):
    """Expand the ``border`` shorthand property.

    See http://www.w3.org/TR/CSS21/box.html#propdef-border

    """
    for suffix in ('_top', '_right', '_bottom', '_left'):
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
        if color([value]) is not None:
            suffix = '_color'
        elif border_width([value]) is not None:
            suffix = '_width'
        elif border_style([value]) is not None:
            suffix = '_style'
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
        if color([value]) is not None:
            suffix = '_color'
        elif image([value]) is not None:
            suffix = '_image'
        elif background_repeat([value]) is not None:
            suffix = '_repeat'
        elif background_attachment([value]) is not None:
            suffix = '_attachment'
        elif background_position([value]):
            if values:
                next_value = values.pop()
                if background_position([value, next_value]):
                    # Two consecutive '-position' values, yield them together
                    yield '_position', [value, next_value]
                    continue
                else:
                    # The next value is not a '-position', put it back
                    # for the next loop iteration
                    values.append(next_value)
            # A single '-position' value
            suffix = '_position'
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

        if font_style([value]) is not None:
            suffix = '_style'
        elif font_variant([value]) is not None:
            suffix = '_variant'
        elif font_weight([value]) is not None:
            suffix = '_weight'
        else:
            # We’re done with these three, continue with font-size
            break
        yield suffix, [value]

    # Then font-size is mandatory
    # Latest `value` from the loop.
    if font_size([value]) is None:
        raise InvalidValues
    yield '_size', [value]

    # Then line-height is optional, but font-family is not so the list
    # must not be empty yet
    if not values:
        raise InvalidValues

    value = values.pop()
    if line_height([value]) is not None:
        yield 'line_height', [value]
    else:
        # We pop()ed a font-family, add it back
        values.append(value)

    # Reverse the stack to get normal list
    values.reverse()
    if font_family(values) is None:
        raise InvalidValues
    yield '_family', values


def validate_non_shorthand(name, values, required=False):
    """Default validator for non-shorthand properties."""
    if not required and name not in INITIAL_VALUES:
        raise InvalidValues('unknown property')

    if not required and name not in VALIDATORS:
        raise InvalidValues('property not supported yet')

    keyword = get_single_keyword(values)
    if keyword in ('initial', 'inherit'):
        value = keyword
    else:
        value = VALIDATORS[name](values)
        if value is None:
            raise InvalidValues
    return [(name, value)]


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
