"""
    weasyprint.tests.layout.position
    --------------------------------

    Tests for position property.

"""

from ..testing_utils import assert_no_logs, render_pages


@assert_no_logs
def test_relative_positioning_1():
    page, = render_pages('''
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


@assert_no_logs
def test_relative_positioning_2():
    page, = render_pages('''
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
def test_absolute_positioning_1():
    page, = render_pages('''
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


@assert_no_logs
def test_absolute_positioning_2():
    page, = render_pages('''
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


@assert_no_logs
def test_absolute_positioning_3():
    page, = render_pages('''
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


@assert_no_logs
def test_absolute_positioning_4():
    page, = render_pages('''
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


@assert_no_logs
def test_absolute_positioning_5():
    page, = render_pages('''
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


@assert_no_logs
def test_absolute_positioning_6():
    page, = render_pages('''
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


@assert_no_logs
def test_absolute_positioning_7():
    page, = render_pages('''
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
def test_absolute_positioning_8():
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/1264
    page, = render_pages('''
      <style>@page{ width: 50px; height: 50px }</style>
      <body style="font-size: 0">
        <div style="position: absolute; margin: auto;
                    left: 0; right: 10px;
                    top: 0; bottom: 10px;
                    width: 10px; height: 20px">
    ''')
    html, = page.children
    body, = html.children
    div, = body.children
    assert (div.content_box_x(), div.content_box_y()) == (15, 10)
    assert (div.width, div.height) == (10, 20)


@assert_no_logs
def test_absolute_images():
    page, = render_pages('''
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
    page_1, page_2, page_3 = render_pages('''
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
def test_fixed_positioning_regression_1():
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/641
    page_1, page_2 = render_pages('''
      <style>
        @page:first { size: 100px 200px }
        @page { size: 200px 100px; margin: 0 }
        article { break-after: page }
        .fixed { position: fixed; top: 10px; width: 20px }
      </style>
      <ul class="fixed" style="right: 0"><li>a</li></ul>
      <img class="fixed" style="right: 20px" src="pattern.png" />
      <div class="fixed" style="right: 40px">b</div>
      <article>page1</article>
      <article>page2</article>
    ''')

    html, = page_1.children
    body, = html.children
    ul, img, div, article = body.children
    marker = ul.children[0]
    assert (ul.position_x, ul.position_y) == (80, 10)
    assert (img.position_x, img.position_y) == (60, 10)
    assert (div.position_x, div.position_y) == (40, 10)
    assert (article.position_x, article.position_y) == (0, 0)
    assert marker.position_x == ul.position_x

    html, = page_2.children
    ul, img, div, body = html.children
    marker = ul.children[0]
    assert (ul.position_x, ul.position_y) == (180, 10)
    assert (img.position_x, img.position_y) == (160, 10)
    assert (div.position_x, div.position_y) == (140, 10)
    assert (article.position_x, article.position_y) == (0, 0)
    assert marker.position_x == ul.position_x


@assert_no_logs
def test_fixed_positioning_regression_2():
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/728
    page_1, page_2 = render_pages('''
      <style>
        @page { size: 100px 100px }
        section { break-after: page }
        .fixed { position: fixed; top: 10px; left: 15px; width: 20px }
      </style>
      <div class="fixed">
        <article class="fixed" style="top: 20px">
          <header class="fixed" style="left: 5px"></header>
        </article>
      </div>
      <section></section>
      <pre></pre>
    ''')
    html, = page_1.children
    body, = html.children
    div, section = body.children
    assert (div.position_x, div.position_y) == (15, 10)
    article, = div.children
    assert (article.position_x, article.position_y) == (15, 20)
    header, = article.children
    assert (header.position_x, header.position_y) == (5, 10)

    html, = page_2.children
    div, body, = html.children
    assert (div.position_x, div.position_y) == (15, 10)
    article, = div.children
    assert (article.position_x, article.position_y) == (15, 20)
    header, = article.children
    assert (header.position_x, header.position_y) == (5, 10)
