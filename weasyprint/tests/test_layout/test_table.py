"""
    weasyprint.tests.layout.table
    -----------------------------

    Tests for layout of tables.

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import pytest

from ..test_boxes import render_pages
from ..test_draw import assert_pixels
from ..testing_utils import assert_no_logs, capture_logs, requires


@assert_no_logs
def test_inline_table():
    page, = render_pages('''
      <table style="display: inline-table; border-spacing: 10px; margin: 5px">
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
def test_implicit_width_table_col_percent():
    # See https://github.com/Kozea/WeasyPrint/issues/169
    page, = render_pages('''
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


@assert_no_logs
def test_implicit_width_table_td_percent():
    page, = render_pages('''
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
def test_layout_table_fixed_1():
    page, = render_pages('''
      <table style="table-layout: fixed; border-spacing: 10px; margin: 5px">
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


@assert_no_logs
def test_layout_table_fixed_2():
    page, = render_pages('''
      <table style="table-layout: fixed; border-spacing: 10px; width: 200px;
                    margin: 5px">
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


@assert_no_logs
def test_layout_table_fixed_3():
    page, = render_pages('''
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


@assert_no_logs
def test_layout_table_fixed_4():
    page, = render_pages('''
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


@assert_no_logs
def test_layout_table_fixed_5():
    # With border-collapse
    page, = render_pages('''
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
def test_layout_table_auto_1():
    page, = render_pages('''
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


@assert_no_logs
def test_layout_table_auto_2():
    page, = render_pages('''
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


@assert_no_logs
def test_layout_table_auto_3():
    page, = render_pages('''
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


@assert_no_logs
def test_layout_table_auto_4():
    page, = render_pages('''
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


@assert_no_logs
def test_layout_table_auto_5():
    page, = render_pages('''
      <style>
        @font-face { src: url(AHEM____.TTF); font-family: ahem }
        * { font-family: ahem }
      </style>
      <table style="width: 1000px; font-family: ahem">
        <tr>
          <td style="width: 40px">aa aa aa aa</td>
          <td style="width: 40px">aaaaaaaaaaa</td>
          <td>This will take the rest of the width</td>
        </tr>
      </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row, = row_group.children
    td_1, td_2, td_3 = row.children

    assert table.width == 1000
    assert td_1.width == 40
    assert td_2.width == 11 * 16
    assert td_3.width == 1000 - 40 - 11 * 16


@assert_no_logs
def test_layout_table_auto_6():
    page, = render_pages('''
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
    assert td_11.width == td_21.width == 4  # minimum width
    assert td_12.position_x == 6  # 1 + 5 + sp
    assert td_12.width == 14  # available width
    assert table.width == 21


@assert_no_logs
def test_layout_table_auto_7():
    page, = render_pages('''
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


@assert_no_logs
def test_layout_table_auto_8():
    page, = render_pages('''
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
    assert td_1.width == 20  # fixed
    assert td_2.position_x == 45  # 15 + 20 + border-spacing
    assert td_2.width == 70  # 120 - 3 * border-spacing - 20
    assert table.width == 120


@assert_no_logs
def test_layout_table_auto_9():
    page, = render_pages('''
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


@assert_no_logs
def test_layout_table_auto_10():
    page, = render_pages('''
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
    assert td_1.width == 6  # 14 - 8
    assert td_2.position_x == 16  # 10 + 6
    assert td_2.width == 8  # maximum of the minimum widths for the column
    assert table.width == 14


@assert_no_logs
def test_layout_table_auto_11():
    page, = render_pages('''
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
    assert td_11.width == 10  # fixed
    assert td_12.width == 28  # 38 - 10
    assert td_21.width == 22  # fixed
    assert td_22.width == 8  # fixed
    assert td_23.width == 8  # fixed
    assert td_31.width == 10  # same as first line
    assert td_32.width == 12  # 22 - 10
    assert td_33.width == 16  # 8 + 8 from second line
    assert table.width == 38


@assert_no_logs
def test_layout_table_auto_12():
    page, = render_pages('''
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
    assert td_11.width == 10  # fixed
    assert td_12.width == 48  # 32 - 10 - sp + 2 * 8 + 2 * sp
    assert td_21.width == 32  # fixed
    assert td_22.width == 8  # fixed
    assert td_23.width == 8  # fixed
    assert td_31.width == 10  # same as first line
    assert td_32.width == 12  # 32 - 10 - sp
    assert td_33.width == 26  # 2 * 8 + sp
    assert table.width == 88


@assert_no_logs
def test_layout_table_auto_13():
    # Regression tests: these used to crash
    page, = render_pages('''
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
    assert td_1.width == 20  # 2 / 3 * 30
    assert td_2.width == 10  # 1 / 3 * 30
    assert table.width == 30


@assert_no_logs
def test_layout_table_auto_14():
    page, = render_pages('''
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
    assert td_1.width == 20
    assert table.width == 20


@assert_no_logs
def test_layout_table_auto_15():
    page, = render_pages('''
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
    assert column_1.width == 0
    assert column_2.width == 0


@assert_no_logs
def test_layout_table_auto_16():
    # Absolute table
    page, = render_pages('''
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
    assert td_1.width == 20  # 2 / 3 * 30
    assert td_2.width == 10  # 1 / 3 * 30
    assert table.width == 30


@assert_no_logs
def test_layout_table_auto_17():
    # With border-collapse
    page, = render_pages('''
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


@assert_no_logs
def test_layout_table_auto_18():
    # Column widths as percentage
    page, = render_pages('''
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


@assert_no_logs
def test_layout_table_auto_19():
    # Column group width
    page, = render_pages('''
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
    assert td_1.width == 100
    assert td_2.width == 100
    assert td_3.width == 100
    assert table.width == 300


@assert_no_logs
def test_layout_table_auto_20():
    # Multiple column width
    page, = render_pages('''
      <table style="width: 200px">
        <colgroup>
          <col style="width: 50px" />
          <col style="width: 30px" />
          <col />
        </colgroup>
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
    assert td_2.width == 30
    assert td_3.width == 120
    assert table.width == 200


@assert_no_logs
def test_layout_table_auto_21():
    # Fixed-width table with column group with widths as percentages and pixels
    page, = render_pages('''
      <table style="width: 500px">
        <colgroup style="width: 100px">
          <col />
          <col />
        </colgroup>
        <colgroup style="width: 30%">
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
    assert td_1.width == 100
    assert td_2.width == 100
    assert td_3.width == 150
    assert td_4.width == 150
    assert table.width == 500


@assert_no_logs
def test_layout_table_auto_22():
    # Auto-width table with column group with widths as percentages and pixels
    page, = render_pages('''
      <table>
        <colgroup style="width: 10%">
          <col />
          <col />
        </colgroup>
        <colgroup style="width: 200px">
          <col />
          <col />
        </colgroup>
        <tbody>
          <tr>
            <td>a a</td>
            <td>a b</td>
            <td>a c</td>
            <td>a d</td>
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
    assert td_3.width == 200
    assert td_4.width == 200
    assert table.width == 500


@assert_no_logs
def test_layout_table_auto_23():
    # Wrong column group width
    page, = render_pages('''
      <table style="width: 200px">
        <colgroup style="width: 20%">
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


@assert_no_logs
def test_layout_table_auto_24():
    # Column width as percentage and cell width in pixels
    page, = render_pages('''
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


@assert_no_logs
def test_layout_table_auto_25():
    # Column width and cell width as percentage
    page, = render_pages('''
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


@assert_no_logs
def test_layout_table_auto_26():
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/307
    # Table with a cell larger than the table's max-width
    page, = render_pages('''
      <table style="max-width: 300px">
        <td style="width: 400px"></td>
      </table>
    ''')


@assert_no_logs
def test_layout_table_auto_27():
    # Table with a cell larger than the table's width
    page, = render_pages('''
      <table style="width: 300px">
        <td style="width: 400px"></td>
      </table>
    ''')


@assert_no_logs
def test_layout_table_auto_28():
    # Table with a cell larger than the table's width and max-width
    page, = render_pages('''
      <table style="width: 300px; max-width: 350px">
        <td style="width: 400px"></td>
      </table>
    ''')


@assert_no_logs
def test_layout_table_auto_29():
    # Table with a cell larger than the table's width and max-width
    page, = render_pages('''
      <table style="width: 300px; max-width: 350px">
        <td style="padding: 50px">
          <div style="width: 300px"></div>
        </td>
      </table>
    ''')


@assert_no_logs
def test_layout_table_auto_30():
    # Table with a cell larger than the table's max-width
    page, = render_pages('''
      <table style="max-width: 300px; margin: 100px">
        <td style="width: 400px"></td>
      </table>
    ''')


@assert_no_logs
def test_layout_table_auto_31():
    # Test a table with column widths < table width < column width + spacing
    page, = render_pages('''
      <table style="width: 300px; border-spacing: 2px">
        <td style="width: 299px"></td>
      </table>
    ''')


@assert_no_logs
def test_layout_table_auto_32():
    # Table with a cell larger than the table's width
    page, = render_pages('''
      <table style="width: 300px; margin: 100px">
        <td style="width: 400px"></td>
      </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    assert table_wrapper.margin_width() == 600  # 400 + 2 * 100


@assert_no_logs
def test_layout_table_auto_33():
    # Div with auto width containing a table with a min-width
    page, = render_pages('''
      <div style="float: left">
        <table style="min-width: 400px; margin: 100px">
          <td></td>
        </table>
      </div>
    ''')
    html, = page.children
    body, = html.children
    div, = body.children
    table_wrapper, = div.children
    assert div.margin_width() == 600  # 400 + 2 * 100
    assert table_wrapper.margin_width() == 600  # 400 + 2 * 100


@assert_no_logs
def test_layout_table_auto_34():
    # Div with auto width containing an empty table with a min-width
    page, = render_pages('''
      <div style="float: left">
        <table style="min-width: 400px; margin: 100px"></table>
      </div>
    ''')
    html, = page.children
    body, = html.children
    div, = body.children
    table_wrapper, = div.children
    assert div.margin_width() == 600  # 400 + 2 * 100
    assert table_wrapper.margin_width() == 600  # 400 + 2 * 100


@assert_no_logs
def test_layout_table_auto_35():
    # Div with auto width containing a table with a cell larger than the
    # table's max-width
    page, = render_pages('''
      <div style="float: left">
        <table style="max-width: 300px; margin: 100px">
          <td style="width: 400px"></td>
        </table>
      </div>
    ''')
    html, = page.children
    body, = html.children
    div, = body.children
    table_wrapper, = div.children
    assert div.margin_width() == 600  # 400 + 2 * 100
    assert table_wrapper.margin_width() == 600  # 400 + 2 * 100


@assert_no_logs
def test_layout_table_auto_36():
    # Test regression on a crash: https://github.com/Kozea/WeasyPrint/pull/152
    page, = render_pages('''
      <table>
        <td style="width: 50%">
      </table>
    ''')


@assert_no_logs
def test_layout_table_auto_37():
    # Other crashes: https://github.com/Kozea/WeasyPrint/issues/305
    page, = render_pages('''
      <table>
        <tr>
          <td>
            <table>
              <tr>
                <th>Test</th>
              </tr>
              <tr>
                <td style="min-width: 100%;"></td>
                <td style="width: 48px;"></td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    ''')


@assert_no_logs
def test_layout_table_auto_38():
    page, = render_pages('''
      <table>
        <tr>
          <td>
            <table>
              <tr>
                <td style="width: 100%;"></td>
                <td style="width: 48px;">
                  <img src="icon.png">
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    ''')


@assert_no_logs
def test_layout_table_auto_39():
    page, = render_pages('''
      <table>
        <tr>
          <td>
            <table style="display: inline-table">
              <tr>
                <td style="width: 100%;"></td>
                <td></td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    ''')


@assert_no_logs
def test_layout_table_auto_40():
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/368
    # Check that white-space is used for the shrink-to-fit algorithm
    page, = render_pages('''
      <style>@font-face { src: url(AHEM____.TTF); font-family: ahem }</style>
      <table style="width: 0">
        <td style="font-family: ahem; white-space: nowrap">a a</td>
      </table>
    ''')
    html, = page.children
    body, = html.children
    div, = body.children
    table_wrapper, = div.children
    table, = table_wrapper.children
    assert table.width == 16 * 3


@assert_no_logs
def test_layout_table_auto_41():
    # Cell width as percentage in auto-width table
    page, = render_pages('''
      <div style="width: 100px">
        <table>
          <tbody>
            <tr>
              <td>a a a a a a a a</td>
              <td style="width: 30%">a a a a a a a a</td>
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
    assert td_1.width == 70
    assert td_2.width == 30
    assert table.width == 100


@assert_no_logs
def test_layout_table_auto_42():
    # Cell width as percentage in auto-width table
    page, = render_pages('''
      <table>
        <tbody>
            <tr>
              <td style="width: 70px">a a a a a a a a</td>
              <td style="width: 30%">a a a a a a a a</td>
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
    assert td_1.width == 70
    assert td_2.width == 30
    assert table.width == 100


@assert_no_logs
def test_layout_table_auto_43():
    # Cell width as percentage on colspan cell in auto-width table
    page, = render_pages('''
      <div style="width: 100px">
        <table>
          <tbody>
            <tr>
              <td>a a a a a a a a</td>
              <td style="width: 30%" colspan=2>a a a a a a a a</td>
              <td>a a a a a a a a</td>
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
    td_1, td_2, td_3 = row.children
    assert td_1.width == 35
    assert td_2.width == 30
    assert td_3.width == 35
    assert table.width == 100


@assert_no_logs
def test_layout_table_auto_44():
    # Cells widths as percentages on normal and colspan cells
    page, = render_pages('''
      <div style="width: 100px">
        <table>
          <tbody>
            <tr>
              <td>a a a a a a a a</td>
              <td style="width: 30%" colspan=2>a a a a a a a a</td>
              <td>a a a a a a a a</td>
              <td style="width: 40%">a a a a a a a a</td>
              <td>a a a a a a a a</td>
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
    td_1, td_2, td_3, td_4, td_5 = row.children
    assert td_1.width == 10
    assert td_2.width == 30
    assert td_3.width == 10
    assert td_4.width == 40
    assert td_5.width == 10
    assert table.width == 100


@assert_no_logs
def test_layout_table_auto_45():
    # Cells widths as percentage on multiple lines
    page, = render_pages('''
      <div style="width: 1000px">
        <table>
          <tbody>
            <tr>
              <td>a a a a a a a a</td>
              <td style="width: 30%">a a a a a a a a</td>
              <td>a a a a a a a a</td>
              <td style="width: 40%">a a a a a a a a</td>
              <td>a a a a a a a a</td>
            </tr>
            <tr>
              <td style="width: 31%" colspan=2>a a a a a a a a</td>
              <td>a a a a a a a a</td>
              <td style="width: 42%" colspan=2>a a a a a a a a</td>
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
    row_1, row_2 = row_group.children
    td_11, td_12, td_13, td_14, td_15 = row_1.children
    td_21, td_22, td_23 = row_2.children
    assert td_11.width == 10  # 31% - 30%
    assert td_12.width == 300  # 30%
    assert td_13.width == 270  # 1000 - 31% - 42%
    assert td_14.width == 400  # 40%
    assert td_15.width == 20  # 42% - 2%
    assert td_21.width == 310  # 31%
    assert td_22.width == 270  # 1000 - 31% - 42%
    assert td_23.width == 420  # 42%
    assert table.width == 1000


@assert_no_logs
def test_layout_table_auto_46():
    # Test regression:
    # http://test.weasyprint.org/suite-css21/chapter8/section2/test56/
    page, = render_pages('''
      <div style="position: absolute">
        <table style="margin: 50px; border: 20px solid black">
          <tr>
            <td style="width: 200px; height: 200px"></td>
          </tr>
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
    td, = row.children
    assert td.width == 200
    assert table.width == 200
    assert div.width == 340  # 200 + 2 * 50 + 2 * 20


@assert_no_logs
def test_layout_table_auto_47():
    # Test regression:
    # https://github.com/Kozea/WeasyPrint/issues/666
    page, = render_pages('''
      <style>@font-face { src: url(AHEM____.TTF); font-family: ahem }</style>
      <table style="font-family: ahem">
        <tr>
          <td colspan=5>aaa</td>
        </tr>
      </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row, = row_group.children
    td, = row.children
    assert td.width == 48  # 3 * font-size


@assert_no_logs
def test_layout_table_auto_48():
    # Related to:
    # https://github.com/Kozea/WeasyPrint/issues/685
    page, = render_pages('''
      <style>@font-face { src: url(AHEM____.TTF); font-family: ahem }</style>
      <table style="font-family: ahem; border-spacing: 100px;
                    border-collapse: collapse">
        <tr>
          <td colspan=5>aaa</td>
        </tr>
      </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row, = row_group.children
    td, = row.children
    assert td.width == 48  # 3 * font-size


@pytest.mark.xfail
@assert_no_logs
def test_layout_table_auto_49():
    # Related to:
    # https://github.com/Kozea/WeasyPrint/issues/685
    # See TODO in table_layout.group_layout
    page, = render_pages('''
      <style>@font-face { src: url(AHEM____.TTF); font-family: ahem }</style>
      <table style="font-family: ahem; border-spacing: 100px">
        <tr>
          <td colspan=5>aaa</td>
        </tr>
      </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row, = row_group.children
    td, = row.children
    assert td.width == 48  # 3 * font-size


@assert_no_logs
def test_layout_table_auto_50():
    # Test regression:
    # https://github.com/Kozea/WeasyPrint/issues/685
    page, = render_pages('''
      <style>@font-face { src: url(AHEM____.TTF); font-family: ahem }</style>
      <table style="font-family: ahem; border-spacing: 5px">
       <tr><td>a</td><td>a</td><td>a</td><td>a</td><td>a</td></tr>
       <tr>
         <td colspan='5'>aaa aaa aaa aaa</td>
       </tr>
      </table>
    ''')
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    row_1, row_2 = row_group.children
    for td in row_1.children:
        assert td.width == 44  # (15 * font_size - 4 * sp) / 5
    td_21, = row_2.children
    assert td_21.width == 240  # 15 * font_size


@assert_no_logs
def test_table_column_width_1():
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
        page, = render_pages(source)
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


@assert_no_logs
def test_table_column_width_2():
    page, = render_pages('''
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


@assert_no_logs
def test_table_column_width_3():
    # Sum of columns width larger that the table width:
    # increase the table width
    page, = render_pages('''
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
def test_table_row_height_1():
    page, = render_pages('''
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


@assert_no_logs
def test_table_row_height_2():
    # A cell box cannot extend beyond the last row box of a table.
    page, = render_pages('''
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
def test_table_row_height_3():
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/
    page, = render_pages('''
      <style>
        @font-face { src: url(AHEM____.TTF); font-family: ahem }
      </style>
      <table style="border-spacing: 0; font-family: ahem; line-height: 20px">
        <tr><td>Table</td><td rowspan="2"></td></tr>
        <tr></tr>
      </table>
    ''')
    html, = page.children
    body, = html.children
    wrapper, = body.children
    table, = wrapper.children
    assert table.height == 20
    row_group, = table.children
    assert row_group.height == 20
    row1, row2 = row_group.children
    assert row1.height == 20
    assert row2.height == 0


@assert_no_logs
@requires('cairo', (1, 12, 0))
def test_table_vertical_align():
    assert_pixels('table_vertical_align', 28, 10, '''
        rrrrrrrrrrrrrrrrrrrrrrrrrrrr
        rBBBBBBBBBBBBBBBBBBBBBBBBBBr
        rBrBB_BB_BB_BB_BBrrBBrrBB_Br
        rBrBB_BB_BBrBBrBBrrBBrrBBrBr
        rB_BBrBB_BBrBBrBBrrBBrrBBrBr
        rB_BBrBB_BB_BB_BBrrBBrrBB_Br
        rB_BB_BBrBB_BB_BB__BB__BB_Br
        rB_BB_BBrBB_BB_BB__BB__BB_Br
        rBBBBBBBBBBBBBBBBBBBBBBBBBBr
        rrrrrrrrrrrrrrrrrrrrrrrrrrrr
    ''', '''
      <style>
        @font-face { src: url(AHEM____.TTF); font-family: ahem }
        @page { size: 28px 10px }
        html { background: #fff; font-size: 1px; color: red }
        body { margin: 0; width: 28px; height: 10px }
        td {
          width: 1em;
          padding: 0 !important;
          border: 1px solid blue;
          line-height: 1em;
          font-family: ahem;
        }
      </style>
      <table style="border: 1px solid red; border-spacing: 0">
        <tr>
          <!-- Test vertical-align: top, auto height -->
          <td style="vertical-align: top">o o</td>

          <!-- Test vertical-align: middle, auto height -->
          <td style="vertical-align: middle">o o</td>

          <!-- Test vertical-align: bottom, fixed useless height -->
          <td style="vertical-align: bottom; height: 2em">o o</td>

          <!-- Test default vertical-align value (baseline),
               fixed useless height -->
          <td style="height: 5em">o o</td>

          <!-- Test vertical-align: baseline with baseline set by next cell,
               auto height -->
          <td style="vertical-align: baseline">o o</td>

          <!-- Set baseline height to 2px, auto height -->
          <td style="vertical-align: baseline; font-size: 2em">o o</td>

          <!-- Test padding-bottom, fixed useless height,
               set the height of the cells to 2 lines * 2em + 2px = 6px -->
          <td style="vertical-align: baseline; height: 1em;
                     font-size: 2em; padding-bottom: 2px !important">
            o o
          </td>

          <!-- Test padding-top, auto height -->
          <td style="vertical-align: top; padding-top: 1em !important">
            o o
          </td>
        </tr>
      </table>
    ''')  # noqa


@assert_no_logs
def test_table_wrapper():
    page, = render_pages('''
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


@assert_no_logs
def test_table_html_tag():
    # Non-regression test: this used to cause an exception
    page, = render_pages('<html style="display: table">')


@assert_no_logs
@pytest.mark.parametrize('html, rows, positions', (
    ('''
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
     ''',
     [2, 3, 1, 2],
     [30, 70, 0, 40, 80, 0, 0, 40]),
    ('''
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
     ''',
     [0, 3, 1],
     [0, 40, 80, 0]),
    ('''
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
     ''',
     [0, 3, 1],
     [0, 40, 80, 0]),
    ('''
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
     ''',
     [1, 2],
     [30, 0, 40]),
))
def test_table_page_breaks(html, rows, positions):
    pages = render_pages(html)
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
        rows_per_page.append(rows_in_this_page)

    assert rows_per_page == rows
    assert rows_position_y == positions


@assert_no_logs
def test_table_page_breaks_complex():
    pages = render_pages('''
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
def test_table_page_break_after():
    page1, page2, page3, page4, page5, page6 = render_pages('''
      <style>
        @page { size: 1000px }
        h1 { height: 30px}
        td { height: 40px }
        table { table-layout: fixed; width: 100% }
      </style>
      <h1>Dummy title</h1>
      <table>

        <tbody>
          <tr><td>row 1</td></tr>
          <tr><td>row 2</td></tr>
          <tr><td>row 3</td></tr>
        </tbody>
        <tbody>
          <tr style="break-after: page"><td>row 1</td></tr>
          <tr><td>row 2</td></tr>
          <tr><td>row 3</td></tr>
        </tbody>
        <tbody>
          <tr><td>row 1</td></tr>
          <tr><td>row 2</td></tr>
          <tr style="break-after: page"><td>row 3</td></tr>
        </tbody>
        <tbody style="break-after: right">
          <tr><td>row 1</td></tr>
          <tr><td>row 2</td></tr>
          <tr><td>row 3</td></tr>
        </tbody>
        <tbody style="break-after: page">
          <tr><td>row 1</td></tr>
          <tr><td>row 2</td></tr>
          <tr><td>row 3</td></tr>
        </tbody>

      </table>
      <p>bla bla</p>
     ''')
    html, = page1.children
    body, = html.children
    h1, table_wrapper = body.children
    table, = table_wrapper.children
    table_group1, table_group2 = table.children
    assert len(table_group1.children) == 3
    assert len(table_group2.children) == 1

    html, = page2.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    table_group1, table_group2 = table.children
    assert len(table_group1.children) == 2
    assert len(table_group2.children) == 3

    html, = page3.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    table_group, = table.children
    assert len(table_group.children) == 3

    html, = page4.children
    assert not html.children

    html, = page5.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    table_group, = table.children
    assert len(table_group.children) == 3

    html, = page6.children
    body, = html.children
    p, = body.children
    assert p.element_tag == 'p'


@assert_no_logs
def test_table_page_break_before():
    page1, page2, page3, page4, page5, page6 = render_pages('''
      <style>
        @page { size: 1000px }
        h1 { height: 30px}
        td { height: 40px }
        table { table-layout: fixed; width: 100% }
      </style>
      <h1>Dummy title</h1>
      <table>

        <tbody>
          <tr style="break-before: page"><td>row 1</td></tr>
          <tr><td>row 2</td></tr>
          <tr><td>row 3</td></tr>
        </tbody>
        <tbody>
          <tr><td>row 1</td></tr>
          <tr style="break-before: page"><td>row 2</td></tr>
          <tr><td>row 3</td></tr>
        </tbody>
        <tbody>
          <tr style="break-before: page"><td>row 1</td></tr>
          <tr><td>row 2</td></tr>
          <tr><td>row 3</td></tr>
        </tbody>
        <tbody>
          <tr><td>row 1</td></tr>
          <tr><td>row 2</td></tr>
          <tr><td>row 3</td></tr>
        </tbody>
        <tbody style="break-before: left">
          <tr><td>row 1</td></tr>
          <tr><td>row 2</td></tr>
          <tr><td>row 3</td></tr>
        </tbody>

      </table>
      <p>bla bla</p>
     ''')
    html, = page1.children
    body, = html.children
    h1, = body.children
    assert h1.element_tag == 'h1'

    html, = page2.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    table_group1, table_group2 = table.children
    assert len(table_group1.children) == 3
    assert len(table_group2.children) == 1

    html, = page3.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    table_group, = table.children
    assert len(table_group.children) == 2

    html, = page4.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    table_group1, table_group2 = table.children
    assert len(table_group1.children) == 3
    assert len(table_group2.children) == 3

    html, = page5.children
    assert not html.children

    html, = page6.children
    body, = html.children
    table_wrapper, p = body.children
    table, = table_wrapper.children
    table_group, = table.children
    assert len(table_group.children) == 3
    assert p.element_tag == 'p'


@assert_no_logs
@pytest.mark.parametrize('html, rows', (
    ('''
      <style>
        @page { size: 100px }
        table { table-layout: fixed; width: 100% }
        tr { height: 26px }
      </style>
      <table>
        <tbody>
          <tr><td>row 0</td></tr>
          <tr><td>row 1</td></tr>
          <tr style="break-before: avoid"><td>row 2</td></tr>
          <tr style="break-before: avoid"><td>row 3</td></tr>
        </tbody>
      </table>
    ''',
     [1, 3]),
    ('''
      <style>
        @page { size: 100px }
        table { table-layout: fixed; width: 100% }
        tr { height: 26px }
      </style>
      <table>
        <tbody>
          <tr><td>row 0</td></tr>
          <tr style="break-after: avoid"><td>row 1</td></tr>
          <tr><td>row 2</td></tr>
          <tr style="break-before: avoid"><td>row 3</td></tr>
        </tbody>
      </table>
     ''',
     [1, 3]),
    ('''
      <style>
        @page { size: 100px }
        table { table-layout: fixed; width: 100% }
        tr { height: 26px }
      </style>
      <table>
        <tbody>
          <tr><td>row 0</td></tr>
          <tr><td>row 1</td></tr>
          <tr style="break-after: avoid"><td>row 2</td></tr>
          <tr><td>row 3</td></tr>
        </tbody>
      </table>
     ''',
     [2, 2]),
    ('''
      <style>
        @page { size: 100px }
        table { table-layout: fixed; width: 100% }
        tr { height: 26px }
      </style>
      <table>
        <tbody>
          <tr style="break-before: avoid"><td>row 0</td></tr>
          <tr style="break-before: avoid"><td>row 1</td></tr>
          <tr style="break-before: avoid"><td>row 2</td></tr>
          <tr style="break-before: avoid"><td>row 3</td></tr>
        </tbody>
      </table>
     ''',
     [3, 1]),
    ('''
      <style>
        @page { size: 100px }
        table { table-layout: fixed; width: 100% }
        tr { height: 26px }
      </style>
      <table>
        <tbody>
          <tr style="break-after: avoid"><td>row 0</td></tr>
          <tr style="break-after: avoid"><td>row 1</td></tr>
          <tr style="break-after: avoid"><td>row 2</td></tr>
          <tr style="break-after: avoid"><td>row 3</td></tr>
        </tbody>
      </table>
     ''',
     [3, 1]),
    ('''
      <style>
        @page { size: 100px }
        table { table-layout: fixed; width: 100% }
        tr { height: 26px }
        p { height: 26px }
      </style>
      <p>wow p</p>
      <table>
        <tbody>
          <tr style="break-after: avoid"><td>row 0</td></tr>
          <tr style="break-after: avoid"><td>row 1</td></tr>
          <tr style="break-after: avoid"><td>row 2</td></tr>
          <tr style="break-after: avoid"><td>row 3</td></tr>
        </tbody>
      </table>
     ''',
     [1, 3, 1]),
    ('''
      <style>
        @page { size: 100px }
        table { table-layout: fixed; width: 100% }
        tr { height: 30px }
      </style>
      <table>
        <tbody style="break-after: avoid">
          <tr><td>row 0</td></tr>
          <tr><td>row 1</td></tr>
          <tr><td>row 2</td></tr>
        </tbody>
        <tbody>
          <tr><td>row 0</td></tr>
          <tr><td>row 1</td></tr>
          <tr><td>row 2</td></tr>
        </tbody>
      </table>
     ''',
     [2, 3, 1]),
    ('''
      <style>
        @page { size: 100px }
        table { table-layout: fixed; width: 100% }
        tr { height: 30px }
      </style>
      <table>
        <tbody>
          <tr><td>row 0</td></tr>
          <tr><td>row 1</td></tr>
          <tr><td>row 2</td></tr>
        </tbody>
        <tbody style="break-before: avoid">
          <tr><td>row 0</td></tr>
          <tr><td>row 1</td></tr>
          <tr><td>row 2</td></tr>
        </tbody>
      </table>
     ''',
     [2, 3, 1]),
    ('''
      <style>
        @page { size: 100px }
        table { table-layout: fixed; width: 100% }
        tr { height: 30px }
      </style>
      <table>
        <tbody>
          <tr><td>row 0</td></tr>
          <tr><td>row 1</td></tr>
          <tr><td>row 2</td></tr>
        </tbody>
        <tbody>
          <tr style="break-before: avoid"><td>row 0</td></tr>
          <tr><td>row 1</td></tr>
          <tr><td>row 2</td></tr>
        </tbody>
      </table>
     ''',
     [2, 3, 1]),
    ('''
      <style>
        @page { size: 100px }
        table { table-layout: fixed; width: 100% }
        tr { height: 30px }
      </style>
      <table>
        <tbody>
          <tr><td>row 0</td></tr>
          <tr><td>row 1</td></tr>
          <tr style="break-after: avoid"><td>row 2</td></tr>
        </tbody>
        <tbody>
          <tr><td>row 0</td></tr>
          <tr><td>row 1</td></tr>
          <tr><td>row 2</td></tr>
        </tbody>
      </table>
     ''',
     [2, 3, 1]),
    ('''
      <style>
        @page { size: 100px }
        table { table-layout: fixed; width: 100% }
        tr { height: 30px }
      </style>
      <table>
        <tbody style="break-after: avoid">
          <tr><td>row 0</td></tr>
          <tr><td>row 1</td></tr>
          <tr style="break-after: page"><td>row 2</td></tr>
        </tbody>
        <tbody>
          <tr><td>row 0</td></tr>
          <tr><td>row 1</td></tr>
          <tr><td>row 2</td></tr>
        </tbody>
      </table>
     ''',
     [3, 3]),
))
def test_table_page_break_avoid(html, rows):
    pages = render_pages(html)
    assert len(pages) == len(rows)
    rows_per_page = []
    for page in pages:
        html, = page.children
        body, = html.children
        if body.children[0].element_tag == 'p':
            rows_per_page.append(len(body.children))
            continue
        else:
            table_wrapper, = body.children
        table, = table_wrapper.children
        rows_in_this_page = 0
        for group in table.children:
            for row in group.children:
                rows_in_this_page += 1
        rows_per_page.append(rows_in_this_page)

    assert rows_per_page == rows


@assert_no_logs
@pytest.mark.parametrize('vertical_align, table_position_y', (
    ('top', 8),
    ('bottom', 8),
    ('baseline', 10),
))
def test_inline_table_baseline(vertical_align, table_position_y):
    # Check that inline table's baseline is its first row's baseline.
    #
    # Div text's baseline is at 18px from the top (10px because of the
    # line-height, 8px as it's Ahem's baseline position).
    #
    # When a row has vertical-align: baseline cells, its baseline is its cell's
    # baseline. The position of the table is thus 10px above the text's
    # baseline.
    #
    # When a row has another value for vertical-align, the baseline is the
    # bottom of the row. The first cell's text is aligned with the div's text,
    # and the top of the table is thus 8px above the baseline.
    page, = render_pages('''
      <style>@font-face { src: url(AHEM____.TTF); font-family: ahem }</style>
      <div style="font-family: ahem; font-size: 10px; line-height: 30px">
        abc
        <table style="display: inline-table; border-collapse: collapse;
                      line-height: 10px">
          <tr><td style="vertical-align: %s">a</td></tr>
          <tr><td>a</td></tr>
        </table>
        abc
      </div>
    ''' % vertical_align)
    html, = page.children
    body, = html.children
    div, = body.children
    line, = div.children
    text1, table_wrapper, text2 = line.children
    table, = table_wrapper.children
    assert text1.position_y == text2.position_y == 0
    assert table.height == 10 * 2
    assert table.position_y == table_position_y


@assert_no_logs
def test_table_caption_margin_top():
    page, = render_pages('''
      <style>
        table { margin: 20px; }
        caption, h1, h2 { margin: 20px; height: 10px }
        td { height: 10px }
      </style>
      <h1></h1>
      <table>
        <caption></caption>
        <tr>
          <td></td>
        </tr>
      </table>
      <h2></h2>
    ''')
    html, = page.children
    body, = html.children
    h1, wrapper, h2 = body.children
    caption, table = wrapper.children
    tbody, = table.children
    assert (h1.content_box_x(), h1.content_box_y()) == (20, 20)
    assert (wrapper.content_box_x(), wrapper.content_box_y()) == (20, 50)
    assert (caption.content_box_x(), caption.content_box_y()) == (40, 70)
    assert (tbody.content_box_x(), tbody.content_box_y()) == (20, 100)
    assert (h2.content_box_x(), h2.content_box_y()) == (20, 130)


@assert_no_logs
def test_table_caption_margin_bottom():
    page, = render_pages('''
      <style>
        table { margin: 20px; }
        caption, h1, h2 { margin: 20px; height: 10px; caption-side: bottom }
        td { height: 10px }
      </style>
      <h1></h1>
      <table>
        <caption></caption>
        <tr>
          <td></td>
        </tr>
      </table>
      <h2></h2>
    ''')
    html, = page.children
    body, = html.children
    h1, wrapper, h2 = body.children
    table, caption = wrapper.children
    tbody, = table.children
    assert (h1.content_box_x(), h1.content_box_y()) == (20, 20)
    assert (wrapper.content_box_x(), wrapper.content_box_y()) == (20, 50)
    assert (tbody.content_box_x(), tbody.content_box_y()) == (20, 50)
    assert (caption.content_box_x(), caption.content_box_y()) == (40, 80)
    assert (h2.content_box_x(), h2.content_box_y()) == (20, 130)
