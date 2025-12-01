"""CSS tokens parsers."""

import functools
from abc import ABC, abstractmethod
from math import e, inf, nan, pi

from tinycss2.ast import DimensionToken, IdentToken, NumberToken, PercentageToken
from tinycss2.color5 import parse_color

from ..logger import LOGGER
from ..urls import get_url_tuple
from . import functions
from .functions import check_math
from .properties import Dimension
from .units import ANGLE_TO_RADIANS, LENGTH_UNITS, RESOLUTION_TO_DPPX

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

DIRECTION_KEYWORDS = {
    # ('angle', radians), 0 upwards, then clockwise.
    ('to', 'top'): ('angle', 0),
    ('to', 'right'): ('angle', pi / 2),
    ('to', 'bottom'): ('angle', pi),
    ('to', 'left'): ('angle', pi * 3 / 2),
    # ('corner', keyword).
    ('to', 'top', 'left'): ('corner', 'top_left'),
    ('to', 'left', 'top'): ('corner', 'top_left'),
    ('to', 'top', 'right'): ('corner', 'top_right'),
    ('to', 'right', 'top'): ('corner', 'top_right'),
    ('to', 'bottom', 'left'): ('corner', 'bottom_left'),
    ('to', 'left', 'bottom'): ('corner', 'bottom_left'),
    ('to', 'bottom', 'right'): ('corner', 'bottom_right'),
    ('to', 'right', 'bottom'): ('corner', 'bottom_right'),
}

E = NumberToken(0, 0, e, None, 'e')
PI = NumberToken(0, 0, pi, None, 'π')
PLUS_INFINITY = NumberToken(0, 0, inf, None, '∞')
MINUS_INFINITY = NumberToken(0, 0, -inf, None, '-∞')
NAN = NumberToken(0, 0, nan, None, 'NaN')


class InvalidValues(ValueError):  # noqa: N818
    """Invalid or unsupported values for a known CSS property."""


class PercentageInMath(ValueError):  # noqa: N818
    """Percentage in math function without reference length."""


class FontUnitInMath(ValueError):  # noqa: N818
    """Font-relative unit in math function without reference style."""


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
        except InvalidValues as exception:
            if self._reported_error:
                raise exception
            source_line = self.tokens[0].source_line
            source_column = self.tokens[0].source_column
            value = ' '.join(token.serialize() for token in tokens)
            message = exception.args[0] if exception.args else 'invalid value'
            LOGGER.warning(
                'Ignored `%s: %s` at %d:%d, %s.',
                self.name, value, source_line, source_column, message)
            self._reported_error = True
            raise exception


def parse_color_hint(tokens):
    if len(tokens) == 1:
        return get_length(tokens[0], percentage=True)


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


def parse_color_stops_and_hints(color_stops_hints):
    if not color_stops_hints:
        raise InvalidValues

    color_stops = [parse_color_stop(color_stops_hints[0])]
    color_hints = []
    previous_was_color_stop = True

    for tokens in color_stops_hints[1:]:
        if hint := parse_color_hint(tokens):
            color_hints.append(hint)
            previous_was_color_stop = False
        elif previous_was_color_stop:
            color_hints.append(FIFTY_PERCENT)
            color_stops.append(parse_color_stop(tokens))
            previous_was_color_stop = True
        else:
            color_stops.append(parse_color_stop(tokens))
            previous_was_color_stop = True

    if not previous_was_color_stop:
        raise InvalidValues

    return color_stops, color_hints


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
    return ('angle', pi), arguments  # Default direction is 'to bottom'


def parse_2d_position(tokens):
    """Common syntax of background-position and transform-origin."""
    if len(tokens) == 1:
        tokens = [tokens[0], IdentToken(0, 0, 'center')]
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


def get_number(token, negative=True, integer=False):
    """Parse a <number> token."""
    from . import resolve_math

    if check_math(token):
        try:
            resolved = resolve_math(token)
        except (PercentageInMath, FontUnitInMath):
            return
        else:
            if resolved is None:
                return
            if resolved.type != 'number':
                return
            value = resolved.value
            if not negative and value < 0:
                value = 0
            if integer:
                # TODO: always round x.5 to +inf, see
                # https://drafts.csswg.org/css-values-4/#combine-integers.
                value = round(value)
            return Dimension(value, None)
    elif token.type == 'number':
        if integer:
            if token.int_value is not None:
                if negative or token.int_value >= 0:
                    return Dimension(token.int_value, None)
        elif negative or token.value >= 0:
            return Dimension(token.value, None)


