# coding: utf-8
"""
    weasyprint.tests.layout
    -----------------------

    Tests for floating boxes layout.

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""


from __future__ import division, unicode_literals

from ..formatting_structure import boxes
from .test_boxes import render_pages as parse
from .testing_utils import assert_no_logs


def outer_area(box):
    """Return the (x, y, w, h) rectangle for the outer area of a box."""
    return (box.position_x, box.position_y,
            box.margin_width(), box.margin_height())


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

    # Regression test
    # https://github.com/Kozea/WeasyPrint/issues/263
    page, = parse('''<div style="top:100%; float:left">''')


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

    # last float does not fit, pushed to next page
    pages = parse('''
        <style>
            @page{
                size: 110px;
                margin: 10px;
                padding: 0;
            }
            .large {
                width: 10px;
                height: 60px;
            }
            .small {
                width: 10px;
                height: 20px;
            }
        </style>
        <body>
            <div class="large"></div>
            <div class="small"></div>
            <div class="large"></div>
    ''')

    assert len(pages) == 2
    page_divs = []
    for page in pages:
        divs = [div for div in page.descendants() if div.element_tag == 'div']
        assert all([div.element_tag == 'div' for div in divs])
        page_divs.append(divs)
        del divs

    positions_y = [[div.position_y for div in divs] for divs in page_divs]
    assert positions_y == [[10, 70], [10]]

    # last float does not fit, pushed to next page
    # center div must not
    pages = parse('''
        <style>
            @page{
                size: 110px;
                margin: 10px;
                padding: 0;
            }
            .large {
                width: 10px;
                height: 60px;
            }
            .small {
                width: 10px;
                height: 20px;
                page-break-after: avoid;
            }
        </style>
        <body>
            <div class="large"></div>
            <div class="small"></div>
            <div class="large"></div>
    ''')

    assert len(pages) == 2
    page_divs = []
    for page in pages:
        divs = [div for div in page.descendants() if div.element_tag == 'div']
        assert all([div.element_tag == 'div' for div in divs])
        page_divs.append(divs)
        del divs

    positions_y = [[div.position_y for div in divs] for divs in page_divs]
    assert positions_y == [[10], [10, 30]]

    # center div must be the last element,
    # but float won't fit and will get pushed anyway
    pages = parse('''
        <style>
            @page{
                size: 110px;
                margin: 10px;
                padding: 0;
            }
            .large {
                width: 10px;
                height: 80px;
            }
            .small {
                width: 10px;
                height: 20px;
                page-break-after: avoid;
            }
        </style>
        <body>
            <div class="large"></div>
            <div class="small"></div>
            <div class="large"></div>
    ''')

    assert len(pages) == 3
    page_divs = []
    for page in pages:
        divs = [div for div in page.descendants() if div.element_tag == 'div']
        assert all([div.element_tag == 'div' for div in divs])
        page_divs.append(divs)
        del divs

    positions_y = [[div.position_y for div in divs] for divs in page_divs]
    assert positions_y == [[10], [10], [10]]


@assert_no_logs
def test_preferred_widths():
    """Unit tests for preferred widths."""
    def get_float_width(body_width):
        page, = parse('''
            <body style="width: %spx; font-family: ahem">
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
    # Preferred minimum width:
    assert get_float_width(10) == len('consectetur elit') * 16
    # Preferred width:
    assert get_float_width(1000000) == len('Lorem ipsum dolor sit amet,') * 16

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
