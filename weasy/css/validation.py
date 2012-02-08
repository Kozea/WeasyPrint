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

from ..logging import LOGGER
from ..formatting_structure import counters
from .values import (get_keyword, get_single_keyword, as_css,
                     make_percentage_value)
from .properties import INITIAL_VALUES, NOT_PRINT_MEDIA
from . import computed_values


# keyword -> (open, insert)
CONTENT_QUOTE_KEYWORDS = {
    'open-quote': (True, True),
    'close-quote': (False, True),
    'no-open-quote': (True, False),
    'no-close-quote': (False, False),
}

BACKGROUND_POSITION_PERCENTAGES = {
    'top': make_percentage_value(0),
    'left': make_percentage_value(0),
    'center': make_percentage_value(50),
    'bottom': make_percentage_value(100),
    'right': make_percentage_value(100),
}


# yes/no validators for non-shorthand properties
# Maps property names to functions taking a property name and a value list,
# returning a value or None for invalid.
# Also transform values: keyword and URLs are returned as strings.
# For properties that take a single value, that value is returned by itself
# instead of a list.
VALIDATORS = {}

EXPANDERS = {}

PREFIXED = set()
# The same replacement was done on property names:
PREFIX = '-weasy-'.replace('-', '_')


class InvalidValues(ValueError):
    """Invalid or unsupported values for a known CSS property."""


# Validators

def validator(property_name=None, prefixed=False):
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
        if prefixed:
            PREFIXED.add(name)
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


def is_angle(value):
    """Return whether the argument is an angle value."""
    return value.type == 'DIMENSION' and \
        value.dimension in computed_values.ANGLE_TO_RADIANS


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
        return 'inherit'


@validator('background-image')
@validator('list-style-image')
@single_value
def image(value):
    """``*-image`` properties validation."""
    if get_keyword(value) == 'none':
        return 'none'
    if value.type == 'URI':
        return value.absoluteUri


@validator('transform-origin', prefixed=True)  # Not in CR yet
@validator()
def background_position(values):
    """``background-position`` property validation.

    See http://www.w3.org/TR/CSS21/colors.html#propdef-background-position

    """
    if len(values) == 1:
        center = BACKGROUND_POSITION_PERCENTAGES['center']
        value = values[0]
        keyword = get_keyword(value)
        if keyword in BACKGROUND_POSITION_PERCENTAGES:
            return BACKGROUND_POSITION_PERCENTAGES[keyword], center
        elif is_dimension_or_percentage(value):
            return value, center

    elif len(values) == 2:
        value_1, value_2 = values
        keyword_1, keyword_2 = map(get_keyword, values)
        if is_dimension_or_percentage(value_1):
            if keyword_2 in ('top', 'center', 'bottom'):
                return value_1, BACKGROUND_POSITION_PERCENTAGES[keyword_2]
            elif is_dimension_or_percentage(value_2):
                return value_1, value_2
        elif is_dimension_or_percentage(value_2):
            if keyword_1 in ('left', 'center', 'right'):
                return BACKGROUND_POSITION_PERCENTAGES[keyword_1], value_2
        elif (keyword_1 in ('left', 'center', 'right') and
              keyword_2 in ('top', 'center', 'bottom')):
            return (BACKGROUND_POSITION_PERCENTAGES[keyword_1],
                    BACKGROUND_POSITION_PERCENTAGES[keyword_2])
        elif (keyword_1 in ('top', 'center', 'bottom') and
              keyword_2 in ('left', 'center', 'right')):
            # Swap values. They need to be in (horizontal, vertical) order.
            return (BACKGROUND_POSITION_PERCENTAGES[keyword_2],
                    BACKGROUND_POSITION_PERCENTAGES[keyword_1])
    #else: invalid


@validator()
@single_keyword
def background_repeat(keyword):
    """``background-repeat`` property validation."""
    return keyword in ('repeat', 'repeat-x', 'repeat-y', 'no-repeat')


