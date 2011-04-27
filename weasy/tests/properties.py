# coding: utf8

import attest
from attest import Tests, assert_hook
from cssutils.css import Property

from ..properties import four_sides_lengths


suite = Tests()


def expand_shorthand(expander, name, value):
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

