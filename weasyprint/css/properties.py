"""Various data about known CSS properties."""

import collections
from math import inf

from tinycss2.color4 import parse_color

Dimension = collections.namedtuple('Dimension', ['value', 'unit'])

ZERO_PIXELS = Dimension(0, 'px')

INITIAL_VALUES = {
    # CSS 2.1: https://www.w3.org/TR/CSS21/propidx.html
    'bottom': 'auto',
    'caption_side': 'top',
    'clear': 'none',
    'clip': (),  # computed value for 'auto'
    'color': parse_color('black'),  # chosen by the user agent
    'direction': 'ltr',
    'display': ('inline', 'flow'),
    'empty_cells': 'show',
    'float': 'none',
    'left': 'auto',
    'line_height': 'normal',
    'margin_top': ZERO_PIXELS,
    'margin_right': ZERO_PIXELS,
    'margin_bottom': ZERO_PIXELS,
    'margin_left': ZERO_PIXELS,
    'padding_top': ZERO_PIXELS,
    'padding_right': ZERO_PIXELS,
    'padding_bottom': ZERO_PIXELS,
    'padding_left': ZERO_PIXELS,
    'position': 'static',
    'right': 'auto',
    'table_layout': 'auto',
    'top': 'auto',
    'unicode_bidi': 'normal',
    'vertical_align': 'baseline',
    'visibility': 'visible',
    'z_index': 'auto',

    # Backgrounds and Borders 3 (CR): https://www.w3.org/TR/css-backgrounds-3/
    'background_attachment': ('scroll',),
    'background_clip': ('border-box',),
    'background_color': parse_color('transparent'),
    'background_image': (('none', None),),
    'background_origin': ('padding-box',),
    'background_position': (('left', Dimension(0, '%'),
                             'top', Dimension(0, '%')),),
    'background_repeat': (('repeat', 'repeat'),),
    'background_size': (('auto', 'auto'),),
    'border_bottom_color': 'currentcolor',
    'border_bottom_left_radius': (ZERO_PIXELS, ZERO_PIXELS),
    'border_bottom_right_radius': (ZERO_PIXELS, ZERO_PIXELS),
    'border_bottom_style': 'none',
    'border_bottom_width': 3,
    'border_collapse': 'separate',
    'border_left_color': 'currentcolor',
    'border_left_style': 'none',
    'border_left_width': 3,
    'border_right_color': 'currentcolor',
    'border_right_style': 'none',
    'border_right_width': 3,
    'border_spacing': (0, 0),
    'border_top_color': 'currentcolor',
    'border_top_left_radius': (ZERO_PIXELS, ZERO_PIXELS),
    'border_top_right_radius': (ZERO_PIXELS, ZERO_PIXELS),
    'border_top_style': 'none',
    'border_top_width': 3,  # computed value for 'medium'
    'border_image_source': ('none', None),
    'border_image_slice': (
        Dimension(100, '%'), Dimension(100, '%'),
        Dimension(100, '%'), Dimension(100, '%'),
        None),
    'border_image_width': (1, 1, 1, 1),
    'border_image_outset': (
        Dimension(0, None), Dimension(0, None),
        Dimension(0, None), Dimension(0, None)),
    'border_image_repeat': ('stretch', 'stretch'),
    'mask_border_source': ('none', None),
    'mask_border_slice': (
        Dimension(100, '%'), Dimension(100, '%'),
        Dimension(100, '%'), Dimension(100, '%'),
        None),
    'mask_border_width': ('auto', 'auto', 'auto', 'auto'),
    'mask_border_outset': (
        Dimension(0, None), Dimension(0, None),
        Dimension(0, None), Dimension(0, None)),
    'mask_border_repeat': ('stretch', 'stretch'),
    'mask_border_mode': 'alpha',


    # Color 3 (REC): https://www.w3.org/TR/css-color-3/
    'opacity': 1,

    # Multi-column Layout (WD): https://www.w3.org/TR/css-multicol-1/
    'column_width': 'auto',
    'column_count': 'auto',
    'column_rule_color': 'currentcolor',
    'column_rule_style': 'none',
    'column_rule_width': 'medium',
    'column_fill': 'balance',
    'column_span': 'none',

    # Fonts 3 (REC): https://www.w3.org/TR/css-fonts-3/
    'font_family': ('serif',),  # depends on user agent
    'font_feature_settings': 'normal',
    'font_kerning': 'auto',
    'font_language_override': 'normal',
    'font_size': 16,  # actually medium, but we define medium from this
    'font_stretch': 'normal',
    'font_style': 'normal',
    'font_variant': 'normal',
    'font_variant_alternates': 'normal',
    'font_variant_caps': 'normal',
    'font_variant_east_asian': 'normal',
    'font_variant_ligatures': 'normal',
    'font_variant_numeric': 'normal',
    'font_variant_position': 'normal',
    'font_weight': 400,

    # Fonts 4 (WD): https://www.w3.org/TR/css-fonts-4/
    'font_variation_settings': 'normal',

    # Fragmentation 3/4 (CR/WD): https://www.w3.org/TR/css-break-4/
    'box_decoration_break': 'slice',
    'break_after': 'auto',
    'break_before': 'auto',
    'break_inside': 'auto',
    'margin_break': 'auto',
    'orphans': 2,
    'widows': 2,

    # Generated Content 3 (WD): https://www.w3.org/TR/css-content-3/
    'bookmark_label': (('content', 'text'),),
    'bookmark_level': 'none',
    'bookmark_state': 'open',
    'content': 'normal',
    'footnote_display': 'block',
    'footnote_policy': 'auto',
    'quotes': 'auto',
    'string_set': 'none',

    # Images 3/4 (CR/WD): https://www.w3.org/TR/css-images-4/
    'image_resolution': 1,  # dppx
    'image_rendering': 'auto',
    'image_orientation': 'from-image',
    'object_fit': 'fill',
    'object_position': (('left', Dimension(50, '%'),
                         'top', Dimension(50, '%')),),

    # Paged Media 3 (WD): https://www.w3.org/TR/css-page-3/
    'size': None,  # set to A4 in computed_values
    'page': 'auto',
    'bleed_left': 'auto',
    'bleed_right': 'auto',
    'bleed_top': 'auto',
    'bleed_bottom': 'auto',
    'marks': (),  # computed value for 'none'

    # Text 3/4 (WD/WD): https://www.w3.org/TR/css-text-4/
    'hyphenate_character': '‐',  # computed value chosen by the user agent
    'hyphenate_limit_chars': (5, 2, 2),
    'hyphenate_limit_zone': ZERO_PIXELS,
    'hyphens': 'manual',
    'letter_spacing': 'normal',
    'tab_size': 8,
    'text_align_all': 'start',
    'text_align_last': 'auto',
    'text_indent': ZERO_PIXELS,
    'text_transform': 'none',
    'white_space': 'normal',
    'word_break': 'normal',
    'word_spacing': 0,  # computed value for 'normal'

    # Transforms 1 (CR): https://www.w3.org/TR/css-transforms-1/
    'transform_origin': (Dimension(50, '%'), Dimension(50, '%')),
    'transform': (),  # computed value for 'none'

    # User Interface 3/4 (REC/WD): https://www.w3.org/TR/css-ui-4/
    'appearance': 'none',
    'outline_color': 'currentcolor',  # invert is not supported
    'outline_style': 'none',
    'outline_width': 3,  # computed value for 'medium'

    # Sizing 3 (WD): https://www.w3.org/TR/css-sizing-3/
    'box_sizing': 'content-box',
    'height': 'auto',
    'max_height': Dimension(inf, 'px'),  # parsed value for 'none'
    'max_width': Dimension(inf, 'px'),
    'min_height': 'auto',
    'min_width': 'auto',
    'width': 'auto',

    # Flexible Box Layout Module 1 (CR): https://www.w3.org/TR/css-flexbox-1/
    'flex_basis': 'auto',
    'flex_direction': 'row',
    'flex_grow': 0,
    'flex_shrink': 1,
    'flex_wrap': 'nowrap',

    # Grid Layout Module Level 2 (CR): https://www.w3.org/TR/css-grid-2/
    'grid_auto_columns': ('auto',),
    'grid_auto_flow': ('row',),
    'grid_auto_rows': ('auto',),
    'grid_template_areas': 'none',
    'grid_template_columns': 'none',
    'grid_template_rows': 'none',
    'grid_row_start': 'auto',
    'grid_column_start': 'auto',
    'grid_row_end': 'auto',
    'grid_column_end': 'auto',

    # CSS Box Alignment Module Level 3 (WD): https://www.w3.org/TR/css-align-3/
    'align_content': ('normal',),
    'align_items': ('normal',),
    'align_self': ('auto',),
    'justify_content': ('normal',),
    'justify_items': ('normal',),
    'justify_self': ('auto',),
    'order': 0,
    'column_gap': 'normal',
    'row_gap': 'normal',

    # Text Decoration Module 3 (CR): https://www.w3.org/TR/css-text-decor-3/
    'text_decoration_line': 'none',
    'text_decoration_color': 'currentcolor',
    'text_decoration_style': 'solid',

    # Overflow Module 3/4 (WD): https://www.w3.org/TR/css-overflow-4/
    'block_ellipsis': 'none',
    'continue': 'auto',
    'max_lines': 'none',
    'overflow': 'visible',
    'overflow_wrap': 'normal',
    'text_overflow': 'clip',

    # Lists Module 3 (WD): https://drafts.csswg.org/css-lists-3/
    # Means 'none', but allow `display: list-item` to increment the
    # list-item counter. If we ever have a way for authors to query
    # computed values (JavaScript?), this value should serialize to 'none'.
    'counter_increment': 'auto',
    'counter_reset': (),  # parsed value for 'none'
    'counter_set': (),  # parsed value for 'none'
    'list_style_image': ('none', None),
    'list_style_position': 'outside',
    'list_style_type': 'disc',

    # Proprietary
    'anchor': None,  # computed value of 'none'
    'link': None,  # computed value of 'none'
    'lang': None,  # computed value of 'none'
}


