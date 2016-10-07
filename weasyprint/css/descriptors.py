# coding: utf-8
"""
    weasyprint.css.descriptors
    --------------------------

    Validate descriptors, currently used for @font-face rules.
    See https://www.w3.org/TR/css-fonts-3/#font-resources.

    :copyright: Copyright 2011-2016 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from tinycss.parsing import remove_whitespace

from ..compat import unquote
from ..logger import LOGGER
from .validation import (
    InvalidValues, comma_separated_list, expand_font_variant,
    font_feature_settings, get_keyword, safe_urljoin, single_keyword,
    single_token, validate_non_shorthand)


DESCRIPTORS = {}


def descriptor(descriptor_name=None, wants_base_url=False):
    """Decorator adding a function to the ``DESCRIPTORS``.

    The name of the descriptor covered by the decorated function is set to
    ``descriptor_name`` if given, or is inferred from the function name
    (replacing underscores by hyphens).

    :param wants_base_url:
        The function takes the stylesheet’s base URL as an additional
        parameter.

    """
    def decorator(function):
        """Add ``function`` to the ``DESCRIPTORS``."""
        if descriptor_name is None:
            name = function.__name__.replace('_', '-')
        else:
            name = descriptor_name
        assert name not in DESCRIPTORS, name

        function.wants_base_url = wants_base_url
        DESCRIPTORS[name] = function
        return function
    return decorator


@descriptor()
def font_family(tokens, allow_spaces=False):
    """``font-family`` descriptor validation."""
    allowed_types = ['IDENT']
    if allow_spaces:
        allowed_types.append('S')
    if len(tokens) == 1 and tokens[0].type == 'STRING':
        return tokens[0].value
    if tokens and all(token.type in allowed_types for token in tokens):
        return ' '.join(
            token.value for token in tokens if token.type == 'IDENT')


@descriptor(wants_base_url=True)
@comma_separated_list
def src(tokens, base_url):
    """``src`` descriptor validation."""
    if len(tokens) <= 2:
        token = tokens.pop()
        if token.type == 'FUNCTION' and token.function_name == 'format':
            token = tokens.pop()
        if token.type == 'FUNCTION' and token.function_name == 'local':
            return 'local', font_family(token.content, allow_spaces=True)
        if token.type == 'URI':
            if token.value.startswith('#'):
                return 'internal', unquote(token.value[1:])
            else:
                return 'external', safe_urljoin(base_url, token.value)


@descriptor()
@single_keyword
def font_style(keyword):
    """``font-style`` descriptor validation."""
    return keyword in ('normal', 'italic', 'oblique')


@descriptor()
@single_token
def font_weight(token):
    """``font-weight`` descriptor validation."""
    keyword = get_keyword(token)
    if keyword in ('normal', 'bold'):
        return keyword
    if token.type == 'INTEGER':
        if token.value in [100, 200, 300, 400, 500, 600, 700, 800, 900]:
            return token.value


@descriptor()
@single_keyword
def font_stretch(keyword):
    """Validation for the ``font-stretch`` descriptor."""
    return keyword in (
        'ultra-condensed', 'extra-condensed', 'condensed', 'semi-condensed',
        'normal',
        'semi-expanded', 'expanded', 'extra-expanded', 'ultra-expanded')


@descriptor('font-feature-settings')
def font_feature_settings_descriptor(tokens):
    """``font-feature-settings`` descriptor validation."""
    return font_feature_settings(tokens)


@descriptor()
def font_variant(tokens):
    """``font-variant`` descriptor validation."""
    if len(tokens) == 1:
        keyword = get_keyword(tokens[0])
        if keyword in ('normal', 'none', 'inherit'):
            return []
    values = []
    for name, sub_tokens in expand_font_variant(tokens):
        try:
            values.append(validate_non_shorthand(
                None, 'font-variant' + name, sub_tokens, required=True))
        except InvalidValues:
            return None
    return values


def validate(base_url, name, tokens):
    """Default validator for descriptors."""
    if name not in DESCRIPTORS:
        raise InvalidValues('descriptor not supported')

    function = DESCRIPTORS[name]
    if function.wants_base_url:
        value = function(tokens, base_url)
    else:
        value = function(tokens)
    if value is None:
        raise InvalidValues
    return [(name, value)]


def preprocess_descriptors(base_url, descriptors):
    """Filter unsupported names and values for descriptors.

    Log a warning for every ignored descriptor.

    Return a iterable of ``(name, value)`` tuples.

    """
    for descriptor in descriptors:
        tokens = remove_whitespace(descriptor.value)
        try:
            # Use list() to consume generators now and catch any error.
            result = list(validate(base_url, descriptor.name, tokens))
        except InvalidValues as exc:
            LOGGER.warning(
                'Ignored `%s: %s` at %i:%i, %s.',
                descriptor.name, descriptor.value.as_css(),
                descriptor.line, descriptor.column,
                exc.args[0] if exc.args and exc.args[0] else 'invalid value')
            continue

        for long_name, value in result:
            yield long_name.replace('-', '_'), value
