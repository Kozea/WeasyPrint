"""
    weasyprint.tests.test_target
    ----------------------------

    Test the CSS cross references using target-*() functions.

    :copyright: Copyright 2018 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from .testing_utils import FakeHTML, assert_no_logs


@assert_no_logs
def test_target_counter():
    document = FakeHTML(string='''
      <style>
        div:first-child { counter-reset: div }
        div { counter-increment: div }
        #id1::before { content: target-counter('#id4', div) }
        #id2::before { content: 'test ' target-counter('#id1' div) }
        #id3::before { content: target-counter(url(#id4), div, lower-roman) }
        #id4::before { content: target-counter('#id3', div) }
      </style>
      <body>
        <div id="id1"></div>
        <div id="id2"></div>
        <div id="id3"></div>
        <div id="id4"></div>
    ''')
    page, = document.render().pages
    html, = page._page_box.children
    body, = html.children
    div1, div2, div3, div4 = body.children
    before = div1.children[0].children[0].children[0]
    assert before.text == '4'
    before = div2.children[0].children[0].children[0]
    assert before.text == 'test 1'
    before = div3.children[0].children[0].children[0]
    assert before.text == 'iv'
    before = div4.children[0].children[0].children[0]
    assert before.text == '3'


@assert_no_logs
def test_target_counter_attr():
    document = FakeHTML(string='''
      <style>
        div:first-child { counter-reset: div }
        div { counter-increment: div }
        div::before { content: target-counter(attr(data-count), div) }
        #id2::before { content: target-counter(attr(data-count, url), div) }
        #id4::before {
          content: target-counter(attr(data-count), div, lower-alpha) }
      </style>
      <body>
        <div id="id1" data-count="#id4"></div>
        <div id="id2" data-count="#id1"></div>
        <div id="id3" data-count="#id2"></div>
        <div id="id4" data-count="#id3"></div>
    ''')
    page, = document.render().pages
    html, = page._page_box.children
    body, = html.children
    div1, div2, div3, div4 = body.children
    before = div1.children[0].children[0].children[0]
    assert before.text == '4'
    before = div2.children[0].children[0].children[0]
    assert before.text == '1'
    before = div3.children[0].children[0].children[0]
    assert before.text == '2'
    before = div4.children[0].children[0].children[0]
    assert before.text == 'c'


@assert_no_logs
def test_target_counters():
    document = FakeHTML(string='''
      <style>
        div:first-child { counter-reset: div }
        div { counter-increment: div }
        #id1-2::before { content: target-counters('#id4-2', div, '.') }
        #id2-1::before { content: target-counters('#id3', div, '++') }
        #id3::before {
          content: target-counters('#id2-1', div, '.', lower-alpha) }
        #id4-2::before { content: target-counters('#id1-2', div, '') }
      </style>
      <body>
        <div id="id1"><div></div><div id="id1-2"></div></div>
        <div id="id2"><div id="id2-1"></div><div></div></div>
        <div id="id3"></div>
        <div id="id4"><div></div><div id="id4-2"></div></div>
    ''')
    page, = document.render().pages
    html, = page._page_box.children
    body, = html.children
    div1, div2, div3, div4 = body.children
    before = div1.children[1].children[0].children[0].children[0]
    assert before.text == '4.2'
    before = div2.children[0].children[0].children[0].children[0]
    assert before.text == '3'
    before = div3.children[0].children[0].children[0]
    assert before.text == 'b.a'
    before = div4.children[1].children[0].children[0].children[0]
    assert before.text == '12'
