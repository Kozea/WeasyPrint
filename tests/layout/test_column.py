"""Tests for multicolumn layout."""

import pytest

from ..testing_utils import assert_no_logs, render_pages


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
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        div { %s; column-gap: 0 }
        body { margin: 0; font-family: weasyprint }
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
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        div { columns: 3; column-gap: %s }
        body { margin: 0; font-family: weasyprint }
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
def test_column_span_1():
    page, = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        body { margin: 0; font-family: weasyprint; line-height: 1 }
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
def test_column_span_2():
    page, = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        body { margin: 0; font-family: weasyprint; line-height: 1 }
        div { columns: 2; width: 10em; column-gap: 0 }
        section { column-span: all; margin: 1em 0 }
      </style>

      <div>
        <section>test</section>
        abc def
        ghi jkl
        mno pqr
        stu vwx
      </div>
    ''')
    html, = page.children
    body, = html.children
    div, = body.children
    section1, column1, column2 = div.children
    assert (section1.content_box_x(), section1.content_box_y()) == (0, 16)
    assert (column1.position_x, column1.position_y) == (0, 3 * 16)
    assert (column2.position_x, column2.position_y) == (5 * 16, 3 * 16)

    assert column1.height == column2.height == 16 * 4


@assert_no_logs
def test_column_span_3():
    page1, page2 = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { margin: 0; size: 8px 3px }
        body { font-family: weasyprint; font-size: 1px }
        div { columns: 2; column-gap: 0; line-height: 1 }
        section { column-span: all }
      </style>
      <div>
        abc def
        ghi jkl
        <section>line1 line2</section>
        mno pqr
      </div>
    ''')
    html, = page1.children
    body, = html.children
    div, = body.children
    column1, column2, section = div.children
    assert (column1.position_x, column1.position_y) == (0, 0)
    assert (column2.position_x, column2.position_y) == (4, 0)
    assert (section.position_x, section.position_y) == (0, 2)

    assert column1.children[0].children[0].children[0].text == 'abc'
    assert column1.children[0].children[1].children[0].text == 'def'
    assert column2.children[0].children[0].children[0].text == 'ghi'
    assert column2.children[0].children[1].children[0].text == 'jkl'
    assert section.children[0].children[0].text == 'line1'

    html, = page2.children
    body, = html.children
    div, = body.children
    section, column1, column2 = div.children
    assert (section.position_x, section.position_y) == (0, 0)
    assert (column1.position_x, column1.position_y) == (0, 1)
    assert (column2.position_x, column2.position_y) == (4, 1)

    assert section.children[0].children[0].text == 'line2'
    assert column1.children[0].children[0].children[0].text == 'mno'
    assert column2.children[0].children[0].children[0].text == 'pqr'


