"""
    weasyprint.css.computed_values
    ------------------------------

    Convert *specified* property values (the result of the cascade and
    inhertance) into *computed* values (that are inherited).

"""

from collections import OrderedDict
from urllib.parse import unquote

from tinycss2.color3 import parse_color

from ..logger import LOGGER
from ..text.ffi import ffi, pango, units_to_double
from ..text.line_break import Layout, first_line_metrics, line_size
from ..urls import get_link_attribute
from .properties import (
    INHERITED, INITIAL_NOT_COMPUTED, INITIAL_VALUES, Dimension)
from .utils import (
    ANGLE_TO_RADIANS, LENGTH_UNITS, LENGTHS_TO_PIXELS, check_var_function,
    safe_urljoin)
from .validation.properties import PROPERTIES

ZERO_PIXELS = Dimension(0, 'px')


# Value in pixels of font-size for <absolute-size> keywords: 12pt (16px) for
# medium, and scaling factors given in CSS3 for others:
# http://www.w3.org/TR/css3-fonts/#font-size-prop
FONT_SIZE_KEYWORDS = OrderedDict(
    # medium is 16px, others are a ratio of medium
    (name, INITIAL_VALUES['font_size'] * a / b)
    for name, a, b in (
        ('xx-small', 3, 5),
        ('x-small', 3, 4),
        ('small', 8, 9),
        ('medium', 1, 1),
        ('large', 6, 5),
        ('x-large', 3, 2),
        ('xx-large', 2, 1),
    )
)

# These are unspecified, other than 'thin' <='medium' <= 'thick'.
# Values are in pixels.
BORDER_WIDTH_KEYWORDS = {
    'thin': 1,
    'medium': 3,
    'thick': 5,
}
assert INITIAL_VALUES['border_top_width'] == BORDER_WIDTH_KEYWORDS['medium']

# http://www.w3.org/TR/CSS21/fonts.html#propdef-font-weight
FONT_WEIGHT_RELATIVE = dict(
    bolder={
        100: 400,
        200: 400,
        300: 400,
        400: 700,
        500: 700,
        600: 900,
        700: 900,
        800: 900,
        900: 900,
    },
    lighter={
        100: 100,
        200: 100,
        300: 100,
        400: 100,
        500: 100,
        600: 400,
        700: 400,
        800: 700,
        900: 700,
    },
)

# http://www.w3.org/TR/css3-page/#size
# name=(width in pixels, height in pixels)
PAGE_SIZES = {
    'a10': (Dimension(26, 'mm'), Dimension(37, 'mm'),),
    'a9': (Dimension(37, 'mm'), Dimension(52, 'mm')),
    'a8': (Dimension(52, 'mm'), Dimension(74, 'mm')),
    'a7': (Dimension(74, 'mm'), Dimension(105, 'mm')),
    'a6': (Dimension(105, 'mm'), Dimension(148, 'mm')),
    'a5': (Dimension(148, 'mm'), Dimension(210, 'mm')),
    'a4': (Dimension(210, 'mm'), Dimension(297, 'mm')),
    'a3': (Dimension(297, 'mm'), Dimension(420, 'mm')),
    'a2': (Dimension(420, 'mm'), Dimension(594, 'mm')),
    'a1': (Dimension(594, 'mm'), Dimension(841, 'mm')),
    'a0': (Dimension(841, 'mm'), Dimension(1189, 'mm')),
    'b10': (Dimension(31, 'mm'), Dimension(44, 'mm')),
    'b9': (Dimension(44, 'mm'), Dimension(62, 'mm')),
    'b8': (Dimension(62, 'mm'), Dimension(88, 'mm')),
    'b7': (Dimension(88, 'mm'), Dimension(125, 'mm')),
    'b6': (Dimension(125, 'mm'), Dimension(176, 'mm')),
    'b5': (Dimension(176, 'mm'), Dimension(250, 'mm')),
    'b4': (Dimension(250, 'mm'), Dimension(353, 'mm')),
    'b3': (Dimension(353, 'mm'), Dimension(500, 'mm')),
    'b2': (Dimension(500, 'mm'), Dimension(707, 'mm')),
    'b1': (Dimension(707, 'mm'), Dimension(1000, 'mm')),
    'b0': (Dimension(1000, 'mm'), Dimension(1414, 'mm')),
    'c10': (Dimension(28, 'mm'), Dimension(40, 'mm')),
    'c9': (Dimension(40, 'mm'), Dimension(57, 'mm')),
    'c8': (Dimension(57, 'mm'), Dimension(81, 'mm')),
    'c7': (Dimension(81, 'mm'), Dimension(114, 'mm')),
    'c6': (Dimension(114, 'mm'), Dimension(162, 'mm')),
    'c5': (Dimension(162, 'mm'), Dimension(229, 'mm')),
    'c4': (Dimension(229, 'mm'), Dimension(324, 'mm')),
    'c3': (Dimension(324, 'mm'), Dimension(458, 'mm')),
    'c2': (Dimension(458, 'mm'), Dimension(648, 'mm')),
    'c1': (Dimension(648, 'mm'), Dimension(917, 'mm')),
    'c0': (Dimension(917, 'mm'), Dimension(1297, 'mm')),
    'jis-b10': (Dimension(32, 'mm'), Dimension(45, 'mm')),
    'jis-b9': (Dimension(45, 'mm'), Dimension(64, 'mm')),
    'jis-b8': (Dimension(64, 'mm'), Dimension(91, 'mm')),
    'jis-b7': (Dimension(91, 'mm'), Dimension(128, 'mm')),
    'jis-b6': (Dimension(128, 'mm'), Dimension(182, 'mm')),
    'jis-b5': (Dimension(182, 'mm'), Dimension(257, 'mm')),
    'jis-b4': (Dimension(257, 'mm'), Dimension(364, 'mm')),
    'jis-b3': (Dimension(364, 'mm'), Dimension(515, 'mm')),
    'jis-b2': (Dimension(515, 'mm'), Dimension(728, 'mm')),
    'jis-b1': (Dimension(728, 'mm'), Dimension(1030, 'mm')),
    'jis-b0': (Dimension(1030, 'mm'), Dimension(1456, 'mm')),
    'letter': (Dimension(8.5, 'in'), Dimension(11, 'in')),
    'legal': (Dimension(8.5, 'in'), Dimension(14, 'in')),
    'ledger': (Dimension(11, 'in'), Dimension(17, 'in')),
}
# In "portrait" orientation.
for w, h in PAGE_SIZES.values():
    assert w.value < h.value