def get_string(token):
    """Parse a <string> token."""
    if token.type == 'string':
        return ('string', token.value)
    if token.type == 'function':
        if token.name == 'attr':
            return functions.check_attr(token, 'string')
        elif token.name in ('counter', 'counters'):
            return functions.check_counter(token)
        elif token.name == 'content':
            return functions.check_content(token)
        elif token.name == 'string':
            return functions.check_string_or_element('string', token)


def get_percentage(token, negative=True):
    """Parse a <percentage> token."""
    from . import resolve_math

    if check_math(token):
        try:
            token = resolve_math(token) or token
        except (PercentageInMath, FontUnitInMath):
            return
        else:
            # Range clamp.
            if not negative:
                token.value = max(0, token.value)
    if token.type == 'percentage' and (negative or token.value >= 0):
        return Dimension(token.value, '%')


def get_length(token, negative=True, percentage=False):
    """Parse a <length> token."""
    from . import resolve_math

    if check_math(token):
        try:
            token = resolve_math(token) or token
        except PercentageInMath:
            # PercentageInMath is raised in priority to help discarding percentages for
            # properties that don’t allow them.
            return token if percentage else None
        except FontUnitInMath:
            return token
        else:
            # Range clamp.
            if not negative and token.type not in ('function', 'number'):
                token.value = max(0, token.value)
    if percentage and token.type == 'percentage':
        if negative or token.value >= 0:
            return Dimension(token.value, '%')
    if token.type == 'dimension' and token.unit.lower() in LENGTH_UNITS:
        if negative or token.value >= 0:
            return Dimension(token.value, token.unit.lower())
    if token.type == 'number' and token.value == 0:
        return Dimension(0, None)


def get_angle(token):
    """Parse an <angle> token in radians."""
    from . import resolve_math

    try:
        token = resolve_math(token) or token
    except (PercentageInMath, FontUnitInMath):
        return
    if token.type == 'dimension':
        factor = ANGLE_TO_RADIANS.get(token.unit.lower())
        if factor is not None:
            return token.value * factor


def get_resolution(token):
    """Parse a <resolution> token in dppx."""
    from . import resolve_math

    try:
        token = resolve_math(token) or token
    except (PercentageInMath, FontUnitInMath):
        return
    if token.type == 'dimension':
        factor = RESOLUTION_TO_DPPX.get(token.unit.lower())
        if factor is not None:
            return token.value * factor


def get_image(token, base_url):
    """Parse an <image> token."""
    from ..images import LinearGradient, RadialGradient

    if parsed_url := get_url(token, base_url):
        assert parsed_url[0] == 'url'
        if parsed_url[1][0] == 'external':
            return 'url', parsed_url[1][1]
    function = functions.Function(token)
    arguments = function.split_comma(single_tokens=False)
    if not arguments:
        return
    repeating = function.name.startswith('repeating-')
    if function.name in ('linear-gradient', 'repeating-linear-gradient'):
        direction, color_stops = parse_linear_gradient_parameters(arguments)
        color_stops, color_hints = parse_color_stops_and_hints(color_stops)
        return 'linear-gradient', LinearGradient(
            color_stops, direction, repeating, color_hints)
    elif function.name in ('radial-gradient', 'repeating-radial-gradient'):
        result = parse_radial_gradient_parameters(arguments)
        if result is not None:
            shape, size, position, color_stops = result
        else:
            shape = 'ellipse'
            size = 'keyword', 'farthest-corner'
            position = 'left', FIFTY_PERCENT, 'top', FIFTY_PERCENT
            color_stops = arguments
        color_stops, color_hints = parse_color_stops_and_hints(color_stops)
        return 'radial-gradient', RadialGradient(
            color_stops, shape, size, position, repeating, color_hints)


