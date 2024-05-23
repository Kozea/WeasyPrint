"""Test expanders for shorthand properties."""

import pytest
import tinycss2
from tinycss2.color3 import parse_color

from weasyprint.css import preprocess_declarations
from weasyprint.css.properties import INITIAL_VALUES, ZERO_PIXELS
from weasyprint.css.validation.expanders import EXPANDERS

from ..testing_utils import assert_no_logs, capture_logs


def expand_to_dict(css, expected_error=None):
    """Helper to test shorthand properties expander functions."""
    declarations = tinycss2.parse_blocks_contents(css)

    with capture_logs() as logs:
        base_url = 'https://weasyprint.org/foo/'
        declarations = list(preprocess_declarations(base_url, declarations))

    if expected_error:
        assert len(logs) == 1
        assert expected_error in logs[0]
    else:
        assert not logs

    return {
        name: value for name, value, _ in declarations if value != 'initial'}


def assert_invalid(css, message='invalid'):
    assert expand_to_dict(css, message) == {}


@assert_no_logs
@pytest.mark.parametrize('expander', EXPANDERS)
def test_empty_expander_value(expander):
    assert_invalid(f'{expander}:', message='Ignored')


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('none', {'text_decoration_line': 'none'}),
    ('overline', {'text_decoration_line': {'overline'}}),
    ('overline blink line-through', {
        'text_decoration_line': {'blink', 'line-through', 'overline'},
    }),
    ('red', {'text_decoration_color': parse_color('red')}),
    ('inherit', {
        f'text_decoration_{key}': 'inherit'
        for key in ('color', 'line', 'style')}),
))
def test_text_decoration(rule, result):
    assert expand_to_dict(f'text-decoration: {rule}') == result


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'solid solid',
    'red red',
    '1px',
    'underline none',
    'none none',
))
def test_text_decoration_invalid(rule):
    assert_invalid(f'text-decoration: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('margin: inherit', {
        'margin_top': 'inherit',
        'margin_right': 'inherit',
        'margin_bottom': 'inherit',
        'margin_left': 'inherit',
    }),
    ('margin: 1em', {
        'margin_top': (1, 'em'),
        'margin_right': (1, 'em'),
        'margin_bottom': (1, 'em'),
        'margin_left': (1, 'em'),
    }),
    ('margin: -1em auto 20%', {
        'margin_top': (-1, 'em'),
        'margin_right': 'auto',
        'margin_bottom': (20, '%'),
        'margin_left': 'auto',
    }),
    ('padding: 1em 0', {
        'padding_top': (1, 'em'),
        'padding_right': (0, None),
        'padding_bottom': (1, 'em'),
        'padding_left': (0, None),
    }),
    ('padding: 1em 0 2%', {
        'padding_top': (1, 'em'),
        'padding_right': (0, None),
        'padding_bottom': (2, '%'),
        'padding_left': (0, None),
    }),
    ('padding: 1em 0 2em 5px', {
        'padding_top': (1, 'em'),
        'padding_right': (0, None),
        'padding_bottom': (2, 'em'),
        'padding_left': (5, 'px'),
    }),
))
def test_four_sides(rule, result):
    assert expand_to_dict(rule) == result


@assert_no_logs
def test_four_sides_warning():
    assert expand_to_dict(
        'padding: 1 2 3 4 5', 'Expected 1 to 4 token components got 5') == {}


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'margin: rgb(0, 0, 0)',
    'padding: auto',
    'padding: -12px',
    'border-width: -3em',
    'border-width: 12%',
))
def test_four_sides_invalid(rule):
    assert_invalid(rule)


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('border-top: 3px dotted red', {
        'border_top_width': (3, 'px'),
        'border_top_style': 'dotted',
        'border_top_color': (1, 0, 0, 1),  # red
    }),
    ('border-top: 3px dotted', {
        'border_top_width': (3, 'px'),
        'border_top_style': 'dotted',
    }),
    ('border-top: 3px red', {
        'border_top_width': (3, 'px'),
        'border_top_color': (1, 0, 0, 1),  # red
    }),
    ('border-top: solid', {'border_top_style': 'solid'}),
    ('border: 6px dashed lime', {
        'border_top_width': (6, 'px'),
        'border_top_style': 'dashed',
        'border_top_color': (0, 1, 0, 1),  # lime

        'border_left_width': (6, 'px'),
        'border_left_style': 'dashed',
        'border_left_color': (0, 1, 0, 1),  # lime

        'border_bottom_width': (6, 'px'),
        'border_bottom_style': 'dashed',
        'border_bottom_color': (0, 1, 0, 1),  # lime

        'border_right_width': (6, 'px'),
        'border_right_style': 'dashed',
        'border_right_color': (0, 1, 0, 1),  # lime
    }),
))
def test_borders(rule, result):
    assert expand_to_dict(rule) == result


