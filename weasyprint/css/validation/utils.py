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
from urllib.parse import urljoin

from .. import computed_values
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


class InvalidValues(ValueError):
    """Invalid or unsupported values for a known CSS property."""


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


def get_length(token, negative=True, percentage=False):
    if percentage and token.type == 'percentage':
        if negative or token.value >= 0:
            return Dimension(token.value, '%')
    if token.type == 'dimension' and token.unit in LENGTH_UNITS:
        if negative or token.value >= 0:
            return Dimension(token.value, token.unit)
    if token.type == 'number' and token.value == 0:
        return Dimension(0, None)


def get_angle(token):
    """Return the value in radians of an <angle> token, or None."""
    if token.type == 'dimension':
        factor = ANGLE_TO_RADIANS.get(token.unit)
        if factor is not None:
            return token.value * factor


def get_resolution(token):
    """Return the value in dppx of a <resolution> token, or None."""
    if token.type == 'dimension':
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
