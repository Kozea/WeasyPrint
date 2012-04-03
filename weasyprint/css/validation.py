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
from tinycss.parsing import split_on_comma

from ..logger import LOGGER
from ..formatting_structure import counters
from ..compat import urljoin
from .values import get_keyword, get_single_keyword, make_percentage_value
from .properties import INITIAL_VALUES, NOT_PRINT_MEDIA
from . import computed_values


# TODO: unit-test these validators

# keyword -> (open, insert)
CONTENT_QUOTE_KEYWORDS = {
    'open-quote': (True, True),
    'close-quote': (False, True),
    'no-open-quote': (True, False),
    'no-close-quote': (False, False),
}

BACKGROUND_POSITION_PERCENTAGES = {
    'top': make_percentage_value(0),
    'left': make_percentage_value(0),
    'center': make_percentage_value(50),
    'bottom': make_percentage_value(100),
    'right': make_percentage_value(100),
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
# The same replacement was done on property names:
PREFIX = '-weasy-'.replace('-', '_')


class InvalidValues(ValueError):
    """Invalid or unsupported values for a known CSS property."""


# Validators

def validator(property_name=None, prefixed=False, wants_base_url=False):
    """Decorator adding a function to the ``VALIDATORS``.

    The name of the property covered by the decorated function is set to
    ``property_name`` if given, or is inferred from the function name
    (replacing underscores by hyphens).

    """
    def decorator(function):
        """Add ``function`` to the ``VALIDATORS``."""
        if property_name is None:
            name = function.__name__
        else:
            name = property_name.replace('-', '_')
        assert name in INITIAL_VALUES, name
        assert name not in VALIDATORS, name

        function.wants_base_url = wants_base_url
        VALIDATORS[name] = function
        if prefixed:
            PREFIXED.add(name)
        return function
    return decorator


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


def is_dimension(token, negative=True):
    """Get if ``token`` is a dimension.

    The ``negative`` argument sets wether negative tokens are allowed.

    """
    type_ = token.type
    # Units may be ommited on zero lenghts.
    return (
        type_ == 'DIMENSION' and (negative or token.value >= 0) and (
            token.unit in computed_values.LENGTHS_TO_PIXELS or
            token.unit in ('em', 'ex'))
        ) or (type_ in ('NUMBER', 'INTEGER') and token.value == 0)


def is_dimension_or_percentage(token, negative=True):
    """Get if ``token`` is a dimension or a percentage.

    The ``negative`` argument sets wether negative tokens are allowed.

    """
    return is_dimension(token, negative) or (
        token.type == 'PERCENTAGE' and (negative or token.value >= 0))


def is_angle(token):
    """Return whether the argument is an angle token."""
    return token.type == 'DIMENSION' and \
        token.unit in computed_values.ANGLE_TO_RADIANS


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
        return urljoin(base_url, token.value)


@validator('transform-origin', prefixed=True)  # Not in CR yet
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
        elif is_dimension_or_percentage(token):
            return token, center

    elif len(tokens) == 2:
        token_1, token_2 = tokens
        keyword_1, keyword_2 = map(get_keyword, tokens)
        if is_dimension_or_percentage(token_1):
            if keyword_2 in ('top', 'center', 'bottom'):
                return token_1, BACKGROUND_POSITION_PERCENTAGES[keyword_2]
            elif is_dimension_or_percentage(token_2):
                return token_1, token_2
        elif is_dimension_or_percentage(token_2):
            if keyword_1 in ('left', 'center', 'right'):
                return BACKGROUND_POSITION_PERCENTAGES[keyword_1], token_2
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
        if is_dimension_or_percentage(token, negative=False):
            return (token, 'auto')
    elif len(tokens) == 2:
        new_tokens = []
        for token in tokens:
            if get_keyword(token) == 'auto':
                new_tokens.append('auto')
            elif is_dimension_or_percentage(token, negative=False):
                new_tokens.append(token)
            else:
                return
        return tuple(tokens)


@validator('background_clip')
@validator('background_origin')
@single_keyword
def box(keyword):
    """Validation for the ``<box>`` type used in ``background-clip``
    and ``background-origin``."""
    return keyword in ('border-box', 'padding-box', 'content-box')


@validator()
def border_spacing(tokens):
    """Validator for the `border-spacing` property."""
    if all(is_dimension(token, negative=False) for token in tokens):
        if len(tokens) == 1:
            return (tokens[0], tokens[0])
        elif len(tokens) == 2:
            return tuple(tokens)


@validator('border-top-style')
@validator('border-right-style')
@validator('border-left-style')
@validator('border-bottom-style')
@single_keyword
def border_style(keyword):
    """``border-*-style`` properties validation."""
    return keyword in ('none', 'hidden', 'dotted', 'dashed', 'double',
                       'inset', 'outset', 'groove', 'ridge', 'solid')


@validator('border-top-width')
@validator('border-right-width')
@validator('border-left-width')
@validator('border-bottom-width')
@single_token
def border_width(token):
    """``border-*-width`` properties validation."""
    if is_dimension(token, negative=False):
        return token
    keyword = get_keyword(token)
    if keyword in ('thin', 'medium', 'thick'):
        return keyword


@validator()
@single_keyword
def box_sizing(keyword):
    """Validation for the ``box-sizing`` property from css3-ui"""
    return keyword in ('padding-box', 'border-box')


@validator()
@single_keyword
def caption_side(keyword):
    """``caption-side`` properties validation."""
    return keyword in ('top', 'bottom')


@validator()
@single_token
def clip(token):
    """Validation for the ``clip`` property."""
    function = parse_function(token)
    if function:
        name, args = function
        if name == 'rect' and len(args) == 4:
            tokens = []
            for arg in args:
                if get_keyword(arg) == 'auto':
                    tokens.append('auto')
                elif is_dimension(arg, negative=True):
                    tokens.append(arg)
                else:
                    raise InvalidValues
            return tokens
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
        return ('URI', urljoin(base_url, token.value))
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
    if token is None:
        return  # expected at least one token
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


#@validator('top')
#@validator('right')
#@validator('left')
#@validator('bottom')
@validator('margin-top')
@validator('margin-right')
@validator('margin-bottom')
@validator('margin-left')
@single_token
def lenght_precentage_or_auto(token, negative=True):
    """``margin-*`` properties validation."""
    if is_dimension_or_percentage(token, negative):
        return token
    if get_keyword(token) == 'auto':
        return 'auto'


@validator('height')
@validator('width')
@single_token
def width_height(token):
    """Validation for the ``width`` and ``height`` properties."""
    return lenght_precentage_or_auto.__func__(token, negative=False)


@validator()
@single_keyword
def direction(keyword):
    """``direction`` property validation."""
    return keyword in ('ltr', 'rtl')


@validator()
@single_keyword
def display(keyword):
    """``display`` property validation."""
    if keyword in ('inline-block',):
        raise InvalidValues('value not supported yet')
    return keyword in (
        'inline', 'block', 'list-item', 'none',
        'table', 'inline-table', 'table-caption',
        'table-row-group', 'table-header-group', 'table-footer-group',
        'table-row', 'table-column-group', 'table-column', 'table-cell')


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
    if is_dimension_or_percentage(token):
        return token
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


@validator('letter_spacing')
@validator('word_spacing')
@single_token
def spacing(token):
    """Validation for ``letter-spacing`` and ``word-spacing``."""
    if get_keyword(token) == 'normal':
        return 'normal'
    if is_dimension(token):
        return token


@validator()
@single_token
def line_height(token):
    """``line-height`` property validation."""
    if get_keyword(token) == 'normal':
        return 'normal'
    if (token.type in ('NUMBER', 'INTEGER', 'DIMENSION', 'PERCENTAGE') and
            token.value >= 0):
        return token


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
@single_token
def length_or_precentage(token):
    """``padding-*`` properties validation."""
    if is_dimension_or_percentage(token, negative=False):
        return token


@validator()
@single_token
def opacity(token):
    """Validation for the ``opacity`` property."""
    if token.type in ('NUMBER', 'INTEGER'):
        return min(1, max(0, token.value))


@validator('orphans')
@validator('widows')
@single_token
def orphans_widows(token):
    """Validation for the ``orphans`` or ``widows`` properties."""
    if token.type == 'INTEGER':
        value = token.value
        if int(value) == value and value >= 1:
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
    if keyword == 'avoid':
        raise InvalidValues('value not supported yet')
    return keyword in ('auto', 'always', 'left', 'right')


# Not very useful, might as well ignore the property anyway.
# Keep it for completeness.
@validator()
@single_keyword
def page_break_inside(keyword):
    """Validation for the ``page-break-inside`` property."""
    return keyword in ('auto', 'avoid')


@validator()
@single_keyword
def position(keyword):
    """``position`` property validation."""
    if keyword in ('relative', 'absolute', 'fixed'):
        raise InvalidValues('value not supported yet')
    return keyword in ('static',)


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
        unique = frozenset(keywords)
        if len(unique) == len(keywords):
            # No duplicate
            return unique


@validator()
@single_token
def text_indent(token):
    """``text-indent`` property validation."""
    if is_dimension_or_percentage(token, negative=True):
        return token


@validator()
@single_keyword
def text_transform(keyword):
    """``text-align`` property validation."""
    return keyword in ('none', 'uppercase', 'lowercase', 'capitalize')


@validator()
@single_token
def vertical_align(token):
    """Validation for the ``vertical-align`` property"""
    if is_dimension_or_percentage(token, negative=True):
        return token
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


@validator(prefixed=True)  # Taken from SVG
@single_keyword
def image_rendering(keyword):
    """Validation for ``image-rendering``."""
    return keyword in ('auto', 'optimizeSpeed', 'optimizeQuality')


@validator(prefixed=True)  # Not in CR yet
def size(tokens):
    """``size`` property validation.

    See http://www.w3.org/TR/css3-page/#page-size-prop

    """
    if is_dimension(tokens[0]):
        if len(tokens) == 1:
            return tokens * 2
        elif len(tokens) == 2 and is_dimension(tokens[1]):
            return tokens

    keywords = [get_keyword(v) for v in tokens]
    if len(keywords) == 1:
        keyword = keywords[0]
        if keyword in ('auto', 'portrait'):
            return INITIAL_VALUES['size']
        elif keyword == 'landscape':
            height, width = INITIAL_VALUES['size']
            return width, height
        elif keyword in computed_values.PAGE_SIZES:
            return computed_values.PAGE_SIZES[keyword]

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


@validator(prefixed=True)  # Not in CR yet
def transform(tokens):
    if get_single_keyword(tokens) == 'none':
        return 'none'
    else:
        return [transform_function(v) for v in tokens]


def transform_function(token):
    function = parse_function(token)
    if not function:
        raise InvalidValues
    name, args = function

    if len(args) == 1:
        if name in ('rotate', 'skewx', 'skewy') and is_angle(args[0]):
            return name, args[0]
        elif name in ('translatex', 'translate') and is_dimension_or_percentage(args[0]):
            return 'translate', (args[0], 0)
        elif name == 'translatey' and is_dimension_or_percentage(args[0]):
            return 'translate', (0, args[0])
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
        if name == 'translate' and all(map(is_dimension_or_percentage, args)):
            return name, args
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
    property_name = property_name.replace('-', '_')
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
    for suffix, token in zip(('_top', '_right', '_bottom', '_left'), tokens):
        i = name.rfind('_')
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
    expanded_names = [name.replace('-', '_') for name in expanded_names]
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
                            % (new_name.strip('_'), name))
                    results[new_name] = new_token

            for new_name in expanded_names:
                if new_name.startswith('_'):
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
                    value = INITIAL_VALUES[actual_new_name]

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
            suffix = '_type'
            type_specified = True
        elif list_style_position([token]) is not None:
            suffix = '_position'
        elif image([token], base_url) is not None:
            suffix = '_image'
            image_specified = True
        else:
            raise InvalidValues
        yield suffix, [token]

    if not type_specified and none_count:
        yield '_type', [none_token]
        none_count -= 1

    if not image_specified and none_count:
        yield '_image', [none_token]
        none_count -= 1

    if none_count:
        # Too many none tokens.
        raise InvalidValues


