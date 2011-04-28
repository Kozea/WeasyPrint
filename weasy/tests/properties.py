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
from cssutils.css import Property

from ..properties import four_sides_lengths


suite = Tests()


def expand_shorthand(expander, name, value):
    """Helper to test shorthand properties expander functions."""
    return dict((property.name, property.value)
                for property in expander(Property(name, value)))


@suite.test
def test_four_sides_lengths():
    assert expand_shorthand(four_sides_lengths, 'margin', '1em') == {
        'margin-top': '1em',
        'margin-right': '1em',
        'margin-bottom': '1em',
        'margin-left': '1em',
    }
    assert expand_shorthand(four_sides_lengths, 'padding', '1em 0') == {
        'padding-top': '1em',
        'padding-right': '0',
        'padding-bottom': '1em',
        'padding-left': '0',
    }
    assert expand_shorthand(four_sides_lengths, 'padding', '1em 0 2em') == {
        'padding-top': '1em',
        'padding-right': '0',
        'padding-bottom': '2em',
        'padding-left': '0',
    }
    assert expand_shorthand(four_sides_lengths, 'padding', '1em 0 2em 5px') == {
        'padding-top': '1em',
        'padding-right': '0',
        'padding-bottom': '2em',
        'padding-left': '5px',
    }
    with attest.raises(ValueError):
        expand_shorthand(four_sides_lengths, 'padding', '1 2 3 4 5')