@assert_no_logs
def test_borders_invalid():
    assert_invalid('border: 6px dashed left')


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('list-style: inherit', {
        'list_style_position': 'inherit',
        'list_style_image': 'inherit',
        'list_style_type': 'inherit',
    }),
    ('list-style: url(../bar/lipsum.png)', {
        'list_style_image': ('url', 'https://weasyprint.org/bar/lipsum.png'),
    }),
    ('list-style: square', {
        'list_style_type': 'square',
    }),
    ('list-style: circle inside', {
        'list_style_position': 'inside',
        'list_style_type': 'circle',
    }),
    ('list-style: none circle inside', {
        'list_style_position': 'inside',
        'list_style_image': ('none', None),
        'list_style_type': 'circle',
    }),
    ('list-style: none inside none', {
        'list_style_position': 'inside',
        'list_style_image': ('none', None),
        'list_style_type': 'none',
    }),
    ('list-style: inside special none', {
        'list_style_position': 'inside',
        'list_style_image': ('none', None),
        'list_style_type': 'special',
    }),
))
def test_list_style(rule, result):
    assert expand_to_dict(rule) == result


@assert_no_logs
def test_list_style_warning():
    assert_invalid(
        'list-style: circle disc',
        'got multiple type values in a list-style shorthand')


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'list-style: none inside none none',
    'list-style: 1px',
))
def test_list_style_invalid(rule):
    assert_invalid(rule)


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('red', {'background_color': (1, 0, 0, 1)}),
    ('url(lipsum.png)', {
        'background_image': [
            ('url', 'https://weasyprint.org/foo/lipsum.png')]}),
    ('no-repeat', {
        'background_repeat': [('no-repeat', 'no-repeat')]}),
    ('fixed', {
        'background_attachment': ['fixed']}),
    ('repeat no-repeat fixed', {
        'background_repeat': [('repeat', 'no-repeat')],
        'background_attachment': ['fixed']}),
    ('inherit', {
        'background_repeat': 'inherit',
        'background_attachment': 'inherit',
        'background_image': 'inherit',
        'background_position': 'inherit',
        'background_size': 'inherit',
        'background_clip': 'inherit',
        'background_origin': 'inherit',
        'background_color': 'inherit'}),
    ('top', {
        'background_position': [('left', (50, '%'), 'top', (0, '%'))]}),
    ('top right', {
        'background_position': [('left', (100, '%'), 'top', (0, '%'))]}),
    ('top right 20px', {
        'background_position': [('right', (20, 'px'), 'top', (0, '%'))]}),
    ('top 1% right 20px', {
        'background_position': [('right', (20, 'px'), 'top', (1, '%'))]}),
    ('top no-repeat', {
        'background_repeat': [('no-repeat', 'no-repeat')],
        'background_position': [('left', (50, '%'), 'top', (0, '%'))]}),
    ('top right no-repeat', {
        'background_repeat': [('no-repeat', 'no-repeat')],
        'background_position': [('left', (100, '%'), 'top', (0, '%'))]}),
    ('top right 20px no-repeat', {
        'background_repeat': [('no-repeat', 'no-repeat')],
        'background_position': [('right', (20, 'px'), 'top', (0, '%'))]}),
    ('top 1% right 20px no-repeat', {
        'background_repeat': [('no-repeat', 'no-repeat')],
        'background_position': [('right', (20, 'px'), 'top', (1, '%'))]}),
    ('url(bar) #f00 repeat-y center left fixed', {
        'background_color': (1, 0, 0, 1),
        'background_image': [('url', 'https://weasyprint.org/foo/bar')],
        'background_repeat': [('no-repeat', 'repeat')],
        'background_attachment': ['fixed'],
        'background_position': [('left', (0, '%'), 'top', (50, '%'))]}),
    ('#00f 10% 200px', {
        'background_color': (0, 0, 1, 1),
        'background_position': [('left', (10, '%'), 'top', (200, 'px'))]}),
    ('right 78px fixed', {
        'background_attachment': ['fixed'],
        'background_position': [('left', (100, '%'), 'top', (78, 'px'))]}),
    ('center / cover red', {
        'background_size': ['cover'],
        'background_position': [('left', (50, '%'), 'top', (50, '%'))],
        'background_color': (1, 0, 0, 1)}),
    ('center / auto red', {
        'background_size': [('auto', 'auto')],
        'background_position': [('left', (50, '%'), 'top', (50, '%'))],
        'background_color': (1, 0, 0, 1)}),
    ('center / 42px', {
        'background_size': [((42, 'px'), 'auto')],
        'background_position': [('left', (50, '%'), 'top', (50, '%'))]}),
    ('center / 7% 4em', {
        'background_size': [((7, '%'), (4, 'em'))],
        'background_position': [('left', (50, '%'), 'top', (50, '%'))]}),
    ('red content-box', {
        'background_color': (1, 0, 0, 1),
        'background_origin': ['content-box'],
        'background_clip': ['content-box']}),
    ('red border-box content-box', {
        'background_color': (1, 0, 0, 1),
        'background_origin': ['border-box'],
        'background_clip': ['content-box']}),
    ('border-box red', {
        'background_color': (1, 0, 0, 1),
        'background_origin': ['border-box']}),
    ('url(bar) center, no-repeat', {
        'background_color': (0, 0, 0, 0),
        'background_image': [
            ('url', 'https://weasyprint.org/foo/bar'), ('none', None)],
        'background_position': [
            ('left', (50, '%'), 'top', (50, '%')),
            ('left', (0, '%'), 'top', (0, '%'))],
        'background_repeat': [
            ('repeat', 'repeat'), ('no-repeat', 'no-repeat')]}),
))
def test_background(rule, result):
    expanded = expand_to_dict(f'background: {rule}')
    assert expanded.pop('background_color') == result.pop(
        'background_color', INITIAL_VALUES['background_color'])
    nb_layers = len(expanded['background_image'])
    for name, value in result.items():
        assert expanded.pop(name) == value
    for name, value in expanded.items():
        assert tuple(value) == INITIAL_VALUES[name] * nb_layers


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'red, url(foo)',
    '10px lipsum',
    'content-box red content-box',
))
def test_background_invalid(rule):
    assert_invalid(f'background: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('1px', {
        'border_top_left_radius': ((1, 'px'), (1, 'px')),
        'border_top_right_radius': ((1, 'px'), (1, 'px')),
        'border_bottom_right_radius': ((1, 'px'), (1, 'px')),
        'border_bottom_left_radius': ((1, 'px'), (1, 'px')),
    }),
    ('1px 2em', {
        'border_top_left_radius': ((1, 'px'), (1, 'px')),
        'border_top_right_radius': ((2, 'em'), (2, 'em')),
        'border_bottom_right_radius': ((1, 'px'), (1, 'px')),
        'border_bottom_left_radius': ((2, 'em'), (2, 'em')),
    }),
    ('1px / 2em', {
        'border_top_left_radius': ((1, 'px'), (2, 'em')),
        'border_top_right_radius': ((1, 'px'), (2, 'em')),
        'border_bottom_right_radius': ((1, 'px'), (2, 'em')),
        'border_bottom_left_radius': ((1, 'px'), (2, 'em')),
    }),
    ('1px 3px / 2em 4%', {
        'border_top_left_radius': ((1, 'px'), (2, 'em')),
        'border_top_right_radius': ((3, 'px'), (4, '%')),
        'border_bottom_right_radius': ((1, 'px'), (2, 'em')),
        'border_bottom_left_radius': ((3, 'px'), (4, '%')),
    }),
    ('1px 2em 3%', {
        'border_top_left_radius': ((1, 'px'), (1, 'px')),
        'border_top_right_radius': ((2, 'em'), (2, 'em')),
        'border_bottom_right_radius': ((3, '%'), (3, '%')),
        'border_bottom_left_radius': ((2, 'em'), (2, 'em')),
    }),
    ('1px 2em 3% 4rem', {
        'border_top_left_radius': ((1, 'px'), (1, 'px')),
        'border_top_right_radius': ((2, 'em'), (2, 'em')),
        'border_bottom_right_radius': ((3, '%'), (3, '%')),
        'border_bottom_left_radius': ((4, 'rem'), (4, 'rem')),
    }),
    ('inherit', {
        'border_top_left_radius': 'inherit',
        'border_top_right_radius': 'inherit',
        'border_bottom_right_radius': 'inherit',
        'border_bottom_left_radius': 'inherit',
    }),
))
def test_border_radius(rule, result):
    assert expand_to_dict(f'border-radius: {rule}') == result