def get_url(token, base_url):
    """Parse an <url> token."""
    if token.type == 'url':
        url = get_url_tuple(token.value, base_url)
    elif token.type == 'function':
        if token.name == 'attr':
            return functions.check_attr(token, 'url')
        elif token.name == 'url' and len(token.arguments) in (1, 2):
            # Ignore url modifiers
            # See https://drafts.csswg.org/css-values-3/#urls
            url = get_url_tuple(token.arguments[0].value, base_url)
        else:
            return
    else:
        return

    if url is None:
        raise InvalidValues(f'Relative URI reference without a base URI: {url!r}')

    return ('url', url)


def get_quote(token):
    """Parse a <quote> token."""
    keyword = get_keyword(token)
    if keyword in (
            'open-quote', 'close-quote',
            'no-open-quote', 'no-close-quote'):
        return keyword


def get_target(token, base_url):
    """Parse a <target> token."""
    function = functions.Function(token)
    arguments = function.split_comma()
    if function.name == 'target-counter':
        if len(arguments) not in (2, 3):
            return
    elif function.name == 'target-counters':
        if len(arguments) not in (3, 4):
            return
    elif function.name == 'target-text':
        if len(arguments) not in (1, 2):
            return
    else:
        return

    values = []

    link = arguments.pop(0)
    string_link = get_string(link)
    if string_link is None:
        url = get_url(link, base_url)
        if url is None:
            return
        values.append(url)
    else:
        values.append(string_link)

    if function.name.startswith('target-counter'):
        ident = arguments.pop(0)
        if ident.type != 'ident':
            return
        values.append(ident.value)

        if function.name == 'target-counters':
            string = get_string(arguments.pop(0))
            if string is None:
                return
            values.append(string)

        if arguments:
            counter_style = get_keyword(arguments.pop(0))
        else:
            counter_style = 'decimal'
        values.append(counter_style)
    else:
        if arguments:
            content = get_keyword(arguments.pop(0))
            if content not in ('content', 'before', 'after', 'first-letter'):
                return
        else:
            content = 'content'
        values.append(content)

    return (f'{function.name}()', tuple(values))


def get_content_list(tokens, base_url):
    """Parse <content-list> tokens."""
    # See https://www.w3.org/TR/css-content-3/#typedef-content-list
    parsed_tokens = [get_content_list_token(token, base_url) for token in tokens]
    if None not in parsed_tokens:
        return parsed_tokens


def get_content_list_token(token, base_url):
    """Parse one of the <content-list> tokens."""
    # See https://drafts.csswg.org/css-content-3/#content-values.

    # <string>
    if (string := get_string(token)) is not None:
        return string

    # contents
    if get_keyword(token) == 'contents':
        return ('content()', 'text')

    # <uri>
    if (url := get_url(token, base_url)) is not None:
        return url

    # <quote>
    if (quote := get_quote(token)) is not None:
        return ('quote', quote)

    # <target>
    if (target := get_target(token, base_url)) is not None:
        return target

    function = functions.Function(token)
    arguments = function.split_comma()

    # <leader()>
    if function.name == 'leader':
        if len(arguments) != 1:
            return
        arg, = arguments
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
    elif function.name == 'element':
        return functions.check_string_or_element('element', token)


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
        return tuple(results)
    wrapper.single_value = function
    return wrapper


def tokenize(item, function=None, unit=None):
    """Transform a computed value result into a token."""
    if isinstance(item, (DimensionToken, Dimension)):
        value = function(item.value) if function else item.value
        return DimensionToken(0, 0, value, None, str(value), item.unit.lower())
    elif isinstance(item, PercentageToken):
        value = function(item.value) if function else item.value
        return PercentageToken(0, 0, value, None, str(value))
    elif isinstance(item, (NumberToken, int, float)):
        if isinstance(item, NumberToken):
            value = item.value
        else:
            value = item
        value = function(value) if function else value
        int_value = round(value) if float(value).is_integer() else None
        representation = str(int_value if float(value).is_integer() else value)
        if unit is None:
            return NumberToken(0, 0, value, int_value, representation)
        elif unit == '%':
            return PercentageToken(0, 0, value, int_value, representation)
        else:
            return DimensionToken(0, 0, value, int_value, representation, unit)
