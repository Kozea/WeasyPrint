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
Test the base mechanisms of CSS.

"""

import os.path

from attest import Tests, raises, assert_hook  # pylint: disable=W0611
import cssutils
from cssutils.helper import path2url

from .testing_utils import (
    resource_filename, TestPNGDocument, assert_no_logs, capture_logs)
from .. import css
from ..css.computed_values import used_line_height


SUITE = Tests()
SUITE.context(assert_no_logs)


def parse_html(filename, **kwargs):
    """Parse an HTML file from the test resources and resolve relative URL."""
    # Make a file:// URL
    url = path2url(resource_filename(filename))
    return TestPNGDocument.from_file(url, **kwargs)


@SUITE.test
def test_style_dict():
    """Test a style in a ``dict``."""
    style = css.StyleDict({
        'margin_left': 12,
        'display': 'block'})
    assert style.display == 'block'
    assert style.margin_left == 12
    with raises(KeyError):
        style.position  # pylint: disable=W0104


@SUITE.test
def test_find_stylesheets():
    """Test if the stylesheets are found in a HTML document."""
    document = parse_html('doc1.html')

    sheets = list(css.find_stylesheets(document))
    assert len(sheets) == 3
    # Also test that stylesheets are in tree order
    assert [s.href.rsplit('/', 1)[-1].rsplit(',', 1)[-1] for s in sheets] \
        == ['sheet1.css', 'a%7Bcolor%3AcurrentColor%7D',
            'doc1.html']

    rules = list(rule for sheet in sheets
                      for rule in css.effective_rules(sheet, 'print'))
    assert len(rules) == 9
    # Also test appearance order
    assert [rule.selectorText for rule in rules] \
        == ['a', 'li', 'p', 'ul', 'li', 'a:after', ':first', 'ul',
            'body > h1:first-child']


@SUITE.test
def test_expand_shorthands():
    """Test the expand shorthands."""
    sheet = cssutils.parseFile(resource_filename('sheet2.css'))
    assert sheet.cssRules[0].selectorText == 'li'

    style = sheet.cssRules[0].style
    assert style['margin'] == '2em 0'
    assert style['margin-bottom'] == '3em'
    assert style['margin-left'] == '4em'
    assert not style['margin-top']

    style = dict(
        (name, css.values.as_css([value]))
        for name, (value, _priority) in css.effective_declarations(style))

    assert 'margin' not in style
    assert style['margin_top'] == '2em'
    assert style['margin_right'] == '0'
    assert style['margin_bottom'] == '2em', \
        '3em was before the shorthand, should be masked'
    assert style['margin_left'] == '4em', \
        '4em was after the shorthand, should not be masked'


def parse_css(filename):
    """Parse and return the CSS at ``filename``."""
    return cssutils.parseFile(resource_filename(filename))


@SUITE.test
def test_annotate_document():
    """Test a document with inline style."""
    # Short names for variables are OK here
    # pylint: disable=C0103

    document = parse_html(
        'doc1.html',
        user_stylesheets=[parse_css('user.css')],
        user_agent_stylesheets=[parse_css('mini_ua.css')],
    )

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

    assert h1.background_image == 'file://' \
        + os.path.abspath(resource_filename('logo_small.png'))

    assert h1.font_weight == 700

    # 32px = 1em * font-size: 2em * initial 16px
    assert p.margin_top == 32
    assert p.margin_right == 0
    assert p.margin_bottom == 32
    assert p.margin_left == 0

    # 32px = 2em * initial 16px
    assert ul.margin_top == 32
    assert ul.margin_right == 32
    assert ul.margin_bottom == 32
    assert ul.margin_left == 32

    # thick = 5px, 0.25 inches = 96*.25 = 24px
    assert ul.border_top_width == 0
    assert ul.border_right_width == 5
    assert ul.border_bottom_width == 0
    assert ul.border_left_width == 24

    # 32px = 2em * initial 16px
    # 64px = 4em * initial 16px
    assert li_0.margin_top == 32
    assert li_0.margin_right == 0
    assert li_0.margin_bottom == 32
    assert li_0.margin_left == 64

    assert a.text_decoration == frozenset(['underline'])

    assert a.padding_top == 1
    assert a.padding_right == 2
    assert a.padding_bottom == 3
    assert a.padding_left == 4

    color = a.color
    assert (color.red, color.green, color.blue, color.alpha) == (255, 0, 0, 1)
    # Test the initial border-color: currentColor
    color = a.border_top_color
    assert (color.red, color.green, color.blue, color.alpha) == (255, 0, 0, 1)

    # The href attr should be as in the source, not made absolute.
    assert after.content == [
        ('STRING', ' ['), ('STRING', 'home.html'), ('STRING', ']')]

    # TODO much more tests here: test that origin and selector precedence
    # and inheritance are correct, ...

    # pylint: enable=C0103


@SUITE.test
def test_default_stylesheet():
    """Test if the user-agent stylesheet is used and applied."""
    document = parse_html('doc1.html')
    head_style = document.style_for(document.dom.head)
    assert head_style.display == 'none', \
        'The HTML4 user-agent stylesheet was not applied'


@SUITE.test
def test_page():
    """Test the ``@page`` properties."""
    document = parse_html('doc1.html', user_stylesheets=[
        cssutils.parseString('''
            html {
                color: red;
            }
            @page {
                margin: 10px;
            }
            @page :right {
                color: blue;
                margin-bottom: 12pt;
                font-size: 20px;
                @top-left {
                    width: 10em;
                }
                @top-right {
                    font-size: 10px;
                }
            }
        ''')
    ])

    style = document.style_for('first_left_page')
    assert style.margin_top == 5
    assert style.margin_left == 10
    assert style.margin_bottom == 10
    assert style.color.cssText == 'red'  # inherited from html

    style = document.style_for('first_right_page')
    assert style.margin_top == 5
    assert style.margin_left == 10
    assert style.margin_bottom == 16
    assert style.color.cssText == 'blue'

    style = document.style_for('left_page')
    assert style.margin_top == 10
    assert style.margin_left == 10
    assert style.margin_bottom == 10
    assert style.color.cssText == 'red'  # inherited from html

    style = document.style_for('right_page')
    assert style.margin_top == 10
    assert style.margin_left == 10
    assert style.margin_bottom == 16
    assert style.color.cssText == 'blue'

    style = document.style_for('first_left_page', '@top-left')
    assert style is None

    style = document.style_for('first_right_page', '@top-left')
    assert style.font_size == 20  # inherited from @page
    assert style.width == 200

    style = document.style_for('first_right_page', '@top-right')
    assert style.font_size == 10


@SUITE.test
def test_warnings():
    """Check that appropriate warnings are logged."""
    for source, messages in [
        ('<style>:link { margin: 2cm',
            ['WARNING: Unsupported selector']),
        ('<style>@page foo { margin: 2cm',
            ['WARNING: Unsupported @page selector']),
        ('<link rel=stylesheet href=data:image/png,>',
            ['WARNING: Expected `text/css` for stylsheet at']),
        ('<style>foo { margin-color: red',
            ['WARNING: Ignored declaration', 'unknown property']),
        ('<style>foo { margin-top: red',
            ['WARNING: Ignored declaration', 'invalid value']),
        ('<html style="margin-color: red">',
            ['WARNING: Ignored declaration', 'unknown property']),
        ('<html style="margin-top: red">',
            ['WARNING: Ignored declaration', 'invalid value']),
    ]:
        with capture_logs() as logs:
            TestPNGDocument.from_string(source).style_for('')
        assert len(logs) == 1
        for message in messages:
            assert message in logs[0]


@SUITE.test
def test_error_recovery():
    with capture_logs() as logs:
        document = TestPNGDocument.from_string('''
            <style> html { color red; color: blue; color
        ''')
        html = document.formatting_structure
        assert html.style.color.value == 'blue'

        document = TestPNGDocument.from_string('''
            <html style="color; color: blue; color red">
        ''')
        html = document.formatting_structure
        assert html.style.color.value == 'blue'
    assert len(logs) == 12


@SUITE.test
def test_line_height_inheritance():
    document = TestPNGDocument.from_string('''
        <style>
            html { font-size: 10px; line-height: 140% }
            section { font-size: 10px; line-height: 1.4 }
            div, p { font-size: 20px; vertical-align: 50% }
        </style>
        <body><div><section><p></p></section></div></body>
    ''')
    html = document.formatting_structure
    body, = html.children
    div, = body.children
    section, = div.children
    paragraph, = section.children
    assert html.style.font_size == 10
    assert div.style.font_size == 20
    # 140% of 10px = 14px is inherited from html
    assert used_line_height(div.style) == 14
    assert div.style.vertical_align == 7  # 50 % of 14px

    assert paragraph.style.font_size == 20
    # 1.4 is inherited from p, 1.4 * 20px on em = 28px
    assert used_line_height(paragraph.style) == 28
    assert paragraph.style.vertical_align == 14  # 50% of 28pxhh
