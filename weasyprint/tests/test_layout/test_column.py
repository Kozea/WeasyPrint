"""
    weasyprint.tests.layout.column
    ------------------------------

    Tests for multicolumn layout.

"""

import pytest

from ..test_boxes import render_pages
from ..testing_utils import assert_no_logs


@assert_no_logs
@pytest.mark.parametrize('css', (
    'columns: 4',
    'columns: 100px',
    'columns: 4 100px',
    'columns: 100px 4',
    'column-width: 100px',
    'column-count: 4',
))
def test_columns(css):
    page, = render_pages('''
      <style>
        @font-face { src: url(AHEM____.TTF); font-family: ahem }
        div { %s; column-gap: 0 }
        body { margin: 0; font-family: "ahem" }
        @page { margin: 0; size: 400px 1000px }
      </style>
      <div>
        Ipsum dolor sit amet,
        consectetur adipiscing elit.
        Sed sollicitudin nibh
        et turpis molestie tristique.
      </div>
    ''' % css)
    html, = page.children
    body, = html.children
    div, = body.children
    columns = div.children
    assert len(columns) == 4
    assert [column.width for column in columns] == [100, 100, 100, 100]
    assert [column.position_x for column in columns] == [0, 100, 200, 300]
    assert [column.position_y for column in columns] == [0, 0, 0, 0]


@pytest.mark.parametrize('value, width', (
    ('normal', 16),  # "normal" is 1em = 16px
    ('unknown', 16),  # default value is normal
    ('15px', 15),
    ('40%', 16),  # percentages are not allowed
    ('-1em', 16),  # negative values are not allowed
))
def test_column_gap(value, width):
    page, = render_pages('''
      <style>
        @font-face { src: url(AHEM____.TTF); font-family: ahem }
        div { columns: 3; column-gap: %s }
        body { margin: 0; font-family: "ahem" }
        @page { margin: 0; size: 300px 1000px }
      </style>
      <div>
        Ipsum dolor sit amet,
        consectetur adipiscing elit.
        Sed sollicitudin nibh
        et turpis molestie tristique.
      </div>
    ''' % value)
    html, = page.children
    body, = html.children
    div, = body.children
    columns = div.children
    assert len(columns) == 3
    assert [column.width for column in columns] == (
        3 * [100 - 2 * width / 3])
    assert [column.position_x for column in columns] == (
        [0, 100 + width / 3, 200 + 2 * width / 3])
    assert [column.position_y for column in columns] == [0, 0, 0]


@assert_no_logs
def test_column_span():
    page, = render_pages('''
      <style>
        @font-face { src: url(AHEM____.TTF); font-family: ahem }
        body { margin: 0; font-family: "ahem"; line-height: 1 }
        div { columns: 2; width: 10em; column-gap: 0 }
        section { column-span: all; margin: 1em 0 }
      </style>

      <div>
        abc def
        <section>test</section>
        <section>test</section>
        ghi jkl
      </div>
    ''')
    html, = page.children
    body, = html.children
    div, = body.children
    column1, column2, section1, section2, column3, column4 = div.children
    assert (column1.position_x, column1.position_y) == (0, 0)
    assert (column2.position_x, column2.position_y) == (5 * 16, 0)
    assert (section1.content_box_x(), section1.content_box_y()) == (0, 32)
    assert (section2.content_box_x(), section2.content_box_y()) == (0, 64)
    assert (column3.position_x, column3.position_y) == (0, 96)
    assert (column4.position_x, column4.position_y) == (5 * 16, 96)

    assert column1.height == 16