INITIAL_PAGE_SIZE = PAGE_SIZES['a4']
INITIAL_VALUES['size'] = tuple(
    d.value * LENGTHS_TO_PIXELS[d.unit] for d in INITIAL_PAGE_SIZE)


def _computing_order():
    """Some computed values are required by others, so order matters."""
    first = [
        'font_stretch', 'font_weight', 'font_family', 'font_variant',
        'font_style', 'font_size', 'line_height', 'marks']
    order = sorted(INITIAL_VALUES)
    for name in first:
        order.remove(name)
    return tuple(first + order)


COMPUTING_ORDER = _computing_order()

# Maps property names to functions returning the computed values
COMPUTER_FUNCTIONS = {}


def _resolve_var(computed, variable_name, default):
    known_variable_names = [variable_name]

    computed_value = computed.get(variable_name)
    if computed_value and len(computed_value) == 1:
        value = computed_value[0]
        if value.type == 'ident' and value.value == 'initial':
            return default

    computed_value = computed.get(variable_name, default)
    while (computed_value and
            isinstance(computed_value, tuple)
            and len(computed_value) == 1):
        var_function = check_var_function(computed_value[0])
        if var_function:
            new_variable_name, new_default = var_function[1]
            if new_variable_name in known_variable_names:
                computed_value = default
                break
            known_variable_names.append(new_variable_name)
            computed_value = computed.get(new_variable_name, new_default)
            default = new_default
        else:
            break
    return computed_value


def register_computer(name):
    """Decorator registering a property ``name`` for a function."""
    name = name.replace('-', '_')

    def decorator(function):
        """Register the property ``name`` for ``function``."""
        COMPUTER_FUNCTIONS[name] = function
        return function
    return decorator


def compute_variable(value, name, computed, base_url, parent_style):
    already_computed_value = False

    if value and isinstance(value, tuple) and value[0] == 'var()':
        variable_name, default = value[1]
        computed_value = _resolve_var(computed, variable_name, default)
        if computed_value is None:
            new_value = None
        else:
            prop = PROPERTIES[name.replace('_', '-')]
            if prop.wants_base_url:
                new_value = prop(computed_value, base_url)
            else:
                new_value = prop(computed_value)

        # See https://drafts.csswg.org/css-variables/#invalid-variables
        if new_value is None:
            try:
                computed_value = ''.join(
                    token.serialize() for token in computed_value)
            except BaseException:
                pass
            LOGGER.warning(
                'Unsupported computed value "%s" set in variable %r '
                'for property %r.', computed_value,
                variable_name.replace('_', '-'), name.replace('_', '-'))
            if name in INHERITED and parent_style:
                already_computed_value = True
                value = parent_style[name]
            else:
                already_computed_value = name not in INITIAL_NOT_COMPUTED
                value = INITIAL_VALUES[name]
        elif isinstance(new_value, list):
            value, = new_value
        else:
            value = new_value
    return value, already_computed_value


