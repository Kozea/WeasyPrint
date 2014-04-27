# coding: utf8
"""
    weasyprint.tests.test_css
    -------------------------

    Test the CSS parsing, cascade, inherited and computed values.

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from pytest import raises

from .testing_utils import (
    resource_filename, assert_no_logs, capture_logs, TestHTML)
from .. import css
from ..css import get_all_computed_styles
from ..css.computed_values import strut_layout
from ..urls import open_data_url, path2url
from .. import CSS, default_url_fetcher


@assert_no_logs
def test_data_url():
    """Test URLs with the "data:" scheme."""
    def parse(url, expected_content, expected_mime_type, expected_charset):
        assert open_data_url(url) == dict(
            string=expected_content,
            mime_type=expected_mime_type,
            encoding=expected_charset,
            redirected_url=url)
    parse('data:,foo', b'foo', 'text/plain', 'US-ASCII')
    parse('data:,foo%22bar', b'foo"bar', 'text/plain', 'US-ASCII')
    parse('data:text/plain,foo', b'foo', 'text/plain', None)
    parse('data:text/html;charset=utf8,<body>', b'<body>', 'text/html', 'utf8')
    parse('data:text/plain;base64,Zm9v', b'foo', 'text/plain', None)
    parse('data:text/plain;base64,Zm9vbw==', b'fooo', 'text/plain', None)
    parse('data:text/plain;base64,Zm9vb28=', b'foooo', 'text/plain', None)
    parse('data:text/plain;base64,Zm9vb29v', b'fooooo', 'text/plain', None)
    parse('data:text/plain;base64,Zm9vbw%3D%3D', b'fooo', 'text/plain', None)
    parse('data:text/plain;base64,Zm9vb28%3D', b'foooo', 'text/plain', None)

    # "From a theoretical point of view, the padding character is not needed,
    #  since the number of missing bytes can be calculated from the number
    #  of Base64 digits."
    # https://en.wikipedia.org/wiki/Base64#Padding

    # The Acid 2 test uses base64 URLs without padding.
    # http://acid2.acidtests.org/
    parse('data:text/plain;base64,Zm9vbw', b'fooo', 'text/plain', None)
    parse('data:text/plain;base64,Zm9vb28', b'foooo', 'text/plain', None)

    with raises(IOError):
        open_data_url('data:foo')


@assert_no_logs
def test_style_dict():
    """Test a style in a ``dict``."""
    style = css.StyleDict({
        'margin_left': 12,
        'display': 'block'})
    assert style.display == 'block'
    assert style.margin_left == 12
    with raises(KeyError):
        style.position  # pylint: disable=W0104


@assert_no_logs
def test_find_stylesheets():
    """Test if the stylesheets are found in a HTML document."""
    document = TestHTML(resource_filename('doc1.html'))

    sheets = list(css.find_stylesheets(
        document.root_element, 'print', default_url_fetcher))
    assert len(sheets) == 2
    # Also test that stylesheets are in tree order
    assert [s.base_url.rsplit('/', 1)[-1].rsplit(',', 1)[-1] for s in sheets] \
        == ['a%7Bcolor%3AcurrentColor%7D', 'doc1.html']

    rules = [rule for sheet in sheets for rule in sheet.rules]
    assert len(rules) == 10
    # Also test appearance order
    assert [
        rule.selector if rule.at_keyword else rule.selector.as_css()
        for rule, _selector_list, _declarations in rules
    ] == [
        'a', 'li', 'p', 'ul', 'li', 'a:after', (None, 'first'), 'ul',
        'body > h1:first-child', 'h1 ~ p ~ ul a:after'
    ]


@assert_no_logs
def test_expand_shorthands():
    """Test the expand shorthands."""
    sheet = CSS(resource_filename('sheet2.css'))
    assert sheet.stylesheet.rules[0].selector.as_css() == 'li'

    style = dict((d.name, d.value.as_css())
                 for d in sheet.stylesheet.rules[0].declarations)
    assert style['margin'] == '2em 0'
    assert style['margin-bottom'] == '3em'
    assert style['margin-left'] == '4em'
    assert 'margin-top' not in style

    style = dict(
        (name, value)
        for _rule, _selectors, declarations in sheet.rules
        for name, value, _priority in declarations)

    assert 'margin' not in style
    assert style['margin_top'] == (2, 'em')
    assert style['margin_right'] == (0, None)
    assert style['margin_bottom'] == (2, 'em'), \
        '3em was before the shorthand, should be masked'
    assert style['margin_left'] == (4, 'em'), \
        '4em was after the shorthand, should not be masked'


@assert_no_logs
def test_annotate_document():
    """Test a document with inline style."""
    # Short names for variables are OK here
    # pylint: disable=C0103
    document = TestHTML(resource_filename('doc1.html'))
    document._ua_stylesheets = lambda: [CSS(resource_filename('mini_ua.css'))]
    style_for = get_all_computed_styles(
        document, user_stylesheets=[CSS(resource_filename('user.css'))])

    # Element objects behave a lists of their children
    _head, body = document.root_element
    h1, p, ul = body
    li_0, _li_1 = ul
    a, = li_0

    h1 = style_for(h1)
    p = style_for(p)
    ul = style_for(ul)
    li_0 = style_for(li_0)
    after = style_for(a, 'after')
    a = style_for(a)

    assert h1.background_image == [
        ('url', path2url(resource_filename('logo_small.png')))]

    assert h1.font_weight == 700
    assert h1.font_size == 40  # 2em

    # x-large * initial = 3/2 * 16 = 24
    assert p.margin_top == (24, 'px')
    assert p.margin_right == (0, 'px')
    assert p.margin_bottom == (24, 'px')
    assert p.margin_left == (0, 'px')
    assert p.background_color == 'currentColor'  # resolved at use-value time.

    # 2em * 1.25ex = 2 * 20 * 1.25 * 0.8 = 40
    # 2.5ex * 1.25ex = 2.5 * 0.8 * 20 * 1.25 * 0.8 = 40
    assert ul.margin_top == (40, 'px')
    assert ul.margin_right == (40, 'px')
    assert ul.margin_bottom == (40, 'px')
    assert ul.margin_left == (40, 'px')

    assert ul.font_weight == 400
    # thick = 5px, 0.25 inches = 96*.25 = 24px
    assert ul.border_top_width == 0
    assert ul.border_right_width == 5
    assert ul.border_bottom_width == 0
    assert ul.border_left_width == 24

    assert li_0.font_weight == 700
    assert li_0.font_size == 8  # 6pt
    assert li_0.margin_top == (16, 'px')  # 2em
    assert li_0.margin_right == (0, 'px')
    assert li_0.margin_bottom == (16, 'px')
    assert li_0.margin_left == (32, 'px')  # 4em

    assert a.text_decoration == frozenset(['underline'])
    assert a.font_weight == 900
    assert a.font_size == 24  # 300% of 8px
    assert a.padding_top == (1, 'px')
    assert a.padding_right == (2, 'px')
    assert a.padding_bottom == (3, 'px')
    assert a.padding_left == (4, 'px')
    assert a.border_top_width == 42
    assert a.border_bottom_width == 42

    assert a.color == (1, 0, 0, 1)
    assert a.border_top_color == 'currentColor'

    # The href attr should be as in the source, not made absolute.
    assert after.content == [
        ('STRING', ' ['), ('STRING', 'home.html'), ('STRING', ']')]
    assert after.background_color == (1, 0, 0, 1)
    assert after.border_top_width == 42
    assert after.border_bottom_width == 3

    # TODO much more tests here: test that origin and selector precedence
    # and inheritance are correct, ...

    # pylint: enable=C0103


@assert_no_logs
def test_page():
    """Test the ``@page`` properties."""
    document = TestHTML(resource_filename('doc1.html'))
    style_for = get_all_computed_styles(
        document, user_stylesheets=[CSS(string='''
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
        ''')])

    style = style_for('first_left_page')
    assert style.margin_top == (5, 'px')
    assert style.margin_left == (10, 'px')
    assert style.margin_bottom == (10, 'px')
    assert style.color == (1, 0, 0, 1)  # red, inherited from html

    style = style_for('first_right_page')
    assert style.margin_top == (5, 'px')
    assert style.margin_left == (10, 'px')
    assert style.margin_bottom == (16, 'px')
    assert style.color == (0, 0, 1, 1)  # blue

    style = style_for('left_page')
    assert style.margin_top == (10, 'px')
    assert style.margin_left == (10, 'px')
    assert style.margin_bottom == (10, 'px')
    assert style.color == (1, 0, 0, 1)  # red, inherited from html

    style = style_for('right_page')
    assert style.margin_top == (10, 'px')
    assert style.margin_left == (10, 'px')
    assert style.margin_bottom == (16, 'px')
    assert style.color == (0, 0, 1, 1)  # blue

    style = style_for('first_left_page', '@top-left')
    assert style is None

    style = style_for('first_right_page', '@top-left')
    assert style.font_size == 20  # inherited from @page
    assert style.width == (200, 'px')

    style = style_for('first_right_page', '@top-right')
    assert style.font_size == 10


@assert_no_logs
def test_warnings():
    """Check that appropriate warnings are logged."""
    for source, messages in [
        (':lipsum { margin: 2cm',
            ['WARNING: Invalid or unsupported selector']),
        ('::lipsum { margin: 2cm',
            ['WARNING: Invalid or unsupported selector']),
        ('@page foo { margin: 2cm',
            ['WARNING: Named pages are not supported yet']),
        ('foo { margin-color: red',
            ['WARNING: Ignored', 'unknown property']),
        ('foo { margin-top: red',
            ['WARNING: Ignored', 'invalid value']),
        ('@import "relative-uri.css',
            ['WARNING: Relative URI reference without a base URI']),
        ('@import "invalid-protocol://absolute-URL',
            ['WARNING: Failed to load stylesheet at']),
    ]:
        with capture_logs() as logs:
            CSS(string=source)
        assert len(logs) == 1
        for message in messages:
            assert message in logs[0]

    html = '<link rel=stylesheet href=invalid-protocol://absolute>'
    with capture_logs() as logs:
        TestHTML(string=html).render()
    assert len(logs) == 1
    assert 'WARNING: Failed to load stylesheet at' in logs[0]


@assert_no_logs
def test_error_recovery():
    with capture_logs() as logs:
        document = TestHTML(string='''
            <style> html { color red; color: blue; color
        ''')
        page, = document.render().pages
        html, = page._page_box.children
        assert html.style.color == (0, 0, 1, 1)  # blue

        document = TestHTML(string='''
            <html style="color; color: blue; color red">
        ''')
        page, = document.render().pages
        html, = page._page_box.children
        assert html.style.color == (0, 0, 1, 1)  # blue
    assert len(logs) == 4


@assert_no_logs
def test_line_height_inheritance():
    document = TestHTML(string='''
        <style>
            html { font-size: 10px; line-height: 140% }
            section { font-size: 10px; line-height: 1.4 }
            div, p { font-size: 20px; vertical-align: 50% }
        </style>
        <body><div><section><p></p></section></div></body>
    ''')
    page, = document.render().pages
    html, = page._page_box.children
    body, = html.children
    div, = body.children
    section, = div.children
    paragraph, = section.children
    assert html.style.font_size == 10
    assert div.style.font_size == 20
    # 140% of 10px = 14px is inherited from html
    assert strut_layout(div.style)[0] == 14
    assert div.style.vertical_align == 7  # 50 % of 14px

    assert paragraph.style.font_size == 20
    # 1.4 is inherited from p, 1.4 * 20px on em = 28px
    assert strut_layout(paragraph.style)[0] == 28
    assert paragraph.style.vertical_align == 14  # 50% of 28px


@assert_no_logs
def test_important():
    document = TestHTML(string='''
        <style>
            p:nth-child(1) { color: lime }
            body p:nth-child(2) { color: red }

            p:nth-child(3) { color: lime !important }
            body p:nth-child(3) { color: red }

            body p:nth-child(5) { color: lime }
            p:nth-child(5) { color: red }

            p:nth-child(6) { color: red }
            p:nth-child(6) { color: lime }
        </style>
        <p></p>
        <p></p>
        <p></p>
        <p></p>
        <p></p>
        <p></p>
    ''')
    page, = document.render(stylesheets=[CSS(string='''
        body p:nth-child(1) { color: red }
        p:nth-child(2) { color: lime !important }

        p:nth-child(4) { color: lime !important }
        body p:nth-child(4) { color: red }
    ''')]).pages
    html, = page._page_box.children
    body, = html.children
    for paragraph in body.children:
        assert paragraph.style.color == (0, 1, 0, 1)  # lime (light green)


@assert_no_logs
def test_units():
    document = TestHTML(string='''
        <p style="margin-left: 96px"></p>
        <p style="margin-left: 1in"></p>
        <p style="margin-left: 72pt"></p>
        <p style="margin-left: 6pc"></p>
        <p style="margin-left: 2.54cm"></p>
        <p style="margin-left: 25.4mm"></p>
        <p style="margin-left: 1.1em"></p>
        <p style="margin-left: 1.1ch; font: 14px Ahem"></p>
        <p style="margin-left: 1.5ex; font: 10px Ahem"></p>
        <p style="margin-left: 1.1ch"></p>
    ''')
    page, = document.render().pages
    html, = page._page_box.children
    body, = html.children
    margins = [round(p.margin_left, 6) for p in body.children]
    default_font_ch = margins.pop()
    # Ahem: 1ex is 0.8em, 1ch is 1em
    assert margins == [96, 96, 96, 96, 96, 96, 17.6, 15.4, 12]
    assert 4 < default_font_ch < 12  # for 1em = 16px
