"""
    weasyprint.tests.layout.flex
    ----------------------------

    Tests for flex layout.

    :copyright: Copyright 2011-2018 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

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
        article.position_y + div_2.height)
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
        article.position_x + div_2.width)
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