@assert_no_logs
@pytest.mark.parametrize('rule, message', (
    ('1px 1px 1px 1px 1px', '1 to 4 token'),
    ('1px 1px 1px 1px 1px / 1px', '1 to 4 token'),
    ('1px / 1px / 1px', 'only one "/"'),
    ('12deg', 'invalid'),
    ('1px 1px 1px 12deg', 'invalid'),
    ('super', 'invalid'),
    ('1px, 1px', 'invalid'),
    ('1px /', 'value after "/"'),
))
def test_border_radius_invalid(rule, message):
    assert_invalid(f'border-radius: {rule}', message)


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('url(border.png) 27', {
        'border_image_source': ('url', 'https://weasyprint.org/foo/border.png'),
        'border_image_slice': ((27, None),),
    }),
    ('url(border.png) 10 / 4 / 2 round stretch', {
        'border_image_source': ('url', 'https://weasyprint.org/foo/border.png'),
        'border_image_slice': ((10, None),),
        'border_image_width': ((4, None),),
        'border_image_outset': ((2, None),),
        'border_image_repeat': (('round', 'stretch')),
    }),
    ('10 // 2', {
        'border_image_slice': ((10, None),),
        'border_image_outset': ((2, None),),
    }),
    ('5.5%', {
        'border_image_slice': ((5.5, '%'),),
    }),
    ('stretch 2 url("border.png")', {
        'border_image_source': ('url', 'https://weasyprint.org/foo/border.png'),
        'border_image_slice': ((2, None),),
        'border_image_repeat': (('stretch',)),
    }),
    ('1/2 round', {
        'border_image_slice': ((1, None),),
        'border_image_width': ((2, None),),
        'border_image_repeat': (('round',)),
    }),
    ('none', {
        'border_image_source': ('none', None),
    }),
))
def test_border_image(rule, result):
    assert expand_to_dict(f'border-image: {rule}') == result


