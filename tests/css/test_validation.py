"""Test validation of properties."""

from math import pi

import pytest
import tinycss2

from weasyprint.css import preprocess_declarations
from weasyprint.css.validation.properties import PROPERTIES
from weasyprint.images import LinearGradient, RadialGradient

from ..testing_utils import assert_no_logs, capture_logs


def get_value(css, expected_error=None):
    declarations = tinycss2.parse_blocks_contents(css)

    with capture_logs() as logs:
        base_url = 'https://weasyprint.org/foo/'
        declarations = list(preprocess_declarations(base_url, declarations))

    if expected_error:
        assert len(logs) == 1
        assert expected_error in logs[0]
    else:
        assert not logs

    if declarations:
        assert len(declarations) == 1
        return declarations[0][1]


def get_default_value(values, index, default):
    if index > len(values) - 1:
        return default
    return values[index] or default


def assert_invalid(css, message='invalid'):
    assert get_value(css, message) is None


@assert_no_logs
def test_not_print():
    assert_invalid('volume: 42', 'does not apply for the print media')


@assert_no_logs
def test_unstable_prefix():
    assert get_value(
        '-weasy-max-lines: 3',
        'prefixes on unstable attributes are deprecated') == 3


@assert_no_logs
def test_normal_prefix():
    assert_invalid(
        '-weasy-display: block', 'prefix on this attribute is not supported')


@assert_no_logs
def test_unknown_prefix():
    assert_invalid('-unknown-display: block', 'prefixed selectors are ignored')


@assert_no_logs
@pytest.mark.parametrize('prop', PROPERTIES)
def test_empty_property_value(prop):
    assert_invalid(f'{prop}:', message='Ignored')


@assert_no_logs
@pytest.mark.parametrize('rule, value', (
    ('1px, 3em, auto, auto', ((1, 'px'), (3, 'em'), 'auto', 'auto')),
    ('1px, 3em, auto auto', ((1, 'px'), (3, 'em'), 'auto', 'auto')),
    ('1px 3em auto 1px', ((1, 'px'), (3, 'em'), 'auto', (1, 'px'))),
))
def test_clip(rule, value):
    assert get_value(f'clip: rect({rule})') == value


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'clip: square(1px, 3em, auto, auto)',
    'clip: rect(1px, 3em, auto)',
    'clip: rect(1px, 3em / auto)',
))
def test_clip_invalid(rule):
    assert_invalid(rule)


@assert_no_logs
@pytest.mark.parametrize('rule, value', (
    ('counter-reset: foo bar 2 baz', (('foo', 0), ('bar', 2), ('baz', 0))),
    ('counter-increment: foo bar 2 baz', (('foo', 1), ('bar', 2), ('baz', 1))),
    ('counter-reset: foo', (('foo', 0),)),
    ('counter-set: FoO', (('FoO', 0),)),
    ('counter-increment: foo bAr 2 Bar', (('foo', 1), ('bAr', 2), ('Bar', 1))),
    ('counter-reset: none', ()),
))
def test_counters(rule, value):
    assert get_value(rule) == value


@pytest.mark.parametrize('rule, warning', (
    ('counter-reset: foo initial', 'Invalid counter name: initial.'),
    ('counter-reset: foo none', 'Invalid counter name: none.'),
))
def test_counters_warning(rule, warning):
    assert_invalid(rule, warning)


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'counter-reset: foo 3px',
    'counter-reset: 3',
))
def test_counters_invalid(rule):
    assert_invalid(rule)


@assert_no_logs
@pytest.mark.parametrize('rule, value', (
    ('letter-spacing: normal', 'normal'),
    ('letter-spacing: 3px', (3, 'px')),
    ('word-spacing: normal', 'normal'),
    ('word-spacing: 3px', (3, 'px')),
))
def test_spacing(rule, value):
    assert get_value(rule) == value


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'letter-spacing: 3',
    'word-spacing: 3',
))
def test_spacing_invalid(rule):
    assert_invalid(rule)


@assert_no_logs
@pytest.mark.parametrize('rule, value', (
    ('none', 'none'),
    ('overline', {'overline'}),
    ('overline blink line-through', {'blink', 'line-through', 'overline'}),
))
def test_text_decoration_line(rule, value):
    assert get_value(f'text-decoration-line: {rule}') == value


@assert_no_logs
@pytest.mark.parametrize('rule, value', (
    ('solid', 'solid'),
    ('double', 'double'),
    ('dotted', 'dotted'),
    ('dashed', 'dashed'),
))
def test_text_decoration_style(rule, value):
    assert get_value(f'text-decoration-style: {rule}') == value