@assert_no_logs
def test_column_span_4():
    page1, page2 = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { margin: 0; size: 8px 3px }
        body { font-family: weasyprint; font-size: 1px }
        div { columns: 2; column-gap: 0; line-height: 1 }
        section { column-span: all }
      </style>
      <div>
        abc def
        <section>line1</section>
        ghi jkl
        mno pqr
      </div>
    ''')
    html, = page1.children
    body, = html.children
    div, = body.children
    column1, column2, section, column3, column4 = div.children
    assert (column1.position_x, column1.position_y) == (0, 0)
    assert (column2.position_x, column2.position_y) == (4, 0)
    assert (section.position_x, section.position_y) == (0, 1)
    assert (column3.position_x, column3.position_y) == (0, 2)
    assert (column4.position_x, column4.position_y) == (4, 2)

    assert column1.children[0].children[0].children[0].text == 'abc'
    assert column2.children[0].children[0].children[0].text == 'def'
    assert section.children[0].children[0].text == 'line1'
    assert column3.children[0].children[0].children[0].text == 'ghi'
    assert column4.children[0].children[0].children[0].text == 'jkl'

    html, = page2.children
    body, = html.children
    div, = body.children
    column1, column2 = div.children
    assert (column1.position_x, column1.position_y) == (0, 0)
    assert (column2.position_x, column2.position_y) == (4, 0)

    assert column1.children[0].children[0].children[0].text == 'mno'
    assert column2.children[0].children[0].children[0].text == 'pqr'


@assert_no_logs
def test_column_span_5():
    page1, page2 = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { margin: 0; size: 8px 3px }
        body { font-family: weasyprint; font-size: 1px }
        div { columns: 2; column-gap: 0; line-height: 1 }
        section { column-span: all }
      </style>
      <div>
        abc def
        ghi jkl
        <section>line1</section>
        mno pqr
      </div>
    ''')
    html, = page1.children
    body, = html.children
    div, = body.children
    column1, column2, section = div.children
    assert (column1.position_x, column1.position_y) == (0, 0)
    assert (column2.position_x, column2.position_y) == (4, 0)
    assert (section.position_x, section.position_y) == (0, 2)

    assert column1.children[0].children[0].children[0].text == 'abc'
    assert column1.children[0].children[1].children[0].text == 'def'
    assert column2.children[0].children[0].children[0].text == 'ghi'
    assert column2.children[0].children[1].children[0].text == 'jkl'
    assert section.children[0].children[0].text == 'line1'

    html, = page2.children
    body, = html.children
    div, = body.children
    column1, column2 = div.children
    assert (column1.position_x, column1.position_y) == (0, 0)
    assert (column2.position_x, column2.position_y) == (4, 0)

    assert column1.children[0].children[0].children[0].text == 'mno'
    assert column2.children[0].children[0].children[0].text == 'pqr'


@assert_no_logs
def test_column_span_6():
    page1, page2 = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { margin: 0; size: 8px 3px }
        body { font-family: weasyprint; font-size: 1px }
        div { columns: 2; column-gap: 0; line-height: 1 }
        section { column-span: all }
      </style>
      <div>
        abc def
        ghi jkl
        mno pqr
        <section>line1</section>
      </div>
    ''')
    html, = page1.children
    body, = html.children
    div, = body.children
    column1, column2 = div.children
    assert (column1.position_x, column1.position_y) == (0, 0)
    assert (column2.position_x, column2.position_y) == (4, 0)

    assert column1.children[0].children[0].children[0].text == 'abc'
    assert column1.children[0].children[1].children[0].text == 'def'
    assert column1.children[0].children[2].children[0].text == 'ghi'
    assert column2.children[0].children[0].children[0].text == 'jkl'
    assert column2.children[0].children[1].children[0].text == 'mno'
    assert column2.children[0].children[2].children[0].text == 'pqr'

    html, = page2.children
    body, = html.children
    div, = body.children
    section, = div.children
    assert section.children[0].children[0].text == 'line1'
    assert (section.position_x, section.position_y) == (0, 0)


@assert_no_logs
def test_column_span_7():
    page1, page2 = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { margin: 0; size: 8px 3px }
        body { font-family: weasyprint; font-size: 1px }
        div { columns: 2; column-gap: 0; line-height: 1 }
        section { column-span: all; font-size: 2px }
      </style>
      <div>
        abc def
        ghi jkl
        <section>l1</section>
        mno pqr
      </div>
    ''')
    html, = page1.children
    body, = html.children
    div, = body.children
    column1, column2 = div.children
    assert (column1.position_x, column1.position_y) == (0, 0)
    assert (column2.position_x, column2.position_y) == (4, 0)

    assert column1.children[0].children[0].children[0].text == 'abc'
    assert column1.children[0].children[1].children[0].text == 'def'
    assert column2.children[0].children[0].children[0].text == 'ghi'
    assert column2.children[0].children[1].children[0].text == 'jkl'

    html, = page2.children
    body, = html.children
    div, = body.children
    section, column1, column2 = div.children
    assert (section.position_x, section.position_y) == (0, 0)
    assert (column1.position_x, column1.position_y) == (0, 2)
    assert (column2.position_x, column2.position_y) == (4, 2)

    assert section.children[0].children[0].text == 'l1'
    assert column1.children[0].children[0].children[0].text == 'mno'
    assert column2.children[0].children[0].children[0].text == 'pqr'


