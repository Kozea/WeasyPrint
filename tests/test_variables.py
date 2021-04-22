"""
    weasyprint.tests.test_variables
    -------------------------------

    Test CSS custom proproperties, also known as CSS variables.

"""

import pytest
from weasyprint.css.properties import KNOWN_PROPERTIES

from .testing_utils import render_pages as parse

SIDES = ('top', 'right', 'bottom', 'left')


def test_variable_simple():
    page, = parse('''
      <style>
        p { --var: 10px; width: var(--var) }
      </style>
      <p></p>
    ''')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    assert paragraph.width == 10


def test_variable_inherit():
    page, = parse('''
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


def test_variable_inherit_override():
    page, = parse('''
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


def test_variable_case_sensitive():
    page, = parse('''
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


def test_variable_chain():
    page, = parse('''
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


def test_variable_partial_1():
    page, = parse('''
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


def test_variable_initial():
    page, = parse('''
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
    parse('''
      <style>
        div {
          --var: improperValue;
          %s: var(--var);
        }
      </style>
      <div></div>
    ''' % prop)
