"""
    weasyprint.tests.layout.list
    ----------------------------

    Tests for lists layout.

"""

import pytest

from ..testing_utils import assert_no_logs, render_pages


@assert_no_logs
@pytest.mark.parametrize('inside', ('inside', '',))
@pytest.mark.parametrize('style, character', (
    ('circle', '◦ '),
    ('disc', '• '),
    ('square', '▪ '),
))
def test_lists_style(inside, style, character):
    page, = render_pages('''
      <style>
        body { margin: 0 }
        ul { margin-left: 50px; list-style: %s %s }
      </style>
      <ul>
        <li>abc</li>
      </ul>
    ''' % (inside, style))
    html, = page.children
    body, = html.children
    unordered_list, = body.children
    list_item, = unordered_list.children
    if inside:
        line, = list_item.children
        marker, content = line.children
        marker_text, = marker.children
    else:
        marker, line_container, = list_item.children
        assert marker.position_x == list_item.position_x
        assert marker.position_y == list_item.position_y
        line, = line_container.children
        content, = line.children
        marker_line, = marker.children
        marker_text, = marker_line.children
    assert marker_text.text == character
    assert content.text == 'abc'


def test_lists_empty_item():
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/873
    page, = render_pages('''
      <ul>
        <li>a</li>
        <li></li>
        <li>a</li>
      </ul>
    ''')
    html, = page.children
    body, = html.children
    unordered_list, = body.children
    li1, li2, li3 = unordered_list.children
    assert li1.position_y != li2.position_y != li3.position_y


@pytest.mark.xfail
def test_lists_whitespace_item():
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/873
    page, = render_pages('''
      <ul>
        <li>a</li>
        <li> </li>
        <li>a</li>
      </ul>
    ''')
    html, = page.children
    body, = html.children
    unordered_list, = body.children
    li1, li2, li3 = unordered_list.children
    assert li1.position_y != li2.position_y != li3.position_y


def test_lists_page_break():
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/945
    page1, page2 = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 300px 100px }
        ul { font-size: 30px; font-family: weasyprint; margin: 0 }
      </style>
      <ul>
        <li>a</li>
        <li>a</li>
        <li>a</li>
        <li>a</li>
      </ul>
    ''')
    html, = page1.children
    body, = html.children
    ul, = body.children
    assert len(ul.children) == 3
    for li in ul.children:
        assert len(li.children) == 2

    html, = page2.children
    body, = html.children
    ul, = body.children
    assert len(ul.children) == 1
    for li in ul.children:
        assert len(li.children) == 2
