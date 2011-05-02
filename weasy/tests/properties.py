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
from cssutils.css import PropertyValue, CSSStyleDeclaration

from ..properties import four_sides, expand_shorthands_in_declaration


suite = Tests()


def expand_shorthand(expander, name, value):
    """Helper to test shorthand properties expander functions."""
    return dict((name, value.cssText)
                for name, value in expander(name, list(PropertyValue(value))))


def expand_to_dict(css):
    """Helper to test shorthand properties expander functions."""
    return dict((prop.name, prop.value)
                for prop in expand_shorthands_in_declaration(
                    CSSStyleDeclaration(css)))


@suite.test
def test_four_sides():
    assert expand_to_dict('margin: 1em') == {
        'margin-top': '1em',
        'margin-right': '1em',
        'margin-bottom': '1em',
        'margin-left': '1em',
    }
    assert expand_to_dict('padding: 1em 0') == {
        'padding-top': '1em',
        'padding-right': '0',
        'padding-bottom': '1em',
        'padding-left': '0',
    }
    assert expand_to_dict('padding: 1em 0 2em') == {
        'padding-top': '1em',
        'padding-right': '0',
        'padding-bottom': '2em',
        'padding-left': '0',
    }
    assert expand_to_dict('padding: 1em 0 2em 5px') == {
        'padding-top': '1em',
        'padding-right': '0',
        'padding-bottom': '2em',
        'padding-left': '5px',
    }
    with attest.raises(ValueError):
        list(four_sides('padding', PropertyValue('1 2 3 4 5')))


