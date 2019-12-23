"""
    weasyprint.css.validation.properties
    ------------------------------------

    Validate properties.
    See http://www.w3.org/TR/CSS21/propidx.html and various CSS3 modules.

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from tinycss2.color3 import parse_color

from ...formatting_structure import counters
from .. import computed_values
from ..properties import KNOWN_PROPERTIES, Dimension
from ..utils import (
    InvalidValues, check_var_function, comma_separated_list, get_angle,
    get_content_list, get_content_list_token, get_custom_ident, get_image,
    get_keyword, get_length, get_resolution, get_single_keyword, get_url,
    parse_2d_position, parse_function, parse_position, single_keyword,
    single_token)

PREFIX = '-weasy-'
PROPRIETARY = set()
UNSTABLE = set()

# Yes/no validators for non-shorthand properties
# Maps property names to functions taking a property name and a value list,
# returning a value or None for invalid.
# For properties that take a single value, that value is returned by itself
# instead of a list.
PROPERTIES = {}


# Validators

def property(property_name=None, proprietary=False, unstable=False,
             wants_base_url=False):
    """Decorator adding a function to the ``PROPERTIES``.

    The name of the property covered by the decorated function is set to
    ``property_name`` if given, or is inferred from the function name
    (replacing underscores by hyphens).

    :param proprietary:
        Proprietary (vendor-specific, non-standard) are prefixed: anchors can
        for example be set using ``-weasy-anchor: attr(id)``.
        See https://www.w3.org/TR/CSS/#proprietary
    :param unstable:
        Mark properties that are defined in specifications that didn't reach
        the Candidate Recommandation stage. They can be used both
        vendor-prefixed or unprefixed.
        See https://www.w3.org/TR/CSS/#unstable-syntax
    :param wants_base_url:
        The function takes the stylesheet’s base URL as an additional
        parameter.

    """
    def decorator(function):
        """Add ``function`` to the ``PROPERTIES``."""
        if property_name is None:
            name = function.__name__.replace('_', '-')
        else:
            name = property_name
        assert name in KNOWN_PROPERTIES, name
        assert name not in PROPERTIES, name

        function.wants_base_url = wants_base_url
        PROPERTIES[name] = function
        if proprietary:
            PROPRIETARY.add(name)
        if unstable:
            UNSTABLE.add(name)
        return function
    return decorator


def validate_non_shorthand(base_url, name, tokens, required=False):
    """Default validator for non-shorthand properties."""
    if name.startswith('--'):
        # TODO: validate content
        return ((name, tokens),)

    if not required and name not in KNOWN_PROPERTIES:
        hyphens_name = name.replace('_', '-')
        if hyphens_name in KNOWN_PROPERTIES:
            raise InvalidValues('did you mean %s?' % hyphens_name)
        else:
            raise InvalidValues('unknown property')

    if not required and name not in PROPERTIES:
        raise InvalidValues('property not supported yet')

    for token in tokens:
        var_function = check_var_function(token)
        if var_function:
            return ((name, var_function),)

    keyword = get_single_keyword(tokens)
    if keyword in ('initial', 'inherit'):
        value = keyword
    else:
        function = PROPERTIES[name]
        if function.wants_base_url:
            value = function(tokens, base_url)
        else:
            value = function(tokens)
        if value is None:
            raise InvalidValues
    return ((name, value),)


@property()
@comma_separated_list
@single_keyword
def background_attachment(keyword):
    """``background-attachment`` property validation."""
    return keyword in ('scroll', 'fixed', 'local')


@property('background-color')
@property('border-top-color')
@property('border-right-color')
@property('border-bottom-color')
@property('border-left-color')
@property('column-rule-color', unstable=True)
@property('text-decoration-color')
@single_token
def other_colors(token):
    return parse_color(token)


@property()
@single_token
def outline_color(token):
    if get_keyword(token) == 'invert':
        return 'currentColor'
    else:
        return parse_color(token)


@property()
@single_keyword
def border_collapse(keyword):
    return keyword in ('separate', 'collapse')


@property()
@single_keyword
def empty_cells(keyword):
    """``empty-cells`` property validation."""
    return keyword in ('show', 'hide')


@property('color')
@single_token
def color(token):
    """``*-color`` and ``color`` properties validation."""
    result = parse_color(token)
    if result == 'currentColor':
        return 'inherit'
    else:
        return result


@property('background-image', wants_base_url=True)
@comma_separated_list
@single_token
def background_image(token, base_url):
    if token.type != 'function':
        if get_keyword(token) == 'none':
            return 'none', None
    return get_image(token, base_url)


@property('list-style-image', wants_base_url=True)
@single_token
def list_style_image(token, base_url):
    """``list-style-image`` property validation."""
    if token.type != 'function':
        if get_keyword(token) == 'none':
            return 'none', None
        parsed_url = get_url(token, base_url)
        if parsed_url:
            if parsed_url[0] == 'url' and parsed_url[1][0] == 'external':
                return 'url', parsed_url[1][1]


@property()
def transform_origin(tokens):
    """``transform-origin`` property validation."""
    if len(tokens) == 3:
        # Ignore third parameter as 3D transforms are ignored.
        tokens = tokens[:2]
    return parse_2d_position(tokens)


@property()
@comma_separated_list
def background_position(tokens):
    """``background-position`` property validation."""
    return parse_position(tokens)


@property()
@comma_separated_list
def object_position(tokens):
    """``object-position`` property validation."""
    return parse_position(tokens)


@property()
@comma_separated_list
def background_repeat(tokens):
    """``background-repeat`` property validation."""
    keywords = tuple(map(get_keyword, tokens))
    if keywords == ('repeat-x',):
        return ('repeat', 'no-repeat')
    if keywords == ('repeat-y',):
        return ('no-repeat', 'repeat')
    if keywords in (('no-repeat',), ('repeat',), ('space',), ('round',)):
        return keywords * 2
    if len(keywords) == 2 and all(
            k in ('no-repeat', 'repeat', 'space', 'round')
            for k in keywords):
        return keywords


@property()
@comma_separated_list
def background_size(tokens):
    """Validation for ``background-size``."""
    if len(tokens) == 1:
        token = tokens[0]
        keyword = get_keyword(token)
        if keyword in ('contain', 'cover'):
            return keyword
        if keyword == 'auto':
            return ('auto', 'auto')
        length = get_length(token, negative=False, percentage=True)
        if length:
            return (length, 'auto')
    elif len(tokens) == 2:
        values = []
        for token in tokens:
            length = get_length(token, negative=False, percentage=True)
            if length:
                values.append(length)
            elif get_keyword(token) == 'auto':
                values.append('auto')
        if len(values) == 2:
            return tuple(values)


@property('background-clip')
@property('background-origin')
@comma_separated_list
@single_keyword
def box(keyword):
    """Validation for the ``<box>`` type used in ``background-clip``
    and ``background-origin``."""
    return keyword in ('border-box', 'padding-box', 'content-box')


@property()
def border_spacing(tokens):
    """Validator for the `border-spacing` property."""
    lengths = [get_length(token, negative=False) for token in tokens]
    if all(lengths):
        if len(lengths) == 1:
            return (lengths[0], lengths[0])
        elif len(lengths) == 2:
            return tuple(lengths)


@property('border-top-right-radius')
@property('border-bottom-right-radius')
@property('border-bottom-left-radius')
@property('border-top-left-radius')
def border_corner_radius(tokens):
    """Validator for the `border-*-radius` properties."""
    lengths = [
        get_length(token, negative=False, percentage=True) for token in tokens]
    if all(lengths):
        if len(lengths) == 1:
            return (lengths[0], lengths[0])
        elif len(lengths) == 2:
            return tuple(lengths)


@property('border-top-style')
@property('border-right-style')
@property('border-left-style')
@property('border-bottom-style')
@property('column-rule-style', unstable=True)
@single_keyword
def border_style(keyword):
    """``border-*-style`` properties validation."""
    return keyword in ('none', 'hidden', 'dotted', 'dashed', 'double',
                       'inset', 'outset', 'groove', 'ridge', 'solid')


@property('break-before')
@property('break-after')
@single_keyword
def break_before_after(keyword):
    """``break-before`` and ``break-after`` properties validation."""
    # 'always' is defined as an alias to 'page' in multi-column
    # https://www.w3.org/TR/css3-multicol/#column-breaks
    return keyword in ('auto', 'avoid', 'avoid-page', 'page', 'left', 'right',
                       'recto', 'verso', 'avoid-column', 'column', 'always')


@property()
@single_keyword
def break_inside(keyword):
    """``break-inside`` property validation."""
    return keyword in ('auto', 'avoid', 'avoid-page', 'avoid-column')


@property()
@single_keyword
def box_decoration_break(keyword):
    """``box-decoration-break`` property validation."""
    return keyword in ('slice', 'clone')


@property(unstable=True)
@single_keyword
def margin_break(keyword):
    """``margin-break`` property validation."""
    return keyword in ('auto', 'keep', 'discard')


@property(unstable=True)
@single_token
def page(token):
    """``page`` property validation."""
    if token.type == 'ident':
        return 'auto' if token.lower_value == 'auto' else token.value


@property('bleed-left', unstable=True)
@property('bleed-right', unstable=True)
@property('bleed-top', unstable=True)
@property('bleed-bottom', unstable=True)
@single_token
def bleed(token):
    """``bleed`` property validation."""
    keyword = get_keyword(token)
    if keyword == 'auto':
        return 'auto'
    else:
        return get_length(token)


@property(unstable=True)
def marks(tokens):
    """``marks`` property validation."""
    if len(tokens) == 2:
        keywords = tuple(get_keyword(token) for token in tokens)
        if 'crop' in keywords and 'cross' in keywords:
            return keywords
    elif len(tokens) == 1:
        keyword = get_keyword(tokens[0])
        if keyword in ('crop', 'cross'):
            return (keyword,)
        elif keyword == 'none':
            return ()


@property('outline-style')
@single_keyword
def outline_style(keyword):
    """``outline-style`` properties validation."""
    return keyword in ('none', 'dotted', 'dashed', 'double', 'inset',
                       'outset', 'groove', 'ridge', 'solid')


@property('border-top-width')
@property('border-right-width')
@property('border-left-width')
@property('border-bottom-width')
@property('column-rule-width', unstable=True)
@property('outline-width')
@single_token
def border_width(token):
    """Border, column rule and outline widths properties validation."""
    length = get_length(token, negative=False)
    if length:
        return length
    keyword = get_keyword(token)
    if keyword in ('thin', 'medium', 'thick'):
        return keyword


@property(unstable=True)
@single_token
def column_width(token):
    """``column-width`` property validation."""
    length = get_length(token, negative=False)
    if length:
        return length
    keyword = get_keyword(token)
    if keyword == 'auto':
        return keyword


@property(unstable=True)
@single_keyword
def column_span(keyword):
    """``column-span`` property validation."""
    return keyword in ('all', 'none')


@property()
@single_keyword
def box_sizing(keyword):
    """Validation for the ``box-sizing`` property from css3-ui"""
    return keyword in ('padding-box', 'border-box', 'content-box')


@property()
@single_keyword
def caption_side(keyword):
    """``caption-side`` properties validation."""
    return keyword in ('top', 'bottom')


@property()
@single_keyword
def clear(keyword):
    """``clear`` property validation."""
    return keyword in ('left', 'right', 'both', 'none')


@property()
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
                return tuple(values)
    if get_keyword(token) == 'auto':
        return ()


@property(wants_base_url=True)
def content(tokens, base_url):
    """``content`` property validation."""
    # See https://www.w3.org/TR/css-content-3/#content-property
    tokens = list(tokens)
    parsed_tokens = []
    while tokens:
        if len(tokens) >= 2 and (
                tokens[1].type == 'literal' and tokens[1].value == ','):
            token, tokens = tokens[0], tokens[2:]
            parsed_token = (
                get_image(token, base_url) or get_url(token, base_url))
            if parsed_token:
                parsed_tokens.append(parsed_token)
            else:
                return
        else:
            break
    if len(tokens) == 0:
        return
    if len(tokens) >= 3 and tokens[-1].type == 'string' and (
            tokens[-2].type == 'literal' and tokens[-2].value == '/'):
        # Ignore text for speech
        tokens = tokens[:-2]
    keyword = get_single_keyword(tokens)
    if keyword in ('normal', 'none'):
        return (keyword,)
    return get_content_list(tokens, base_url)


@property()
def counter_increment(tokens):
    """``counter-increment`` property validation."""
    return counter(tokens, default_integer=1)


@property()
def counter_reset(tokens):
    """``counter-reset`` property validation."""
    return counter(tokens, default_integer=0)


def counter(tokens, default_integer):
    """``counter-increment`` and ``counter-reset`` properties validation."""
    if get_single_keyword(tokens) == 'none':
        return ()
    tokens = iter(tokens)
    token = next(tokens, None)
    assert token, 'got an empty token list'
    results = []
    while token is not None:
        if token.type != 'ident':
            return  # expected a keyword here
        counter_name = token.value
        if counter_name in ('none', 'initial', 'inherit'):
            raise InvalidValues('Invalid counter name: ' + counter_name)
        token = next(tokens, None)
        if token is not None and (
                token.type == 'number' and token.int_value is not None):
            # Found an integer. Use it and get the next token
            integer = token.int_value
            token = next(tokens, None)
        else:
            # Not an integer. Might be the next counter name.
            # Keep `token` for the next loop iteration.
            integer = default_integer
        results.append((counter_name, integer))
    return tuple(results)


@property('top')
@property('right')
@property('left')
@property('bottom')
@property('margin-top')
@property('margin-right')
@property('margin-bottom')
@property('margin-left')
@single_token
def lenght_precentage_or_auto(token):
    """``margin-*`` properties validation."""
    length = get_length(token, percentage=True)
    if length:
        return length
    if get_keyword(token) == 'auto':
        return 'auto'


@property('height')
@property('width')
@single_token
def width_height(token):
    """Validation for the ``width`` and ``height`` properties."""
    length = get_length(token, negative=False, percentage=True)
    if length:
        return length
    if get_keyword(token) == 'auto':
        return 'auto'


@property(unstable=True)
@single_token
def column_gap(token):
    """Validation for the ``column-gap`` property."""
    length = get_length(token, negative=False)
    if length:
        return length
    keyword = get_keyword(token)
    if keyword == 'normal':
        return keyword


@property(unstable=True)
@single_keyword
def column_fill(keyword):
    """``column-fill`` property validation."""
    return keyword in ('auto', 'balance')


@property()
@single_keyword
def direction(keyword):
    """``direction`` property validation."""
    return keyword in ('ltr', 'rtl')


@property()
@single_keyword
def display(keyword):
    """``display`` property validation."""
    return keyword in (
        'inline', 'block', 'inline-block', 'list-item', 'none',
        'table', 'inline-table', 'table-caption',
        'table-row-group', 'table-header-group', 'table-footer-group',
        'table-row', 'table-column-group', 'table-column', 'table-cell',
        'flex', 'inline-flex')


@property('float')
@single_keyword
def float_(keyword):  # XXX do not hide the "float" builtin
    """``float`` property validation."""
    return keyword in ('left', 'right', 'none')


@property()
@comma_separated_list
def font_family(tokens):
    """``font-family`` property validation."""
    if len(tokens) == 1 and tokens[0].type == 'string':
        return tokens[0].value
    elif tokens and all(token.type == 'ident' for token in tokens):
        return ' '.join(token.value for token in tokens)


@property()
@single_keyword
def font_kerning(keyword):
    return keyword in ('auto', 'normal', 'none')


@property()
@single_token
def font_language_override(token):
    keyword = get_keyword(token)
    if keyword == 'normal':
        return keyword
    elif token.type == 'string':
        return token.value


@property()
def font_variant_ligatures(tokens):
    if len(tokens) == 1:
        keyword = get_keyword(tokens[0])
        if keyword in ('normal', 'none'):
            return keyword
    values = []
    couples = (
        ('common-ligatures', 'no-common-ligatures'),
        ('historical-ligatures', 'no-historical-ligatures'),
        ('discretionary-ligatures', 'no-discretionary-ligatures'),
        ('contextual', 'no-contextual'))
    all_values = []
    for couple in couples:
        all_values.extend(couple)
    for token in tokens:
        if token.type != 'ident':
            return None
        if token.value in all_values:
            concurrent_values = [
                couple for couple in couples if token.value in couple][0]
            if any(value in values for value in concurrent_values):
                return None
            else:
                values.append(token.value)
        else:
            return None
    if values:
        return tuple(values)


@property()
@single_keyword
def font_variant_position(keyword):
    return keyword in ('normal', 'sub', 'super')


@property()
@single_keyword
def font_variant_caps(keyword):
    return keyword in (
        'normal', 'small-caps', 'all-small-caps', 'petite-caps',
        'all-petite-caps', 'unicase', 'titling-caps')


@property()
def font_variant_numeric(tokens):
    if len(tokens) == 1:
        keyword = get_keyword(tokens[0])
        if keyword == 'normal':
            return keyword
    values = []
    couples = (
        ('lining-nums', 'oldstyle-nums'),
        ('proportional-nums', 'tabular-nums'),
        ('diagonal-fractions', 'stacked-fractions'),
        ('ordinal',), ('slashed-zero',))
    all_values = []
    for couple in couples:
        all_values.extend(couple)
    for token in tokens:
        if token.type != 'ident':
            return None
        if token.value in all_values:
            concurrent_values = [
                couple for couple in couples if token.value in couple][0]
            if any(value in values for value in concurrent_values):
                return None
            else:
                values.append(token.value)
        else:
            return None
    if values:
        return tuple(values)


@property()
def font_feature_settings(tokens):
    """``font-feature-settings`` property validation."""
    if len(tokens) == 1 and get_keyword(tokens[0]) == 'normal':
        return 'normal'

    @comma_separated_list
    def font_feature_settings_list(tokens):
        feature, value = None, None

        if len(tokens) == 2:
            tokens, token = tokens[:-1], tokens[-1]
            if token.type == 'ident':
                value = {'on': 1, 'off': 0}.get(token.value)
            elif (token.type == 'number' and
                    token.int_value is not None and token.int_value >= 0):
                value = token.int_value
        elif len(tokens) == 1:
            value = 1

        if len(tokens) == 1:
            token, = tokens
            if token.type == 'string' and len(token.value) == 4:
                if all(0x20 <= ord(letter) <= 0x7f for letter in token.value):
                    feature = token.value

        if feature is not None and value is not None:
            return feature, value

    return font_feature_settings_list(tokens)


@property()
@single_keyword
def font_variant_alternates(keyword):
    # TODO: support other values
    # See https://www.w3.org/TR/css-fonts-3/#font-variant-caps-prop
    return keyword in ('normal', 'historical-forms')


@property()
def font_variant_east_asian(tokens):
    if len(tokens) == 1:
        keyword = get_keyword(tokens[0])
        if keyword == 'normal':
            return keyword
    values = []
    couples = (
        ('jis78', 'jis83', 'jis90', 'jis04', 'simplified', 'traditional'),
        ('full-width', 'proportional-width'),
        ('ruby',))
    all_values = []
    for couple in couples:
        all_values.extend(couple)
    for token in tokens:
        if token.type != 'ident':
            return None
        if token.value in all_values:
            concurrent_values = [
                couple for couple in couples if token.value in couple][0]
            if any(value in values for value in concurrent_values):
                return None
            else:
                values.append(token.value)
        else:
            return None
    if values:
        return tuple(values)


@property()
@single_token
def font_size(token):
    """``font-size`` property validation."""
    length = get_length(token, negative=False, percentage=True)
    if length:
        return length
    font_size_keyword = get_keyword(token)
    if font_size_keyword in ('smaller', 'larger'):
        return font_size_keyword
    if font_size_keyword in computed_values.FONT_SIZE_KEYWORDS:
        return font_size_keyword


@property()
@single_keyword
def font_style(keyword):
    """``font-style`` property validation."""
    return keyword in ('normal', 'italic', 'oblique')


@property()
@single_keyword
def font_stretch(keyword):
    """Validation for the ``font-stretch`` property."""
    return keyword in (
        'ultra-condensed', 'extra-condensed', 'condensed', 'semi-condensed',
        'normal',
        'semi-expanded', 'expanded', 'extra-expanded', 'ultra-expanded')


@property()
@single_token
def font_weight(token):
    """``font-weight`` property validation."""
    keyword = get_keyword(token)
    if keyword in ('normal', 'bold', 'bolder', 'lighter'):
        return keyword
    if token.type == 'number' and token.int_value is not None:
        if token.int_value in (100, 200, 300, 400, 500, 600, 700, 800, 900):
            return token.int_value


@property()
@single_keyword
def object_fit(keyword):
    # TODO: Figure out what the spec means by "'scale-down' flag".
    #   As of this writing, neither Firefox nor chrome support
    #   anything other than a single keyword as is done here.
    return keyword in ('fill', 'contain', 'cover', 'none', 'scale-down')


@property(unstable=True)
@single_token
def image_resolution(token):
    # TODO: support 'snap' and 'from-image'
    return get_resolution(token)


@property('letter-spacing')
@property('word-spacing')
@single_token
def spacing(token):
    """Validation for ``letter-spacing`` and ``word-spacing``."""
    if get_keyword(token) == 'normal':
        return 'normal'
    length = get_length(token)
    if length:
        return length


@property()
@single_token
def line_height(token):
    """``line-height`` property validation."""
    if get_keyword(token) == 'normal':
        return 'normal'
    if token.type == 'number' and token.value >= 0:
        return Dimension(token.value, None)
    if token.type == 'percentage' and token.value >= 0:
        return Dimension(token.value, '%')
    elif token.type == 'dimension' and token.value >= 0:
        return get_length(token)


@property()
@single_keyword
def list_style_position(keyword):
    """``list-style-position`` property validation."""
    return keyword in ('inside', 'outside')


@property()
@single_keyword
def list_style_type(keyword):
    """``list-style-type`` property validation."""
    return keyword == 'none' or keyword in counters.STYLES


@property('min-width')
@property('min-height')
@single_token
def min_width_height(token):
    """``min-width`` and ``min-height`` properties validation."""
    # See https://www.w3.org/TR/css-flexbox-1/#min-size-auto
    keyword = get_keyword(token)
    if keyword == 'auto':
        return keyword
    else:
        return length_or_precentage([token])


@property('padding-top')
@property('padding-right')
@property('padding-bottom')
@property('padding-left')
@single_token
def length_or_precentage(token):
    """``padding-*`` properties validation."""
    length = get_length(token, negative=False, percentage=True)
    if length:
        return length


@property('max-width')
@property('max-height')
@single_token
def max_width_height(token):
    """Validation for max-width and max-height"""
    length = get_length(token, negative=False, percentage=True)
    if length:
        return length
    if get_keyword(token) == 'none':
        return Dimension(float('inf'), 'px')


@property()
@single_token
def opacity(token):
    """Validation for the ``opacity`` property."""
    if token.type == 'number':
        return min(1, max(0, token.value))


@property()
@single_token
def z_index(token):
    """Validation for the ``z-index`` property."""
    if get_keyword(token) == 'auto':
        return 'auto'
    if token.type == 'number' and token.int_value is not None:
        return token.int_value


@property('orphans')
@property('widows')
@single_token
def orphans_widows(token):
    """Validation for the ``orphans`` and ``widows`` properties."""
    if token.type == 'number' and token.int_value is not None:
        value = token.int_value
        if value >= 1:
            return value


@property(unstable=True)
@single_token
def column_count(token):
    """Validation for the ``column-count`` property."""
    if token.type == 'number' and token.int_value is not None:
        value = token.int_value
        if value >= 1:
            return value
    if get_keyword(token) == 'auto':
        return 'auto'


@property()
@single_keyword
def overflow(keyword):
    """Validation for the ``overflow`` property."""
    return keyword in ('auto', 'visible', 'hidden', 'scroll')


@property()
@single_keyword
def text_overflow(keyword):
    """Validation for the ``text-overflow`` property."""
    return keyword in ('clip', 'ellipsis')


@property()
@single_token
def position(token):
    """``position`` property validation."""
    if token.type == 'function' and token.name == 'running':
        if len(token.arguments) == 1 and token.arguments[0].type == 'ident':
            return ('running()', token.arguments[0].value)
    keyword = get_single_keyword([token])
    if keyword in ('static', 'relative', 'absolute', 'fixed'):
        return keyword


@property()
def quotes(tokens):
    """``quotes`` property validation."""
    if (tokens and len(tokens) % 2 == 0 and
            all(token.type == 'string' for token in tokens)):
        strings = tuple(token.value for token in tokens)
        # Separate open and close quotes.
        # eg.  ('«', '»', '“', '”')  -> (('«', '“'), ('»', '”'))
        return strings[::2], strings[1::2]


@property()
@single_keyword
def table_layout(keyword):
    """Validation for the ``table-layout`` property"""
    if keyword in ('fixed', 'auto'):
        return keyword


@property()
@single_keyword
def text_align(keyword):
    """``text-align`` property validation."""
    return keyword in ('left', 'right', 'center', 'justify')


@property()
def text_decoration_line(tokens):
    """``text-decoration-line`` property validation."""
    keywords = {get_keyword(token) for token in tokens}
    if keywords == {'none'}:
        return 'none'
    allowed_values = {'underline', 'overline', 'line-through', 'blink'}
    if len(tokens) == len(keywords) and keywords.issubset(allowed_values):
        return keywords


@property()
@single_keyword
def text_decoration_style(keyword):
    """``text-decoration-style`` property validation."""
    if keyword in ('solid', 'double', 'dotted', 'dashed', 'wavy'):
        return keyword


@property()
@single_token
def text_indent(token):
    """``text-indent`` property validation."""
    length = get_length(token, percentage=True)
    if length:
        return length


@property()
@single_keyword
def text_transform(keyword):
    """``text-align`` property validation."""
    return keyword in (
        'none', 'uppercase', 'lowercase', 'capitalize', 'full-width')


@property()
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


@property()
@single_keyword
def visibility(keyword):
    """``white-space`` property validation."""
    return keyword in ('visible', 'hidden', 'collapse')


@property()
@single_keyword
def white_space(keyword):
    """``white-space`` property validation."""
    return keyword in ('normal', 'pre', 'nowrap', 'pre-wrap', 'pre-line')


@property()
@single_keyword
def overflow_wrap(keyword):
    """``overflow-wrap`` property validation."""
    return keyword in ('normal', 'break-word')


@property()
@single_token
def flex_basis(token):
    """``flex-basis`` property validation."""
    basis = width_height([token])
    if basis is not None:
        return basis
    if get_keyword(token) == 'content':
        return 'content'


@property()
@single_keyword
def flex_direction(keyword):
    """``flex-direction`` property validation."""
    return keyword in ('row', 'row-reverse', 'column', 'column-reverse')


@property('flex-grow')
@property('flex-shrink')
@single_token
def flex_grow_shrink(token):
    if token.type == 'number':
        return token.value


@property()
@single_token
def order(token):
    if token.type == 'number' and token.int_value is not None:
        return token.int_value


@property()
@single_keyword
def flex_wrap(keyword):
    """``flex-wrap`` property validation."""
    return keyword in ('nowrap', 'wrap', 'wrap-reverse')


@property()
@single_keyword
def justify_content(keyword):
    """``justify-content`` property validation."""
    return keyword in (
        'flex-start', 'flex-end', 'center', 'space-between', 'space-around',
        'space-evenly', 'stretch')


@property()
@single_keyword
def align_items(keyword):
    """``align-items`` property validation."""
    return keyword in (
        'flex-start', 'flex-end', 'center', 'baseline', 'stretch')


@property()
@single_keyword
def align_self(keyword):
    """``align-self`` property validation."""
    return keyword in (
        'auto', 'flex-start', 'flex-end', 'center', 'baseline', 'stretch')


@property()
@single_keyword
def align_content(keyword):
    """``align-content`` property validation."""
    return keyword in (
        'flex-start', 'flex-end', 'center', 'space-between', 'space-around',
        'space-evenly', 'stretch')


@property(unstable=True)
@single_keyword
def image_rendering(keyword):
    """Validation for ``image-rendering``."""
    return keyword in ('auto', 'crisp-edges', 'pixelated')


@property(unstable=True)
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

    keywords = [get_keyword(token) for token in tokens]
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


@property(proprietary=True)
@single_token
def anchor(token):
    """Validation for ``anchor``."""
    if get_keyword(token) == 'none':
        return 'none'
    function = parse_function(token)
    if function:
        name, args = function
        prototype = (name, [a.type for a in args])
        args = [getattr(a, 'value', a) for a in args]
        if prototype == ('attr', ['ident']):
            return ('attr()', args[0])


@property(proprietary=True, wants_base_url=True)
@single_token
def link(token, base_url):
    """Validation for ``link``."""
    if get_keyword(token) == 'none':
        return 'none'
    parsed_url = get_url(token, base_url)
    if parsed_url:
        return parsed_url
    function = parse_function(token)
    if function:
        name, args = function
        prototype = (name, [a.type for a in args])
        args = [getattr(a, 'value', a) for a in args]
        if prototype == ('attr', ['ident']):
            return ('attr()', args[0])


@property()
@single_token
def tab_size(token):
    """Validation for ``tab-size``.

    See https://www.w3.org/TR/css-text-3/#tab-size

    """
    if token.type == 'number' and token.int_value is not None:
        value = token.int_value
        if value >= 0:
            return value
    return get_length(token, negative=False)


@property(unstable=True)
@single_token
def hyphens(token):
    """Validation for ``hyphens``."""
    keyword = get_keyword(token)
    if keyword in ('none', 'manual', 'auto'):
        return keyword


@property(unstable=True)
@single_token
def hyphenate_character(token):
    """Validation for ``hyphenate-character``."""
    keyword = get_keyword(token)
    if keyword == 'auto':
        return '‐'
    elif token.type == 'string':
        return token.value


@property(unstable=True)
@single_token
def hyphenate_limit_zone(token):
    """Validation for ``hyphenate-limit-zone``."""
    return get_length(token, negative=False, percentage=True)


@property(unstable=True)
def hyphenate_limit_chars(tokens):
    """Validation for ``hyphenate-limit-chars``."""
    if len(tokens) == 1:
        token, = tokens
        keyword = get_keyword(token)
        if keyword == 'auto':
            return (5, 2, 2)
        elif token.type == 'number' and token.int_value is not None:
            return (token.int_value, 2, 2)
    elif len(tokens) == 2:
        total, left = tokens
        total_keyword = get_keyword(total)
        left_keyword = get_keyword(left)
        if total.type == 'number' and total.int_value is not None:
            if left.type == 'number' and left.int_value is not None:
                return (total.int_value, left.int_value, left.int_value)
            elif left_keyword == 'auto':
                return (total.value, 2, 2)
        elif total_keyword == 'auto':
            if left.type == 'number' and left.int_value is not None:
                return (5, left.int_value, left.int_value)
            elif left_keyword == 'auto':
                return (5, 2, 2)
    elif len(tokens) == 3:
        total, left, right = tokens
        if (
            (get_keyword(total) == 'auto' or
                (total.type == 'number' and total.int_value is not None)) and
            (get_keyword(left) == 'auto' or
                (left.type == 'number' and left.int_value is not None)) and
            (get_keyword(right) == 'auto' or
                (right.type == 'number' and right.int_value is not None))
        ):
            total = total.int_value if total.type == 'number' else 5
            left = left.int_value if left.type == 'number' else 2
            right = right.int_value if right.type == 'number' else 2
            return (total, left, right)


@property(proprietary=True)
@single_token
def lang(token):
    """Validation for ``lang``."""
    if get_keyword(token) == 'none':
        return 'none'
    function = parse_function(token)
    if function:
        name, args = function
        prototype = (name, [a.type for a in args])
        args = [getattr(a, 'value', a) for a in args]
        if prototype == ('attr', ['ident']):
            return ('attr()', args[0])
    elif token.type == 'string':
        return ('string', token.value)


@property(unstable=True, wants_base_url=True)
def bookmark_label(tokens, base_url):
    """Validation for ``bookmark-label``."""
    parsed_tokens = tuple(
        get_content_list_token(token, base_url) for token in tokens)
    if None not in parsed_tokens:
        return parsed_tokens


@property(unstable=True)
@single_token
def bookmark_level(token):
    """Validation for ``bookmark-level``."""
    if token.type == 'number' and token.int_value is not None:
        value = token.int_value
        if value >= 1:
            return value
    elif get_keyword(token) == 'none':
        return 'none'


@property(unstable=True)
@single_keyword
def bookmark_state(keyword):
    """Validation for ``bookmark-state``."""
    return keyword in ('open', 'closed')


@property(unstable=True, wants_base_url=True)
@comma_separated_list
def string_set(tokens, base_url):
    """Validation for ``string-set``."""
    # Spec asks for strings after custom keywords, but we allow content-lists
    if len(tokens) >= 2:
        var_name = get_custom_ident(tokens[0])
        if var_name is None:
            return
        parsed_tokens = tuple(
            get_content_list_token(token, base_url) for token in tokens[1:])
        if None not in parsed_tokens:
            return (var_name, parsed_tokens)
    elif tokens and get_keyword(tokens[0]) == 'none':
        return 'none', ()


@property()
def transform(tokens):
    """Validation for ``transform``."""
    if get_single_keyword(tokens) == 'none':
        return ()
    else:
        transforms = []
        for token in tokens:
            function = parse_function(token)
            if not function:
                return
            name, args = function

            if len(args) == 1:
                angle = get_angle(args[0])
                length = get_length(args[0], percentage=True)
                if name in ('rotate', 'skewx', 'skewy') and angle:
                    transforms.append((name, angle))
                elif name in ('translatex', 'translate') and length:
                    transforms.append((
                        'translate', (length, computed_values.ZERO_PIXELS)))
                elif name == 'translatey' and length:
                    transforms.append((
                        'translate', (computed_values.ZERO_PIXELS, length)))
                elif name == 'scalex' and args[0].type == 'number':
                    transforms.append(('scale', (args[0].value, 1)))
                elif name == 'scaley' and args[0].type == 'number':
                    transforms.append(('scale', (1, args[0].value)))
                elif name == 'scale' and args[0].type == 'number':
                    transforms.append(('scale', (args[0].value,) * 2))
                else:
                    return
            elif len(args) == 2:
                if name == 'scale' and all(a.type == 'number' for a in args):
                    transforms.append((name, tuple(arg.value for arg in args)))
                else:
                    lengths = tuple(
                        get_length(token, percentage=True) for token in args)
                    if name == 'translate' and all(lengths):
                        transforms.append((name, lengths))
                    else:
                        return
            elif len(args) == 6 and name == 'matrix' and all(
                    a.type == 'number' for a in args):
                transforms.append((name, tuple(arg.value for arg in args)))
            else:
                return
        return tuple(transforms)