@expander('border')
def expand_border(base_url, name, tokens):
    """Expand the ``border`` shorthand property.

    See http://www.w3.org/TR/CSS21/box.html#propdef-border

    """
    for suffix in ('_top', '_right', '_bottom', '_left'):
        for new_prop in expand_border_side(base_url, name + suffix, tokens):
            yield new_prop


@expander('border-top')
@expander('border-right')
@expander('border-bottom')
@expander('border-left')
@generic_expander('-width', '-color', '-style')
def expand_border_side(name, tokens):
    """Expand the ``border-*`` shorthand properties.

    See http://www.w3.org/TR/CSS21/box.html#propdef-border-top

    """
    for token in tokens:
        if parse_color(token) is not None:
            suffix = '_color'
        elif border_width([token]) is not None:
            suffix = '_width'
        elif border_style([token]) is not None:
            suffix = '_style'
        else:
            raise InvalidValues
        yield suffix, [token]


def is_valid_background_positition(token):
    """Tell whether the token is valid for ``background-position``."""
    return (
        token.type in ('DIMENSION', 'PERCENTAGE') or
        (token.type in ('NUMBER', 'INTEGER') and token.value == 0) or
        get_keyword(token) in ('left', 'right', 'top', 'bottom', 'center'))


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
            suffix = '_color'
        elif image([token], base_url) is not None:
            suffix = '_image'
        elif background_repeat([token]) is not None:
            suffix = '_repeat'
        elif background_attachment([token]) is not None:
            suffix = '_attachment'
        elif background_position([token]):
            if tokens:
                next_token = tokens.pop()
                if background_position([token, next_token]):
                    # Two consecutive '-position' tokens, yield them together
                    yield '_position', [token, next_token]
                    continue
                else:
                    # The next token is not a '-position', put it back
                    # for the next loop iteration
                    tokens.append(next_token)
            # A single '-position' token
            suffix = '_position'
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
        LOGGER.warn(
            'System fonts are not supported, `font: %s` ignored.',
            expand_font_keyword)
        return

    # Make `tokens` a stack
    tokens = list(reversed(tokens))
    # Values for font-style font-variant and font-weight can come in any
    # order and are all optional.
    while tokens:
        token = tokens.pop()
        if get_keyword(token) == 'normal':
            # Just ignore 'normal' keywords. Unspecified properties will get
            # their initial token, which is 'normal' for all three here.
            continue

        if font_style([token]) is not None:
            suffix = '_style'
        elif font_variant([token]) is not None:
            suffix = '_variant'
        elif font_weight([token]) is not None:
            suffix = '_weight'
        else:
            # We’re done with these three, continue with font-size
            break
        yield suffix, [token]

    # Then font-size is mandatory
    # Latest `token` from the loop.
    if font_size([token]) is None:
        raise InvalidValues
    yield '_size', [token]

    # Then line-height is optional, but font-family is not so the list
    # must not be empty yet
    if not tokens:
        raise InvalidValues

    token = tokens.pop()
    if token.type == 'DELIM' and token.value == '/':
        token = tokens.pop()
        if line_height([token]) is None:
            raise InvalidValues
        yield 'line_height', [token]
    else:
        # We pop()ed a font-family, add it back
        tokens.append(token)

    # Reverse the stack to get normal list
    tokens.reverse()
    if font_family(tokens) is None:
        raise InvalidValues
    yield '_family', tokens