def compute(element, pseudo_type, specified, computed, parent_style,
            root_style, base_url, target_collector):
    """Create a dict of computed values.

    :param element: The HTML element these style apply to
    :param pseudo_type: The type of pseudo-element, eg 'before', None
    :param specified: A dict of specified values. Should contain
                      values for all properties.
    :param computed: A dict of already known computed values.
                     Only contains some properties (or none).
    :param parent_style: A dict of computed values of the parent
                         element (should contain values for all properties),
                         or ``None`` if ``element`` is the root element.
    :param base_url: The base URL used to resolve relative URLs.
    :param target_collector: A target collector used to get computed targets.

    """

    computer = {
        'is_root_element': parent_style is None,
        'element': element,
        'pseudo_type': pseudo_type,
        'specified': specified,
        'computed': computed,
        'parent_style': parent_style or INITIAL_VALUES,
        'root_style': root_style,
        'base_url': base_url,
        'target_collector': target_collector,
    }

    getter = COMPUTER_FUNCTIONS.get

    for name in COMPUTING_ORDER:
        if name in computed:
            # Already computed
            continue

        value = specified[name]
        function = getter(name)
        already_computed_value = False

        if value:
            converted_to_list = False

            if not isinstance(value, list):
                converted_to_list = True
                value = [value]

            for i, v in enumerate(value):
                value[i], already_computed_value = compute_variable(
                    v, name, computed, base_url, parent_style)

            if converted_to_list:
                value, = value

        if function is not None and not already_computed_value:
            value = function(computer, name, value)
        # else: same as specified

        computed[name] = value

    computed['_weasy_specified_display'] = specified['display']
    return computed


@register_computer('background-image')
def background_image(computer, name, values):
    """Compute lenghts in gradient background-image."""
    for type_, value in values:
        if type_ in ('linear-gradient', 'radial-gradient'):
            value.stop_positions = tuple(
                length(computer, name, pos) if pos is not None else None
                for pos in value.stop_positions)
        if type_ == 'radial-gradient':
            value.center, = compute_position(
                computer, name, (value.center,))
            if value.size_type == 'explicit':
                value.size = length_or_percentage_tuple(
                    computer, name, value.size)
    return values


@register_computer('background-position')
@register_computer('object-position')
def compute_position(computer, name, values):
    """Compute lengths in background-position."""
    return tuple(
        (origin_x, length(computer, name, pos_x),
         origin_y, length(computer, name, pos_y))
        for origin_x, pos_x, origin_y, pos_y in values)


@register_computer('transform-origin')
def length_or_percentage_tuple(computer, name, values):
    """Compute the lists of lengths that can be percentages."""
    return tuple(length(computer, name, value) for value in values)


@register_computer('border-spacing')
@register_computer('size')
@register_computer('clip')
def length_tuple(computer, name, values):
    """Compute the properties with a list of lengths."""
    return tuple(length(computer, name, value, pixels_only=True)
                 for value in values)


@register_computer('break-after')
@register_computer('break-before')
def break_before_after(computer, name, value):
    """Compute the ``break-before`` and ``break-after`` properties."""
    # 'always' is defined as an alias to 'page' in multi-column
    # https://www.w3.org/TR/css3-multicol/#column-breaks
    if value == 'always':
        return 'page'
    else:
        return value


