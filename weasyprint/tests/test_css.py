"""
    weasyprint.tests.test_css
    -------------------------

    Test the CSS parsing, cascade, inherited and computed values.

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import pytest
import tinycss2

from .. import CSS, css, default_url_fetcher
from ..css import PageType, get_all_computed_styles, parse_page_selectors
from ..css.computed_values import strut_layout
from ..layout.pages import set_page_type_computed_styles
from ..urls import path2url
from .testing_utils import (
    BASE_URL, FakeHTML, assert_no_logs, capture_logs, resource_filename)


@assert_no_logs
def test_style_dict():
    style = {'margin_left': 12, 'display': 'block'}
    assert style['display'] == 'block'
    assert style['margin_left'] == 12
    with pytest.raises(KeyError):
        style['position']


@assert_no_logs
def test_find_stylesheets():
    html = FakeHTML(resource_filename('doc1.html'))

    sheets = list(css.find_stylesheets(
        html.wrapper_element, 'print', default_url_fetcher, html.base_url,
        font_config=None, page_rules=None))
    assert len(sheets) == 2
    # Also test that stylesheets are in tree order
    assert [s.base_url.rsplit('/', 1)[-1].rsplit(',', 1)[-1] for s in sheets] \
        == ['a%7Bcolor%3AcurrentColor%7D', 'doc1.html']

    rules = []
    for sheet in sheets:
        for sheet_rules in sheet.matcher.lower_local_name_selectors.values():
            for rule in sheet_rules:
                rules.append(rule)
        for rule in sheet.page_rules:
            rules.append(rule)
    assert len(rules) == 10

    # TODO: test that the values are correct too


@assert_no_logs
def test_expand_shorthands():
    sheet = CSS(resource_filename('sheet2.css'))
    assert list(sheet.matcher.lower_local_name_selectors) == ['li']

    rules = sheet.matcher.lower_local_name_selectors['li'][0][4]
    assert rules[0][0] == 'margin_bottom'
    assert rules[0][1] == (3, 'em')
    assert rules[1][0] == 'margin_top'
    assert rules[1][1] == (2, 'em')
    assert rules[2][0] == 'margin_right'
    assert rules[2][1] == (0, None)
    assert rules[3][0] == 'margin_bottom'
    assert rules[3][1] == (2, 'em')
    assert rules[4][0] == 'margin_left'
    assert rules[4][1] == (0, None)
    assert rules[5][0] == 'margin_left'
    assert rules[5][1] == (4, 'em')

    # TODO: test that the values are correct too


@assert_no_logs
def test_annotate_document():
    document = FakeHTML(resource_filename('doc1.html'))
    document._ua_stylesheets = lambda: [CSS(resource_filename('mini_ua.css'))]
    style_for = get_all_computed_styles(
        document, user_stylesheets=[CSS(resource_filename('user.css'))])

    # Element objects behave a lists of their children
    _head, body = document.etree_element
    h1, p, ul, div = body
    li_0, _li_1 = ul
    a, = li_0
    span1, = div
    span2, = span1

    h1 = style_for(h1)
    p = style_for(p)
    ul = style_for(ul)
    li_0 = style_for(li_0)
    div = style_for(div)
    after = style_for(a, 'after')
    a = style_for(a)
    span1 = style_for(span1)
    span2 = style_for(span2)

    assert h1['background_image'] == (
        ('url', path2url(resource_filename('logo_small.png'))),)

    assert h1['font_weight'] == 700
    assert h1['font_size'] == 40  # 2em

    # x-large * initial = 3/2 * 16 = 24
    assert p['margin_top'] == (24, 'px')
    assert p['margin_right'] == (0, 'px')
    assert p['margin_bottom'] == (24, 'px')
    assert p['margin_left'] == (0, 'px')
    assert p['background_color'] == 'currentColor'

    # 2em * 1.25ex = 2 * 20 * 1.25 * 0.8 = 40
    # 2.5ex * 1.25ex = 2.5 * 0.8 * 20 * 1.25 * 0.8 = 40
    # TODO: ex unit doesn't work with @font-face fonts, see computed_values.py
    # assert ul['margin_top'] == (40, 'px')
    # assert ul['margin_right'] == (40, 'px')
    # assert ul['margin_bottom'] == (40, 'px')
    # assert ul['margin_left'] == (40, 'px')

    assert ul['font_weight'] == 400
    # thick = 5px, 0.25 inches = 96*.25 = 24px
    assert ul['border_top_width'] == 0
    assert ul['border_right_width'] == 5
    assert ul['border_bottom_width'] == 0
    assert ul['border_left_width'] == 24

    assert li_0['font_weight'] == 700
    assert li_0['font_size'] == 8  # 6pt
    assert li_0['margin_top'] == (16, 'px')  # 2em
    assert li_0['margin_right'] == (0, 'px')
    assert li_0['margin_bottom'] == (16, 'px')
    assert li_0['margin_left'] == (32, 'px')  # 4em

    assert a['text_decoration'] == frozenset(['underline'])
    assert a['font_weight'] == 900
    assert a['font_size'] == 24  # 300% of 8px
    assert a['padding_top'] == (1, 'px')
    assert a['padding_right'] == (2, 'px')
    assert a['padding_bottom'] == (3, 'px')
    assert a['padding_left'] == (4, 'px')
    assert a['border_top_width'] == 42
    assert a['border_bottom_width'] == 42

    assert a['color'] == (1, 0, 0, 1)
    assert a['border_top_color'] == 'currentColor'

    assert div['font_size'] == 40  # 2 * 20px
    assert span1['width'] == (160, 'px')  # 10 * 16px (root default is 16px)
    assert span1['height'] == (400, 'px')  # 10 * (2 * 20px)
    assert span2['font_size'] == 32

    # The href attr should be as in the source, not made absolute.
    assert after['content'] == (
        ('string', ' ['), ('string', 'home.html'), ('string', ']'))
    assert after['background_color'] == (1, 0, 0, 1)
    assert after['border_top_width'] == 42
    assert after['border_bottom_width'] == 3

    # TODO much more tests here: test that origin and selector precedence
    # and inheritance are correct, ...


@assert_no_logs
def test_page():
    document = FakeHTML(resource_filename('doc1.html'))
    style_for = get_all_computed_styles(
        document, user_stylesheets=[CSS(string='''
          html { color: red }
          @page { margin: 10px }
          @page :right {
            color: blue;
            margin-bottom: 12pt;
            font-size: 20px;
            @top-left { width: 10em }
            @top-right { font-size: 10px}
          }
        ''')])

    page_type = PageType(
        side='left', first=True, blank=False, index=0, name='')
    set_page_type_computed_styles(page_type, document, style_for)
    style = style_for(page_type)
    assert style['margin_top'] == (5, 'px')
    assert style['margin_left'] == (10, 'px')
    assert style['margin_bottom'] == (10, 'px')
    assert style['color'] == (1, 0, 0, 1)  # red, inherited from html

    page_type = PageType(
        side='right', first=True, blank=False, index=0, name='')
    set_page_type_computed_styles(page_type, document, style_for)
    style = style_for(page_type)
    assert style['margin_top'] == (5, 'px')
    assert style['margin_left'] == (10, 'px')
    assert style['margin_bottom'] == (16, 'px')
    assert style['color'] == (0, 0, 1, 1)  # blue

    page_type = PageType(
        side='left', first=False, blank=False, index=1, name='')
    set_page_type_computed_styles(page_type, document, style_for)
    style = style_for(page_type)
    assert style['margin_top'] == (10, 'px')
    assert style['margin_left'] == (10, 'px')
    assert style['margin_bottom'] == (10, 'px')
    assert style['color'] == (1, 0, 0, 1)  # red, inherited from html

    page_type = PageType(
        side='right', first=False, blank=False, index=1, name='')
    set_page_type_computed_styles(page_type, document, style_for)
    style = style_for(page_type)
    assert style['margin_top'] == (10, 'px')
    assert style['margin_left'] == (10, 'px')
    assert style['margin_bottom'] == (16, 'px')
    assert style['color'] == (0, 0, 1, 1)  # blue

    page_type = PageType(
        side='left', first=True, blank=False, index=0, name='')
    set_page_type_computed_styles(page_type, document, style_for)
    style = style_for(page_type, '@top-left')
    assert style is None

    page_type = PageType(
        side='right', first=True, blank=False, index=0, name='')
    set_page_type_computed_styles(page_type, document, style_for)
    style = style_for(page_type, '@top-left')
    assert style['font_size'] == 20  # inherited from @page
    assert style['width'] == (200, 'px')

    page_type = PageType(
        side='right', first=True, blank=False, index=0, name='')
    set_page_type_computed_styles(page_type, document, style_for)
    style = style_for(page_type, '@top-right')
    assert style['font_size'] == 10


@assert_no_logs
@pytest.mark.parametrize('style, selectors', (
    ('@page {}', [{
        'side': None, 'blank': None, 'first': None, 'name': None,
        'index': None, 'specificity': [0, 0, 0]}]),
    ('@page :left {}', [{
        'side': 'left', 'blank': None, 'first': None, 'name': None,
        'index': None, 'specificity': [0, 0, 1]}]),
    ('@page:first:left {}', [{
        'side': 'left', 'blank': None, 'first': True, 'name': None,
        'index': None, 'specificity': [0, 1, 1]}]),
    ('@page pagename {}', [{
        'side': None, 'blank': None, 'first': None, 'name': 'pagename',
        'index': None, 'specificity': [1, 0, 0]}]),
    ('@page pagename:first:right:blank {}', [{
        'side': 'right', 'blank': True, 'first': True, 'name': 'pagename',
        'index': None, 'specificity': [1, 2, 1]}]),
    ('@page pagename, :first {}', [
        {'side': None, 'blank': None, 'first': None, 'name': 'pagename',
         'index': None, 'specificity': [1, 0, 0]},
        {'side': None, 'blank': None, 'first': True, 'name': None,
         'index': None, 'specificity': [0, 1, 0]}]),
    ('@page :first:first {}', [{
        'side': None, 'blank': None, 'first': True, 'name': None,
        'index': None, 'specificity': [0, 2, 0]}]),
    ('@page :left:left {}', [{
        'side': 'left', 'blank': None, 'first': None, 'name': None,
        'index': None, 'specificity': [0, 0, 2]}]),
    ('@page :nth(2) {}', [{
        'side': None, 'blank': None, 'first': None, 'name': None,
        'index': (0, 2, None), 'specificity': [0, 1, 0]}]),
    ('@page :nth(2n + 4) {}', [{
        'side': None, 'blank': None, 'first': None, 'name': None,
        'index': (2, 4, None), 'specificity': [0, 1, 0]}]),
    ('@page :nth(3n) {}', [{
        'side': None, 'blank': None, 'first': None, 'name': None,
        'index': (3, 0, None), 'specificity': [0, 1, 0]}]),
    ('@page :nth( n+2 ) {}', [{
        'side': None, 'blank': None, 'first': None, 'name': None,
        'index': (1, 2, None), 'specificity': [0, 1, 0]}]),
    ('@page :nth(even) {}', [{
        'side': None, 'blank': None, 'first': None, 'name': None,
        'index': (2, 0, None), 'specificity': [0, 1, 0]}]),
    ('@page pagename:nth(2) {}', [{
        'side': None, 'blank': None, 'first': None, 'name': 'pagename',
        'index': (0, 2, None), 'specificity': [1, 1, 0]}]),
    ('@page page page {}', None),
    ('@page :left page {}', None),
    ('@page :left, {}', None),
    ('@page , {}', None),
    ('@page :left, test, {}', None),
    ('@page :wrong {}', None),
    ('@page :left:wrong {}', None),
    ('@page :left:right {}', None),
))
def test_page_selectors(style, selectors):
    at_rule, = tinycss2.parse_stylesheet(style)
    assert parse_page_selectors(at_rule) == selectors


@assert_no_logs
@pytest.mark.parametrize('source, messages', (
    (':lipsum { margin: 2cm', ['WARNING: Invalid or unsupported selector']),
    ('::lipsum { margin: 2cm', ['WARNING: Invalid or unsupported selector']),
    ('foo { margin-color: red', ['WARNING: Ignored', 'unknown property']),
    ('foo { margin-top: red', ['WARNING: Ignored', 'invalid value']),
    ('@import "relative-uri.css',
     ['ERROR: Relative URI reference without a base URI']),
    ('@import "invalid-protocol://absolute-URL',
     ['ERROR: Failed to load stylesheet at']),
))
def test_warnings(source, messages):
    """Check that appropriate warnings are logged."""
    with capture_logs() as logs:
        CSS(string=source)
    assert len(logs) == 1, source
    for message in messages:
        assert message in logs[0]


@assert_no_logs
def test_warnings_stylesheet():
    html = '<link rel=stylesheet href=invalid-protocol://absolute>'
    with capture_logs() as logs:
        FakeHTML(string=html).render()
    assert len(logs) == 1
    assert 'ERROR: Failed to load stylesheet at' in logs[0]


@assert_no_logs
@pytest.mark.parametrize('style', (
    '<style> html { color red; color: blue; color',
    '<html style="color; color: blue; color red">',
))
def test_error_recovery(style):
    with capture_logs() as logs:
        document = FakeHTML(string=style)
        page, = document.render().pages
        html, = page._page_box.children
        assert html.style['color'] == (0, 0, 1, 1)  # blue
    assert len(logs) == 2


@assert_no_logs
def test_line_height_inheritance():
    document = FakeHTML(string='''
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
    assert html.style['font_size'] == 10
    assert div.style['font_size'] == 20
    # 140% of 10px = 14px is inherited from html
    assert strut_layout(div.style)[0] == 14
    assert div.style['vertical_align'] == 7  # 50 % of 14px

    assert paragraph.style['font_size'] == 20
    # 1.4 is inherited from p, 1.4 * 20px on em = 28px
    assert strut_layout(paragraph.style)[0] == 28
    assert paragraph.style['vertical_align'] == 14  # 50% of 28px


@assert_no_logs
def test_important():
    document = FakeHTML(string='''
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
        assert paragraph.style['color'] == (0, 1, 0, 1)  # lime (light green)


@assert_no_logs
def test_named_pages():
    document = FakeHTML(string='''
      <style>
        @page NARRow { size: landscape }
        div { page: AUTO }
        p { page: NARRow }
      </style>
      <div><p><span>a</span></p></div>
    ''')
    page, = document.render().pages
    html, = page._page_box.children
    body, = html.children
    div, = body.children
    p, = div.children
    span, = p.children
    assert html.style['page'] == ''
    assert body.style['page'] == ''
    assert div.style['page'] == ''
    assert p.style['page'] == 'NARRow'
    assert span.style['page'] == 'NARRow'


@assert_no_logs
@pytest.mark.parametrize('value, width', (
    ('96px', 96),
    ('1in', 96),
    ('72pt', 96),
    ('6pc', 96),
    ('2.54cm', 96),
    ('25.4mm', 96),
    ('101.6q', 96),
    ('1.1em', 11),
    ('1.1rem', 17.6),
    # TODO: ch and ex units don't work with font-face, see computed_values.py
    # ('1.1ch', 11),
    # ('1.5ex', 12),
))
def test_units(value, width):
    document = FakeHTML(base_url=BASE_URL, string='''
      <style>@font-face { src: url(AHEM____.TTF); font-family: ahem }</style>
      <body style="font: 10px ahem"><p style="margin-left: %s"></p>''' % value)
    page, = document.render().pages
    html, = page._page_box.children
    body, = html.children
    p, = body.children
    assert p.margin_left == width
