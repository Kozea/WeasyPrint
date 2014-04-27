# coding: utf8
"""
    weasyprint.css.validation
    -------------------------

    Expand shorthands and validate property values.
    See http://www.w3.org/TR/CSS21/propidx.html and various CSS3 modules.

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import functools
import math

from tinycss.color3 import parse_color
from tinycss.parsing import split_on_comma, remove_whitespace

from ..logger import LOGGER
from ..formatting_structure import counters
from ..compat import urljoin, unquote
from ..urls import url_is_absolute, iri_to_uri
from ..images import LinearGradient, RadialGradient
from .properties import (INITIAL_VALUES, KNOWN_PROPERTIES, NOT_PRINT_MEDIA,
                         Dimension)
from . import computed_values

# TODO: unit-test these validators


# get the sets of keys
LENGTH_UNITS = set(computed_values.LENGTHS_TO_PIXELS) | set(['ex', 'em', 'ch'])


# keyword -> (open, insert)
CONTENT_QUOTE_KEYWORDS = {
    'open-quote': (True, True),
    'close-quote': (False, True),
    'no-open-quote': (True, False),
    'no-close-quote': (False, False),
}

ZERO_PERCENT = Dimension(0, '%')
FIFTY_PERCENT = Dimension(50, '%')
HUNDRED_PERCENT = Dimension(100, '%')
BACKGROUND_POSITION_PERCENTAGES = {
    'top': ZERO_PERCENT,
    'left': ZERO_PERCENT,
    'center': FIFTY_PERCENT,
    'bottom': HUNDRED_PERCENT,
    'right': HUNDRED_PERCENT,
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
UNPREFIXED = set()
PREFIX = '-weasy-'


class InvalidValues(ValueError):
    """Invalid or unsupported values for a known CSS property."""


# Validators

def validator(property_name=None, prefixed=False, unprefixed=False,
              wants_base_url=False):
    """Decorator adding a function to the ``VALIDATORS``.

    The name of the property covered by the decorated function is set to
    ``property_name`` if given, or is inferred from the function name
    (replacing underscores by hyphens).

    :param prefixed:
        Vendor-specific (non-standard) and experimental properties are
        prefixed: stylesheets need to use eg. ``-weasy-bookmark-level: 2``
        instead of ``bookmark-level: 2``.
        See http://wiki.csswg.org/spec/vendor-prefixes
    :param unprefixed:
        Mark properties that used to be prefixed. When used with the prefix,
        they will be ignored be give a specific warning.
    :param wants_base_url:
        The function takes the stylesheet’s base URL as an additional
        parameter.

    """
    assert not (prefixed and unprefixed)

    def decorator(function):
        """Add ``function`` to the ``VALIDATORS``."""
        if property_name is None:
            name = function.__name__.replace('_', '-')
        else:
            name = property_name
        assert name in KNOWN_PROPERTIES, name
        assert name not in VALIDATORS, name

        function.wants_base_url = wants_base_url
        VALIDATORS[name] = function
        if prefixed:
            PREFIXED.add(name)
        if unprefixed:
            UNPREFIXED.add(name)
        return function
    return decorator


def get_keyword(token):
    """If ``value`` is a keyword, return its name.

    Otherwise return ``None``.

    """
    if token.type == 'IDENT':
        return token.value.lower()


def get_single_keyword(tokens):
    """If ``values`` is a 1-element list of keywords, return its name.

    Otherwise return ``None``.

    """
    if len(tokens) == 1:
        token = tokens[0]
        if token.type == 'IDENT':
            return token.value.lower()


def single_keyword(function):
    """Decorator for validators that only accept a single keyword."""
    @functools.wraps(function)
    def keyword_validator(tokens):
        """Wrap a validator to call get_single_keyword on tokens."""
        keyword = get_single_keyword(tokens)
        if function(keyword):
            return keyword
    return keyword_validator


def single_token(function):
    """Decorator for validators that only accept a single token."""
    @functools.wraps(function)
    def single_token_validator(tokens, *args):
        """Validate a property whose token is single."""
        if len(tokens) == 1:
            return function(tokens[0], *args)
    single_token_validator.__func__ = function
    return single_token_validator


def comma_separated_list(function):
    """Decorator for validators that accept a comma separated list."""
    @functools.wraps(function)
    def wrapper(tokens, *args):
        results = []
        for part in split_on_comma(tokens):
            result = function(remove_whitespace(part), *args)
            if result is None:
                return None
            results.append(result)
        return results
    wrapper.single_value = function
    return wrapper


def get_length(token, negative=True, percentage=False):
    if (token.unit in LENGTH_UNITS or (percentage and token.unit == '%')
            or (token.type in ('INTEGER', 'NUMBER')
                and token.value == 0)) and (negative or token.value >= 0):
        return Dimension(token.value, token.unit)


# http://dev.w3.org/csswg/css3-values/#angles
# 1<unit> is this many radians.
ANGLE_TO_RADIANS = {
    'rad': 1,
    'turn': 2 * math.pi,
    'deg': math.pi / 180,
    'grad': math.pi / 200,
}


def get_angle(token):
    """Return the value in radians of an <angle> token, or None."""
    factor = ANGLE_TO_RADIANS.get(token.unit)
    if factor is not None:
        return token.value * factor


# http://dev.w3.org/csswg/css-values/#resolution
RESOLUTION_TO_DPPX = {
    'dppx': 1,
    'dpi': 1 / computed_values.LENGTHS_TO_PIXELS['in'],
    'dpcm': 1 / computed_values.LENGTHS_TO_PIXELS['cm'],
}


def get_resolution(token):
    """Return the value in dppx of a <resolution> token, or None."""
    factor = RESOLUTION_TO_DPPX.get(token.unit)
    if factor is not None:
        return token.value * factor


def safe_urljoin(base_url, url):
    if url_is_absolute(url):
        return iri_to_uri(url)
    elif base_url:
        return iri_to_uri(urljoin(base_url, url))
    else:
        raise InvalidValues(
            'Relative URI reference without a base URI: %r' % url)


@validator()
@comma_separated_list
@single_keyword
def background_attachment(keyword):
    """``background-attachment`` property validation."""
    return keyword in ('scroll', 'fixed', 'local')


@validator('background-color')
@validator('border-top-color')
@validator('border-right-color')
@validator('border-bottom-color')
@validator('border-left-color')
@single_token
def other_colors(token):
    return parse_color(token)


@validator()
@single_token
def outline_color(token):
    if get_keyword(token) == 'invert':
        return 'currentColor'
    else:
        return parse_color(token)


@validator()
@single_keyword
def border_collapse(keyword):
    return keyword in ('separate', 'collapse')


@validator('color')
@single_token
def color(token):
    """``*-color`` and ``color`` properties validation."""
    result = parse_color(token)
    if result == 'currentColor':
        return 'inherit'
    else:
        return result


@validator('background-image', wants_base_url=True)
@comma_separated_list
@single_token
def background_image(token, base_url):
    if token.type != 'FUNCTION':
        return image_url([token], base_url)
    arguments = split_on_comma(t for t in token.content if t.type != 'S')
    name = token.function_name.lower()
    if name in ('linear-gradient', 'repeating-linear-gradient'):
        direction, color_stops = parse_linear_gradient_parameters(arguments)
        if color_stops:
            return 'linear-gradient', LinearGradient(
                [parse_color_stop(stop) for stop in color_stops],
                direction, 'repeating' in name)
    elif name in ('radial-gradient', 'repeating-radial-gradient'):
        result = parse_radial_gradient_parameters(arguments)
        if result is not None:
            shape, size, position, color_stops = result
        else:
            shape = 'ellipse'
            size = 'keyword', 'farthest-corner'
            position = 'left', FIFTY_PERCENT, 'top', FIFTY_PERCENT
            color_stops = arguments
        if color_stops:
            return 'radial-gradient', RadialGradient(
                [parse_color_stop(stop) for stop in color_stops],
                shape, size, position, 'repeating' in name)


DIRECTION_KEYWORDS = {
    # ('angle', radians)  0 upwards, then clockwise
    ('to', 'top'): ('angle', 0),
    ('to', 'right'): ('angle', math.pi / 2),
    ('to', 'bottom'): ('angle', math.pi),
    ('to', 'left'): ('angle', math.pi * 3 / 2),
    # ('corner', keyword)
    ('to', 'top', 'left'): ('corner', 'top_left'),
    ('to', 'left', 'top'): ('corner', 'top_left'),
    ('to', 'top', 'right'): ('corner', 'top_right'),
    ('to', 'right', 'top'): ('corner', 'top_right'),
    ('to', 'bottom', 'left'): ('corner', 'bottom_left'),
    ('to', 'left', 'bottom'): ('corner', 'bottom_left'),
    ('to', 'bottom', 'right'): ('corner', 'bottom_right'),
    ('to', 'right', 'bottom'): ('corner', 'bottom_right'),
}


def parse_linear_gradient_parameters(arguments):
    first_arg = arguments[0]
    if len(first_arg) == 1:
        angle = get_angle(first_arg[0])
        if angle is not None:
            return ('angle', angle), arguments[1:]
    else:
        result = DIRECTION_KEYWORDS.get(tuple(map(get_keyword, first_arg)))
        if result is not None:
            return result, arguments[1:]
    return ('angle', math.pi), arguments  # Default direction is 'to bottom'


def parse_radial_gradient_parameters(arguments):
    shape = None
    position = None
    size = None
    size_shape = None
    stack = arguments[0][::-1]
    while stack:
        token = stack.pop()
        keyword = get_keyword(token)
        if keyword == 'at':
            position = background_position.single_value(stack[::-1])
            if position is None:
                return
            break
        elif keyword in ('circle', 'ellipse') and shape is None:
            shape = keyword
        elif keyword in ('closest-corner', 'farthest-corner',
                         'closest-side', 'farthest-side') and size is None:
            size = 'keyword', keyword
        else:
            if stack and size is None:
                length_1 = get_length(token, percentage=True)
                length_2 = get_length(stack[-1], percentage=True)
                if None not in (length_1, length_2):
                    size = 'explicit', (length_1, length_2)
                    size_shape = 'ellipse'
                    stack.pop()
            if size is None:
                length_1 = get_length(token)
                if length_1 is not None:
                    size = 'explicit', (length_1, length_1)
                    size_shape = 'circle'
            if size is None:
                return
    if (shape, size_shape) in (('circle', 'ellipse'), ('circle', 'ellipse')):
        return
    return (
        shape or size_shape or 'ellipse',
        size or ('keyword', 'farthest-corner'),
        position or ('left', FIFTY_PERCENT, 'top', FIFTY_PERCENT),
        arguments[1:])


def parse_color_stop(tokens):
    if len(tokens) == 1:
        color = parse_color(tokens[0])
        if color is not None:
            return color, None
    elif len(tokens) == 2:
        color = parse_color(tokens[0])
        position = get_length(tokens[1], negative=True, percentage=True)
        if color is not None and position is not None:
            return color, position
    raise InvalidValues


@validator('list-style-image', wants_base_url=True)
@single_token
def image_url(token, base_url):
    """``*-image`` properties validation."""
    if get_keyword(token) == 'none':
        return 'none', None
    if token.type == 'URI':
        return 'url', safe_urljoin(base_url, token.value)


class CenterKeywordFakeToken(object):
    type = 'IDENT'
    value = 'center'
    unit = None


@validator(unprefixed=True)
def transform_origin(tokens):
    # TODO: parse (and ignore) a third value for Z.
    return simple_2d_position(tokens)


@validator()
@comma_separated_list
def background_position(tokens):
    """``background-position`` property validation.

    See http://dev.w3.org/csswg/css3-background/#the-background-position

    """
    result = simple_2d_position(tokens)
    if result is not None:
        pos_x, pos_y = result
        return 'left', pos_x, 'top', pos_y

    if len(tokens) == 4:
        keyword_1 = get_keyword(tokens[0])
        keyword_2 = get_keyword(tokens[2])
        length_1 = get_length(tokens[1], percentage=True)
        length_2 = get_length(tokens[3], percentage=True)
        if length_1 and length_2:
            if (keyword_1 in ('left', 'right') and
                    keyword_2 in ('top', 'bottom')):
                return keyword_1, length_1, keyword_2, length_2
            if (keyword_2 in ('left', 'right') and
                    keyword_1 in ('top', 'bottom')):
                return keyword_2, length_2, keyword_1, length_1

    if len(tokens) == 3:
        length = get_length(tokens[2], percentage=True)
        if length is not None:
            keyword = get_keyword(tokens[1])
            other_keyword = get_keyword(tokens[0])
        else:
            length = get_length(tokens[1], percentage=True)
            other_keyword = get_keyword(tokens[2])
            keyword = get_keyword(tokens[0])

        if length is not None:
            if other_keyword == 'center':
                if keyword in ('top', 'bottom'):
                    return 'left', FIFTY_PERCENT, keyword, length
                if keyword in ('left', 'right'):
                    return keyword, length, 'top', FIFTY_PERCENT
            elif (keyword in ('left', 'right') and
                    other_keyword in ('top', 'bottom')):
                return keyword, length, other_keyword, ZERO_PERCENT
            elif (keyword in ('top', 'bottom') and
                    other_keyword in ('left', 'right')):
                return other_keyword, ZERO_PERCENT, keyword, length


def simple_2d_position(tokens):
    """Common syntax of background-position and transform-origin."""
    if len(tokens) == 1:
        tokens = [tokens[0], CenterKeywordFakeToken]
    elif len(tokens) != 2:
        return None

    token_1, token_2 = tokens
    length_1 = get_length(token_1, percentage=True)
    length_2 = get_length(token_2, percentage=True)
    if length_1 and length_2:
        return length_1, length_2
    keyword_1, keyword_2 = map(get_keyword, tokens)
    if length_1 and keyword_2 in ('top', 'center', 'bottom'):
        return length_1, BACKGROUND_POSITION_PERCENTAGES[keyword_2]
    elif length_2 and keyword_1 in ('left', 'center', 'right'):
            return BACKGROUND_POSITION_PERCENTAGES[keyword_1], length_2
    elif (keyword_1 in ('left', 'center', 'right') and
          keyword_2 in ('top', 'center', 'bottom')):
        return (BACKGROUND_POSITION_PERCENTAGES[keyword_1],
                BACKGROUND_POSITION_PERCENTAGES[keyword_2])
    elif (keyword_1 in ('top', 'center', 'bottom') and
          keyword_2 in ('left', 'center', 'right')):
        # Swap tokens. They need to be in (horizontal, vertical) order.
        return (BACKGROUND_POSITION_PERCENTAGES[keyword_2],
                BACKGROUND_POSITION_PERCENTAGES[keyword_1])


@validator()
@comma_separated_list
def background_repeat(tokens):
    """``background-repeat`` property validation."""
    keywords = tuple(map(get_keyword, tokens))
    if keywords == ('repeat-x',):
        return ('repeat', 'no-repeat')
    if keywords == ('repeat-y',):
        return ('no-repeat', 'repeat')
    if keywords in (('no-repeat',), ('repeat',), ('space',), ('round',)):
        return keywords * 2
    if len(keywords) == 2 and all(
            k in ('no-repeat', 'repeat', 'space', 'round')
            for k in keywords):
        return keywords


@validator()
@comma_separated_list
def background_size(tokens):
    """Validation for ``background-size``."""
    if len(tokens) == 1:
        token = tokens[0]
        keyword = get_keyword(token)
        if keyword in ('contain', 'cover'):
            return keyword
        if keyword == 'auto':
            return ('auto', 'auto')
        length = get_length(token, negative=False, percentage=True)
        if length:
            return (length, 'auto')
    elif len(tokens) == 2:
        values = []
        for token in tokens:
            length = get_length(token, negative=False, percentage=True)
            if length:
                values.append(length)
            elif get_keyword(token) == 'auto':
                values.append('auto')
        if len(values) == 2:
            return tuple(values)


@validator('background-clip')
@validator('background-origin')
@comma_separated_list
@single_keyword
def box(keyword):
    """Validation for the ``<box>`` type used in ``background-clip``
    and ``background-origin``."""
    return keyword in ('border-box', 'padding-box', 'content-box')


@validator()
def border_spacing(tokens):
    """Validator for the `border-spacing` property."""
    lengths = [get_length(token, negative=False) for token in tokens]
    if all(lengths):
        if len(lengths) == 1:
            return (lengths[0], lengths[0])
        elif len(lengths) == 2:
            return tuple(lengths)


@validator('border-top-right-radius')
@validator('border-bottom-right-radius')
@validator('border-bottom-left-radius')
@validator('border-top-left-radius')
def border_corner_radius(tokens):
    """Validator for the `border-*-radius` properties."""
    lengths = [
        get_length(token, negative=False, percentage=True) for token in tokens]
    if all(lengths):
        if len(lengths) == 1:
            return (lengths[0], lengths[0])
        elif len(lengths) == 2:
            return tuple(lengths)


@validator('border-top-style')
@validator('border-right-style')
@validator('border-left-style')
@validator('border-bottom-style')
@single_keyword
def border_style(keyword):
    """``border-*-style`` properties validation."""
    return keyword in ('none', 'hidden', 'dotted', 'dashed', 'double',
                       'inset', 'outset', 'groove', 'ridge', 'solid')


@validator('outline-style')
@single_keyword
def outline_style(keyword):
    """``outline-style`` properties validation."""
    return keyword in ('none', 'dotted', 'dashed', 'double', 'inset',
                       'outset', 'groove', 'ridge', 'solid')


@validator('border-top-width')
@validator('border-right-width')
@validator('border-left-width')
@validator('border-bottom-width')
@validator('outline-width')
@single_token
def border_width(token):
    """``border-*-width`` properties validation."""
    length = get_length(token, negative=False)
    if length:
        return length
    keyword = get_keyword(token)
    if keyword in ('thin', 'medium', 'thick'):
        return keyword


@validator()
@single_keyword
def box_sizing(keyword):
    """Validation for the ``box-sizing`` property from css3-ui"""
    return keyword in ('padding-box', 'border-box', 'content-box')


@validator()
@single_keyword
def caption_side(keyword):
    """``caption-side`` properties validation."""
    return keyword in ('top', 'bottom')


@validator()
@single_keyword
def clear(keyword):
    """``clear`` property validation."""
    return keyword in ('left', 'right', 'both', 'none')


@validator()
@single_token
def clip(token):
    """Validation for the ``clip`` property."""
    function = parse_function(token)
    if function:
        name, args = function
        if name == 'rect' and len(args) == 4:
            values = []
            for arg in args:
                if get_keyword(arg) == 'auto':
                    values.append('auto')
                else:
                    length = get_length(arg)
                    if length:
                        values.append(length)
            if len(values) == 4:
                return values
    if get_keyword(token) == 'auto':
        return []


@validator(wants_base_url=True)
def content(tokens, base_url):
    """``content`` property validation."""
    keyword = get_single_keyword(tokens)
    if keyword in ('normal', 'none'):
        return keyword
    parsed_tokens = [validate_content_token(base_url, v) for v in tokens]
    if None not in parsed_tokens:
        return parsed_tokens


def validate_content_token(base_url, token):
    """Validation for a signle token for the ``content`` property.

    Return (type, content) or False for invalid tokens.

    """
    quote_type = CONTENT_QUOTE_KEYWORDS.get(get_keyword(token))
    if quote_type is not None:
        return ('QUOTE', quote_type)

    type_ = token.type
    if type_ == 'STRING':
        return ('STRING', token.value)
    if type_ == 'URI':
        return ('URI', safe_urljoin(base_url, token.value))
    function = parse_function(token)
    if function:
        name, args = function
        prototype = (name, [a.type for a in args])
        args = [getattr(a, 'value', a) for a in args]
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


def parse_function(function_token):
    """Return ``(name, args)`` if the given token is a function
    with comma-separated arguments, or None.
    .
    """
    if function_token.type == 'FUNCTION':
        content = [t for t in function_token.content if t.type != 'S']
        if len(content) % 2:
            for token in content[1::2]:
                if token.type != 'DELIM' or token.value != ',':
                    break
            else:
                return function_token.function_name.lower(), content[::2]


@validator()
def counter_increment(tokens):
    """``counter-increment`` property validation."""
    return counter(tokens, default_integer=1)


@validator()
def counter_reset(tokens):
    """``counter-reset`` property validation."""
    return counter(tokens, default_integer=0)


def counter(tokens, default_integer):
    """``counter-increment`` and ``counter-reset`` properties validation."""
    if get_single_keyword(tokens) == 'none':
        return []
    tokens = iter(tokens)
    token = next(tokens, None)
    assert token, 'got an empty token list'
    results = []
    while token is not None:
        if token.type != 'IDENT':
            return  # expected a keyword here
        counter_name = token.value
        if counter_name in ('none', 'initial', 'inherit'):
            raise InvalidValues('Invalid counter name: ' + counter_name)
        token = next(tokens, None)
        if token is not None and token.type == 'INTEGER':
            # Found an integer. Use it and get the next token
            integer = token.value
            token = next(tokens, None)
        else:
            # Not an integer. Might be the next counter name.
            # Keep `token` for the next loop iteration.
            integer = default_integer
        results.append((counter_name, integer))
    return results


@validator('top')
@validator('right')
@validator('left')
@validator('bottom')
@validator('margin-top')
@validator('margin-right')
@validator('margin-bottom')
@validator('margin-left')
@single_token
def lenght_precentage_or_auto(token):
    """``margin-*`` properties validation."""
    length = get_length(token, percentage=True)
    if length:
        return length
    if get_keyword(token) == 'auto':
        return 'auto'


@validator('height')
@validator('width')
@single_token
def width_height(token):
    """Validation for the ``width`` and ``height`` properties."""
    length = get_length(token, negative=False, percentage=True)
    if length:
        return length
    if get_keyword(token) == 'auto':
        return 'auto'


@validator()
@single_keyword
def direction(keyword):
    """``direction`` property validation."""
    return keyword in ('ltr', 'rtl')


@validator()
@single_keyword
def display(keyword):
    """``display`` property validation."""
    return keyword in (
        'inline', 'block', 'inline-block', 'list-item', 'none',
        'table', 'inline-table', 'table-caption',
        'table-row-group', 'table-header-group', 'table-footer-group',
        'table-row', 'table-column-group', 'table-column', 'table-cell')


@validator('float')
@single_keyword
def float_(keyword):  # XXX do not hide the "float" builtin
    """``float`` property validation."""
    return keyword in ('left', 'right', 'none')


@validator()
@comma_separated_list
def font_family(tokens):
    """``font-family`` property validation."""
    if len(tokens) == 1 and tokens[0].type == 'STRING':
        return tokens[0].value
    elif tokens and all(token.type == 'IDENT' for token in tokens):
        return ' '.join(token.value for token in tokens)


@validator()
@single_token
def font_size(token):
    """``font-size`` property validation."""
    length = get_length(token, negative=False, percentage=True)
    if length:
        return length
    font_size_keyword = get_keyword(token)
    if font_size_keyword in ('smaller', 'larger'):
        raise InvalidValues('value not supported yet')
    if font_size_keyword in computed_values.FONT_SIZE_KEYWORDS:
        # or keyword in ('smaller', 'larger')
        return font_size_keyword


@validator()
@single_keyword
def font_style(keyword):
    """``font-style`` property validation."""
    return keyword in ('normal', 'italic', 'oblique')


@validator()
@single_keyword
def font_stretch(keyword):
    """Validation for the ``font-stretch`` property."""
    return keyword in (
        'ultra-condensed', 'extra-condensed', 'condensed', 'semi-condensed',
        'normal',
        'semi-expanded', 'expanded', 'extra-expanded', 'ultra-expanded')


@validator()
@single_keyword
def font_variant(keyword):
    """``font-variant`` property validation."""
    return keyword in ('normal', 'small-caps')


@validator()
@single_token
def font_weight(token):
    """``font-weight`` property validation."""
    keyword = get_keyword(token)
    if keyword in ('normal', 'bold', 'bolder', 'lighter'):
        return keyword
    if token.type == 'INTEGER':
        if token.value in [100, 200, 300, 400, 500, 600, 700, 800, 900]:
            return token.value


@validator()
@single_token
def image_resolution(token):
    # TODO: support 'snap' and 'from-image'
    return get_resolution(token)


@validator('letter-spacing')
@validator('word-spacing')
@single_token
def spacing(token):
    """Validation for ``letter-spacing`` and ``word-spacing``."""
    if get_keyword(token) == 'normal':
        return 'normal'
    length = get_length(token)
    if length:
        return length


@validator()
@single_token
def line_height(token):
    """``line-height`` property validation."""
    if get_keyword(token) == 'normal':
        return 'normal'
    if (token.type in ('NUMBER', 'INTEGER', 'DIMENSION', 'PERCENTAGE') and
            token.value >= 0):
        return Dimension(token.value, token.unit)


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
@validator('min-width')
@validator('min-height')
@single_token
def length_or_precentage(token):
    """``padding-*`` properties validation."""
    length = get_length(token, negative=False, percentage=True)
    if length:
        return length


@validator('max-width')
@validator('max-height')
@single_token
def max_width_height(token):
    """Validation for max-width and max-height"""
    length = get_length(token, negative=False, percentage=True)
    if length:
        return length
    if get_keyword(token) == 'none':
        return Dimension(float('inf'), 'px')


@validator()
@single_token
def opacity(token):
    """Validation for the ``opacity`` property."""
    if token.type in ('NUMBER', 'INTEGER'):
        return min(1, max(0, token.value))


@validator()
@single_token
def z_index(token):
    """Validation for the ``z-index`` property."""
    if get_keyword(token) == 'auto':
        return 'auto'
    if token.type == 'INTEGER':
        return token.value


@validator('orphans')
@validator('widows')
@single_token
def orphans_widows(token):
    """Validation for the ``orphans`` or ``widows`` properties."""
    if token.type == 'INTEGER':
        value = token.value
        if value >= 1:
            return value


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
    return keyword in ('auto', 'always', 'left', 'right', 'avoid')


@validator()
@single_keyword
def page_break_inside(keyword):
    """Validation for the ``page-break-inside`` property."""
    return keyword in ('auto', 'avoid')


@validator()
@single_keyword
def position(keyword):
    """``position`` property validation."""
    return keyword in ('static', 'relative', 'absolute', 'fixed')


@validator()
def quotes(tokens):
    """``quotes`` property validation."""
    if (tokens and len(tokens) % 2 == 0
            and all(v.type == 'STRING' for v in tokens)):
        strings = [token.value for token in tokens]
        # Separate open and close quotes.
        # eg.  ['«', '»', '“', '”']  -> (['«', '“'], ['»', '”'])
        return strings[::2], strings[1::2]


@validator()
@single_keyword
def table_layout(keyword):
    """Validation for the ``table-layout`` property"""
    if keyword in ('fixed', 'auto'):
        return keyword


@validator()
@single_keyword
def text_align(keyword):
    """``text-align`` property validation."""
    return keyword in ('left', 'right', 'center', 'justify')


@validator()
def text_decoration(tokens):
    """``text-decoration`` property validation."""
    keywords = [get_keyword(v) for v in tokens]
    if keywords == ['none']:
        return 'none'
    if all(keyword in ('underline', 'overline', 'line-through', 'blink')
            for keyword in keywords):
        unique = set(keywords)
        if len(unique) == len(keywords):
            # No duplicate
            # blink is accepted but ignored
            # "Conforming user agents may simply not blink the text."
            return frozenset(unique - set(['blink']))


@validator()
@single_token
def text_indent(token):
    """``text-indent`` property validation."""
    length = get_length(token, percentage=True)
    if length:
        return length


@validator()
@single_keyword
def text_transform(keyword):
    """``text-align`` property validation."""
    return keyword in ('none', 'uppercase', 'lowercase', 'capitalize')


@validator()
@single_token
def vertical_align(token):
    """Validation for the ``vertical-align`` property"""
    length = get_length(token, percentage=True)
    if length:
        return length
    keyword = get_keyword(token)
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


@validator()
@single_keyword
def overflow_wrap(keyword):
    """``overflow-wrap`` property validation."""
    return keyword in ('normal', 'break-word')


@validator(unprefixed=True)
@single_keyword
def image_rendering(keyword):
    """Validation for ``image-rendering``."""
    return keyword in ('auto', 'optimizespeed', 'optimizequality')


@validator(unprefixed=True)
def size(tokens):
    """``size`` property validation.

    See http://www.w3.org/TR/css3-page/#page-size-prop

    """
    lengths = [get_length(token, negative=False) for token in tokens]
    if all(lengths):
        if len(lengths) == 1:
            return (lengths[0], lengths[0])
        elif len(lengths) == 2:
            return tuple(lengths)

    keywords = [get_keyword(v) for v in tokens]
    if len(keywords) == 1:
        keyword = keywords[0]
        if keyword in computed_values.PAGE_SIZES:
            return computed_values.PAGE_SIZES[keyword]
        elif keyword in ('auto', 'portrait'):
            return computed_values.INITIAL_PAGE_SIZE
        elif keyword == 'landscape':
            return computed_values.INITIAL_PAGE_SIZE[::-1]

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


@validator(prefixed=True)  # Non-standard
@single_token
def anchor(token):
    """Validation for ``anchor``."""
    if get_keyword(token) == 'none':
        return 'none'
    function = parse_function(token)
    if function:
        name, args = function
        prototype = (name, [a.type for a in args])
        args = [getattr(a, 'value', a) for a in args]
        if prototype == ('attr', ['IDENT']):
            return (name, args[0])


@validator(prefixed=True, wants_base_url=True)  # Non-standard
@single_token
def link(token, base_url):
    """Validation for ``link``."""
    if get_keyword(token) == 'none':
        return 'none'
    elif token.type == 'URI':
        if token.value.startswith('#'):
            return 'internal', unquote(token.value[1:])
        else:
            return 'external', safe_urljoin(base_url, token.value)
    function = parse_function(token)
    if function:
        name, args = function
        prototype = (name, [a.type for a in args])
        args = [getattr(a, 'value', a) for a in args]
        if prototype == ('attr', ['IDENT']):
            return (name, args[0])


@validator(prefixed=True)  # Non-standard
@single_token
def hyphens(token):
    """Validation for ``hyphens``."""
    keyword = get_keyword(token)
    if keyword in ('none', 'manual', 'auto'):
        return keyword


@validator(prefixed=True)  # Non-standard
@single_token
def hyphenate_character(token):
    """Validation for ``hyphenate-character``."""
    keyword = get_keyword(token)
    if keyword == 'auto':
        return '‐'
    elif token.type == 'STRING':
        return token.value


@validator(prefixed=True)  # Non-standard
@single_token
def hyphenate_limit_zone(token):
    """Validation for ``hyphenate-limit-zone``."""
    return get_length(token, negative=False, percentage=True)


@validator(prefixed=True)  # Non-standard
def hyphenate_limit_chars(tokens):
    """Validation for ``hyphenate-limit-chars``."""
    if len(tokens) == 1:
        token, = tokens
        keyword = get_keyword(token)
        if keyword == 'auto':
            return (5, 2, 2)
        elif token.type == 'INTEGER':
            return (token.value, 2, 2)
    elif len(tokens) == 2:
        total, left = tokens
        total_keyword = get_keyword(total)
        left_keyword = get_keyword(left)
        if total.type == 'INTEGER':
            if left.type == 'INTEGER':
                return (total.value, left.value, left.value)
            elif left_keyword == 'auto':
                return (total.value, 2, 2)
        elif total_keyword == 'auto':
            if left.type == 'INTEGER':
                return (5, left.value, left.value)
            elif left_keyword == 'auto':
                return (5, 2, 2)
    elif len(tokens) == 3:
        total, left, right = tokens
        if (
            (get_keyword(total) == 'auto' or total.type == 'INTEGER') and
            (get_keyword(left) == 'auto' or left.type == 'INTEGER') and
            (get_keyword(right) == 'auto' or right.type == 'INTEGER')
        ):
            total = total.value if total.type == 'INTEGER' else 5
            left = left.value if left.type == 'INTEGER' else 2
            right = right.value if right.type == 'INTEGER' else 2
            return (total, left, right)


@validator(prefixed=True)  # Non-standard
@single_token
def lang(token):
    """Validation for ``lang``."""
    if get_keyword(token) == 'none':
        return 'none'
    function = parse_function(token)
    if function:
        name, args = function
        prototype = (name, [a.type for a in args])
        args = [getattr(a, 'value', a) for a in args]
        if prototype == ('attr', ['IDENT']):
            return (name, args[0])
    elif token.type == 'STRING':
        return ('string', token.value)


@validator(prefixed=True)  # CSS3 GCPM, experimental
@single_token
def bookmark_label(token):
    """Validation for ``bookmark-label``."""
    keyword = get_keyword(token)
    if keyword in ('none', 'contents', 'content-before',
                   'content-element', 'content-after'):
        return ('keyword', keyword)
    elif token.type == 'STRING':
        return ('string', token.value)


@validator(prefixed=True)  # CSS3 GCPM, experimental
@single_token
def bookmark_level(token):
    """Validation for ``bookmark-level``."""
    if token.type == 'INTEGER':
        value = token.value
        if value >= 1:
            return value
    elif get_keyword(token) == 'none':
        return 'none'


@validator(unprefixed=True)
def transform(tokens):
    if get_single_keyword(tokens) == 'none':
        return []
    else:
        return [transform_function(v) for v in tokens]


def transform_function(token):
    function = parse_function(token)
    if not function:
        raise InvalidValues
    name, args = function

    if len(args) == 1:
        angle = get_angle(args[0])
        length = get_length(args[0], percentage=True)
        if name in ('rotate', 'skewx', 'skewy') and angle:
            return name, angle
        elif name in ('translatex', 'translate') and length:
            return 'translate', (length, computed_values.ZERO_PIXELS)
        elif name == 'translatey' and length:
            return 'translate', (computed_values.ZERO_PIXELS, length)
        elif name == 'scalex' and args[0].type in ('NUMBER', 'INTEGER'):
            return 'scale', (args[0].value, 1)
        elif name == 'scaley' and args[0].type in ('NUMBER', 'INTEGER'):
            return 'scale', (1, args[0].value)
        elif name == 'scale' and args[0].type in ('NUMBER', 'INTEGER'):
            return 'scale', (args[0].value,) * 2
    elif len(args) == 2:
        if name == 'scale' and all(a.type in ('NUMBER', 'INTEGER')
                                   for a in args):
            return name, [arg.value for arg in args]
        lengths = tuple(get_length(token, percentage=True) for token in args)
        if name == 'translate' and all(lengths):
            return name, lengths
    elif len(args) == 6 and name == 'matrix' and all(
            a.type in ('NUMBER', 'INTEGER') for a in args):
        return name, [arg.value for arg in args]
    raise InvalidValues


# Expanders

# Let's be consistent, always use ``name`` as an argument even
# when it is useless.
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
def expand_four_sides(base_url, name, tokens):
    """Expand properties setting a token for the four sides of a box."""
    # Make sure we have 4 tokens
    if len(tokens) == 1:
        tokens *= 4
    elif len(tokens) == 2:
        tokens *= 2  # (bottom, left) defaults to (top, right)
    elif len(tokens) == 3:
        tokens.append(tokens[1])  # left defaults to right
    elif len(tokens) != 4:
        raise InvalidValues(
            'Expected 1 to 4 token components got %i' % len(tokens))
    for suffix, token in zip(('-top', '-right', '-bottom', '-left'), tokens):
        i = name.rfind('-')
        if i == -1:
            new_name = name + suffix
        else:
            # eg. border-color becomes border-*-color, not border-color-*
            new_name = name[:i] + suffix + name[i:]

        # validate_non_shorthand returns [(name, value)], we want
        # to yield (name, value)
        result, = validate_non_shorthand(
            base_url, new_name, [token], required=True)
        yield result


@expander('border-radius')
def border_radius(base_url, name, tokens):
    """Validator for the `border-radius` property."""
    current = horizontal = []
    vertical = []
    for token in tokens:
        if token.type == 'DELIM' and token.value == '/':
            if current is horizontal:
                if token == tokens[-1]:
                    raise InvalidValues('Expected value after "/" separator')
                else:
                    current = vertical
            else:
                raise InvalidValues('Expected only one "/" separator')
        else:
            current.append(token)

    if not vertical:
        vertical = horizontal[:]

    for values in horizontal, vertical:
        # Make sure we have 4 tokens
        if len(values) == 1:
            values *= 4
        elif len(values) == 2:
            values *= 2  # (br, bl) defaults to (tl, tr)
        elif len(values) == 3:
            values.append(values[1])  # bl defaults to tr
        elif len(values) != 4:
            raise InvalidValues(
                'Expected 1 to 4 token components got %i' % len(values))
    corners = ('top-left', 'top-right', 'bottom-right', 'bottom-left')
    for corner, tokens in zip(corners, zip(horizontal, vertical)):
        new_name = 'border-%s-radius' % corner
        # validate_non_shorthand returns [(name, value)], we want
        # to yield (name, value)
        result, = validate_non_shorthand(
            base_url, new_name, tokens, required=True)
        yield result


def generic_expander(*expanded_names, **kwargs):
    """Decorator helping expanders to handle ``inherit`` and ``initial``.

    Wrap an expander so that it does not have to handle the 'inherit' and
    'initial' cases, and can just yield name suffixes. Missing suffixes
    get the initial value.

    """
    wants_base_url = kwargs.pop('wants_base_url', False)
    assert not kwargs

    def generic_expander_decorator(wrapped):
        """Decorate the ``wrapped`` expander."""
        @functools.wraps(wrapped)
        def generic_expander_wrapper(base_url, name, tokens):
            """Wrap the expander."""
            keyword = get_single_keyword(tokens)
            if keyword in ('inherit', 'initial'):
                results = dict.fromkeys(expanded_names, keyword)
                skip_validation = True
            else:
                skip_validation = False
                results = {}
                if wants_base_url:
                    result = wrapped(name, tokens, base_url)
                else:
                    result = wrapped(name, tokens)
                for new_name, new_token in result:
                    assert new_name in expanded_names, new_name
                    if new_name in results:
                        raise InvalidValues(
                            'got multiple %s values in a %s shorthand'
                            % (new_name.strip('-'), name))
                    results[new_name] = new_token

            for new_name in expanded_names:
                if new_name.startswith('-'):
                    # new_name is a suffix
                    actual_new_name = name + new_name
                else:
                    actual_new_name = new_name

                if new_name in results:
                    value = results[new_name]
                    if not skip_validation:
                        # validate_non_shorthand returns [(name, value)]
                        (actual_new_name, value), = validate_non_shorthand(
                            base_url, actual_new_name, value, required=True)
                else:
                    value = 'initial'

                yield actual_new_name, value
        return generic_expander_wrapper
    return generic_expander_decorator


@expander('list-style')
@generic_expander('-type', '-position', '-image', wants_base_url=True)
def expand_list_style(name, tokens, base_url):
    """Expand the ``list-style`` shorthand property.

    See http://www.w3.org/TR/CSS21/generate.html#propdef-list-style

    """
    type_specified = image_specified = False
    none_count = 0
    for token in tokens:
        if get_keyword(token) == 'none':
            # Can be either -style or -image, see at the end which is not
            # otherwise specified.
            none_count += 1
            none_token = token
            continue

        if list_style_type([token]) is not None:
            suffix = '-type'
            type_specified = True
        elif list_style_position([token]) is not None:
            suffix = '-position'
        elif image_url([token], base_url) is not None:
            suffix = '-image'
            image_specified = True
        else:
            raise InvalidValues
        yield suffix, [token]

    if not type_specified and none_count:
        yield '-type', [none_token]
        none_count -= 1

    if not image_specified and none_count:
        yield '-image', [none_token]
        none_count -= 1

    if none_count:
        # Too many none tokens.
        raise InvalidValues


@expander('border')
def expand_border(base_url, name, tokens):
    """Expand the ``border`` shorthand property.

    See http://www.w3.org/TR/CSS21/box.html#propdef-border

    """
    for suffix in ('-top', '-right', '-bottom', '-left'):
        for new_prop in expand_border_side(base_url, name + suffix, tokens):
            yield new_prop


@expander('border-top')
@expander('border-right')
@expander('border-bottom')
@expander('border-left')
@expander('outline')
@generic_expander('-width', '-color', '-style')
def expand_border_side(name, tokens):
    """Expand the ``border-*`` shorthand properties.

    See http://www.w3.org/TR/CSS21/box.html#propdef-border-top

    """
    for token in tokens:
        if parse_color(token) is not None:
            suffix = '-color'
        elif border_width([token]) is not None:
            suffix = '-width'
        elif border_style([token]) is not None:
            suffix = '-style'
        else:
            raise InvalidValues
        yield suffix, [token]


@expander('background')
def expand_background(base_url, name, tokens):
    """Expand the ``background`` shorthand property.

    See http://dev.w3.org/csswg/css3-background/#the-background

    """
    properties = [
        'background_color', 'background_image', 'background_repeat',
        'background_attachment', 'background_position', 'background_size',
        'background_clip', 'background_origin']
    keyword = get_single_keyword(tokens)
    if keyword in ('initial', 'inherit'):
        for name in properties:
            yield name, keyword
        return

    def parse_layer(tokens, final_layer=False):
        results = {}

        def add(name, value):
            if value is None:
                return False
            name = 'background_' + name
            if name in results:
                raise InvalidValues
            results[name] = value
            return True

        # Make `tokens` a stack
        tokens = tokens[::-1]
        while tokens:
            if add('repeat',
                   background_repeat.single_value(tokens[-2:][::-1])):
                del tokens[-2:]
                continue
            token = tokens[-1:]
            if (
                (final_layer and add('color', other_colors(token)))
                or add('image', background_image.single_value(token, base_url))
                or add('repeat', background_repeat.single_value(token))
                or add('attachment', background_attachment.single_value(token))
            ):
                tokens.pop()
                continue
            for n in (4, 3, 2, 1)[-len(tokens):]:
                n_tokens = tokens[-n:][::-1]
                position = background_position.single_value(n_tokens)
                if position is not None:
                    assert add('position', position)
                    del tokens[-n:]
                    if (tokens and tokens[-1].type == 'DELIM'
                            and tokens[-1].value == '/'):
                        for n in (3, 2)[-len(tokens):]:
                            # n includes the '/' delimiter.
                            n_tokens = tokens[-n:-1][::-1]
                            size = background_size.single_value(n_tokens)
                            if size is not None:
                                assert add('size', size)
                                del tokens[-n:]
                    break
            if position is not None:
                continue
            if add('origin', box.single_value(token)):
                tokens.pop()
                next_token = tokens[-1:]
                if add('clip', box.single_value(next_token)):
                    tokens.pop()
                else:
                    # The same keyword sets both:
                    assert add('clip', box.single_value(token))
                continue
            raise InvalidValues

        color = results.pop(
            'background_color', INITIAL_VALUES['background_color'])
        for name in properties:
            if name not in results:
                results[name] = INITIAL_VALUES[name][0]
        return color, results

    layers = reversed(split_on_comma(tokens))
    color, last_layer = parse_layer(next(layers), final_layer=True)
    results = dict((k, [v]) for k, v in last_layer.items())
    for tokens in layers:
        _, layer = parse_layer(tokens)
        for name, value in layer.items():
            results[name].append(value)
    for name, values in results.items():
        yield name, values[::-1]  # "Un-reverse"
    yield 'background-color', color


@expander('font')
@generic_expander('-style', '-variant', '-weight', '-stretch', '-size',
                  'line-height', '-family')  # line-height is not a suffix
def expand_font(name, tokens):
    """Expand the ``font`` shorthand property.

    http://www.w3.org/TR/CSS21/fonts.html#font-shorthand
    """
    expand_font_keyword = get_single_keyword(tokens)
    if expand_font_keyword in ('caption', 'icon', 'menu', 'message-box',
                               'small-caption', 'status-bar'):
        raise InvalidValues('System fonts are not supported')

    # Make `tokens` a stack
    tokens = list(reversed(tokens))
    # Values for font-style font-variant and font-weight can come in any
    # order and are all optional.
    while tokens:
        token = tokens.pop()
        if get_keyword(token) == 'normal':
            # Just ignore 'normal' keywords. Unspecified properties will get
            # their initial token, which is 'normal' for all three here.
            # TODO: fail if there is too many 'normal' values?
            continue

        if font_style([token]) is not None:
            suffix = '-style'
        elif font_variant([token]) is not None:
            suffix = '-variant'
        elif font_weight([token]) is not None:
            suffix = '-weight'
        elif font_stretch([token]) is not None:
            suffix = '-stretch'
        else:
            # We’re done with these three, continue with font-size
            break
        yield suffix, [token]

    # Then font-size is mandatory
    # Latest `token` from the loop.
    if font_size([token]) is None:
        raise InvalidValues
    yield '-size', [token]

    # Then line-height is optional, but font-family is not so the list
    # must not be empty yet
    if not tokens:
        raise InvalidValues

    token = tokens.pop()
    if token.type == 'DELIM' and token.value == '/':
        token = tokens.pop()
        if line_height([token]) is None:
            raise InvalidValues
        yield 'line-height', [token]
    else:
        # We pop()ed a font-family, add it back
        tokens.append(token)

    # Reverse the stack to get normal list
    tokens.reverse()
    if font_family(tokens) is None:
        raise InvalidValues
    yield '-family', tokens


@expander('word-wrap')
def expand_word_wrap(base_url, name, tokens):
    """Expand the ``word-wrap`` legacy property.

    See http://http://www.w3.org/TR/css3-text/#overflow-wrap

    """
    keyword = overflow_wrap(tokens)
    if keyword is None:
        raise InvalidValues

    yield 'overflow-wrap', keyword


def validate_non_shorthand(base_url, name, tokens, required=False):
    """Default validator for non-shorthand properties."""
    if not required and name not in KNOWN_PROPERTIES:
        hyphens_name = name.replace('_', '-')
        if hyphens_name in KNOWN_PROPERTIES:
            raise InvalidValues('did you mean %s?' % hyphens_name)
        else:
            raise InvalidValues('unknown property')

    if not required and name not in VALIDATORS:
        raise InvalidValues('property not supported yet')

    keyword = get_single_keyword(tokens)
    if keyword in ('initial', 'inherit'):
        value = keyword
    else:
        function = VALIDATORS[name]
        if function.wants_base_url:
            value = function(tokens, base_url)
        else:
            value = function(tokens)
        if value is None:
            raise InvalidValues
    return [(name, value)]


def preprocess_declarations(base_url, declarations):
    """
    Expand shorthand properties and filter unsupported properties and values.

    Log a warning for every ignored declaration.

    Return a iterable of ``(name, value, priority)`` tuples.

    """
    def validation_error(level, reason):
        getattr(LOGGER, level)(
            'Ignored `%s: %s` at %i:%i, %s.',
            declaration.name, declaration.value.as_css(),
            declaration.line, declaration.column, reason)

    for declaration in declarations:
        name = declaration.name

        if name in PREFIXED and not name.startswith(PREFIX):
            validation_error(
                'warning',
                'the property is experimental or non-standard, use '
                + PREFIX + name)
            continue

        if name in NOT_PRINT_MEDIA:
            validation_error(
                'info', 'the property does not apply for the print media')
            continue

        if name.startswith(PREFIX):
            unprefixed_name = name[len(PREFIX):]
            if unprefixed_name in UNPREFIXED:
                validation_error(
                    'warning',
                    'the property was unprefixed, use ' + unprefixed_name)
                continue
            if unprefixed_name in PREFIXED:
                name = unprefixed_name

        expander_ = EXPANDERS.get(name, validate_non_shorthand)
        tokens = remove_whitespace(declaration.value)
        try:
            # Use list() to consume generators now and catch any error.
            result = list(expander_(base_url, name, tokens))
        except InvalidValues as exc:
            validation_error(
                'warning',
                exc.args[0] if exc.args and exc.args[0] else 'invalid value')
            continue

        priority = declaration.priority
        for long_name, value in result:
            yield long_name.replace('-', '_'), value, priority
