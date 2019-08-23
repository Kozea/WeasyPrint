"""
    weasyprint.tests.layout.list
    ----------------------------

    Tests for lists layout.

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import pytest

from ..test_boxes import render_pages as parse
from ..testing_utils import assert_no_logs


@assert_no_logs
@pytest.mark.parametrize('inside', ('inside', '',))
@pytest.mark.parametrize('style, character', (
    ('circle', '◦ '),
    ('disc', '• '),
    ('square', '▪ '),
))
def test_lists_style(inside, style, character):
    page, = parse('''
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
    if inside:
        list_item, = unordered_list.children
        line, = list_item.children
        marker, content = line.children
        marker_text, = marker.children
    else:
        marker, list_item = unordered_list.children
        assert marker.position_x == list_item.position_x
        assert marker.position_y == list_item.position_y
        line, = list_item.children
        content, = line.children
        marker_line, = marker.children
        marker_text, = marker_line.children
    assert marker_text.text == character
    assert content.text == 'abc'


def test_lists_empty_item():
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/873
    page, = parse('''
      <style>
        body { margin: 0 }
        ul { margin-left: 50px; list-style: %s %s }
      </style>
      <ul>
        <li>a</li>
        <li></li>
        <li>a</li>
      </ul>
    ''')
    html, = page.children
    body, = html.children
    unordered_list, = body.children
    _1, li1, _2, li2, _3, li3 = unordered_list.children
    assert li1.position_y != li2.position_y != li3.position_y