@assert_no_logs
@pytest.mark.parametrize('rule, reason', (
    ('url(border.png) url(border.png)', 'multiple source'),
    ('10 10 10 10 10', 'multiple slice'),
    ('1 / 2 / 3 / 4', 'invalid'),
    ('/1', 'invalid'),
    ('/1', 'invalid'),
    ('round round round', 'invalid'),
    ('-1', 'invalid'),
    ('1 repeat 2', 'multiple slice'),
    ('1% // 1%', 'invalid'),
    ('1 / repeat', 'invalid'),
    ('', 'no value'),
))
def test_border_image_invalid(rule, reason):
    assert_invalid(f'border-image: {rule}', reason)


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('12px My Fancy Font, serif', {
        'font_size': (12, 'px'),
        'font_family': ('My Fancy Font', 'serif'),
    }),
    ('small/1.2 "Some Font", serif', {
        'font_size': 'small',
        'line_height': (1.2, None),
        'font_family': ('Some Font', 'serif'),
    }),
    ('small-caps italic 700 large serif', {
        'font_style': 'italic',
        'font_variant_caps': 'small-caps',
        'font_weight': 700,
        'font_size': 'large',
        'font_family': ('serif',),
    }),
    ('small-caps condensed normal 700 large serif', {
        'font_stretch': 'condensed',
        'font_variant_caps': 'small-caps',
        'font_weight': 700,
        'font_size': 'large',
        'font_family': ('serif',),
    }),
))
def test_font(rule, result):
    assert expand_to_dict(f'font: {rule}') == result


