"""Test CSS custom proproperties, also known as CSS variables."""

import pytest
from weasyprint.css.properties import KNOWN_PROPERTIES

from .testing_utils import assert_no_logs, capture_logs, render_pages

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
def test_variable_shorthand_margin():
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
def test_variable_shorthand_margin_multiple():
    page, = render_pages('''
      <style>
        html { --var1: 10px; --var2: 20px }
        div { margin: var(--var2) 0 0 var(--var1) }
      </style>
      <div></div>
    ''')
    html, = page.children
    body, = html.children
    div, = body.children
    assert div.margin_top == 20
    assert div.margin_right == 0
    assert div.margin_bottom == 0
    assert div.margin_left == 10


@assert_no_logs
def test_variable_shorthand_margin_invalid():
    with capture_logs() as logs:
        page, = render_pages('''
          <style>
            html { --var: blue }
            div { margin: 0 0 0 var(--var) }
          </style>
          <div></div>
        ''')
        log, = logs
        assert 'invalid value' in log
    html, = page.children
    body, = html.children
    div, = body.children
    assert div.margin_top == 0
    assert div.margin_right == 0
    assert div.margin_bottom == 0
    assert div.margin_left == 0


@assert_no_logs
def test_variable_shorthand_border():
    page, = render_pages('''
      <style>
        html { --var: 1px solid blue }
        div { border: var(--var) }
      </style>
      <div></div>
    ''')
    html, = page.children
    body, = html.children
    div, = body.children
    assert div.border_top_width == 1
    assert div.border_right_width == 1
    assert div.border_bottom_width == 1
    assert div.border_left_width == 1


@assert_no_logs
def test_variable_shorthand_border_side():
    page, = render_pages('''
      <style>
        html { --var: 1px solid blue }
        div { border-top: var(--var) }
      </style>
      <div></div>
    ''')
    html, = page.children
    body, = html.children
    div, = body.children
    assert div.border_top_width == 1
    assert div.border_right_width == 0
    assert div.border_bottom_width == 0
    assert div.border_left_width == 0


@assert_no_logs
def test_variable_shorthand_border_mixed():
    page, = render_pages('''
      <style>
        html { --var: 1px solid }
        div { border: blue var(--var) }
      </style>
      <div></div>
    ''')
    html, = page.children
    body, = html.children
    div, = body.children
    assert div.border_top_width == 1
    assert div.border_right_width == 1
    assert div.border_bottom_width == 1
    assert div.border_left_width == 1


def test_variable_shorthand_border_mixed_invalid():
    with capture_logs() as logs:
        page, = render_pages('''
          <style>
            html { --var: 1px solid blue }
            div { border: blue var(--var) }
          </style>
          <div></div>
        ''')
        # TODO: we should only get one warning here
        assert 'multiple color values' in logs[0]
    html, = page.children
    body, = html.children
    div, = body.children
    assert div.border_top_width == 0
    assert div.border_right_width == 0
    assert div.border_bottom_width == 0
    assert div.border_left_width == 0


@assert_no_logs
@pytest.mark.parametrize('var, background', (
    ('blue', 'var(--v)'),
    ('padding-box url(pattern.png)', 'var(--v)'),
    ('padding-box url(pattern.png)', 'white var(--v) center'),
    ('100%', 'url(pattern.png) var(--v) var(--v) / var(--v) var(--v)'),
    ('left / 100%', 'url(pattern.png) top var(--v) 100%'),
))
def test_variable_shorthand_background(var, background):
    page, = render_pages('''
      <style>
        html { --v: %s }
        div { background: %s }
      </style>
      <div></div>
    ''' % (var, background))


@pytest.mark.parametrize('var, background', (
    ('invalid', 'var(--v)'),
    ('blue', 'var(--v) var(--v)'),
    ('100%', 'url(pattern.png) var(--v) var(--v) var(--v)'),
))
def test_variable_shorthand_background_invalid(var, background):
    with capture_logs() as logs:
        page, = render_pages('''
          <style>
            html { --v: %s }
            div { background: %s }
          </style>
          <div></div>
        ''' % (var, background))
        log, = logs
        assert 'invalid value' in log


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
def test_variable_list_content():
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


@assert_no_logs
@pytest.mark.parametrize('var, display', (
    ('inline', 'var(--var)'),
    ('inline-block', 'var(--var)'),
    ('inline flow', 'var(--var)'),
    ('inline', 'var(--var) flow'),
    ('flow', 'inline var(--var)'),
))
def test_variable_list_display(var, display):
    page, = render_pages('''
      <style>
        html { --var: %s }
        div { display: %s }
      </style>
      <section><div></div></section>
    ''' % (var, display))
    html, = page.children
    body, = html.children
    section, = body.children
    child, = section.children
    assert type(child).__name__ == 'LineBox'


@assert_no_logs
@pytest.mark.parametrize('var, font', (
    ('weasyprint', 'var(--var)'),
    ('"weasyprint"', 'var(--var)'),
    ('weasyprint', 'var(--var), monospace'),
    ('weasyprint, monospace', 'var(--var)'),
    ('monospace', 'weasyprint, var(--var)'),
))
def test_variable_list_font(var, font):
    page, = render_pages('''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        html { font-size: 2px; --var: %s }
        div { font-family: %s }
      </style>
      <div>aa</div>
    ''' % (var, font))
    html, = page.children
    body, = html.children
    div, = body.children
    line, = div.children
    text, = line.children
    assert text.width == 4
