"""
    weasyprint.tests.test_variables
    -------------------------------

    Test CSS custom proproperties, also known as CSS variables.

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from .test_boxes import render_pages as parse


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
