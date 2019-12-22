"""
    weasyprint.tests.layout.page
    ----------------------------

    Tests for pages layout.

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import pytest

from ...formatting_structure import boxes
from ..test_boxes import render_pages
from ..testing_utils import assert_no_logs


@assert_no_logs
@pytest.mark.parametrize('size, width, height', (
    ('auto', 793, 1122),
    ('2in 10in', 192, 960),
    ('242px', 242, 242),
    ('letter', 816, 1056),
    ('letter portrait', 816, 1056),
    ('letter landscape', 1056, 816),
    ('portrait', 793, 1122),
    ('landscape', 1122, 793),
))
def test_page_size_basic(size, width, height):
    """Test the layout for ``@page`` properties."""
    page, = render_pages('<style>@page { size: %s; }</style>' % size)
    assert int(page.margin_width()) == width
    assert int(page.margin_height()) == height


@assert_no_logs
def test_page_size_with_margin():
    page, = render_pages('''<style>
      @page { size: 200px 300px; margin: 10px 10% 20% 1in }
      body { margin: 8px }
    </style>
    <p style="margin: 0">''')
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


@assert_no_logs
def test_page_size_with_margin_border_padding():
    page, = render_pages('''<style> @page {
      size: 100px; margin: 1px 2px; padding: 4px 8px;
      border-width: 16px 32px; border-style: solid;
    }</style>''')
    assert page.width == 16  # 100 - 2 * 42
    assert page.height == 58  # 100 - 2 * 21
    html, = page.children
    assert html.element_tag == 'html'
    assert html.position_x == 42  # 2 + 8 + 32
    assert html.position_y == 21  # 1 + 4 + 16


@assert_no_logs
@pytest.mark.parametrize('margin, top, right, bottom, left', (
    ('auto', 15, 10, 15, 10),
    ('5px 5px auto auto', 5, 5, 25, 15),
))
def test_page_size_margins(margin, top, right, bottom, left):
    page, = render_pages('''<style>@page {
      size: 106px 206px; width: 80px; height: 170px;
      padding: 1px; border: 2px solid; margin: %s }</style>''' % margin)
    assert page.margin_top == top
    assert page.margin_right == right
    assert page.margin_bottom == bottom
    assert page.margin_left == left


@assert_no_logs
@pytest.mark.parametrize('style, width, height', (
    ('size: 4px 10000px; width: 100px; height: 100px;'
     'padding: 1px; border: 2px solid; margin: 3px',
     112, 112),
    ('size: 1000px; margin: 100px; max-width: 500px; min-height: 1500px',
     700, 1700),
    ('size: 1000px; margin: 100px; min-width: 1500px; max-height: 500px',
     1700, 700),
))
def test_page_size_over_constrained(style, width, height):
    page, = render_pages('<style>@page { %s }</style>' % style)
    assert page.margin_width() == width
    assert page.margin_height() == height


@assert_no_logs
@pytest.mark.parametrize('html', (
    '<div>1</div>',
    '<div></div>',
    '<img src=pattern.png>'
))
def test_page_breaks(html):
    pages = render_pages('''
      <style>
        @page { size: 100px; margin: 10px }
        body { margin: 0 }
        div { height: 30px; font-size: 20px }
        img { height: 30px; display: block }
      </style>
      %s''' % (5 * html))
    page_children = []
    for page in pages:
        html, = page.children
        body, = html.children
        children = body.children
        assert all([child.element_tag in ('div', 'img') for child in children])
        assert all([child.position_x == 10 for child in children])
        page_children.append(children)
    assert [
        [child.position_y for child in page_child]
        for page_child in page_children] == [[10, 40], [10, 40], [10]]


@assert_no_logs
def test_page_breaks_complex_1():
    page_1, page_2, page_3, page_4 = render_pages('''
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


@assert_no_logs
def test_page_breaks_complex_2():
    # Reference for the following test:
    # Without any 'avoid', this breaks after the <div>
    page_1, page_2 = render_pages('''
      <style>
        @page { size: 140px; margin: 0 }
        img { height: 25px; vertical-align: top }
        p { orphans: 1; widows: 1 }
      </style>
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


@assert_no_logs
def test_page_breaks_complex_3():
    # Adding a few page-break-*: avoid, the only legal break is
    # before the <div>
    page_1, page_2 = render_pages('''
      <style>
        @page { size: 140px; margin: 0 }
        img { height: 25px; vertical-align: top }
        p { orphans: 1; widows: 1 }
      </style>
      <img src=pattern.png><!-- page break here -->
      <div>
        <p style="page-break-inside: avoid">
          <img src=pattern.png><br/><img src=pattern.png></p>
        <p style="page-break-before: avoid; page-break-after: avoid; widows: 2"
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


@assert_no_logs
def test_page_breaks_complex_4():
    page_1, page_2 = render_pages('''
      <style>
        @page { size: 140px; margin: 0 }
        img { height: 25px; vertical-align: top }
        p { orphans: 1; widows: 1 }
      </style>
      <img src=pattern.png><!-- page break here -->
      <div>
        <div>
          <p style="page-break-inside: avoid">
            <img src=pattern.png><br/><img src=pattern.png></p>
          <p style="page-break-before:avoid; page-break-after:avoid; widows:2"
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


@assert_no_logs
def test_page_breaks_complex_5():
    # Reference for the next test
    page_1, page_2, page_3 = render_pages('''
      <style>
        @page { size: 100px; margin: 0 }
        img { height: 30px; display: block; }
        p { orphans: 1; widows: 1 }
      </style>
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
    assert div.height == 100
    html, = page_2.children
    body, = html.children
    div, img_4 = body.children
    assert div.height == 60
    assert img_4.height == 30
    html, = page_3.children
    body, = html.children
    img_5, = body.children
    assert img_5.height == 30


@assert_no_logs
def test_page_breaks_complex_6():
    page_1, page_2, page_3 = render_pages('''
      <style>
        @page { size: 100px; margin: 0 }
        img { height: 30px; display: block; }
        p { orphans: 1; widows: 1 }
      </style>
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
    assert div.height == 100
    html, = page_2.children
    body, = html.children
    div, = body.children
    section, = div.children
    img_2, = section.children
    assert img_2.height == 30
    # TODO: currently this is 60: we do not increase the used height of blocks
    # to make them fill the blank space at the end of the age when we remove
    # children from them for some break-*: avoid.
    # See TODOs in blocks.block_container_layout
    # assert div.height == 100
    html, = page_3.children
    body, = html.children
    div, img_4, img_5, = body.children
    assert div.height == 30
    assert img_4.height == 30
    assert img_5.height == 30


@assert_no_logs
def test_page_breaks_complex_7():
    page_1, page_2, page_3 = render_pages('''
      <style>
        @page { @bottom-center { content: counter(page) } }
        @page:blank { @bottom-center { content: none } }
      </style>
      <p style="page-break-after: right">foo</p>
      <p>bar</p>
    ''')
    assert len(page_1.children) == 2  # content and @bottom-center
    assert len(page_2.children) == 1  # content only
    assert len(page_3.children) == 2  # content and @bottom-center


@assert_no_logs
def test_page_breaks_complex_8():
    page_1, page_2 = render_pages('''
      <style>
        @page { size: 75px; margin: 0 }
        div { height: 20px }
      </style>
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
@pytest.mark.parametrize('break_after, margin_break, margin_top', (
    ('page', 'auto', 5),
    ('auto', 'auto', 0),
    ('page', 'keep', 5),
    ('auto', 'keep', 5),
    ('page', 'discard', 0),
    ('auto', 'discard', 0),
))
def test_margin_break(break_after, margin_break, margin_top):
    page_1, page_2 = render_pages('''
      <style>
        @page { size: 70px; margin: 0 }
        div { height: 63px; margin: 5px 0 8px;
              break-after: %s; margin-break: %s }
      </style>
      <section>
        <div></div>
      </section>
      <section>
        <div></div>
      </section>
    ''' % (break_after, margin_break))
    html, = page_1.children
    body, = html.children
    section, = body.children
    div, = section.children
    assert div.margin_top == 5

    html, = page_2.children
    body, = html.children
    section, = body.children
    div, = section.children
    assert div.margin_top == margin_top


@pytest.mark.xfail
@assert_no_logs
def test_margin_break_clearance():
    page_1, page_2 = render_pages('''
      <style>
        @page { size: 70px; margin: 0 }
        div { height: 63px; margin: 5px 0 8px; break-after: page }
      </style>
      <section>
        <div></div>
      </section>
      <section>
        <div style="border-top: 1px solid black">
          <div></div>
        </div>
      </section>
    ''')
    html, = page_1.children
    body, = html.children
    section, = body.children
    div, = section.children
    assert div.margin_top == 5

    html, = page_2.children
    body, = html.children
    section, = body.children
    div_1, = section.children
    assert div_1.margin_top == 0
    div_2, = div_1.children
    assert div_2.margin_top == 5
    assert div_2.content_box_y() == 5


@assert_no_logs
@pytest.mark.parametrize('direction, page_break, pages_number', (
    ('ltr', 'recto', 3),
    ('ltr', 'verso', 2),
    ('rtl', 'recto', 3),
    ('rtl', 'verso', 2),
    ('ltr', 'right', 3),
    ('ltr', 'left', 2),
    ('rtl', 'right', 2),
    ('rtl', 'left', 3),
))
def test_recto_verso_break(direction, page_break, pages_number):
    pages = render_pages('''
      <style>
        html { direction: %s }
        p { break-before: %s }
      </style>
      abc
      <p>def</p>
    ''' % (direction, page_break))
    assert len(pages) == pages_number


@assert_no_logs
def test_page_names_1():
    pages = render_pages('''
      <style>
        @page { size: 100px 100px }
        section { page: small }
      </style>
      <div>
        <section>large</section>
      </div>
    ''')
    page1, = pages
    assert (page1.width, page1.height) == (100, 100)


@assert_no_logs
def test_page_names_2():
    pages = render_pages('''
      <style>
        @page { size: 100px 100px }
        @page narrow { margin: 1px }
        section { page: small }
      </style>
      <div>
        <section>large</section>
      </div>
    ''')
    page1, = pages
    assert (page1.width, page1.height) == (100, 100)


@assert_no_logs
def test_page_names_3():
    pages = render_pages('''
      <style>
        @page { margin: 0 }
        @page narrow { size: 100px 200px }
        @page large { size: 200px 100px }
        div { page: narrow }
        section { page: large }
      </style>
      <div>
        <section>large</section>
        <section>large</section>
        <p>narrow</p>
      </div>
    ''')
    page1, page2 = pages

    assert (page1.width, page1.height) == (200, 100)
    html, = page1.children
    body, = html.children
    div, = body.children
    section1, section2 = div.children
    assert section1.element_tag == section2.element_tag == 'section'

    assert (page2.width, page2.height) == (100, 200)
    html, = page2.children
    body, = html.children
    div, = body.children
    p, = div.children
    assert p.element_tag == 'p'


@assert_no_logs
def test_page_names_4():
    pages = render_pages('''
      <style>
        @page { size: 200px 200px; margin: 0 }
        @page small { size: 100px 100px }
        p { page: small }
      </style>
      <section>normal</section>
      <section>normal</section>
      <p>small</p>
      <section>small</section>
    ''')
    page1, page2 = pages

    assert (page1.width, page1.height) == (200, 200)
    html, = page1.children
    body, = html.children
    section1, section2 = body.children
    assert section1.element_tag == section2.element_tag == 'section'

    assert (page2.width, page2.height) == (100, 100)
    html, = page2.children
    body, = html.children
    p, section = body.children
    assert p.element_tag == 'p'
    assert section.element_tag == 'section'


@assert_no_logs
def test_page_names_5():
    pages = render_pages('''
      <style>
        @page { size: 200px 200px; margin: 0 }
        @page small { size: 100px 100px }
        div { page: small }
      </style>
      <section><p>a</p>b</section>
      <section>c<div>d</div></section>
    ''')
    page1, page2 = pages

    assert (page1.width, page1.height) == (200, 200)
    html, = page1.children
    body, = html.children
    section1, section2 = body.children
    assert section1.element_tag == section2.element_tag == 'section'
    p, line = section1.children
    line, = section2.children

    assert (page2.width, page2.height) == (100, 100)
    html, = page2.children
    body, = html.children
    section2, = body.children
    div, = section2.children


@assert_no_logs
def test_page_names_6():
    pages = render_pages('''
      <style>
        @page { margin: 0 }
        @page large { size: 200px 200px }
        @page small { size: 100px 100px }
        section { page: large }
        div { page: small }
      </style>
      <section>a<p>b</p>c</section>
      <section>d<div>e</div>f</section>
    ''')
    page1, page2, page3 = pages

    assert (page1.width, page1.height) == (200, 200)
    html, = page1.children
    body, = html.children
    section1, section2 = body.children
    assert section1.element_tag == section2.element_tag == 'section'
    line1, p, line2 = section1.children
    line, = section2.children

    assert (page2.width, page2.height) == (100, 100)
    html, = page2.children
    body, = html.children
    section2, = body.children
    div, = section2.children

    assert (page3.width, page3.height) == (200, 200)
    html, = page3.children
    body, = html.children
    section2, = body.children
    line, = section2.children


@assert_no_logs
def test_page_names_7():
    pages = render_pages('''
      <style>
        @page { size: 200px 200px; margin: 0 }
        @page small { size: 100px 100px }
        p { page: small; break-before: right }
      </style>
      <section>normal</section>
      <section>normal</section>
      <p>small</p>
      <section>small</section>
    ''')
    page1, page2, page3 = pages

    assert (page1.width, page1.height) == (200, 200)
    html, = page1.children
    body, = html.children
    section1, section2 = body.children
    assert section1.element_tag == section2.element_tag == 'section'

    assert (page2.width, page2.height) == (200, 200)
    html, = page2.children
    assert not html.children

    assert (page3.width, page3.height) == (100, 100)
    html, = page3.children
    body, = html.children
    p, section = body.children
    assert p.element_tag == 'p'
    assert section.element_tag == 'section'


@assert_no_logs
def test_page_names_8():
    pages = render_pages('''
      <style>
        @page small { size: 100px 100px }
        section { page: small }
        p { line-height: 80px }
      </style>
      <section>
        <p>small</p>
        <p>small</p>
      </section>
    ''')
    page1, page2 = pages

    assert (page1.width, page1.height) == (100, 100)
    html, = page1.children
    body, = html.children
    section, = body.children
    p, = section.children
    assert section.element_tag == 'section'
    assert p.element_tag == 'p'

    assert (page2.width, page2.height) == (100, 100)
    html, = page2.children
    body, = html.children
    section, = body.children
    p, = section.children
    assert section.element_tag == 'section'
    assert p.element_tag == 'p'


@assert_no_logs
def test_page_names_9():
    pages = render_pages('''
      <style>
        @page { size: 200px 200px }
        @page small { size: 100px 100px }
        section { break-after: page; page: small }
        article { page: small }
      </style>
      <section>
        <div>big</div>
        <div>big</div>
      </section>
      <article>
        <div>small</div>
        <div>small</div>
      </article>
    ''')
    page1, page2, = pages

    assert (page1.width, page1.height) == (100, 100)
    html, = page1.children
    body, = html.children
    section, = body.children
    assert section.element_tag == 'section'

    assert (page2.width, page2.height) == (100, 100)
    html, = page2.children
    body, = html.children
    article, = body.children
    assert article.element_tag == 'article'


@assert_no_logs
@pytest.mark.parametrize('style, line_counts', (
    ('orphans: 2; widows: 2', [4, 3]),
    ('orphans: 5; widows: 2', [0, 7]),
    ('orphans: 2; widows: 4', [3, 4]),
    ('orphans: 4; widows: 4', [0, 7]),
    ('orphans: 2; widows: 2; page-break-inside: avoid', [0, 7]),
))
def test_orphans_widows_avoid(style, line_counts):
    pages = render_pages('''
      <style>
        @page { size: 200px }
        h1 { height: 120px }
        p { line-height: 20px;
            width: 1px; /* line break at each word */
            %s }
      </style>
      <h1>Tasty test</h1>
      <!-- There is room for 4 lines after h1 on the fist page -->
      <p>one two three four five six seven</p>
    ''' % style)
    for i, page in enumerate(pages):
        html, = page.children
        body, = html.children
        body_children = body.children if i else body.children[1:]  # skip h1
        count = len(body_children[0].children) if body_children else 0
        assert line_counts.pop(0) == count
    assert not line_counts


@assert_no_logs
def test_page_and_linebox_breaking():
    # Empty <span/> tests a corner case in skip_first_whitespace()
    pages = render_pages('''
      <style>
        @font-face { src: url(AHEM____.TTF); font-family: ahem }
        @page { size: 100px; margin: 2px; border: 1px solid }
        body { margin: 0 }
        div { font-family: ahem; font-size: 20px }
      </style>
      <div><span/>1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15</div>
    ''')
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
    assert len(pages) == 4
    assert ''.join(texts) == '1,2,3,4,5,6,7,8,9,10,11,12,13,14,15'


@assert_no_logs
def test_margin_boxes_fixed_dimension_1():
    # Corner boxes
    page, = render_pages('''
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


@assert_no_logs
def test_margin_boxes_fixed_dimension_2():
    # Test rules 2 and 3
    page, = render_pages('''
      <style>
        @page {
          margin: 100px 200px;
          @bottom-left-corner { content: ""; margin: 60px }
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


@assert_no_logs
def test_margin_boxes_fixed_dimension_3():
    # Test rule 3 with a non-auto inner dimension
    page, = render_pages('''
      <style>
        @page {
          margin: 100px;
          @left-middle { content: ""; margin: 10px; width: 130px }
        }
      </style>
    ''')
    html, margin_box = page.children
    assert margin_box.margin_width() == 100
    assert margin_box.margin_left == -40  # Not 10px
    assert margin_box.margin_right == 10
    assert margin_box.width == 130  # As specified


@assert_no_logs
def test_margin_boxes_fixed_dimension_4():
    # Test rule 4
    page, = render_pages('''
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


@assert_no_logs
def test_margin_boxes_fixed_dimension_5():
    # Test rules 2, 3 and 4
    page, = render_pages('''
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


@assert_no_logs
def test_margin_boxes_fixed_dimension_6():
    # Test rule 5
    page, = render_pages('''
      <style>
        @page {
          margin: 100px;
          @top-left { content: ""; margin-top: 10px; margin-bottom: auto }
        }
      </style>
    ''')
    html, margin_box = page.children
    assert margin_box.margin_height() == 100
    assert margin_box.margin_top == 10
    assert margin_box.margin_bottom == 0
    assert margin_box.height == 90


@assert_no_logs
def test_margin_boxes_fixed_dimension_7():
    # Test rule 5
    page, = render_pages('''
      <style>
        @page {
          margin: 100px;
          @top-center { content: ""; margin: auto 0 }
        }
      </style>
    ''')
    html, margin_box = page.children
    assert margin_box.margin_height() == 100
    assert margin_box.margin_top == 0
    assert margin_box.margin_bottom == 0
    assert margin_box.height == 100


@assert_no_logs
def test_margin_boxes_fixed_dimension_8():
    # Test rule 6
    page, = render_pages('''
      <style>
        @page {
          margin: 100px;
          @bottom-right { content: ""; margin: auto; height: 70px }
        }
      </style>
    ''')
    html, margin_box = page.children
    assert margin_box.margin_height() == 100
    assert margin_box.margin_top == 15
    assert margin_box.margin_bottom == 15
    assert margin_box.height == 70


@assert_no_logs
def test_margin_boxes_fixed_dimension_9():
    # Rule 2 inhibits rule 6
    page, = render_pages('''
      <style>
        @page {
          margin: 100px;
          @bottom-center { content: ""; margin: auto 0; height: 150px }
        }
      </style>
    ''')
    html, margin_box = page.children
    assert margin_box.margin_height() == 100
    assert margin_box.margin_top == 0
    assert margin_box.margin_bottom == -50  # outside
    assert margin_box.height == 150


def images(*widths):
    return ' '.join(
        'url(\'data:image/svg+xml,<svg width="%i" height="10"></svg>\')'
        % width for width in widths)


@assert_no_logs
@pytest.mark.parametrize('css, widths', (
    ('''@top-left { content: %s }
        @top-center { content: %s }
        @top-right { content: %s }
     ''' % (images(50, 50), images(50, 50), images(50, 50)),
     [100, 100, 100]),  # Use preferred widths if they fit
    ('''@top-left { content: %s; margin: auto }
        @top-center { content: %s }
        @top-right { content: %s }
     ''' % (images(50, 50), images(50, 50), images(50, 50)),
     [100, 100, 100]),  # 'auto' margins are set to 0
    ('''@top-left { content: %s }
        @top-center { content: %s }
        @top-right { content: 'foo'; width: 200px }
     ''' % (images(100, 50), images(300, 150)),
     [150, 300, 200]),  # Use at least minimum widths, even if boxes overlap
    ('''@top-left { content: %s }
        @top-center { content: %s }
        @top-right { content: %s }
     ''' % (images(150, 150), images(150, 150), images(150, 150)),
     [200, 200, 200]),  # Distribute remaining space proportionally
    ('''@top-left { content: %s }
        @top-center { content: %s }
        @top-right { content: %s }
     ''' % (images(100, 100, 100), images(100, 100), images(10)),
     [220, 160, 10]),
    ('''@top-left { content: %s; width: 205px }
        @top-center { content: %s }
        @top-right { content: %s }
     ''' % (images(100, 100, 100), images(100, 100), images(10)),
     [205, 190, 10]),
    ('''@top-left { width: 1000px; margin: 1000px; padding: 1000px;
                    border: 1000px solid }
        @top-center { content: %s }
        @top-right { content: %s }
     ''' % (images(100, 100), images(10)),
     [200, 10]),  # 'width' and other have no effect without 'content'
    ('''@top-left { content: ''; width: 200px }
        @top-center { content: ''; width: 300px }
        @top-right { content: %s }
     ''' % images(50, 50),  # This leaves 150px for @top-right’s shrink-to-fit
     [200, 300, 100]),
    ('''@top-left { content: ''; width: 200px }
        @top-center { content: ''; width: 300px }
        @top-right { content: %s }
     ''' % images(100, 100, 100),
     [200, 300, 150]),
    ('''@top-left { content: ''; width: 200px }
        @top-center { content: ''; width: 300px }
        @top-right { content: %s }
     ''' % images(170, 175),
     [200, 300, 175]),
    ('''@top-left { content: ''; width: 200px }
        @top-center { content: ''; width: 300px }
        @top-right { content: %s }
     ''' % images(170, 175),
     [200, 300, 175]),
    ('''@top-left { content: ''; width: 200px }
        @top-right { content: ''; width: 500px }
     ''',
     [200, 500]),
    ('''@top-left { content: ''; width: 200px }
        @top-right { content: %s }
     ''' % images(150, 50, 150),
     [200, 350]),
    ('''@top-left { content: ''; width: 200px }
        @top-right { content: %s }
     ''' % images(150, 50, 150, 200),
     [200, 400]),
    ('''@top-left { content: %s }
        @top-right { content: ''; width: 200px }
     ''' % images(150, 50, 450),
     [450, 200]),
    ('''@top-left { content: %s }
        @top-right { content: %s }
     ''' % (images(150, 100), images(10, 120)),
     [250, 130]),
    ('''@top-left { content: %s }
        @top-right { content: %s }
     ''' % (images(550, 100), images(10, 120)),
     [550, 120]),
    ('''@top-left { content: %s }
        @top-right { content: %s }
     ''' % (images(250, 60), images(250, 180)),
     [275, 325]),  # 250 + (100 * 1 / 4), 250 + (100 * 3 / 4)
))
def test_page_style(css, widths):
    expected_at_keywords = [
        at_keyword for at_keyword in [
            '@top-left', '@top-center', '@top-right']
        if at_keyword + ' { content: ' in css]
    page, = render_pages('''
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
    assert [box.margin_width() for box in margin_boxes] == widths


@assert_no_logs
def test_margin_boxes_vertical_align():
    # 3 px ->    +-----+
    #            |  1  |
    #            +-----+
    #
    #        43 px ->   +-----+
    #        53 px ->   |  2  |
    #                   +-----+
    #
    #               83 px ->   +-----+
    #                          |  3  |
    #               103px ->   +-----+
    page, = render_pages('''
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
def test_margin_boxes_element():
    pages = render_pages('''
      <style>
        footer {
          position: running(footer);
        }
        @page {
          margin: 50px;
          size: 200px;
          @bottom-center {
            content: element(footer);
          }
        }
        h1 {
          height: 40px;
        }
        .pages:before {
          content: counter(page);
        }
        .pages:after {
          content: counter(pages);
        }
      </style>
      <footer class="pages"> of </footer>
      <h1>test1</h1>
      <h1>test2</h1>
      <h1>test3</h1>
      <h1>test4</h1>
      <h1>test5</h1>
      <h1>test6</h1>
      <footer>Static</footer>
    ''')
    footer1_text = ''.join(
        getattr(node, 'text', '')
        for node in pages[0].children[1].descendants())
    assert footer1_text == '1 of 3'

    footer2_text = ''.join(
        getattr(node, 'text', '')
        for node in pages[1].children[1].descendants())
    assert footer2_text == '2 of 3'

    footer3_text = ''.join(
        getattr(node, 'text', '')
        for node in pages[2].children[1].descendants())
    assert footer3_text == 'Static'


@assert_no_logs
@pytest.mark.parametrize('argument, texts', (
    # TODO: start doesn’t work because running elements are removed from the
    # original tree, and the current implentation in
    # layout.get_running_element_for uses the tree to know if it’s at the
    # beginning of the page

    # ('start', ('', '2-first', '2-last', '3-last', '5')),

    ('first', ('', '2-first', '3-first', '3-last', '5')),
    ('last', ('', '2-last', '3-last', '3-last', '5')),
    ('first-except', ('', '', '', '3-last', '')),
))
def test_running_elements(argument, texts):
    pages = render_pages('''
      <style>
        @page {
          margin: 50px;
          size: 200px;
          @bottom-center { content: element(title %s) }
        }
        article { break-after: page }
        h1 { position: running(title) }
      </style>
      <article>
        <div>1</div>
      </article>
      <article>
        <h1>2-first</h1>
        <h1>2-last</h1>
      </article>
      <article>
        <p>3</p>
        <h1>3-first</h1>
        <h1>3-last</h1>
      </article>
      <article>
      </article>
      <article>
        <h1>5</h1>
      </article>
    ''' % argument)
    assert len(pages) == 5
    for page, text in zip(pages, texts):
        html, margin = page.children
        if margin.children:
            h1, = margin.children
            line, = h1.children
            textbox, = line.children
            assert textbox.text == text
        else:
            assert not text


@assert_no_logs
def test_running_elements_display():
    page, = render_pages('''
      <style>
        @page {
          margin: 50px;
          size: 200px;
          @bottom-left { content: element(inline) }
          @bottom-center { content: element(block) }
          @bottom-right { content: element(table) }
        }
        table { position: running(table) }
        div { position: running(block) }
        span { position: running(inline) }
      </style>
      text
      <table><tr><td>table</td></tr></table>
      <div>block</div>
      <span>inline</span>
    ''')
    html, left, center, right = page.children
    assert ''.join(
        getattr(node, 'text', '') for node in left.descendants()) == 'inline'
    assert ''.join(
        getattr(node, 'text', '') for node in center.descendants()) == 'block'
    assert ''.join(
        getattr(node, 'text', '') for node in right.descendants()) == 'table'