@register_computer('top')
@register_computer('right')
@register_computer('left')
@register_computer('bottom')
@register_computer('margin-top')
@register_computer('margin-right')
@register_computer('margin-bottom')
@register_computer('margin-left')
@register_computer('height')
@register_computer('width')
@register_computer('min-width')
@register_computer('min-height')
@register_computer('max-width')
@register_computer('max-height')
@register_computer('padding-top')
@register_computer('padding-right')
@register_computer('padding-bottom')
@register_computer('padding-left')
@register_computer('text-indent')
@register_computer('hyphenate-limit-zone')
@register_computer('flex-basis')
def length(computer, name, value, font_size=None, pixels_only=False):
    """Compute a length ``value``."""
    if value in ('auto', 'content'):
        return value
    if value.value == 0:
        return 0 if pixels_only else ZERO_PIXELS

    unit = value.unit
    if unit == 'px':
        return value.value if pixels_only else value
    elif unit in LENGTHS_TO_PIXELS:
        # Convert absolute lengths to pixels
        result = value.value * LENGTHS_TO_PIXELS[unit]
    elif unit in ('em', 'ex', 'ch', 'rem'):
        if font_size is None:
            font_size = computer['computed']['font_size']
        if unit == 'ex':
            # TODO: cache
            result = value.value * font_size * ex_ratio(computer['computed'])
        elif unit == 'ch':
            # TODO: cache
            # TODO: use context to use @font-face fonts
            layout = Layout(
                context=None, font_size=font_size,
                style=computer['computed'])
            layout.set_text('0')
            line, _ = layout.get_first_line()
            logical_width, _ = line_size(line, computer['computed'])
            result = value.value * logical_width
        elif unit == 'em':
            result = value.value * font_size
        elif unit == 'rem':
            result = value.value * computer['root_style']['font_size']
    else:
        # A percentage or 'auto': no conversion needed.
        return value

    return result if pixels_only else Dimension(result, 'px')


@register_computer('bleed-left')
@register_computer('bleed-right')
@register_computer('bleed-top')
@register_computer('bleed-bottom')
def bleed(computer, name, value):
    if value == 'auto':
        if 'crop' in computer['computed']['marks']:
            return Dimension(8, 'px')  # 6pt
        else:
            return Dimension(0, 'px')
    else:
        return length(computer, name, value)


@register_computer('letter-spacing')
def pixel_length(computer, name, value):
    if value == 'normal':
        return value
    else:
        return length(computer, name, value, pixels_only=True)


@register_computer('background-size')
def background_size(computer, name, values):
    """Compute the ``background-size`` properties."""
    return tuple(
        value if value in ('contain', 'cover') else
        length_or_percentage_tuple(computer, name, value)
        for value in values)


@register_computer('border-top-width')
@register_computer('border-right-width')
@register_computer('border-left-width')
@register_computer('border-bottom-width')
@register_computer('column-rule-width')
@register_computer('outline-width')
def border_width(computer, name, value):
    """Compute the ``border-*-width`` properties."""
    style = computer['computed'][name.replace('width', 'style')]
    if style in ('none', 'hidden'):
        return 0

    if value in BORDER_WIDTH_KEYWORDS:
        return BORDER_WIDTH_KEYWORDS[value]

    if isinstance(value, int):
        # The initial value can get here, but length() would fail as
        # it does not have a 'unit' attribute.
        return value

    return length(computer, name, value, pixels_only=True)


@register_computer('column-width')
def column_width(computer, name, value):
    """Compute the ``column-width`` property."""
    return length(computer, name, value, pixels_only=True)


@register_computer('border-top-left-radius')
@register_computer('border-top-right-radius')
@register_computer('border-bottom-left-radius')
@register_computer('border-bottom-right-radius')
def border_radius(computer, name, values):
    """Compute the ``border-*-radius`` properties."""
    return tuple(length(computer, name, value) for value in values)


@register_computer('column-gap')
def column_gap(computer, name, value):
    """Compute the ``column-gap`` property."""
    if value == 'normal':
        value = Dimension(1, 'em')
    return length(computer, name, value, pixels_only=True)


def compute_attr_function(computer, values):
    # TODO: use real token parsing instead of casting with Python types
    func_name, value = values
    assert func_name == 'attr()'
    attr_name, type_or_unit, fallback = value
    # computer['element'] sometimes is None
    # computer['element'] sometimes is a 'PageType' object without .get()
    # so wrapt the .get() into try and return None instead of crashing
    try:
        attr_value = computer['element'].get(attr_name, fallback)
        if type_or_unit == 'string':
            pass  # Keep the string
        elif type_or_unit == 'url':
            if attr_value.startswith('#'):
                attr_value = ('internal', unquote(attr_value[1:]))
            else:
                attr_value = (
                    'external', safe_urljoin(computer['base_url'], attr_value))
        elif type_or_unit == 'color':
            attr_value = parse_color(attr_value.strip())
        elif type_or_unit == 'integer':
            attr_value = int(attr_value.strip())
        elif type_or_unit == 'number':
            attr_value = float(attr_value.strip())
        elif type_or_unit == '%':
            attr_value = Dimension(float(attr_value.strip()), '%')
            type_or_unit = 'length'
        elif type_or_unit in LENGTH_UNITS:
            attr_value = Dimension(float(attr_value.strip()), type_or_unit)
            type_or_unit = 'length'
        elif type_or_unit in ANGLE_TO_RADIANS:
            attr_value = Dimension(float(attr_value.strip()), type_or_unit)
            type_or_unit = 'angle'
    except Exception:
        return
    return (type_or_unit, attr_value)