@assert_no_logs
@pytest.mark.parametrize('rule, message', (
    ('menu', 'System fonts are not supported'),
    ('12deg My Fancy Font, serif', 'invalid'),
    ('12px', 'invalid'),
    ('12px/foo serif', 'invalid'),
    ('12px "Invalid" family', 'invalid'),
    ('normal normal normal normal normal large serif', 'invalid'),
    ('normal small-caps italic 700 condensed large serif', 'invalid'),
    ('small-caps italic 700 normal condensed large serif', 'invalid'),
    ('small-caps italic 700 condensed normal large serif', 'invalid'),
    ('normal normal normal normal', 'invalid'),
    ('normal normal normal italic', 'invalid'),
    ('caption', 'System fonts'),
))
def test_font_invalid(rule, message):
    assert_invalid(f'font: {rule}', message)


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('normal', {
        'font_variant_alternates': 'normal',
        'font_variant_caps': 'normal',
        'font_variant_east_asian': 'normal',
        'font_variant_ligatures': 'normal',
        'font_variant_numeric': 'normal',
        'font_variant_position': 'normal',
    }),
    ('none', {
        'font_variant_alternates': 'normal',
        'font_variant_caps': 'normal',
        'font_variant_east_asian': 'normal',
        'font_variant_ligatures': 'none',
        'font_variant_numeric': 'normal',
        'font_variant_position': 'normal',
    }),
    ('historical-forms petite-caps', {
        'font_variant_alternates': 'historical-forms',
        'font_variant_caps': 'petite-caps',
    }),
    ('lining-nums contextual small-caps common-ligatures', {
        'font_variant_ligatures': ('contextual', 'common-ligatures'),
        'font_variant_numeric': ('lining-nums',),
        'font_variant_caps': 'small-caps',
    }),
    ('jis78 ruby proportional-width', {
        'font_variant_east_asian': ('jis78', 'ruby', 'proportional-width'),
    }),
    # CSS2-style font-variant
    ('small-caps', {'font_variant_caps': 'small-caps'}),
))
def test_font_variant(rule, result):
    assert expand_to_dict(f'font-variant: {rule}') == result


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'normal normal',
    '2',
    '""',
    'extra',
    'jis78 jis04',
    'full-width lining-nums ordinal normal',
    'diagonal-fractions stacked-fractions',
    'common-ligatures contextual no-common-ligatures',
    'sub super',
    'slashed-zero slashed-zero',
))
def test_font_variant_invalid(rule):
    assert_invalid(f'font-variant: {rule}')


