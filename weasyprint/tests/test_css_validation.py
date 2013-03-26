# coding: utf8
"""
    weasyprint.tests.test_css_properties
    ------------------------------------

    Test expanders for shorthand properties.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from .testing_utils import assert_no_logs, capture_logs
from ..css import PARSER, preprocess_declarations
from ..css.properties import INITIAL_VALUES


def expand_to_dict(css, expected_error=None):
    """Helper to test shorthand properties expander functions."""
    declarations, errors = PARSER.parse_style_attr(css)
    assert not errors

    with capture_logs() as logs:
        base_url = 'http://weasyprint.org/foo/'
        declarations = list(preprocess_declarations(base_url, declarations))

    if expected_error:
        assert len(logs) == 1
        assert expected_error in logs[0]
    else:
        assert not logs

    return dict((name, value) for name, value, _priority in declarations
                 if value != 'initial')


def assert_invalid(css, message='invalid'):
    assert expand_to_dict(css, message) == {}


@assert_no_logs
def test_not_print():
    assert expand_to_dict('volume: 42',
        'the property does not apply for the print media') == {}


@assert_no_logs
def test_function():
    assert expand_to_dict('clip: rect(1px, 3em, auto, auto)') == {
        'clip': [(1, 'px'), (3, 'em'), 'auto', 'auto']}
    assert_invalid('clip: square(1px, 3em, auto, auto)')
    assert_invalid('clip: rect(1px, 3em, auto auto)', 'invalid')
    assert_invalid('clip: rect(1px, 3em, auto)')
    assert_invalid('clip: rect(1px, 3em / auto)')


@assert_no_logs
def test_counters():
    assert expand_to_dict('counter-reset: foo bar 2 baz') == {
        'counter_reset': [('foo', 0), ('bar', 2), ('baz', 0)]}
    assert expand_to_dict('counter-increment: foo bar 2 baz') == {
        'counter_increment': [('foo', 1), ('bar', 2), ('baz', 1)]}
    assert expand_to_dict('counter-reset: foo') == {
        'counter_reset': [('foo', 0)]}
    assert expand_to_dict('counter-reset: none') == {
        'counter_reset': []}
    assert expand_to_dict('counter-reset: foo none',
        'Invalid counter name') == {}
    assert expand_to_dict('counter-reset: foo initial',
        'Invalid counter name') == {}
    assert_invalid('counter-reset: foo 3px')
    assert_invalid('counter-reset: 3')


@assert_no_logs
def test_spacing():
    assert expand_to_dict('letter-spacing: normal') == {
        'letter_spacing': 'normal'}
    assert expand_to_dict('letter-spacing: 3px') == {
        'letter_spacing': (3, 'px')}
    assert_invalid('letter-spacing: 3')
    assert expand_to_dict('letter_spacing: normal',
        'did you mean letter-spacing') == {}

    assert expand_to_dict('word-spacing: normal') == {
        'word_spacing': 'normal'}
    assert expand_to_dict('word-spacing: 3px') == {
        'word_spacing': (3, 'px')}
    assert_invalid('word-spacing: 3')


@assert_no_logs
def test_decoration():
    assert expand_to_dict('text-decoration: none') == {
        'text_decoration': 'none'}
    assert expand_to_dict('text-decoration: overline') == {
        'text_decoration': frozenset(['overline'])}
    # blink is accepted but ignored
    assert expand_to_dict('text-decoration: overline blink line-through') == {
        'text_decoration': frozenset(['line-through', 'overline'])}


@assert_no_logs
def test_size():
    assert expand_to_dict('size: 200px') == {
        'size': ((200, 'px'), (200, 'px'))}
    assert expand_to_dict('size: 200px 300pt') == {
        'size': ((200, 'px'), (300, 'pt'))}
    assert expand_to_dict('size: auto') == {
        'size': ((210, 'mm'), (297, 'mm'))}
    assert expand_to_dict('size: portrait') == {
        'size': ((210, 'mm'), (297, 'mm'))}
    assert expand_to_dict('size: landscape') == {
        'size': ((297, 'mm'), (210, 'mm'))}
    assert expand_to_dict('size: A3 portrait') == {
        'size': ((297, 'mm'), (420, 'mm'))}
    assert expand_to_dict('size: A3 landscape') == {
        'size': ((420, 'mm'), (297, 'mm'))}
    assert expand_to_dict('size: portrait A3') == {
        'size': ((297, 'mm'), (420, 'mm'))}
    assert expand_to_dict('size: landscape A3') == {
        'size': ((420, 'mm'), (297, 'mm'))}
    assert_invalid('size: A3 landscape A3')
    assert_invalid('size: A9')
    assert_invalid('size: foo')
    assert_invalid('size: foo bar')
    assert_invalid('size: 20%')


@assert_no_logs
def test_transforms():
    assert expand_to_dict('transform: none') == {
        'transform': []}
    assert expand_to_dict('transform: translate(6px) rotate(90deg)'
        ) == {'transform': [('translate', ((6, 'px'), (0, 'px'))),
                            ('rotate', (90, 'deg'))]}
    assert expand_to_dict('transform: translate(-4px, 0)'
        ) == {'transform': [('translate', ((-4, 'px'), (0, None)))]}
    assert expand_to_dict('transform: translate(6px, 20%)'
        ) == {'transform': [('translate', ((6, 'px'), (20, '%')))]}
    assert expand_to_dict('transform: scale(2)'
        ) == {'transform': [('scale', (2, 2))]}
    assert_invalid('transform: translate(6px 20%)')  # missing comma
    assert_invalid('transform: lipsumize(6px)')
    assert_invalid('transform: foo')
    assert_invalid('transform: scale(2) foo')
    assert_invalid('transform: 6px')
    assert_invalid('-weasy-transform: none',
                   'the property was unprefixed, use transform')


@assert_no_logs
def test_expand_four_sides():
    """Test the 4-value properties."""
    assert expand_to_dict('margin: inherit') == {
        'margin_top': 'inherit',
        'margin_right': 'inherit',
        'margin_bottom': 'inherit',
        'margin_left': 'inherit',
    }
    assert expand_to_dict('margin: 1em') == {
        'margin_top': (1, 'em'),
        'margin_right': (1, 'em'),
        'margin_bottom': (1, 'em'),
        'margin_left': (1, 'em'),
    }
    assert expand_to_dict('margin: -1em auto 20%') == {
        'margin_top': (-1, 'em'),
        'margin_right': 'auto',
        'margin_bottom': (20, '%'),
        'margin_left': 'auto',
    }
    assert expand_to_dict('padding: 1em 0') == {
        'padding_top': (1, 'em'),
        'padding_right': (0, None),
        'padding_bottom': (1, 'em'),
        'padding_left': (0, None),
    }
    assert expand_to_dict('padding: 1em 0 2%') == {
        'padding_top': (1, 'em'),
        'padding_right': (0, None),
        'padding_bottom': (2, '%'),
        'padding_left': (0, None),
    }
    assert expand_to_dict('padding: 1em 0 2em 5px') == {
        'padding_top': (1, 'em'),
        'padding_right': (0, None),
        'padding_bottom': (2, 'em'),
        'padding_left': (5, 'px'),
    }
    assert expand_to_dict('padding: 1 2 3 4 5',
        'Expected 1 to 4 token components got 5') == {}
    assert_invalid('margin: rgb(0, 0, 0)')
    assert_invalid('padding: auto')
    assert_invalid('padding: -12px')
    assert_invalid('border-width: -3em')
    assert_invalid('border-width: 12%')


@assert_no_logs
def test_expand_borders():
    """Test the ``border`` property."""
    assert expand_to_dict('border-top: 3px dotted red') == {
        'border_top_width': (3, 'px'),
        'border_top_style': 'dotted',
        'border_top_color': (1, 0, 0, 1),  # red
    }
    assert expand_to_dict('border-top: 3px dotted') == {
        'border_top_width': (3, 'px'),
        'border_top_style': 'dotted',
    }
    assert expand_to_dict('border-top: 3px red') == {
        'border_top_width': (3, 'px'),
        'border_top_color': (1, 0, 0, 1),  # red
    }
    assert expand_to_dict('border-top: solid') == {
        'border_top_style': 'solid',
    }
    assert expand_to_dict('border: 6px dashed lime') == {
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
    }
    assert_invalid('border: 6px dashed left')


@assert_no_logs
def test_expand_list_style():
    """Test the ``list_style`` property."""
    assert expand_to_dict('list-style: inherit') == {
        'list_style_position': 'inherit',
        'list_style_image': 'inherit',
        'list_style_type': 'inherit',
    }
    assert expand_to_dict('list-style: url(../bar/lipsum.png)') == {
        'list_style_image': 'http://weasyprint.org/bar/lipsum.png',
    }
    assert expand_to_dict('list-style: square') == {
        'list_style_type': 'square',
    }
    assert expand_to_dict('list-style: circle inside') == {
        'list_style_position': 'inside',
        'list_style_type': 'circle',
    }
    assert expand_to_dict('list-style: none circle inside') == {
        'list_style_position': 'inside',
        'list_style_image': 'none',
        'list_style_type': 'circle',
    }
    assert expand_to_dict('list-style: none inside none') == {
        'list_style_position': 'inside',
        'list_style_image': 'none',
        'list_style_type': 'none',
    }
    assert_invalid('list-style: none inside none none')
    assert_invalid('list-style: red')
    assert_invalid('list-style: circle disc',
                   'got multiple type values in a list-style shorthand')


def assert_background(css, **expected):
    """Helper checking the background properties."""
    expanded = expand_to_dict('background: ' + css)
    assert expanded.pop('background_color') == expected.pop(
        'background_color', INITIAL_VALUES['background_color'])
    nb_layers = len(expanded['background_image'])
    for name, value in expected.items():
        assert expanded.pop(name) == value
    for name, value in expanded.items():
        assert value == INITIAL_VALUES[name] * nb_layers


@assert_no_logs
def test_expand_background():
    """Test the ``background`` property."""
    assert_background('red', background_color=(1, 0, 0, 1))
    assert_background(
        'url(lipsum.png)',
        background_image=['http://weasyprint.org/foo/lipsum.png'])
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
        background_image=['http://weasyprint.org/foo/bar'],
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
        background_image=['http://weasyprint.org/foo/bar', 'none'],
        background_position=[('left', (50, '%'), 'top', (50, '%')),
                             ('left', (0, '%'), 'top', (0, '%'))],
        background_repeat=[('repeat', 'repeat'), ('no-repeat', 'no-repeat')])
    assert_invalid('background: 10px lipsum')
    assert_invalid('background-position: 10px lipsum')
    assert_invalid('background: content-box red content-box')
    # Color must be in the last layer:
    assert_invalid('background: red, url(foo)')


@assert_no_logs
def test_expand_background_position():
    """Test the ``background-position`` property."""
    def position(css, *expected):
        [(name, [value])] = expand_to_dict('background-position:' + css).items()
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
        'font_family': ['My Fancy Font', 'serif'],
    }
    assert expand_to_dict('font: small/1.2 "Some Font", serif') == {
        'font_size': 'small',
        'line_height': (1.2, None),
        'font_family': ['Some Font', 'serif'],
    }
    assert expand_to_dict('font: small-caps italic 700 large serif') == {
        'font_style': 'italic',
        'font_variant': 'small-caps',
        'font_weight': 700,
        'font_size': 'large',
        'font_family': ['serif'],
    }
    assert expand_to_dict('font: small-caps normal 700 large serif') == {
        #'font_style': 'normal',  XXX shouldn’t this be here?
        'font_variant': 'small-caps',
        'font_weight': 700,
        'font_size': 'large',
        'font_family': ['serif'],
    }
    assert_invalid('font-family: "My" Font, serif')
    assert_invalid('font-family: "My" "Font", serif')
    assert_invalid('font-family: "My", 12pt, serif')
    assert_invalid('font: menu', 'System fonts are not supported')
    assert_invalid('font: 12deg My Fancy Font, serif')
    assert_invalid('font: 12px')
    assert_invalid('font: 12px/foo serif')
    assert_invalid('font: 12px "Invalid" family')
