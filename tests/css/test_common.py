"""Test the CSS parsing, cascade, inherited and computed values."""

import pytest

from weasyprint import CSS, default_url_fetcher
from weasyprint.css import find_stylesheets, get_all_computed_styles
from weasyprint.urls import path2url

from ..testing_utils import (  # isort:skip
    BASE_URL, FakeHTML, assert_no_logs, capture_logs, resource_path)


@assert_no_logs
def test_find_stylesheets():
    html = FakeHTML(resource_path('doc1.html'))

    sheets = list(find_stylesheets(
        html.wrapper_element, 'print', default_url_fetcher, html.base_url,
        font_config=None, counter_style=None, page_rules=None))
    assert len(sheets) == 2
    # Also test that stylesheets are in tree order.
    sheet_names = [
        sheet.base_url.rsplit('/', 1)[-1].rsplit(',', 1)[-1]
        for sheet in sheets]
    assert sheet_names == ['a%7Bcolor%3AcurrentColor%7D', 'doc1.html']

    rules = []
    for sheet in sheets:
        for sheet_rules in sheet.matcher.lower_local_name_selectors.values():
            for rule in sheet_rules:
                rules.append(rule)
        for rule in sheet.page_rules:
            rules.append(rule)
    assert len(rules) == 10

    # TODO: Test that the values are correct too.


@assert_no_logs
def test_annotate_document():
    document = FakeHTML(resource_path('doc1.html'))
    document._ua_stylesheets = (
        lambda *_, **__: [CSS(resource_path('mini_ua.css'))])
    style_for = get_all_computed_styles(
        document, user_stylesheets=[CSS(resource_path('user.css'))])

    # Element objects behave as lists of their children.
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
        ('url', path2url(resource_path('logo_small.png'))),)

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

    assert a['text_decoration_line'] == {'underline'}
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

    # TODO: much more tests here: test that origin and selector precedence
    # and inheritance are correct…


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
    # TODO: ch and ex units don't work with font-face, see computed_values.py.
    # ('1.1ch', 11),
    # ('1.5ex', 12),
))
def test_units(value, width):
    document = FakeHTML(base_url=BASE_URL, string='''
      <style>@font-face {
        src: url(weasyprint.otf); font-family: weasyprint
      }</style>
      <body style="font: 10px weasyprint">
      <p style="margin-left: %s"></p>''' % value)
    page, = document.render().pages
    html, = page._page_box.children
    body, = html.children
    p, = body.children
    assert p.margin_left == width


@pytest.mark.parametrize('media, width, warning', (
    ('@media screen { @page { size: 10px } }', 20, False),
    ('@media print { @page { size: 10px } }', 10, False),
    ('@media ("unknown content") { @page { size: 10px } }', 20, True),
))
def test_media_queries(media, width, warning):
    document = FakeHTML(string='<p>a<span>b')
    with capture_logs() as logs:
        page, = document.render(
            stylesheets=[CSS(string='@page{size:20px}%s' % media)]).pages
    html, = page._page_box.children
    assert html.width == width
    assert (logs if warning else not logs)
