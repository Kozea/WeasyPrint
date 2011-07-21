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

import os.path
from cssutils.helper import path2url

from attest import Tests, assert_hook
import attest
import cssutils

from .. import css
from ..css import shorthands
from ..document import Document

from . import resource_filename


suite = Tests()


def parse_html(filename):
    """Parse an HTML file from the test resources and resolve relative URL."""
    return Document.from_file(path2url(resource_filename(filename)))


@suite.test
def test_style_dict():
    style = css.StyleDict({
        'margin-left': cssutils.css.PropertyValue('12px'),
        'display': cssutils.css.PropertyValue('block')
    })
    assert style.display == 'block'
    assert style.margin_left == 12
    with attest.raises(AttributeError):
        style.position


@suite.test
def test_find_stylesheets():
    document = parse_html('doc1.html')

    sheets = list(css.find_stylesheets(document))
    assert len(sheets) == 2
    # Also test that stylesheets are in tree order
    assert [s.href.rsplit('/', 1)[-1] for s in sheets] \
        == ['sheet1.css', 'doc1.html']

    rules = list(rule for sheet in sheets
                      for rule in css.effective_rules(sheet, 'print'))
    assert len(rules) == 8
    # Also test appearance order
    assert [rule.selectorText for rule in rules] \
        == ['li', 'p', 'ul', 'a', 'a:after', ':first', 'ul',
            'body > h1:first-child']


def expand_shorthands(declaration_block):
    return dict(
        expanded
        for declaration in declaration_block
        for expanded in shorthands.expand_shorthand(declaration))


@suite.test
def test_expand_shorthands():
    sheet = cssutils.parseFile(resource_filename('sheet2.css'))
    assert sheet.cssRules[0].selectorText == 'li'

    style = sheet.cssRules[0].style
    assert style['margin'] == '2em 0'
    assert style['margin-bottom'] == '3em'
    assert style['margin-left'] == '4em'
    assert not style['margin-top']

    style = expand_shorthands(style)
    assert 'margin' not in style
    assert style['margin-top'].value == '2em'
    assert style['margin-right'].value == '0'
    assert style['margin-bottom'].value == '2em', \
        "3em was before the shorthand, should be masked"
    assert style['margin-left'].value == '4em', \
        "4em was after the shorthand, should not be masked"


@suite.test
def test_annotate_document():
    user_stylesheet = cssutils.parseFile(resource_filename('user.css'))
    ua_stylesheet = cssutils.parseFile(resource_filename('mini_ua.css'))
    document = parse_html('doc1.html')

    document.do_css(user_stylesheets=[user_stylesheet],
                    ua_stylesheets=[ua_stylesheet])

    # Element objects behave a lists of their children
    _head, body = document.dom
    h1, p, ul = body
    li_0, _li_1 = ul
    a, = li_0

    h1 = document.style_for(h1)
    p = document.style_for(p)
    ul = document.style_for(ul)
    li_0 = document.style_for(li_0)
    after = document.style_for(a, 'after')
    a = document.style_for(a)

    assert h1['background-image'][0].absoluteUri == 'file://' \
        + os.path.abspath(resource_filename('logo_small.png'))

    assert h1.font_weight == '700'

    sides = ('-top', '-right', '-bottom', '-left')
    # 32px = 1em * font-size: 2em * initial 16px
    for side, expected_value in zip(sides, ('32px', '0', '32px', '0')):
        assert p['margin' + side].value == expected_value

    # 32px = 2em * initial 16px
    for side, expected_value in zip(sides, ('32px', '32px', '32px', '32px')):
        assert ul['margin' + side].value == expected_value

    # thick = 5px, 0.25 inches = 96*.25 = 24px
    for side, expected_value in zip(sides, ('0', '5px', '0', '24px')):
        assert ul['border' + side + '-width'].value == expected_value

    # 32px = 2em * initial 16px
    # 64px = 4em * initial 16px
    for side, expected_value in zip(sides, ('32px', '0', '32px', '64px')):
        assert li_0['margin' + side].value == expected_value

    assert a.text_decoration == 'underline'

    color = a['color'][0]
    assert (color.red, color.green, color.blue, color.alpha) == (255, 0, 0, 1)
    assert a.padding_top == 1
    assert a.padding_right == 2
    assert a.padding_bottom == 3
    assert a.padding_left == 4

    # The href attr should be as in the source, not made absolute.
    assert ''.join(v.value for v in after['content']) == ' [home.html]'

    # TODO much more tests here: test that origin and selector precedence
    # and inheritance are correct, ...


@suite.test
def test_default_stylesheet():
    document = parse_html('doc1.html')
    document.do_css()
    head_style = document.style_for(document.dom.head)
    assert head_style.display == 'none', \
        'The HTML4 user-agent stylesheet was not applied'


@suite.test
def test_page():
    document = parse_html('doc1.html')
    user_sheet = cssutils.parseString(u"""
        @page {
            margin: 10px;
        }
        @page :right {
            margin-bottom: 12pt;
        }
    """)
    document.do_css(user_stylesheets=[user_sheet])

    style = document.style_for('@page', 'first_left')
    assert style.margin_top == 5
    assert style.margin_left == 10
    assert style.margin_bottom == 10

    style = document.style_for('@page', 'first_right')
    assert style.margin_top == 5
    assert style.margin_left == 10
    assert style.margin_bottom == 16

    style = document.style_for('@page', 'left')
    assert style.margin_top == 10
    assert style.margin_left == 10
    assert style.margin_bottom == 10

    style = document.style_for('@page', 'right')
    assert style.margin_top == 10
    assert style.margin_left == 10
    assert style.margin_bottom == 16
