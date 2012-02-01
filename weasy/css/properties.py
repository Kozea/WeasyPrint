# coding: utf8

#  WeasyPrint converts web documents (HTML, CSS, ...) to PDF.
#  Copyright (C) 2011  Simon Sapin
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
    Data about known CSS properties.
"""


from cssutils.css import PropertyValue


# See http://www.w3.org/TR/CSS21/propidx.html
INITIAL_VALUES = {
    'background_attachment': 'scroll',
    'background_color': PropertyValue('transparent')[0],
    'background_image': 'none',
    'background_position': list(PropertyValue('0% 0%')),
    'background_repeat': 'repeat',
    'background_clip': 'border-box',  # CSS3
    'background_origin': 'padding-box',  # CSS3
    'background_size': ('auto', 'auto'),  # CSS3
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
    'clip': 'auto',
    'color': PropertyValue('#000')[0],     # depends on user agent
    'content': 'normal',
    # Means 'none', but allow `display: list-item` to increment the
    # list-item counter. If we ever have a way for authors to query
    # computed values (JavaScript?), this value should serialize to 'none'.
    'counter_increment': 'auto',
    'counter_reset': [],  # parsed value for 'none'
#    'counter_set': [],  # parsed value for 'none'
    'direction': 'ltr',
    'display': 'inline',
    'empty_cells': 'show',
    'float': 'none',
    'font_family': ['serif'], # depends on user agent
    'font_size': 16,  # Actually medium, but we define medium from this.
    'font_style': 'normal',
    'font_variant': 'normal',
    'font_weight': 400,
    'height': 'auto',
    'left': 'auto',
    'letter_spacing': 'normal',
    'line_height': 'normal',
    'list_style_image': 'none',
    'list_style_position': 'outside',
    'list_style_type': 'disc',
    'margin_top': 0,
    'margin_right': 0,
    'margin_bottom': 0,
    'margin_left': 0,
    'max_height': 'none',
    'max_width': 'none',
    'min_height': 0,
    'min_width': 0,
    'orphans': 2,
    'overflow': 'visible',
    'padding_top': 0,
    'padding_right': 0,
    'padding_bottom': 0,
    'padding_left': 0,
    'page_break_after': 'auto',
    'page_break_before': 'auto',
    'page_break_inside': 'auto',
    'quotes': list(u'“”‘’'),  # depends on user agent
    'position': 'static',
    'right': 'auto',
    'table_layout': 'auto',
    'text_align': '-weasy-start',  # Taken from CSS3 Text.
                   # The only other supported value form CSS3 is -weasy-end.
    'text_decoration': 'none',
    'text_indent': 0,
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

    # Taken from SVG:
    # http://www.w3.org/TR/SVG/painting.html#ImageRenderingProperty
    'image_rendering': 'auto',
}

# Not applicable to the print media
NOT_PRINT_MEDIA = set([
    # Aural media:
    'azimuth',
    'cue',
    'cue_after',
    'cue_before',
    'cursor',
    'elevation',
    'pause',
    'pause_after',
    'pause_before',
    'pitch_range',
    'pitch',
    'play_during',
    'richness',
    'speak_header',
    'speak_numeral',
    'speak_punctuation',
    'speak',
    'speech_rate',
    'stress',
    'voice_family',
    'volume',

    # Outlines only apply to interactive media, just like cursor.
    'outline'
    'outline_color',
    'outline_style',
    'outline_width',
])


# Do not list shorthand properties here as we handle them before inheritance.
#
# text_decoration is not a really inherited, see
# http://www.w3.org/TR/CSS2/text.html#propdef-text-decoration
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
    font_variant
    font_weight
    letter_spacing
    line_height
    list_style_image
    list_style_position
    list_style_type
    orphans
    quotes
    text_align
    text_decoration
    text_indent
    text_transform
    visibility
    white_space
    widows
    word_spacing
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
'''.split())


BACKGROUND_INITIAL = dict(
    (name, value) for name, value in INITIAL_VALUES.iteritems()
    if name.startswith('background'))