@assert_no_logs
@pytest.mark.parametrize('rule, value', (
    ('200px', ((200, 'px'), (200, 'px'))),
    ('200px 300pt', ((200, 'px'), (300, 'pt'))),
    ('auto', ((210, 'mm'), (297, 'mm'))),
    ('portrait', ((210, 'mm'), (297, 'mm'))),
    ('landscape', ((297, 'mm'), (210, 'mm'))),
    ('A3 portrait', ((297, 'mm'), (420, 'mm'))),
    ('A3 landscape', ((420, 'mm'), (297, 'mm'))),
    ('portrait A3', ((297, 'mm'), (420, 'mm'))),
    ('landscape A3', ((420, 'mm'), (297, 'mm'))),
))
def test_size(rule, value):
    assert get_value(f'size: {rule}') == value


@pytest.mark.parametrize('rule', (
    'A3 landscape A3',
    'A12',
    'foo',
    'foo bar',
    '20%',
))
def test_size_invalid(rule):
    assert_invalid(f'size: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, value', (
    ('none', ()),
    ('translate(6px) rotate(90deg)', (
        ('translate', ((6, 'px'), (0, 'px'))), ('rotate', pi / 2))),
    ('translate(-4px, 0)', (('translate', ((-4, 'px'), (0, None))),)),
    ('translate(6px, 20%)', (('translate', ((6, 'px'), (20, '%'))),)),
    ('scale(2)', (('scale', (2, 2)),)),
    ('translate(6px 20%)', (('translate', ((6, 'px'), (20, '%'))),)),
))
def test_transform(rule, value):
    assert get_value(f'transform: {rule}') == value


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'lipsumize(6px)',
    'foo',
    'scale(2) foo',
    '6px',
))
def test_transform_invalid(rule):
    assert_invalid(f'transform: {rule}')


@pytest.mark.parametrize('rule', (
    'inexistent-gradient(blue, green)',
))
def test_background_image_invalid(rule):
    assert_invalid(f'background-image: {rule}')


@pytest.mark.parametrize('rule, value', (
    # One token, vertical
    ('top', (('left', (50, '%'), 'top', (0, '%')),)),
    ('bottom', (('left', (50, '%'), 'top', (100, '%')),)),

    # Three tokens
    ('center top 10%', (('left', (50, '%'), 'top', (10, '%')),)),
    ('top 10% center', (('left', (50, '%'), 'top', (10, '%')),)),
    ('center bottom 10%', (('left', (50, '%'), 'bottom', (10, '%')),)),
    ('bottom 10% center', (('left', (50, '%'), 'bottom', (10, '%')),)),

    ('right top 10%', (('right', (0, '%'), 'top', (10, '%')),)),
    ('top 10% right', (('right', (0, '%'), 'top', (10, '%')),)),
    ('right bottom 10%', (('right', (0, '%'), 'bottom', (10, '%')),)),
    ('bottom 10% right', (('right', (0, '%'), 'bottom', (10, '%')),)),

    ('center left 10%', (('left', (10, '%'), 'top', (50, '%')),)),
    ('left 10% center', (('left', (10, '%'), 'top', (50, '%')),)),
    ('center right 10%', (('right', (10, '%'), 'top', (50, '%')),)),
    ('right 10% center', (('right', (10, '%'), 'top', (50, '%')),)),

    ('bottom left 10%', (('left', (10, '%'), 'bottom', (0, '%')),)),
    ('left 10% bottom', (('left', (10, '%'), 'bottom', (0, '%')),)),
    ('bottom right 10%', (('right', (10, '%'), 'bottom', (0, '%')),)),
    ('right 10% bottom', (('right', (10, '%'), 'bottom', (0, '%')),)),

    # Four tokens
    ('left 10% bottom 3px', (('left', (10, '%'), 'bottom', (3, 'px')),)),
    ('bottom 3px left 10%', (('left', (10, '%'), 'bottom', (3, 'px')),)),
    ('right 10% top 3px', (('right', (10, '%'), 'top', (3, 'px')),)),
    ('top 3px right 10%', (('right', (10, '%'), 'top', (3, 'px')),)),
    *tuple(
        (css_x, (('left', val_x, 'top', (50, '%')),))
        for css_x, val_x in (
                ('left', (0, '%')), ('center', (50, '%')), ('right', (100, '%')),
                ('4.5%', (4.5, '%')), ('12px', (12, 'px')))
    ),
    *tuple(
        (f'{css_x} {css_y}', (('left', val_x, 'top', val_y),))
        for css_x, val_x in (
                ('left', (0, '%')), ('center', (50, '%')), ('right', (100, '%')),
                ('4.5%', (4.5, '%')), ('12px', (12, 'px')))
        for css_y, val_y in (
                ('top', (0, '%')), ('center', (50, '%')), ('bottom', (100, '%')),
                ('7%', (7, '%')), ('1.5px', (1.5, 'px')))
    ),
))
def test_background_position(rule, value):
    assert get_value(f'background-position: {rule}') == value


