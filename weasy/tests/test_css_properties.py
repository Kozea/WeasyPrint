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

import attest
from attest import Tests, assert_hook
from cssutils.css import PropertyValue

from ..css import validation
from ..css.values import as_css


suite = Tests()


def expand_to_dict(short_name, short_values):
    """Helper to test shorthand properties expander functions."""
    return dict((name, as_css(values))
                for name, values in validation.EXPANDERS[short_name](
                    short_name, list(PropertyValue(short_values))))


@suite.test
def test_expand_four_sides():
    assert expand_to_dict('margin', 'inherit') == {
        'margin-top': 'inherit',
        'margin-right': 'inherit',
        'margin-bottom': 'inherit',
        'margin-left': 'inherit',
    }
    assert expand_to_dict('margin', '1em') == {
        'margin-top': '1em',
        'margin-right': '1em',
        'margin-bottom': '1em',
        'margin-left': '1em',
    }
    assert expand_to_dict('padding', '1em 0') == {
        'padding-top': '1em',
        'padding-right': '0',
        'padding-bottom': '1em',
        'padding-left': '0',
    }
    assert expand_to_dict('padding', '1em 0 2em') == {
        'padding-top': '1em',
        'padding-right': '0',
        'padding-bottom': '2em',
        'padding-left': '0',
    }
    assert expand_to_dict('padding', '1em 0 2em 5px') == {
        'padding-top': '1em',
        'padding-right': '0',
        'padding-bottom': '2em',
        'padding-left': '5px',
    }
    with attest.raises(ValueError):
        expand_to_dict('padding', '1 2 3 4 5')


@suite.test
def test_expand_borders():
    assert expand_to_dict('border-top', '3px dotted red') == {
        'border-top-width': '3px',
        'border-top-style': 'dotted',
        'border-top-color': 'red',
    }
    assert expand_to_dict('border-top', '3px dotted') == {
        'border-top-width': '3px',
        'border-top-style': 'dotted',
        'border-top-color': 'currentColor',
    }
    assert expand_to_dict('border-top', '3px red') == {
        'border-top-width': '3px',
        'border-top-style': 'none',
        'border-top-color': 'red',
    }
    assert expand_to_dict('border-top', 'inset') == {
        'border-top-width': 'medium',
        'border-top-style': 'inset',
        'border-top-color': 'currentColor',
    }
    assert expand_to_dict('border', '6px dashed green') == {
        'border-top-width': '6px',
        'border-top-style': 'dashed',
        'border-top-color': 'green',

        'border-left-width': '6px',
        'border-left-style': 'dashed',
        'border-left-color': 'green',

        'border-bottom-width': '6px',
        'border-bottom-style': 'dashed',
        'border-bottom-color': 'green',

        'border-right-width': '6px',
        'border-right-style': 'dashed',
        'border-right-color': 'green',
    }
    with attest.raises(ValueError):
        expand_to_dict('border', '6px dashed left')


@suite.test
def test_expand_list_style():
    assert expand_to_dict('list-style', 'inherit') == {
        'list-style-position': 'inherit',
        'list-style-image': 'inherit',
        'list-style-type': 'inherit',
    }
    assert expand_to_dict('list-style', 'url(foo.png)') == {
        'list-style-position': 'outside',
        'list-style-image': 'url(foo.png)',
        'list-style-type': 'disc',
    }
    assert expand_to_dict('list-style', 'decimal') == {
        'list-style-position': 'outside',
        'list-style-image': 'none',
        'list-style-type': 'decimal',
    }
    assert expand_to_dict('list-style', 'circle inside') == {
        'list-style-position': 'inside',
        'list-style-image': 'none',
        'list-style-type': 'circle',
    }
    with attest.raises(ValueError):
        expand_to_dict('list-style', 'red')


def assert_background(css, **kwargs):
    expanded = expand_to_dict('background', css).items()
    expected = [('background-' + key, value)
                for key, value in kwargs.iteritems()]
    assert sorted(expanded) == sorted(expected)


@suite.test
def test_expand_background():
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
        image='url(foo.png)', ##
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
        position='top right' ##
    )
    assert_background(
        'url(bar) #f00 repeat-y center left fixed',
        color='#f00', ##
        image='url(bar)', ##
        repeat='repeat-y', ##
        attachment='fixed', ##
        position='center left' ##
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
        position='right 78px' ##
    )


@suite.test
def test_font():
    assert expand_to_dict('font', '12px sans-serif') == {
        'font-style': 'normal',
        'font-variant': 'normal',
        'font-weight': 'normal',
        'font-size': '12px', ##
        'line-height': 'normal',
        'font-family': 'sans-serif', ##
    }
    assert expand_to_dict('font', 'small/1.2 "Some Font", serif') == {
        'font-style': 'normal',
        'font-variant': 'normal',
        'font-weight': 'normal',
        'font-size': 'small', ##
        'line-height': '1.2', ##
        # The comma was lost in expand_to_dict()
        'font-family': '"Some Font" serif', ##
    }
    assert expand_to_dict('font', 'small-caps italic 700 large serif') == {
        'font-style': 'italic', ##
        'font-variant': 'small-caps', ##
        'font-weight': '700', ##
        'font-size': 'large', ##
        'line-height': 'normal',
        'font-family': 'serif', ##
    }
