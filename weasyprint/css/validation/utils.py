"""
    weasyprint.css.validation.utils
    -------------------------------

    Utils for property validation.
    See http://www.w3.org/TR/CSS21/propidx.html and various CSS3 modules.

    :copyright: Copyright 2011-2018 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import functools
import math
from urllib.parse import unquote, urljoin

from tinycss2.color3 import parse_color

from .. import computed_values
from ...formatting_structure import counters
from ...images import LinearGradient, RadialGradient
from ...logger import LOGGER
from ...urls import iri_to_uri, url_is_absolute
from ..properties import Dimension


# http://dev.w3.org/csswg/css3-values/#angles
# 1<unit> is this many radians.
ANGLE_TO_RADIANS = {
    'rad': 1,
    'turn': 2 * math.pi,
    'deg': math.pi / 180,
    'grad': math.pi / 200,
}

# http://dev.w3.org/csswg/css-values/#resolution
RESOLUTION_TO_DPPX = {
    'dppx': 1,
    'dpi': 1 / computed_values.LENGTHS_TO_PIXELS['in'],
    'dpcm': 1 / computed_values.LENGTHS_TO_PIXELS['cm'],
}

# Sets of possible length units
LENGTH_UNITS = (
    set(computed_values.LENGTHS_TO_PIXELS) | set(['ex', 'em', 'ch', 'rem']))

# Constants about background positions
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

# Direction keywords used for gradients
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

# Keywords for quotes in 'content' property
CONTENT_QUOTE_KEYWORDS = {
    'open-quote': (True, True),
    'close-quote': (False, True),
    'no-open-quote': (True, False),
    'no-close-quote': (False, False),
}


class InvalidValues(ValueError):
    """Invalid or unsupported values for a known CSS property."""


class CenterKeywordFakeToken(object):
    type = 'ident'
    lower_value = 'center'
    unit = None


def split_on_comma(tokens):
    """Split a list of tokens on commas, ie ``LiteralToken(',')``.

    Only "top-level" comma tokens are splitting points, not commas inside a
    function or blocks.

    """
    parts = []
    this_part = []
    for token in tokens:
        if token.type == 'literal' and token.value == ',':
            parts.append(this_part)
            this_part = []
        else:
            this_part.append(token)
    parts.append(this_part)
    return tuple(parts)


def remove_whitespace(tokens):
    """Remove any top-level whitespace and comments in a token list."""
    return tuple(
        token for token in tokens
        if token.type not in ('whitespace', 'comment'))


def safe_urljoin(base_url, url):
    if url_is_absolute(url):
        return iri_to_uri(url)
    elif base_url:
        return iri_to_uri(urljoin(base_url, url))
    else:
        raise InvalidValues(
            'Relative URI reference without a base URI: %r' % url)


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
        return tuple(results)
    wrapper.single_value = function
    return wrapper


def get_keyword(token):
    """If ``value`` is a keyword, return its name.

    Otherwise return ``None``.

    """
    if token.type == 'ident':
        return token.lower_value


def get_single_keyword(tokens):
    """If ``values`` is a 1-element list of keywords, return its name.

    Otherwise return ``None``.

    """
    if len(tokens) == 1:
        token = tokens[0]
        if token.type == 'ident':
            return token.lower_value


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


def parse_2d_position(tokens):
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


def parse_background_position(tokens):
    """Parse background position.

    See http://dev.w3.org/csswg/css3-background/#the-background-position

    """
    result = parse_2d_position(tokens)
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
            position = parse_background_position(stack[::-1])
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


def parse_function(function_token):
    """Parse functional notation.

    Return ``(name, args)`` if the given token is a function with comma- or
    space-separated arguments. Return ``None`` otherwise.

    """
    if not getattr(function_token, 'type', None) == 'function':
        return

    content = list(remove_whitespace(function_token.arguments))
    arguments = []
    last_is_comma = False
    while content:
        token = content.pop(0)
        is_comma = token.type == 'literal' and token.value == ','
        if last_is_comma and is_comma:
            return
        if is_comma:
            last_is_comma = True
        else:
            last_is_comma = False
            if token.type == 'function':
                argument_function = parse_function(token)
                if argument_function is None:
                    return
            arguments.append(token)
    return function_token.lower_name, arguments


def get_length(token, negative=True, percentage=False):
    """Parse a <length> token."""
    if percentage and token.type == 'percentage':
        if negative or token.value >= 0:
            return Dimension(token.value, '%')
    if token.type == 'dimension' and token.unit in LENGTH_UNITS:
        if negative or token.value >= 0:
            return Dimension(token.value, token.unit)
    if token.type == 'number' and token.value == 0:
        return Dimension(0, None)


def get_angle(token):
    """Parse an <angle> token in radians."""
    if token.type == 'dimension':
        factor = ANGLE_TO_RADIANS.get(token.unit)
        if factor is not None:
            return token.value * factor


def get_resolution(token):
    """Parse a <resolution> token in ddpx."""
    if token.type == 'dimension':
        factor = RESOLUTION_TO_DPPX.get(token.unit)
        if factor is not None:
            return token.value * factor


def get_image(token, base_url):
    """Parse an <image> token."""
    if token.type != 'function':
        if get_keyword(token) == 'none':
            return 'none', None
        parsed_url = get_url(token, base_url)
        if parsed_url and parsed_url[0] == 'external':
            return 'url', parsed_url[1]
        return
    arguments = split_on_comma(remove_whitespace(token.arguments))
    name = token.lower_name
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


def get_url(token, base_url):
    """Parse an <url> token."""
    if token.type == 'url':
        if token.value.startswith('#'):
            return 'internal', unquote(token.value[1:])
        else:
            return 'external', safe_urljoin(base_url, token.value)


def get_content_list(tokens, base_url):
    """Parse <content-list> tokens."""
    parsed_tokens = [
        get_content_list_token(token, base_url) for token in tokens]
    if None not in parsed_tokens:
        return parsed_tokens


def get_content_list_token(token, base_url):
    """Parse one of the <content-list> tokens."""

    def validate_target_token(token):
        """ validate first parameter of ``target-*()``-token
            returns ['attr', '<attrname>' ]
                 or ['STRING', '<anchorname>'] when valid
            evaluation of the anchorname is job of compute()
        """
        # TODO: what about ``attr(href url)`` ?
        if isinstance(token, str):
            # url() or "string" given
            # verify #anchor is done in compute()
            # if token.value.startswith('#'):
            return ['STRING', token]
        function = parse_function(token)
        if function:
            name, args = function
            params = [a.type for a in args]
            values = [getattr(a, 'value', a) for a in args]
            if name == 'attr' and params == ['ident']:
                return [name, values[0]]

    quote_type = CONTENT_QUOTE_KEYWORDS.get(get_keyword(token))
    if quote_type is not None:
        return ('QUOTE', quote_type)
    if get_keyword(token) == 'contents':
        return ('content', 'text')
    type_ = token.type
    if type_ == 'string':
        return ('STRING', token.value)
    if type_ == 'url':
        return ('URI', safe_urljoin(base_url, token.value))
    function = parse_function(token)
    if not function:
        # to pass unit test `test_boxes.test_before_after`
        # the log string must contain "invalid value"
        raise InvalidValues('invalid value/unsupported token ´%s\´' % (token,))

    name, args = function
    # known functions in 'content', 'string-set' and 'bookmark-label':
    valid_functions = [
        'attr', 'counter', 'counters', 'target-counter', 'target-counters',
        'target-text']
    # 'content'
    valid_functions += ['string', 'leader', 'content']
    unsupported_functions = ['leader']
    if name not in valid_functions:
        # to pass unit test `test_boxes.test_before_after`
        # the log string must contain "invalid value"
        raise InvalidValues('invalid value: function `%s()`' % (name))
    if name in unsupported_functions:
        # suppress -- not (yet) implemented, no error
        LOGGER.warn('\'%s()\' not (yet) supported', name)
        return ('STRING', '')

    prototype = (name, [a.type for a in args])
    args = [getattr(a, 'value', a) for a in args]
    if prototype == ('attr', ['ident']):
        # TODO: what about ``attr(href url)`` ?
        return (name, args[0])
    elif prototype in (('content', []), ('content', ['ident', ])):
        if not args:
            return (name, 'text')
        elif args[0] in ('text', 'after', 'before', 'first-letter'):
            return (name, args[0])
    elif prototype in (('counter', ['ident']),
                       ('counters', ['ident', 'string'])):
        args.append('decimal')
        return (name, args)
    elif prototype in (('counter', ['ident', 'ident']),
                       ('counters', ['ident', 'string', 'ident'])):
        style = args[-1]
        if style in ('none', 'decimal') or style in counters.STYLES:
            return (name, args)
    elif prototype in (('string', ['ident']),
                       ('string', ['ident', 'ident'])):
        if len(args) > 1:
            args[1] = args[1].lower()
            if args[1] not in ('first', 'start', 'last', 'first-except'):
                raise InvalidValues()
        return (name, args)
    # target-counter() = target-counter(
    #    [ <string> | <url> ] , <custom-ident> ,
    #    <counter-style>? )
    elif name == 'target-counter':
        if prototype in ((name, ['url', 'ident']),
                         (name, ['url', 'ident', 'ident']),
                         (name, ['string', 'ident']),
                         (name, ['string', 'ident', 'ident']),
                         (name, ['function', 'ident']),
                         (name, ['function', 'ident', 'ident'])):
            # default style
            if len(args) == 2:
                args.append('decimal')
            # accept "#anchorname" and attr(x)
            retval = validate_target_token(args.pop(0))
            if retval is None:
                raise InvalidValues()
            style = args[-1]
            if style in ('none', 'decimal') or style in counters.STYLES:
                return (name, retval + args)
    # target-counters() = target-counters(
    #    [ <string> | <url> ] , <custom-ident> , <string> ,
    #    <counter-style>? )
    elif name == 'target-counters':
        if prototype in ((name, ['url', 'ident', 'string']),
                         (name, ['url', 'ident', 'string', 'ident']),
                         (name, ['string', 'ident', 'string']),
                         (name, ['string', 'ident', 'string', 'ident']),
                         (name, ['function', 'ident', 'string']),
                         (name, ['function', 'ident', 'string', 'ident'])):
            # default style
            if len(args) == 3:
                args.append('decimal')
            # accept "#anchorname" and attr(x)
            retval = validate_target_token(args.pop(0))
            if retval is None:
                raise InvalidValues()
            style = args[-1]
            if style in ('none', 'decimal') or style in counters.STYLES:
                return (name, retval + args)
    # target-text() = target-text(
    #    [ <string> | <url> ] ,
    #    [ content | before | after | first-letter ]? )
    elif name == 'target-text':
        if prototype in ((name, ['url']),
                         (name, ['url', 'ident']),
                         (name, ['string']),
                         (name, ['string', 'ident']),
                         (name, ['function']),
                         (name, ['function', 'ident'])):
            if len(args) == 1:
                args.append('content')
            # accept "#anchorname" and attr(x)
            retval = validate_target_token(args.pop(0))
            if retval is None:
                raise InvalidValues()
            style = args[-1]
            # hint: the syntax isn't stable yet!
            if style in ('content', 'after', 'before', 'first-letter'):
                # build.TEXT_CONTENT_EXTRACTORS needs 'text'
                # TODO: should we define
                # TEXT_CONTENT_EXTRACTORS['content'] == box_text ?
                if style == 'content':
                    args[-1] = 'text'
                return (name, retval + args)