@pytest.mark.parametrize('rule', (
    '10px lipsum',
    'left center 3px',
    '3px left',
    'bottom 4%',
    'bottom top'
))
def test_background_position_invalid(rule):
    assert_invalid(f'background-position: {rule}')


@pytest.mark.parametrize('rule', (
    ('"My" Font, serif'),
    ('"My" "Font", serif'),
    ('"My", 12pt, serif'),
))
def test_font_family_invalid(rule):
    assert_invalid(f'font-family: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, value', (
    ('1px', (1, 'px')),
    ('1.1%', (1.1, '%')),
    ('1em', (1, 'em')),
    ('1', (1, None)),
    ('1.3', (1.3, None)),
    ('-0', (0, None)),
    ('0px', (0, 'px')),
))
def test_line_height(rule, value):
    assert get_value(f'line-height: {rule}') == value


@pytest.mark.parametrize('rule', (
    '1deg',
    '-1px',
    '-1',
    '-0.5%',
    '1px 1px',
))
def test_line_height_invalid(rule):
    assert_invalid(f'line-height: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'symbols()',
    'symbols(cyclic)',
    'symbols(symbolic)',
    'symbols(fixed)',
    'symbols(alphabetic "a")',
    'symbols(numeric "1")',
    'symbols(test "a" "b")',
    'symbols(fixed symbolic "a" "b")',
))
def test_list_style_type_invalid(rule):
    assert_invalid(f'list-style-type: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, value', (
    ('none', 'none'),
    ('from-image', 'from-image'),
    ('90deg', (pi / 2, False)),
    ('30deg', (pi / 6, False)),
    ('180deg flip', (pi, True)),
    ('0deg flip', (0, True)),
    ('flip 90deg', (pi / 2, True)),
    ('flip', (0, True)),
))
def test_image_orientation(rule, value):
    assert get_value(f'image-orientation: {rule}') == value


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'none none',
    'unknown',
    'none flip',
    'from-image flip',
    '10',
    '10 flip',
    'flip 10',
    'flip flip',
    '90deg flop',
    '90deg 180deg',
))
def test_image_orientation_invalid(rule):
    assert_invalid(f'image-orientation: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, value', (
    ('1', ((1, None),)),
    ('1 2    3 4', ((1, None), (2, None), (3, None), (4, None))),
    ('50% 1000.1 0', ((50, '%'), (1000.1, None), (0, None))),
    ('1% 2% 3% 4%', ((1, '%'), (2, '%'), (3, '%'), (4, '%'))),
    ('fill 10% 20', ('fill', (10, '%'), (20, None))),
    ('0 1 0.5 fill', ((0, None), (1, None), (0.5, None), 'fill')),
))
def test_border_image_slice(rule, value):
    assert get_value(f'border-image-slice: {rule}') == value


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'none',
    '1, 2',
    '-10',
    '-10%',
    '1 2 3 -10%',
    '-0.3',
    '1 fill 2',
    'fill 1 2 3 fill',
))
def test_border_image_slice_invalid(rule):
    assert_invalid(f'border-image-slice: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, value', (
    ('1', ((1, None),)),
    ('1 2    3 4', ((1, None), (2, None), (3, None), (4, None))),
    ('50% 1000.1 0', ((50, '%'), (1000.1, None), (0, None))),
    ('1% 2px 3em 4', ((1, '%'), (2, 'px'), (3, 'em'), (4, None))),
    ('auto', ('auto',)),
    ('1 auto', ((1, None), 'auto')),
    ('auto auto', ('auto', 'auto')),
    ('auto auto auto 2', ('auto', 'auto', 'auto', (2, None))),
))
def test_border_image_width(rule, value):
    assert get_value(f'border-image-width: {rule}') == value


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'none',
    '1, 2',
    '1 -2',
    '-10',
    '-10%',
    '1px 2px 3px -10%',
    '-3px',
    'auto auto auto auto auto',
    '1 2 3 4 5',
))
def test_border_image_width_invalid(rule):
    assert_invalid(f'border-image-width: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, value', (
    ('1', ((1, None),)),
    ('1 2    3 4', ((1, None), (2, None), (3, None), (4, None))),
    ('50px 1000.1 0', ((50, 'px'), (1000.1, None), (0, None))),
    ('1in 2px 3em 4', ((1, 'in'), (2, 'px'), (3, 'em'), (4, None))),
))
def test_border_image_outset(rule, value):
    assert get_value(f'border-image-outset: {rule}') == value


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'none',
    'auto',
    '1, 2',
    '-10',
    '1 -2',
    '10%',
    '1px 2px 3px -10px',
    '-3px',
    '1 2 3 4 5',
))
def test_border_image_outset_invalid(rule):
    assert_invalid(f'border-image-outset: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, value', (
    ('stretch', ('stretch',)),
    ('repeat repeat', ('repeat', 'repeat')),
    ('round     space', ('round', 'space')),
))
def test_border_image_repeat(rule, value):
    assert get_value(f'border-image-repeat: {rule}') == value


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'none',
    'test',
    'round round round',
    'stretch space round',
    'repeat test',
))
def test_border_image_repeat_invalid(rule):
    assert_invalid(f'border-image-repeat: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, value', (
    ('test content(text)', (('test', (('content()', 'text'),)),)),
    ('test content(before)', (('test', (('content()', 'before'),)),)),
    ('test "string"', (('test', (('string', 'string'),)),)),
    ('test1 "string", test2 "string"', (
        ('test1', (('string', 'string'),)),
        ('test2', (('string', 'string'),)))),
    ('test attr(class)', (('test', (('attr()', ('class', 'string', '')),)),)),
    ('test counter(count)', (
        ('test', (('counter()', ('count', 'decimal')),)),)),
    ('test counter(count, upper-roman)', (
        ('test', (('counter()', ('count', 'upper-roman')),)),)),
    ('test counters(count, ".")', (
        ('test', (('counters()', ('count', '.', 'decimal')),)),)),
    ('test counters(count, ".", upper-roman)', (
        ('test', (('counters()', ('count', '.', 'upper-roman')),)),)),
    ('test content(text) "string" attr(title) attr(title) counter(count)', (
        ('test', (
            ('content()', 'text'), ('string', 'string'),
            ('attr()', ('title', 'string', '')),
            ('attr()', ('title', 'string', '')),
            ('counter()', ('count', 'decimal')))),)),
))
def test_string_set(rule, value):
    assert get_value(f'string-set: {rule}') == value


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'test',
    'test test1',
    'test content(test)',
    'test unknown()',
    'test attr(id, class)',
))
def test_string_set_invalid(rule):
    assert_invalid(f'string-set: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, value', (
    ('normal', 'normal'),
    ('break-word', 'break-word'),
    ('inherit', 'inherit'),
))
def test_overflow_wrap(rule, value):
    assert get_value(f'overflow-wrap: {rule}') == value


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'none',
    'normal, break-word',
))
def test_overflow_wrap_invalid(rule):
    assert_invalid(f'overflow-wrap: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, value', (
    ('blue', ()),
    ('red', (None, ((1, 0, 0, 1),))),
    ('blue 1%, lime,red 2em ', (
        None,
        ((0, 0, 1, 1), (0, 1, 0, 1), (1, 0, 0, 1)),
        ((1, '%'), None, (2, 'em')))),
    ('18deg, blue', (('angle', pi / 10),)),
    ('4rad, blue', (('angle', 4),)),
    ('.25turn, blue', (('angle', pi / 2),)),
    ('100grad, blue', (('angle', pi / 2),)),
    ('12rad, blue 1%, lime,red 2em ', (
        ('angle', 12),
        ((0, 0, 1, 1), (0, 1, 0, 1), (1, 0, 0, 1)),
        ((1, '%'), None, (2, 'em')))),
    ('to top, blue', (('angle', 0),)),
    ('to right, blue', (('angle', pi / 2),)),
    ('to bottom, blue', (('angle', pi),)),
    ('to left, blue', (('angle', pi * 3 / 2),)),
    ('to right, blue 1%, lime,red 2em ', (
        ('angle', pi / 2),
        ((0, 0, 1, 1), (0, 1, 0, 1), (1, 0, 0, 1)),
        ((1, '%'), None, (2, 'em')))),
    ('to top left, blue', (('corner', 'top_left'),)),
    ('to left top, blue', (('corner', 'top_left'),)),
    ('to top right, blue', (('corner', 'top_right'),)),
    ('to right top, blue', (('corner', 'top_right'),)),
    ('to bottom left, blue', (('corner', 'bottom_left'),)),
    ('to left bottom, blue', (('corner', 'bottom_left'),)),
    ('to bottom right, blue', (('corner', 'bottom_right'),)),
    ('to right bottom, blue', (('corner', 'bottom_right'),)),
))
def test_linear_gradient(rule, value):
    direction = get_default_value(value, 0, ('angle', pi))
    colors = get_default_value(value, 1, ((0, 0, 1, 1),))
    stop_positions = get_default_value(value, 2, (None,))
    for repeating, prefix in ((False, ''), (True, 'repeating-')):
        (type_, image), = get_value(
            f'background-image: {prefix}linear-gradient({rule})')
        assert type_ == 'linear-gradient'
        assert isinstance(image, LinearGradient)
        assert image.repeating == repeating
        assert image.direction_type == direction[0]
        if isinstance(image.direction, str):
            image.direction == direction[1]
        else:
            assert image.direction == pytest.approx(direction[1])
        assert image.colors == tuple(colors)
        assert image.stop_positions == tuple(stop_positions)