@assert_no_logs
def test_column_span_8():
    page1, page2 = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { margin: 0; size: 8px 2px }
        body { font-family: weasyprint; font-size: 1px }
        div { columns: 2; column-gap: 0; line-height: 1 }
        section { column-span: all }
      </style>
      <div>
        abc def
        ghi jkl
        mno pqr
        <section>line1</section>
      </div>
    ''')
    html, = page1.children
    body, = html.children
    div, = body.children
    column1, column2 = div.children
    assert (column1.position_x, column1.position_y) == (0, 0)
    assert (column2.position_x, column2.position_y) == (4, 0)

    assert column1.children[0].children[0].children[0].text == 'abc'
    assert column1.children[0].children[1].children[0].text == 'def'
    assert column2.children[0].children[0].children[0].text == 'ghi'
    assert column2.children[0].children[1].children[0].text == 'jkl'

    html, = page2.children
    body, = html.children
    div, = body.children
    column1, column2, section = div.children
    assert (column1.position_x, column1.position_y) == (0, 0)
    assert (column2.position_x, column2.position_y) == (4, 0)
    assert (section.position_x, section.position_y) == (0, 1)

    assert column1.children[0].children[0].children[0].text == 'mno'
    assert column2.children[0].children[0].children[0].text == 'pqr'
    assert section.children[0].children[0].text == 'line1'


@assert_no_logs
def test_column_span_9():
    page1, = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { margin: 0; size: 8px 3px }
        body { font-family: weasyprint; font-size: 1px }
        div { columns: 2; column-gap: 0; line-height: 1 }
        section { column-span: all }
      </style>
      <div>
        abc
        <section>line1</section>
        def ghi
      </div>
    ''')
    html, = page1.children
    body, = html.children
    div, = body.children
    column1, section, column2, column3 = div.children
    assert (column1.position_x, column1.position_y) == (0, 0)
    assert (section.position_x, section.position_y) == (0, 1)
    assert (column2.position_x, column2.position_y) == (0, 2)
    assert (column3.position_x, column3.position_y) == (4, 2)

    assert column1.children[0].children[0].children[0].text == 'abc'
    assert section.children[0].children[0].text == 'line1'
    assert column2.children[0].children[0].children[0].text == 'def'
    assert column3.children[0].children[0].children[0].text == 'ghi'