@assert_no_logs
def test_word_wrap():
    assert expand_to_dict('word-wrap: normal') == {
        'overflow_wrap': 'normal'}
    assert expand_to_dict('word-wrap: break-word') == {
        'overflow_wrap': 'break-word'}
    assert expand_to_dict('word-wrap: inherit') == {
        'overflow_wrap': 'inherit'}
    assert_invalid('word-wrap: none')
    assert_invalid('word-wrap: normal, break-word')


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('auto', {'flex_grow': 1, 'flex_shrink': 1, 'flex_basis': 'auto'}),
    ('none', {'flex_grow': 0, 'flex_shrink': 0, 'flex_basis': 'auto'}),
    ('10', {'flex_grow': 10, 'flex_shrink': 1, 'flex_basis': ZERO_PIXELS}),
    ('2 2', {'flex_grow': 2, 'flex_shrink': 2, 'flex_basis': ZERO_PIXELS}),
    ('2 2 1px', {'flex_grow': 2, 'flex_shrink': 2, 'flex_basis': (1, 'px')}),
    ('2 2 auto', {'flex_grow': 2, 'flex_shrink': 2, 'flex_basis': 'auto'}),
    ('2 auto', {'flex_grow': 2, 'flex_shrink': 1, 'flex_basis': 'auto'}),
    ('0 auto', {'flex_grow': 0, 'flex_shrink': 1, 'flex_basis': 'auto'}),
    ('inherit', {
        'flex_grow': 'inherit',
        'flex_shrink': 'inherit',
        'flex_basis': 'inherit'}),
))
def test_flex(rule, result):
    assert expand_to_dict(f'flex: {rule}') == result


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'auto 0 0 0',
    '1px 2px',
    'auto auto',
    'auto 1 auto',
))
def test_flex_invalid(rule):
    assert_invalid(f'flex: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('column', {'flex_direction': 'column'}),
    ('wrap', {'flex_wrap': 'wrap'}),
    ('wrap column', {'flex_direction': 'column', 'flex_wrap': 'wrap'}),
    ('row wrap', {'flex_direction': 'row', 'flex_wrap': 'wrap'}),
    ('inherit', {'flex_direction': 'inherit', 'flex_wrap': 'inherit'}),
))
def test_flex_flow(rule, result):
    assert expand_to_dict(f'flex-flow: {rule}') == result


@assert_no_logs
@pytest.mark.parametrize('rule', (
    '1px',
    'wrap 1px',
    'row row',
    'wrap nowrap',
    'column wrap nowrap row',
))
def test_flex_flow_invalid(rule):
    assert_invalid(f'flex-flow: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('auto', {'start': 'auto', 'end': 'auto'}),
    ('auto / auto', {'start': 'auto', 'end': 'auto'}),
    ('4', {'start': (None, 4, None), 'end': 'auto'}),
    ('c', {'start': (None, None, 'c'), 'end': (None, None, 'c')}),
    ('4 / -4', {'start': (None, 4, None), 'end': (None, -4, None)}),
    ('c / d', {'start': (None, None, 'c'), 'end': (None, None, 'd')}),
    ('ab / cd 4', {'start': (None, None, 'ab'), 'end': (None, 4, 'cd')}),
    ('ab 2 span', {'start': ('span', 2, 'ab'), 'end': 'auto'}),
))
def test_grid_column_row(rule, result):
    assert expand_to_dict(f'grid-column: {rule}') == dict(
        (f'grid_column_{key}', value) for key, value in result.items())
    assert expand_to_dict(f'grid-row: {rule}') == dict(
        (f'grid_row_{key}', value) for key, value in result.items())


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'auto auto',
    '4 / 2 / c',
    'span',
    '4 / span',
    'c /',
    '/4',
    'col / 2.1',
))
def test_grid_column_row_invalid(rule):
    assert_invalid(f'grid-column: {rule}')
    assert_invalid(f'grid-row: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('auto', {
        'row_start': 'auto', 'row_end': 'auto',
        'column_start': 'auto', 'column_end': 'auto'}),
    ('auto / auto', {
        'row_start': 'auto', 'row_end': 'auto',
        'column_start': 'auto', 'column_end': 'auto'}),
    ('auto / auto / auto', {
        'row_start': 'auto', 'row_end': 'auto',
        'column_start': 'auto', 'column_end': 'auto'}),
    ('auto / auto / auto / auto', {
        'row_start': 'auto', 'row_end': 'auto',
        'column_start': 'auto', 'column_end': 'auto'}),
    ('1/c/2 d/span 2 ab', {
        'row_start': (None, 1, None), 'column_start': (None, None, 'c'),
        'row_end': (None, 2, 'd'), 'column_end': ('span', 2, 'ab')}),
    ('1  /  c', {
        'row_start': (None, 1, None), 'column_start': (None, None, 'c'),
        'row_end': 'auto', 'column_end': (None, None, 'c')}),
    ('a / c 2', {
        'row_start': (None, None, 'a'), 'column_start': (None, 2, 'c'),
        'row_end': (None, None, 'a'), 'column_end': 'auto'}),
    ('a', {
        'row_start': (None, None, 'a'), 'row_end': (None, None, 'a'),
        'column_start': (None, None, 'a'), 'column_end': (None, None, 'a')}),
    ('span 2', {
        'row_start': ('span', 2, None), 'row_end': 'auto',
        'column_start': 'auto', 'column_end': 'auto'}),
))
def test_grid_area(rule, result):
    assert expand_to_dict(f'grid-area: {rule}') == dict(
        (f'grid_{key}', value) for key, value in result.items())


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'auto auto',
    'auto / auto auto',
    '4 / 2 / c / d / e',
    'span',
    '4 / span',
    'c /',
    '/4',
    'c//4',
    '/',
    '1 / 2 / 4 / 0.5',
))
def test_grid_area_invalid(rule):
    assert_invalid(f'grid-area: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('none', {
        'rows': 'none', 'columns': 'none', 'areas': 'none',
    }),
    ('subgrid / [outer-edge] 20px [main-start]', {
        'rows': ('subgrid', ()),
        'columns': (('outer-edge',), (20, 'px'), ('main-start',)),
        'areas': 'none',
    }),
    ('repeat(2, [e] 40px) repeat(5, auto) / subgrid [a] repeat(auto-fill, [b])', {
        'rows': (
            (), ('repeat()', 2, (('e',), (40, 'px'), ())), (),
            ('repeat()', 5, ((), 'auto', ())), ()),
        'columns': ('subgrid', (('a',), ('repeat()', 'auto-fill', (('b',),)))),
        'areas': 'none',
    }),
    # TODO: support last syntax
    # ('[a b] "x y y" [c] [d] "x y y" 1fr [e] / auto 2fr auto', {
    #     'rows': 'none', 'columns': 'none', 'areas': 'none',
    # }),
    # ('[a b c] "x x x" 2fr', {
    #     'rows': 'none', 'columns': 'none', 'areas': 'none',
    # }),
))
def test_grid_template(rule, result):
    assert expand_to_dict(f'grid-template: {rule}') == dict(
        (f'grid_template_{key}', value) for key, value in result.items())

