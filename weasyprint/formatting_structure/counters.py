"""
    weasyprint.formatting_structure.counters
    ----------------------------------------

    Implement the various counter types and list-style-type values.

    These are defined in the same terms as CSS 3 Lists:
    http://dev.w3.org/csswg/css3-lists/#predefined-counters

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import functools

__all__ = ['format', 'format_list_marker']


# Initial values for counter style descriptors.
INITIAL_VALUES = dict(
    negative=('-', ''),
    prefix='',
    suffix='.',
    range=(float('-inf'), float('inf')),
    fallback='decimal',
    # type and symbols ommited here.
)

# Maps counter-style names to a dict of descriptors.
STYLES = {
    # Included here for format_list_marker().
    # format() special-cases decimal and does not use this.
    'decimal': INITIAL_VALUES,
}

# Maps counter types to a function implementing it.
# The functions take three arguments: the values of the `symbols`
# (or `additive-symbols` for the additive type) and `negative` descriptors,
# and the integer value being formatted.
# They return the representation as a string or None. None means that
# the value can not represented and the fallback should be used.
FORMATTERS = {}


def register_style(name, type='symbolic', **descriptors):
    """Register a counter style."""
    if type == 'override':
        # TODO: when @counter-style rules are supported, change override
        # to bind when a value is generated, not when the @rule is parsed.
        style = dict(STYLES[descriptors.pop('override')])
    else:
        style = dict(INITIAL_VALUES, formatter=functools.partial(
            FORMATTERS[type],
            descriptors.pop('symbols'),
            descriptors.pop('negative', INITIAL_VALUES['negative'])))
    style.update(descriptors)
    STYLES[name] = style


def register_formatter(function):
    """Register a counter type/algorithm."""
    FORMATTERS[function.__name__.replace('_', '-')] = function
    return function


@register_formatter
def repeating(symbols, _negative, value):
    """Implement the algorithm for `type: repeating`."""
    return symbols[(value - 1) % len(symbols)]


@register_formatter
def numeric(symbols, negative, value):
    """Implement the algorithm for `type: numeric`."""
    if value == 0:
        return symbols[0]
    is_negative = value < 0
    if is_negative:
        value = abs(value)
        prefix, suffix = negative
        reversed_parts = [suffix]
    else:
        reversed_parts = []
    length = len(symbols)
    value = abs(value)
    while value != 0:
        reversed_parts.append(symbols[value % length])
        value //= length
    if is_negative:
        reversed_parts.append(prefix)
    return ''.join(reversed(reversed_parts))


@register_formatter
def alphabetic(symbols, _negative, value):
    """Implement the algorithm for `type: alphabetic`."""
    if value <= 0:
        return None
    length = len(symbols)
    reversed_parts = []
    while value != 0:
        value -= 1
        reversed_parts.append(symbols[value % length])
        value //= length
    return ''.join(reversed(reversed_parts))


@register_formatter
def symbolic(symbols, _negative, value):
    """Implement the algorithm for `type: symbolic`."""
    if value <= 0:
        return None
    length = len(symbols)
    return symbols[value % length] * ((value - 1) // length)


@register_formatter
def non_repeating(symbols, _negative, value):
    """Implement the algorithm for `type: non-repeating`."""
    first_symbol_value, symbols = symbols
    value -= first_symbol_value
    if 0 <= value < len(symbols):
        return symbols[value]


@register_formatter
def additive(symbols, negative, value):
    """Implement the algorithm for `type: additive`."""
    if value == 0:
        for weight, symbol in symbols:
            if weight == 0:
                return symbol
    is_negative = value < 0
    if is_negative:
        value = abs(value)
        prefix, suffix = negative
        parts = [prefix]
    else:
        parts = []
    for weight, symbol in symbols:
        repetitions = value // weight
        parts.extend([symbol] * repetitions)
        value -= weight * repetitions
        if value == 0:
            if is_negative:
                parts.append(suffix)
            return ''.join(parts)
    return None  # Failed to find a representation for this value


# 'decimal' behaves the same as this, but defining it this way is silly.
# We’ll special-case it and just use str().
# register_style(
#     'decimal',
#     type='numeric',
#     symbols='0 1 2 3 4 5 6 7 8 9'.split(),
# )
register_style(
    'decimal-leading-zero',
    type='non-repeating',
    symbols=(-9, '''-09 -08 -07 -06 -05 -04 -03 -02 -01
                    00 01 02 03 04 05 06 07 08 09'''.split()),
)
register_style(
    'lower-roman',
    type='additive',
    range=(1, 4999),
    symbols=[(1000, 'm'), (900, 'cm'), (500, 'd'), (400, 'cd'),
             (100, 'c'), (90, 'xc'), (50, 'l'), (40, 'xl'),
             (10, 'x'), (9, 'ix'), (5, 'v'), (4, 'iv'),
             (1, 'i')],
)
register_style(
    'upper-roman',
    type='additive',
    range=(1, 4999),
    symbols=[(1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'),
             (100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'),
             (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'),
             (1, 'I')],
)
register_style(
    'georgian',
    type='additive',
    range=(1, 19999),
    symbols=[
        (10000, 'ჵ'), (9000, 'ჰ'), (8000, 'ჯ'), (7000, 'ჴ'), (6000, 'ხ'),
        (5000, 'ჭ'), (4000, 'წ'), (3000, 'ძ'), (2000, 'ც'), (1000, 'ჩ'),
        (900, 'შ'), (800, 'ყ'), (700, 'ღ'), (600, 'ქ'),
        (500, 'ფ'), (400, 'ჳ'), (300, 'ტ'), (200, 'ს'), (100, 'რ'),
        (90, 'ჟ'), (80, 'პ'), (70, 'ო'), (60, 'ჲ'),
        (50, 'ნ'), (40, 'მ'), (30, 'ლ'), (20, 'კ'), (10, 'ი'),
        (9, 'თ'), (8, 'ჱ'), (7, 'ზ'), (6, 'ვ'),
        (5, 'ე'), (4, 'დ'), (3, 'გ'), (2, 'ბ'), (1, 'ა')],
)
register_style(
    'armenian',
    type='additive',
    range=(1, 9999),
    symbols=[
        (9000, 'Ք'), (8000, 'Փ'), (7000, 'Ւ'), (6000, 'Ց'),
        (5000, 'Ր'), (4000, 'Տ'), (3000, 'Վ'), (2000, 'Ս'), (1000, 'Ռ'),
        (900, 'Ջ'), (800, 'Պ'), (700, 'Չ'), (600, 'Ո'),
        (500, 'Շ'), (400, 'Ն'), (300, 'Յ'), (200, 'Մ'), (100, 'Ճ'),
        (90, 'Ղ'), (80, 'Ձ'), (70, 'Հ'), (60, 'Կ'),
        (50, 'Ծ'), (40, 'Խ'), (30, 'Լ'), (20, 'Ի'), (10, 'Ժ'),
        (9, 'Թ'), (8, 'Ը'), (7, 'Է'), (6, 'Զ'),
        (5, 'Ե'), (4, 'Դ'), (3, 'Գ'), (2, 'Բ'), (1, 'Ա')],
)
register_style(
    'lower-alpha',
    type='alphabetic',
    symbols='a b c d e f g h i j k l m n o p q r s t u v w x y z'.split(),
)
register_style(
    'upper-alpha',
    type='alphabetic',
    symbols='A B C D E F G H I J K L M N O P Q R S T U V W X Y Z'.split(),
)
register_style(
    'lower-greek',
    type='alphabetic',
    symbols='α β γ δ ε ζ η θ ι κ λ μ ν ξ ο π ρ σ τ υ φ χ ψ ω'.split()
)
register_style(
    'disc',
    type='repeating',
    symbols=['•'],  # U+2022, BULLET
    suffix='',
)
register_style(
    'circle',
    type='repeating',
    symbols=['◦'],  # U+25E6 WHITE BULLET
    suffix='',
)
register_style(
    'square',
    type='repeating',
    # CSS Lists 3 suggests U+25FE BLACK MEDIUM SMALL SQUARE
    # But I think this one looks better.
    symbols=['▪'],  # U+25AA BLACK SMALL SQUARE
    suffix='',
)
register_style(
    'lower-latin',
    type='override',
    override='lower-alpha',
)
register_style(
    'upper-latin',
    type='override',
    override='upper-alpha',
)


def format(value, counter_style):
    """
    Return a representation of ``value`` formatted by ``counter_style``
    or one of its fallback.

    The representation includes negative signs, but not the prefix and suffix.

    """
    if counter_style == 'none':
        return ''
    failed_styles = set()  # avoid fallback loops
    while True:
        if counter_style == 'decimal' or counter_style in failed_styles:
            return str(value)
        style = STYLES[counter_style]
        low, high = style['range']
        if low <= value <= high:
            representation = style['formatter'](value)
            if representation is not None:
                return representation
        failed_styles.add(counter_style)
        counter_style = style['fallback']


def format_list_marker(value, counter_style):
    """
    Return a representation of ``value`` formatted for a list marker.

    This is the same as :func:`format()`, but includes the counter’s
    prefix and suffix.
    """
    style = STYLES[counter_style]
    return style['prefix'] + format(value, counter_style) + style['suffix']