def validate_non_shorthand(base_url, name, tokens, required=False):
    """Default validator for non-shorthand properties."""
    if not required and name not in INITIAL_VALUES:
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


def validate_and_expand(base_url, name, tokens):
    """Expand and validate shorthand properties.

    The invalid or unsupported declarations are ignored and logged.

    Return a iterable of ``(name, value)`` tuples.

    """
    if name in PREFIXED and not name.startswith(PREFIX):
        level = 'warn'
        reason = ('the property is experimental, use ' +
                  (PREFIX + name).replace('_', '-'))
    elif name in NOT_PRINT_MEDIA:
        level = 'info'
        reason = 'the property does not apply for the print media'
    else:
        if name.startswith(PREFIX):
            unprefixed_name = name[len(PREFIX):]
            if unprefixed_name in PREFIXED:
                name = unprefixed_name
        expander_ = EXPANDERS.get(name, validate_non_shorthand)
        try:
            tokens = [token for token in tokens if token.type != 'S']
            results = expander_(base_url, name, tokens)
            # Use list() to consume any generator now,
            # so that InvalidValues is caught.
            return list(results)
        except InvalidValues as exc:
            level = 'warn'
            if exc.args and exc.args[0]:
                reason = exc.args[0]
            else:
                reason = 'invalid value'
    getattr(LOGGER, level)('Ignored declaration: `%s: %s`, %s.',
        name.replace('_', '-'), ''.join(v.as_css for v in tokens), reason)
    return []