@assert_no_logs
def test_columns_multipage():
    page1, page2 = render_pages('''
      <style>
        @font-face { src: url(AHEM____.TTF); font-family: ahem }
        div { columns: 2; column-gap: 1px }
        body { margin: 0; font-family: "ahem";
               font-size: 1px; line-height: 1px }
        @page { margin: 0; size: 3px 2px }
      </style>
      <div>a b c d e f g</div>
    ''')
    html, = page1.children
    body, = html.children
    div, = body.children
    columns = div.children
    assert len(columns) == 2
    assert len(columns[0].children) == 2
    assert len(columns[1].children) == 2
    columns[0].children[0].children[0].text == 'a'
    columns[0].children[1].children[0].text == 'b'
    columns[1].children[0].children[0].text == 'c'
    columns[1].children[1].children[0].text == 'd'

    html, = page2.children
    body, = html.children
    div, = body.children
    columns = div.children
    assert len(columns) == 2
    assert len(columns[0].children) == 2
    assert len(columns[1].children) == 1
    columns[0].children[0].children[0].text == 'e'
    columns[0].children[1].children[0].text == 'f'
    columns[1].children[0].children[0].text == 'g'


@assert_no_logs
def test_columns_not_enough_content():
    page, = render_pages('''
      <style>
        @font-face { src: url(AHEM____.TTF); font-family: ahem }
        div { columns: 5; column-gap: 0 }
        body { margin: 0; font-family: "ahem" }
        @page { margin: 0; size: 5px; font-size: 1px }
      </style>
      <div>a b c</div>
    ''')
    html, = page.children
    body, = html.children
    div, = body.children
    assert div.width == 5
    columns = div.children
    assert len(columns) == 3
    assert [column.width for column in columns] == [1, 1, 1]
    assert [column.position_x for column in columns] == [0, 1, 2]
    assert [column.position_y for column in columns] == [0, 0, 0]


@assert_no_logs
def test_columns_empty():
    page, = render_pages('''
      <style>
        @font-face { src: url(AHEM____.TTF); font-family: ahem }
        div { columns: 3 }
        body { margin: 0; font-family: "ahem" }
        @page { margin: 0; size: 3px; font-size: 1px }
      </style>
      <div></div>
    ''')
    html, = page.children
    body, = html.children
    div, = body.children
    assert div.width == 3
    assert div.height == 0
    columns = div.children
    assert len(columns) == 0


@assert_no_logs
@pytest.mark.parametrize('prop', ('height', 'min-height'))
def test_columns_fixed_height(prop):
    # TODO: we should test when the height is too small
    page, = render_pages('''
      <style>
        @font-face { src: url(AHEM____.TTF); font-family: ahem }
        div { columns: 4; column-gap: 0; %s: 10px }
        body { margin: 0; font-family: "ahem"; line-height: 1px }
        @page { margin: 0; size: 4px 50px; font-size: 1px }
      </style>
      <div>a b c</div>
    ''' % prop)
    html, = page.children
    body, = html.children
    div, = body.children
    assert div.width == 4
    columns = div.children
    assert len(columns) == 3
    assert [column.width for column in columns] == [1, 1, 1]
    assert [column.height for column in columns] == [10, 10, 10]
    assert [column.position_x for column in columns] == [0, 1, 2]
    assert [column.position_y for column in columns] == [0, 0, 0]


@assert_no_logs
def test_columns_relative():
    page, = render_pages('''
      <style>
        @font-face { src: url(AHEM____.TTF); font-family: ahem }
        article { position: absolute; top: 3px }
        div { columns: 4; column-gap: 0; position: relative;
              top: 1px; left: 2px }
        body { margin: 0; font-family: "ahem"; line-height: 1px }
        @page { margin: 0; size: 4px 50px; font-size: 1px }
      </style>
      <div>a b c d<article>e</article></div>
    ''')
    html, = page.children
    body, = html.children
    div, = body.children
    assert div.width == 4
    columns = div.children
    assert [column.width for column in columns] == [1, 1, 1, 1]
    assert [column.position_x for column in columns] == [2, 3, 4, 5]
    assert [column.position_y for column in columns] == [1, 1, 1, 1]
    column4 = columns[-1]
    column_line, = column4.children
    _, absolute_article = column_line.children
    absolute_line, = absolute_article.children
    span, = absolute_line.children
    assert span.position_x == 5  # Default position of the 4th column
    assert span.position_y == 4  # div's 1px + span's 3px