@assert_no_logs
def test_column_span_balance():
    page, = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { margin: 0; size: 8px 5px }
        body { font-family: weasyprint; font-size: 1px }
        div { columns: 2; column-gap: 0; line-height: 1; column-fill: auto }
        section { column-span: all }
      </style>
      <div>
        abc def
        <section>line1</section>
        ghi jkl
      </div>
    ''')
    html, = page.children
    body, = html.children
    div, = body.children
    column1, column2, section, column3 = div.children
    assert (column1.position_x, column1.position_y) == (0, 0)
    assert (column2.position_x, column2.position_y) == (4, 0)
    assert (section.position_x, section.position_y) == (0, 1)
    assert (column3.position_x, column3.position_y) == (0, 2)

    assert column1.children[0].children[0].children[0].text == 'abc'
    assert column2.children[0].children[0].children[0].text == 'def'
    assert section.children[0].children[0].text == 'line1'
    assert column3.children[0].children[0].children[0].text == 'ghi'
    assert column3.children[0].children[1].children[0].text == 'jkl'


@assert_no_logs
def test_columns_multipage():
    page1, page2 = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        div { columns: 2; column-gap: 1px }
        body { margin: 0; font-family: weasyprint;
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
    assert columns[0].children[0].children[0].text == 'a'
    assert columns[0].children[1].children[0].text == 'b'
    assert columns[1].children[0].children[0].text == 'c'
    assert columns[1].children[1].children[0].text == 'd'

    html, = page2.children
    body, = html.children
    div, = body.children
    columns = div.children
    assert len(columns) == 2
    assert len(columns[0].children) == 2
    assert len(columns[1].children) == 1
    assert columns[0].children[0].children[0].text == 'e'
    assert columns[0].children[1].children[0].text == 'f'
    assert columns[1].children[0].children[0].text == 'g'


@assert_no_logs
def test_columns_breaks():
    page1, page2 = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        div { columns: 2; column-gap: 1px }
        body { margin: 0; font-family: weasyprint;
               font-size: 1px; line-height: 1px }
        @page { margin: 0; size: 3px 2px }
        section { break-before: always; }
      </style>
      <div>a<section>b</section><section>c</section></div>
    ''')
    html, = page1.children
    body, = html.children
    div, = body.children
    columns = div.children
    assert len(columns) == 2
    assert len(columns[0].children) == 1
    assert len(columns[1].children) == 1
    assert columns[0].children[0].children[0].children[0].text == 'a'
    assert columns[1].children[0].children[0].children[0].text == 'b'

    html, = page2.children
    body, = html.children
    div, = body.children
    columns = div.children
    assert len(columns) == 1
    assert len(columns[0].children) == 1
    assert columns[0].children[0].children[0].children[0].text == 'c'


@assert_no_logs
def test_columns_break_after_column_1():
    page1, = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        div { columns: 2; column-gap: 1px }
        body { margin: 0; font-family: weasyprint;
               font-size: 1px; line-height: 1px }
        @page { margin: 0; size: 3px 10px }
        section { break-after: column }
      </style>
      <div>a b <section>c</section> d</div>
    ''')
    html, = page1.children
    body, = html.children
    div, = body.children
    columns = div.children
    assert len(columns) == 2
    assert columns[0].children[0].children[0].children[0].text == 'a'
    assert columns[0].children[0].children[1].children[0].text == 'b'
    assert columns[0].children[1].children[0].children[0].text == 'c'
    assert columns[1].children[0].children[0].children[0].text == 'd'


@assert_no_logs
def test_columns_break_after_column_2():
    page1, = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        div { columns: 2; column-gap: 1px }
        body { margin: 0; font-family: weasyprint;
               font-size: 1px; line-height: 1px }
        @page { margin: 0; size: 3px 10px }
        section { break-after: column }
      </style>
      <div><section>a</section> b c d</div>
    ''')
    html, = page1.children
    body, = html.children
    div, = body.children
    columns = div.children
    assert len(columns) == 2
    assert columns[0].children[0].children[0].children[0].text == 'a'
    assert columns[1].children[0].children[0].children[0].text == 'b'
    assert columns[1].children[0].children[1].children[0].text == 'c'
    assert columns[1].children[0].children[2].children[0].text == 'd'


@assert_no_logs
def test_columns_break_after_avoid_column():
    page1, = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        div { columns: 2; column-gap: 1px }
        body { margin: 0; font-family: weasyprint;
               font-size: 1px; line-height: 1px }
        @page { margin: 0; size: 3px 10px }
        section { break-after: avoid-column }
      </style>
      <div>a <section>b</section> c d</div>
    ''')
    html, = page1.children
    body, = html.children
    div, = body.children
    columns = div.children
    assert len(columns) == 2
    assert columns[0].children[0].children[0].children[0].text == 'a'
    assert columns[0].children[1].children[0].children[0].text == 'b'
    assert columns[0].children[2].children[0].children[0].text == 'c'
    assert columns[1].children[0].children[0].children[0].text == 'd'


@assert_no_logs
def test_columns_break_before_column_1():
    page1, = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        div { columns: 2; column-gap: 1px }
        body { margin: 0; font-family: weasyprint;
               font-size: 1px; line-height: 1px }
        @page { margin: 0; size: 3px 10px }
        section { break-before: column }
      </style>
      <div>a b c <section>d</section></div>
    ''')
    html, = page1.children
    body, = html.children
    div, = body.children
    columns = div.children
    assert len(columns) == 2
    assert columns[0].children[0].children[0].children[0].text == 'a'
    assert columns[0].children[0].children[1].children[0].text == 'b'
    assert columns[0].children[0].children[2].children[0].text == 'c'
    assert columns[1].children[0].children[0].children[0].text == 'd'


