"""Convert specified property values into computed values."""

from math import pi
from urllib.parse import unquote

from tinycss2.color3 import parse_color

from ..logger import LOGGER
from ..text.ffi import ffi, pango, units_to_double
from ..text.line_break import Layout, first_line_metrics
from ..urls import get_link_attribute
from .properties import INITIAL_VALUES, ZERO_PIXELS, Dimension
from .utils import ANGLE_TO_RADIANS, LENGTH_UNITS, LENGTHS_TO_PIXELS, safe_urljoin

# Value in pixels of font-size for <absolute-size> keywords: 12pt (16px) for
# medium, and scaling factors given in CSS3 for others:
# https://www.w3.org/TR/css-fonts-3/#font-size-prop
FONT_SIZE_KEYWORDS = {
    # medium is 16px, others are a ratio of medium
    name: INITIAL_VALUES['font_size'] * factor
    for name, factor in (
        ('xx-small', 3 / 5),
        ('x-small', 3 / 4),
        ('small', 8 / 9),
        ('medium', 1),
        ('large', 6 / 5),
        ('x-large', 3 / 2),
        ('xx-large', 2),
    )
}

# These are unspecified, other than 'thin' <= 'medium' <= 'thick'.
# Values are in pixels.
BORDER_WIDTH_KEYWORDS = {
    'thin': 1,
    'medium': 3,
    'thick': 5,
}
assert INITIAL_VALUES['border_top_width'] == BORDER_WIDTH_KEYWORDS['medium']

