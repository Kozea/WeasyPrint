# coding: utf-8
"""
    weasyprint.css.computed_values
    ------------------------------

    Convert *specified* property values (the result of the cascade and
    inhertance) into *computed* values (that are inherited).

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from .. import text
from ..urls import get_link_attribute
from .properties import INITIAL_VALUES, Dimension

ZERO_PIXELS = Dimension(0, 'px')


# How many CSS pixels is one <unit>?
# http://www.w3.org/TR/CSS21/syndata.html#length-units
LENGTHS_TO_PIXELS = {
    'px': 1,
    'pt': 1. / 0.75,
    'pc': 16.,  # LENGTHS_TO_PIXELS['pt'] * 12
    'in': 96.,  # LENGTHS_TO_PIXELS['pt'] * 72
    'cm': 96. / 2.54,  # LENGTHS_TO_PIXELS['in'] / 2.54
    'mm': 96. / 25.4,  # LENGTHS_TO_PIXELS['in'] / 25.4
    'q': 96. / 25.4 / 4.,  # LENGTHS_TO_PIXELS['mm'] / 4
}


# Value in pixels of font-size for <absolute-size> keywords: 12pt (16px) for
# medium, and scaling factors given in CSS3 for others:
# http://www.w3.org/TR/css3-fonts/#font-size-prop
# TODO: this will need to be ordered to implement 'smaller' and 'larger'
FONT_SIZE_KEYWORDS = dict(
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
PAGE_SIZES = dict(
    a5=(
        Dimension(148, 'mm'),
        Dimension(210, 'mm'),
    ),
    a4=(
        Dimension(210, 'mm'),
        Dimension(297, 'mm'),
    ),
    a3=(
        Dimension(297, 'mm'),
        Dimension(420, 'mm'),
    ),
    b5=(
        Dimension(176, 'mm'),
        Dimension(250, 'mm'),
    ),
    b4=(
        Dimension(250, 'mm'),
        Dimension(353, 'mm'),
    ),
    letter=(
        Dimension(8.5, 'in'),
        Dimension(11, 'in'),
    ),
    legal=(
        Dimension(8.5, 'in'),
        Dimension(14, 'in'),
    ),
    ledger=(
        Dimension(11, 'in'),
        Dimension(17, 'in'),
    ),
)
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


def register_computer(name):
    """Decorator registering a property ``name`` for a function."""
    name = name.replace('-', '_')

    def decorator(function):
        """Register the property ``name`` for ``function``."""
        COMPUTER_FUNCTIONS[name] = function
        return function
    return decorator


def compute(element, pseudo_type, specified, computed, parent_style,
            root_style, base_url):
    """
    Return a dict of computed values.

    :param element: The HTML element these style apply to
    :param pseudo_type: The type of pseudo-element, eg 'before', None
    :param specified: a dict of specified values. Should contain
                      values for all properties.
    :param computed: a dict of already known computed values.
                     Only contains some properties (or none).
    :param parent_style: a dict of computed values of the parent
                         element (should contain values for all properties),
                         or ``None`` if ``element`` is the root element.
    :param base_url: The base URL used to resolve relative URLs.

    """

    def computer():
        """Dummy object that holds attributes."""
        return 0

    computer.is_root_element = parent_style is None
    if parent_style is None:
        parent_style = INITIAL_VALUES

    computer.element = element
    computer.pseudo_type = pseudo_type
    computer.specified = specified
    computer.computed = computed
    computer.parent_style = parent_style
    computer.root_style = root_style
    computer.base_url = base_url

    getter = COMPUTER_FUNCTIONS.get

    for name in COMPUTING_ORDER:
        if name in computed:
            # Already computed
            continue

        value = specified[name]
        function = getter(name)
        if function is not None:
            value = function(computer, name, value)
        # else: same as specified

        computed[name] = value

    computed['_weasy_specified_display'] = specified['display']
    return computed


# Let's be consistent, always use ``name`` as an argument even when
# it is useless.
# pylint: disable=W0613


@register_computer('background-image')
def background_image(computer, name, values):
    """Compute lenghts in gradient background-image."""
    for type_, value in values:
        if type_ in ('linear-gradient', 'radial-gradient'):
            value.stop_positions = tuple(
                length(computer, name, pos) if pos is not None else None
                for pos in value.stop_positions)
        if type_ == 'radial-gradient':
            value.center, = background_position(
                computer, name, (value.center,))
            if value.size_type == 'explicit':
                value.size = length_or_percentage_tuple(
                    computer, name, value.size)
    return values


@register_computer('background-position')
def background_position(computer, name, values):
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
def length(computer, name, value, font_size=None, pixels_only=False):
    """Compute a length ``value``."""
    if value == 'auto':
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
            font_size = computer.computed['font_size']
        if unit == 'ex':
            # TODO: cache
            result = value.value * font_size * ex_ratio(computer.computed)
        elif unit == 'ch':
            # TODO: cache
            layout = text.Layout(
                context=None, font_size=font_size,
                style=computer.computed)
            layout.set_text('0')
            line, = layout.iter_lines()
            logical_width, _ = text.get_size(line, computer.computed)
            result = value.value * logical_width
        elif unit == 'em':
            result = value.value * font_size
        elif unit == 'rem':
            result = value.value * computer.root_style['font_size']
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
        if 'crop' in computer.computed['marks']:
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
    style = computer.computed[name.replace('width', 'style')]
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


@register_computer('content')
def content(computer, name, values):
    """Compute the ``content`` property."""
    if values in ('normal', 'none'):
        return values
    else:
        return tuple(
            ('STRING', computer.element.get(value, ''))
            if type_ == 'attr' else (type_, value)
            for type_, value in values)


@register_computer('display')
def display(computer, name, value):
    """Compute the ``display`` property.

    See http://www.w3.org/TR/CSS21/visuren.html#dis-pos-flo

    """
    float_ = computer.specified['float']
    position = computer.specified['position']
    if position in ('absolute', 'fixed') or float_ != 'none' or \
            computer.is_root_element:
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
    if computer.specified['position'] in ('absolute', 'fixed'):
        return 'none'
    else:
        return value


@register_computer('font-size')
def font_size(computer, name, value):
    """Compute the ``font-size`` property."""
    if value in FONT_SIZE_KEYWORDS:
        return FONT_SIZE_KEYWORDS[value]
    # TODO: support 'larger' and 'smaller'

    parent_font_size = computer.parent_style['font_size']
    if value.unit == '%':
        return value.value * parent_font_size / 100.
    else:
        return length(computer, name, value, pixels_only=True,
                      font_size=parent_font_size)


@register_computer('font-weight')
def font_weight(computer, name, value):
    """Compute the ``font-weight`` property."""
    if value == 'normal':
        return 400
    elif value == 'bold':
        return 700
    elif value in ('bolder', 'lighter'):
        parent_value = computer.parent_style['font_weight']
        # Use a string here as StyleDict.__setattr__ turns integers into pixel
        # lengths. This is a number without unit.
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
        font_size_value = computer.computed['font_size']
        pixels = factor * font_size_value
    else:
        pixels = length(computer, name, value, pixels_only=True)
    return ('PIXELS', pixels)


@register_computer('anchor')
def anchor(computer, name, values):
    """Compute the ``anchor`` property."""
    if values != 'none':
        _, key = values
        return computer.element.get(key) or None


@register_computer('link')
def link(computer, name, values):
    """Compute the ``link`` property."""
    if values == 'none':
        return None
    else:
        type_, value = values
        if type_ == 'attr':
            return get_link_attribute(
                computer.element, value, computer.base_url)
        else:
            return values


@register_computer('lang')
def lang(computer, name, values):
    """Compute the ``lang`` property."""
    if values == 'none':
        return None
    else:
        type_, key = values
        if type_ == 'attr':
            return computer.element.get(key) or None
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
        return computer.computed['font_size'] * 0.5
    elif value == 'sub':
        return computer.computed['font_size'] * -0.5
    elif value.unit == '%':
        height, _ = strut_layout(computer.computed)
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

    layout = text.Layout(
        context=context, font_size=style['font_size'], style=style)
    line, = layout.iter_lines()
    _, _, _, _, text_height, baseline = text.first_line_metrics(
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
    layout = text.Layout(context=None, font_size=font_size, style=style)
    layout.set_text('x')
    line, = layout.iter_lines()
    _, ink_height_above_baseline = text.get_ink_position(line)
    # Zero means some kind of failure, fallback is 0.5.
    # We round to try keeping exact values that were altered by Pango.
    return round(-ink_height_above_baseline / font_size, 5) or 0.5
