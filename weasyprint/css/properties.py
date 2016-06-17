# coding: utf-8
"""
    weasyprint.css.properties
    -------------------------

    Various data about known properties.

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals
import collections

from tinycss.color3 import COLOR_KEYWORDS


Dimension = collections.namedtuple('Dimension', ['value', 'unit'])


# See http://www.w3.org/TR/CSS21/propidx.html
INITIAL_VALUES = {
    'background_attachment': ['scroll'],
    'background_color': COLOR_KEYWORDS['transparent'],
    'background_image': [('none', None)],
    'background_position': [('left', Dimension(0, '%'),
                             'top', Dimension(0, '%'))],
    'background_repeat': [('repeat', 'repeat')],
    'background_clip': ['border-box'],  # CSS3
    'background_origin': ['padding-box'],  # CSS3
    'background_size': [('auto', 'auto')],  # CSS3
    'border_collapse': 'separate',
    # http://www.w3.org/TR/css3-color/#currentcolor
    'border_top_color': 'currentColor',
    'border_right_color': 'currentColor',
    'border_bottom_color': 'currentColor',
    'border_left_color': 'currentColor',
    'border_spacing': (0, 0),
    'border_top_style': 'none',
    'border_right_style': 'none',
    'border_bottom_style': 'none',
    'border_left_style': 'none',
    'border_top_width': 3,  # Computed value for 'medium'
    'border_right_width': 3,
    'border_bottom_width': 3,
    'border_left_width': 3,
    'bottom': 'auto',
    'caption_side': 'top',
    'clear': 'none',
    'clip': (),  # empty collection, computed value for 'auto'
    'color': COLOR_KEYWORDS['black'],     # chosen by the user agent
    'content': 'normal',
    # Means 'none', but allow `display: list-item` to increment the
    # list-item counter. If we ever have a way for authors to query
    # computed values (JavaScript?), this value should serialize to 'none'.
    'counter_increment': 'auto',
    'counter_reset': [],  # parsed value for 'none'
    # 'counter_set': [],  # parsed value for 'none'
    'direction': 'ltr',
    'display': 'inline',
    'empty_cells': 'show',
    'float': 'none',
    'font_family': ['serif'],  # depends on user agent
    'font_size': 16,  # Actually medium, but we define medium from this.
    'font_stretch': 'normal',  # css3-fonts
    'font_style': 'normal',
    'font_variant': 'normal',
    'font_weight': 400,
    'height': 'auto',
    'left': 'auto',
    'letter_spacing': 'normal',
    'line_height': 'normal',
    'list_style_image': ('none', None),
    'list_style_position': 'outside',
    'list_style_type': 'disc',
    'margin_top': Dimension(0, 'px'),
    'margin_right': Dimension(0, 'px'),
    'margin_bottom': Dimension(0, 'px'),
    'margin_left': Dimension(0, 'px'),
    'max_height': Dimension(float('inf'), 'px'),  # Parsed value for 'none'
    'max_width': Dimension(float('inf'), 'px'),
    'min_height': Dimension(0, 'px'),
    'min_width': Dimension(0, 'px'),
    'orphans': 2,
    'outline_color': 'currentColor',  # invert is not supported
    'outline_style': 'none',
    'outline_width': 3,  # Computed value for 'medium'
    'overflow': 'visible',
    'padding_top': Dimension(0, 'px'),
    'padding_right': Dimension(0, 'px'),
    'padding_bottom': Dimension(0, 'px'),
    'padding_left': Dimension(0, 'px'),
    'page_break_after': 'auto',
    'page_break_before': 'auto',
    'page_break_inside': 'auto',
    'quotes': list('“”‘’'),  # depends on user agent
    'position': 'static',
    'right': 'auto',
    # http://dev.w3.org/csswg/css-gcpm/#named-strings
    'string_set': 'none',
    'table_layout': 'auto',
    # Taken from CSS3 Text.
    # The only other supported value form CSS3 is -weasy-end.
    'text_align': '-weasy-start',
    'text_decoration': 'none',
    'text_indent': Dimension(0, 'px'),
    'text_transform': 'none',
    'top': 'auto',
    'unicode_bidi': 'normal',
    'vertical_align': 'baseline',
    'visibility': 'visible',
    'white_space': 'normal',
    'widows': 2,
    'width': 'auto',
    'word_spacing': 0,  # computed value for 'normal'
    'z_index': 'auto',

    # CSS3 Paged Media: http://www.w3.org/TR/css3-page/#page-size
    'size': None,  # XXX set to A4 in computed_values

    # CSS3 User Interface: http://www.w3.org/TR/css3-ui/#box-sizing
    'box_sizing': 'content-box',
    'overflow_wrap': 'normal',

    # CSS3 Backgrounds and Borders: http://www.w3.org/TR/css3-background/
    'border_top_left_radius': (Dimension(0, 'px'), Dimension(0, 'px')),
    'border_top_right_radius': (Dimension(0, 'px'), Dimension(0, 'px')),
    'border_bottom_left_radius': (Dimension(0, 'px'), Dimension(0, 'px')),
    'border_bottom_right_radius': (Dimension(0, 'px'), Dimension(0, 'px')),

    # CSS3 Color: http://www.w3.org/TR/css3-color/#transparency
    'opacity': 1,

    # CSS3 2D Transforms: http://www.w3.org/TR/css3-2d-transforms
    'transform_origin': (Dimension(50, '%'), Dimension(50, '%')),
    'transform': (),  # empty sequence: computed value for 'none'

    # Taken from SVG:
    # http://www.w3.org/TR/SVG/painting.html#ImageRenderingProperty
    'image_rendering': 'auto',

    # http://www.w3.org/TR/css3-images/#the-image-resolution
    'image_resolution': 1,  # dppx

    # Proprietary
    'anchor': None,  # computed value of 'none'
    'link': None,  # computed value of 'none'
    'lang': None,  # computed value of 'none'

    # CSS3 Generated Content for Paged Media
    # http://dev.w3.org/csswg/css3-gcpm/
    'bookmark_label': [('content', 'text')],
    'bookmark_level': 'none',

    # CSS4 Text
    # http://dev.w3.org/csswg/css4-text/#hyphenation
    'hyphens': 'manual',
    'hyphenate_character': '‐',
    'hyphenate_limit_chars': (5, 2, 2),
    'hyphenate_limit_zone': Dimension(0, 'px'),

    # Internal, to implement the "static position" for absolute boxes.
    '_weasy_specified_display': 'inline',
}


KNOWN_PROPERTIES = set(name.replace('_', '-') for name in INITIAL_VALUES)

# Not applicable to the print media
NOT_PRINT_MEDIA = set([
    # Aural media:
    'azimuth',
    'cue',
    'cue-after',
    'cue-before',
    'cursor',
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

    # outlines are not just for interactive but any visual media in css3-ui
])


# Do not list shorthand properties here as we handle them before inheritance.
#
# text_decoration is not a really inherited, see
# http://www.w3.org/TR/CSS2/text.html#propdef-text-decoration
#
# link: click events normally bubble up to link ancestors
#   See http://lists.w3.org/Archives/Public/www-style/2012Jun/0315.html
INHERITED = set("""
    border_collapse
    border_spacing
    caption_side
    color
    direction
    empty_cells
    font_family
    font_size
    font_style
    font_stretch
    font_variant
    font_weight
    letter_spacing
    line_height
    list_style_image
    list_style_position
    list_style_type
    orphans
    overflow_wrap
    quotes
    text_align
    text_decoration
    text_indent
    text_transform
    visibility
    white_space
    widows
    word_spacing

    hyphens
    hyphenate_character
    hyphenate_limit_chars
    hyphenate_limit_zone
    image_rendering
    image_resolution
    lang
    link
""".split())

# Inherited but not applicable to print:
#    azimuth
#    cursor
#    elevation
#    pitch_range
#    pitch
#    richness
#    speak_header
#    speak_numeral
#    speak_punctuation
#    speak
#    speech_rate
#    stress
#    voice_family
#    volume


# http://www.w3.org/TR/CSS21/tables.html#model
# See also http://lists.w3.org/Archives/Public/www-style/2012Jun/0066.html
# Only non-inherited properties need to be included here.
TABLE_WRAPPER_BOX_PROPERTIES = set('''
    position
    float
    margin_top
    margin_bottom
    margin_left
    margin_right
    top
    bottom
    left
    right

    clear
    counter_increment
    counter_reset
    opacity
    page_break_before
    page_break_after
    page_break_inside
    transform
    transform_origin
    vertical_align
    z_index
'''.split())
