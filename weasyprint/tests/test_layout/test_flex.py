"""
    weasyprint.tests.layout.flex
    ----------------------------

    Tests for flex layout.

"""

import pytest

from ..test_boxes import render_pages
from ..testing_utils import assert_no_logs


@assert_no_logs
def test_flex_direction_row():
    page, = render_pages('''
      <article style="display: flex">
        <div>A</div>
        <div>B</div>
        <div>C</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_1, div_2, div_3 = article.children
    assert div_1.children[0].children[0].text == 'A'
    assert div_2.children[0].children[0].text == 'B'
    assert div_3.children[0].children[0].text == 'C'
    assert (
        div_1.position_y ==
        div_2.position_y ==
        div_3.position_y ==
        article.position_y)
    assert div_1.position_x == article.position_x
    assert div_1.position_x < div_2.position_x < div_3.position_x


@assert_no_logs
def test_flex_direction_row_rtl():
    page, = render_pages('''
      <article style="display: flex; direction: rtl">
        <div>A</div>
        <div>B</div>
        <div>C</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_1, div_2, div_3 = article.children
    assert div_1.children[0].children[0].text == 'A'
    assert div_2.children[0].children[0].text == 'B'
    assert div_3.children[0].children[0].text == 'C'
    assert (
        div_1.position_y ==
        div_2.position_y ==
        div_3.position_y ==
        article.position_y)
    assert (
        div_1.position_x + div_1.width ==
        article.position_x + article.width)
    assert div_1.position_x > div_2.position_x > div_3.position_x


@assert_no_logs
def test_flex_direction_row_reverse():
    page, = render_pages('''
      <article style="display: flex; flex-direction: row-reverse">
        <div>A</div>
        <div>B</div>
        <div>C</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_1, div_2, div_3 = article.children
    assert div_1.children[0].children[0].text == 'C'
    assert div_2.children[0].children[0].text == 'B'
    assert div_3.children[0].children[0].text == 'A'
    assert (
        div_1.position_y ==
        div_2.position_y ==
        div_3.position_y ==
        article.position_y)
    assert (
        div_3.position_x + div_3.width ==
        article.position_x + article.width)
    assert div_1.position_x < div_2.position_x < div_3.position_x


@assert_no_logs
def test_flex_direction_row_reverse_rtl():
    page, = render_pages('''
      <article style="display: flex; flex-direction: row-reverse;
      direction: rtl">
        <div>A</div>
        <div>B</div>
        <div>C</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_1, div_2, div_3 = article.children
    assert div_1.children[0].children[0].text == 'C'
    assert div_2.children[0].children[0].text == 'B'
    assert div_3.children[0].children[0].text == 'A'
    assert (
        div_1.position_y ==
        div_2.position_y ==
        div_3.position_y ==
        article.position_y)
    assert div_3.position_x == article.position_x
    assert div_1.position_x > div_2.position_x > div_3.position_x


@assert_no_logs
def test_flex_direction_column():
    page, = render_pages('''
      <article style="display: flex; flex-direction: column">
        <div>A</div>
        <div>B</div>
        <div>C</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_1, div_2, div_3 = article.children
    assert div_1.children[0].children[0].text == 'A'
    assert div_2.children[0].children[0].text == 'B'
    assert div_3.children[0].children[0].text == 'C'
    assert (
        div_1.position_x ==
        div_2.position_x ==
        div_3.position_x ==
        article.position_x)
    assert div_1.position_y == article.position_y
    assert div_1.position_y < div_2.position_y < div_3.position_y


@assert_no_logs
def test_flex_direction_column_rtl():
    page, = render_pages('''
      <article style="display: flex; flex-direction: column;
      direction: rtl">
        <div>A</div>
        <div>B</div>
        <div>C</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_1, div_2, div_3 = article.children
    assert div_1.children[0].children[0].text == 'A'
    assert div_2.children[0].children[0].text == 'B'
    assert div_3.children[0].children[0].text == 'C'
    assert (
        div_1.position_x ==
        div_2.position_x ==
        div_3.position_x ==
        article.position_x)
    assert div_1.position_y == article.position_y
    assert div_1.position_y < div_2.position_y < div_3.position_y


@assert_no_logs
def test_flex_direction_column_reverse():
    page, = render_pages('''
      <article style="display: flex; flex-direction: column-reverse">
        <div>A</div>
        <div>B</div>
        <div>C</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_1, div_2, div_3 = article.children
    assert div_1.children[0].children[0].text == 'C'
    assert div_2.children[0].children[0].text == 'B'
    assert div_3.children[0].children[0].text == 'A'
    assert (
        div_1.position_x ==
        div_2.position_x ==
        div_3.position_x ==
        article.position_x)
    assert (
        div_3.position_y + div_3.height ==
        article.position_y + article.height)
    assert div_1.position_y < div_2.position_y < div_3.position_y


@assert_no_logs
def test_flex_direction_column_reverse_rtl():
    page, = render_pages('''
      <article style="display: flex; flex-direction: column-reverse;
      direction: rtl">
        <div>A</div>
        <div>B</div>
        <div>C</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_1, div_2, div_3 = article.children
    assert div_1.children[0].children[0].text == 'C'
    assert div_2.children[0].children[0].text == 'B'
    assert div_3.children[0].children[0].text == 'A'
    assert (
        div_1.position_x ==
        div_2.position_x ==
        div_3.position_x ==
        article.position_x)
    assert (
        div_3.position_y + div_3.height ==
        article.position_y + article.height)
    assert div_1.position_y < div_2.position_y < div_3.position_y


@assert_no_logs
def test_flex_row_wrap():
    page, = render_pages('''
      <article style="display: flex; flex-flow: wrap; width: 50px">
        <div style="width: 20px">A</div>
        <div style="width: 20px">B</div>
        <div style="width: 20px">C</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_1, div_2, div_3 = article.children
    assert div_1.children[0].children[0].text == 'A'
    assert div_2.children[0].children[0].text == 'B'
    assert div_3.children[0].children[0].text == 'C'
    assert div_1.position_y == div_2.position_y == article.position_y
    assert div_3.position_y == article.position_y + div_2.height
    assert div_1.position_x == div_3.position_x == article.position_x
    assert div_1.position_x < div_2.position_x


@assert_no_logs
def test_flex_column_wrap():
    page, = render_pages('''
      <article style="display: flex; flex-flow: column wrap; height: 50px">
        <div style="height: 20px">A</div>
        <div style="height: 20px">B</div>
        <div style="height: 20px">C</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_1, div_2, div_3 = article.children
    assert div_1.children[0].children[0].text == 'A'
    assert div_2.children[0].children[0].text == 'B'
    assert div_3.children[0].children[0].text == 'C'
    assert div_1.position_x == div_2.position_x == article.position_x
    assert div_3.position_x == article.position_x + div_2.width
    assert div_1.position_y == div_3.position_y == article.position_y
    assert div_1.position_y < div_2.position_y


@assert_no_logs
def test_flex_row_wrap_reverse():
    page, = render_pages('''
      <article style="display: flex; flex-flow: wrap-reverse; width: 50px">
        <div style="width: 20px">A</div>
        <div style="width: 20px">B</div>
        <div style="width: 20px">C</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_1, div_2, div_3 = article.children
    assert div_1.children[0].children[0].text == 'C'
    assert div_2.children[0].children[0].text == 'A'
    assert div_3.children[0].children[0].text == 'B'
    assert div_1.position_y == article.position_y
    assert (
        div_2.position_y ==
        div_3.position_y ==
        article.position_y + div_1.height)
    assert div_1.position_x == div_2.position_x == article.position_x
    assert div_2.position_x < div_3.position_x


@assert_no_logs
def test_flex_column_wrap_reverse():
    page, = render_pages('''
      <article style="display: flex; flex-flow: column wrap-reverse;
                      height: 50px">
        <div style="height: 20px">A</div>
        <div style="height: 20px">B</div>
        <div style="height: 20px">C</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_1, div_2, div_3 = article.children
    assert div_1.children[0].children[0].text == 'C'
    assert div_2.children[0].children[0].text == 'A'
    assert div_3.children[0].children[0].text == 'B'
    assert div_1.position_x == article.position_x
    assert (
        div_2.position_x ==
        div_3.position_x ==
        article.position_x + div_1.width)
    assert div_1.position_y == div_2.position_y == article.position_y
    assert div_2.position_y < div_3.position_y


@assert_no_logs
def test_flex_direction_column_fixed_height_container():
    page, = render_pages('''
      <section style="height: 10px">
        <article style="display: flex; flex-direction: column">
          <div>A</div>
          <div>B</div>
          <div>C</div>
        </article>
      </section>
    ''')
    html, = page.children
    body, = html.children
    section, = body.children
    article, = section.children
    div_1, div_2, div_3 = article.children
    assert div_1.children[0].children[0].text == 'A'
    assert div_2.children[0].children[0].text == 'B'
    assert div_3.children[0].children[0].text == 'C'
    assert (
        div_1.position_x ==
        div_2.position_x ==
        div_3.position_x ==
        article.position_x)
    assert div_1.position_y == article.position_y
    assert div_1.position_y < div_2.position_y < div_3.position_y
    assert section.height == 10
    assert article.height > 10


@pytest.mark.xfail
@assert_no_logs
def test_flex_direction_column_fixed_height():
    page, = render_pages('''
      <article style="display: flex; flex-direction: column; height: 10px">
        <div>A</div>
        <div>B</div>
        <div>C</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_1, div_2, div_3 = article.children
    assert div_1.children[0].children[0].text == 'A'
    assert div_2.children[0].children[0].text == 'B'
    assert div_3.children[0].children[0].text == 'C'
    assert (
        div_1.position_x ==
        div_2.position_x ==
        div_3.position_x ==
        article.position_x)
    assert div_1.position_y == article.position_y
    assert div_1.position_y < div_2.position_y < div_3.position_y
    assert article.height == 10
    assert div_3.position_y > 10


@assert_no_logs
def test_flex_direction_column_fixed_height_wrap():
    page, = render_pages('''
      <article style="display: flex; flex-direction: column; height: 10px;
                      flex-wrap: wrap">
        <div>A</div>
        <div>B</div>
        <div>C</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_1, div_2, div_3 = article.children
    assert div_1.children[0].children[0].text == 'A'
    assert div_2.children[0].children[0].text == 'B'
    assert div_3.children[0].children[0].text == 'C'
    assert (
        div_1.position_x !=
        div_2.position_x !=
        div_3.position_x)
    assert div_1.position_y == article.position_y
    assert (
        div_1.position_y ==
        div_2.position_y ==
        div_3.position_y ==
        article.position_y)
    assert article.height == 10


@assert_no_logs
def test_flex_item_min_width():
    page, = render_pages('''
      <article style="display: flex">
        <div style="min-width: 30px">A</div>
        <div style="min-width: 50px">B</div>
        <div style="min-width: 5px">C</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_1, div_2, div_3 = article.children
    assert div_1.children[0].children[0].text == 'A'
    assert div_2.children[0].children[0].text == 'B'
    assert div_3.children[0].children[0].text == 'C'
    assert div_1.position_x == 0
    assert div_1.width == 30
    assert div_2.position_x == 30
    assert div_2.width == 50
    assert div_3.position_x == 80
    assert div_3.width > 5
    assert (
        div_1.position_y ==
        div_2.position_y ==
        div_3.position_y ==
        article.position_y)


@assert_no_logs
def test_flex_item_min_height():
    page, = render_pages('''
      <article style="display: flex">
        <div style="min-height: 30px">A</div>
        <div style="min-height: 50px">B</div>
        <div style="min-height: 5px">C</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_1, div_2, div_3 = article.children
    assert div_1.children[0].children[0].text == 'A'
    assert div_2.children[0].children[0].text == 'B'
    assert div_3.children[0].children[0].text == 'C'
    assert (
        div_1.height ==
        div_2.height ==
        div_3.height ==
        article.height ==
        50)


@assert_no_logs
def test_flex_auto_margin():
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/800
    page, = render_pages('<div style="display: flex; margin: auto">')
    page, = render_pages(
        '<div style="display: flex; flex-direction: column; margin: auto">')


@assert_no_logs
def test_flex_no_baseline():
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/765
    page, = render_pages('''
      <div class="references" style="display: flex; align-items: baseline;">
        <div></div>
      </div>''')


@assert_no_logs
@pytest.mark.parametrize('align, height, y1, y2', (
    ('flex-start', 50, 0, 10),
    ('flex-end', 50, 30, 40),
    ('space-around', 60, 10, 40),
    ('space-between', 50, 0, 40),
    ('space-evenly', 50, 10, 30),
))
def test_flex_align_content(align, height, y1, y2):
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/811
    page, = render_pages('''
      <style>
        @font-face { src: url(AHEM____.TTF); font-family: ahem }
        article {
          align-content: %s;
          display: flex;
          flex-wrap: wrap;
          font-family: ahem;
          font-size: 10px;
          height: %ipx;
          line-height: 1;
        }
        section {
          width: 100%%;
        }
      </style>
      <article>
        <section><span>Lorem</span></section>
        <section><span>Lorem</span></section>
      </article>
    ''' % (align, height))
    html, = page.children
    body, = html.children
    article, = body.children
    section1, section2 = article.children
    line1, = section1.children
    line2, = section2.children
    span1, = line1.children
    span2, = line2.children
    assert section1.position_x == span1.position_x == 0
    assert section1.position_y == span1.position_y == y1
    assert section2.position_x == span2.position_x == 0
    assert section2.position_y == span2.position_y == y2


@assert_no_logs
def test_flex_item_percentage():
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/885
    page, = render_pages('''
      <div style="display: flex; font-size: 15px; line-height: 1">
        <div style="height: 100%">a</div>
      </div>''')
    html, = page.children
    body, = html.children
    flex, = body.children
    flex_item, = flex.children
    assert flex_item.height == 15


@assert_no_logs
def test_flex_undefined_percentage_height_multiple_lines():
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/1204
    page, = render_pages('''
      <div style="display: flex; flex-wrap: wrap; height: 100%">
        <div style="width: 100%">a</div>
        <div style="width: 100%">b</div>
      </div>''')
