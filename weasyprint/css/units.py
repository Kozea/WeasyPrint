"""Constants and helpers for units."""

import math

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

# How many ddpx is one <unit>?
# https://drafts.csswg.org/css-values/#resolution
RESOLUTION_TO_DPPX = {
    'dppx': 1,
    'dpi': 1 / LENGTHS_TO_PIXELS['in'],
    'dpcm': 1 / LENGTHS_TO_PIXELS['cm'],
}

# Sets of units.
# https://drafts.csswg.org/css-values-4/#lengths
FONT_UNITS = {'ex', 'em', 'ch', 'rem', 'lh', 'rlh'}
ABSOLUTE_UNITS = set(LENGTHS_TO_PIXELS)
LENGTH_UNITS = ABSOLUTE_UNITS | FONT_UNITS
# https://drafts.csswg.org/css-values-4/#angles
ANGLE_UNITS = set(ANGLE_TO_RADIANS)