@assert_no_logs
@pytest.mark.parametrize('rule', (
    ' ',
    '1% blue',
    'blue 10deg',
    'blue 4',
    'soylent-green 4px',
    'red 4px 2px',
    '18deg',
    '10arc-minutes, blue',
    '10px, blue',
    'to 90deg, blue',
    'to the top, blue',
    'to up, blue',
    'into top, blue',
    'top, blue',
    'to bottom up, blue',
    'bottom left, blue',
))
def test_linear_gradient_invalid(rule):
    assert_invalid(f'background-image: linear-gradient({rule})')
    assert_invalid(f'background-image: repeating-linear-gradient({rule})')


@assert_no_logs
@pytest.mark.parametrize('rule, value', (
    ('blue', ()),
    ('red', (None, None, None, ((1, 0, 0, 1),))),
    ('blue 1%, lime,red 2em ', (
        None, None, None, ((0, 0, 1, 1), (0, 1, 0, 1), (1, 0, 0, 1)),
        ((1, '%'), None, (2, 'em')))),
    ('circle, blue', ('circle',)),
    ('ellipse, blue', ()),
    ('ellipse closest-corner, blue', (
        'ellipse', ('keyword', 'closest-corner'))),
    ('circle closest-side, blue', (
        'circle', ('keyword', 'closest-side'))),
    ('farthest-corner circle, blue', (
        'circle', ('keyword', 'farthest-corner'))),
    ('farthest-side, blue', (None, (('keyword', 'farthest-side')))),
    ('5ch, blue', ('circle', ('explicit', ((5, 'ch'), (5, 'ch'))))),
    ('5ch circle, blue', ('circle', ('explicit', ((5, 'ch'), (5, 'ch'))))),
    ('circle 5ch, blue', ('circle', ('explicit', ((5, 'ch'), (5, 'ch'))))),
    ('10px 50px, blue', (None, ('explicit', ((10, 'px'), (50, 'px'))))),
    ('10px 50px ellipse, blue', (
        None, ('explicit', ((10, 'px'), (50, 'px'))))),
    ('ellipse 10px 50px, blue', (
        None, ('explicit', ((10, 'px'), (50, 'px'))))),
    ('10px 50px, blue', (
        None, ('explicit', ((10, 'px'), (50, 'px'))))),
    ('at top 10% right, blue', (
        None, None, ('right', (0, '%'), 'top', (10, '%')))),
    ('circle at bottom, blue', (
        'circle', None, ('left', (50, '%'), 'top', (100, '%')))),
    ('circle at 10px, blue', (
        'circle', None, ('left', (10, 'px'), 'top', (50, '%')))),
    ('closest-side circle at right 5em, blue', (
        'circle', ('keyword', 'closest-side'),
        ('left', (100, '%'), 'top', (5, 'em')))),
))
def test_radial_gradient(rule, value):
    shape = get_default_value(value, 0, 'ellipse')
    size = get_default_value(value, 1, ('keyword', 'farthest-corner'))
    center = get_default_value(value, 2, ('left', (50, '%'), 'top', (50, '%')))
    colors = get_default_value(value, 3, ((0, 0, 1, 1),))
    stop_positions = get_default_value(value, 4, (None,))
    for repeating, prefix in ((False, ''), (True, 'repeating-')):
        (type_, image), = get_value(
            f'background-image: {prefix}radial-gradient({rule})')
        assert type_ == 'radial-gradient'
        assert isinstance(image, RadialGradient)
        assert image.repeating == repeating
        assert image.shape == shape
        assert image.size_type == size[0]
        assert image.size == size[1]
        assert image.center == center
        assert image.colors == tuple(colors)
        assert image.stop_positions == tuple(stop_positions)