@assert_no_logs
def test_columns_break_before_column_2():
    page1, = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        div { columns: 2; column-gap: 1px }
        body { margin: 0; font-family: weasyprint;
               font-size: 1px; line-height: 1px }
        @page { margin: 0; size: 3px 10px }
        section { break-before: column }
      </style>
      <div>a <section>b</section> c d</div>
    ''')
    html, = page1.children
    body, = html.children
    div, = body.children
    columns = div.children
    assert len(columns) == 2
    assert columns[0].children[0].children[0].children[0].text == 'a'
    assert columns[1].children[0].children[0].children[0].text == 'b'
    assert columns[1].children[1].children[0].children[0].text == 'c'
    assert columns[1].children[1].children[1].children[0].text == 'd'


@assert_no_logs
def test_columns_break_before_avoid_column():
    page1, = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        div { columns: 2; column-gap: 1px }
        body { margin: 0; font-family: weasyprint;
               font-size: 1px; line-height: 1px }
        @page { margin: 0; size: 3px 10px }
        section { break-before: avoid-column }
      </style>
      <div>a b <section>c</section> d</div>
    ''')
    html, = page1.children
    body, = html.children
    div, = body.children
    columns = div.children
    assert len(columns) == 2
    assert columns[0].children[0].children[0].children[0].text == 'a'
    assert columns[0].children[0].children[1].children[0].text == 'b'
    assert columns[0].children[1].children[0].children[0].text == 'c'
    assert columns[1].children[0].children[0].children[0].text == 'd'


@assert_no_logs
def test_columns_break_inside_column_1():
    page1, = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        div { columns: 2; column-gap: 1px }
        body { margin: 0; font-family: weasyprint;
               font-size: 1px; line-height: 1px }
        @page { margin: 0; size: 3px 10px }
        section { break-inside: avoid-column }
      </style>
      <div><section>a b c</section> d</div>
    ''')
    html, = page1.children
    body, = html.children
    div, = body.children
    columns = div.children
    assert len(columns) == 2
    assert columns[0].children[0].children[0].children[0].text == 'a'
    assert columns[0].children[0].children[1].children[0].text == 'b'
    assert columns[0].children[0].children[2].children[0].text == 'c'
    assert columns[1].children[0].children[0].children[0].text == 'd'


@assert_no_logs
def test_columns_break_inside_column_2():
    page1, = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        div { columns: 2; column-gap: 1px }
        body { margin: 0; font-family: weasyprint;
               font-size: 1px; line-height: 1px }
        @page { margin: 0; size: 3px 10px }
        section { break-inside: avoid-column }
      </style>
      <div>a <section>b c d</section></div>
    ''')
    html, = page1.children
    body, = html.children
    div, = body.children
    columns = div.children
    assert len(columns) == 2
    assert columns[0].children[0].children[0].children[0].text == 'a'
    assert columns[1].children[0].children[0].children[0].text == 'b'
    assert columns[1].children[0].children[1].children[0].text == 'c'
    assert columns[1].children[0].children[2].children[0].text == 'd'