@assert_no_logs
@pytest.mark.parametrize('rule', (
    'none none',
    'auto',
    'subgrid / subgrid / subgrid',
    '[a] 1px [b] / none /',
    '[a] 1px [b] // none',
    '[a] 1px [b] none',
))
def test_grid_template_invalid(rule):
    assert_invalid(f'grid-template: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('none', {
        'template_rows': 'none', 'template_columns': 'none',
        'template_areas': 'none',
        'auto_rows': ('auto',), 'auto_columns': ('auto',),
        'auto_flow': ('row',),
    }),
    ('subgrid / [outer-edge] 20px [main-start]', {
        'template_rows': ('subgrid', ()),
        'template_columns': (('outer-edge',), (20, 'px'), ('main-start',)),
        'template_areas': 'none',
        'auto_rows': ('auto',), 'auto_columns': ('auto',),
        'auto_flow': ('row',),
    }),
    ('repeat(2, [e] 40px) repeat(5, auto) / subgrid [a] repeat(auto-fill, [b])', {
        'template_rows': (
            (), ('repeat()', 2, (('e',), (40, 'px'), ())), (),
            ('repeat()', 5, ((), 'auto', ())), ()),
        'template_columns': ('subgrid', (('a',), ('repeat()', 'auto-fill', (('b',),)))),
        'template_areas': 'none',
        'auto_rows': ('auto',), 'auto_columns': ('auto',),
        'auto_flow': ('row',),
    }),
    ('auto-flow 1fr / 100px', {
        'template_rows': 'none', 'template_columns': ((), (100, 'px'), ()),
        'template_areas': 'none',
        'auto_rows': ((1, 'fr'),), 'auto_columns': ('auto',),
        'auto_flow': ('row',),
    }),
    ('none / dense auto-flow 1fr', {
        'template_rows': 'none', 'template_columns': 'none',
        'template_areas': 'none',
        'auto_rows': ('auto',), 'auto_columns': ((1, 'fr'),),
        'auto_flow': ('column', 'dense'),
    }),
    # TODO: support last grid-template syntax
    # ('[a b] "x y y" [c] [d] "x y y" 1fr [e] / auto 2fr auto', {
    # }),
    # ('[a b c] "x x x" 2fr', {
    # }),
))
def test_grid(rule, result):
    assert expand_to_dict(f'grid: {rule}') == dict(
        (f'grid_{key}', value) for key, value in result.items())


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'none none',
    'auto',
    'subgrid / subgrid / subgrid',
    '[a] 1px [b] / none /',
    '[a] 1px [b] // none',
    '[a] 1px [b] none',
    'none / auto-flow 1fr dense',
    'none / dense 1fr auto-flow',
    '100px auto-flow / none',
    'dense 100px / auto-flow 1fr'
))
def test_grid_invalid(rule):
    assert_invalid(f'grid: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('page-break-after: left', {'break_after': 'left'}),
    ('page-break-before: always', {'break_before': 'page'}),
    ('page-break-after: inherit', {'break_after': 'inherit'}),
    ('page-break-before: inherit', {'break_before': 'inherit'}),
))
def test_page_break(rule, result):
    assert expand_to_dict(rule) == result


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'page-break-after: top',
    'page-break-before: 1px',
))
def test_page_break_invalid(rule):
    assert_invalid(rule)


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('avoid', {'break_inside': 'avoid'}),
    ('inherit', {'break_inside': 'inherit'}),
))
def test_page_break_inside(rule, result):
    assert expand_to_dict(f'page-break-inside: {rule}') == result


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'top',
))
def test_page_break_inside_invalid(rule):
    assert_invalid(f'page-break-inside: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('1em', {'column_width': (1, 'em'), 'column_count': 'auto'}),
    ('auto', {'column_width': 'auto', 'column_count': 'auto'}),
    ('auto auto', {'column_width': 'auto', 'column_count': 'auto'}),
))
def test_columns(rule, result):
    assert expand_to_dict(f'columns: {rule}') == result


