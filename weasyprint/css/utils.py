"""Utils for CSS properties."""

import functools
import math
from abc import ABC, abstractmethod
from urllib.parse import unquote, urljoin

from tinycss2.color4 import parse_color

from .. import LOGGER
from ..urls import iri_to_uri, url_is_absolute
from .properties import Dimension

# https://drafts.csswg.org/css-values-3/#angles
# 1<unit> is this many radians.
ANGLE_TO_RADIANS = {
    'rad': 1,
    'turn': 2 * math.pi,
    'deg': math.pi / 180,
    'grad': math.pi / 200,
}

# How many CSS pixels is one <unit>?
# https://www.w3.org/TR/CSS21/syndata.html#length-units
LENGTHS_TO_PIXELS = {
    'px': 1,
    'pt': 1. / 0.75,
    'pc': 16.,  # LENGTHS_TO_PIXELS['pt'] * 12
    'in': 96.,  # LENGTHS_TO_PIXELS['pt'] * 72
    'cm': 96. / 2.54,  # LENGTHS_TO_PIXELS['in'] / 2.54
    'mm': 96. / 25.4,  # LENGTHS_TO_PIXELS['in'] / 25.4
    'q': 96. / 25.4 / 4,  # LENGTHS_TO_PIXELS['mm'] / 4
}

# https://drafts.csswg.org/css-values/#resolution
RESOLUTION_TO_DPPX = {
    'dppx': 1,
    'dpi': 1 / LENGTHS_TO_PIXELS['in'],
    'dpcm': 1 / LENGTHS_TO_PIXELS['cm'],
}

# Sets of possible length units
LENGTH_UNITS = set(LENGTHS_TO_PIXELS) | set(['ex', 'em', 'ch', 'rem'])

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

# Default fallback values used in attr() functions
ATTR_FALLBACKS = {
    'string': ('string', ''),
    'color': ('ident', 'currentcolor'),
    'url': ('external', 'about:invalid'),
    'integer': ('number', 0),
    'number': ('number', 0),
    '%': ('number', 0),
}
for unit in LENGTH_UNITS:
    ATTR_FALLBACKS[unit] = ('length', Dimension('0', unit))
for unit in ANGLE_TO_RADIANS:
    ATTR_FALLBACKS[unit] = ('angle', Dimension('0', unit))


class InvalidValues(ValueError):  # noqa: N818
    """Invalid or unsupported values for a known CSS property."""


class CenterKeywordFakeToken:
    type = 'ident'
    lower_value = 'center'
    unit = None


class Pending(ABC):
    """Abstract class representing property value with pending validation."""
    # See https://drafts.csswg.org/css-variables-2/#variables-in-shorthands.
    def __init__(self, tokens, name):
        self.tokens = tokens
        self.name = name
        self._reported_error = False

    @abstractmethod
    def validate(self, tokens, wanted_key):
        """Get validated value for wanted key."""
        raise NotImplementedError

    def solve(self, tokens, wanted_key):
        """Get validated value or raise error."""
        try:
            if not tokens:
                # Having no tokens is allowed by grammar but refused by all
                # properties and expanders.
                raise InvalidValues('no value')
            return self.validate(tokens, wanted_key)
        except InvalidValues as exc:
            if self._reported_error:
                raise exc
            source_line = self.tokens[0].source_line
            source_column = self.tokens[0].source_column
            value = ' '.join(token.serialize() for token in tokens)
            message = (exc.args and exc.args[0]) or 'invalid value'
            LOGGER.warning(
                'Ignored `%s: %s` at %d:%d, %s.',
                self.name, value, source_line, source_column, message)
            self._reported_error = True
            raise exc


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


def split_on_optional_comma(tokens):
    """Split a list of tokens on optional commas, ie ``LiteralToken(',')``."""
    parts = []
    for split_part in split_on_comma(tokens):
        if not split_part:
            # Happens when there's a comma at the beginning, at the end, or
            # when two commas are next to each other.
            return
        for part in split_part:
            parts.append(part)
    return parts


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
            f'Relative URI reference without a base URI: {url!r}')


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
    """If ``token`` is a keyword, return its lowercase name.

    Otherwise return ``None``.

    """
    if token.type == 'ident':
        return token.lower_value


