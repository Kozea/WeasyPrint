"""Test CSS font-related properties."""

from math import isclose

import pytest

from weasyprint import CSS
from weasyprint.css import get_all_computed_styles
from weasyprint.css.computed_values import strut_layout

from ..testing_utils import FakeHTML, assert_no_logs, render_pages


@assert_no_logs
@pytest.mark.parametrize('parent_css, parent_size, child_css, child_size', (
    ('10px', 10, '10px', 10),
    ('x-small', 12, 'xx-large', 32),
    ('x-large', 24, '2em', 48),
    ('1em', 16, '1em', 16),
    ('1em', 16, 'larger', 6 / 5 * 16),
    ('medium', 16, 'larger', 6 / 5 * 16),
    ('x-large', 24, 'larger', 32),
    ('xx-large', 32, 'larger', 1.2 * 32),
    ('1px', 1, 'larger', 3 / 5 * 16),
    ('28px', 28, 'larger', 32),
    ('100px', 100, 'larger', 120),
    ('xx-small', 3 / 5 * 16, 'larger', 12),
    ('1em', 16, 'smaller', 8 / 9 * 16),
    ('medium', 16, 'smaller', 8 / 9 * 16),
    ('x-large', 24, 'smaller', 6 / 5 * 16),
    ('xx-large', 32, 'smaller', 24),
    ('xx-small', 3 / 5 * 16, 'smaller', 0.8 * 3 / 5 * 16),
    ('1px', 1, 'smaller', 0.8),
    ('28px', 28, 'smaller', 24),
    ('100px', 100, 'smaller', 32),
))
def test_font_size(parent_css, parent_size, child_css, child_size):
    document = FakeHTML(string='<p>a<span>b')
    style_for = get_all_computed_styles(document, user_stylesheets=[CSS(
        string='p{font-size:%s}span{font-size:%s}' % (parent_css, child_css))])

    _head, body = document.etree_element
    p, = body
    span, = p
    assert isclose(style_for(p)['font_size'], parent_size)
    assert isclose(style_for(span)['font_size'], child_size)


@assert_no_logs
def test_line_height_inheritance():
    page, = render_pages('''
      <style>
        html { font-size: 10px; line-height: 140% }
        section { font-size: 10px; line-height: 1.4 }
        div, p { font-size: 20px; vertical-align: 50% }
      </style>
      <body><div><section><p></p></section></div></body>
    ''')
    html, = page.children
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
