"""Constants and helpers for units."""

import math

from ..text.line_break import character_ratio, strut

# How many radians is one <unit>?
# https://drafts.csswg.org/css-values-4/#angles
ANGLE_TO_RADIANS = {
    'rad': 1,
    'turn': 2 * math.pi,
    'deg': math.pi / 180,
    'grad': math.pi / 200,
}

# How many CSS pixels is one <unit>?
# https://www.w3.org/TR/CSS21/syndata.html#length-units
LENGTHS_TO_PIXELS = {
    'px': 1,
    'pt': 1 / 0.75,
    'pc': 16,
    'in': 96,
    'cm': 96 / 2.54,
    'mm': 96 / 25.4,
    'q': 96 / 25.4 / 4,
}

# How many dppx is one <unit>?
# https://drafts.csswg.org/css-values/#resolution
RESOLUTION_TO_DPPX = {
    'dppx': 1,
    'x': 1,
    'dpi': 1 / LENGTHS_TO_PIXELS['in'],
    'dpcm': 1 / LENGTHS_TO_PIXELS['cm'],
}

# Sets of units.
# https://drafts.csswg.org/css-values-4/#lengths
FONT_UNITS = {'em', 'ex', 'cap', 'ch', 'ic', 'lh'}
FONT_UNITS |= {f'r{unit}' for unit in FONT_UNITS}
ABSOLUTE_UNITS = set(LENGTHS_TO_PIXELS)
LENGTH_UNITS = ABSOLUTE_UNITS | FONT_UNITS
# https://drafts.csswg.org/css-values-4/#angles
ANGLE_UNITS = set(ANGLE_TO_RADIANS)


def to_pixels(value, style, property_name, font_size=None):
    """Get number of pixels corresponding to a length."""
    if value.value == 0:
        return 0
    elif (unit := value.unit.lower()) == 'px':
        return value.value
    elif unit in LENGTHS_TO_PIXELS:
        # Convert absolute lengths to pixels.
        return value.value * LENGTHS_TO_PIXELS[unit]
    elif unit in FONT_UNITS:
        assert (style, font_size) != (None, None)
        if font_size is None:
            font_size = style['font_size']
        if unit == 'lh':
            if property_name in ('font_size', 'line_height'):
                if style.parent_style is None:
                    parent_style = style.root_style
                else:
                    parent_style = style.parent_style
                line_height, _ = strut(parent_style)
            else:
                line_height, _ = strut(style)
            return value.value * line_height
        elif unit == 'rlh':
            parent_style = style.root_style
            line_height, _ = strut(parent_style)
            return value.value * line_height
        elif unit == 'em':
            return value.value * font_size
        elif unit == 'rem':
            return value.value * style.root_style['font_size']
        elif unit.startswith('r'):
            ratio = character_ratio(style.root_style, unit[1:])
            return value.value * style.root_style['font_size'] * ratio
        else:
            ratio = character_ratio(style, unit)
            return value.value * font_size * ratio


def to_radians(value):
    """Get number of radians corresponding to an angle."""
    if (unit := value.unit.lower()) == 'rad':
        return value.value
    elif unit in ANGLE_TO_RADIANS:
        return value.value * ANGLE_TO_RADIANS[unit]