KNOWN_PROPERTIES = set(name.replace('_', '-') for name in INITIAL_VALUES)

# Do not list shorthand properties here as we handle them before inheritance.
#
# Values inherited but not applicable to print are not included.
#
# text_decoration is not a really inherited, see
# https://www.w3.org/TR/CSS2/text.html#propdef-text-decoration
#
# link: click events normally bubble up to link ancestors
#   See https://lists.w3.org/Archives/Public/www-style/2012Jun/0315.html
INHERITED = {
    'block_ellipsis',
    'border_collapse',
    'border_spacing',
    'caption_side',
    'color',
    'direction',
    'empty_cells',
    'font_family',
    'font_feature_settings',
    'font_kerning',
    'font_language_override',
    'font_size',
    'font_style',
    'font_stretch',
    'font_variant',
    'font_variant_alternates',
    'font_variant_caps',
    'font_variant_east_asian',
    'font_variant_ligatures',
    'font_variant_numeric',
    'font_variant_position',
    'font_variation_settings',
    'font_weight',
    'hyphens',
    'hyphenate_character',
    'hyphenate_limit_chars',
    'hyphenate_limit_zone',
    'image_rendering',
    'image_resolution',
    'lang',
    'letter_spacing',
    'line_height',
    'link',
    'list_style_image',
    'list_style_position',
    'list_style_type',
    'orphans',
    'overflow_wrap',
    'quotes',
    'tab_size',
    'text_align_all',
    'text_align_last',
    'text_indent',
    'text_transform',
    'visibility',
    'white_space',
    'widows',
    'word_break',
    'word_spacing',
}


# https://www.w3.org/TR/CSS21/tables.html#model
# See also https://lists.w3.org/Archives/Public/www-style/2012Jun/0066.html
# Only non-inherited properties need to be included here.
TABLE_WRAPPER_BOX_PROPERTIES = {
    'bottom',
    'break_after',
    'break_before',
    'clear',
    'counter_increment',
    'counter_reset',
    'counter_set',
    'float',
    'left',
    'margin_top',
    'margin_bottom',
    'margin_left',
    'margin_right',
    'opacity',
    'overflow',
    'position',
    'right',
    'top',
    'transform',
    'transform_origin',
    'vertical_align',
    'z_index',
}


# Properties that have an initial value that is not always the same when
# computed.
INITIAL_NOT_COMPUTED = {
    'display',
    'column_gap',
    'bleed_top',
    'bleed_left',
    'bleed_bottom',
    'bleed_right',
    'outline_width',
    'outline_color',
    'column_rule_width',
    'column_rule_color',
    'border_top_width',
    'border_left_width',
    'border_bottom_width',
    'border_right_width',
    'border_top_color',
    'border_left_color',
    'border_bottom_color',
    'border_right_color',
}