@assert_no_logs
def test_columns_regression_1():
    # Regression test #1 for https://github.com/Kozea/WeasyPrint/issues/659
    page1, page2, page3 = render_pages('''
      <style>
        @page {margin: 0; width: 100px; height: 100px}
        body {margin: 0; font-size: 1px}
      </style>
      <div style="height:95px">A</div>
      <div style="column-count:2">
        <div style="height:20px">B1</div>
        <div style="height:20px">B2</div>
        <div style="height:20px">B3</div>
      </div>
      <div style="height:95px">C</div>
    ''')

    html, = page1.children
    body, = html.children
    div, = body.children
    assert div.position_y == 0
    assert div.children[0].children[0].text == 'A'

    html, = page2.children
    body, = html.children
    div, = body.children
    assert div.position_y == 0
    column1, column2 = div.children
    assert column1.position_y == column2.position_y == 0
    div1, div2 = column1.children
    div3, = column2.children
    assert div1.position_y == div3.position_y == 0
    assert div2.position_y == 20
    assert div1.children[0].children[0].text == 'B1'
    assert div2.children[0].children[0].text == 'B2'
    assert div3.children[0].children[0].text == 'B3'

    html, = page3.children
    body, = html.children
    div, = body.children
    assert div.position_y == 0
    assert div.children[0].children[0].text == 'C'


@assert_no_logs
def test_columns_regression_2():
    # Regression test #2 for https://github.com/Kozea/WeasyPrint/issues/659
    page1, page2 = render_pages('''
      <style>
        @page {margin: 0; width: 100px; height: 100px}
        body {margin: 0; font-size: 1px}
      </style>
      <div style="column-count:2">
        <div style="height:20px">B1</div>
        <div style="height:60px">B2</div>
        <div style="height:60px">B3</div>
        <div style="height:60px">B4</div>
      </div>
    ''')

    html, = page1.children
    body, = html.children
    div, = body.children
    assert div.position_y == 0
    column1, column2 = div.children
    assert column1.position_y == column2.position_y == 0
    div1, div2 = column1.children
    div3, = column2.children
    assert div1.position_y == div3.position_y == 0
    assert div2.position_y == 20
    assert div1.children[0].children[0].text == 'B1'
    assert div2.children[0].children[0].text == 'B2'
    assert div3.children[0].children[0].text == 'B3'

    html, = page2.children
    body, = html.children
    div, = body.children
    assert div.position_y == 0
    column1, = div.children
    assert column1.position_y == 0
    div1, = column1.children
    assert div1.position_y == div3.position_y == 0
    assert div1.children[0].children[0].text == 'B4'


@assert_no_logs
def test_columns_regression_3():
    # Regression test #3 for https://github.com/Kozea/WeasyPrint/issues/659
    page, = render_pages('''
      <style>
        @page {margin: 0; width: 100px; height: 100px}
        body {margin: 0; font-size: 10px}
      </style>
      <div style="column-count:2">
        <div style="height:20px; margin:5px">B1</div>
        <div style="height:60px">B2</div>
        <div style="height:60px">B3</div>
      </div>
    ''')
    html, = page.children
    body, = html.children
    div, = body.children
    assert div.position_y == 0
    column1, column2 = div.children
    assert column1.position_y == column2.position_y == 0
    div1, div2 = column1.children
    div3, = column2.children
    assert div1.position_y == div3.position_y == 0
    assert div2.position_y == 30
    assert div.height == 5 + 20 + 5 + 60
    assert div1.children[0].children[0].text == 'B1'
    assert div2.children[0].children[0].text == 'B2'
    assert div3.children[0].children[0].text == 'B3'


@assert_no_logs
def test_columns_regression_4():
    # Regression test #3 for https://github.com/Kozea/WeasyPrint/issues/897
    page, = render_pages('''
      <div style="position:absolute">
        <div style="column-count:2">
          <div>a</div>
        </div>
      </div>
    ''')
    html, = page.children
    body, = html.children
    div, = body.children
    assert div.position_y == 0
    column1, = div.children
    assert column1.position_y == 0
    div1, = column1.children
    assert div1.position_y == 0