@assert_no_logs
@pytest.mark.parametrize('rule', (
    ' ',
    '1% blue',
    'blue 10deg',
    'blue 4',
    'soylent-green 4px',
    'red 4px 2px',
    'circle',
    'square, blue',
    'closest-triangle, blue',
    'center, blue',
    'ellipse 5ch',
    '5ch ellipse',
    'circle 10px 50px, blue',
    '10px 50px circle, blue',
    '10%, blue',
    '10% circle, blue',
    'circle 10%, blue',
    'at appex, blue',
))
def test_radial_gradient_invalid(rule):
    assert_invalid(f'background-image: radial-gradient({rule})')
    assert_invalid(f'background-image: repeating-radial-gradient({rule})')


@assert_no_logs
@pytest.mark.parametrize('rule, value', (
    ('40px', ((40, 'px'),)),
    ('2fr', ((2, 'fr'),)),
    ('18%', ((18, '%'),)),
    ('auto', ('auto',)),
    ('min-content', ('min-content',)),
    ('max-content', ('max-content',)),
    ('fit-content(20%)', (('fit-content()', (20, '%')),)),
    ('minmax(20px, 25px)', (('minmax()', (20, 'px'), (25, 'px')),)),
    ('minmax(min-content, max-content)',
     (('minmax()', 'min-content', 'max-content'),)),
    ('min-content max-content', ('min-content', 'max-content')),
))
def test_grid_auto_columns_rows(rule, value):
    assert get_value(f'grid-auto-columns: {rule}') == value
    assert get_value(f'grid-auto-rows: {rule}') == value


