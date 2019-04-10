"""
    weasyprint.css.validation
    -------------------------

    Validate properties, expanders and descriptors.

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""


from tinycss2 import serialize

from ... import LOGGER
from ..utils import InvalidValues, remove_whitespace
from .expanders import EXPANDERS
from .properties import PREFIX, PROPRIETARY, UNSTABLE, validate_non_shorthand

# Not applicable to the print media
NOT_PRINT_MEDIA = {
    # Aural media
    'azimuth',
    'cue',
    'cue-after',
    'cue-before',
    'elevation',
    'pause',
    'pause-after',
    'pause-before',
    'pitch-range',
    'pitch',
    'play-during',
    'richness',
    'speak-header',
    'speak-numeral',
    'speak-punctuation',
    'speak',
    'speech-rate',
    'stress',
    'voice-family',
    'volume',
    # Interactive
    'cursor',
    # Animations and transitions
    'animation',
    'animation-delay',
    'animation-direction',
    'animation-duration',
    'animation-fill-mode',
    'animation-iteration-count',
    'animation-name',
    'animation-play-state',
    'animation-timing-function',
    'transition',
    'transition-delay',
    'transition-duration',
    'transition-property',
    'transition-timing-function',
}


def preprocess_declarations(base_url, declarations):
    """Expand shorthand properties, filter unsupported properties and values.

    Log a warning for every ignored declaration.

    Return a iterable of ``(name, value, important)`` tuples.

    """
    for declaration in declarations:
        if declaration.type == 'error':
            LOGGER.warning(
                'Error: %s at %i:%i.',
                declaration.message,
                declaration.source_line, declaration.source_column)

        if declaration.type != 'declaration':
            continue

        name = declaration.name
        if not name.startswith('--'):
            name = declaration.lower_name

        def validation_error(level, reason):
            getattr(LOGGER, level)(
                'Ignored `%s:%s` at %i:%i, %s.',
                declaration.name, serialize(declaration.value),
                declaration.source_line, declaration.source_column, reason)

        if name in NOT_PRINT_MEDIA:
            validation_error(
                'debug', 'the property does not apply for the print media')
            continue

        if name.startswith(PREFIX):
            unprefixed_name = name[len(PREFIX):]
            if unprefixed_name in PROPRIETARY:
                name = unprefixed_name
            elif unprefixed_name in UNSTABLE:
                LOGGER.warning(
                    'Deprecated `%s:%s` at %i:%i, '
                    'prefixes on unstable attributes are deprecated, '
                    'use `%s` instead.',
                    declaration.name, serialize(declaration.value),
                    declaration.source_line, declaration.source_column,
                    unprefixed_name)
                name = unprefixed_name
            else:
                LOGGER.warning(
                    'Ignored `%s:%s` at %i:%i, '
                    'prefix on this attribute is not supported, '
                    'use `%s` instead.',
                    declaration.name, serialize(declaration.value),
                    declaration.source_line, declaration.source_column,
                    unprefixed_name)
                continue

        if name.startswith('-') and not name.startswith('--'):
            validation_error('debug', 'prefixed selectors are ignored')
            continue

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

        important = declaration.important
        for long_name, value in result:
            yield long_name.replace('-', '_'), value, important
