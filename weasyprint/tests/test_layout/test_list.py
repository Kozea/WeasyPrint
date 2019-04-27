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
    ('circle', '◦'),
    ('disc', '•'),
    ('square', '▪'),
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
    list_item, = unordered_list.children
    if inside:
        line, = list_item.children
        marker, content = line.children
    else:
        marker = list_item.outside_list_marker
        assert marker.position_x == (
            list_item.padding_box_x() - marker.width - marker.margin_right)
        assert marker.position_y == list_item.position_y
        line, = list_item.children
        content, = line.children
    assert marker.text == character
    assert content.text == 'abc'
