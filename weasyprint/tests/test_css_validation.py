# coding: utf8
"""
    weasyprint.tests.test_css_properties
    ------------------------------------

    Test expanders for shorthand properties.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from tinycss.color3 import RGBA

from .testing_utils import assert_no_logs, capture_logs
from ..css import PARSER, preprocess_declarations


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

    return dict((name, value) for name, value, _priority in declarations)


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
    assert expand_to_dict('padding: 1em 0') == {
        'padding_top': (1, 'em'),
        'padding_right': (0, None),
        'padding_bottom': (1, 'em'),
        'padding_left': (0, None),
    }
    assert expand_to_dict('padding: 1em 0 2em') == {
        'padding_top': (1, 'em'),
        'padding_right': (0, None),
        'padding_bottom': (2, 'em'),
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


@assert_no_logs
def test_expand_borders():
    """Test the ``border`` property."""
    assert expand_to_dict('border_top: 3px dotted red') == {
        'border_top_width': (3, 'px'),
        'border_top_style': 'dotted',
        'border_top_color': (1, 0, 0, 1),  # red
    }
    assert expand_to_dict('border_top: 3px dotted') == {
        'border_top_width': (3, 'px'),
        'border_top_style': 'dotted',
        'border_top_color': 'currentColor',
    }
    assert expand_to_dict('border_top: 3px red') == {
        'border_top_width': (3, 'px'),
        'border_top_style': 'none',
        'border_top_color': (1, 0, 0, 1),  # red
    }
    assert expand_to_dict('border_top: solid') == {
        'border_top_width': 3,  # initial value
        'border_top_style': 'solid',
        'border_top_color': 'currentColor',
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
    assert expand_to_dict('border: 6px dashed left', 'invalid') == {}


@assert_no_logs
def test_expand_list_style():
    """Test the ``list_style`` property."""
    assert expand_to_dict('list_style: inherit') == {
        'list_style_position': 'inherit',
        'list_style_image': 'inherit',
        'list_style_type': 'inherit',
    }
    assert expand_to_dict('list_style: url(../bar/lipsum.png)') == {
        'list_style_position': 'outside',
        'list_style_image': 'http://weasyprint.org/bar/lipsum.png',
        'list_style_type': 'disc',
    }
    assert expand_to_dict('list_style: square') == {
        'list_style_position': 'outside',
        'list_style_image': 'none',
        'list_style_type': 'square',
    }
    assert expand_to_dict('list_style: circle inside') == {
        'list_style_position': 'inside',
        'list_style_image': 'none',
        'list_style_type': 'circle',
    }
    assert expand_to_dict('list_style: red', 'invalid') == {}
    assert expand_to_dict('list_style: circle disc',
        'got multiple type values in a list_style shorthand') == {}


def assert_background(css, **kwargs):
    """Helper checking the background properties."""
    expanded = expand_to_dict('background: '+ css).items()
    expected = [('background_' + key, value)
                for key, value in kwargs.items()]
    assert sorted(expanded) == sorted(expected)


@assert_no_logs
def test_expand_background():
    """Test the ``background`` property."""
    assert_background(
        'red',
        color=(1, 0, 0, 1), ## red
        image='none',
        repeat='repeat',
        attachment='scroll',
        position=((0, '%'), (0, '%')),

    )
    assert_background(
        'url(lipsum.png)',
        color=(0, 0, 0, 0), # transparent
        image='http://weasyprint.org/foo/lipsum.png', ##
        repeat='repeat',
        attachment='scroll',
        position=((0, '%'), (0, '%')),
    )
    assert_background(
        'no-repeat',
        color=(0, 0, 0, 0), # transparent
        image='none',
        repeat='no-repeat', ##
        attachment='scroll',
        position=((0, '%'), (0, '%')),
    )
    assert_background(
        'fixed',
        color=(0, 0, 0, 0), # transparent
        image='none',
        repeat='repeat',
        attachment='fixed', ##
        position=((0, '%'), (0, '%')),
    )
    assert_background(
        'top right',
        color=(0, 0, 0, 0), # transparent
        image='none',
        repeat='repeat',
        attachment='scroll',
        # Order swapped to be in (horizontal, vertical) order.
        position=((100, '%'), (0, '%')), ##
    )
    assert_background(
        'url(bar) #f00 repeat-y center left fixed',
        color=(1, 0, 0, 1), ## #f00
        image='http://weasyprint.org/foo/bar', ##
        repeat='repeat-y', ##
        attachment='fixed', ##
        # Order swapped to be in (horizontal, vertical) order.
        position=((0, '%'), (50, '%')), ##
    )
    assert_background(
        '#00f 10% 200px',
        color=(0, 0, 1, 1), ## #00f
        image='none',
        repeat='repeat',
        attachment='scroll',
        position=((10, '%'), (200, 'px')),  ##
    )
    assert_background(
        'right 78px fixed',
        color=(0, 0, 0, 0), # transparent
        image='none',
        repeat='repeat',
        attachment='fixed', ##
        position=((100, '%'), (78, 'px')), ##
    )


@assert_no_logs
def test_font():
    """Test the ``font`` property."""
    assert expand_to_dict('font: 12px My Fancy Font, serif') == {
        'font_style': 'normal',
        'font_variant': 'normal',
        'font_weight': 400,
        'font_size': (12, 'px'), ##
        'line_height': 'normal',
        'font_family': ['My Fancy Font', 'serif'], ##
    }
    assert expand_to_dict('font: small/1.2 "Some Font", serif') == {
        'font_style': 'normal',
        'font_variant': 'normal',
        'font_weight': 400,
        'font_size': 'small', ##
        'line_height': (1.2, None), ##
        'font_family': ['Some Font', 'serif'], ##
    }
    assert expand_to_dict('font: small-caps italic 700 large serif') == {
        'font_style': 'italic', ##
        'font_variant': 'small-caps', ##
        'font_weight': 700, ##
        'font_size': 'large', ##
        'line_height': 'normal',
        'font_family': ['serif'], ##
    }
