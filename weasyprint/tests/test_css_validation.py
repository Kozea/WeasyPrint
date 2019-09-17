"""
    weasyprint.tests.test_css_properties
    ------------------------------------

    Test expanders for shorthand properties.

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import math

import pytest
import tinycss2

from ..css import preprocess_declarations
from ..css.computed_values import ZERO_PIXELS
from ..css.properties import INITIAL_VALUES, Dimension
from ..images import LinearGradient, RadialGradient
from .testing_utils import assert_no_logs, capture_logs


def expand_to_dict(css, expected_error=None):
    """Helper to test shorthand properties expander functions."""
    declarations = tinycss2.parse_declaration_list(css)

    with capture_logs() as logs:
        base_url = 'http://weasyprint.org/foo/'
        declarations = list(preprocess_declarations(base_url, declarations))

    if expected_error:
        assert len(logs) == 1
        assert expected_error in logs[0]
    else:
        assert not logs

    return dict(
        (name, value) for name, value, _priority in declarations
        if value != 'initial')


def assert_invalid(css, message='invalid'):
    assert expand_to_dict(css, message) == {}


@assert_no_logs
def test_not_print():
    assert expand_to_dict(
        'volume: 42', 'the property does not apply for the print media') == {}


@assert_no_logs
@pytest.mark.parametrize('rule, values', (
    ('1px, 3em, auto, auto', ((1, 'px'), (3, 'em'), 'auto', 'auto')),
    ('1px, 3em, auto auto', ((1, 'px'), (3, 'em'), 'auto', 'auto')),
    ('1px 3em auto 1px', ((1, 'px'), (3, 'em'), 'auto', (1, 'px'))),
))
def test_function(rule, values):
    assert expand_to_dict('clip: rect(%s)' % rule) == {'clip': values}


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'clip: square(1px, 3em, auto, auto)',
    'clip: rect(1px, 3em, auto)',
    'clip: rect(1px, 3em / auto)',
))
def test_function_invalid(rule):
    assert_invalid(rule)


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('counter-reset: foo bar 2 baz', {
        'counter_reset': (('foo', 0), ('bar', 2), ('baz', 0))}),
    ('counter-increment: foo bar 2 baz', {
        'counter_increment': (('foo', 1), ('bar', 2), ('baz', 1))}),
    ('counter-reset: foo', {'counter_reset': (('foo', 0),)}),
    ('counter-reset: FoO', {'counter_reset': (('FoO', 0),)}),
    ('counter-increment: foo bAr 2 Bar', {
        'counter_increment': (('foo', 1), ('bAr', 2), ('Bar', 1))}),
    ('counter-reset: none', {'counter_reset': ()}),
))
def test_counters(rule, result):
    assert expand_to_dict(rule) == result


@pytest.mark.parametrize('rule, warning, result', (
    ('counter-reset: foo initial', 'Invalid counter name: initial.', {}),
    ('counter-reset: foo none', 'Invalid counter name: none.', {}),
))
def test_counters_warning(rule, warning, result):
    assert expand_to_dict(rule, warning) == result


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'counter-reset: foo 3px',
    'counter-reset: 3',
))
def test_counters_invalid(rule):
    assert_invalid(rule)


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('letter-spacing: normal', {'letter_spacing': 'normal'}),
    ('letter-spacing: 3px', {'letter_spacing': (3, 'px')}),
    ('word-spacing: normal', {'word_spacing': 'normal'}),
    ('word-spacing: 3px', {'word_spacing': (3, 'px')}),
))
def test_spacing(rule, result):
    assert expand_to_dict(rule) == result


@assert_no_logs
def test_spacing_warning():
    assert expand_to_dict(
        'letter_spacing: normal', 'did you mean letter-spacing?') == {}


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'letter-spacing: 3',
    'word-spacing: 3',
))
def test_spacing_invalid(rule):
    assert_invalid(rule)


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('text-decoration-line: none', {'text_decoration_line': 'none'}),
    ('text-decoration-line: overline', {'text_decoration_line': {'overline'}}),
    ('text-decoration-line: overline blink line-through', {
        'text_decoration_line': {'blink', 'line-through', 'overline'}}),
))
def test_decoration_line(rule, result):
    assert expand_to_dict(rule) == result


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('text-decoration-style: solid', {'text_decoration_style': 'solid'}),
    ('text-decoration-style: double', {'text_decoration_style': 'double'}),
    ('text-decoration-style: dotted', {'text_decoration_style': 'dotted'}),
    ('text-decoration-style: dashed', {'text_decoration_style': 'dashed'}),
))
def test_decoration_style(rule, result):
    assert expand_to_dict(rule) == result


TEXT_DECORATION_DEFAULT = {
    'text_decoration_line': 'none',
    'text_decoration_color': 'currentColor',
    'text_decoration_style': 'solid',
}


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('text-decoration: none', {'text_decoration_line': 'none'}),
    ('text-decoration: overline', {'text_decoration_line': {'overline'}}),
    ('text-decoration: overline blink line-through', {
        'text_decoration_line': {'blink', 'line-through', 'overline'}}),
    ('text-decoration: red', {'text_decoration_color': (1, 0, 0, 1)}),
))
def test_decoration(rule, result):
    real_result = {**TEXT_DECORATION_DEFAULT, **result}
    assert expand_to_dict(rule) == real_result


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('size: 200px', {'size': ((200, 'px'), (200, 'px'))}),
    ('size: 200px 300pt', {'size': ((200, 'px'), (300, 'pt'))}),
    ('size: auto', {'size': ((210, 'mm'), (297, 'mm'))}),
    ('size: portrait', {'size': ((210, 'mm'), (297, 'mm'))}),
    ('size: landscape', {'size': ((297, 'mm'), (210, 'mm'))}),
    ('size: A3 portrait', {'size': ((297, 'mm'), (420, 'mm'))}),
    ('size: A3 landscape', {'size': ((420, 'mm'), (297, 'mm'))}),
    ('size: portrait A3', {'size': ((297, 'mm'), (420, 'mm'))}),
    ('size: landscape A3', {'size': ((420, 'mm'), (297, 'mm'))}),
))
def test_size(rule, result):
    assert expand_to_dict(rule) == result


@pytest.mark.parametrize('rule', (
    'size: A3 landscape A3',
    'size: A9',
    'size: foo',
    'size: foo bar',
    'size: 20%',
))
def test_size_invalid(rule):
    assert_invalid(rule)


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('transform: none', {'transform': ()}),
    ('transform: translate(6px) rotate(90deg)', {
        'transform': (
            ('translate', ((6, 'px'), (0, 'px'))),
            ('rotate', math.pi / 2))}),
    ('transform: translate(-4px, 0)', {
        'transform': (('translate', ((-4, 'px'), (0, None))),)}),
    ('transform: translate(6px, 20%)', {
        'transform': (('translate', ((6, 'px'), (20, '%'))),)}),
    ('transform: scale(2)', {'transform': (('scale', (2, 2)),)}),
    ('transform: translate(6px 20%)', {
        'transform': (('translate', ((6, 'px'), (20, '%'))),)}),
))
def test_transforms(rule, result):
    assert expand_to_dict(rule) == result


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'transform: lipsumize(6px)',
    'transform: foo',
    'transform: scale(2) foo',
    'transform: 6px',
))
def test_transforms_invalid(rule):
    assert_invalid(rule)


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
def test_expand_four_sides(rule, result):
    assert expand_to_dict(rule) == result


@assert_no_logs
def test_expand_four_sides_warning():
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
def test_expand_four_sides_invalid(rule):
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
def test_expand_borders(rule, result):
    assert expand_to_dict(rule) == result


@assert_no_logs
def test_expand_borders_invalid():
    assert_invalid('border: 6px dashed left')


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('list-style: inherit', {
        'list_style_position': 'inherit',
        'list_style_image': 'inherit',
        'list_style_type': 'inherit',
    }),
    ('list-style: url(../bar/lipsum.png)', {
        'list_style_image': ('url', 'http://weasyprint.org/bar/lipsum.png'),
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
))
def test_expand_list_style(rule, result):
    assert expand_to_dict(rule) == result


@assert_no_logs
def test_expand_list_style_warning():
    assert_invalid(
        'list-style: circle disc',
        'got multiple type values in a list-style shorthand')


@assert_no_logs
@pytest.mark.parametrize('rule', (
    'list-style: none inside none none',
    'list-style: red',
))
def test_expand_list_style_invalid(rule):
    assert_invalid(rule)


def assert_background(css, **expected):
    """Helper checking the background properties."""
    expanded = expand_to_dict('background: ' + css)
    assert expanded.pop('background_color') == expected.pop(
        'background_color', INITIAL_VALUES['background_color'])
    nb_layers = len(expanded['background_image'])
    for name, value in expected.items():
        assert expanded.pop(name) == value
    for name, value in expanded.items():
        assert tuple(value) == INITIAL_VALUES[name] * nb_layers


@assert_no_logs
def test_expand_background():
    assert_background('red', background_color=(1, 0, 0, 1))
    assert_background(
        'url(lipsum.png)',
        background_image=[('url', 'http://weasyprint.org/foo/lipsum.png')])
    assert_background(
        'no-repeat',
        background_repeat=[('no-repeat', 'no-repeat')])
    assert_background('fixed', background_attachment=['fixed'])
    assert_background(
        'repeat no-repeat fixed',
        background_repeat=[('repeat', 'no-repeat')],
        background_attachment=['fixed'])
    assert_background(
        'top',
        background_position=[('left', (50, '%'), 'top', (0, '%'))])
    assert_background(
        'top right',
        background_position=[('left', (100, '%'), 'top', (0, '%'))])
    assert_background(
        'top right 20px',
        background_position=[('right', (20, 'px'), 'top', (0, '%'))])
    assert_background(
        'top 1% right 20px',
        background_position=[('right', (20, 'px'), 'top', (1, '%'))])
    assert_background(
        'top no-repeat',
        background_repeat=[('no-repeat', 'no-repeat')],
        background_position=[('left', (50, '%'), 'top', (0, '%'))])
    assert_background(
        'top right no-repeat',
        background_repeat=[('no-repeat', 'no-repeat')],
        background_position=[('left', (100, '%'), 'top', (0, '%'))])
    assert_background(
        'top right 20px no-repeat',
        background_repeat=[('no-repeat', 'no-repeat')],
        background_position=[('right', (20, 'px'), 'top', (0, '%'))])
    assert_background(
        'top 1% right 20px no-repeat',
        background_repeat=[('no-repeat', 'no-repeat')],
        background_position=[('right', (20, 'px'), 'top', (1, '%'))])
    assert_background(
        'url(bar) #f00 repeat-y center left fixed',
        background_color=(1, 0, 0, 1),
        background_image=[('url', 'http://weasyprint.org/foo/bar')],
        background_repeat=[('no-repeat', 'repeat')],
        background_attachment=['fixed'],
        background_position=[('left', (0, '%'), 'top', (50, '%'))])
    assert_background(
        '#00f 10% 200px',
        background_color=(0, 0, 1, 1),
        background_position=[('left', (10, '%'), 'top', (200, 'px'))])
    assert_background(
        'right 78px fixed',
        background_attachment=['fixed'],
        background_position=[('left', (100, '%'), 'top', (78, 'px'))])
    assert_background(
        'center / cover red',
        background_size=['cover'],
        background_position=[('left', (50, '%'), 'top', (50, '%'))],
        background_color=(1, 0, 0, 1))
    assert_background(
        'center / auto red',
        background_size=[('auto', 'auto')],
        background_position=[('left', (50, '%'), 'top', (50, '%'))],
        background_color=(1, 0, 0, 1))
    assert_background(
        'center / 42px',
        background_size=[((42, 'px'), 'auto')],
        background_position=[('left', (50, '%'), 'top', (50, '%'))])
    assert_background(
        'center / 7% 4em',
        background_size=[((7, '%'), (4, 'em'))],
        background_position=[('left', (50, '%'), 'top', (50, '%'))])
    assert_background(
        'red content-box',
        background_color=(1, 0, 0, 1),
        background_origin=['content-box'],
        background_clip=['content-box'])
    assert_background(
        'red border-box content-box',
        background_color=(1, 0, 0, 1),
        background_origin=['border-box'],
        background_clip=['content-box'])
    assert_background(
        'url(bar) center, no-repeat',
        background_color=(0, 0, 0, 0),
        background_image=[('url', 'http://weasyprint.org/foo/bar'),
                          ('none', None)],
        background_position=[('left', (50, '%'), 'top', (50, '%')),
                             ('left', (0, '%'), 'top', (0, '%'))],
        background_repeat=[('repeat', 'repeat'), ('no-repeat', 'no-repeat')])
    assert_invalid('background: 10px lipsum')
    assert_invalid('background-position: 10px lipsum')
    assert_invalid('background: content-box red content-box')
    assert_invalid('background-image: inexistent-gradient(blue, green)')
    # Color must be in the last layer:
    assert_invalid('background: red, url(foo)')


@assert_no_logs
def test_expand_background_position():
    """Test the ``background-position`` property."""
    def position(css, *expected):
        [(name, [value])] = expand_to_dict(
            'background-position:' + css).items()
        assert name == 'background_position'
        assert value == expected
    for css_x, val_x in [
        ('left', (0, '%')), ('center', (50, '%')), ('right', (100, '%')),
        ('4.5%', (4.5, '%')), ('12px', (12, 'px'))
    ]:
        for css_y, val_y in [
            ('top', (0, '%')), ('center', (50, '%')), ('bottom', (100, '%')),
            ('7%', (7, '%')), ('1.5px', (1.5, 'px'))
        ]:
            # Two tokens:
            position('%s %s' % (css_x, css_y), 'left', val_x, 'top', val_y)
        # One token:
        position(css_x, 'left', val_x, 'top', (50, '%'))
    # One token, vertical
    position('top', 'left', (50, '%'), 'top', (0, '%'))
    position('bottom', 'left', (50, '%'), 'top', (100, '%'))

    # Three tokens:
    position('center top 10%', 'left', (50, '%'), 'top', (10, '%'))
    position('top 10% center', 'left', (50, '%'), 'top', (10, '%'))
    position('center bottom 10%', 'left', (50, '%'), 'bottom', (10, '%'))
    position('bottom 10% center', 'left', (50, '%'), 'bottom', (10, '%'))

    position('right top 10%', 'right', (0, '%'), 'top', (10, '%'))
    position('top 10% right', 'right', (0, '%'), 'top', (10, '%'))
    position('right bottom 10%', 'right', (0, '%'), 'bottom', (10, '%'))
    position('bottom 10% right', 'right', (0, '%'), 'bottom', (10, '%'))

    position('center left 10%', 'left', (10, '%'), 'top', (50, '%'))
    position('left 10% center', 'left', (10, '%'), 'top', (50, '%'))
    position('center right 10%', 'right', (10, '%'), 'top', (50, '%'))
    position('right 10% center', 'right', (10, '%'), 'top', (50, '%'))

    position('bottom left 10%', 'left', (10, '%'), 'bottom', (0, '%'))
    position('left 10% bottom', 'left', (10, '%'), 'bottom', (0, '%'))
    position('bottom right 10%', 'right', (10, '%'), 'bottom', (0, '%'))
    position('right 10% bottom', 'right', (10, '%'), 'bottom', (0, '%'))

    # Four tokens:
    position('left 10% bottom 3px', 'left', (10, '%'), 'bottom', (3, 'px'))
    position('bottom 3px left 10%', 'left', (10, '%'), 'bottom', (3, 'px'))
    position('right 10% top 3px', 'right', (10, '%'), 'top', (3, 'px'))
    position('top 3px right 10%', 'right', (10, '%'), 'top', (3, 'px'))

    assert_invalid('background-position: left center 3px')
    assert_invalid('background-position: 3px left')
    assert_invalid('background-position: bottom 4%')
    assert_invalid('background-position: bottom top')


@assert_no_logs
def test_font():
    """Test the ``font`` property."""
    assert expand_to_dict('font: 12px My Fancy Font, serif') == {
        'font_size': (12, 'px'),
        'font_family': ('My Fancy Font', 'serif'),
    }
    assert expand_to_dict('font: small/1.2 "Some Font", serif') == {
        'font_size': 'small',
        'line_height': (1.2, None),
        'font_family': ('Some Font', 'serif'),
    }
    assert expand_to_dict('font: small-caps italic 700 large serif') == {
        'font_style': 'italic',
        'font_variant_caps': 'small-caps',
        'font_weight': 700,
        'font_size': 'large',
        'font_family': ('serif',),
    }
    assert expand_to_dict(
        'font: small-caps condensed normal 700 large serif'
    ) == {
        'font_stretch': 'condensed',
        'font_variant_caps': 'small-caps',
        'font_weight': 700,
        'font_size': 'large',
        'font_family': ('serif',),
    }
    assert_invalid('font-family: "My" Font, serif')
    assert_invalid('font-family: "My" "Font", serif')
    assert_invalid('font-family: "My", 12pt, serif')
    assert_invalid('font: menu', 'System fonts are not supported')
    assert_invalid('font: 12deg My Fancy Font, serif')
    assert_invalid('font: 12px')
    assert_invalid('font: 12px/foo serif')
    assert_invalid('font: 12px "Invalid" family')
    assert_invalid('font: normal normal normal normal normal large serif')
    assert_invalid('font: normal small-caps italic 700 condensed large serif')
    assert_invalid('font: small-caps italic 700 normal condensed large serif')
    assert_invalid('font: small-caps italic 700 condensed normal large serif')


@assert_no_logs
def test_font_variant():
    """Test the ``font-variant`` property."""
    assert expand_to_dict('font-variant: normal') == {
        'font_variant_alternates': 'normal',
        'font_variant_caps': 'normal',
        'font_variant_east_asian': 'normal',
        'font_variant_ligatures': 'normal',
        'font_variant_numeric': 'normal',
        'font_variant_position': 'normal',
    }
    assert expand_to_dict('font-variant: none') == {
        'font_variant_alternates': 'normal',
        'font_variant_caps': 'normal',
        'font_variant_east_asian': 'normal',
        'font_variant_ligatures': 'none',
        'font_variant_numeric': 'normal',
        'font_variant_position': 'normal',
    }
    assert expand_to_dict('font-variant: historical-forms petite-caps') == {
        'font_variant_alternates': 'historical-forms',
        'font_variant_caps': 'petite-caps',
    }
    assert expand_to_dict(
        'font-variant: lining-nums contextual small-caps common-ligatures'
    ) == {
        'font_variant_ligatures': ('contextual', 'common-ligatures'),
        'font_variant_numeric': ('lining-nums',),
        'font_variant_caps': 'small-caps',
    }
    assert expand_to_dict('font-variant: jis78 ruby proportional-width') == {
        'font_variant_east_asian': ('jis78', 'ruby', 'proportional-width'),
    }
    # CSS2-style font-variant
    assert expand_to_dict('font-variant: small-caps') == {
        'font_variant_caps': 'small-caps',
    }
    assert_invalid('font-variant: normal normal')
    assert_invalid('font-variant: 2')
    assert_invalid('font-variant: ""')
    assert_invalid('font-variant: extra')
    assert_invalid('font-variant: jis78 jis04')
    assert_invalid('font-variant: full-width lining-nums ordinal normal')
    assert_invalid('font-variant: diagonal-fractions stacked-fractions')
    assert_invalid(
        'font-variant: common-ligatures contextual no-common-ligatures')
    assert_invalid('font-variant: sub super')
    assert_invalid('font-variant: slashed-zero slashed-zero')


@assert_no_logs
def test_line_height():
    """Test the ``line-height`` property."""
    assert expand_to_dict('line-height: 1px') == {'line_height': (1, 'px')}
    assert expand_to_dict('line-height: 1.1%') == {'line_height': (1.1, '%')}
    assert expand_to_dict('line-height: 1em') == {'line_height': (1, 'em')}
    assert expand_to_dict('line-height: 1') == {'line_height': (1, None)}
    assert expand_to_dict('line-height: 1.3') == {'line_height': (1.3, None)}
    assert expand_to_dict('line-height: -0') == {'line_height': (0, None)}
    assert expand_to_dict('line-height: 0px') == {'line_height': (0, 'px')}
    assert_invalid('line-height: 1deg')
    assert_invalid('line-height: -1px')
    assert_invalid('line-height: -1')
    assert_invalid('line-height: -0.5%')
    assert_invalid('line-height: 1px 1px')


@assert_no_logs
def test_string_set():
    """Test the ``string-set`` property."""
    assert expand_to_dict('string-set: test content(text)') == {
        'string_set': (('test', (('content()', 'text'),)),)}
    assert expand_to_dict('string-set: test content(before)') == {
        'string_set': (('test', (('content()', 'before'),)),)}
    assert expand_to_dict('string-set: test "string"') == {
        'string_set': (('test', (('string', 'string'),)),)}
    assert expand_to_dict(
        'string-set: test1 "string", test2 "string"') == {
            'string_set': (
                ('test1', (('string', 'string'),)),
                ('test2', (('string', 'string'),)))}
    assert expand_to_dict('string-set: test attr(class)') == {
        'string_set': (('test', (('attr()', ('class', 'string', '')),)),)}
    assert expand_to_dict('string-set: test counter(count)') == {
        'string_set': (('test', (('counter()', ('count', 'decimal')),)),)}
    assert expand_to_dict(
        'string-set: test counter(count, upper-roman)') == {
            'string_set': (
                ('test', (('counter()', ('count', 'upper-roman')),)),)}
    assert expand_to_dict('string-set: test counters(count, ".")') == {
        'string_set': (
            ('test', (('counters()', ('count', '.', 'decimal')),)),)}
    assert expand_to_dict(
        'string-set: test counters(count, ".", upper-roman)') == {
            'string_set': (
                ('test', (('counters()', ('count', '.', 'upper-roman')),)),)}
    assert expand_to_dict(
        'string-set: test content(text) "string" '
        'attr(title) attr(title) counter(count)') == {
            'string_set': (('test', (
                ('content()', 'text'), ('string', 'string'),
                ('attr()', ('title', 'string', '')),
                ('attr()', ('title', 'string', '')),
                ('counter()', ('count', 'decimal')))),)}

    assert_invalid('string-set: test')
    assert_invalid('string-set: test test1')
    assert_invalid('string-set: test content(test)')
    assert_invalid('string-set: test unknown()')
    assert_invalid('string-set: test attr(id, class)')


@assert_no_logs
def test_linear_gradient():
    red = (1, 0, 0, 1)
    lime = (0, 1, 0, 1)
    blue = (0, 0, 1, 1)
    pi = math.pi

    def gradient(css, direction, colors=[blue], stop_positions=[None]):
        for repeating, prefix in ((False, ''), (True, 'repeating-')):
            expanded = expand_to_dict(
                'background-image: %slinear-gradient(%s)' % (prefix, css))
            [(_, [(type_, image)])] = expanded.items()
            assert type_ == 'linear-gradient'
            assert isinstance(image, LinearGradient)
            assert image.repeating == repeating
            assert image.direction_type == direction[0]
            if isinstance(image.direction, str):
                image.direction == direction[1]
            else:
                assert image.direction == pytest.approx(direction[1])
            assert image.colors == colors
            assert image.stop_positions == stop_positions

    def invalid(css):
        assert_invalid('background-image: linear-gradient(%s)' % css)
        assert_invalid('background-image: repeating-linear-gradient(%s)' % css)

    invalid(' ')
    invalid('1% blue')
    invalid('blue 10deg')
    invalid('blue 4')
    invalid('soylent-green 4px')
    invalid('red 4px 2px')
    gradient('blue', ('angle', pi))
    gradient('red', ('angle', pi), [red], [None])
    gradient('blue 1%, lime,red 2em ', ('angle', pi),
             [blue, lime, red], [(1, '%'), None, (2, 'em')])
    invalid('18deg')
    gradient('18deg, blue', ('angle', pi / 10))
    gradient('4rad, blue', ('angle', 4))
    gradient('.25turn, blue', ('angle', pi / 2))
    gradient('100grad, blue', ('angle', pi / 2))
    gradient('12rad, blue 1%, lime,red 2em ', ('angle', 12),
             [blue, lime, red], [(1, '%'), None, (2, 'em')])
    invalid('10arc-minutes, blue')
    invalid('10px, blue')
    invalid('to 90deg, blue')
    gradient('to top, blue', ('angle', 0))
    gradient('to right, blue', ('angle', pi / 2))
    gradient('to bottom, blue', ('angle', pi))
    gradient('to left, blue', ('angle', pi * 3 / 2))
    gradient('to right, blue 1%, lime,red 2em ', ('angle', pi / 2),
             [blue, lime, red], [(1, '%'), None, (2, 'em')])
    invalid('to the top, blue')
    invalid('to up, blue')
    invalid('into top, blue')
    invalid('top, blue')
    gradient('to top left, blue', ('corner', 'top_left'))
    gradient('to left top, blue', ('corner', 'top_left'))
    gradient('to top right, blue', ('corner', 'top_right'))
    gradient('to right top, blue', ('corner', 'top_right'))
    gradient('to bottom left, blue', ('corner', 'bottom_left'))
    gradient('to left bottom, blue', ('corner', 'bottom_left'))
    gradient('to bottom right, blue', ('corner', 'bottom_right'))
    gradient('to right bottom, blue', ('corner', 'bottom_right'))
    invalid('to bottom up, blue')
    invalid('bottom left, blue')


@assert_no_logs
def test_overflow_wrap():
    assert expand_to_dict('overflow-wrap: normal') == {
        'overflow_wrap': 'normal'}
    assert expand_to_dict('overflow-wrap: break-word') == {
        'overflow_wrap': 'break-word'}
    assert_invalid('overflow-wrap: none')
    assert_invalid('overflow-wrap: normal, break-word')


@assert_no_logs
def test_expand_word_wrap():
    assert expand_to_dict('word-wrap: normal') == {
        'overflow_wrap': 'normal'}
    assert expand_to_dict('word-wrap: break-word') == {
        'overflow_wrap': 'break-word'}
    assert_invalid('word-wrap: none')
    assert_invalid('word-wrap: normal, break-word')


@assert_no_logs
def test_radial_gradient():
    red = (1, 0, 0, 1)
    lime = (0, 1, 0, 1)
    blue = (0, 0, 1, 1)

    def gradient(css, shape='ellipse', size=('keyword', 'farthest-corner'),
                 center=('left', (50, '%'), 'top', (50, '%')),
                 colors=[blue], stop_positions=[None]):
        for repeating, prefix in ((False, ''), (True, 'repeating-')):
            expanded = expand_to_dict(
                'background-image: %sradial-gradient(%s)' % (prefix, css))
            [(_, [(type_, image)])] = expanded.items()
            assert type_ == 'radial-gradient'
            assert isinstance(image, RadialGradient)
            assert image.repeating == repeating
            assert image.shape == shape
            assert image.size_type == size[0]
            assert image.size == size[1]
            assert image.center == center
            assert image.colors == colors
            assert image.stop_positions == stop_positions

    def invalid(css):
        assert_invalid('background-image: radial-gradient(%s)' % css)
        assert_invalid('background-image: repeating-radial-gradient(%s)' % css)

    invalid(' ')
    invalid('1% blue')
    invalid('blue 10deg')
    invalid('blue 4')
    invalid('soylent-green 4px')
    invalid('red 4px 2px')
    gradient('blue')
    gradient('red', colors=[red])
    gradient('blue 1%, lime,red 2em ', colors=[blue, lime, red],
             stop_positions=[(1, '%'), None, (2, 'em')])
    gradient('circle, blue', 'circle')
    gradient('ellipse, blue', 'ellipse')
    invalid('circle')
    invalid('square, blue')
    invalid('closest-triangle, blue')
    invalid('center, blue')
    gradient('ellipse closest-corner, blue',
             'ellipse', ('keyword', 'closest-corner'))
    gradient('circle closest-side, blue',
             'circle', ('keyword', 'closest-side'))
    gradient('farthest-corner circle, blue',
             'circle', ('keyword', 'farthest-corner'))
    gradient('farthest-side, blue',
             'ellipse', ('keyword', 'farthest-side'))
    gradient('5ch, blue',
             'circle', ('explicit', ((5, 'ch'), (5, 'ch'))))
    gradient('5ch circle, blue',
             'circle', ('explicit', ((5, 'ch'), (5, 'ch'))))
    gradient('circle 5ch, blue',
             'circle', ('explicit', ((5, 'ch'), (5, 'ch'))))
    invalid('ellipse 5ch')
    invalid('5ch ellipse')
    gradient('10px 50px, blue',
             'ellipse', ('explicit', ((10, 'px'), (50, 'px'))))
    gradient('10px 50px ellipse, blue',
             'ellipse', ('explicit', ((10, 'px'), (50, 'px'))))
    gradient('ellipse 10px 50px, blue',
             'ellipse', ('explicit', ((10, 'px'), (50, 'px'))))
    invalid('circle 10px 50px, blue')
    invalid('10px 50px circle, blue')
    invalid('10%, blue')
    invalid('10% circle, blue')
    invalid('circle 10%, blue')
    gradient('10px 50px, blue',
             'ellipse', ('explicit', ((10, 'px'), (50, 'px'))))
    invalid('at appex, blue')
    gradient('at top 10% right, blue',
             center=('right', (0, '%'), 'top', (10, '%')))
    gradient('circle at bottom, blue', shape='circle',
             center=('left', (50, '%'), 'top', (100, '%')))
    gradient('circle at 10px, blue', shape='circle',
             center=('left', (10, 'px'), 'top', (50, '%')))
    gradient('closest-side circle at right 5em, blue',
             shape='circle', size=('keyword', 'closest-side'),
             center=('left', (100, '%'), 'top', (5, 'em')))


@assert_no_logs
@pytest.mark.parametrize('rule, result', (
    ('flex: auto', {
        'flex_grow': 1,
        'flex_shrink': 1,
        'flex_basis': 'auto',
    }),
    ('flex: none', {
        'flex_grow': 0,
        'flex_shrink': 0,
        'flex_basis': 'auto',
    }),
    ('flex: 10', {
        'flex_grow': 10,
        'flex_shrink': 1,
        'flex_basis': ZERO_PIXELS,
    }),
    ('flex: 2 2', {
        'flex_grow': 2,
        'flex_shrink': 2,
        'flex_basis': ZERO_PIXELS,
    }),
    ('flex: 2 2 1px', {
        'flex_grow': 2,
        'flex_shrink': 2,
        'flex_basis': Dimension(1, 'px'),
    }),
    ('flex: 2 2 auto', {
        'flex_grow': 2,
        'flex_shrink': 2,
        'flex_basis': 'auto',
    }),
    ('flex: 2 auto', {
        'flex_grow': 2,
        'flex_shrink': 1,
        'flex_basis': 'auto',
    }),
))
def test_flex(rule, result):
    """Test the ``flex`` property."""
    assert expand_to_dict(rule) == result
