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
Test the management of the CSS properties.

"""

from attest import Tests, raises, assert_hook  # pylint: disable=W0611
from cssutils.css import PropertyValue

from .testing_utils import assert_no_logs
from ..css import validation
from ..css.values import as_css


SUITE = Tests()
SUITE.context(assert_no_logs)


def expand_to_dict(short_name, short_values):
    """Helper to test shorthand properties expander functions."""
    return dict((name, as_css(value) if isinstance(value, (list, tuple))
                       else getattr(value, 'cssText', value))
                for name, value in validation.EXPANDERS[short_name](
                    short_name, list(PropertyValue(short_values))))


@SUITE.test
def test_expand_four_sides():
    """Test the 4-value properties."""
    assert expand_to_dict('margin', 'inherit') == {
        'margin_top': 'inherit',
        'margin_right': 'inherit',
        'margin_bottom': 'inherit',
        'margin_left': 'inherit',
    }
    assert expand_to_dict('margin', '1em') == {
        'margin_top': '1em',
        'margin_right': '1em',
        'margin_bottom': '1em',
        'margin_left': '1em',
    }
    assert expand_to_dict('padding', '1em 0') == {
        'padding_top': '1em',
        'padding_right': '0',
        'padding_bottom': '1em',
        'padding_left': '0',
    }
    assert expand_to_dict('padding', '1em 0 2em') == {
        'padding_top': '1em',
        'padding_right': '0',
        'padding_bottom': '2em',
        'padding_left': '0',
    }
    assert expand_to_dict('padding', '1em 0 2em 5px') == {
        'padding_top': '1em',
        'padding_right': '0',
        'padding_bottom': '2em',
        'padding_left': '5px',
    }
    with raises(ValueError):
        expand_to_dict('padding', '1 2 3 4 5')


@SUITE.test
def test_expand_borders():
    """Test the ``border`` property."""
    assert expand_to_dict('border_top', '3px dotted red') == {
        'border_top_width': '3px',
        'border_top_style': 'dotted',
        'border_top_color': 'red',
    }
    assert expand_to_dict('border_top', '3px dotted') == {
        'border_top_width': '3px',
        'border_top_style': 'dotted',
        'border_top_color': 'currentColor',
    }
    assert expand_to_dict('border_top', '3px red') == {
        'border_top_width': '3px',
        'border_top_style': 'none',
        'border_top_color': 'red',
    }
    assert expand_to_dict('border_top', 'solid') == {
        'border_top_width': 3,
        'border_top_style': 'solid',
        'border_top_color': 'currentColor',
    }
    assert expand_to_dict('border', '6px dashed green') == {
        'border_top_width': '6px',
        'border_top_style': 'dashed',
        'border_top_color': 'green',

        'border_left_width': '6px',
        'border_left_style': 'dashed',
        'border_left_color': 'green',

        'border_bottom_width': '6px',
        'border_bottom_style': 'dashed',
        'border_bottom_color': 'green',

        'border_right_width': '6px',
        'border_right_style': 'dashed',
        'border_right_color': 'green',
    }
    with raises(ValueError):
        expand_to_dict('border', '6px dashed left')


@SUITE.test
def test_expand_list_style():
    """Test the ``list_style`` property."""
    assert expand_to_dict('list_style', 'inherit') == {
        'list_style_position': 'inherit',
        'list_style_image': 'inherit',
        'list_style_type': 'inherit',
    }
    assert expand_to_dict('list_style', 'url(foo.png)') == {
        'list_style_position': 'outside',
        'list_style_image': 'foo.png',
        'list_style_type': 'disc',
    }
    assert expand_to_dict('list_style', 'square') == {
        'list_style_position': 'outside',
        'list_style_image': 'none',
        'list_style_type': 'square',
    }
    assert expand_to_dict('list_style', 'circle inside') == {
        'list_style_position': 'inside',
        'list_style_image': 'none',
        'list_style_type': 'circle',
    }
    with raises(ValueError):
        expand_to_dict('list_style', 'red')


def assert_background(css, **kwargs):
    """Helper checking the background properties."""
    expanded = expand_to_dict('background', css).items()
    expected = [('background_' + key, value)
                for key, value in kwargs.iteritems()]
    assert sorted(expanded) == sorted(expected)


@SUITE.test
def test_expand_background():
    """Test the ``background`` property."""
    assert_background(
        'red',
        color='red', ##
        image='none',
        repeat='repeat',
        attachment='scroll',
        position='0% 0%'

    )
    assert_background(
        'url(foo.png)',
        color='transparent',
        image='foo.png', ##
        repeat='repeat',
        attachment='scroll',
        position='0% 0%'
    )
    assert_background(
        'no-repeat',
        color='transparent',
        image='none',
        repeat='no-repeat', ##
        attachment='scroll',
        position='0% 0%'
    )
    assert_background(
        'fixed',
        color='transparent',
        image='none',
        repeat='repeat',
        attachment='fixed', ##
        position='0% 0%'
    )
    assert_background(
        'top right',
        color='transparent',
        image='none',
        repeat='repeat',
        attachment='scroll',
        # Order swapped to be in (horizontal, vertical) order.
        position='100% 0%' ##
    )
    assert_background(
        'url(bar) #f00 repeat-y center left fixed',
        color='#f00', ##
        image='bar', ##
        repeat='repeat-y', ##
        attachment='fixed', ##
        # Order swapped to be in (horizontal, vertical) order.
        position='0% 50%' ##
    )
    assert_background(
        '#00f 10% 200px',
        color='#00f', ##
        image='none',
        repeat='repeat',
        attachment='scroll',
        position='10% 200px' ##
    )
    assert_background(
        'right 78px fixed',
        color='transparent',
        image='none',
        repeat='repeat',
        attachment='fixed', ##
        position='100% 78px' ##
    )


@SUITE.test
def test_font():
    """Test the ``font`` property."""
    assert expand_to_dict('font', '12px sans_serif') == {
        'font_style': 'normal',
        'font_variant': 'normal',
        'font_weight': 400,
        'font_size': '12px', ##
        'line_height': 'normal',
        'font_family': 'sans_serif', ##
    }
    assert expand_to_dict('font', 'small/1.2 "Some Font", serif') == {
        'font_style': 'normal',
        'font_variant': 'normal',
        'font_weight': 400,
        'font_size': 'small', ##
        'line_height': '1.2', ##
        # The comma and quotes were lost in expand_to_dict()
        'font_family': 'Some Font serif', ##
    }
    assert expand_to_dict('font', 'small-caps italic 700 large serif') == {
        'font_style': 'italic', ##
        'font_variant': 'small-caps', ##
        'font_weight': 700, ##
        'font_size': 'large', ##
        'line_height': 'normal',
        'font_family': 'serif', ##
    }