@validator()
def background_size(values):
    """Validation for ``background-size``."""
    if len(values) == 1:
        value = values[0]
        keyword = get_keyword(value)
        if keyword in ('contain', 'cover'):
            return keyword
        if keyword == 'auto':
            return ('auto', 'auto')
        if is_dimension_or_percentage(value, negative=False):
            return (value, 'auto')
    elif len(values) == 2:
        new_values = []
        for value in values:
            if get_keyword(value) == 'auto':
                new_values.append('auto')
            elif is_dimension_or_percentage(value, negative=False):
                new_values.append(value)
            else:
                return
        return tuple(values)


@validator('background_clip')
@validator('background_origin')
@single_keyword
def box(keyword):
    """Validation for the ``<box>`` type used in ``background-clip``
    and ``background-origin``."""
    return keyword in ('border-box', 'padding-box', 'content-box')


@validator()
def border_spacing(values):
    """Validator for the `border-spacing` property."""
    if all(is_dimension(value, negative=False) for value in values):
        if len(values) == 1:
            return (values[0], values[0])
        elif len(values) == 2:
            return tuple(values)


@validator('border-top-style')
@validator('border-right-style')
@validator('border-left-style')
@validator('border-bottom-style')
@single_keyword
def border_style(keyword):
    """``border-*-style`` properties validation."""
    return keyword in ('none', 'hidden', 'dotted', 'dashed', 'double',
                       'inset', 'outset', 'groove', 'ridge', 'solid')


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


@validator()
@single_keyword
def box_sizing(keyword):
    """Validation for the ``box-sizing`` property from css3-ui"""
    return keyword in ('padding-box', 'border-box')


@validator()
@single_keyword
def caption_side(keyword):
    """``caption-side`` properties validation."""
    return keyword in ('top', 'bottom')


@validator()
@single_value
def clip(value):
    """Validation for the ``clip`` property."""
    function = parse_function(value)
    if function:
        name, args = function
        if name == 'rect' and len(args) == 4:
            values = []
            for arg in args:
                if get_keyword(arg) == 'auto':
                    values.append('auto')
                elif is_dimension(arg, negative=True):
                    values.append(arg)
                else:
                    raise InvalidValues
            return values
    if get_keyword(value) == 'auto':
        return []


@validator()
def content(values):
    """``content`` property validation."""
    keyword = get_single_keyword(values)
    if keyword in ('normal', 'none'):
        return keyword
    parsed_values = map(validate_content_value, values)
    if None not in parsed_values:
        return parsed_values


def validate_content_value(value):
    """Validation for a signle value for the ``content`` property.

    Return (type, content) or False for invalid values.

    """
    quote_type = CONTENT_QUOTE_KEYWORDS.get(get_keyword(value))
    if quote_type is not None:
        return ('QUOTE', quote_type)

    type_ = value.type
    if type_ == 'STRING':
        return ('STRING', value.value)
    if type_ == 'URI':
        return ('URI', value.absoluteUri)
    function = parse_function(value)
    if function:
        name, args = function
        prototype = (name, [a.type for a in args])
        args = [a.value for a in args]
        if prototype == ('attr', ['IDENT']):
            return (name, args[0])
        elif prototype in (('counter', ['IDENT']),
                           ('counters', ['IDENT', 'STRING'])):
            args.append('decimal')
            return (name, args)
        elif prototype in (('counter', ['IDENT', 'IDENT']),
                           ('counters', ['IDENT', 'STRING', 'IDENT'])):
            style = args[-1]
            if style in ('none', 'decimal') or style in counters.STYLES:
                return (name, args)


