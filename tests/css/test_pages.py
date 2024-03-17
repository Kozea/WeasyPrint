"""Test CSS pages."""

import pytest
import tinycss2

from weasyprint import CSS
from weasyprint.css import PageType, get_all_computed_styles, parse_page_selectors
from weasyprint.layout.page import set_page_type_computed_styles

from ..testing_utils import FakeHTML, assert_no_logs, render_pages, resource_path


@assert_no_logs
def test_page():
    document = FakeHTML(resource_path('doc1.html'))
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
def test_named_pages():
    page, = render_pages('''
      <style>
        @page NARRow { size: landscape }
        div { page: AUTO }
        p { page: NARRow }
      </style>
      <div><p><span>a</span></p></div>
    ''')
    html, = page.children
    body, = html.children
    div, = body.children
    p, = div.children
    span, = p.children
    assert html.style['page'] == ''
    assert body.style['page'] == ''
    assert div.style['page'] == ''
    assert p.style['page'] == 'NARRow'
    assert span.style['page'] == 'NARRow'