def _content_list(computer, values):
    computed_values = []
    for value in values:
        if value[0] in ('string', 'content', 'url', 'quote', 'leader()'):
            computed_value = value
        elif value[0] == 'attr()':
            assert value[1][1] == 'string'
            computed_value = compute_attr_function(computer, value)
        elif value[0] in (
                'counter()', 'counters()', 'content()', 'element()',
                'string()',
        ):
            # Other values need layout context, their computed value cannot be
            # better than their specified value yet.
            # See build.compute_content_list.
            computed_value = value
        elif value[0] in (
                'target-counter()', 'target-counters()', 'target-text()'):
            anchor_token = value[1][0]
            if anchor_token[0] == 'attr()':
                attr = compute_attr_function(computer, anchor_token)
                if attr is None:
                    computed_value = None
                else:
                    computed_value = (value[0], (
                        (attr,) + value[1][1:]))
            else:
                computed_value = value
        if computed_value is None:
            LOGGER.warning('Unable to compute %r value for content: %r' % (
                computer['element'], ', '.join(str(item) for item in value)))
        else:
            computed_values.append(computed_value)

    return tuple(computed_values)


@register_computer('bookmark-label')
def bookmark_label(computer, name, values):
    """Compute the ``bookmark-label`` property."""
    return _content_list(computer, values)


@register_computer('string-set')
def string_set(computer, name, values):
    """Compute the ``string-set`` property."""
    # Spec asks for strings after custom keywords, but we allow content-lists
    return tuple(
        (string_set[0], _content_list(computer, string_set[1]))
        for string_set in values)


@register_computer('content')
def content(computer, name, values):
    """Compute the ``content`` property."""
    if len(values) == 1:
        value, = values
        if value == 'normal':
            return 'inhibit' if computer['pseudo_type'] else 'contents'
        elif value == 'none':
            return 'inhibit'
    return _content_list(computer, values)


@register_computer('display')
def display(computer, name, value):
    """Compute the ``display`` property.

    See http://www.w3.org/TR/CSS21/visuren.html#dis-pos-flo

    """
    float_ = computer['specified']['float']
    position = computer['specified']['position']
    if position in ('absolute', 'fixed') or float_ != 'none' or \
            computer['is_root_element']:
        if value == 'inline-table':
            return'table'
        elif value in ('inline', 'table-row-group', 'table-column',
                       'table-column-group', 'table-header-group',
                       'table-footer-group', 'table-row', 'table-cell',
                       'table-caption', 'inline-block'):
            return 'block'
    return value


@register_computer('float')
def compute_float(computer, name, value):
    """Compute the ``float`` property.

    See http://www.w3.org/TR/CSS21/visuren.html#dis-pos-flo

    """
    if computer['specified']['position'] in ('absolute', 'fixed'):
        return 'none'
    else:
        return value


@register_computer('font-size')
def font_size(computer, name, value):
    """Compute the ``font-size`` property."""
    if value in FONT_SIZE_KEYWORDS:
        return FONT_SIZE_KEYWORDS[value]

    keyword_values = list(FONT_SIZE_KEYWORDS.values())
    parent_font_size = computer['parent_style']['font_size']

    if value == 'larger':
        for i, keyword_value in enumerate(keyword_values):
            if keyword_value > parent_font_size:
                return keyword_values[i]
        else:
            return parent_font_size * 1.2
    elif value == 'smaller':
        for i, keyword_value in enumerate(keyword_values[::-1]):
            if keyword_value < parent_font_size:
                return keyword_values[-i - 1]
        else:
            return parent_font_size * 0.8
    elif value.unit == '%':
        return value.value * parent_font_size / 100.
    else:
        return length(
            computer, name, value, pixels_only=True,
            font_size=parent_font_size)


@register_computer('font-weight')
def font_weight(computer, name, value):
    """Compute the ``font-weight`` property."""
    if value == 'normal':
        return 400
    elif value == 'bold':
        return 700
    elif value in ('bolder', 'lighter'):
        parent_value = computer['parent_style']['font_weight']
        return FONT_WEIGHT_RELATIVE[value][parent_value]
    else:
        return value