def parse_function(value):
    """Return ``(name, args)`` if the given value is a function
    with comma-separated arguments, or None.
    .
    """
    if value.type == 'FUNCTION':
        seq = [e.value for e in value.seq]
        # seq is expected to look like
        # ['name(', ARG_1, ',', ARG_2, ',', ..., ARG_N, ')']
        if (seq[0][-1] == '(' and seq[-1] == ')' and
                all(v == ',' for v in seq[2:-1:2])):
            name = seq[0][:-1]
            args = seq[1:-1:2]
            return name, args


@validator()
def counter_increment(values):
    """``counter-increment`` property validation."""
    return counter(values, default_integer=1)


@validator()
def counter_reset(values):
    """``counter-reset`` property validation."""
    return counter(values, default_integer=0)


def counter(values, default_integer):
    """``counter-increment`` and ``counter-reset`` properties validation."""
    if get_single_keyword(values) == 'none':
        return []
    values = iter(values)
    value = next(values, None)
    if value is None:
        return  # expected at least one value
    results = []
    while value is not None:
        counter_name = get_keyword(value)
        if counter_name is None:
            return  # expected a keyword here
        if counter_name in ('none', 'initial', 'inherit'):
            raise InvalidValues('Invalid counter name: '+ counter_name)
        value = next(values, None)
        if (value is not None and value.type == 'NUMBER' and
                isinstance(value.value, int)):
            # Found an integer. Use it and get the next value
            integer = value.value
            value = next(values, None)
        else:
            # Not an integer. Might be the next counter name.
            # Keep `value` for the next loop iteration.
            integer = default_integer
        results.append((counter_name, integer))
    return results


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
def width_height(value):
    """Validation for the ``width`` and ``height`` properties."""
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
    if keyword in ('inline-block',):
        raise InvalidValues('value not supported yet')
    return keyword in (
        'inline', 'block', 'list-item', 'none',
        'table', 'inline-table', 'table-caption',
        'table-row-group', 'table-header-group', 'table-footer-group',
        'table-row', 'table-column-group', 'table-column', 'table-cell')


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


@validator('letter_spacing')
@validator('word_spacing')
@single_value
def spacing(value):
    """Validation for ``letter-spacing`` and ``word-spacing``."""
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
    return keyword in ('none', 'decimal') or keyword in counters.STYLES


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
@single_value
def opacity(value):
    """Validation for the ``opacity`` property."""
    if value.type == 'NUMBER':
        return min(1, max(0, value.value))


@validator()
@single_keyword
def overflow(keyword):
    """Validation for the ``overflow`` property."""
    return keyword in ('auto', 'visible', 'hidden', 'scroll')


@validator('page-break-before')
@validator('page-break-after')
@single_keyword
def page_break(keyword):
    """Validation for the ``page-break-before`` and ``page-break-after``
    properties.

    """
    if keyword == 'avoid':
        raise InvalidValues('value not supported yet')
    return keyword in ('auto', 'always', 'left', 'right')


# Not very useful, might as well ignore the property anyway.
# Keep it for completeness.
@validator()
@single_keyword
def page_break_inside(keyword):
    """Validation for the ``page-break-inside`` property."""
    if keyword == 'avoid':
        raise InvalidValues('value not supported yet')
    return keyword  ('auto',)


@validator()
@single_keyword
def position(keyword):
    """``position`` property validation."""
    if keyword in ('relative', 'absolute', 'fixed'):
        raise InvalidValues('value not supported yet')
    return keyword in ('static',)


@validator()
def quotes(values):
    """``quotes`` property validation."""
    if (values and len(values) % 2 == 0
            and all(v.type == 'STRING' for v in values)):
        strings = [v.value for v in values]
        # Separate open and close quotes.
        # eg.  ['«', '»', '“', '”']  -> (['«', '“'], ['»', '”'])
        return strings[::2], strings[1::2]


@validator()
@single_keyword
def text_align(keyword):
    """``text-align`` property validation."""
    return keyword in ('left', 'right', 'center', 'justify')


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
    """Validation for the ``vertical-align`` property"""
    if is_dimension_or_percentage(value, negative=True):
        return value
    keyword = get_keyword(value)
    if keyword in ('baseline', 'middle', 'sub', 'super',
                   'text-top', 'text-bottom', 'top', 'bottom'):
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