@assert_no_logs
@pytest.mark.parametrize('rule', (
    '40',
    'coucou',
    'fit-content',
    'fit-content(min-content)',
    'minmax(40px)',
    'minmax(2fr, 1fr)',
    '1fr 1fr coucou',
    'fit-content()',
    'fit-content(2%, 18%)',
))
def test_grid_auto_columns_rows_invalid(rule):
    assert_invalid(f'grid-auto-columns: {rule}')
    assert_invalid(f'grid-auto-rows: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, value', (
    ('row', ('row',)),
    ('column', ('column',)),
    ('row dense', ('row', 'dense')),
    ('column dense', ('column', 'dense')),
    ('dense row', ('dense', 'row')),
    ('dense column', ('dense', 'column')),
    ('dense', ('dense', 'row')),
))
def test_grid_auto_flow(rule, value):
    assert get_value(f'grid-auto-flow: {rule}') == value


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'row row',
    'column column',
    'dense dense',
    'coucou',
    'row column',
    'column row',
    'row coucou',
    'column coucou',
    'coucou row',
    'coucou column',
    'row column dense',
))
def test_grid_auto_flow_invalid(rule):
    assert_invalid(f'grid-auto-flow: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, value', (
    ('none', 'none'),
    ('subgrid', ('subgrid', ())),
    ('subgrid [a] repeat(auto-fill, [b]) [c]',
     ('subgrid', (('a',), ('repeat()', 'auto-fill', (('b',),)), ('c',)))),
    ('subgrid [a] [a] [a] [a] repeat(auto-fill, [b]) [c] [c]',
     ('subgrid', (('a',), ('a',), ('a',), ('a',),
      ('repeat()', 'auto-fill', (('b',),)), ('c',), ('c',)))),
    ('subgrid [] [a]', ('subgrid', ((), ('a',)))),
    ('subgrid [a] [b] [c] [d] [e] [f]',
     ('subgrid', (('a',), ('b',), ('c',), ('d',), ('e',), ('f',)))),
    ('[outer-edge] 20px [main-start] 1fr [center] 1fr max-content [main-end]',
     (('outer-edge',), (20, 'px'), ('main-start',), (1, 'fr'), ('center',),
      (1, 'fr'), (), 'max-content', ('main-end',))),
    ('repeat(auto-fill, minmax(25ch, 1fr))',
     ((), ('repeat()', 'auto-fill', (
         (), ('minmax()', (25, 'ch'), (1, 'fr')), ())), ())),
    ('[a] auto [b] minmax(min-content, 1fr) [b c d] '
     'repeat(2, [e] 40px) repeat(5, auto)',
     (('a',), 'auto', ('b',), ('minmax()', 'min-content', (1, 'fr')),
      ('b', 'c', 'd'), ('repeat()', 2, (('e',), (40, 'px'), ())),
      (), ('repeat()', 5, ((), 'auto', ())), ())),
))
def test_grid_template_columns_rows(rule, value):
    assert get_value(f'grid-template-columns: {rule}') == value
    assert get_value(f'grid-template-rows: {rule}') == value


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'coucou',
    'subgrid subgrid',
    'subgrid coucou',
    'subgrid [coucou] repeat(0, [wow])',
    'subgrid [coucou] repeat(auto-fit [wow])',
    'fit-content(18%) repeat(auto-fill, 15em)',
    '[coucou] [wow]',
))
def test_grid_template_columns_rows_invalid(rule):
    assert_invalid(f'grid-template-columns: {rule}')
    assert_invalid(f'grid-template-rows: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, value', (
    ('none', 'none'),
    ('"head head" "nav main" "foot ...."',
     (('head', 'head'), ('nav', 'main'), ('foot', None))),
    ('"title board" "stats board"',
     (('title', 'board'), ('stats', 'board'))),
    ('". a" "b a" ".a"',
     ((None, 'a'), ('b', 'a'), (None, 'a'))),
))
def test_grid_template_areas(rule, value):
    assert get_value(f'grid-template-areas: {rule}') == value