@assert_no_logs
@pytest.mark.parametrize('rule, reason', (
    ('1px 2px', 'invalid'),
    ('auto auto auto', 'multiple'),
))
def test_columns_invalid(rule, reason):
    assert_invalid(f'columns: {rule}', reason)


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('none', {
        'max_lines': 'none', 'continue': 'auto', 'block_ellipsis': 'none'}),
    ('2', {
        'max_lines': 2, 'continue': 'discard', 'block_ellipsis': 'auto'}),
    ('3 "…"', {
        'max_lines': 3, 'continue': 'discard',
        'block_ellipsis': ('string', '…')}),
    ('inherit', {
        'max_lines': 'inherit', 'continue': 'inherit',
        'block_ellipsis': 'inherit'}),
))
def test_line_clamp(rule, result):
    assert expand_to_dict(f'line-clamp: {rule}') == result


@assert_no_logs
@pytest.mark.parametrize('rule, reason', (
    ('none none none', 'invalid'),
    ('1px', 'invalid'),
    ('0 "…"', 'invalid'),
    ('1px 2px', 'invalid'),
))
def test_line_clamp_invalid(rule, reason):
    assert_invalid(f'line-clamp: {rule}', reason)


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('start', {'text_align_all': 'start', 'text_align_last': 'start'}),
    ('right', {'text_align_all': 'right', 'text_align_last': 'right'}),
    ('justify', {'text_align_all': 'justify', 'text_align_last': 'start'}),
    ('justify-all', {
        'text_align_all': 'justify', 'text_align_last': 'justify'}),
    ('inherit', {'text_align_all': 'inherit', 'text_align_last': 'inherit'}),
))
def test_text_align(rule, result):
    assert expand_to_dict(f'text-align: {rule}') == result


@assert_no_logs
@pytest.mark.parametrize('rule, reason', (
    ('none', 'invalid'),
    ('start end', 'invalid'),
    ('1', 'invalid'),
    ('left left', 'invalid'),
    ('top', 'invalid'),
    ('"right"', 'invalid'),
    ('1px', 'invalid'),
))
def test_text_align_invalid(rule, reason):
    assert_invalid(f'text-align: {rule}', reason)
