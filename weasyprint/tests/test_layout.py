# coding: utf8
"""
    weasyprint.tests.layout
    -----------------------

    Tests for layout, ie. positioning and dimensioning of boxes,
    line breaks, page breaks.

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import math

import pytest

from .testing_utils import FONTS, assert_no_logs, capture_logs, almost_equal
from ..formatting_structure import boxes
from .test_boxes import render_pages as parse


def body_children(page):
    """Take a ``page``  and return its <body>’s children."""
    html, = page.children
    assert html.element_tag == 'html'
    body, = html.children
    assert body.element_tag == 'body'
    return body.children


def outer_area(box):
    """Return the (x, y, w, h) rectangle for the outer area of a box."""
    return (box.position_x, box.position_y,
            box.margin_width(), box.margin_height())


@assert_no_logs
def test_page_size():
    """Test the layout for ``@page`` properties."""
    pages = parse('<p>')
    page = pages[0]
    assert isinstance(page, boxes.PageBox)
    assert int(page.margin_width()) == 793  # A4: 210 mm in pixels
    assert int(page.margin_height()) == 1122  # A4: 297 mm in pixels

    page, = parse('<style>@page { size: 2in 10in; }</style>')
    assert page.margin_width() == 192
    assert page.margin_height() == 960

    page, = parse('<style>@page { size: 242px; }</style>')
    assert page.margin_width() == 242
    assert page.margin_height() == 242

    page, = parse('<style>@page { size: letter; }</style>')
    assert page.margin_width() == 816  # 8.5in
    assert page.margin_height() == 1056  # 11in

    page, = parse('<style>@page { size: letter portrait; }</style>')
    assert page.margin_width() == 816  # 8.5in
    assert page.margin_height() == 1056  # 11in

    page, = parse('<style>@page { size: letter landscape; }</style>')
    assert page.margin_width() == 1056  # 11in
    assert page.margin_height() == 816  # 8.5in

    page, = parse('<style>@page { size: portrait; }</style>')
    assert int(page.margin_width()) == 793  # A4: 210 mm
    assert int(page.margin_height()) == 1122  # A4: 297 mm

    page, = parse('<style>@page { size: landscape; }</style>')
    assert int(page.margin_width()) == 1122  # A4: 297 mm
    assert int(page.margin_height()) == 793  # A4: 210 mm

    page, = parse('''
        <style>@page { size: 200px 300px; margin: 10px 10% 20% 1in }
               body { margin: 8px }
        </style>
        <p style="margin: 0">
    ''')
    assert page.margin_width() == 200
    assert page.margin_height() == 300
    assert page.position_x == 0
    assert page.position_y == 0
    assert page.width == 84  # 200px - 10% - 1 inch
    assert page.height == 230  # 300px - 10px - 20%

    html, = page.children
    assert html.element_tag == 'html'
    assert html.position_x == 96  # 1in
    assert html.position_y == 10  # root element’s margins do not collapse
    assert html.width == 84

    body, = html.children
    assert body.element_tag == 'body'
    assert body.position_x == 96  # 1in
    assert body.position_y == 10
    # body has margins in the UA stylesheet
    assert body.margin_left == 8
    assert body.margin_right == 8
    assert body.margin_top == 8
    assert body.margin_bottom == 8
    assert body.width == 68

    paragraph, = body.children
    assert paragraph.element_tag == 'p'
    assert paragraph.position_x == 104  # 1in + 8px
    assert paragraph.position_y == 18  # 10px + 8px
    assert paragraph.width == 68

    page, = parse('''
        <style>
            @page { size: 100px; margin: 1px 2px; padding: 4px 8px;
                    border-width: 16px 32px; border-style: solid }
        </style>
        <body>
    ''')
    assert page.width == 16  # 100 - 2 * 42
    assert page.height == 58  # 100 - 2 * 21
    html, = page.children
    assert html.element_tag == 'html'
    assert html.position_x == 42  # 2 + 8 + 32
    assert html.position_y == 21  # 1 + 4 + 16

    page, = parse('''<style>@page {
        size: 106px 206px; width: 80px; height: 170px;
        padding: 1px; border: 2px solid; margin: auto;
    }</style>''')
    assert page.margin_top == 15  # (206 - 2*1 - 2*2 - 170) / 2
    assert page.margin_right == 10  # (106 - 2*1 - 2*2 - 80) / 2
    assert page.margin_bottom == 15  # (206 - 2*1 - 2*2 - 170) / 2
    assert page.margin_left == 10  # (106 - 2*1 - 2*2 - 80) / 2

    page, = parse('''<style>@page {
        size: 106px 206px; width: 80px; height: 170px;
        padding: 1px; border: 2px solid; margin: 5px 5px auto auto;
    }</style>''')
    assert page.margin_top == 5
    assert page.margin_right == 5
    assert page.margin_bottom == 25  # 206 - 2*1 - 2*2 - 170 - 5
    assert page.margin_left == 15  # 106 - 2*1 - 2*2 - 80 - 5

    # Over-constrained: the containing block is resized
    page, = parse('''<style>@page {
        size: 4px 10000px; width: 100px; height: 100px;
        padding: 1px; border: 2px solid; margin: 3px;
    }</style>''')
    assert page.margin_width() == 112  # 100 + 2*1 + 2*2 + 2*3
    assert page.margin_height() == 112

    page, = parse('''<style>@page {
        size: 1000px; margin: 100px;
        max-width: 500px; min-height: 1500px;
    }</style>''')
    assert page.margin_width() == 700
    assert page.margin_height() == 1700

    page, = parse('''<style>@page {
        size: 1000px; margin: 100px;
        min-width: 1500px; max-height: 500px;
    }</style>''')
    assert page.margin_width() == 1700
    assert page.margin_height() == 700


@assert_no_logs
def test_block_widths():
    """Test the blocks widths."""
    page, = parse('''
        <style>
            @page { margin: 0; size: 120px 2000px }
            body { margin: 0 }
            div { margin: 10px }
            p { padding: 2px; border-width: 1px; border-style: solid }
        </style>
        <div>
          <p></p>
          <p style="width: 50px"></p>
        </div>
        <div style="direction: rtl">
          <p style="width: 50px; direction: rtl"></p>
        </div>
        <div>
          <p style="margin: 0 10px 0 20px"></p>
          <p style="width: 50px; margin-left: 20px; margin-right: auto"></p>
          <p style="width: 50px; margin-left: auto; margin-right: 20px"></p>
          <p style="width: 50px; margin: auto"></p>

          <p style="margin-left: 20px; margin-right: auto"></p>
          <p style="margin-left: auto; margin-right: 20px"></p>
          <p style="margin: auto"></p>

          <p style="width: 200px; margin: auto"></p>

          <p style="min-width: 200px; margin: auto"></p>
          <p style="max-width: 50px; margin: auto"></p>
          <p style="min-width: 50px; margin: auto"></p>

          <p style="width: 70%"></p>
        </div>
    ''')
    html, = page.children
    assert html.element_tag == 'html'
    body, = html.children
    assert body.element_tag == 'body'
    assert body.width == 120

    divs = body.children

    paragraphs = []
    for div in divs:
        assert isinstance(div, boxes.BlockBox)
        assert div.element_tag == 'div'
        assert div.width == 100
        for paragraph in div.children:
            assert isinstance(paragraph, boxes.BlockBox)
            assert paragraph.element_tag == 'p'
            assert paragraph.padding_left == 2
            assert paragraph.padding_right == 2
            assert paragraph.border_left_width == 1
            assert paragraph.border_right_width == 1
            paragraphs.append(paragraph)

    assert len(paragraphs) == 15

    # width is 'auto'
    assert paragraphs[0].width == 94
    assert paragraphs[0].margin_left == 0
    assert paragraphs[0].margin_right == 0

    # No 'auto', over-constrained equation with ltr, the initial
    # 'margin-right: 0' was ignored.
    assert paragraphs[1].width == 50
    assert paragraphs[1].margin_left == 0

    # No 'auto', over-constrained equation with rtl, the initial
    # 'margin-left: 0' was ignored.
    assert paragraphs[2].width == 50
    assert paragraphs[2].margin_right == 0

    # width is 'auto'
    assert paragraphs[3].width == 64
    assert paragraphs[3].margin_left == 20

    # margin-right is 'auto'
    assert paragraphs[4].width == 50
    assert paragraphs[4].margin_left == 20

    # margin-left is 'auto'
    assert paragraphs[5].width == 50
    assert paragraphs[5].margin_left == 24

    # Both margins are 'auto', remaining space is split in half
    assert paragraphs[6].width == 50
    assert paragraphs[6].margin_left == 22

    # width is 'auto', other 'auto' are set to 0
    assert paragraphs[7].width == 74
    assert paragraphs[7].margin_left == 20

    # width is 'auto', other 'auto' are set to 0
    assert paragraphs[8].width == 74
    assert paragraphs[8].margin_left == 0

    # width is 'auto', other 'auto' are set to 0
    assert paragraphs[9].width == 94
    assert paragraphs[9].margin_left == 0

    # sum of non-auto initially is too wide, set auto values to 0
    assert paragraphs[10].width == 200
    assert paragraphs[10].margin_left == 0

    # Constrained by min-width, same as above
    assert paragraphs[11].width == 200
    assert paragraphs[11].margin_left == 0

    # Constrained by max-width, same as paragraphs[6]
    assert paragraphs[12].width == 50
    assert paragraphs[12].margin_left == 22

    # NOT constrained by min-width
    assert paragraphs[13].width == 94
    assert paragraphs[13].margin_left == 0

    # 70%
    assert paragraphs[14].width == 70
    assert paragraphs[14].margin_left == 0


@assert_no_logs
def test_block_heights():
    """Test the blocks heights."""
    page, = parse('''
        <style>
            @page { margin: 0; size: 100px 20000px }
            html, body { margin: 0 }
            div { margin: 4px; border-width: 2px; border-style: solid;
                  padding: 4px }
            /* Only use top margins so that margin collapsing does not change
               the result: */
            p { margin: 16px 0 0; border-width: 4px; border-style: solid;
                padding: 8px; height: 50px }
        </style>
        <div>
          <p></p>
          <!-- These two are not in normal flow: the do not contribute to
            the parent’s height. -->
          <p style="position: absolute"></p>
          <p style="float: left"></p>
        </div>
        <div>
          <p></p>
          <p></p>
          <p></p>
        </div>
        <div style="height: 20px">
          <p></p>
        </div>
        <div style="height: 120px">
          <p></p>
        </div>
        <div style="max-height: 20px">
          <p></p>
        </div>
        <div style="min-height: 120px">
          <p></p>
        </div>
        <div style="min-height: 20px">
          <p></p>
        </div>
        <div style="max-height: 120px">
          <p></p>
        </div>
    ''')
    heights = [div.height for div in body_children(page)]
    assert heights == [90, 90 * 3, 20, 120, 20, 120, 90, 90]

    page, = parse('''
        <style>
            body { height: 200px; font-size: 0; }
        </style>
        <div>
          <img src=pattern.png style="height: 40px">
        </div>
        <div style="height: 10%">
          <img src=pattern.png style="height: 40px">
        </div>
        <div style="max-height: 20px">
          <img src=pattern.png style="height: 40px">
        </div>
        <div style="max-height: 10%">
          <img src=pattern.png style="height: 40px">
        </div>
        <div style="min-height: 20px"></div>
        <div style="min-height: 10%"></div>
    ''')
    heights = [div.height for div in body_children(page)]
    assert heights == [40, 20, 20, 20, 20, 20]

    # Same but with no height on body: percentage *-height is ignored
    page, = parse('''
        <style>
            body { font-size: 0; }
        </style>
        <div>
          <img src=pattern.png style="height: 40px">
        </div>
        <div style="height: 10%">
          <img src=pattern.png style="height: 40px">
        </div>
        <div style="max-height: 20px">
          <img src=pattern.png style="height: 40px">
        </div>
        <div style="max-height: 10%">
          <img src=pattern.png style="height: 40px">
        </div>
        <div style="min-height: 20px"></div>
        <div style="min-height: 10%"></div>
    ''')
    heights = [div.height for div in body_children(page)]
    assert heights == [40, 40, 20, 40, 20, 0]


@assert_no_logs
def test_block_percentage_heights():
    """Test the blocks heights set in percents."""
    page, = parse('''
        <style>
            html, body { margin: 0 }
            body { height: 50% }
        </style>
        <body>
    ''')
    html, = page.children
    assert html.element_tag == 'html'
    body, = html.children
    assert body.element_tag == 'body'

    # Since html’s height depend on body’s, body’s 50% means 'auto'
    assert body.height == 0

    page, = parse('''
        <style>
            html, body { margin: 0 }
            html { height: 300px }
            body { height: 50% }
        </style>
        <body>
    ''')
    html, = page.children
    assert html.element_tag == 'html'
    body, = html.children
    assert body.element_tag == 'body'

    # This time the percentage makes sense
    assert body.height == 150


@assert_no_logs
def test_inline_block_sizes():
    """Test the inline-block elements sizes."""
    page, = parse('''
        <style>
            @page { margin: 0; size: 200px 2000px }
            body { margin: 0 }
            div { display: inline-block; }
        </style>
        <div> </div>
        <div>a</div>
        <div style="margin: 10px; height: 100px"></div>
        <div style="margin-left: 10px; margin-top: -50px;
                    padding-right: 20px;"></div>
        <div>
            Ipsum dolor sit amet,
            consectetur adipiscing elit.
            Sed sollicitudin nibh
            et turpis molestie tristique.
        </div>
        <div style="width: 100px; height: 100px;
                    padding-left: 10px; margin-right: 10px;
                    margin-top: -10px; margin-bottom: 50px"></div>
        <div style="font-size: 0">
          <div style="min-width: 10px; height: 10px"></div>
          <div style="width: 10%">
            <div style="width: 10px; height: 10px"></div>
          </div>
        </div>
        <div style="min-width: 185px">foo</div>
        <div style="max-width: 10px
          ">Supercalifragilisticexpialidocious</div>''')
    html, = page.children
    assert html.element_tag == 'html'
    body, = html.children
    assert body.element_tag == 'body'
    assert body.width == 200

    line_1, line_2, line_3, line_4 = body.children

    # First line:
    # White space in-between divs ends up preserved in TextBoxes
    div_1, _, div_2, _, div_3, _, div_4, _ = line_1.children

    # First div, one ignored space collapsing with next space
    assert div_1.element_tag == 'div'
    assert div_1.width == 0

    # Second div, one letter
    assert div_2.element_tag == 'div'
    assert 0 < div_2.width < 20

    # Third div, empty with margin
    assert div_3.element_tag == 'div'
    assert div_3.width == 0
    assert div_3.margin_width() == 20
    assert div_3.height == 100

    # Fourth div, empty with margin and padding
    assert div_4.element_tag == 'div'
    assert div_4.width == 0
    assert div_4.margin_width() == 30

    # Second line:
    div_5, = line_2.children

    # Fifth div, long text, full-width div
    assert div_5.element_tag == 'div'
    assert len(div_5.children) > 1
    assert div_5.width == 200

    # Third line:
    div_6, _, div_7, _ = line_3.children

    # Sixth div, empty div with fixed width and height
    assert div_6.element_tag == 'div'
    assert div_6.width == 100
    assert div_6.margin_width() == 120
    assert div_6.height == 100
    assert div_6.margin_height() == 140

    # Seventh div
    assert div_7.element_tag == 'div'
    assert div_7.width == 20
    child_line, = div_7.children
    # Spaces have font-size: 0, they get removed
    child_div_1, child_div_2 = child_line.children
    assert child_div_1.element_tag == 'div'
    assert child_div_1.width == 10
    assert child_div_2.element_tag == 'div'
    assert child_div_2.width == 2
    grandchild, = child_div_2.children
    assert grandchild.element_tag == 'div'
    assert grandchild.width == 10

    div_8, _, div_9 = line_4.children
    assert div_8.width == 185
    assert div_9.width == 10

    # Previously, the hinting for in shrink-to-fit did not match that
    # of the layout, which often resulted in a line break just before
    # the last word.
    page, = parse('''
        <p style="display: inline-block">Lorem ipsum dolor sit amet …</p>''')
    html, = page.children
    body, = html.children
    outer_line, = body.children
    paragraph, = outer_line.children
    inner_lines = paragraph.children
    assert len(inner_lines) == 1
    text_box, = inner_lines[0].children
    assert text_box.text == 'Lorem ipsum dolor sit amet …'


@assert_no_logs
def test_inline_table():
    """Test the inline-table elements sizes."""
    page, = parse('''
        <table style="display: inline-table; border-spacing: 10px;
                      margin: 5px">
            <tr>
                <td><img src=pattern.png style="width: 20px"></td>
                <td><img src=pattern.png style="width: 30px"></td>
            </tr>
        </table>
        foo
    ''')
    html, = page.children
    body, = html.children
    line, = body.children
    table_wrapper, text = line.children
    table, = table_wrapper.children
    row_group, = table.children
    row, = row_group.children
    td_1, td_2 = row.children
    assert table_wrapper.position_x == 0
    assert table.position_x == 5  # 0 + margin-left
    assert td_1.position_x == 15  # 0 + border-spacing
    assert td_1.width == 20
    assert td_2.position_x == 45  # 15 + 20 + border-spacing
    assert td_2.width == 30
    assert table.width == 80  # 20 + 30 + 3 * border-spacing
    assert table_wrapper.margin_width() == 90  # 80 + 2 * margin
    assert text.position_x == 90


@assert_no_logs
def test_implicit_width_table():
    """Test table with implicit width."""
    # See https://github.com/Kozea/WeasyPrint/issues/169
    page, = parse('''
        <table>
            <col style="width:25%"></col>
            <col></col>
            <tr>
                <td></td>
                <td></td>
            </tr>
        </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row, = row_group.children
    td_1, td_2 = row.children

    page, = parse('''
        <table>
            <tr>
                <td style="width:25%"></td>
                <td></td>
            </tr>
        </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row, = row_group.children
    td_1, td_2 = row.children


@assert_no_logs
def test_fixed_layout_table():
    """Test the fixed layout table elements sizes."""
    page, = parse('''
        <table style="table-layout: fixed; border-spacing: 10px;
                      margin: 5px">
            <colgroup>
              <col style="width: 20px" />
            </colgroup>
            <tr>
                <td></td>
                <td style="width: 40px">a</td>
            </tr>
        </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row, = row_group.children
    td_1, td_2 = row.children
    assert table_wrapper.position_x == 0
    assert table.position_x == 5  # 0 + margin-left
    assert td_1.position_x == 15  # 5 + border-spacing
    assert td_1.width == 20
    assert td_2.position_x == 45  # 15 + 20 + border-spacing
    assert td_2.width == 40
    assert table.width == 90  # 20 + 40 + 3 * border-spacing

    page, = parse('''
        <table style="table-layout: fixed; border-spacing: 10px;
                      width: 200px; margin: 5px">
            <tr>
                <td style="width: 20px">a</td>
                <td style="width: 40px"></td>
            </tr>
        </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row, = row_group.children
    td_1, td_2 = row.children
    assert table_wrapper.position_x == 0
    assert table.position_x == 5  # 0 + margin-left
    assert td_1.position_x == 15  # 5 + border-spacing
    assert td_1.width == 75  # 20 + ((200 - 20 - 40 - 3 * border-spacing) / 2)
    assert td_2.position_x == 100  # 15 + 75 + border-spacing
    assert td_2.width == 95  # 40 + ((200 - 20 - 40 - 3 * border-spacing) / 2)
    assert table.width == 200

    page, = parse('''
        <table style="table-layout: fixed; border-spacing: 10px;
                      width: 110px; margin: 5px">
            <tr>
                <td style="width: 40px">a</td>
                <td>b</td>
            </tr>
            <tr>
                <td style="width: 50px">a</td>
                <td style="width: 30px">b</td>
            </tr>
        </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row_1, row_2 = row_group.children
    td_1, td_2 = row_1.children
    td_3, td_4 = row_2.children
    assert table_wrapper.position_x == 0
    assert table.position_x == 5  # 0 + margin-left
    assert td_1.position_x == 15  # 0 + border-spacing
    assert td_3.position_x == 15
    assert td_1.width == 40
    assert td_2.width == 40
    assert td_2.position_x == 65  # 15 + 40 + border-spacing
    assert td_4.position_x == 65
    assert td_3.width == 40
    assert td_4.width == 40
    assert table.width == 110  # 20 + 40 + 3 * border-spacing

    page, = parse('''
        <table style="table-layout: fixed; border-spacing: 0;
                      width: 100px; margin: 10px">
            <colgroup>
              <col />
              <col style="width: 20px" />
            </colgroup>
            <tr>
                <td></td>
                <td style="width: 40px">a</td>
            </tr>
        </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row, = row_group.children
    td_1, td_2 = row.children
    assert table_wrapper.position_x == 0
    assert table.position_x == 10  # 0 + margin-left
    assert td_1.position_x == 10
    assert td_1.width == 80  # 100 - 20
    assert td_2.position_x == 90  # 10 + 80
    assert td_2.width == 20
    assert table.width == 100

    # With border-collapse
    page, = parse('''
        <style>
          /* Do not apply: */
          colgroup, col, tbody, tr, td { margin: 1000px }
        </style>
        <table style="table-layout: fixed;
                      border-collapse: collapse; border: 10px solid;
                      /* ignored with collapsed borders: */
                      border-spacing: 10000px; padding: 1000px">
            <colgroup>
              <col style="width: 30px" />
            </colgroup>
            <tbody>
              <tr>
                <td style="padding: 2px"></td>
                <td style="width: 34px; padding: 10px; border: 2px solid"></td>
              </tr>
            </tbody>
        </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row, = row_group.children
    td_1, td_2 = row.children
    assert table_wrapper.position_x == 0
    assert table.position_x == 0
    assert table.border_left_width == 5  # half of the collapsed 10px border
    assert td_1.position_x == 5  # border-spacing is ignored
    assert td_1.margin_width() == 30  # as <col>
    assert td_1.width == 20  # 30 - 5 (border-left) - 1 (border-right) - 2*2
    assert td_2.position_x == 35
    assert td_2.width == 34
    assert td_2.margin_width() == 60  # 34 + 2*10 + 5 + 1
    assert table.width == 90  # 30 + 60
    assert table.margin_width() == 100  # 90 + 2*5 (border)


@assert_no_logs
def test_auto_layout_table():
    """Test the auto layout table elements sizes."""
    page, = parse('''
        <body style="width: 100px">
        <table style="border-spacing: 10px; margin: auto">
            <tr>
                <td><img src=pattern.png></td>
                <td><img src=pattern.png></td>
            </tr>
        </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row, = row_group.children
    td_1, td_2 = row.children
    assert table_wrapper.position_x == 0
    assert table_wrapper.width == 38  # Same as table, see below
    assert table_wrapper.margin_left == 31  # 0 + margin-left = (100 - 38) / 2
    assert table_wrapper.margin_right == 31
    assert table.position_x == 31
    assert td_1.position_x == 41  # 31 + spacing
    assert td_1.width == 4
    assert td_2.position_x == 55  # 31 + 4 + spacing
    assert td_2.width == 4
    assert table.width == 38  # 3 * spacing + 2 * 4

    page, = parse('''
        <body style="width: 50px">
        <table style="border-spacing: 1px; margin: 10%">
            <tr>
                <td style="border: 3px solid black"><img src=pattern.png></td>
                <td style="border: 3px solid black">
                    <img src=pattern.png><img src=pattern.png>
                </td>
            </tr>
        </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row, = row_group.children
    td_1, td_2 = row.children
    assert table_wrapper.position_x == 0
    assert table.position_x == 5  # 0 + margin-left
    assert td_1.position_x == 6  # 5 + border-spacing
    assert td_1.width == 4
    assert td_2.position_x == 17  # 6 + 4 + spacing + 2 * border
    assert td_2.width == 8
    assert table.width == 27  # 3 * spacing + 4 + 8 + 4 * border

    page, = parse('''
        <table style="border-spacing: 1px; margin: 5px; font-size: 0">
            <tr>
                <td></td>
                <td><img src=pattern.png><img src=pattern.png></td>
            </tr>
            <tr>
                <td>
                    <img src=pattern.png>
                    <img src=pattern.png>
                    <img src=pattern.png>
                </td>
                <td><img src=pattern.png></td>
            </tr>
        </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row1, row2 = row_group.children
    td_11, td_12 = row1.children
    td_21, td_22 = row2.children
    assert table_wrapper.position_x == 0
    assert table.position_x == 5  # 0 + margin-left
    assert td_11.position_x == td_21.position_x == 6  # 5 + spacing
    assert td_11.width == td_21.width == 12
    assert td_12.position_x == td_22.position_x == 19  # 6 + 12 + spacing
    assert td_12.width == td_22.width == 8
    assert table.width == 23  # 3 * spacing + 12 + 8

    page, = parse('''
        <table style="border-spacing: 1px; margin: 5px">
            <tr>
                <td style="border: 1px solid black"><img src=pattern.png></td>
                <td style="border: 2px solid black; padding: 1px">
                    <img src=pattern.png>
                </td>
            </tr>
            <tr>
                <td style="border: 5px solid black"><img src=pattern.png></td>
                <td><img src=pattern.png></td>
            </tr>
        </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row1, row2 = row_group.children
    td_11, td_12 = row1.children
    td_21, td_22 = row2.children
    assert table_wrapper.position_x == 0
    assert table.position_x == 5  # 0 + margin-left
    assert td_11.position_x == td_21.position_x == 6  # 5 + spacing
    assert td_11.width == 12  # 4 + 2 * 5 - 2 * 1
    assert td_21.width == 4
    assert td_12.position_x == td_22.position_x == 21  # 6 + 4 + 2 * b1 + sp
    assert td_12.width == 4
    assert td_22.width == 10  # 4 + 2 * 3
    assert table.width == 27  # 3 * spacing + 4 + 4 + 2 * b1 + 2 * b2

    page, = parse('''
        <style>
            @page { size: 100px 1000px; }
        </style>
        <table style="border-spacing: 1px; margin-right: 79px; font-size: 0">
            <tr>
                <td><img src=pattern.png></td>
                <td>
                    <img src=pattern.png> <img src=pattern.png>
                    <img src=pattern.png> <img src=pattern.png>
                    <img src=pattern.png> <img src=pattern.png>
                    <img src=pattern.png> <img src=pattern.png>
                    <img src=pattern.png>
                </td>
            </tr>
            <tr>
                <td></td>
            </tr>
        </table>
    ''')
    # Preferred minimum width is 2 * 4 + 3 * 1 = 11
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row1, row2 = row_group.children
    td_11, td_12 = row1.children
    td_21, = row2.children
    assert table_wrapper.position_x == 0
    assert table.position_x == 0
    assert td_11.position_x == td_21.position_x == 1  # spacing
    assert td_11.width == td_21.width == 5  # 4 + (width - pmw) * 1 / 10
    assert td_12.position_x == 7  # 1 + 5 + sp
    assert td_12.width == 13  # 4 + (width - pmw) * 9 / 10
    assert table.width == 21

    page, = parse('''
        <table style="border-spacing: 10px; margin: 5px">
            <colgroup>
              <col style="width: 20px" />
            </colgroup>
            <tr>
                <td></td>
                <td style="width: 40px">a</td>
            </tr>
        </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row, = row_group.children
    td_1, td_2 = row.children
    assert table_wrapper.position_x == 0
    assert table.position_x == 5  # 0 + margin-left
    assert td_1.position_x == 15  # 0 + border-spacing
    assert td_1.width == 20
    assert td_2.position_x == 45  # 15 + 20 + border-spacing
    assert td_2.width == 40
    assert table.width == 90  # 20 + 40 + 3 * border-spacing

    page, = parse('''
        <table style="border-spacing: 10px; width: 120px; margin: 5px;
                      font-size: 0">
            <tr>
                <td style="width: 20px"><img src=pattern.png></td>
                <td><img src=pattern.png style="width: 40px"></td>
            </tr>
        </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row, = row_group.children
    td_1, td_2 = row.children
    assert table_wrapper.position_x == 0
    assert table.position_x == 5  # 0 + margin-left
    assert td_1.position_x == 15  # 5 + border-spacing
    assert td_1.width == 30  # 20 + ((120 - 20 - 40 - 3 * sp) * 1 / 3)
    assert td_2.position_x == 55  # 15 + 30 + border-spacing
    assert td_2.width == 60  # 40 + ((120 - 20 - 40 - 3 * sp) * 2 / 3)
    assert table.width == 120

    page, = parse('''
        <table style="border-spacing: 10px; width: 110px; margin: 5px">
            <tr>
                <td style="width: 60px"></td>
                <td></td>
            </tr>
            <tr>
                <td style="width: 50px"></td>
                <td style="width: 30px"></td>
            </tr>
        </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row_1, row_2 = row_group.children
    td_1, td_2 = row_1.children
    td_3, td_4 = row_2.children
    assert table_wrapper.position_x == 0
    assert table.position_x == 5  # 0 + margin-left
    assert td_1.position_x == 15  # 0 + border-spacing
    assert td_3.position_x == 15
    assert td_1.width == 60
    assert td_2.width == 30
    assert td_2.position_x == 85  # 15 + 60 + border-spacing
    assert td_4.position_x == 85
    assert td_3.width == 60
    assert td_4.width == 30
    assert table.width == 120  # 60 + 30 + 3 * border-spacing

    page, = parse('''
        <table style="border-spacing: 0; width: 14px; margin: 10px">
            <colgroup>
              <col />
              <col style="width: 6px" />
            </colgroup>
            <tr>
                <td><img src=pattern.png><img src=pattern.png></td>
                <td style="width: 8px"></td>
            </tr>
        </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row, = row_group.children
    td_1, td_2 = row.children
    assert table_wrapper.position_x == 0
    assert table.position_x == 10  # 0 + margin-left
    assert td_1.position_x == 10
    assert td_1.width == 5  # 4 + ((14 - 4 - 8) * 8 / 16)
    assert td_2.position_x == 15  # 10 + 5
    assert td_2.width == 9  # 8 + ((14 - 4 - 8) * 8 / 16)
    assert table.width == 14

    page, = parse('''
        <table style="border-spacing: 0">
            <tr>
                <td style="width: 10px"></td>
                <td colspan="3"></td>
            </tr>
            <tr>
                <td colspan="2" style="width: 22px"></td>
                <td style="width: 8px"></td>
                <td style="width: 8px"></td>
            </tr>
            <tr>
                <td></td>
                <td></td>
                <td colspan="2"></td>
            </tr>
        </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row1, row2, row3 = row_group.children
    td_11, td_12 = row1.children
    td_21, td_22, td_23 = row2.children
    td_31, td_32, td_33 = row3.children
    assert table_wrapper.position_x == 0
    assert table.position_x == 0
    assert td_11.width == 16  # 10 + (22 - 10) / 2
    assert td_12.width == 22  # (0 + (22 - 10) / 2) + 8 + 8
    assert td_21.width == 22
    assert td_22.width == 8
    assert td_23.width == 8
    assert td_31.width == 16
    assert td_32.width == 6
    assert td_33.width == 16
    assert table.width == 38

    page, = parse('''
        <table style="border-spacing: 10px">
            <tr>
                <td style="width: 10px"></td>
                <td colspan="3"></td>
            </tr>
            <tr>
                <td colspan="2" style="width: 32px"></td>
                <td style="width: 8px"></td>
                <td style="width: 8px"></td>
            </tr>
            <tr>
                <td></td>
                <td></td>
                <td colspan="2"></td>
            </tr>
        </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row1, row2, row3 = row_group.children
    td_11, td_12 = row1.children
    td_21, td_22, td_23 = row2.children
    td_31, td_32, td_33 = row3.children
    assert table_wrapper.position_x == 0
    assert table.position_x == 0
    assert td_11.width == 16  # 10 + (22 - 10) / 2
    assert td_12.width == 42  # (0 + (22 - 10) / 2) + 8 + 8
    assert td_21.width == 32
    assert td_22.width == 8
    assert td_23.width == 8
    assert td_31.width == 16
    assert td_32.width == 6
    assert td_33.width == 26
    assert table.width == 88

    # Regression tests: these used to crash
    page, = parse('''
        <table style="width: 30px">
            <tr>
                <td colspan=2></td>
                <td></td>
            </tr>
        </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row, = row_group.children
    td_1, td_2 = row.children
    assert td_1.width == 20
    assert td_2.width == 10
    assert table.width == 30

    page, = parse('''
        <table style="width: 20px">
            <col />
            <col />
            <tr>
                <td></td>
            </tr>
        </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row, = row_group.children
    td_1, = row.children
    assert td_1.width == 10  # TODO: should this be 20?
    assert table.width == 20

    page, = parse('''
        <table style="width: 20px">
            <col />
            <col />
        </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    column_group, = table.column_groups
    column_1, column_2 = column_group.children
    assert column_1.width == 10
    assert column_2.width == 10

    # Absolute table
    page, = parse('''
        <table style="width: 30px; position: absolute">
            <tr>
                <td colspan=2></td>
                <td></td>
            </tr>
        </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row, = row_group.children
    td_1, td_2 = row.children
    assert td_1.width == 20
    assert td_2.width == 10
    assert table.width == 30

    # With border-collapse
    page, = parse('''
        <style>
          /* Do not apply: */
          colgroup, col, tbody, tr, td { margin: 1000px }
        </style>
        <table style="border-collapse: collapse; border: 10px solid;
                      /* ignored with collapsed borders: */
                      border-spacing: 10000px; padding: 1000px">
            <colgroup>
              <col style="width: 30px" />
            </colgroup>
            <tbody>
              <tr>
                <td style="padding: 2px"></td>
                <td style="width: 34px; padding: 10px; border: 2px solid"></td>
              </tr>
            </tbody>
        </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row, = row_group.children
    td_1, td_2 = row.children
    assert table_wrapper.position_x == 0
    assert table.position_x == 0
    assert table.border_left_width == 5  # half of the collapsed 10px border
    assert td_1.position_x == 5  # border-spacing is ignored
    assert td_1.margin_width() == 30  # as <col>
    assert td_1.width == 20  # 30 - 5 (border-left) - 1 (border-right) - 2*2
    assert td_2.position_x == 35
    assert td_2.width == 34
    assert td_2.margin_width() == 60  # 34 + 2*10 + 5 + 1
    assert table.width == 90  # 30 + 60
    assert table.margin_width() == 100  # 90 + 2*5 (border)

    # Column widths as percentage
    page, = parse('''
        <table style="width: 200px">
            <colgroup>
              <col style="width: 70%" />
              <col style="width: 30%" />
            </colgroup>
            <tbody>
              <tr>
                <td>a</td>
                <td>abc</td>
              </tr>
            </tbody>
        </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row, = row_group.children
    td_1, td_2 = row.children
    assert td_1.width == 140
    assert td_2.width == 60
    assert table.width == 200

    # Column group width
    page, = parse('''
        <table style="width: 200px">
            <colgroup style="width: 100px">
              <col />
              <col />
            </colgroup>
            <col style="width: 100px" />
            <tbody>
              <tr>
                <td>a</td>
                <td>a</td>
                <td>abc</td>
              </tr>
            </tbody>
        </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row, = row_group.children
    td_1, td_2, td_3 = row.children
    assert td_1.width == 50
    assert td_2.width == 50
    assert td_3.width == 100
    assert table.width == 200

    # Column group width as percentage
    page, = parse('''
        <table style="width: 200px">
            <colgroup style="width: 100px">
              <col />
              <col />
            </colgroup>
            <colgroup style="width: 50%">
              <col />
              <col />
            </colgroup>
            <tbody>
              <tr>
                <td>a</td>
                <td>a</td>
                <td>abc</td>
                <td>abc</td>
              </tr>
            </tbody>
        </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row, = row_group.children
    td_1, td_2, td_3, td_4 = row.children
    assert td_1.width == 50
    assert td_2.width == 50
    assert td_3.width == 50
    assert td_4.width == 50
    assert table.width == 200

    # Wrong column group width
    page, = parse('''
        <table style="width: 200px">
            <colgroup style="width: 80%">
              <col />
              <col />
            </colgroup>
            <tbody>
              <tr>
                <td>a</td>
                <td>a</td>
              </tr>
            </tbody>
        </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row, = row_group.children
    td_1, td_2 = row.children
    assert td_1.width == 100
    assert td_2.width == 100
    assert table.width == 200

    # Column width as percentage and cell width in pixels
    page, = parse('''
        <table style="width: 200px">
            <colgroup>
              <col style="width: 70%" />
              <col />
            </colgroup>
            <tbody>
              <tr>
                <td>a</td>
                <td style="width: 60px">abc</td>
              </tr>
            </tbody>
        </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row, = row_group.children
    td_1, td_2 = row.children
    assert td_1.width == 140
    assert td_2.width == 60
    assert table.width == 200

    # Column width and cell width as percentage
    page, = parse('''
        <div style="width: 400px">
            <table style="width: 50%">
                <colgroup>
                    <col style="width: 70%" />
                    <col />
                </colgroup>
                <tbody>
                    <tr>
                        <td>a</td>
                        <td style="width: 30%">abc</td>
                    </tr>
                </tbody>
            </table>
        </div>
    ''')
    html, = page.children
    body, = html.children
    div, = body.children
    table_wrapper, = div.children
    table, = table_wrapper.children
    row_group, = table.children
    row, = row_group.children
    td_1, td_2 = row.children
    assert td_1.width == 140
    assert td_2.width == 60
    assert table.width == 200

    # Test regression on a crash: https://github.com/Kozea/WeasyPrint/pull/152
    page, = parse('''
        <table>
            <td style="width: 50%">
        </table>
    ''')


@assert_no_logs
def test_lists():
    """Test the lists."""
    page, = parse('''
        <style>
            body { margin: 0 }
            ul { margin-left: 50px; list-style: inside circle }
        </style>
        <ul>
          <li>abc</li>
        </ul>
    ''')
    unordered_list, = body_children(page)
    list_item, = unordered_list.children
    line, = list_item.children
    marker, content = line.children
    assert marker.text == '◦'
    assert marker.margin_left == 0
    assert marker.margin_right == 8
    assert content.text == 'abc'

    page, = parse('''
        <style>
            body { margin: 0 }
            ul { margin-left: 50px; }
        </style>
        <ul>
          <li>abc</li>
        </ul>
    ''')
    unordered_list, = body_children(page)
    list_item, = unordered_list.children
    marker = list_item.outside_list_marker
    font_size = marker.style.font_size
    assert marker.margin_right == 0.5 * font_size  # 0.5em
    assert marker.position_x == (
        list_item.padding_box_x() - marker.width - marker.margin_right)
    assert marker.position_y == list_item.position_y
    assert marker.text == '•'
    line, = list_item.children
    content, = line.children
    assert content.text == 'abc'


@assert_no_logs
def test_empty_linebox():
    """Test lineboxes with no content other than space-like characters."""
    page, = parse('<p> </p>')
    paragraph, = body_children(page)
    assert len(paragraph.children) == 0
    assert paragraph.height == 0

    # Whitespace removed at the beginning of the line => empty line => no line
    page, = parse('''
        <style>
            p { width: 1px }
        </style>
        <p><br>  </p>
    ''')
    paragraph, = body_children(page)
    # TODO: The second line should be removed
    pytest.xfail()
    assert len(paragraph.children) == 1


@assert_no_logs
def test_breaking_linebox():
    """Test lineboxes breaks with a lot of text and deep nesting."""
    page, = parse('''
        <style>
        p { font-size: 13px;
            width: 300px;
            font-family: %(fonts)s;
            background-color: #393939;
            color: #FFFFFF;
            line-height: 1;
            text-decoration: underline overline line-through;}
        </style>
        <p><em>Lorem<strong> Ipsum <span>is very</span>simply</strong><em>
        dummy</em>text of the printing and. naaaa </em> naaaa naaaa naaaa
        naaaa naaaa naaaa naaaa naaaa</p>
    ''' % {'fonts': FONTS})
    html, = page.children
    body, = html.children
    paragraph, = body.children
    assert len(list(paragraph.children)) == 3

    lines = paragraph.children
    for line in lines:
        assert line.style.font_size == 13
        assert line.element_tag == 'p'
        for child in line.children:
            assert child.element_tag in ('em', 'p')
            assert child.style.font_size == 13
            if isinstance(child, boxes.ParentBox):
                for child_child in child.children:
                    assert child.element_tag in ('em', 'strong', 'span')
                    assert child.style.font_size == 13

    # See http://unicode.org/reports/tr14/
    page, = parse('<pre>a\nb\rc\r\nd\u2029e</pre>')
    html, = page.children
    body, = html.children
    pre, = body.children
    lines = pre.children
    texts = []
    for line in lines:
        text_box, = line.children
        texts.append(text_box.text)
    assert texts == ['a', 'b', 'c', 'd', 'e']


@assert_no_logs
def test_linebox_text():
    """Test the creation of line boxes."""
    page, = parse('''
        <style>
            p { width: 165px; font-family:%(fonts)s;}
        </style>
        <p><em>Lorem Ipsum</em>is very <strong>coool</strong></p>
    ''' % {'fonts': FONTS})
    paragraph, = body_children(page)
    lines = list(paragraph.children)
    assert len(lines) == 2

    text = ' '.join(
        (''.join(box.text for box in line.descendants()
                 if isinstance(box, boxes.TextBox)))
        for line in lines)
    assert text == 'Lorem Ipsumis very coool'


@assert_no_logs
def test_linebox_positions():
    """Test the position of line boxes."""
    for width, expected_lines in [(165, 2), (1, 5), (0, 5)]:
        page = '''
            <style>
                p { width:%(width)spx; font-family:%(fonts)s;
                    line-height: 20px }
            </style>
            <p>this is test for <strong>Weasyprint</strong></p>'''
        page, = parse(page % {'fonts': FONTS, 'width': width})
        paragraph, = body_children(page)
        lines = list(paragraph.children)
        assert len(lines) == expected_lines

        ref_position_y = lines[0].position_y
        ref_position_x = lines[0].position_x
        for line in lines:
            assert ref_position_y == line.position_y
            assert ref_position_x == line.position_x
            for box in line.children:
                assert ref_position_x == box.position_x
                ref_position_x += box.width
                assert ref_position_y == box.position_y
            assert ref_position_x - line.position_x <= line.width
            ref_position_x = line.position_x
            ref_position_y += line.height


@assert_no_logs
def test_forced_line_breaks():
    """Test <pre> and <br>."""
    # These lines should be small enough to fit on the default A4 page
    # with the default 12pt font-size.
    page, = parse('''
        <style> pre { line-height: 42px }</style>
        <pre>Lorem ipsum dolor sit amet,
            consectetur adipiscing elit.


            Sed sollicitudin nibh

            et turpis molestie tristique.</pre>
    ''')
    pre, = body_children(page)
    assert pre.element_tag == 'pre'
    lines = pre.children
    assert all(isinstance(line, boxes.LineBox) for line in lines)
    assert len(lines) == 7
    assert [line.height for line in lines] == [42] * 7

    page, = parse('''
        <style> p { line-height: 42px }</style>
        <p>Lorem ipsum dolor sit amet,<br>
            consectetur adipiscing elit.<br><br><br>
            Sed sollicitudin nibh<br>
            <br>

            et turpis molestie tristique.</p>
    ''')
    pre, = body_children(page)
    assert pre.element_tag == 'p'
    lines = pre.children
    assert all(isinstance(line, boxes.LineBox) for line in lines)
    assert len(lines) == 7
    assert [line.height for line in lines] == [42] * 7


@assert_no_logs
def test_page_breaks():
    """Test the page breaks."""
    pages = parse('''
        <style>
            @page { size: 100px; margin: 10px }
            body { margin: 0 }
            div { height: 30px; font-size: 20px; }
        </style>
        <div>1</div>
        <div>2</div>
        <div>3</div>
        <div>4</div>
        <div>5</div>
    ''')
    page_divs = []
    for page in pages:
        divs = body_children(page)
        assert all([div.element_tag == 'div' for div in divs])
        assert all([div.position_x == 10 for div in divs])
        page_divs.append(divs)
        del divs

    positions_y = [[div.position_y for div in divs] for divs in page_divs]
    assert positions_y == [[10, 40], [10, 40], [10]]

    # Same as above, but no content inside each <div>.
    # This used to produce no page break.
    pages = parse('''
        <style>
            @page { size: 100px; margin: 10px }
            body { margin: 0 }
            div { height: 30px }
        </style>
        <div></div><div></div><div></div><div></div><div></div>
    ''')
    page_divs = []
    for page in pages:
        divs = body_children(page)
        assert all([div.element_tag == 'div' for div in divs])
        assert all([div.position_x == 10 for div in divs])
        page_divs.append(divs)
        del divs

    positions_y = [[div.position_y for div in divs] for divs in page_divs]
    assert positions_y == [[10, 40], [10, 40], [10]]

    pages = parse('''
        <style>
            @page { size: 100px; margin: 10px }
            img { height: 30px; display: block }
        </style>
        <body>
            <img src=pattern.png>
            <img src=pattern.png>
            <img src=pattern.png>
            <img src=pattern.png>
            <img src=pattern.png>
    ''')
    page_images = []
    for page in pages:
        images = body_children(page)
        assert all([img.element_tag == 'img' for img in images])
        assert all([img.position_x == 10 for img in images])
        page_images.append(images)
        del images
    positions_y = [[img.position_y for img in images]
                   for images in page_images]
    assert positions_y == [[10, 40], [10, 40], [10]]

    page_1, page_2, page_3, page_4 = parse('''
        <style>
            @page { margin: 10px }
            @page :left { margin-left: 50px }
            @page :right { margin-right: 50px }

            html { page-break-before: left }
            div { page-break-after: left }
            ul { page-break-before: always }
        </style>
        <div>1</div>
        <p>2</p>
        <p>3</p>
        <article>
            <section>
                <ul><li>4</li></ul>
            </section>
        </article>
    ''')

    # The first page is a right page on rtl, but not here because of
    # page-break-before on the root element.
    assert page_1.margin_left == 50  # left page
    assert page_1.margin_right == 10
    html, = page_1.children
    body, = html.children
    div, = body.children
    line, = div.children
    text, = line.children
    assert div.element_tag == 'div'
    assert text.text == '1'

    html, = page_2.children
    assert page_2.margin_left == 10
    assert page_2.margin_right == 50  # right page
    assert not html.children  # empty page to get to a left page

    assert page_3.margin_left == 50  # left page
    assert page_3.margin_right == 10
    html, = page_3.children
    body, = html.children
    p_1, p_2 = body.children
    assert p_1.element_tag == 'p'
    assert p_2.element_tag == 'p'

    assert page_4.margin_left == 10
    assert page_4.margin_right == 50  # right page
    html, = page_4.children
    body, = html.children
    article, = body.children
    section, = article.children
    ulist, = section.children
    assert ulist.element_tag == 'ul'

    # Reference for the following test:
    # Without any 'avoid', this breaks after the <div>
    page_1, page_2 = parse('''
        <style>
            @page { size: 140px; margin: 0 }
            img { height: 25px; vertical-align: top }
            p { orphans: 1; widows: 1 }
        </style>
        <body>
            <img src=pattern.png>
            <div>
                <p><img src=pattern.png><br/><img src=pattern.png><p>
                <p><img src=pattern.png><br/><img src=pattern.png><p>
            </div><!-- page break here -->
            <img src=pattern.png>
    ''')
    html, = page_1.children
    body, = html.children
    img_1, div = body.children
    assert img_1.position_y == 0
    assert img_1.height == 25
    assert div.position_y == 25
    assert div.height == 100

    html, = page_2.children
    body, = html.children
    img_2, = body.children
    assert img_2.position_y == 0
    assert img_2.height == 25

    # Adding a few page-break-*: avoid, the only legal break is
    # before the <div>
    page_1, page_2 = parse('''
        <style>
            @page { size: 140px; margin: 0 }
            img { height: 25px; vertical-align: top }
            p { orphans: 1; widows: 1 }
        </style>
        <body>
            <img src=pattern.png><!-- page break here -->
            <div>
                <p style="page-break-inside: avoid">
                    ><img src=pattern.png><br/><img src=pattern.png></p>
                <p style="page-break-before: avoid; page-break-after: avoid;
                          widows: 2"
                    ><img src=pattern.png><br/><img src=pattern.png></p>
            </div>
            <img src=pattern.png>
    ''')
    html, = page_1.children
    body, = html.children
    img_1, = body.children
    assert img_1.position_y == 0
    assert img_1.height == 25

    html, = page_2.children
    body, = html.children
    div, img_2 = body.children
    assert div.position_y == 0
    assert div.height == 100
    assert img_2.position_y == 100
    assert img_2.height == 25

    page_1, page_2 = parse('''
        <style>
            @page { size: 140px; margin: 0 }
            img { height: 25px; vertical-align: top }
            p { orphans: 1; widows: 1 }
        </style>
        <body>
            <img src=pattern.png><!-- page break here -->
            <div>
                <div>
                    <p style="page-break-inside: avoid">
                        ><img src=pattern.png><br/><img src=pattern.png></p>
                    <p style="page-break-before: avoid;
                              page-break-after: avoid;
                              widows: 2"
                        ><img src=pattern.png><br/><img src=pattern.png></p>
                </div>
                <img src=pattern.png>
            </div>
    ''')
    html, = page_1.children
    body, = html.children
    img_1, = body.children
    assert img_1.position_y == 0
    assert img_1.height == 25

    html, = page_2.children
    body, = html.children
    outer_div, = body.children
    inner_div, img_2 = outer_div.children
    assert inner_div.position_y == 0
    assert inner_div.height == 100
    assert img_2.position_y == 100
    assert img_2.height == 25

    # Reference for the next test
    page_1, page_2, page_3 = parse('''
        <style>
            @page { size: 100px; margin: 0 }
            img { height: 30px; display: block; }
            p { orphans: 1; widows: 1 }
        </style>
        <body>
            <div>
                <img src=pattern.png style="page-break-after: always">
                <section>
                    <img src=pattern.png>
                    <img src=pattern.png>
                </section>
            </div>
            <img src=pattern.png><!-- page break here -->
            <img src=pattern.png>
    ''')
    html, = page_1.children
    body, = html.children
    div, = body.children
    assert div.height == 30
    html, = page_2.children
    body, = html.children
    div, img_4 = body.children
    assert div.height == 60
    assert img_4.height == 30
    html, = page_3.children
    body, = html.children
    img_5, = body.children
    assert img_5.height == 30

    page_1, page_2, page_3 = parse('''
        <style>
            @page { size: 100px; margin: 0 }
            img { height: 30px; display: block; }
            p { orphans: 1; widows: 1 }
        </style>
        <body>
            <div>
                <img src=pattern.png style="page-break-after: always">
                <section>
                    <img src=pattern.png><!-- page break here -->
                    <img src=pattern.png style="page-break-after: avoid">
                </section>
            </div>
            <img src=pattern.png style="page-break-after: avoid">
            <img src=pattern.png>
    ''')
    html, = page_1.children
    body, = html.children
    div, = body.children
    assert div.height == 30
    html, = page_2.children
    body, = html.children
    div, = body.children
    section, = div.children
    img_2, = section.children
    assert img_2.height == 30
    # TODO: currently this is 60: we do not decrease the used height of
    # blocks with 'height: auto' when we remove children from them for
    # some page-break-*: avoid.
    # assert div.height == 30
    html, = page_3.children
    body, = html.children
    div, img_4, img_5, = body.children
    assert div.height == 30
    assert img_4.height == 30
    assert img_5.height == 30

    page_1, page_2, page_3 = parse('''
        <style>
            @page {
                @bottom-center { content: counter(page) }
            }
            @page:blank {
                @bottom-center { content: none }
            }
        </style>
        <p style="page-break-after: right">foo</p>
        <p>bar</p>
    ''')
    assert len(page_1.children) == 2  # content and @bottom-center
    assert len(page_2.children) == 1  # content only
    assert len(page_3.children) == 2  # content and @bottom-center

    page_1, page_2 = parse('''
        <style>
          @page { size: 75px; margin: 0 }
          div { height: 20px }
        </style>
        <body>
          <div></div>
          <section>
            <div></div>
            <div style="page-break-after: avoid">
              <div style="position: absolute"></div>
              <div style="position: fixed"></div>
            </div>
          </section>
          <div></div>
    ''')
    html, = page_1.children
    body, _div = html.children
    div_1, section = body.children
    div_2, = section.children
    assert div_1.position_y == 0
    assert div_2.position_y == 20
    assert div_1.height == 20
    assert div_2.height == 20
    html, = page_2.children
    body, = html.children
    section, div_4 = body.children
    div_3, = section.children
    absolute, fixed = div_3.children
    assert div_3.position_y == 0
    assert div_4.position_y == 20
    assert div_3.height == 20
    assert div_4.height == 20


@assert_no_logs
def test_orphans_widows_avoid():
    """Test orphans and widows control."""
    def line_distribution(css):
        pages = parse('''
            <style>
                @page { size: 200px }
                h1 { height: 120px }
                p { line-height: 20px;
                    width: 1px; /* line break at each word */
                    %s }
            </style>
            <h1>Tasty test</h1>
            <!-- There is room for 4 lines after h1 on the fist page -->
            <p>
                one
                two
                three
                four
                five
                six
                seven
            </p>
        ''' % css)
        line_counts = []
        for i, page in enumerate(pages):
            html, = page.children
            body, = html.children
            if i == 0:
                body_children = body.children[1:]  # skip h1
            else:
                body_children = body.children
            if body_children:
                paragraph, = body_children
                line_counts.append(len(paragraph.children))
            else:
                line_counts.append(0)
        return line_counts

    assert line_distribution('orphans: 2; widows: 2') == [4, 3]
    assert line_distribution('orphans: 5; widows: 2') == [0, 7]
    assert line_distribution('orphans: 2; widows: 4') == [3, 4]
    assert line_distribution('orphans: 4; widows: 4') == [0, 7]

    assert line_distribution(
        'orphans: 2; widows: 2; page-break-inside: avoid') == [0, 7]


@assert_no_logs
def test_table_page_breaks():
    """Test the page breaks inside tables."""
    def run(html):
        pages = parse(html)
        rows_per_page = []
        rows_position_y = []
        for i, page in enumerate(pages):
            html, = page.children
            body, = html.children
            if i == 0:
                body_children = body.children[1:]  # skip h1
            else:
                body_children = body.children
            if not body_children:
                rows_per_page.append(0)
                continue
            table_wrapper, = body_children
            table, = table_wrapper.children
            rows_in_this_page = 0
            for group in table.children:
                assert group.children, 'found an empty table group'
                for row in group.children:
                    rows_in_this_page += 1
                    rows_position_y.append(row.position_y)
                    cell, = row.children
                    line, = cell.children
                    text, = line.children
                    assert text.text == 'row %i' % len(rows_position_y)
            rows_per_page.append(rows_in_this_page)
        return rows_per_page, rows_position_y

    rows_per_page, rows_position_y = run('''
        <style>
            @page { size: 120px }
            table { table-layout: fixed; width: 100% }
            h1 { height: 30px }
            td { height: 40px }
        </style>
        <h1>Dummy title</h1>
        <table>
            <tr><td>row 1</td></tr>
            <tr><td>row 2</td></tr>

            <tr><td>row 3</td></tr>
            <tr><td>row 4</td></tr>
            <tr><td>row 5</td></tr>

            <tr><td style="height: 300px"> <!-- overflow the page -->
                row 6</td></tr>
            <tr><td>row 7</td></tr>
            <tr><td>row 8</td></tr>
        </table>
    ''')
    assert rows_per_page == [2, 3, 1, 2]
    assert rows_position_y == [30, 70, 0, 40, 80, 0, 0, 40]

    rows_per_page, rows_position_y = run('''
        <style>
            @page { size: 120px }
            h1 { height: 30px}
            td { height: 40px }
            table { table-layout: fixed; width: 100%;
                    page-break-inside: avoid }
        </style>
        <h1>Dummy title</h1>
        <table>
            <tr><td>row 1</td></tr>
            <tr><td>row 2</td></tr>
            <tr><td>row 3</td></tr>

            <tr><td>row 4</td></tr>
        </table>
    ''')
    assert rows_per_page == [0, 3, 1]
    assert rows_position_y == [0, 40, 80, 0]

    rows_per_page, rows_position_y = run('''
        <style>
            @page { size: 120px }
            h1 { height: 30px}
            td { height: 40px }
            table { table-layout: fixed; width: 100%;
                    page-break-inside: avoid }
        </style>
        <h1>Dummy title</h1>
        <table>
            <tbody>
                <tr><td>row 1</td></tr>
                <tr><td>row 2</td></tr>
                <tr><td>row 3</td></tr>
            </tbody>

            <tr><td>row 4</td></tr>
        </table>
    ''')
    assert rows_per_page == [0, 3, 1]
    assert rows_position_y == [0, 40, 80, 0]

    rows_per_page, rows_position_y = run('''
        <style>
            @page { size: 120px }
            h1 { height: 30px}
            td { height: 40px }
            table { table-layout: fixed; width: 100% }
        </style>
        <h1>Dummy title</h1>
        <table>
            <tr><td>row 1</td></tr>

            <tbody style="page-break-inside: avoid">
                <tr><td>row 2</td></tr>
                <tr><td>row 3</td></tr>
            </tbody>
        </table>
    ''')
    assert rows_per_page == [1, 2]
    assert rows_position_y == [30, 0, 40]

    pages = parse('''
        <style>
            @page { size: 100px }
        </style>
        <h1 style="margin: 0; height: 30px">Lipsum</h1>
        <!-- Leave 70px on the first page: enough for the header or row1
             but not both.  -->
        <table style="border-spacing: 0; font-size: 5px">
            <thead>
                <tr><td style="height: 20px">Header</td></tr>
            </thead>
            <tbody>
                <tr><td style="height: 60px">Row 1</td></tr>
                <tr><td style="height: 10px">Row 2</td></tr>
                <tr><td style="height: 50px">Row 3</td></tr>
                <tr><td style="height: 61px">Row 4</td></tr>
                <tr><td style="height: 90px">Row 5</td></tr>
            </tbody>
            <tfoot>
                <tr><td style="height: 20px">Footer</td></tr>
            </tfoot>
        </table>
    ''')
    rows_per_page = []
    for i, page in enumerate(pages):
        groups = []
        html, = page.children
        body, = html.children
        table_wrapper, = body.children
        if i == 0:
            assert table_wrapper.element_tag == 'h1'
        else:
            table, = table_wrapper.children
            for group in table.children:
                assert group.children, 'found an empty table group'
                rows = []
                for row in group.children:
                    cell, = row.children
                    line, = cell.children
                    text, = line.children
                    rows.append(text.text)
                groups.append(rows)
        rows_per_page.append(groups)
    assert rows_per_page == [
        [],
        [['Header'], ['Row 1'], ['Footer']],
        [['Header'], ['Row 2', 'Row 3'], ['Footer']],
        [['Header'], ['Row 4']],
        [['Row 5']]
    ]


@assert_no_logs
def test_inlinebox_spliting():
    """Test the inline boxes spliting."""
    for width in [10000, 100, 10, 0]:
        page, = parse('''
            <style>p { font-family:%(fonts)s; width: %(width)spx; }</style>
            <p><strong>WeasyPrint is a free software visual rendering engine
                       for HTML and CSS.</strong></p>
        ''' % {'fonts': FONTS, 'width': width})
        html, = page.children
        body, = html.children
        paragraph, = body.children
        lines = paragraph.children
        if width == 10000:
            assert len(lines) == 1
        else:
            assert len(lines) > 1
        text_parts = []
        for line in lines:
            strong, = line.children
            text, = strong.children
            text_parts.append(text.text)
        assert ' '.join(text_parts) == ('WeasyPrint is a free software visual '
                                        'rendering engine for HTML and CSS.')


@assert_no_logs
def test_page_and_linebox_breaking():
    """Test the linebox text after spliting linebox and page."""
    # The empty <span/> tests a corner case
    # in skip_first_whitespace()
    pages = parse('''
        <style>
            div { font-family:%(fonts)s; font-size:22px}
            @page { size: 100px; margin:2px; border:1px solid }
            body { margin: 0 }
        </style>
        <div><span/>1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15</div>
    ''' % {'fonts': FONTS})

    texts = []
    for page in pages:
        html, = page.children
        body, = html.children
        div, = body.children
        lines = div.children
        for line in lines:
            line_texts = []
            for child in line.descendants():
                if isinstance(child, boxes.TextBox):
                    line_texts.append(child.text)
            texts.append(''.join(line_texts))

    assert len(pages) == 2
    assert ' '.join(texts) == \
        '1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15'


@assert_no_logs
def test_whitespace_processing():
    """Test various spaces and tabulations processing."""
    for source in ['a', '  a  ', ' \n  \ta', ' a\t ']:
        page, = parse('<p><em>%s</em></p>' % source)
        html, = page.children
        body, = html.children
        p, = body.children
        line, = p.children
        em, = line.children
        text, = em.children
        assert text.text == 'a', 'source was %r' % (source,)

        page, = parse('<p style="white-space: pre-line">\n\n<em>%s</em></pre>'
                      % source.replace('\n', ' '))
        html, = page.children
        body, = html.children
        p, = body.children
        _line1, _line2, line3 = p.children
        em, = line3.children
        text, = em.children
        assert text.text == 'a', 'source was %r' % (source,)


@assert_no_logs
def test_images():
    """Test that width, height and ratio of images are respected."""
    def get_img(html):
        page, = parse(html)
        html, = page.children
        body, = html.children
        line, = body.children
        img, = line.children
        return body, img

    # Try a few image formats
    for html in [
        '<img src="%s">' % url for url in [
            'pattern.png', 'pattern.gif', 'blue.jpg', 'pattern.svg',
            "data:image/svg+xml,<svg width='4' height='4'></svg>",
            "DatA:image/svg+xml,<svg width='4px' height='4px'></svg>",
        ]
    ] + [
        '<embed src=pattern.png>',
        '<embed src=pattern.svg>',
        '<embed src=really-a-png.svg type=image/png>',
        '<embed src=really-a-svg.png type=image/svg+xml>',

        '<object data=pattern.png>',
        '<object data=pattern.svg>',
        '<object data=really-a-png.svg type=image/png>',
        '<object data=really-a-svg.png type=image/svg+xml>',
    ]:
        body, img = get_img(html)
        assert img.width == 4
        assert img.height == 4

    # With physical units
    url = "data:image/svg+xml,<svg width='2.54cm' height='0.5in'></svg>"
    body, img = get_img('<img src="%s">' % url)
    assert img.width == 96
    assert img.height == 48

    # Invalid images
    for url in [
        'nonexistent.png',
        'unknownprotocol://weasyprint.org/foo.png',
        'data:image/unknowntype,Not an image',
        # Invalid protocol
        'datå:image/svg+xml,<svg width="4" height="4"></svg>',
        # zero-byte images
        'data:image/png,',
        'data:image/jpeg,',
        'data:image/svg+xml,',
        # Incorrect format
        'data:image/png,Not a PNG',
        'data:image/jpeg,Not a JPEG',
        'data:image/svg+xml,<svg>invalid xml',
        'really-a-svg.png',
    ]:
        with capture_logs() as logs:
            body, img = get_img("<img src='%s' alt='invalid image'>" % url)
        assert len(logs) == 1
        assert 'WARNING: Failed to load image' in logs[0]
        assert isinstance(img, boxes.InlineBox)  # not a replaced box
        text, = img.children
        assert text.text == 'invalid image', url

    with capture_logs() as logs:
        parse('<img src=nonexistent.png><img src=nonexistent.png>')
    # Failures are cached too: only one warning
    assert len(logs) == 1
    assert 'WARNING: Failed to load image' in logs[0]

    # Layout rules try to preserve the ratio, so the height should be 40px too:
    body, img = get_img('''<body style="font-size: 0">
        <img src="pattern.png" style="width: 40px">''')
    assert body.height == 40
    assert img.position_y == 0
    assert img.width == 40
    assert img.height == 40

    body, img = get_img('''<body style="font-size: 0">
        <img src="pattern.png" style="height: 40px">''')
    assert body.height == 40
    assert img.position_y == 0
    assert img.width == 40
    assert img.height == 40

    # Same with percentages
    body, img = get_img('''<body style="font-size: 0"><p style="width: 200px">
        <img src="pattern.png" style="width: 20%">''')
    assert body.height == 40
    assert img.position_y == 0
    assert img.width == 40
    assert img.height == 40

    body, img = get_img('''<body style="font-size: 0">
        <img src="pattern.png" style="min-width: 40px">''')
    assert body.height == 40
    assert img.position_y == 0
    assert img.width == 40
    assert img.height == 40

    body, img = get_img('<img src="pattern.png" style="max-width: 2px">')
    assert img.width == 2
    assert img.height == 2

    # display: table-cell is ignored. XXX Should it?
    page, = parse('''<body style="font-size: 0">
        <img src="pattern.png" style="width: 40px">
        <img src="pattern.png" style="width: 60px; display: table-cell">
    ''')
    html, = page.children
    body, = html.children
    line, = body.children
    img_1, img_2 = line.children
    assert body.height == 60
    assert img_1.width == 40
    assert img_1.height == 40
    assert img_2.width == 60
    assert img_2.height == 60
    assert img_1.position_y == 20
    assert img_2.position_y == 0

    # Block-level image:
    page, = parse('''
        <style>
            @page { size: 100px }
            img { width: 40px; margin: 10px auto; display: block }
        </style>
        <body>
            <img src="pattern.png">
    ''')
    html, = page.children
    body, = html.children
    img, = body.children
    assert img.element_tag == 'img'
    assert img.position_x == 0
    assert img.position_y == 0
    assert img.width == 40
    assert img.height == 40
    assert img.content_box_x() == 30  # (100 - 40) / 2 == 30px for margin-left
    assert img.content_box_y() == 10

    page, = parse('''
        <style>
            @page { size: 100px }
            img { min-width: 40%; margin: 10px auto; display: block }
        </style>
        <body>
            <img src="pattern.png">
    ''')
    html, = page.children
    body, = html.children
    img, = body.children
    assert img.element_tag == 'img'
    assert img.position_x == 0
    assert img.position_y == 0
    assert img.width == 40
    assert img.height == 40
    assert img.content_box_x() == 30  # (100 - 40) / 2 == 30px for margin-left
    assert img.content_box_y() == 10

    page, = parse('''
        <style>
            @page { size: 100px }
            img { min-width: 40px; margin: 10px auto; display: block }
        </style>
        <body>
            <img src="pattern.png">
    ''')
    html, = page.children
    body, = html.children
    img, = body.children
    assert img.element_tag == 'img'
    assert img.position_x == 0
    assert img.position_y == 0
    assert img.width == 40
    assert img.height == 40
    assert img.content_box_x() == 30  # (100 - 40) / 2 == 30px for margin-left
    assert img.content_box_y() == 10

    page, = parse('''
        <style>
            @page { size: 100px }
            img { min-height: 30px; max-width: 2px;
                  margin: 10px auto; display: block }
        </style>
        <body>
            <img src="pattern.png">
    ''')
    html, = page.children
    body, = html.children
    img, = body.children
    assert img.element_tag == 'img'
    assert img.position_x == 0
    assert img.position_y == 0
    assert img.width == 2
    assert img.height == 30
    assert img.content_box_x() == 49  # (100 - 2) / 2 == 49px for margin-left
    assert img.content_box_y() == 10


@assert_no_logs
def test_vertical_align():
    """Test various values of vertical-align."""
    """
               +-------+      <- position_y = 0
         +-----+       |
    40px |     |       | 60px
         |     |       |
         +-----+-------+      <- baseline
    """
    page, = parse('''
        <span>
            <img src="pattern.png" style="width: 40px"
            ><img src="pattern.png" style="width: 60px"
        ></span>''')
    html, = page.children
    body, = html.children
    line, = body.children
    span, = line.children
    img_1, img_2 = span.children
    assert img_1.height == 40
    assert img_2.height == 60
    assert img_1.position_y == 20
    assert img_2.position_y == 0
    # 60px + the descent of the font below the baseline
    assert 60 < line.height < 70
    assert body.height == line.height

    """
               +-------+      <- position_y = 0
          35px |       |
         +-----+       | 60px
    40px |     |       |
         |     +-------+      <- baseline
         +-----+  15px

    """
    page, = parse('''
        <span>
            <img src="pattern.png" style="width: 40px; vertical-align: -15px"
            ><img src="pattern.png" style="width: 60px"></span>''')
    html, = page.children
    body, = html.children
    line, = body.children
    span, = line.children
    img_1, img_2 = span.children
    assert img_1.height == 40
    assert img_2.height == 60
    assert img_1.position_y == 35
    assert img_2.position_y == 0
    assert line.height == 75
    assert body.height == line.height

    # Same as previously, but with percentages
    page, = parse('''
        <span style="line-height: 10px">
            <img src="pattern.png" style="width: 40px; vertical-align: -150%"
            ><img src="pattern.png" style="width: 60px"></span>''')
    html, = page.children
    body, = html.children
    line, = body.children
    span, = line.children
    img_1, img_2 = span.children
    assert img_1.height == 40
    assert img_2.height == 60
    assert img_1.position_y == 35
    assert img_2.position_y == 0
    assert line.height == 75
    assert body.height == line.height

    # Same again, but have the vertical-align on an inline box.
    page, = parse('''
        <span style="line-height: 10px">
            <span style="line-height: 10px; vertical-align: -15px">
                <img src="pattern.png" style="width: 40px"></span>
            <img src="pattern.png" style="width: 60px"></span>''')
    html, = page.children
    body, = html.children
    line, = body.children
    span_1, = line.children
    span_2, _whitespace, img_1 = span_1.children
    img_1, = span_2.children
    assert img_1.height == 40
    assert img_2.height == 60
    assert img_1.position_y == 35
    assert img_2.position_y == 0
    assert line.height == 75
    assert body.height == line.height

    # Same as previously, but with percentages
    page, = parse('''
        <span style="line-height: 12px; font-size: 12px; font-family: 'ahem'">
            <img src="pattern.png" style="width: 40px; vertical-align: middle"
            ><img src="pattern.png" style="width: 60px"></span>''')
    html, = page.children
    body, = html.children
    line, = body.children
    span, = line.children
    img_1, img_2 = span.children
    assert img_1.height == 40
    assert img_2.height == 60
    # middle of the image (position_y + 20) is at half the ex-height above
    # the baseline of the parent. The ex-height of Ahem is something like 0.8em
    assert img_1.position_y == 35.2  # 60 - 0.5 * 0.8 * font-size - 40/2
    assert img_2.position_y == 0
    assert line.height == 75.2
    assert body.height == line.height

    # sup and sub currently mean +/- 0.5 em
    # With the initial 16px font-size, that’s 8px.
    page, = parse('''
        <span style="line-height: 10px">
            <img src="pattern.png" style="width: 60px"
            ><img src="pattern.png" style="width: 40px; vertical-align: super"
            ><img src="pattern.png" style="width: 40px; vertical-align: sub"
        ></span>''')
    html, = page.children
    body, = html.children
    line, = body.children
    span, = line.children
    img_1, img_2, img_3 = span.children
    assert img_1.height == 60
    assert img_2.height == 40
    assert img_3.height == 40
    assert img_1.position_y == 0
    assert img_2.position_y == 12  # 20 - 16 * 0.5
    assert img_3.position_y == 28  # 20 + 16 * 0.5
    assert line.height == 68
    assert body.height == line.height

    page, = parse('''
        <body style="line-height: 10px">
            <span>
                <img src="pattern.png" style="vertical-align: text-top"
                ><img src="pattern.png" style="vertical-align: text-bottom"
            ></span>''')
    html, = page.children
    body, = html.children
    line, = body.children
    span, = line.children
    img_1, img_2 = span.children
    assert img_1.height == 4
    assert img_2.height == 4
    assert img_1.position_y == 0
    assert img_2.position_y == 12  # 16 - 4
    assert line.height == 16
    assert body.height == line.height

    # This case used to cause an exception:
    # The second span has no children but should count for line heights
    # since it has padding.
    page, = parse('''<span style="line-height: 1.5">
         <span style="padding: 1px"></span></span>''')
    html, = page.children
    body, = html.children
    line, = body.children
    span_1, = line.children
    span_2, = span_1.children
    assert span_1.height == 16
    assert span_2.height == 16
    # The line’s strut does not has 'line-height: normal' but the result should
    # be smaller than 1.5.
    assert span_1.margin_height() == 24
    assert span_2.margin_height() == 24
    assert line.height == 24

    page, = parse('''
        <span>
            <img src="pattern.png" style="width: 40px; vertical-align: -15px"
            ><img src="pattern.png" style="width: 60px"
        ></span><div style="display: inline-block; vertical-align: 3px">
            <div>
                <div style="height: 100px">foo</div>
                <div>
                    <img src="pattern.png" style="
                        width: 40px; vertical-align: -15px"
                    ><img src="pattern.png" style="width: 60px"
                ></div>
            </div>
        </div>''')
    html, = page.children
    body, = html.children
    line, = body.children
    span, div_1 = line.children
    assert line.height == 178
    assert body.height == line.height

    # Same as earlier
    img_1, img_2 = span.children
    assert img_1.height == 40
    assert img_2.height == 60
    assert img_1.position_y == 138
    assert img_2.position_y == 103

    div_2, = div_1.children
    div_3, div_4 = div_2.children
    div_line, = div_4.children
    div_img_1, div_img_2 = div_line.children
    assert div_1.position_y == 0
    assert div_1.height == 175
    assert div_3.height == 100
    assert div_line.height == 75
    assert div_img_1.height == 40
    assert div_img_2.height == 60
    assert div_img_1.position_y == 135
    assert div_img_2.position_y == 100

    # The first two images bring the top of the line box 30px above
    # the baseline and 10px below.
    # Each of the inner span
    page, = parse('''
        <span style="font-size: 0">
            <img src="pattern.png" style="vertical-align: 26px">
            <img src="pattern.png" style="vertical-align: -10px">
            <span style="vertical-align: top">
                <img src="pattern.png" style="vertical-align: -10px">
                <span style="vertical-align: -10px">
                    <img src="pattern.png" style="vertical-align: bottom">
                </span>
            </span>
            <span style="vertical-align: bottom">
                <img src="pattern.png" style="vertical-align: 6px">
            </span>
        </span>''')
    html, = page.children
    body, = html.children
    line, = body.children
    span_1, = line.children
    img_1, img_2, span_2, span_4 = span_1.children
    img_3, span_3 = span_2.children
    img_4, = span_3.children
    img_5, = span_4.children
    assert body.height == line.height
    assert line.height == 40
    assert img_1.position_y == 0
    assert img_2.position_y == 36
    assert img_3.position_y == 6
    assert img_4.position_y == 36
    assert img_5.position_y == 30

    page, = parse('''
        <span style="font-size: 0">
            <img src="pattern.png" style="vertical-align: bottom">
            <img src="pattern.png" style="vertical-align: top; height: 100px">
        </span>
    ''')
    html, = page.children
    body, = html.children
    line, = body.children
    span, = line.children
    img_1, img_2 = span.children
    assert img_1.position_y == 96
    assert img_2.position_y == 0

    # Reference for the next test
    page, = parse('''
        <span style="font-size: 0; vertical-align: top">
            <img src="pattern.png">
        </span>
    ''')
    html, = page.children
    body, = html.children
    line, = body.children
    span, = line.children
    img_1, = span.children
    assert img_1.position_y == 0

    # Should be the same as above
    page, = parse('''
        <span style="font-size: 0; vertical-align: top; display: inline-block">
            <img src="pattern.png">
        </span>''')
    html, = page.children
    body, = html.children
    line_1, = body.children
    span, = line_1.children
    line_2, = span.children
    img_1, = line_2.children
    assert img_1.element_tag == 'img'
    assert img_1.position_y == 0


@assert_no_logs
def test_text_align_left():
    """Test the left text alignment."""

    """
        <-------------------->  page, body
            +-----+
        +---+     |
        |   |     |
        +---+-----+

        ^   ^     ^          ^
        x=0 x=40  x=100      x=200
    """
    page, = parse('''
        <style>
            @page { size: 200px }
        </style>
        <body>
            <img src="pattern.png" style="width: 40px"
            ><img src="pattern.png" style="width: 60px">''')
    html, = page.children
    body, = html.children
    line, = body.children
    img_1, img_2 = line.children
    # initial value for text-align: left (in ltr text)
    assert img_1.position_x == 0
    assert img_2.position_x == 40


@assert_no_logs
def test_text_align_right():
    """Test the right text alignment."""

    """
        <-------------------->  page, body
                       +-----+
                   +---+     |
                   |   |     |
                   +---+-----+

        ^          ^   ^     ^
        x=0        x=100     x=200
                       x=140
    """
    page, = parse('''
        <style>
            @page { size: 200px }
            body { text-align: right }
        </style>
        <body>
            <img src="pattern.png" style="width: 40px"
            ><img src="pattern.png" style="width: 60px">''')
    html, = page.children
    body, = html.children
    line, = body.children
    img_1, img_2 = line.children
    assert img_1.position_x == 100  # 200 - 60 - 40
    assert img_2.position_x == 140  # 200 - 60


@assert_no_logs
def test_text_align_center():
    """Test the center text alignment."""

    """
        <-------------------->  page, body
                  +-----+
              +---+     |
              |   |     |
              +---+-----+

        ^     ^   ^     ^
        x=    x=50     x=150
                  x=90
    """
    page, = parse('''
        <style>
            @page { size: 200px }
            body { text-align: center }
        </style>
        <body>
            <img src="pattern.png" style="width: 40px"
            ><img src="pattern.png" style="width: 60px">''')
    html, = page.children
    body, = html.children
    line, = body.children
    img_1, img_2 = line.children
    assert img_1.position_x == 50
    assert img_2.position_x == 90


@assert_no_logs
def test_text_align_justify():
    """Test justified text."""
    page, = parse('''
        <style>
            @page { size: 300px 1000px }
            body { text-align: justify }
        </style>
        <p><img src="pattern.png" style="width: 40px">
            <strong>
                <img src="pattern.png" style="width: 60px">
                <img src="pattern.png" style="width: 10px">
                <img src="pattern.png" style="width: 100px"
            ></strong><img src="pattern.png" style="width: 290px"
            ><!-- Last image will be on its own line. -->''')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    line_1, line_2 = paragraph.children
    image_1, space_1, strong = line_1.children
    image_2, space_2, image_3, space_3, image_4 = strong.children
    image_5, = line_2.children
    assert space_1.text == ' '
    assert space_2.text == ' '
    assert space_3.text == ' '

    assert image_1.position_x == 0
    assert space_1.position_x == 40
    assert strong.position_x == 70
    assert image_2.position_x == 70
    assert space_2.position_x == 130
    assert image_3.position_x == 160
    assert space_3.position_x == 170
    assert image_4.position_x == 200
    assert strong.width == 230

    assert image_5.position_x == 0

    # single-word line (zero spaces)
    page, = parse('''
        <style>
            body { text-align: justify; width: 50px }
        </style>
        <p>Supercalifragilisticexpialidocious bar</p>
    ''')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    line_1, line_2 = paragraph.children
    text, = line_1.children
    assert text.position_x == 0


@assert_no_logs
def test_word_spacing():
    """Test word-spacing."""
    # keep the empty <style> as a regression test: element.text is None
    # (Not a string.)
    page, = parse('''
        <style></style>
        <body><strong>Lorem ipsum dolor<em>sit amet</em></strong>''')
    html, = page.children
    body, = html.children
    line, = body.children
    strong_1, = line.children
    assert 200 <= strong_1.width <= 250

    # TODO: Pango gives only half of word-spacing to a space at the end
    # of a TextBox. Is this what we want?
    page, = parse('''
        <style>strong { word-spacing: 11px }</style>
        <body><strong>Lorem ipsum dolor<em>sit amet</em></strong>''')
    html, = page.children
    body, = html.children
    line, = body.children
    strong_2, = line.children
    assert strong_2.width - strong_1.width == 33


@assert_no_logs
def test_letter_spacing():
    """Test letter-spacing."""
    page, = parse('''
        <body><strong>Supercalifragilisticexpialidocious</strong>''')
    html, = page.children
    body, = html.children
    line, = body.children
    strong_1, = line.children
    assert 250 <= strong_1.width <= 300

    page, = parse('''
        <style>strong { letter-spacing: 11px }</style>
        <body><strong>Supercalifragilisticexpialidocious</strong>''')
    html, = page.children
    body, = html.children
    line, = body.children
    strong_2, = line.children
    assert strong_2.width - strong_1.width == 33 * 11


@assert_no_logs
def test_text_indent():
    """Test the text-indent property."""
    for indent in ['12px', '6%']:  # 6% of 200px is 12px
        page, = parse('''
            <style>
                @page { size: 220px }
                body { margin: 10px; text-indent: %(indent)s }
            </style>
            <p>Some text that is long enough that it take at least three line,
               but maybe more.
        ''' % {'indent': indent})
        html, = page.children
        body, = html.children
        paragraph, = body.children
        lines = paragraph.children
        text_1, = lines[0].children
        text_2, = lines[1].children
        text_3, = lines[2].children
        assert text_1.position_x == 22  # 10px margin-left + 12px indent
        assert text_2.position_x == 10  # No indent
        assert text_3.position_x == 10  # No indent


@assert_no_logs
def test_inline_replaced_auto_margins():
    """Test that auto margins are ignored for inline replaced boxes."""
    page, = parse('''
        <style>
            @page { size: 200px }
            img { display: inline; margin: auto; width: 50px }
        </style>
        <body><img src="pattern.png" />''')
    html, = page.children
    body, = html.children
    line, = body.children
    img, = line.children
    assert img.margin_top == 0
    assert img.margin_right == 0
    assert img.margin_bottom == 0
    assert img.margin_left == 0


@assert_no_logs
def test_empty_inline_auto_margins():
    """Test that horizontal auto margins are ignored for empty inline boxes."""
    page, = parse('''
        <style>
            @page { size: 200px }
            span { margin: auto }
        </style>
        <body><span></span>''')
    html, = page.children
    body, = html.children
    block, = body.children
    span, = block.children
    assert span.margin_top != 0
    assert span.margin_right == 0
    assert span.margin_bottom != 0
    assert span.margin_left == 0


@assert_no_logs
def test_box_sizing():
    """Test the box-sizing property.

    http://www.w3.org/TR/css3-ui/#box-sizing

    """
    page, = parse('''
        <style>
            @page { size: 100000px }
            body { width: 10000px; margin: 0 }
            div { width: 10%; height: 1000px;
                  margin: 100px; padding: 10px; border: 1px solid }
            div:nth-child(2) { box-sizing: content-box }
            div:nth-child(3) { box-sizing: padding-box }
            div:nth-child(4) { box-sizing: border-box }
        </style>
        <div></div>
        <div></div>
        <div></div>
        <div></div>
    ''')
    html, = page.children
    body, = html.children
    div_1, div_2, div_3, div_4 = body.children
    for div in div_1, div_2:
        assert div.style.box_sizing == 'content-box'
        assert div.width == 1000
        assert div.height == 1000
        assert div.padding_width() == 1020
        assert div.padding_height() == 1020
        assert div.border_width() == 1022
        assert div.border_height() == 1022
        assert div.margin_height() == 1222
        # margin_width() is the width of the containing block

    # padding-box
    assert div_3.style.box_sizing == 'padding-box'
    assert div_3.width == 980  # 1000 - 20
    assert div_3.height == 980
    assert div_3.padding_width() == 1000
    assert div_3.padding_height() == 1000
    assert div_3.border_width() == 1002
    assert div_3.border_height() == 1002
    assert div_3.margin_height() == 1202

    # border-box
    assert div_4.style.box_sizing == 'border-box'
    assert div_4.width == 978  # 1000 - 20 - 2
    assert div_4.height == 978
    assert div_4.padding_width() == 998
    assert div_4.padding_height() == 998
    assert div_4.border_width() == 1000
    assert div_4.border_height() == 1000
    assert div_4.margin_height() == 1200


@assert_no_logs
def test_table_column_width():
    source = '''
        <style>
            body { width: 20000px; margin: 0 }
            table {
              width: 10000px; margin: 0 auto; border-spacing: 100px 0;
              table-layout: fixed
            }
            td { border: 10px solid; padding: 1px }
        </style>
        <table>
            <col style="width: 10%">
            <tr>
                <td style="width: 30%" colspan=3>
                <td>
            </tr>
            <tr>
                <td>
                <td>
                <td>
                <td>
            </tr>
            <tr>
                <td>
                <td colspan=12>This cell will be truncated to grid width
                <td>This cell will be removed as it is beyond the grid width
            </tr>
        </table>
    '''
    with capture_logs() as logs:
        page, = parse(source)
    assert len(logs) == 1
    assert logs[0].startswith('WARNING: This table row has more columns than '
                              'the table, ignored 1 cell')
    html, = page.children
    body, = html.children
    wrapper, = body.children
    table, = wrapper.children
    row_group, = table.children
    first_row, second_row, third_row = row_group.children
    cells = [first_row.children, second_row.children, third_row.children]
    assert len(first_row.children) == 2
    assert len(second_row.children) == 4
    # Third cell here is completly removed
    assert len(third_row.children) == 2

    assert body.position_x == 0
    assert wrapper.position_x == 0
    assert wrapper.margin_left == 5000
    assert wrapper.content_box_x() == 5000  # auto margin-left
    assert wrapper.width == 10000
    assert table.position_x == 5000
    assert table.width == 10000
    assert row_group.position_x == 5100  # 5000 + border_spacing
    assert row_group.width == 9800  # 10000 - 2*border-spacing
    assert first_row.position_x == row_group.position_x
    assert first_row.width == row_group.width

    # This cell has colspan=3
    assert cells[0][0].position_x == 5100  # 5000 + border-spacing
    # `width` on a cell sets the content width
    assert cells[0][0].width == 3000  # 30% of 10000px
    assert cells[0][0].border_width() == 3022  # 3000 + borders + padding

    # Second cell of the first line, but on the fourth and last column
    assert cells[0][1].position_x == 8222  # 5100 + 3022 + border-spacing
    assert cells[0][1].border_width() == 6678  # 10000 - 3022 - 3*100
    assert cells[0][1].width == 6656  # 6678 - borders - padding

    assert cells[1][0].position_x == 5100  # 5000 + border-spacing
    # `width` on a column sets the border width of cells
    assert cells[1][0].border_width() == 1000  # 10% of 10000px
    assert cells[1][0].width == 978  # 1000 - borders - padding

    assert cells[1][1].position_x == 6200  # 5100 + 1000 + border-spacing
    assert cells[1][1].border_width() == 911  # (3022 - 1000 - 2*100) / 2
    assert cells[1][1].width == 889  # 911 - borders - padding

    assert cells[1][2].position_x == 7211  # 6200 + 911 + border-spacing
    assert cells[1][2].border_width() == 911  # (3022 - 1000 - 2*100) / 2
    assert cells[1][2].width == 889  # 911 - borders - padding

    # Same as cells[0][1]
    assert cells[1][3].position_x == 8222  # Also 7211 + 911 + border-spacing
    assert cells[1][3].border_width() == 6678
    assert cells[1][3].width == 6656

    # Same as cells[1][0]
    assert cells[2][0].position_x == 5100
    assert cells[2][0].border_width() == 1000
    assert cells[2][0].width == 978

    assert cells[2][1].position_x == 6200  # Same as cells[1][1]
    assert cells[2][1].border_width() == 8700  # 1000 - 1000 - 3*border-spacing
    assert cells[2][1].width == 8678  # 8700 - borders - padding
    assert cells[2][1].colspan == 3  # truncated to grid width

    page, = parse('''
        <style>
            table { width: 1000px; border-spacing: 100px; table-layout: fixed }
        </style>
        <table>
            <tr>
                <td style="width: 50%">
                <td style="width: 60%">
                <td>
            </tr>
        </table>
    ''')
    html, = page.children
    body, = html.children
    wrapper, = body.children
    table, = wrapper.children
    row_group, = table.children
    row, = row_group.children
    assert row.children[0].width == 500
    assert row.children[1].width == 600
    assert row.children[2].width == 0
    assert table.width == 1500  # 500 + 600 + 4 * border-spacing

    # Sum of columns width larger that the table width:
    # increase the table width
    page, = parse('''
        <style>
            table { width: 1000px; border-spacing: 100px; table-layout: fixed }
            td { width: 60% }
        </style>
        <table>
            <tr>
                <td>
                <td>
            </tr>
        </table>
    ''')
    html, = page.children
    body, = html.children
    wrapper, = body.children
    table, = wrapper.children
    row_group, = table.children
    row, = row_group.children
    cell_1, cell_2 = row.children
    assert cell_1.width == 600  # 60% of 1000px
    assert cell_2.width == 600
    assert table.width == 1500  # 600 + 600 + 3*border-spacing
    assert wrapper.width == table.width


@assert_no_logs
def test_table_row_height():
    page, = parse('''
        <table style="width: 1000px; border-spacing: 0 100px;
                      font: 20px/1em serif; margin: 3px; table-layout: fixed">
            <tr>
                <td rowspan=0 style="height: 420px; vertical-align: top"></td>
                <td>X<br>X<br>X</td>
                <td><table style="margin-top: 20px; border-spacing: 0">
                    <tr><td>X</td></tr></table></td>
                <td style="vertical-align: top">X</td>
                <td style="vertical-align: middle">X</td>
                <td style="vertical-align: bottom">X</td>
            </tr>
            <tr>
                <!-- cells with no text (no line boxes) is a corner case
                     in cell baselines -->
                <td style="padding: 15px"></td>
                <td><div style="height: 10px"></div></td>
            </tr>
            <tr></tr>
            <tr>
                <td style="vertical-align: bottom"></td>
            </tr>
        </table>
    ''')
    html, = page.children
    body, = html.children
    wrapper, = body.children
    table, = wrapper.children
    row_group, = table.children

    assert wrapper.position_y == 0
    assert table.position_y == 3  # 0 + margin-top
    assert table.height == 620  # sum of row heigths + 5*border-spacing
    assert wrapper.height == table.height
    assert row_group.position_y == 103  # 3 + border-spacing
    assert row_group.height == 420  # 620 - 2*border-spacing
    assert [row.height for row in row_group.children] == [
        80, 30, 0, 10]
    assert [row.position_y for row in row_group.children] == [
        # cumulative sum of previous row heights and border-spacings
        103, 283, 413, 513]
    assert [[cell.height for cell in row.children]
            for row in row_group.children] == [
        [420, 60, 40, 20, 20, 20],
        [0, 10],
        [],
        [0]
    ]
    assert [[cell.border_height() for cell in row.children]
            for row in row_group.children] == [
        [420, 80, 80, 80, 80, 80],
        [30, 30],
        [],
        [10]
    ]
    # The baseline of the first row is at 40px because of the third column.
    # The second column thus gets a top padding of 20px pushes the bottom
    # to 80px.The middle is at 40px.
    assert [[cell.padding_top for cell in row.children]
            for row in row_group.children] == [
        [0, 20, 0, 0, 30, 60],
        [15, 5],
        [],
        [10]
    ]
    assert [[cell.padding_bottom for cell in row.children]
            for row in row_group.children] == [
        [0, 0, 40, 60, 30, 0],
        [15, 15],
        [],
        [0]
    ]
    assert [[cell.position_y for cell in row.children]
            for row in row_group.children] == [
        [103, 103, 103, 103, 103, 103],
        [283, 283],
        [],
        [513]
    ]

    # A cell box cannot extend beyond the last row box of a table.
    page, = parse('''
        <table style="border-spacing: 0">
            <tr style="height: 10px">
                <td rowspan=5></td>
                <td></td>
            </tr>
            <tr style="height: 10px">
                <td></td>
            </tr>
        </table>
    ''')
    html, = page.children
    body, = html.children
    wrapper, = body.children
    table, = wrapper.children
    row_group, = table.children


@assert_no_logs
def test_table_wrapper():
    page, = parse('''
        <style>
            @page { size: 1000px }
            table { width: 600px; height: 500px; table-layout: fixed;
                    padding: 1px; border: 10px solid; margin: 100px; }
        </style>
        <table></table>
    ''')
    html, = page.children
    body, = html.children
    wrapper, = body.children
    table, = wrapper.children
    assert body.width == 1000
    assert wrapper.width == 600  # Not counting borders or padding
    assert wrapper.margin_left == 100
    assert table.margin_width() == 600
    assert table.width == 578  # 600 - 2*10 - 2*1, no margin
    # box-sizing in the UA stylesheet  makes `height: 500px` set this
    assert table.border_height() == 500
    assert table.height == 478  # 500 - 2*10 - 2*1
    assert table.margin_height() == 500  # no margin
    assert wrapper.height == 500
    assert wrapper.margin_height() == 700  # 500 + 2*100

    # Non-regression test: this used to cause an exception
    page, = parse('<html style="display: table">')


@assert_no_logs
def test_margin_boxes_fixed_dimension():
    # Corner boxes
    page, = parse('''
        <style>
            @page {
                @top-left-corner {
                    content: 'top_left';
                    padding: 10px;
                }
                @top-right-corner {
                    content: 'top_right';
                    padding: 10px;
                }
                @bottom-left-corner {
                    content: 'bottom_left';
                    padding: 10px;
                }
                @bottom-right-corner {
                    content: 'bottom_right';
                    padding: 10px;
                }

                size: 1000px;
                margin-top: 10%;
                margin-bottom: 40%;
                margin-left: 20%;
                margin-right: 30%;
            }
        </style>
    ''')
    html, top_left, top_right, bottom_left, bottom_right = page.children
    for margin_box, text in zip(
            [top_left, top_right, bottom_left, bottom_right],
            ['top_left', 'top_right', 'bottom_left', 'bottom_right']):

        line, = margin_box.children
        text, = line.children
        assert text == text

    # Check positioning and Rule 1 for fixed dimensions
    assert top_left.position_x == 0
    assert top_left.position_y == 0
    assert top_left.margin_width() == 200  # margin-left
    assert top_left.margin_height() == 100  # margin-top

    assert top_right.position_x == 700  # size-x - margin-right
    assert top_right.position_y == 0
    assert top_right.margin_width() == 300  # margin-right
    assert top_right.margin_height() == 100  # margin-top

    assert bottom_left.position_x == 0
    assert bottom_left.position_y == 600  # size-y - margin-bottom
    assert bottom_left.margin_width() == 200  # margin-left
    assert bottom_left.margin_height() == 400  # margin-bottom

    assert bottom_right.position_x == 700  # size-x - margin-right
    assert bottom_right.position_y == 600  # size-y - margin-bottom
    assert bottom_right.margin_width() == 300  # margin-right
    assert bottom_right.margin_height() == 400  # margin-bottom

    # Test rules 2 and 3
    page, = parse('''
        <style>
            @page {
                margin: 100px 200px;
                @bottom-left-corner {
                    content: "";
                    margin: 60px
                }
            }
        </style>
    ''')
    html, margin_box = page.children
    assert margin_box.margin_width() == 200
    assert margin_box.margin_left == 60
    assert margin_box.margin_right == 60
    assert margin_box.width == 80  # 200 - 60 - 60

    assert margin_box.margin_height() == 100
    # total was too big, the outside margin was ignored:
    assert margin_box.margin_top == 60
    assert margin_box.margin_bottom == 40  # Not 60
    assert margin_box.height == 0  # But not negative

    # Test rule 3 with a non-auto inner dimension
    page, = parse('''
        <style>
            @page {
                margin: 100px;
                @left-middle {
                    content: "";
                    margin: 10px;
                    width: 130px;
                }
            }
        </style>
    ''')
    html, margin_box = page.children
    assert margin_box.margin_width() == 100
    assert margin_box.margin_left == -40  # Not 10px
    assert margin_box.margin_right == 10
    assert margin_box.width == 130  # As specified

    # Test rule 4
    page, = parse('''
        <style>
            @page {
                margin: 100px;
                @left-bottom {
                    content: "";
                    margin-left: 10px;
                    margin-right: auto;
                    width: 70px;
                }
            }
        </style>
    ''')
    html, margin_box = page.children
    assert margin_box.margin_width() == 100
    assert margin_box.margin_left == 10  # 10px this time, no over-constrain
    assert margin_box.margin_right == 20
    assert margin_box.width == 70  # As specified

    # Test rules 2, 3 and 4
    page, = parse('''
        <style>
            @page {
                margin: 100px;
                @right-top {
                    content: "";
                    margin-right: 10px;
                    margin-left: auto;
                    width: 130px;
                }
            }
        </style>
    ''')
    html, margin_box = page.children
    assert margin_box.margin_width() == 100
    assert margin_box.margin_left == 0  # rule 2
    assert margin_box.margin_right == -30  # rule 3, after rule 2
    assert margin_box.width == 130  # As specified

    # Test rule 5
    page, = parse('''
        <style>
            @page {
                margin: 100px;
                @top-left {
                    content: "";
                    margin-top: 10px;
                    margin-bottom: auto;
                }
            }
        </style>
    ''')
    html, margin_box = page.children
    assert margin_box.margin_height() == 100
    assert margin_box.margin_top == 10
    assert margin_box.margin_bottom == 0
    assert margin_box.height == 90

    # Test rule 5
    page, = parse('''
        <style>
            @page {
                margin: 100px;
                @top-center {
                    content: "";
                    margin: auto 0;
                }
            }
        </style>
    ''')
    html, margin_box = page.children
    assert margin_box.margin_height() == 100
    assert margin_box.margin_top == 0
    assert margin_box.margin_bottom == 0
    assert margin_box.height == 100

    # Test rule 6
    page, = parse('''
        <style>
            @page {
                margin: 100px;
                @bottom-right {
                    content: "";
                    margin: auto;
                    height: 70px;
                }
            }
        </style>
    ''')
    html, margin_box = page.children
    assert margin_box.margin_height() == 100
    assert margin_box.margin_top == 15
    assert margin_box.margin_bottom == 15
    assert margin_box.height == 70

    # Rule 2 inhibits rule 6
    page, = parse('''
        <style>
            @page {
                margin: 100px;
                @bottom-center {
                    content: "";
                    margin: auto 0;
                    height: 150px;
                }
            }
        </style>
    ''')
    html, margin_box = page.children
    assert margin_box.margin_height() == 100
    assert margin_box.margin_top == 0
    assert margin_box.margin_bottom == -50  # outside
    assert margin_box.height == 150


@assert_no_logs
def test_preferred_widths():
    """Unit tests for preferred widths."""
    def get_float_width(body_width):
        page, = parse('''
            <body style="width: %spx">
            <p style="white-space: pre-line; float: left">
                Lorem ipsum dolor sit amet,
                  consectetur elit
            </p>
                       <!--  ^  No-break space here  -->
        ''' % body_width)
        html, = page.children
        body, = html.children
        paragraph, = body.children
        return paragraph.width
    # Not exact, depends on the installed fonts
    # Preferred minimum width:
    assert 120 < get_float_width(10) < 140
    # Preferred width:
    assert 220 < get_float_width(10000) < 240

    # Non-regression test:
    # Incorrect whitespace handling in preferred width used to cause
    # unnecessary line break.
    page, = parse('''
        <p style="float: left">Lorem <em>ipsum</em> dolor.</p>
    ''')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    assert len(paragraph.children) == 1
    assert isinstance(paragraph.children[0], boxes.LineBox)

    page, = parse('''
        <style>img { width: 20px }</style>
        <p style="float: left">
            <img src=pattern.png><img src=pattern.png><br>
            <img src=pattern.png></p>
    ''')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    assert paragraph.width == 40

    page, = parse('''<style>p { font: 20px Ahem }</style>
                     <p style="float: left">XX<br>XX<br>X</p>''')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    assert paragraph.width == 40

    # The space is the start of the line is collapsed.
    page, = parse('''<style>p { font: 20px Ahem }</style>
                     <p style="float: left">XX<br> XX<br>X</p>''')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    assert paragraph.width == 40


@assert_no_logs
def test_margin_boxes_variable_dimension():
    def get_widths(css):
        """Take some CSS to have inside @page

        Return margin-widths of the sub-sequence of the three margin boxes
        that are generated.

        The containing block’s width is 600px. It starts at x = 100 and ends
        at x = 700.

        """
        expected_at_keywords = [
            at_keyword for at_keyword in [
                '@top-left', '@top-center', '@top-right']
            if at_keyword + ' { content: ' in css]
        page, = parse('''
            <style>
                @page {
                    size: 800px;
                    margin: 100px;
                    padding: 42px;
                    border: 7px solid;
                    %s
                }
            </style>
        ''' % css)
        assert page.children[0].element_tag == 'html'
        margin_boxes = page.children[1:]
        assert [box.at_keyword for box in margin_boxes] == expected_at_keywords
        offsets = {'@top-left': 0, '@top-center': 0.5, '@top-right': 1}
        for box in margin_boxes:
            assert box.position_x == 100 + offsets[box.at_keyword] * (
                600 - box.margin_width())
        return [box.margin_width() for box in margin_boxes]

    def images(*widths):
        return ' '.join(
            'url(\'data:image/svg+xml,<svg width="%i" height="10"></svg>\')'
            % width for width in widths)

    # Use preferred widths if they fit
    css = '''
        @top-left { content: %s }
        @top-center { content: %s }
        @top-right { content: %s }
    ''' % (images(50, 50), images(50, 50), images(50, 50))
    assert get_widths(css) == [100, 100, 100]

    # 'auto' margins are set to 0
    css = '''
        @top-left { content: %s; margin: auto }
        @top-center { content: %s }
        @top-right { content: %s }
    ''' % (images(50, 50), images(50, 50), images(50, 50))
    assert get_widths(css) == [100, 100, 100]

    # Use at least minimum widths, even if boxes overlap
    css = '''
        @top-left { content: %s }
        @top-center { content: %s }
        @top-right { content: 'foo'; width: 200px }
    ''' % (images(100, 50), images(300, 150))
    # @top-center is 300px wide and centered: this leaves 150 on either side
    # There is 50px of overlap with @top-right
    assert get_widths(css) == [150, 300, 200]

    # In the intermediate case, distribute the remaining space proportionally
    css = '''
        @top-left { content: %s }
        @top-center { content: %s }
        @top-right { content: %s }
    ''' % (images(150, 150), images(150, 150), images(150, 150))
    assert get_widths(css) == [200, 200, 200]

    css = '''
        @top-left { content: %s }
        @top-center { content: %s }
        @top-right { content: %s }
    ''' % (images(100, 100, 100), images(100, 100), images(10))
    assert get_widths(css) == [220, 160, 10]

    css = '''
        @top-left { content: %s; width: 205px }
        @top-center { content: %s }
        @top-right { content: %s }
    ''' % (images(100, 100, 100), images(100, 100), images(10))
    assert get_widths(css) == [205, 190, 10]

    # 'width' and other properties have no effect without 'content'
    css = '''
        @top-left { width: 1000px; margin: 1000px; padding: 1000px;
                    border: 1000px solid }
        @top-center { content: %s }
        @top-right { content: %s }
    ''' % (images(100, 100), images(10))
    assert get_widths(css) == [200, 10]

    # This leaves 150px for @top-right’s shrink-to-fit
    css = '''
        @top-left { content: ''; width: 200px }
        @top-center { content: ''; width: 300px }
        @top-right { content: %s }
    ''' % images(50, 50)
    assert get_widths(css) == [200, 300, 100]

    css = '''
        @top-left { content: ''; width: 200px }
        @top-center { content: ''; width: 300px }
        @top-right { content: %s }
    ''' % images(100, 100, 100)
    assert get_widths(css) == [200, 300, 150]

    css = '''
        @top-left { content: ''; width: 200px }
        @top-center { content: ''; width: 300px }
        @top-right { content: %s }
    ''' % images(170, 175)
    assert get_widths(css) == [200, 300, 175]

    css = '''
        @top-left { content: ''; width: 200px }
        @top-center { content: ''; width: 300px }
        @top-right { content: %s }
    ''' % images(170, 175)
    assert get_widths(css) == [200, 300, 175]

    # Without @top-center

    css = '''
        @top-left { content: ''; width: 200px }
        @top-right { content: ''; width: 500px }
    '''
    assert get_widths(css) == [200, 500]

    css = '''
        @top-left { content: ''; width: 200px }
        @top-right { content: %s }
    ''' % images(150, 50, 150)
    assert get_widths(css) == [200, 350]

    css = '''
        @top-left { content: ''; width: 200px }
        @top-right { content: %s }
    ''' % images(150, 50, 150, 200)
    assert get_widths(css) == [200, 400]

    css = '''
        @top-left { content: %s }
        @top-right { content: ''; width: 200px }
    ''' % images(150, 50, 450)
    assert get_widths(css) == [450, 200]

    css = '''
        @top-left { content: %s }
        @top-right { content: %s }
    ''' % (images(150, 100), images(10, 120))
    assert get_widths(css) == [250, 130]

    css = '''
        @top-left { content: %s }
        @top-right { content: %s }
    ''' % (images(550, 100), images(10, 120))
    assert get_widths(css) == [550, 120]

    css = '''
        @top-left { content: %s }
        @top-right { content: %s }
    ''' % (images(250, 60), images(250, 180))
    # 250 + (100 * 1 / 4), 250 + (100 * 3 / 4)
    assert get_widths(css) == [275, 325]


@assert_no_logs
def test_margin_boxes_vertical_align():
    """
         3 px ->    +-----+
                    |  1  |
                    +-----+

                43 px ->   +-----+
                53 px ->   |  2  |
                           +-----+

                       83 px ->   +-----+
                                  |  3  |
                       103px ->   +-----+
    """
    page, = parse('''
        <style>
            @page {
                size: 800px;
                margin: 106px;  /* margin boxes’ content height is 100px */

                @top-left {
                    content: "foo"; line-height: 20px; border: 3px solid;
                    vertical-align: top;
                }
                @top-center {
                    content: "foo"; line-height: 20px; border: 3px solid;
                    vertical-align: middle;
                }
                @top-right {
                    content: "foo"; line-height: 20px; border: 3px solid;
                    vertical-align: bottom;
                }
            }
        </style>
    ''')
    html, top_left, top_center, top_right = page.children
    line_1, = top_left.children
    line_2, = top_center.children
    line_3, = top_right.children
    assert line_1.position_y == 3
    assert line_2.position_y == 43
    assert line_3.position_y == 83


@assert_no_logs
def test_margin_collapsing():
    """
    The vertical space between to sibling blocks is the max of their margins,
    not the sum. But that’s only the simplest case...
    """
    def assert_collapsing(vertical_space):
        assert vertical_space('10px', '15px') == 15  # not 25
        # "The maximum of the absolute values of the negative adjoining margins
        #  is deducted from the maximum of the positive adjoining margins"
        assert vertical_space('-10px', '15px') == 5
        assert vertical_space('10px', '-15px') == -5
        assert vertical_space('-10px', '-15px') == -15
        assert vertical_space('10px', 'auto') == 10  # 'auto' is 0
        return vertical_space

    def assert_NOT_collapsing(vertical_space):
        assert vertical_space('10px', '15px') == 25
        assert vertical_space('-10px', '15px') == 5
        assert vertical_space('10px', '-15px') == -5
        assert vertical_space('-10px', '-15px') == -25
        assert vertical_space('10px', 'auto') == 10  # 'auto' is 0
        return vertical_space

    # Siblings
    @assert_collapsing
    def vertical_space_1(p1_margin_bottom, p2_margin_top):
        page, = parse('''
            <style>
                p { font: 20px/1 serif } /* block height == 20px */
                #p1 { margin-bottom: %s }
                #p2 { margin-top: %s }
            </style>
            <p id=p1>Lorem ipsum
            <p id=p2>dolor sit amet
        ''' % (p1_margin_bottom, p2_margin_top))
        html, = page.children
        body, = html.children
        p1, p2 = body.children
        p1_bottom = p1.content_box_y() + p1.height
        p2_top = p2.content_box_y()
        return p2_top - p1_bottom

    # Not siblings, first is nested
    @assert_collapsing
    def vertical_space_2(p1_margin_bottom, p2_margin_top):
        page, = parse('''
            <style>
                p { font: 20px/1 serif } /* block height == 20px */
                #p1 { margin-bottom: %s }
                #p2 { margin-top: %s }
            </style>
            <div>
                <p id=p1>Lorem ipsum
            </div>
            <p id=p2>dolor sit amet
        ''' % (p1_margin_bottom, p2_margin_top))
        html, = page.children
        body, = html.children
        div, p2 = body.children
        p1, = div.children
        p1_bottom = p1.content_box_y() + p1.height
        p2_top = p2.content_box_y()
        return p2_top - p1_bottom

    # Not siblings, second is nested
    @assert_collapsing
    def vertical_space_3(p1_margin_bottom, p2_margin_top):
        page, = parse('''
            <style>
                p { font: 20px/1 serif } /* block height == 20px */
                #p1 { margin-bottom: %s }
                #p2 { margin-top: %s }
            </style>
            <p id=p1>Lorem ipsum
            <div>
                <p id=p2>dolor sit amet
            </div>
        ''' % (p1_margin_bottom, p2_margin_top))
        html, = page.children
        body, = html.children
        p1, div = body.children
        p2, = div.children
        p1_bottom = p1.content_box_y() + p1.height
        p2_top = p2.content_box_y()
        return p2_top - p1_bottom

    # Not siblings, second is doubly nested
    @assert_collapsing
    def vertical_space_4(p1_margin_bottom, p2_margin_top):
        page, = parse('''
            <style>
                p { font: 20px/1 serif } /* block height == 20px */
                #p1 { margin-bottom: %s }
                #p2 { margin-top: %s }
            </style>
            <p id=p1>Lorem ipsum
            <div>
                <div>
                    <p id=p2>dolor sit amet
                </div>
            </div>
        ''' % (p1_margin_bottom, p2_margin_top))
        html, = page.children
        body, = html.children
        p1, div1 = body.children
        div2, = div1.children
        p2, = div2.children
        p1_bottom = p1.content_box_y() + p1.height
        p2_top = p2.content_box_y()
        return p2_top - p1_bottom

    # Collapsing with children
    @assert_collapsing
    def vertical_space_5(margin_1, margin_2):
        page, = parse('''
            <style>
                p { font: 20px/1 serif } /* block height == 20px */
                #div1 { margin-top: %s }
                #div2 { margin-top: %s }
            </style>
            <p>Lorem ipsum
            <div id=div1>
                <div id=div2>
                    <p id=p2>dolor sit amet
                </div>
            </div>
        ''' % (margin_1, margin_2))
        html, = page.children
        body, = html.children
        p1, div1 = body.children
        div2, = div1.children
        p2, = div2.children
        p1_bottom = p1.content_box_y() + p1.height
        p2_top = p2.content_box_y()
        # Parent and element edge are the same:
        assert div1.border_box_y() == p2.border_box_y()
        assert div2.border_box_y() == p2.border_box_y()
        return p2_top - p1_bottom

    # Block formatting context: Not collapsing with children
    @assert_NOT_collapsing
    def vertical_space_6(margin_1, margin_2):
        page, = parse('''
            <style>
                p { font: 20px/1 serif } /* block height == 20px */
                #div1 { margin-top: %s; overflow: hidden }
                #div2 { margin-top: %s }
            </style>
            <p>Lorem ipsum
            <div id=div1>
                <div id=div2>
                    <p id=p2>dolor sit amet
                </div>
            </div>
        ''' % (margin_1, margin_2))
        html, = page.children
        body, = html.children
        p1, div1 = body.children
        div2, = div1.children
        p2, = div2.children
        p1_bottom = p1.content_box_y() + p1.height
        p2_top = p2.content_box_y()
        return p2_top - p1_bottom

    # Collapsing through an empty div
    @assert_collapsing
    def vertical_space_7(p1_margin_bottom, p2_margin_top):
        page, = parse('''
            <style>
                p { font: 20px/1 serif } /* block height == 20px */
                #p1 { margin-bottom: %s }
                #p2 { margin-top: %s }
                div { margin-bottom: %s; margin-top: %s }
            </style>
            <p id=p1>Lorem ipsum
            <div></div>
            <p id=p2>dolor sit amet
        ''' % (2 * (p1_margin_bottom, p2_margin_top)))
        html, = page.children
        body, = html.children
        p1, div, p2 = body.children
        p1_bottom = p1.content_box_y() + p1.height
        p2_top = p2.content_box_y()
        return p2_top - p1_bottom

    # The root element does not collapse
    @assert_NOT_collapsing
    def vertical_space_8(margin_1, margin_2):
        page, = parse('''
            <html>
                <style>
                    html { margin-top: %s }
                    body { margin-top: %s }
                </style>
                <body>
                    <p>Lorem ipsum
        ''' % (margin_1, margin_2))
        html, = page.children
        body, = html.children
        p1, = body.children
        p1_top = p1.content_box_y()
        # Vertical space from y=0
        return p1_top

    # <body> DOES collapse
    @assert_collapsing
    def vertical_space_9(margin_1, margin_2):
        page, = parse('''
            <html>
                <style>
                    body { margin-top: %s }
                    div { margin-top: %s }
                </style>
                <body>
                    <div>
                        <p>Lorem ipsum
        ''' % (margin_1, margin_2))
        html, = page.children
        body, = html.children
        div, = body.children
        p1, = div.children
        p1_top = p1.content_box_y()
        # Vertical space from y=0
        return p1_top


@assert_no_logs
def test_relative_positioning():
    page, = parse('''
        <style>
          p { height: 20px }
        </style>
        <p>1</p>
        <div style="position: relative; top: 10px">
            <p>2</p>
            <p style="position: relative; top: -5px; left: 5px">3</p>
            <p>4</p>
            <p style="position: relative; bottom: 5px; right: 5px">5</p>
            <p style="position: relative">6</p>
            <p>7</p>
        </div>
        <p>8</p>
    ''')
    html, = page.children
    body, = html.children
    p1, div, p8 = body.children
    p2, p3, p4, p5, p6, p7 = div.children
    assert (p1.position_x, p1.position_y) == (0, 0)
    assert (div.position_x, div.position_y) == (0, 30)
    assert (p2.position_x, p2.position_y) == (0, 30)
    assert (p3.position_x, p3.position_y) == (5, 45)  # (0 + 5, 50 - 5)
    assert (p4.position_x, p4.position_y) == (0, 70)
    assert (p5.position_x, p5.position_y) == (-5, 85)  # (0 - 5, 90 - 5)
    assert (p6.position_x, p6.position_y) == (0, 110)
    assert (p7.position_x, p7.position_y) == (0, 130)
    assert (p8.position_x, p8.position_y) == (0, 140)
    assert div.height == 120

    page, = parse('''
        <style>
          img { width: 20px }
          body { font-size: 0 } /* Remove spaces */
        </style>
        <body>
        <span><img src=pattern.png></span>
        <span style="position: relative; left: 10px">
            <img src=pattern.png>
            <img src=pattern.png
                 style="position: relative; left: -5px; top: 5px">
            <img src=pattern.png>
            <img src=pattern.png
                 style="position: relative; right: 5px; bottom: 5px">
            <img src=pattern.png style="position: relative">
            <img src=pattern.png>
        </span>
        <span><img src=pattern.png></span>
    ''')
    html, = page.children
    body, = html.children
    line, = body.children
    span1, span2, span3 = line.children
    img1, = span1.children
    img2, img3, img4, img5, img6, img7 = span2.children
    img8, = span3.children
    assert (img1.position_x, img1.position_y) == (0, 0)
    # Don't test the span2.position_y because it depends on fonts
    assert span2.position_x == 30
    assert (img2.position_x, img2.position_y) == (30, 0)
    assert (img3.position_x, img3.position_y) == (45, 5)  # (50 - 5, y + 5)
    assert (img4.position_x, img4.position_y) == (70, 0)
    assert (img5.position_x, img5.position_y) == (85, -5)  # (90 - 5, y - 5)
    assert (img6.position_x, img6.position_y) == (110, 0)
    assert (img7.position_x, img7.position_y) == (130, 0)
    assert (img8.position_x, img8.position_y) == (140, 0)
    assert span2.width == 120


@assert_no_logs
def test_absolute_positioning():
    page, = parse('''
        <div style="margin: 3px">
            <div style="height: 20px; width: 20px; position: absolute"></div>
            <div style="height: 20px; width: 20px; position: absolute;
                        left: 0"></div>
            <div style="height: 20px; width: 20px; position: absolute;
                        top: 0"></div>
        </div>
    ''')
    html, = page.children
    body, = html.children
    div1, = body.children
    div2, div3, div4 = div1.children
    assert div1.height == 0
    assert (div1.position_x, div1.position_y) == (0, 0)
    assert (div2.width, div2.height) == (20, 20)
    assert (div2.position_x, div2.position_y) == (3, 3)
    assert (div3.width, div3.height) == (20, 20)
    assert (div3.position_x, div3.position_y) == (0, 3)
    assert (div4.width, div4.height) == (20, 20)
    assert (div4.position_x, div4.position_y) == (3, 0)

    page, = parse('''
        <div style="position: relative; width: 20px">
            <div style="height: 20px; width: 20px; position: absolute"></div>
            <div style="height: 20px; width: 20px"></div>
        </div>
    ''')
    html, = page.children
    body, = html.children
    div1, = body.children
    div2, div3 = div1.children
    for div in (div1, div2, div3):
        assert (div.position_x, div.position_y) == (0, 0)
        assert (div.width, div.height) == (20, 20)

    page, = parse('''
        <body style="font-size: 0">
            <img src=pattern.png>
            <span style="position: relative">
                <span style="position: absolute">2</span>
                <span style="position: absolute">3</span>
                <span>4</span>
            </span>
    ''')
    html, = page.children
    body, = html.children
    line, = body.children
    img, span1 = line.children
    span2, span3, span4 = span1.children
    assert span1.position_x == 4
    assert (span2.position_x, span2.position_y) == (4, 0)
    assert (span3.position_x, span3.position_y) == (4, 0)
    assert span4.position_x == 4

    page, = parse('''
        <style> img { width: 5px; height: 20px} </style>
        <body style="font-size: 0">
            <img src=pattern.png>
            <span style="position: absolute">2</span>
            <img src=pattern.png>
    ''')
    html, = page.children
    body, = html.children
    line, = body.children
    img1, span, img2 = line.children
    assert (img1.position_x, img1.position_y) == (0, 0)
    assert (span.position_x, span.position_y) == (5, 0)
    assert (img2.position_x, img2.position_y) == (5, 0)

    page, = parse('''
        <style> img { width: 5px; height: 20px} </style>
        <body style="font-size: 0">
            <img src=pattern.png>
            <span style="position: absolute; display: block">2</span>
            <img src=pattern.png>
    ''')
    html, = page.children
    body, = html.children
    line, = body.children
    img1, span, img2 = line.children
    assert (img1.position_x, img1.position_y) == (0, 0)
    assert (span.position_x, span.position_y) == (0, 20)
    assert (img2.position_x, img2.position_y) == (5, 0)

    page, = parse('''
        <div style="position: relative; width: 20px; height: 60px;
                    border: 10px solid; padding-top: 6px; top: 5px; left: 1px">
            <div style="height: 20px; width: 20px; position: absolute;
                        bottom: 50%"></div>
            <div style="height: 20px; width: 20px; position: absolute;
                        top: 13px"></div>
        </div>
    ''')
    html, = page.children
    body, = html.children
    div1, = body.children
    div2, div3 = div1.children
    assert (div1.position_x, div1.position_y) == (1, 5)
    assert (div1.width, div1.height) == (20, 60)
    assert (div1.border_width(), div1.border_height()) == (40, 86)
    assert (div2.position_x, div2.position_y) == (11, 28)
    assert (div2.width, div2.height) == (20, 20)
    assert (div3.position_x, div3.position_y) == (11, 28)
    assert (div3.width, div3.height) == (20, 20)

    page, = parse('''
        <style>
          @page { size: 1000px 2000px }
          html { font-size: 0 }
          p { height: 20px }
        </style>
        <p>1</p>
        <div style="width: 100px">
            <p>2</p>
            <p style="position: absolute; top: -5px; left: 5px">3</p>
            <p style="margin: 3px">4</p>
            <p style="position: absolute; bottom: 5px; right: 15px;
                      width: 50px; height: 10%;
                      padding: 3px; margin: 7px">5
                <span>
                  <img src="pattern.png">
                  <span style="position: absolute"></span>
                  <span style="position: absolute; top: -10px; right: 5px;
                               width: 20px; height: 15px"></span>
                </span>
            </p>
            <p style="margin-top: 8px">6</p>
        </div>
        <p>7</p>
    ''')
    html, = page.children
    body, = html.children
    p1, div, p7 = body.children
    p2, p3, p4, p5, p6 = div.children
    line, = p5.children
    span1, = line.children
    img, span2, span3 = span1.children
    assert (p1.position_x, p1.position_y) == (0, 0)
    assert (div.position_x, div.position_y) == (0, 20)
    assert (p2.position_x, p2.position_y) == (0, 20)
    assert (p3.position_x, p3.position_y) == (5, -5)
    assert (p4.position_x, p4.position_y) == (0, 40)
    # p5 x = page width - right - margin/padding/border - width
    #      = 1000       - 15    - 2 * 10                - 50
    #      = 915
    # p5 y = page height - bottom - margin/padding/border - height
    #      = 2000        - 5      - 2 * 10                - 200
    #      = 1775
    assert (p5.position_x, p5.position_y) == (915, 1775)
    assert (img.position_x, img.position_y) == (925, 1785)
    assert (span2.position_x, span2.position_y) == (929, 1785)
    # span3 x = p5 right - p5 margin - span width - span right
    #         = 985      - 7         - 20         - 5
    #         = 953
    # span3 y = p5 y + p5 margin top + span top
    #         = 1775 + 7             + -10
    #         = 1772
    assert (span3.position_x, span3.position_y) == (953, 1772)
    # p6 y = p4 y + p4 margin height - margin collapsing
    #      = 40   + 26               - 3
    #      = 63
    assert (p6.position_x, p6.position_y) == (0, 63)
    assert div.height == 71  # 20*3 + 2*3 + 8 - 3
    assert (p7.position_x, p7.position_y) == (0, 91)


@assert_no_logs
def test_absolute_images():
    page, = parse('''
        <style>
            img { display: block; position: absolute }
        </style>
        <div style="margin: 10px">
            <img src=pattern.png />
            <img src=pattern.png style="left: 15px" />
        </div>
    ''')
    html, = page.children
    body, = html.children
    div, = body.children
    img1, img2 = div.children
    assert div.height == 0
    assert (div.position_x, div.position_y) == (0, 0)
    assert (img1.position_x, img1.position_y) == (10, 10)
    assert (img1.width, img1.height) == (4, 4)
    assert (img2.position_x, img2.position_y) == (15, 10)
    assert (img2.width, img2.height) == (4, 4)

    # TODO: test the various cases in absolute_replaced()


@assert_no_logs
def test_fixed_positioning():
    # TODO:test page-break-before: left/right
    page_1, page_2, page_3 = parse('''
        a
        <div style="page-break-before: always; page-break-after: always">
            <p style="position: fixed">b</p>
        </div>
        c
    ''')
    html, = page_1.children
    assert [c.element_tag for c in html.children] == ['body', 'p']
    html, = page_2.children
    body, = html.children
    div, = body.children
    assert [c.element_tag for c in div.children] == ['p']
    html, = page_3.children
    assert [c.element_tag for c in html.children] == ['p', 'body']


@assert_no_logs
def test_floats():
    # adjacent-floats-001
    page, = parse('''
        <style>
            div { float: left }
            img { width: 100px; vertical-align: top }
        </style>
        <div><img src=pattern.png /></div>
        <div><img src=pattern.png /></div>''')
    html, = page.children
    body, = html.children
    div_1, div_2 = body.children
    assert outer_area(div_1) == (0, 0, 100, 100)
    assert outer_area(div_2) == (100, 0, 100, 100)

    # c414-flt-fit-000
    page, = parse('''
        <style>
            body { width: 290px }
            div { float: left; width: 100px;  }
            img { width: 60px; vertical-align: top }
        </style>
        <div><img src=pattern.png /><!-- 1 --></div>
        <div><img src=pattern.png /><!-- 2 --></div>
        <div><img src=pattern.png /><!-- 4 --></div>
        <img src=pattern.png /><!-- 3
        --><img src=pattern.png /><!-- 5 -->''')
    html, = page.children
    body, = html.children
    div_1, div_2, div_4, anon_block = body.children
    line_3, line_5 = anon_block.children
    img_3, = line_3.children
    img_5, = line_5.children
    assert outer_area(div_1) == (0, 0, 100, 60)
    assert outer_area(div_2) == (100, 0, 100, 60)
    assert outer_area(img_3) == (200, 0, 60, 60)

    assert outer_area(div_4) == (0, 60, 100, 60)
    assert outer_area(img_5) == (100, 60, 60, 60)

    # c414-flt-fit-002
    page, = parse('''
        <style type="text/css">
            body { width: 200px }
            p { width: 70px; height: 20px }
            .left { float: left }
            .right { float: right }
        </style>
        <p class="left"> ⇦ A 1 </p>
        <p class="left"> ⇦ B 2 </p>
        <p class="left"> ⇦ A 3 </p>
        <p class="right"> B 4 ⇨ </p>
        <p class="left"> ⇦ A 5 </p>
        <p class="right"> B 6 ⇨ </p>
        <p class="right"> B 8 ⇨ </p>
        <p class="left"> ⇦ A 7 </p>
        <p class="left"> ⇦ A 9 </p>
        <p class="left"> ⇦ B 10 </p>
    ''')
    html, = page.children
    body, = html.children
    positions = [(paragraph.position_x, paragraph.position_y)
                 for paragraph in body.children]
    assert positions == [
        (0, 0), (70, 0), (0, 20), (130, 20), (0, 40), (130, 40),
        (130, 60), (0, 60), (0, 80), (70, 80), ]

    # c414-flt-wrap-000 ... more or less
    page, = parse('''
        <style>
            body { width: 100px }
            p { float: left; height: 100px }
            img { width: 60px; vertical-align: top }
        </style>
        <p style="width: 20px"></p>
        <p style="width: 100%"></p>
        <img src=pattern.png /><img src=pattern.png />
    ''')
    html, = page.children
    body, = html.children
    p_1, p_2, anon_block = body.children
    line_1, line_2 = anon_block.children
    assert anon_block.position_y == 0
    assert (line_1.position_x, line_1.position_y) == (20, 0)
    assert (line_2.position_x, line_2.position_y) == (0, 200)

    # c414-flt-wrap-000 with text ... more or less
    page, = parse('''
        <style>
            body { width: 100px; font: 60px Ahem; }
            p { float: left; height: 100px }
            img { width: 60px; vertical-align: top }
        </style>
        <p style="width: 20px"></p>
        <p style="width: 100%"></p>
        A B
    ''')
    html, = page.children
    body, = html.children
    p_1, p_2, anon_block = body.children
    line_1, line_2 = anon_block.children
    assert anon_block.position_y == 0
    assert (line_1.position_x, line_1.position_y) == (20, 0)
    assert (line_2.position_x, line_2.position_y) == (0, 200)

    # floats-placement-vertical-001b
    page, = parse('''
        <style>
            body { width: 90px; font-size: 0 }
            img { vertical-align: top }
        </style>
        <body>
        <span>
            <img src=pattern.png style="width: 50px" />
            <img src=pattern.png style="width: 50px" />
            <img src=pattern.png style="float: left; width: 30px" />
        </span>
    ''')
    html, = page.children
    body, = html.children
    line_1, line_2 = body.children
    span_1, = line_1.children
    span_2, = line_2.children
    img_1, = span_1.children
    img_2, img_3 = span_2.children
    assert outer_area(img_1) == (0, 0, 50, 50)
    assert outer_area(img_2) == (30, 50, 50, 50)
    assert outer_area(img_3) == (0, 50, 30, 30)

    # Variant of the above: no <span>
    page, = parse('''
        <style>
            body { width: 90px; font-size: 0 }
            img { vertical-align: top }
        </style>
        <body>
        <img src=pattern.png style="width: 50px" />
        <img src=pattern.png style="width: 50px" />
        <img src=pattern.png style="float: left; width: 30px" />
    ''')
    html, = page.children
    body, = html.children
    line_1, line_2 = body.children
    img_1, = line_1.children
    img_2, img_3 = line_2.children
    assert outer_area(img_1) == (0, 0, 50, 50)
    assert outer_area(img_2) == (30, 50, 50, 50)
    assert outer_area(img_3) == (0, 50, 30, 30)

    # Floats do no affect other pages
    page_1, page_2 = parse('''
        <style>
            body { width: 90px; font-size: 0 }
            img { vertical-align: top }
        </style>
        <body>
        <img src=pattern.png style="float: left; width: 30px" />
        <img src=pattern.png style="width: 50px" />
        <div style="page-break-before: always"></div>
        <img src=pattern.png style="width: 50px" />
    ''')
    html, = page_1.children
    body, = html.children
    float_img, anon_block, = body.children
    line, = anon_block.children
    img_1, = line.children
    assert outer_area(float_img) == (0, 0, 30, 30)
    assert outer_area(img_1) == (30, 0, 50, 50)

    html, = page_2.children
    body, = html.children
    div, anon_block = body.children
    line, = anon_block.children
    img_2, = line.children
    assert outer_area(img_2) == (0, 0, 50, 50)


@assert_no_logs
def test_floats_page_breaks():
    """Tests the page breaks when floated boxes
    do not fit the page."""

    # Tests floated images shorter than the page
    pages = parse('''
        <style>
            @page { size: 100px; margin: 10px }
            img { height: 45px; width:70px; float: left;}
        </style>
        <body>
            <img src=pattern.png>
                    <!-- page break should be here !!! -->
            <img src=pattern.png>
    ''')

    assert len(pages) == 2

    page_images = []
    for page in pages:
        images = [d for d in page.descendants() if d.element_tag == 'img']
        assert all([img.element_tag == 'img' for img in images])
        assert all([img.position_x == 10 for img in images])
        page_images.append(images)
        del images
    positions_y = [[img.position_y for img in images]
                   for images in page_images]
    assert positions_y == [[10], [10]]

    # Tests floated images taller than the page
    pages = parse('''
        <style>
            @page { size: 100px; margin: 10px }
            img { height: 81px; width:70px; float: left;}
        </style>
        <body>
            <img src=pattern.png>
                    <!-- page break should be here !!! -->
            <img src=pattern.png>
    ''')

    assert len(pages) == 2

    page_images = []
    for page in pages:
        images = [d for d in page.descendants() if d.element_tag == 'img']
        assert all([img.element_tag == 'img' for img in images])
        assert all([img.position_x == 10 for img in images])
        page_images.append(images)
        del images
    positions_y = [[img.position_y for img in images]
                   for images in page_images]
    assert positions_y == [[10], [10]]

    # Tests floated images shorter than the page
    pages = parse('''
        <style>
            @page { size: 100px; margin: 10px }
            img { height: 30px; width:70px; float: left;}
        </style>
        <body>
            <img src=pattern.png>
            <img src=pattern.png>
                    <!-- page break should be here !!! -->
            <img src=pattern.png>
            <img src=pattern.png>
                    <!-- page break should be here !!! -->
            <img src=pattern.png>
    ''')

    assert len(pages) == 3

    page_images = []
    for page in pages:
        images = [d for d in page.descendants() if d.element_tag == 'img']
        assert all([img.element_tag == 'img' for img in images])
        assert all([img.position_x == 10 for img in images])
        page_images.append(images)
        del images
    positions_y = [[img.position_y for img in images]
                   for images in page_images]
    assert positions_y == [[10, 40], [10, 40], [10]]


@assert_no_logs
def test_font_stretch():
    page, = parse('''
        <style>p { float: left }</style>
        <p>Hello, world!</p>
        <p style="font-stretch: semi-condensed">Hello, world!</p>
        <p style="font-stretch: semi-expanded">Hello, world!</p>
    ''')
    html, = page.children
    body, = html.children
    p_1, p_2, p_3 = body.children
    normal = p_1.width
    condensed = p_2.width
    assert condensed < normal
    # TODO: when @font-face is supported use a font with an expanded variant.
#    expanded = p_3.width
#    assert normal < expanded


@assert_no_logs
def test_box_decoration_break():
    # http://www.w3.org/TR/css3-background/#the-box-decoration-break
    # Property not implemented yet, always "slice".
    page_1, page_2 = parse('''
        <style>
            @page { size: 100px }
            p { padding: 2px; border: 3px solid; margin: 5px }
            img { height: 40px; vertical-align: top }
        </style>
        <p>
            <img src=pattern.png><br>
            <img src=pattern.png><br>
            <img src=pattern.png><br>
            <img src=pattern.png><br>''')
    html, = page_1.children
    body, = html.children
    paragraph, = body.children
    line_1, line_2 = paragraph.children
    assert paragraph.position_y == 0
    assert paragraph.margin_top == 5
    assert paragraph.border_top_width == 3
    assert paragraph.padding_top == 2
    assert paragraph.content_box_y() == 10
    assert line_1.position_y == 10
    assert line_2.position_y == 50
    assert paragraph.height == 80
    assert paragraph.margin_bottom == 0
    assert paragraph.border_bottom_width == 0
    assert paragraph.padding_bottom == 0
    assert paragraph.margin_height() == 90

    html, = page_2.children
    body, = html.children
    paragraph, = body.children
    line_1, line_2 = paragraph.children
    assert paragraph.position_y == 0
    assert paragraph.margin_top == 0
    assert paragraph.border_top_width == 0
    assert paragraph.padding_top == 0
    assert paragraph.content_box_y() == 0
    assert line_1.position_y == 0
    assert line_2.position_y == 40
    assert paragraph.height == 80
    assert paragraph.padding_bottom == 2
    assert paragraph.border_bottom_width == 3
    assert paragraph.margin_bottom == 5
    assert paragraph.margin_height() == 90


@assert_no_logs
def test_hyphenation():
    def line_count(source):
        page, = parse('<html style="width: 5em">' + source)
        html, = page.children
        body, = html.children
        lines = body.children
        return len(lines)

    # Default: no hyphenation
    assert line_count('<body>hyphenation') == 1
    # lang only: no hyphenation
    assert line_count(
        '<body lang=en>hyphenation') == 1
    # `hyphens: auto` only: no hyphenation
    assert line_count(
        '<body style="-weasy-hyphens: auto">hyphenation') == 1
    # lang + `hyphens: auto`: hyphenation
    assert line_count(
        '<body style="-weasy-hyphens: auto" lang=en>hyphenation') > 1

    # Hyphenation with soft hyphens
    assert line_count('<body>hyp&shy;henation') == 2
    # … unless disabled
    assert line_count(
        '<body style="-weasy-hyphens: none">hyp&shy;henation') == 1


@assert_no_logs
def test_hyphenate_character():
    page, = parse(
        '<html style="width: 5em">'
        '<body style="-weasy-hyphens: auto;'
        '-weasy-hyphenate-character: \'!\'" lang=en>'
        'hyphenation')
    html, = page.children
    body, = html.children
    lines = body.children
    assert len(lines) > 1
    assert lines[0].children[0].text.endswith('!')
    full_text = ''.join(line.children[0].text for line in lines)
    assert full_text.replace('!', '') == 'hyphenation'

    page, = parse(
        '<html style="width: 5em">'
        '<body style="-weasy-hyphens: auto;'
        '-weasy-hyphenate-character: \'é\'" lang=en>'
        'hyphenation')
    html, = page.children
    body, = html.children
    lines = body.children
    assert len(lines) > 1
    assert lines[0].children[0].text.endswith('é')
    full_text = ''.join(line.children[0].text for line in lines)
    assert full_text.replace('é', '') == 'hyphenation'

    page, = parse(
        '<html style="width: 5em">'
        '<body style="-weasy-hyphens: auto;'
        '-weasy-hyphenate-character: \'ù ù\'" lang=en>'
        'hyphenation')
    html, = page.children
    body, = html.children
    lines = body.children
    assert len(lines) > 1
    assert lines[0].children[0].text.endswith('ù ù')
    full_text = ''.join(line.children[0].text for line in lines)
    assert full_text.replace(' ', '').replace('ù', '') == 'hyphenation'

    page, = parse(
        '<html style="width: 5em">'
        '<body style="-weasy-hyphens: auto;'
        '-weasy-hyphenate-character: \'\'" lang=en>'
        'hyphenation')
    html, = page.children
    body, = html.children
    lines = body.children
    assert len(lines) > 1
    full_text = ''.join(line.children[0].text for line in lines)
    assert full_text == 'hyphenation'

    # TODO: strange error with some characters
    # page, = parse(
    #     '<html style="width: 5em">'
    #     '<body style="-weasy-hyphens: auto;'
    #     '-weasy-hyphenate-character: \'———\'" lang=en>'
    #     'hyphenation')
    # html, = page.children
    # body, = html.children
    # lines = body.children
    # assert len(lines) > 1
    # assert lines[0].children[0].text.endswith('———')
    # full_text = ''.join(line.children[0].text for line in lines)
    # assert full_text.replace('—', '') == 'hyphenation'


@assert_no_logs
def test_hyphenate_limit_zone():
    page, = parse(
        '<html style="width: 10em">'
        '<body style="-weasy-hyphens: auto;'
        '-weasy-hyphenate-limit-zone: 0" lang=en>'
        'mmmmm hyphenation')
    html, = page.children
    body, = html.children
    lines = body.children
    assert len(lines) == 2
    assert lines[0].children[0].text.endswith('‐')
    full_text = ''.join(line.children[0].text for line in lines)
    assert full_text.replace('‐', '') == 'mmmmm hyphenation'

    page, = parse(
        '<html style="width: 10em">'
        '<body style="-weasy-hyphens: auto;'
        '-weasy-hyphenate-limit-zone: 9em" lang=en>'
        'mmmmm hyphenation')
    html, = page.children
    body, = html.children
    lines = body.children
    assert len(lines) > 1
    assert lines[0].children[0].text.endswith('mm')
    full_text = ''.join(line.children[0].text for line in lines)
    assert full_text == 'mmmmmhyphenation'

    page, = parse(
        '<html style="width: 10em">'
        '<body style="-weasy-hyphens: auto;'
        '-weasy-hyphenate-limit-zone: 5%" lang=en>'
        'mmmmm hyphenation')
    html, = page.children
    body, = html.children
    lines = body.children
    assert len(lines) == 2
    assert lines[0].children[0].text.endswith('‐')
    full_text = ''.join(line.children[0].text for line in lines)
    assert full_text.replace('‐', '') == 'mmmmm hyphenation'

    page, = parse(
        '<html style="width: 10em">'
        '<body style="-weasy-hyphens: auto;'
        '-weasy-hyphenate-limit-zone: 95%" lang=en>'
        'mmmmm hyphenation')
    html, = page.children
    body, = html.children
    lines = body.children
    assert len(lines) > 1
    assert lines[0].children[0].text.endswith('mm')
    full_text = ''.join(line.children[0].text for line in lines)
    assert full_text == 'mmmmmhyphenation'


@assert_no_logs
def test_hyphenate_limit_chars():
    def line_count(limit_chars):
        page, = parse((
            '<html style="width: 1em">'
            '<body style="-weasy-hyphens: auto;'
            '-weasy-hyphenate-limit-chars: %s" lang=en>'
            'hyphen') % limit_chars)
        html, = page.children
        body, = html.children
        lines = body.children
        return len(lines)

    assert line_count('auto') == 2
    assert line_count('auto auto 0') == 2
    assert line_count('0 0 0') == 2
    assert line_count('4 4 auto') == 1
    assert line_count('6 2 4') == 2
    assert line_count('auto 1 auto') == 2
    assert line_count('7 auto auto') == 1
    assert line_count('6 auto auto') == 2
    assert line_count('5 2') == 2
    assert line_count('3') == 2
    assert line_count('2 4 6') == 1
    assert line_count('auto 4') == 1
    assert line_count('auto 2') == 2


@assert_no_logs
def test_overflow_wrap():
    def get_lines(wrap, text):
        page, = parse('''
            <style>
                body {width: 80px; overflow: hidden; font-family: ahem; }
                span {overflow-wrap: %s; white-space: normal; }
            </style>
            <body style="-weasy-hyphens: auto;" lang="en">
                <span>%s
        ''' % (wrap, text))
        html, = page.children
        body, = html.children
        body_lines = []
        for line in body.children:
            box, = line.children
            textBox, = box.children
            body_lines.append(textBox.text)
        return body_lines

    # break-word
    lines = get_lines('break-word', 'aaaaaaaa')
    assert len(lines) > 1
    full_text = ''.join(line for line in lines)
    assert full_text == 'aaaaaaaa'

    # normal
    lines = get_lines('normal', 'aaaaaaaa')
    assert len(lines) == 1
    full_text = ''.join(line for line in lines)
    assert full_text == 'aaaaaaaa'

    # break-word after hyphenation
    lines = get_lines('break-word', 'hyphenations')
    assert len(lines) > 3
    full_text = ''.join(line for line in lines)
    assert full_text == "hy\u2010phen\u2010ations"

    # break word after normal white-space wrap and hyphenation
    lines = get_lines(
        'break-word', "A splitted word.  An hyphenated word.")
    assert len(lines) > 8
    full_text = ''.join(line for line in lines)
    assert full_text == "Asplittedword.Anhy\u2010phen\u2010atedword."


@assert_no_logs
def test_white_space():
    """Test the white-space property."""
    def lines(width, space):
        page, = parse('''
            <style>
              body { font-size: 100px; width: %ipx }
              span { white-space: %s }
            </style>
            <body><span>This    \n    is text''' % (width, space))
        html, = page.children
        body, = html.children
        return body.children

    line1, line2, line3 = lines(1, 'normal')
    box1, = line1.children
    text1, = box1.children
    assert text1.text == 'This'
    box2, = line2.children
    text2, = box2.children
    assert text2.text == 'is'
    box3, = line3.children
    text3, = box3.children
    assert text3.text == 'text'

    line1, line2 = lines(1, 'pre')
    box1, = line1.children
    text1, = box1.children
    assert text1.text == 'This\xA0\xA0\xA0\xA0'
    box2, = line2.children
    text2, = box2.children
    assert text2.text == '\xA0\xA0\xA0\xA0is\xA0text'

    line1, = lines(1, 'nowrap')
    box1, = line1.children
    text1, = box1.children
    assert text1.text == 'This\xA0is\xA0text'

    line1, line2, line3, line4 = lines(1, 'pre-wrap')
    box1, = line1.children
    text1, = box1.children
    assert text1.text == 'This\xA0\xA0\xA0\xA0\u200b'
    box2, = line2.children
    text2, = box2.children
    assert text2.text == '\xA0\xA0\xA0\xA0\u200b'
    box3, = line3.children
    text3, = box3.children
    assert text3.text == 'is\xA0\u200b'
    box4, = line4.children
    text4, = box4.children
    assert text4.text == 'text'

    line1, line2, line3 = lines(1, 'pre-line')
    box1, = line1.children
    text1, = box1.children
    assert text1.text == 'This'
    box2, = line2.children
    text2, = box2.children
    assert text2.text == 'is'
    box3, = line3.children
    text3, = box3.children
    assert text3.text == 'text'

    line1, = lines(1000000, 'normal')
    box1, = line1.children
    text1, = box1.children
    assert text1.text == 'This is text'

    line1, line2 = lines(1000000, 'pre')
    box1, = line1.children
    text1, = box1.children
    assert text1.text == 'This\xA0\xA0\xA0\xA0'
    box2, = line2.children
    text2, = box2.children
    assert text2.text == '\xA0\xA0\xA0\xA0is\xA0text'

    line1, = lines(1000000, 'nowrap')
    box1, = line1.children
    text1, = box1.children
    assert text1.text == 'This\xA0is\xA0text'

    line1, line2 = lines(1000000, 'pre-wrap')
    box1, = line1.children
    text1, = box1.children
    assert text1.text == 'This\xA0\xA0\xA0\xA0\u200b'
    box2, = line2.children
    text2, = box2.children
    assert text2.text == '\xA0\xA0\xA0\xA0\u200bis\xA0\u200btext'

    line1, line2 = lines(1000000, 'pre-line')
    box1, = line1.children
    text1, = box1.children
    assert text1.text == 'This'
    box2, = line2.children
    text2, = box2.children
    assert text2.text == 'is text'


@assert_no_logs
def test_linear_gradient():
    red = (1, 0, 0, 1)
    lime = (0, 1, 0, 1)
    blue = (0, 0, 1, 1)

    def layout(gradient_css, type_='linear', init=(),
               positions=[0, 1], colors=[blue, lime], scale=(1, 1)):
        page, = parse('<style>@page { background: ' + gradient_css)
        layer, = page.background.layers
        scale_x, scale_y = scale
        result = layer.image.layout(
            400, 300, lambda dx, dy: (dx * scale_x, dy * scale_y))
        expected = 1, type_, init, positions, colors
        assert almost_equal(result, expected), (result, expected)

    layout('linear-gradient(blue)', 'solid', blue, [], [])
    layout('repeating-linear-gradient(blue)', 'solid', blue, [], [])
    layout('repeating-linear-gradient(blue, lime 1.5px)',
           'solid', (0, .5, .5, 1), [], [])
    layout('linear-gradient(blue, lime)', init=(200, 0, 200, 300))
    layout('repeating-linear-gradient(blue, lime)', init=(200, 0, 200, 300))
    layout('repeating-linear-gradient(blue, lime 20px)',
           init=(200, 0, 200, 20))
    layout('repeating-linear-gradient(blue, lime 20px)',
           'solid', (0, .5, .5, 1), [], [], scale=(1/20, 1/20))

    layout('linear-gradient(to bottom, blue, lime)', init=(200, 0, 200, 300))
    layout('linear-gradient(to top, blue, lime)', init=(200, 300, 200, 0))
    layout('linear-gradient(to right, blue, lime)', init=(0, 150, 400, 150))
    layout('linear-gradient(to left, blue, lime)', init=(400, 150, 0, 150))

    layout('linear-gradient(to top left, blue, lime)',
           init=(344, 342, 56, -42))
    layout('linear-gradient(to top right, blue, lime)',
           init=(56, 342, 344, -42))
    layout('linear-gradient(to bottom left, blue, lime)',
           init=(344, -42, 56, 342))
    layout('linear-gradient(to bottom right, blue, lime)',
           init=(56, -42, 344, 342))

    layout('linear-gradient(270deg, blue, lime)', init=(400, 150, 0, 150))
    layout('linear-gradient(.75turn, blue, lime)', init=(400, 150, 0, 150))
    layout('linear-gradient(45deg, blue, lime)', init=(25, 325, 375, -25))
    layout('linear-gradient(.125turn, blue, lime)', init=(25, 325, 375, -25))
    layout('linear-gradient(.375turn, blue, lime)', init=(25, -25, 375, 325))
    layout('linear-gradient(.625turn, blue, lime)', init=(375, -25, 25, 325))
    layout('linear-gradient(.875turn, blue, lime)', init=(375, 325, 25, -25))

    layout('linear-gradient(blue 2em, lime 20%)', init=(200, 32, 200, 60))
    layout('linear-gradient(blue 100px, red, blue, red 160px, lime)',
           init=(200, 100, 200, 300), colors=[blue, red, blue, red, lime],
           positions=[0, .1, .2, .3, 1])
    layout('linear-gradient(blue -100px, blue 0, red -12px, lime 50%)',
           init=(200, -100, 200, 150), colors=[blue, blue, red, lime],
           positions=[0, .4, .4, 1])
    layout('linear-gradient(blue, blue, red, lime -7px)',
           init=(200, 0, 200, 100), colors=[blue, blue, red, lime],
           positions=[0, 0, 0, 0])
    layout('repeating-linear-gradient(blue, blue, lime, lime -7px)',
           'solid', (0, .5, .5, 1), [], [])


@assert_no_logs
def test_radial_gradient():
    red = (1, 0, 0, 1)
    lime = (0, 1, 0, 1)
    blue = (0, 0, 1, 1)

    def layout(gradient_css, type_='radial', init=(),
               positions=[0, 1], colors=[blue, lime], scale_y=1,
               ctm_scale=(1, 1)):
        if type_ == 'radial':
            center_x, center_y, radius0, radius1 = init
            init = (center_x, center_y / scale_y, radius0,
                    center_x, center_y / scale_y, radius1)
        page, = parse('<style>@page { background: ' + gradient_css)
        layer, = page.background.layers
        ctm_scale_x, ctm_scale_y = ctm_scale
        result = layer.image.layout(
            400, 300, lambda dx, dy: (dx * ctm_scale_x, dy * ctm_scale_y))
        expected = scale_y, type_, init, positions, colors
        assert almost_equal(result, expected), (result, expected)

    layout('radial-gradient(blue)', 'solid', blue, [], [])
    layout('repeating-radial-gradient(blue)', 'solid', blue, [], [])
    layout('radial-gradient(100px, blue, lime)',
           init=(200, 150, 0, 100))

    layout('radial-gradient(100px at right 20px bottom 30px, lime, red)',
           init=(380, 270, 0, 100), colors=[lime, red])
    layout('radial-gradient(0 0, blue, lime)',
           init=(200, 150, 0, 1e-7))
    layout('radial-gradient(1px 0, blue, lime)',
           init=(200, 150, 0, 1e7), scale_y=1e-14)
    layout('radial-gradient(0 1px, blue, lime)',
           init=(200, 150, 0, 1e-7), scale_y=1e14)
    layout('repeating-radial-gradient(20px 40px, blue, lime)',
           init=(200, 150, 0, 20), scale_y=40/20)
    layout('repeating-radial-gradient(20px 40px, blue, lime)',
           init=(200, 150, 0, 20), scale_y=40/20, ctm_scale=(1/9, 1))
    layout('repeating-radial-gradient(20px 40px, blue, lime)',
           init=(200, 150, 0, 20), scale_y=40/20, ctm_scale=(1, 1/19))
    layout('repeating-radial-gradient(20px 40px, blue, lime)',
           'solid', (0, .5, .5, 1), [], [], ctm_scale=(1/11, 1))
    layout('repeating-radial-gradient(20px 40px, blue, lime)',
           'solid', (0, .5, .5, 1), [], [], ctm_scale=(1, 1/21))
    layout('repeating-radial-gradient(42px, blue -20px, lime 10px)',
           init=(200, 150, 10, 40))
    layout('repeating-radial-gradient(42px, blue -140px, lime -110px)',
           init=(200, 150, 10, 40))
    layout('radial-gradient(42px, blue -20px, lime -1px)',
           'solid', lime, [], [])
    layout('radial-gradient(42px, blue -20px, lime 0)',
           'solid', lime, [], [])
    layout('radial-gradient(42px, blue -20px, lime 20px)',
           init=(200, 150, 0, 20), colors=[(0, .5, .5, 1), lime])

    layout('radial-gradient(100px 120px, blue, lime)',
           init=(200, 150, 0, 100), scale_y=120/100)
    layout('radial-gradient(25% 40%, blue, lime)',
           init=(200, 150, 0, 100), scale_y=120/100)

    layout('radial-gradient(circle closest-side, blue, lime)',
           init=(200, 150, 0, 150))
    layout('radial-gradient(circle closest-side at 150px 50px, blue, lime)',
           init=(150, 50, 0, 50))
    layout('radial-gradient(circle closest-side at 45px 50px, blue, lime)',
           init=(45, 50, 0, 45))
    layout('radial-gradient(circle closest-side at 420px 50px, blue, lime)',
           init=(420, 50, 0, 20))
    layout('radial-gradient(circle closest-side at 420px 281px, blue, lime)',
           init=(420, 281, 0, 19))

    layout('radial-gradient(closest-side, blue 20%, lime)',
           init=(200, 150, 40, 200), scale_y=150/200)
    layout('radial-gradient(closest-side at 300px 20%, blue, lime)',
           init=(300, 60, 0, 100), scale_y=60/100)
    layout('radial-gradient(closest-side at 10% 230px, blue, lime)',
           init=(40, 230, 0, 40), scale_y=70/40)

    layout('radial-gradient(circle farthest-side, blue, lime)',
           init=(200, 150, 0, 200))
    layout('radial-gradient(circle farthest-side at 150px 50px, blue, lime)',
           init=(150, 50, 0, 250))
    layout('radial-gradient(circle farthest-side at 45px 50px, blue, lime)',
           init=(45, 50, 0, 355))
    layout('radial-gradient(circle farthest-side at 420px 50px, blue, lime)',
           init=(420, 50, 0, 420))
    layout('radial-gradient(circle farthest-side at 220px 310px, blue, lime)',
           init=(220, 310, 0, 310))

    layout('radial-gradient(farthest-side, blue, lime)',
           init=(200, 150, 0, 200), scale_y=150/200)
    layout('radial-gradient(farthest-side at 300px 20%, blue, lime)',
           init=(300, 60, 0, 300), scale_y=240/300)
    layout('radial-gradient(farthest-side at 10% 230px, blue, lime)',
           init=(40, 230, 0, 360), scale_y=230/360)

    layout('radial-gradient(circle closest-corner, blue, lime)',
           init=(200, 150, 0, 250))
    layout('radial-gradient(circle closest-corner at 340px 80px, blue, lime)',
           init=(340, 80, 0, 100))
    layout('radial-gradient(circle closest-corner at 0 342px, blue, lime)',
           init=(0, 342, 0, 42))

    sqrt2 = math.sqrt(2)
    layout('radial-gradient(closest-corner, blue, lime)',
           init=(200, 150, 0, 200 * sqrt2), scale_y=150/200)
    layout('radial-gradient(closest-corner at 450px 100px, blue, lime)',
           init=(450, 100, 0, 50 * sqrt2), scale_y=100/50)
    layout('radial-gradient(closest-corner at 40px 210px, blue, lime)',
           init=(40, 210, 0, 40 * sqrt2), scale_y=90/40)

    layout('radial-gradient(circle farthest-corner, blue, lime)',
           init=(200, 150, 0, 250))
    layout('radial-gradient(circle farthest-corner'
           ' at 300px -100px, blue, lime)',
           init=(300, -100, 0, 500))
    layout('radial-gradient(circle farthest-corner at 400px 0, blue, lime)',
           init=(400, 0, 0, 500))

    layout('radial-gradient(farthest-corner, blue, lime)',
           init=(200, 150, 0, 200 * sqrt2), scale_y=150/200)
    layout('radial-gradient(farthest-corner at 450px 100px, blue, lime)',
           init=(450, 100, 0, 450 * sqrt2), scale_y=200/450)
    layout('radial-gradient(farthest-corner at 40px 210px, blue, lime)',
           init=(40, 210, 0, 360 * sqrt2), scale_y=210/360)