@register_computer('line-height')
def line_height(computer, name, value):
    """Compute the ``line-height`` property."""
    if value == 'normal':
        return value
    elif not value.unit:
        return ('NUMBER', value.value)
    elif value.unit == '%':
        factor = value.value / 100.
        font_size_value = computer['computed']['font_size']
        pixels = factor * font_size_value
    else:
        pixels = length(computer, name, value, pixels_only=True)
    return ('PIXELS', pixels)


@register_computer('anchor')
def anchor(computer, name, values):
    """Compute the ``anchor`` property."""
    if values != 'none':
        _, key = values
        anchor_name = computer['element'].get(key) or None
        computer['target_collector'].collect_anchor(anchor_name)
        return anchor_name


@register_computer('link')
def link(computer, name, values):
    """Compute the ``link`` property."""
    if values == 'none':
        return None
    else:
        type_, value = values
        if type_ == 'attr()':
            return get_link_attribute(
                computer['element'], value, computer['base_url'])
        else:
            return values


@register_computer('lang')
def lang(computer, name, values):
    """Compute the ``lang`` property."""
    if values == 'none':
        return None
    else:
        type_, key = values
        if type_ == 'attr()':
            return computer['element'].get(key) or None
        elif type_ == 'string':
            return key


@register_computer('tab-size')
def tab_size(computer, name, value):
    """Compute the ``tab-size`` property."""
    if isinstance(value, int):
        return value
    else:
        return length(computer, name, value)


@register_computer('transform')
def transform(computer, name, value):
    """Compute the ``transform`` property."""
    result = []
    for function, args in value:
        if function == 'translate':
            args = length_or_percentage_tuple(computer, name, args)
        result.append((function, args))
    return tuple(result)


@register_computer('vertical-align')
def vertical_align(computer, name, value):
    """Compute the ``vertical-align`` property."""
    # Use +/- half an em for super and sub, same as Pango.
    # (See the SUPERSUB_RISE constant in pango-markup.c)
    if value in ('baseline', 'middle', 'text-top', 'text-bottom',
                 'top', 'bottom'):
        return value
    elif value == 'super':
        return computer['computed']['font_size'] * 0.5
    elif value == 'sub':
        return computer['computed']['font_size'] * -0.5
    elif value.unit == '%':
        height, _ = strut_layout(computer['computed'])
        return height * value.value / 100.
    else:
        return length(computer, name, value, pixels_only=True)


@register_computer('word-spacing')
def word_spacing(computer, name, value):
    """Compute the ``word-spacing`` property."""
    if value == 'normal':
        return 0
    else:
        return length(computer, name, value, pixels_only=True)


def strut_layout(style, context=None):
    """Return a tuple of the used value of ``line-height`` and the baseline.

    The baseline is given from the top edge of line height.

    """
    # TODO: always get the real value for `context`? (if we really care…)

    if style['font_size'] == 0:
        return 0, 0

    if context:
        key = (
            style['font_size'], style['font_language_override'], style['lang'],
            tuple(style['font_family']), style['font_style'],
            style['font_stretch'], style['font_weight'], style['line_height'])
        if key in context.strut_layouts:
            return context.strut_layouts[key]

    layout = Layout(context, style['font_size'], style)
    layout.set_text(' ')
    line, _ = layout.get_first_line()
    _, _, _, _, text_height, baseline = first_line_metrics(
        line, '', layout, resume_at=None, space_collapse=False, style=style)
    if style['line_height'] == 'normal':
        result = text_height, baseline
        if context:
            context.strut_layouts[key] = result
        return result
    type_, line_height = style['line_height']
    if type_ == 'NUMBER':
        line_height *= style['font_size']
    result = line_height, baseline + (line_height - text_height) / 2
    if context:
        context.strut_layouts[key] = result
    return result


def ex_ratio(style):
    """Return the ratio 1ex/font_size, according to given style."""
    font_size = 1000  # big value
    # TODO: use context to use @font-face fonts
    layout = Layout(context=None, font_size=font_size, style=style)
    layout.set_text('x')
    line, _ = layout.get_first_line()

    ink_extents = ffi.new('PangoRectangle *')
    pango.pango_layout_line_get_extents(line, ink_extents, ffi.NULL)
    height_above_baseline = units_to_double(ink_extents.y)
    ffi.release(ink_extents)

    # Zero means some kind of failure, fallback is 0.5.
    # We round to try keeping exact values that were altered by Pango.
    return round(-height_above_baseline / font_size, 5) or 0.5