@assert_no_logs
@pytest.mark.parametrize('rule', (
    '"head head coucou" "nav main" "foot ...."',
    '". a" "b c" ". a"',
    '". a" "b a" "a a"',
    '"a a a a" "a b b a" "a a a a"',
    '" "',
))
def test_grid_template_areas_invalid(rule):
    assert_invalid(f'grid-template-areas: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, value', (
    ('auto', 'auto'),
    ('4', (None, 4, None)),
    ('C', (None, None, 'c')),
    ('4 c', (None, 4, 'c')),
    ('col -4', (None, -4, 'col')),
    ('span c 4', ('span', 4, 'c')),
    ('span 4 c', ('span', 4, 'c')),
    ('4 span c', ('span', 4, 'c')),
    ('super 4 span', ('span', 4, 'super')),
))
def test_grid_line(rule, value):
    assert get_value(f'grid-row-start: {rule}') == value
    assert get_value(f'grid-row-end: {rule}') == value
    assert get_value(f'grid-column-start: {rule}') == value
    assert get_value(f'grid-column-end: {rule}') == value


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'span',
    '0',
    '1.1',
    'span 0',
    'span -1',
    'span 2.1',
    'span auto',
    'auto auto',
    '-4 cOL span',
    'span 1.1 col',
))
def test_grid_line_invalid(rule):
    assert_invalid(f'grid-row-start: {rule}')
    assert_invalid(f'grid-row-end: {rule}')
    assert_invalid(f'grid-column-start: {rule}')
    assert_invalid(f'grid-column-end: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, value', (
    ('normal', ('normal',)),
    ('baseline', ('first', 'baseline')),
    ('first baseline', ('first', 'baseline')),
    ('last baseline', ('last', 'baseline')),
    ('baseline last', ('baseline', 'last')),
    ('space-between', ('space-between',)),
    ('space-around', ('space-around',)),
    ('space-evenly', ('space-evenly',)),
    ('stretch', ('stretch',)),
    ('center', ('center',)),
    ('start', ('start',)),
    ('end', ('end',)),
    ('flex-start', ('flex-start',)),
    ('flex-end', ('flex-end',)),
    ('safe center', ('safe', 'center')),
    ('unsafe start', ('unsafe', 'start')),
    ('safe end', ('safe', 'end')),
    ('safe flex-start', ('safe', 'flex-start')),
    ('unsafe flex-start', ('unsafe', 'flex-start')),
))
def test_align_content(rule, value):
    assert get_value(f'align-content: {rule}') == value


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'auto',
    'none',
    'auto auto',
    'first last',
    'baseline baseline',
    'start safe',
    'start end',
    'safe unsafe',
    'left',
    'right',
))
def test_align_content_invalid(rule):
    assert_invalid(f'align-content: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, value', (
    ('normal', ('normal',)),
    ('stretch', ('stretch',)),
    ('baseline', ('first', 'baseline')),
    ('first baseline', ('first', 'baseline')),
    ('last baseline', ('last', 'baseline')),
    ('baseline last', ('baseline', 'last')),
    ('center', ('center',)),
    ('self-start', ('self-start',)),
    ('self-end', ('self-end',)),
    ('start', ('start',)),
    ('end', ('end',)),
    ('flex-start', ('flex-start',)),
    ('flex-end', ('flex-end',)),
    ('safe center', ('safe', 'center')),
    ('unsafe start', ('unsafe', 'start')),
    ('safe end', ('safe', 'end')),
    ('unsafe self-start', ('unsafe', 'self-start')),
    ('safe self-end', ('safe', 'self-end')),
    ('safe flex-start', ('safe', 'flex-start')),
    ('unsafe flex-start', ('unsafe', 'flex-start')),
))
def test_align_items(rule, value):
    assert get_value(f'align-items: {rule}') == value


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'auto',
    'none',
    'auto auto',
    'first last',
    'baseline baseline',
    'start safe',
    'start end',
    'safe unsafe',
    'left',
    'right',
    'space-between',
))
def test_align_items_invalid(rule):
    assert_invalid(f'align-items: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, value', (
    ('auto', ('auto',)),
    ('normal', ('normal',)),
    ('stretch', ('stretch',)),
    ('baseline', ('first', 'baseline')),
    ('first baseline', ('first', 'baseline')),
    ('last baseline', ('last', 'baseline')),
    ('baseline last', ('baseline', 'last')),
    ('center', ('center',)),
    ('self-start', ('self-start',)),
    ('self-end', ('self-end',)),
    ('start', ('start',)),
    ('end', ('end',)),
    ('flex-start', ('flex-start',)),
    ('flex-end', ('flex-end',)),
    ('safe center', ('safe', 'center')),
    ('unsafe start', ('unsafe', 'start')),
    ('safe end', ('safe', 'end')),
    ('unsafe self-start', ('unsafe', 'self-start')),
    ('safe self-end', ('safe', 'self-end')),
    ('safe flex-start', ('safe', 'flex-start')),
    ('unsafe flex-start', ('unsafe', 'flex-start')),
))
def test_align_self(rule, value):
    assert get_value(f'align-self: {rule}') == value


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'none',
    'auto auto',
    'first last',
    'baseline baseline',
    'start safe',
    'start end',
    'safe unsafe',
    'left',
    'right',
    'space-between',
))
def test_align_self_invalid(rule):
    assert_invalid(f'align-self: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, value', (
    ('normal', ('normal',)),
    ('space-between', ('space-between',)),
    ('space-around', ('space-around',)),
    ('space-evenly', ('space-evenly',)),
    ('stretch', ('stretch',)),
    ('center', ('center',)),
    ('left', ('left',)),
    ('right', ('right',)),
    ('start', ('start',)),
    ('end', ('end',)),
    ('flex-start', ('flex-start',)),
    ('flex-end', ('flex-end',)),
    ('safe center', ('safe', 'center')),
    ('unsafe start', ('unsafe', 'start')),
    ('safe end', ('safe', 'end')),
    ('unsafe left', ('unsafe', 'left')),
    ('safe right', ('safe', 'right')),
    ('safe flex-start', ('safe', 'flex-start')),
    ('unsafe flex-start', ('unsafe', 'flex-start')),
))
def test_justify_content(rule, value):
    assert get_value(f'justify-content: {rule}') == value


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'auto',
    'none',
    'baseline',
    'auto auto',
    'first last',
    'baseline baseline',
    'start safe',
    'start end',
    'safe unsafe',
))
def test_justify_content_invalid(rule):
    assert_invalid(f'justify-content: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, value', (
    ('normal', ('normal',)),
    ('stretch', ('stretch',)),
    ('baseline', ('first', 'baseline')),
    ('first baseline', ('first', 'baseline')),
    ('last baseline', ('last', 'baseline')),
    ('baseline last', ('baseline', 'last')),
    ('center', ('center',)),
    ('self-start', ('self-start',)),
    ('self-end', ('self-end',)),
    ('start', ('start',)),
    ('end', ('end',)),
    ('left', ('left',)),
    ('right', ('right',)),
    ('flex-start', ('flex-start',)),
    ('flex-end', ('flex-end',)),
    ('safe center', ('safe', 'center')),
    ('unsafe start', ('unsafe', 'start')),
    ('safe end', ('safe', 'end')),
    ('unsafe self-start', ('unsafe', 'self-start')),
    ('safe self-end', ('safe', 'self-end')),
    ('safe flex-start', ('safe', 'flex-start')),
    ('unsafe flex-start', ('unsafe', 'flex-start')),
    ('legacy', ('legacy',)),
    ('legacy left', ('legacy', 'left')),
    ('left legacy', ('left', 'legacy')),
    ('legacy center', ('legacy', 'center')),
))
def test_justify_items(rule, value):
    assert get_value(f'justify-items: {rule}') == value


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'auto',
    'none',
    'auto auto',
    'first last',
    'baseline baseline',
    'start safe',
    'start end',
    'safe unsafe',
    'space-between',
))
def test_justify_items_invalid(rule):
    assert_invalid(f'justify-items: {rule}')


