"""Test CSS custom proproperties, also known as CSS variables."""

import pytest
from weasyprint.css.properties import KNOWN_PROPERTIES

from .testing_utils import assert_no_logs, render_pages

SIDES = ('top', 'right', 'bottom', 'left')


@assert_no_logs
def test_variable_simple():
    page, = render_pages('''
      <style>
        p { --var: 10px; width: var(--var) }
      </style>
      <p></p>
    ''')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    assert paragraph.width == 10


@assert_no_logs
def test_variable_not_computed():
    page, = render_pages('''
      <style>
        p { --var: 1rem; width: var(--var) }
      </style>
      <p></p>
    ''')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    assert paragraph.width == 16


@assert_no_logs
def test_variable_inherit():
    page, = render_pages('''
      <style>
        html { --var: 10px }
        p { width: var(--var) }
      </style>
      <p></p>
    ''')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    assert paragraph.width == 10


@assert_no_logs
def test_variable_inherit_override():
    page, = render_pages('''
      <style>
        html { --var: 20px }
        p { width: var(--var); --var: 10px }
      </style>
      <p></p>
    ''')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    assert paragraph.width == 10


@assert_no_logs
def test_variable_case_sensitive():
    page, = render_pages('''
      <style>
        html { --var: 20px }
        body { --VAR: 10px }
        p { width: var(--VAR) }
      </style>
      <p></p>
    ''')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    assert paragraph.width == 10


@assert_no_logs
def test_variable_chain():
    page, = render_pages('''
      <style>
        html { --foo: 10px }
        body { --var: var(--foo) }
        p { width: var(--var) }
      </style>
      <p></p>
    ''')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    assert paragraph.width == 10


@assert_no_logs
def test_variable_chain_root():
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/1656
    page, = render_pages('''
      <style>
        html { --var2: 10px; --var1: var(--var2); width: var(--var1) }
      </style>
    ''')
    html, = page.children
    assert html.width == 10


def test_variable_chain_root_missing():
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/1656
    page, = render_pages('''
      <style>
        html { --var1: var(--var-missing); width: var(--var1) }
      </style>
    ''')


@assert_no_logs
def test_variable_partial_1():
    page, = render_pages('''
      <style>
        html { --var: 10px }
        div { margin: 0 0 0 var(--var) }
      </style>
      <div></div>
    ''')
    html, = page.children
    body, = html.children
    div, = body.children
    assert div.margin_top == 0
    assert div.margin_right == 0
    assert div.margin_bottom == 0
    assert div.margin_left == 10


@assert_no_logs
def test_variable_initial():
    page, = render_pages('''
      <style>
        html { --var: initial }
        p { width: var(--var, 10px) }
      </style>
      <p></p>
    ''')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    assert paragraph.width == 10


@pytest.mark.parametrize('prop', sorted(KNOWN_PROPERTIES))
def test_variable_fallback(prop):
    render_pages('''
      <style>
        div {
          --var: improperValue;
          %s: var(--var);
        }
      </style>
      <div></div>
    ''' % prop)


@assert_no_logs
def test_variable_list():
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/1287
    page, = render_pages('''
      <style>
        :root { --var: "Page " counter(page) "/" counter(pages) }
        div::before { content: var(--var) }
      </style>
      <div></div>
    ''')
    html, = page.children
    body, = html.children
    div, = body.children
    line, = div.children
    before, = line.children
    text, = before.children
    assert text.text == 'Page 1/1'