@validator(prefixed=True)  # Taken from SVG
@single_keyword
def image_rendering(keyword):
    """Validation for ``image-rendering``."""
    return keyword in ('auto', 'optimizeSpeed', 'optimizeQuality')


@validator(prefixed=True)  # Not in CR yet
def size(values):
    """``size`` property validation.

    See http://www.w3.org/TR/css3-page/#page-size-prop

    """
    if is_dimension(values[0]):
        if len(values) == 1:
            return values * 2
        elif len(values) == 2 and is_dimension(values[1]):
            return values

    keywords = map(get_keyword, values)
    if len(keywords) == 1:
        keyword = keywords[0]
        if keyword in ('auto', 'portrait'):
            return INITIAL_VALUES['size']
        elif keyword == 'landscape':
            height, width = INITIAL_VALUES['size']
            return width, height
        elif keyword in computed_values.PAGE_SIZES:
            return computed_values.PAGE_SIZES[keyword]

    if len(keywords) == 2:
        if keywords[0] in ('portrait', 'landscape'):
            orientation, page_size = keywords
        elif keywords[1] in ('portrait', 'landscape'):
            page_size, orientation = keywords
        else:
            page_size = None
        if page_size in computed_values.PAGE_SIZES:
            width_height = computed_values.PAGE_SIZES[page_size]
            if orientation == 'portrait':
                return width_height
            else:
                height, width = width_height
                return width, height


@validator(prefixed=True)  # Not in CR yet
def transform(values):
    if get_single_keyword(values) == 'none':
        return 'none'
    else:
        return map(transform_function, values)


def transform_function(value):
    function = parse_function(value)
    if not function:
        raise InvalidValues
    name, args = function  # cssutils has already made name lower-case

    if len(args) == 1:
        if name in ('rotate', 'skewx', 'skewy') and is_angle(args[0]):
            return name, args[0]
        elif name == 'translatex' and is_dimension_or_percentage(args[0]):
            return 'translate', (args[0], 0)
        elif name == 'translatey' and is_dimension_or_percentage(args[0]):
            return 'translate', (0, args[0])
        elif name == 'scalex' and args[0].type == 'NUMBER':
            return 'scale', (args[0].value, 1)
        elif name == 'scaley' and args[0].type == 'NUMBER':
            return 'scale', (1, args[0].value)
    elif len(args) == 2:
        if name == 'scale' and all(a.type == 'NUMBER' for a in args):
            return name, [arg.value for arg in args]
        if name == 'translate' and all(map(is_dimension_or_percentage, args)):
            return name, args
    elif len(args) == 6 and name == 'matrix' and all(
            a.type == 'NUMBER' for a in args):
        return name, [arg.value for arg in args]
    raise InvalidValues


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
    if name in PREFIXED and not name.startswith(PREFIX):
        level = 'warn'
        reason = ('the property is experimental, use ' +
                  (PREFIX + name).replace('_', '-'))
    elif name in NOT_PRINT_MEDIA:
        level = 'info'
        reason = 'the property does not apply for the print media'
    else:
        if name.startswith(PREFIX):
            unprefixed_name = name[len(PREFIX):]
            if unprefixed_name in PREFIXED:
                name = unprefixed_name
        expander_ = EXPANDERS.get(name, validate_non_shorthand)
        try:
            results = expander_(name, values)
            # Use list() to consume any generator now,
            # so that InvalidValues is caught.
            return list(results)
        except InvalidValues, exc:
            level = 'warn'
            if exc.args and exc.args[0]:
                reason = exc.args[0]
            else:
                reason = 'invalid value'
    getattr(LOGGER, level)('Ignored declaration: `%s: %s`, %s.',
        name.replace('_', '-'), as_css(values), reason)
    return []
