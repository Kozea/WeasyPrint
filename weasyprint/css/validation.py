# coding: utf8
"""
    weasyprint.css.validation
    -------------------------

    Expand shorthands and validate property values.
    See http://www.w3.org/TR/CSS21/propidx.html and various CSS3 modules.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import functools

from tinycss.color3 import parse_color
from tinycss.parsing import split_on_comma, remove_whitespace

from ..logger import LOGGER
from ..formatting_structure import counters
from ..compat import urljoin, unquote
from ..urls import url_is_absolute, iri_to_uri
from .properties import (INITIAL_VALUES, KNOWN_PROPERTIES, NOT_PRINT_MEDIA,
                         Dimension)
from . import computed_values

# TODO: unit-test these validators


# get the sets of keys
LENGTH_UNITS = set(computed_values.LENGTHS_TO_PIXELS) | set(['ex', 'em'])
ANGLE_UNITS = set(computed_values.ANGLE_TO_RADIANS)

# keyword -> (open, insert)
CONTENT_QUOTE_KEYWORDS = {
    'open-quote': (True, True),
    'close-quote': (False, True),
    'no-open-quote': (True, False),
    'no-close-quote': (False, False),
}

BACKGROUND_POSITION_PERCENTAGES = {
    'top': Dimension(0, '%'),
    'left': Dimension(0, '%'),
    'center': Dimension(50, '%'),
    'bottom': Dimension(100, '%'),
    'right': Dimension(100, '%'),
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


def get_length(token, negative=True, percentage=False):
    if (token.unit in LENGTH_UNITS or (percentage and token.unit == '%')
                or (token.type in ('INTEGER', 'NUMBER') and token.value == 0)
            ) and (negative or token.value >= 0):
        return Dimension(token.value, token.unit)


def get_angle(token):
    """Return whether the argument is an angle token."""
    if token.unit in ANGLE_UNITS:
        return Dimension(token.value, token.unit)


def safe_urljoin(base_url, url):
    if url_is_absolute(url):
        return url
    elif base_url:
        return urljoin(base_url, url)
    else:
        raise InvalidValues(
            'Relative URI reference without a base URI: %r' % url)


@validator()
@single_keyword
def background_attachment(keyword):
    """``background-attachment`` property validation."""
    return keyword in ('scroll', 'fixed')


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
@validator('list-style-image', wants_base_url=True)
@single_token
def image(token, base_url):
    """``*-image`` properties validation."""
    if get_keyword(token) == 'none':
        return 'none'
    if token.type == 'URI':
        return safe_urljoin(base_url, token.value)


@validator('transform-origin', unprefixed=True)
@validator()
def background_position(tokens):
    """``background-position`` property validation.

    See http://www.w3.org/TR/CSS21/colors.html#propdef-background-position

    """
    if len(tokens) == 1:
        center = BACKGROUND_POSITION_PERCENTAGES['center']
        token = tokens[0]
        keyword = get_keyword(token)
        if keyword in BACKGROUND_POSITION_PERCENTAGES:
            return BACKGROUND_POSITION_PERCENTAGES[keyword], center
        else:
            length = get_length(token, percentage=True)
            if length:
                return length, center

    elif len(tokens) == 2:
        token_1, token_2 = tokens
        keyword_1, keyword_2 = map(get_keyword, tokens)
        length_1 = get_length(token_1, percentage=True)
        if length_1:
            if keyword_2 in ('top', 'center', 'bottom'):
                return length_1, BACKGROUND_POSITION_PERCENTAGES[keyword_2]
            length_2 = get_length(token_2, percentage=True)
            if length_2:
                return length_1, length_2
            raise InvalidValues
        length_2 = get_length(token_2, percentage=True)
        if length_2:
            if keyword_1 in ('left', 'center', 'right'):
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
    #else: invalid


@validator()
@single_keyword
def background_repeat(keyword):
    """``background-repeat`` property validation."""
    return keyword in ('repeat', 'repeat-x', 'repeat-y', 'no-repeat')


@validator()
def background_size(tokens):
    """Validation for ``background-size``."""
    if len(tokens) == 1:
        token = tokens[0]
        keyword = get_keyword(token)
        if keyword in ('contain', 'cover'):
            return keyword
        if keyword == 'auto':
            return ('auto', 'auto')
        length = get_length(token, negative=False)
        if length:
            return (length, 'auto')
    elif len(tokens) == 2:
        values = []
        for token in tokens:
            if get_keyword(token) == 'auto':
                values.append('auto')
            else:
                length = get_length(token, negative=False)
                if length:
                    values.append(token)
        if len(values) == 2:
            return tuple(values)


@validator('background-clip')
@validator('background-origin')
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


@validator('border-top-style')
@validator('border-right-style')
@validator('border-left-style')
@validator('border-bottom-style')
@validator('outline-style')
@single_keyword
def border_style(keyword):
    """``border-*-style`` properties validation."""
    return keyword in ('none', 'hidden', 'dotted', 'dashed', 'double',
                       'inset', 'outset', 'groove', 'ridge', 'solid')


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
        args = [a.value for a in args]
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
        counter_name = get_keyword(token)
        if counter_name is None:
            return  # expected a keyword here
        if counter_name in ('none', 'initial', 'inherit'):
            raise InvalidValues('Invalid counter name: '+ counter_name)
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
def font_family(tokens):
    """``font-family`` property validation."""
    parts = split_on_comma(tokens)
    families = []
    for part in parts:
        if len(part) == 1 and part[0].type == 'STRING':
            families.append(part[0].value)
        elif part and all(token.type == 'IDENT' for token in part):
            families.append(' '.join(token.value for token in part))
        else:
            break
    else:
        return families


@validator()
@single_token
def font_size(token):
    """``font-size`` property validation."""
    length = get_length(token, percentage=True)
    if length:
        return length
    font_size_keyword = get_keyword(token)
    if font_size_keyword in ('smaller', 'larger'):
        raise InvalidValues('value not supported yet')
    if (
        font_size_keyword in computed_values.FONT_SIZE_KEYWORDS #or
        #keyword in ('smaller', 'larger')
    ):
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
        strings = [v.value for v in tokens]
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
        args = [a.value for a in args]
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
            return 'external', iri_to_uri(safe_urljoin(base_url, token.value))
    function = parse_function(token)
    if function:
        name, args = function
        prototype = (name, [a.type for a in args])
        args = [a.value for a in args]
        if prototype == ('attr', ['IDENT']):
            return (name, args[0])


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
                    value = INITIAL_VALUES[actual_new_name.replace('-', '_')]

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
        elif image([token], base_url) is not None:
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
@generic_expander('-color', '-image', '-repeat', '-attachment', '-position',
                  wants_base_url=True)
def expand_background(name, tokens, base_url):
    """Expand the ``background`` shorthand property.

    See http://www.w3.org/TR/CSS21/colors.html#propdef-background

    """
    # Make `tokens` a stack
    tokens = list(reversed(tokens))
    while tokens:
        token = tokens.pop()
        if parse_color(token) is not None:
            suffix = '-color'
        elif image([token], base_url) is not None:
            suffix = '-image'
        elif background_repeat([token]) is not None:
            suffix = '-repeat'
        elif background_attachment([token]) is not None:
            suffix = '-attachment'
        elif background_position([token]):
            if tokens:
                next_token = tokens.pop()
                if background_position([token, next_token]):
                    # Two consecutive '-position' tokens, yield them together
                    yield '-position', [token, next_token]
                    continue
                else:
                    # The next token is not a '-position', put it back
                    # for the next loop iteration
                    tokens.append(next_token)
            # A single '-position' token
            suffix = '-position'
        else:
            raise InvalidValues
        yield suffix, [token]


@expander('font')
@generic_expander('-style', '-variant', '-weight', '-size',
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
        getattr(LOGGER, level)('Ignored `%s: %s` at %i:%i, %s.',
            declaration.name, declaration.value.as_css(),
            declaration.line, declaration.column, reason)

    for declaration in declarations:
        name = declaration.name

        if name in PREFIXED and not name.startswith(PREFIX):
            validation_error('warn',
                'the property is experimental or non-standard, use '
                + PREFIX + name)
            continue

        if name in NOT_PRINT_MEDIA:
            validation_error('info',
                'the property does not apply for the print media')
            continue

        if name.startswith(PREFIX):
            unprefixed_name = name[len(PREFIX):]
            if unprefixed_name in UNPREFIXED:
                validation_error('warn',
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
            validation_error('warn',
                exc.args[0] if exc.args and exc.args[0] else 'invalid value')
            continue

        priority = declaration.priority
        for long_name, value in result:
            yield long_name.replace('-', '_'), value, priority
