"""
    weasyprint.css.descriptors
    --------------------------

    Validate descriptors used for @font-face rules.
    See https://www.w3.org/TR/css-fonts-3/#font-resources.

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import tinycss2

from ...logger import LOGGER
from ..utils import (
    InvalidValues, comma_separated_list, get_keyword, get_single_keyword,
    get_url, remove_whitespace, single_keyword, single_token)
from . import properties

DESCRIPTORS = {}


class NoneFakeToken(object):
    type = 'ident'
    lower_value = 'none'


class NormalFakeToken(object):
    type = 'ident'
    lower_value = 'normal'


def preprocess_descriptors(base_url, descriptors):
    """Filter unsupported names and values for descriptors.

    Log a warning for every ignored descriptor.

    Return a iterable of ``(name, value)`` tuples.

    """
    for descriptor in descriptors:
        if descriptor.type != 'declaration' or descriptor.important:
            continue
        tokens = remove_whitespace(descriptor.value)
        try:
            # Use list() to consume generators now and catch any error.
            if descriptor.name not in DESCRIPTORS:
                raise InvalidValues('descriptor not supported')

            function = DESCRIPTORS[descriptor.name]
            if function.wants_base_url:
                value = function(tokens, base_url)
            else:
                value = function(tokens)
            if value is None:
                raise InvalidValues
            result = ((descriptor.name, value),)
        except InvalidValues as exc:
            LOGGER.warning(
                'Ignored `%s:%s` at %i:%i, %s.',
                descriptor.name, tinycss2.serialize(descriptor.value),
                descriptor.source_line, descriptor.source_column,
                exc.args[0] if exc.args and exc.args[0] else 'invalid value')
            continue

        for long_name, value in result:
            yield long_name.replace('-', '_'), value


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


def expand_font_variant(tokens):
    keyword = get_single_keyword(tokens)
    if keyword in ('normal', 'none'):
        for suffix in (
                '-alternates', '-caps', '-east-asian', '-numeric',
                '-position'):
            yield suffix, [NormalFakeToken]
        token = NormalFakeToken if keyword == 'normal' else NoneFakeToken
        yield '-ligatures', [token]
    else:
        features = {
            'alternates': [],
            'caps': [],
            'east-asian': [],
            'ligatures': [],
            'numeric': [],
            'position': []}
        for token in tokens:
            keyword = get_keyword(token)
            if keyword == 'normal':
                # We don't allow 'normal', only the specific values
                raise InvalidValues
            for feature in features:
                function_name = 'font_variant_%s' % feature.replace('-', '_')
                if getattr(properties, function_name)([token]):
                    features[feature].append(token)
                    break
            else:
                raise InvalidValues
        for feature, tokens in features.items():
            if tokens:
                yield '-%s' % feature, tokens


@descriptor()
def font_family(tokens, allow_spaces=False):
    """``font-family`` descriptor validation."""
    allowed_types = ['ident']
    if allow_spaces:
        allowed_types.append('whitespace')
    if len(tokens) == 1 and tokens[0].type == 'string':
        return tokens[0].value
    if tokens and all(token.type in allowed_types for token in tokens):
        return ' '.join(
            token.value for token in tokens if token.type == 'ident')


@descriptor(wants_base_url=True)
@comma_separated_list
def src(tokens, base_url):
    """``src`` descriptor validation."""
    if len(tokens) <= 2:
        tokens, token = tokens[:-1], tokens[-1]
        if token.type == 'function' and token.lower_name == 'format':
            tokens, token = tokens[:-1], tokens[-1]
        if token.type == 'function' and token.lower_name == 'local':
            return 'local', font_family(token.arguments, allow_spaces=True)
        url = get_url(token, base_url)
        if url is not None and url[0] == 'url':
            return url[1]


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
    if token.type == 'number' and token.int_value is not None:
        if token.int_value in [100, 200, 300, 400, 500, 600, 700, 800, 900]:
            return token.int_value


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
    return properties.font_feature_settings(tokens)


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
            values.append(properties.validate_non_shorthand(
                None, 'font-variant' + name, sub_tokens, required=True))
        except InvalidValues:
            return None
    return values