@assert_no_logs
def test_columns_break_inside_column_not_empty_page():
    page1, = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        div { columns: 2; column-gap: 1px }
        body { margin: 0; font-family: weasyprint;
               font-size: 1px; line-height: 1px }
        @page { margin: 0; size: 3px 10px }
        section { break-inside: avoid-column }
      </style>
      <p>p</p>
      <div><section>a b c</section> d</div>
    ''')
    html, = page1.children
    body, = html.children
    p, div, = body.children
    assert p.children[0].children[0].text == 'p'
    columns = div.children
    assert len(columns) == 2
    assert columns[0].children[0].children[0].children[0].text == 'a'
    assert columns[0].children[0].children[1].children[0].text == 'b'
    assert columns[0].children[0].children[2].children[0].text == 'c'
    assert columns[1].children[0].children[0].children[0].text == 'd'


@assert_no_logs
def test_columns_not_enough_content():
    page, = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        div { columns: 5; column-gap: 0 }
        body { margin: 0; font-family: weasyprint; font-size: 1px }
        @page { margin: 0; size: 5px }
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
def test_columns_higher_than_page():
    page1, page2 = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        div { columns: 5; column-gap: 0 }
        body { margin: 0; font-family: weasyprint; font-size: 2px }
        @page { margin: 0; size: 5px 1px }
      </style>
      <div>a b c d e f g h</div>
    ''')
    html, = page1.children
    body, = html.children
    div, = body.children
    assert div.width == 5
    columns = div.children
    assert len(columns) == 5
    assert columns[0].children[0].children[0].text == 'a'
    assert columns[1].children[0].children[0].text == 'b'
    assert columns[2].children[0].children[0].text == 'c'
    assert columns[3].children[0].children[0].text == 'd'
    assert columns[4].children[0].children[0].text == 'e'

    html, = page2.children
    body, = html.children
    div, = body.children
    assert div.width == 5
    columns = div.children
    assert len(columns) == 3
    assert columns[0].children[0].children[0].text == 'f'
    assert columns[1].children[0].children[0].text == 'g'
    assert columns[2].children[0].children[0].text == 'h'


@assert_no_logs
def test_columns_empty():
    page, = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        div { columns: 3 }
        body { margin: 0; font-family: weasyprint }
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
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        div { columns: 4; column-gap: 0; %s: 10px }
        body { margin: 0; font-family: weasyprint; line-height: 1px }
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
def test_columns_padding():
    page, = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        div { columns: 4; column-gap: 0; padding: 1px }
        body { margin: 0; font-family: weasyprint; line-height: 1px }
        @page { margin: 0; size: 6px 50px; font-size: 1px }
      </style>
      <div>a b c</div>
    ''')
    html, = page.children
    body, = html.children
    div, = body.children
    assert div.width == 4
    assert div.height == 1
    assert div.padding_width() == 6
    assert div.padding_height() == 3
    columns = div.children
    assert len(columns) == 3
    assert [column.width for column in columns] == [1, 1, 1]
    assert [column.height for column in columns] == [1, 1, 1]
    assert [column.position_x for column in columns] == [1, 2, 3]
    assert [column.position_y for column in columns] == [1, 1, 1]


@assert_no_logs
def test_columns_relative():
    page, = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        article { position: absolute; top: 3px }
        div { columns: 4; column-gap: 0; position: relative;
              top: 1px; left: 2px }
        body { margin: 0; font-family: weasyprint; line-height: 1px }
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
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/897
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


@assert_no_logs
def test_columns_regression_5():
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/1191
    render_pages('''
      <style>
        @page {width: 100px; height: 100px}
      </style>
      <div style="height: 1px"></div>
      <div style="columns: 2">
        <div style="break-after: avoid">
          <div style="height: 50px"></div>
        </div>
        <div style="break-after: avoid">
          <div style="height: 50px"></div>
          <p>a</p>
        </div>
      </div>
      <div style="height: 50px"></div>
    ''')
