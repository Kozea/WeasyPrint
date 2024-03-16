"""Test the CSS cross references using target-*() functions."""

from ..testing_utils import assert_no_logs, render_pages


@assert_no_logs
def test_target_counter():
    page, = render_pages('''
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
    html, = page.children
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
    page, = render_pages('''
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
    html, = page.children
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
    page, = render_pages('''
      <style>
        div:first-child { counter-reset: div }
        div { counter-increment: div }
        #id1-2::before { content: target-counters('#id4-2', div, '.') }
        #id2-1::before { content: target-counters(url(#id3), div, '++') }
        #id3::before {
          content: target-counters('#id2-1', div, '.', lower-alpha) }
        #id4-2::before {
          content: target-counters(attr(data-count, url), div, '') }
      </style>
      <body>
        <div id="id1"><div></div><div id="id1-2"></div></div>
        <div id="id2"><div id="id2-1"></div><div></div></div>
        <div id="id3"></div>
        <div id="id4">
          <div></div><div id="id4-2" data-count="#id1-2"></div>
        </div>
    ''')
    html, = page.children
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


@assert_no_logs
def test_target_text():
    page, = render_pages('''
      <style>
        a { display: block; color: red }
        div:first-child { counter-reset: div }
        div { counter-increment: div }
        #id2::before { content: 'wow' }
        #link1::before { content: 'test ' target-text('#id4') }
        #link2::before { content: target-text(attr(data-count, url), before) }
        #link3::before { content: target-text('#id3', after) }
        #link4::before { content: target-text(url(#id1), first-letter) }
      </style>
      <body>
        <a id="link1"></a>
        <div id="id1">1 Chapter 1</div>
        <a id="link2" data-count="#id2"></a>
        <div id="id2">2 Chapter 2</div>
        <div id="id3">3 Chapter 3</div>
        <a id="link3"></a>
        <div id="id4">4 Chapter 4</div>
        <a id="link4"></a>
    ''')
    html, = page.children
    body, = html.children
    a1, div1, a2, div2, div3, a3, div4, a4 = body.children
    before = a1.children[0].children[0].children[0]
    assert before.text == 'test 4 Chapter 4'
    before = a2.children[0].children[0].children[0]
    assert before.text == 'wow'
    assert len(a3.children[0].children[0].children) == 0
    before = a4.children[0].children[0].children[0]
    assert before.text == '1'


@assert_no_logs
def test_target_float():
    page, = render_pages('''
      <style>
        a::after {
          content: target-counter('#h', page);
          float: right;
        }
      </style>
      <div><a id="span">link</a></div>
      <h1 id="h">abc</h1>
    ''')
    html, = page.children
    body, = html.children
    div, h1 = body.children
    line, = div.children
    inline, = line.children
    text_box, after = inline.children
    assert text_box.text == 'link'
    assert after.children[0].children[0].text == '1'


@assert_no_logs
def test_target_absolute():
    page, = render_pages('''
      <style>
        a::after {
          content: target-counter('#h', page);
        }
        div {
          position: absolute;
        }
      </style>
      <div><a id="span">link</a></div>
      <h1 id="h">abc</h1>
    ''')
    html, = page.children
    body, = html.children
    div, h1 = body.children
    line, = div.children
    inline, = line.children
    text_box, after = inline.children
    assert text_box.text == 'link'
    assert after.children[0].text == '1'


@assert_no_logs
def test_target_absolute_non_root():
    page, = render_pages('''
      <style>
        a::after {
          content: target-counter('#h', page);
        }
        section {
          position: relative;
        }
        div {
          position: absolute;
        }
      </style>
      <section><div><a id="span">link</a></div></section>
      <h1 id="h">abc</h1>
    ''')
    html, = page.children
    body, = html.children
    section, h1 = body.children
    div, = section.children
    line, = div.children
    inline, = line.children
    text_box, after = inline.children
    assert text_box.text == 'link'
    assert after.children[0].text == '1'