@assert_no_logs
@pytest.mark.parametrize('rule, value', (
    ('auto', ('auto',)),
    ('normal', ('normal',)),
    ('stretch', ('stretch',)),
    ('baseline', ('first', 'baseline')),
    ('first baseline', ('first', 'baseline')),
    ('last baseline', ('last', 'baseline')),
    ('baseline last', ('baseline', 'last')),
    ('center', ('center',)),
    ('self-start', ('self-start',)),
    ('self-end', ('self-end',)),
    ('start', ('start',)),
    ('end', ('end',)),
    ('left', ('left',)),
    ('right', ('right',)),
    ('flex-start', ('flex-start',)),
    ('flex-end', ('flex-end',)),
    ('safe center', ('safe', 'center')),
    ('unsafe start', ('unsafe', 'start')),
    ('safe end', ('safe', 'end')),
    ('unsafe left', ('unsafe', 'left')),
    ('safe right', ('safe', 'right')),
    ('unsafe self-start', ('unsafe', 'self-start')),
    ('safe self-end', ('safe', 'self-end')),
    ('safe flex-start', ('safe', 'flex-start')),
    ('unsafe flex-start', ('unsafe', 'flex-start')),
))
def test_justify_self(rule, value):
    assert get_value(f'justify-self: {rule}') == value


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'none',
    'auto auto',
    'first last',
    'baseline baseline',
    'start safe',
    'start end',
    'safe unsafe',
    'space-between',
))
def test_justify_self_invalid(rule):
    assert_invalid(f'justify-self: {rule}')
