"""Validate descriptors used for some at-rules."""

from math import inf

import tinycss2

from ...logger import LOGGER
from ..utils import (
    InvalidValues, comma_separated_list, get_custom_ident, get_keyword,
    get_single_keyword, get_url, remove_whitespace, single_keyword,
    single_token, split_on_comma)
from . import properties

DESCRIPTORS = {
    'font-face': {},
    'counter-style': {},
}


class NoneFakeToken:
    type = 'ident'
    lower_value = 'none'


class NormalFakeToken:
    type = 'ident'
    lower_value = 'normal'


def preprocess_descriptors(rule, base_url, descriptors):
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
            if descriptor.name not in DESCRIPTORS[rule]:
                raise InvalidValues('descriptor not supported')

            function = DESCRIPTORS[rule][descriptor.name]
            if function.wants_base_url:
                value = function(tokens, base_url)
            else:
                value = function(tokens)
            if value is None:
                raise InvalidValues
            result = ((descriptor.name, value),)
        except InvalidValues as exc:
            LOGGER.warning(
                'Ignored `%s:%s` at %d:%d, %s.',
                descriptor.name, tinycss2.serialize(descriptor.value),
                descriptor.source_line, descriptor.source_column,
                exc.args[0] if exc.args and exc.args[0] else 'invalid value')
            continue

        for long_name, value in result:
            yield long_name.replace('-', '_'), value


def descriptor(rule, descriptor_name=None, wants_base_url=False):
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
        assert name not in DESCRIPTORS[rule], name

        function.wants_base_url = wants_base_url
        DESCRIPTORS[rule][name] = function
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
                function_name = f'font_variant_{feature.replace("-", "_")}'
                if getattr(properties, function_name)([token]):
                    features[feature].append(token)
                    break
            else:
                raise InvalidValues
        for feature, tokens in features.items():
            if tokens:
                yield (f'-{feature}', tokens)


@descriptor('font-face')
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


@descriptor('font-face', wants_base_url=True)
@comma_separated_list
def src(tokens, base_url):
    """``src`` descriptor validation."""
    if len(tokens) in (1, 2):
        tokens, token = tokens[:-1], tokens[-1]
        if token.type == 'function' and token.lower_name == 'format':
            tokens, token = tokens[:-1], tokens[-1]
        if token.type == 'function' and token.lower_name == 'local':
            return 'local', font_family(token.arguments, allow_spaces=True)
        url = get_url(token, base_url)
        if url is not None and url[0] == 'url':
            return url[1]


@descriptor('font-face')
@single_keyword
def font_style(keyword):
    """``font-style`` descriptor validation."""
    return keyword in ('normal', 'italic', 'oblique')


@descriptor('font-face')
@single_token
def font_weight(token):
    """``font-weight`` descriptor validation."""
    keyword = get_keyword(token)
    if keyword in ('normal', 'bold'):
        return keyword
    if token.type == 'number' and token.int_value is not None:
        if token.int_value in [100, 200, 300, 400, 500, 600, 700, 800, 900]:
            return token.int_value


@descriptor('font-face')
@single_keyword
def font_stretch(keyword):
    """``font-stretch`` descriptor validation."""
    return keyword in (
        'ultra-condensed', 'extra-condensed', 'condensed', 'semi-condensed',
        'normal',
        'semi-expanded', 'expanded', 'extra-expanded', 'ultra-expanded')


@descriptor('font-face')
def font_feature_settings(tokens):
    """``font-feature-settings`` descriptor validation."""
    return properties.font_feature_settings(tokens)


@descriptor('font-face')
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
                None, f'font-variant{name}', sub_tokens, required=True))
        except InvalidValues:
            return None
    return values


@descriptor('counter-style')
def system(tokens):
    """``system`` descriptor validation."""
    if len(tokens) > 2:
        return

    keyword = get_keyword(tokens[0])

    if keyword == 'extends':
        if len(tokens) == 2:
            second_keyword = get_keyword(tokens[1])
            if second_keyword:
                return (keyword, second_keyword, None)
    elif keyword == 'fixed':
        if len(tokens) == 1:
            return (None, 'fixed', 1)
        elif tokens[1].type == 'number' and tokens[1].is_integer:
            return (None, 'fixed', tokens[1].int_value)
    elif len(tokens) == 1 and keyword in (
            'cyclic', 'numeric', 'alphabetic', 'symbolic', 'additive'):
        return (None, keyword, None)


@descriptor('counter-style', wants_base_url=True)
def negative(tokens, base_url):
    """``negative`` descriptor validation."""
    if len(tokens) > 2:
        return

    values = []
    tokens = list(tokens)
    while tokens:
        token = tokens.pop(0)
        if token.type in ('string', 'ident'):
            values.append(('string', token.value))
            continue
        url = get_url(token, base_url)
        if url is not None and url[0] == 'url':
            values.append(('url', url[1]))

    if len(values) == 1:
        values.append(('string', ''))

    if len(values) == 2:
        return values


@descriptor('counter-style', 'prefix', wants_base_url=True)
@descriptor('counter-style', 'suffix', wants_base_url=True)
def prefix_suffix(tokens, base_url):
    """``prefix`` and ``suffix`` descriptors validation."""
    if len(tokens) != 1:
        return

    token, = tokens
    if token.type in ('string', 'ident'):
        return ('string', token.value)
    url = get_url(token, base_url)
    if url is not None and url[0] == 'url':
        return ('url', url[1])


@descriptor('counter-style')
@comma_separated_list
def range(tokens):
    """``range`` descriptor validation."""
    if len(tokens) == 1:
        keyword = get_single_keyword(tokens)
        if keyword == 'auto':
            return 'auto'
    elif len(tokens) == 2:
        values = []
        for i, token in enumerate(tokens):
            if token.type == 'ident' and token.value == 'infinite':
                values.append(inf if i else -inf)
            elif token.type == 'number' and token.is_integer:
                values.append(token.int_value)
        if len(values) == 2 and values[0] <= values[1]:
            return tuple(values)


@descriptor('counter-style', wants_base_url=True)
def pad(tokens, base_url):
    """``pad`` descriptor validation."""
    if len(tokens) == 2:
        values = [None, None]
        for token in tokens:
            if token.type == 'number':
                if token.is_integer and token.value >= 0 and values[0] is None:
                    values[0] = token.int_value
            elif token.type in ('string', 'ident'):
                values[1] = ('string', token.value)
            url = get_url(token, base_url)
            if url is not None and url[0] == 'url':
                values[1] = ('url', url[1])

        if None not in values:
            return tuple(values)


@descriptor('counter-style')
@single_token
def fallback(token):
    """``fallback`` descriptor validation."""
    ident = get_custom_ident(token)
    if ident != 'none':
        return ident


@descriptor('counter-style', wants_base_url=True)
def symbols(tokens, base_url):
    """``symbols`` descriptor validation."""
    values = []
    for token in tokens:
        if token.type in ('string', 'ident'):
            values.append(('string', token.value))
            continue
        url = get_url(token, base_url)
        if url is not None and url[0] == 'url':
            values.append(('url', url[1]))
            continue
        return
    return tuple(values)


@descriptor('counter-style', wants_base_url=True)
def additive_symbols(tokens, base_url):
    """``additive-symbols`` descriptor validation."""
    results = []
    for part in split_on_comma(tokens):
        result = pad(remove_whitespace(part), base_url)
        if result is None:
            return
        if results and results[-1][0] <= result[0]:
            return
        results.append(result)
    return tuple(results)