def get_custom_ident(token):
    """If ``token`` is a keyword, return its name.

    Otherwise return ``None``.

    """
    if token.type == 'ident':
        return token.value


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


def parse_position(tokens):
    """Parse background-position and object-position.

    See https://drafts.csswg.org/css-backgrounds-3/#the-background-position
    https://drafts.csswg.org/css-images-3/#propdef-object-position

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
            position = parse_position(stack[::-1])
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
        if color == 'currentcolor':
            # TODO: return the current color instead
            return parse_color('black'), None
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
    if function_token.type != 'function':
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
    if last_is_comma:
        return
    return function_token.lower_name, arguments


def check_attr_function(token, allowed_type=None):
    function = parse_function(token)
    if function is None:
        return
    name, args = function
    if name == 'attr' and len(args) in (1, 2, 3):
        if args[0].type != 'ident':
            return
        attr_name = args[0].value
        if len(args) == 1:
            type_or_unit = 'string'
            fallback = ''
        else:
            if args[1].type != 'ident':
                return
            type_or_unit = args[1].value
            if type_or_unit not in ATTR_FALLBACKS:
                return
            if len(args) == 2:
                fallback = ATTR_FALLBACKS[type_or_unit]
            else:
                fallback_type = args[2].type
                if fallback_type == 'string':
                    fallback = args[2].value
                else:
                    # TODO: handle other fallback types
                    return
        if allowed_type in (None, type_or_unit):
            return ('attr()', (attr_name, type_or_unit, fallback))


def check_counter_function(token, allowed_type=None):
    from .validation.properties import list_style_type

    function = parse_function(token)
    if function is None:
        return
    name, args = function
    arguments = []
    if (name == 'counter' and len(args) in (1, 2)) or (
            name == 'counters' and len(args) in (2, 3)):
        ident = args.pop(0)
        if ident.type != 'ident':
            return
        arguments.append(ident.value)

        if name == 'counters':
            string = args.pop(0)
            if string.type != 'string':
                return
            arguments.append(string.value)

        if args:
            counter_style = list_style_type((args.pop(0),))
            if counter_style is None:
                return
            arguments.append(counter_style)
        else:
            arguments.append('decimal')

        return (f'{name}()', tuple(arguments))


def check_content_function(token):
    function = parse_function(token)
    if function is None:
        return
    name, args = function
    if name == 'content':
        if len(args) == 0:
            return ('content()', 'text')
        elif len(args) == 1:
            ident = args.pop(0)
            if ident.type == 'ident' and ident.lower_value in (
                    'text', 'before', 'after', 'first-letter', 'marker'):
                return ('content()', ident.lower_value)


def check_string_or_element_function(string_or_element, token):
    function = parse_function(token)
    if function is None:
        return
    name, args = function
    if name == string_or_element and len(args) in (1, 2):
        custom_ident = args.pop(0)
        if custom_ident.type != 'ident':
            return
        custom_ident = custom_ident.value

        if args:
            ident = args.pop(0)
            if ident.type != 'ident' or ident.lower_value not in (
                    'first', 'start', 'last', 'first-except'):
                return
            ident = ident.lower_value
        else:
            ident = 'first'

        return (f'{string_or_element}()', (custom_ident, ident))


def check_var_function(token):
    if function := parse_function(token):
        name, args = function
        if name == 'var' and args:
            ident = args.pop(0)
            # TODO: we should check authorized tokens
            # https://drafts.csswg.org/css-syntax-3/#typedef-declaration-value
            return ident.type == 'ident' and ident.value.startswith('--')
        for arg in args:
            if check_var_function(arg):
                return True


def get_string(token):
    """Parse a <string> token."""
    if token.type == 'string':
        return ('string', token.value)
    if token.type == 'function':
        if token.name == 'attr':
            return check_attr_function(token, 'string')
        elif token.name in ('counter', 'counters'):
            return check_counter_function(token)
        elif token.name == 'content':
            return check_content_function(token)
        elif token.name == 'string':
            return check_string_or_element_function('string', token)


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
    from ..images import LinearGradient, RadialGradient

    parsed_url = get_url(token, base_url)
    if parsed_url:
        assert parsed_url[0] == 'url'
        if parsed_url[1][0] == 'external':
            return 'url', parsed_url[1][1]
    if token.type != 'function':
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


def _get_url_tuple(string, base_url):
    if string.startswith('#'):
        return ('url', ('internal', unquote(string[1:])))
    else:
        return ('url', ('external', safe_urljoin(base_url, string)))


def get_url(token, base_url):
    """Parse an <url> token."""
    if token.type == 'url':
        return _get_url_tuple(token.value, base_url)
    elif token.type == 'function':
        if token.name == 'attr':
            return check_attr_function(token, 'url')
        elif token.name == 'url' and len(token.arguments) in (1, 2):
            # Ignore url modifiers
            # See https://drafts.csswg.org/css-values-3/#urls
            return _get_url_tuple(token.arguments[0].value, base_url)


def get_quote(token):
    """Parse a <quote> token."""
    keyword = get_keyword(token)
    if keyword in (
            'open-quote', 'close-quote',
            'no-open-quote', 'no-close-quote'):
        return keyword


def get_target(token, base_url):
    """Parse a <target> token."""
    function = parse_function(token)
    if function is None:
        return
    name, args = function
    args = split_on_optional_comma(args)
    if not args:
        return

    if name == 'target-counter':
        if len(args) not in (2, 3):
            return
    elif name == 'target-counters':
        if len(args) not in (3, 4):
            return
    elif name == 'target-text':
        if len(args) not in (1, 2):
            return
    else:
        return

    values = []

    link = args.pop(0)
    string_link = get_string(link)
    if string_link is None:
        url = get_url(link, base_url)
        if url is None:
            return
        values.append(url)
    else:
        values.append(string_link)

    if name.startswith('target-counter'):
        if not args:
            return

        ident = args.pop(0)
        if ident.type != 'ident':
            return
        values.append(ident.value)

        if name == 'target-counters':
            string = get_string(args.pop(0))
            if string is None:
                return
            values.append(string)

        if args:
            counter_style = get_keyword(args.pop(0))
        else:
            counter_style = 'decimal'
        values.append(counter_style)
    else:
        if args:
            content = get_keyword(args.pop(0))
            if content not in ('content', 'before', 'after', 'first-letter'):
                return
        else:
            content = 'content'
        values.append(content)

    return (f'{name}()', tuple(values))


def get_content_list(tokens, base_url):
    """Parse <content-list> tokens."""
    # See https://www.w3.org/TR/css-content-3/#typedef-content-list
    parsed_tokens = [
        get_content_list_token(token, base_url) for token in tokens]
    if None not in parsed_tokens:
        return parsed_tokens


def get_content_list_token(token, base_url):
    """Parse one of the <content-list> tokens."""
    # See https://www.w3.org/TR/css-content-3/#typedef-content-list

    # <string>
    string = get_string(token)
    if string is not None:
        return string

    # contents
    if get_keyword(token) == 'contents':
        return ('content()', 'text')

    # <uri>
    url = get_url(token, base_url)
    if url is not None:
        return url

    # <quote>
    quote = get_quote(token)
    if quote is not None:
        return ('quote', quote)

    # <target>
    target = get_target(token, base_url)
    if target is not None:
        return target

    function = parse_function(token)
    if function is None:
        return
    name, args = function

    # <leader()>
    if name == 'leader':
        if len(args) != 1:
            return
        arg, = args
        if arg.type == 'ident':
            if arg.value == 'dotted':
                string = '.'
            elif arg.value == 'solid':
                string = '_'
            elif arg.value == 'space':
                string = ' '
            else:
                return
        elif arg.type == 'string':
            string = arg.value
        return ('leader()', ('string', string))

    # <element()>
    elif name == 'element':
        return check_string_or_element_function('element', token)