# https://www.w3.org/TR/CSS21/fonts.html#propdef-font-weight
FONT_WEIGHT_RELATIVE = {
    'bolder': {
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
    'lighter': {
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
}

# https://www.w3.org/TR/css-page-3/#size
PAGE_SIZES = {
    page_size: (Dimension(width, unit), Dimension(height, unit))
    for page_size, width, height, unit in (
        ('a10', 26, 37, 'mm'),
        ('a9', 37, 52, 'mm'),
        ('a8', 52, 74, 'mm'),
        ('a7', 74, 105, 'mm'),
        ('a6', 105, 148, 'mm'),
        ('a5', 148, 210, 'mm'),
        ('a4', 210, 297, 'mm'),
        ('a3', 297, 420, 'mm'),
        ('a2', 420, 594, 'mm'),
        ('a1', 594, 841, 'mm'),
        ('a0', 841, 1189, 'mm'),
        ('b10', 31, 44, 'mm'),
        ('b9', 44, 62, 'mm'),
        ('b8', 62, 88, 'mm'),
        ('b7', 88, 125, 'mm'),
        ('b6', 125, 176, 'mm'),
        ('b5', 176, 250, 'mm'),
        ('b4', 250, 353, 'mm'),
        ('b3', 353, 500, 'mm'),
        ('b2', 500, 707, 'mm'),
        ('b1', 707, 1000, 'mm'),
        ('b0', 1000, 1414, 'mm'),
        ('c10', 28, 40, 'mm'),
        ('c9', 40, 57, 'mm'),
        ('c8', 57, 81, 'mm'),
        ('c7', 81, 114, 'mm'),
        ('c6', 114, 162, 'mm'),
        ('c5', 162, 229, 'mm'),
        ('c4', 229, 324, 'mm'),
        ('c3', 324, 458, 'mm'),
        ('c2', 458, 648, 'mm'),
        ('c1', 648, 917, 'mm'),
        ('c0', 917, 1297, 'mm'),
        ('jis-b10', 32, 45, 'mm'),
        ('jis-b9', 45, 64, 'mm'),
        ('jis-b8', 64, 91, 'mm'),
        ('jis-b7', 91, 128, 'mm'),
        ('jis-b6', 128, 182, 'mm'),
        ('jis-b5', 182, 257, 'mm'),
        ('jis-b4', 257, 364, 'mm'),
        ('jis-b3', 364, 515, 'mm'),
        ('jis-b2', 515, 728, 'mm'),
        ('jis-b1', 728, 1030, 'mm'),
        ('jis-b0', 1030, 1456, 'mm'),
        ('letter', 8.5, 11, 'in'),
        ('legal', 8.5, 14, 'in'),
        ('ledger', 11, 17, 'in'),
    )
}
# In "portrait" orientation.
assert all(width.value < height.value for width, height in PAGE_SIZES.values())

INITIAL_PAGE_SIZE = PAGE_SIZES['a4']
INITIAL_VALUES['size'] = tuple(
    size.value * LENGTHS_TO_PIXELS[size.unit] for size in INITIAL_PAGE_SIZE)


# Maps property names to functions returning the computed values
COMPUTER_FUNCTIONS = {}


def _font_style_cache_key(style, include_size=False):
    key = str((
        style['font_family'],
        style['font_style'],
        style['font_stretch'],
        style['font_weight'],
        style['font_variant_ligatures'],
        style['font_variant_position'],
        style['font_variant_caps'],
        style['font_variant_numeric'],
        style['font_variant_alternates'],
        style['font_variant_east_asian'],
        style['font_feature_settings'],
        style['font_variation_settings'],
        style['font_language_override'],
        style['lang'],
    ))
    if include_size:
        key += str(style['font_size']) + str(style['line_height'])
    return key


def register_computer(name):
    """Decorator registering a property ``name`` for a function."""
    name = name.replace('-', '_')

    def decorator(function):
        """Register the property ``name`` for ``function``."""
        COMPUTER_FUNCTIONS[name] = function
        return function
    return decorator


def compute_attr(style, values):
    # TODO: use real token parsing instead of casting with Python types
    func_name, value = values
    assert func_name == 'attr()'
    attr_name, type_or_unit, fallback = value
    try:
        attr_value = style.element.get(attr_name, fallback)
        if type_or_unit == 'string':
            pass  # Keep the string
        elif type_or_unit == 'url':
            if attr_value.startswith('#'):
                attr_value = ('internal', unquote(attr_value[1:]))
            else:
                attr_value = (
                    'external', safe_urljoin(style.base_url, attr_value))
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


@register_computer('background-image')
def background_image(style, name, values):
    """Compute lenghts in gradient background-image."""
    for type_, value in values:
        if type_ in ('linear-gradient', 'radial-gradient'):
            value.stop_positions = tuple(
                length(style, name, pos) if pos is not None else None
                for pos in value.stop_positions)
        if type_ == 'radial-gradient':
            value.center, = compute_position(
                style, name, (value.center,))
            if value.size_type == 'explicit':
                value.size = length_or_percentage_tuple(
                    style, name, value.size)
    return values


@register_computer('background-position')
@register_computer('object-position')
def compute_position(style, name, values):
    """Compute lengths in background-position."""
    return tuple(
        (origin_x, length(style, name, pos_x),
         origin_y, length(style, name, pos_y))
        for origin_x, pos_x, origin_y, pos_y in values)


@register_computer('transform-origin')
def length_or_percentage_tuple(style, name, values):
    """Compute the lists of lengths that can be percentages."""
    return tuple(length(style, name, value) for value in values)


@register_computer('border-spacing')
@register_computer('size')
@register_computer('clip')
def length_tuple(style, name, values):
    """Compute the properties with a list of lengths."""
    return tuple(
        length(style, name, value, pixels_only=True) for value in values)


@register_computer('break-after')
@register_computer('break-before')
def break_before_after(style, name, value):
    """Compute the ``break-before`` and ``break-after`` properties."""
    return 'page' if value == 'always' else value


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
def length(style, name, value, font_size=None, pixels_only=False):
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
            font_size = style['font_size']
        if unit == 'ex':
            # TODO: use context to use @font-face fonts
            ratio = character_ratio(style, 'x')
            result = value.value * font_size * ratio
        elif unit == 'ch':
            ratio = character_ratio(style, '0')
            result = value.value * font_size * ratio
        elif unit == 'em':
            result = value.value * font_size
        elif unit == 'rem':
            result = value.value * style.root_style['font_size']
    else:
        # A percentage or 'auto': no conversion needed.
        return value

    return result if pixels_only else Dimension(result, 'px')


@register_computer('bleed-left')
@register_computer('bleed-right')
@register_computer('bleed-top')
@register_computer('bleed-bottom')
def bleed(style, name, value):
    if value == 'auto':
        return Dimension(8 if 'crop' in style['marks'] else 0, 'px')
    else:
        return length(style, name, value)


@register_computer('letter-spacing')
def pixel_length(style, name, value):
    if value == 'normal':
        return value
    else:
        return length(style, name, value, pixels_only=True)


@register_computer('background-size')
def background_size(style, name, values):
    """Compute the ``background-size`` properties."""
    return tuple(
        value if value in ('contain', 'cover') else
        length_or_percentage_tuple(style, name, value)
        for value in values)


@register_computer('image-orientation')
def image_orientation(style, name, values):
    """Compute the ``image-orientation`` properties."""
    if values in ('none', 'from-image'):
        return values
    angle, flip = values
    return (int(round(angle / pi * 2)) % 4 * 90, flip)


@register_computer('border-top-width')
@register_computer('border-right-width')
@register_computer('border-left-width')
@register_computer('border-bottom-width')
@register_computer('column-rule-width')
@register_computer('outline-width')
def border_width(style, name, value):
    """Compute the ``border-*-width`` properties."""
    border_style = style[name.replace('width', 'style')]
    if border_style in ('none', 'hidden'):
        return 0

    if value in BORDER_WIDTH_KEYWORDS:
        return BORDER_WIDTH_KEYWORDS[value]

    if isinstance(value, int):
        # The initial value can get here, but length() would fail as
        # it does not have a 'unit' attribute.
        return value

    return length(style, name, value, pixels_only=True)


@register_computer('border-image-slice')
def border_image_slice(style, name, values):
    """Compute the ``border-image-slice`` property."""
    computed_values = []
    fill = None
    for value in values:
        if value == 'fill':
            fill = value
        else:
            number, unit = value
            if unit is None:
                computed_values.append(number)
            else:
                computed_values.append(Dimension(number, '%'))
    if len(computed_values) == 1:
        computed_values *= 4
    elif len(computed_values) == 2:
        computed_values *= 2
    elif len(computed_values) == 3:
        computed_values.append(computed_values[1])
    return (*computed_values, fill)


@register_computer('border-image-width')
def border_image_width(style, name, values):
    """Compute the ``border-image-width`` property."""
    computed_values = []
    for value in values:
        if value == 'auto':
            computed_values.append(value)
        else:
            number, unit = value
            computed_values.append(number if unit is None else value)
    if len(computed_values) == 1:
        computed_values *= 4
    elif len(computed_values) == 2:
        computed_values *= 2
    elif len(computed_values) == 3:
        computed_values.append(computed_values[1])
    return tuple(computed_values)


@register_computer('border-image-outset')
def border_image_outset(style, name, values):
    """Compute the ``border-image-outset`` property."""
    computed_values = [
        value if isinstance(value, (int, float)) else length(style, name, value)
        for value in values]
    if len(computed_values) == 1:
        computed_values *= 4
    elif len(computed_values) == 2:
        computed_values *= 2
    elif len(computed_values) == 3:
        computed_values.append(computed_values[1])
    return tuple(computed_values)


@register_computer('border-image-repeat')
def border_image_repeat(style, name, values):
    """Compute the ``border-image-repeat`` property."""
    return (values * 2) if len(values) == 1 else values


@register_computer('column-width')
def column_width(style, name, value):
    """Compute the ``column-width`` property."""
    return length(style, name, value, pixels_only=True)


@register_computer('border-top-left-radius')
@register_computer('border-top-right-radius')
@register_computer('border-bottom-left-radius')
@register_computer('border-bottom-right-radius')
def border_radius(style, name, values):
    """Compute the ``border-*-radius`` properties."""
    return tuple(length(style, name, value) for value in values)


@register_computer('column-gap')
@register_computer('row-gap')
def gap(style, name, value):
    """Compute the ``*-gap`` properties."""
    if value == 'normal':
        return value
    return length(style, name, value, pixels_only=True)


def _content_list(style, values):
    computed_values = []
    for value in values:
        if value[0] in ('string', 'content', 'url', 'quote', 'leader()'):
            computed_value = value
        elif value[0] == 'attr()':
            assert value[1][1] == 'string'
            computed_value = compute_attr(style, value)
        elif value[0] in (
                'counter()', 'counters()', 'content()', 'element()',
                'string()'):
            # Other values need layout context, their computed value cannot be
            # better than their specified value yet.
            # See build.compute_content_list.
            computed_value = value
        elif value[0] in (
                'target-counter()', 'target-counters()', 'target-text()'):
            anchor_token = value[1][0]
            if anchor_token[0] == 'attr()':
                attr = compute_attr(style, anchor_token)
                if attr is None:
                    computed_value = None
                else:
                    computed_value = (value[0], ((attr,) + value[1][1:]))
            else:
                computed_value = value
        if computed_value is None:
            LOGGER.warning('Unable to compute %r value for content: %r' % (
                style.element, ', '.join(str(item) for item in value)))
        else:
            computed_values.append(computed_value)

    return tuple(computed_values)


@register_computer('bookmark-label')
def bookmark_label(style, name, values):
    """Compute the ``bookmark-label`` property."""
    return _content_list(style, values)


@register_computer('string-set')
def string_set(style, name, values):
    """Compute the ``string-set`` property."""
    # Spec asks for strings after custom keywords, but we allow content-lists
    return tuple(
        (string_set[0], _content_list(style, string_set[1]))
        for string_set in values)


@register_computer('content')
def content(style, name, values):
    """Compute the ``content`` property."""
    if len(values) == 1:
        value, = values
        if value == 'normal':
            return 'inhibit' if style.pseudo_type else 'contents'
        elif value == 'none':
            return 'inhibit'
    return _content_list(style, values)


@register_computer('display')
def display(style, name, value):
    """Compute the ``display`` property."""
    # See https://www.w3.org/TR/CSS21/visuren.html#dis-pos-flo.
    float_ = style.specified['float']
    position = style.specified['position']
    if position in ('absolute', 'fixed') or float_ != 'none' or (
            style.is_root_element):
        if value == ('inline-table',):
            return ('block', 'table')
        elif len(value) == 1 and value[0].startswith('table-'):
            return ('block', 'flow')
        elif value[0] == 'inline':
            if 'list-item' in value:
                return ('block', 'flow', 'list-item')
            else:
                return ('block', 'flow')
    return value


@register_computer('float')
def compute_float(style, name, value):
    """Compute the ``float`` property."""
    # See https://www.w3.org/TR/CSS21/visuren.html#dis-pos-flo.
    position = style.specified['position']
    if position in ('absolute', 'fixed') or position[0] == 'running()':
        return 'none'
    else:
        return value


@register_computer('font-size')
def font_size(style, name, value):
    """Compute the ``font-size`` property."""
    if value in FONT_SIZE_KEYWORDS:
        return FONT_SIZE_KEYWORDS[value]

    keyword_values = list(FONT_SIZE_KEYWORDS.values())
    if style.parent_style is None:
        parent_font_size = INITIAL_VALUES['font_size']
    else:
        parent_font_size = style.parent_style['font_size']

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
        return value.value * parent_font_size / 100
    else:
        return length(
            style, name, value, pixels_only=True,
            font_size=parent_font_size)


@register_computer('font-weight')
def font_weight(style, name, value):
    """Compute the ``font-weight`` property."""
    if value == 'normal':
        return 400
    elif value == 'bold':
        return 700
    elif value in ('bolder', 'lighter'):
        if style.parent_style is None:
            parent_value = INITIAL_VALUES['font_weight']
        else:
            parent_value = style.parent_style['font_weight']
        return FONT_WEIGHT_RELATIVE[value][parent_value]
    else:
        return value


def _compute_track_breadth(style, name, value):
    """Compute track breadth."""
    if value in ('auto', 'min-content', 'max-content'):
        return value
    elif isinstance(value, Dimension):
        if value.unit == 'fr':
            return value
        else:
            return length(style, name, value)


def _track_size(style, name, values):
    """Compute track size."""
    return_values = []
    for i, value in enumerate(values):
        if i % 2 == 0:
            # line name
            return_values.append(value)
        else:
            # track section
            track_breadth = _compute_track_breadth(style, name, value)
            if track_breadth:
                return_values.append(track_breadth)
            elif value[0] == 'minmax()':
                return_values.append((
                    'minmax()',
                    _compute_track_breadth(style, name, value[1]),
                    _compute_track_breadth(style, name, value[2])))
            elif value[0] == 'fit-content()':
                return_values.append((
                    'fit-content()', length(style, name, value[1])))
            elif value[0] == 'repeat()':
                return_values.append((
                    'repeat()', value[1], _track_size(style, name, value[2])))
    return tuple(return_values)


@register_computer('grid-template-columns')
@register_computer('grid-template-rows')
def grid_template(style, name, values):
    """Compute the ``grid-template-*`` properties."""
    if values == 'none' or values[0] == 'subgrid':
        return values
    else:
        return _track_size(style, name, values)


@register_computer('grid-auto-columns')
@register_computer('grid-auto-rows')
def grid_auto(style, name, values):
    """Compute the ``grid-auto-*`` properties."""
    return_values = []
    for value in values:
        track_breadth = _compute_track_breadth(style, name, value)
        if track_breadth:
            return_values.append(track_breadth)
        elif value[0] == 'minmax()':
            return_values.append((
                'minmax()', grid_auto(style, name, [value[1]])[0],
                grid_auto(style, name, [value[2]])[0]))
        elif value[0] == 'fit-content()':
            return_values.append((
                'fit-content()', grid_auto(style, name, [value[1]])[0]))
    return tuple(return_values)


@register_computer('line-height')
def line_height(style, name, value):
    """Compute the ``line-height`` property."""
    if value == 'normal':
        return value
    elif not value.unit:
        return ('NUMBER', value.value)
    elif value.unit == '%':
        factor = value.value / 100
        font_size_value = style['font_size']
        pixels = factor * font_size_value
    else:
        pixels = length(style, name, value, pixels_only=True)
    return ('PIXELS', pixels)


@register_computer('anchor')
def anchor(style, name, values):
    """Compute the ``anchor`` property."""
    if values != 'none':
        _, key = values
        anchor_name = style.element.get(key) or None
        return anchor_name


@register_computer('link')
def link(style, name, values):
    """Compute the ``link`` property."""
    if values == 'none':
        return None
    else:
        type_, value = values
        if type_ == 'attr()':
            return get_link_attribute(style.element, value, style.base_url)
        else:
            return values


@register_computer('lang')
def lang(style, name, values):
    """Compute the ``lang`` property."""
    if values == 'none':
        return None
    else:
        name, key = values
        if name == 'attr()':
            return style.element.get(key) or None
        elif name == 'string':
            return key


@register_computer('tab-size')
def tab_size(style, name, value):
    """Compute the ``tab-size`` property."""
    return value if isinstance(value, int) else length(style, name, value)


@register_computer('transform')
def transform(style, name, value):
    """Compute the ``transform`` property."""
    result = []
    for function, args in value:
        if function == 'translate':
            args = length_or_percentage_tuple(style, name, args)
        result.append((function, args))
    return tuple(result)


@register_computer('vertical-align')
def vertical_align(style, name, value):
    """Compute the ``vertical-align`` property."""
    # Use +/- half an em for super and sub, same as Pango.
    # (See the SUPERSUB_RISE constant in pango-markup.c)
    if value in (
            'baseline', 'middle', 'text-top', 'text-bottom', 'top', 'bottom'):
        return value
    elif value == 'super':
        return style['font_size'] * 0.5
    elif value == 'sub':
        return style['font_size'] * -0.5
    elif value.unit == '%':
        height, _ = strut_layout(style)
        return height * value.value / 100
    else:
        return length(style, name, value, pixels_only=True)


@register_computer('word-spacing')
def word_spacing(style, name, value):
    """Compute the ``word-spacing`` property."""
    if value == 'normal':
        return 0
    else:
        return length(style, name, value, pixels_only=True)


def strut_layout(style, context=None):
    """Return a tuple of the used value of ``line-height`` and the baseline.

    The baseline is given from the top edge of line height.

    """
    if style['font_size'] == 0:
        return 0, 0

    if context:
        key = _font_style_cache_key(style, include_size=True)
        if key in context.strut_layouts:
            return context.strut_layouts[key]

    layout = Layout(context, style)
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


def character_ratio(style, character):
    """Return the ratio of 1ex/font_size or 1ch/font_size."""
    # TODO: use context to use @font-face fonts

    assert character in ('x', '0')

    cache = style.cache[f'ratio_{"ex" if character == "x" else "ch"}']
    cache_key = _font_style_cache_key(style)
    if cache_key in cache:
        return cache[cache_key]

    # Avoid recursion for letter-spacing and word-spacing properties
    style = style.copy()
    style['letter_spacing'] = 'normal'
    style['word_spacing'] = 0
    # Random big value
    style['font_size'] = 1000

    layout = Layout(context=None, style=style)
    layout.set_text(character)
    line, _ = layout.get_first_line()

    ink_extents = ffi.new('PangoRectangle *')
    logical_extents = ffi.new('PangoRectangle *')
    pango.pango_layout_line_get_extents(line, ink_extents, logical_extents)
    if character == 'x':
        measure = -units_to_double(ink_extents.y)
    else:
        measure = units_to_double(logical_extents.width)
    ffi.release(ink_extents)
    ffi.release(logical_extents)

    # Zero means some kind of failure, fallback is 0.5.
    # We round to try keeping exact values that were altered by Pango.
    ratio = round(measure / style['font_size'], 5) or 0.5
    cache[cache_key] = ratio
    return ratio
