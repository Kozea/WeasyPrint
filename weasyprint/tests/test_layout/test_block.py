"""
    weasyprint.tests.layout.block
    -----------------------------

    Tests for blocks layout.

"""

import pytest

from ...formatting_structure import boxes
from ..test_boxes import render_pages as parse
from ..testing_utils import assert_no_logs


@assert_no_logs
def test_block_widths():
    page, = parse('''
      <style>
        @page { margin: 0; size: 120px 2000px }
        body { margin: 0 }
        div { margin: 10px }
        p { padding: 2px; border-width: 1px; border-style: solid }
      </style>
      <div>
        <p></p>
        <p style="width: 50px"></p>
      </div>
      <div style="direction: rtl">
        <p style="width: 50px; direction: rtl"></p>
      </div>
      <div>
        <p style="margin: 0 10px 0 20px"></p>
        <p style="width: 50px; margin-left: 20px; margin-right: auto"></p>
        <p style="width: 50px; margin-left: auto; margin-right: 20px"></p>
        <p style="width: 50px; margin: auto"></p>

        <p style="margin-left: 20px; margin-right: auto"></p>
        <p style="margin-left: auto; margin-right: 20px"></p>
        <p style="margin: auto"></p>

        <p style="width: 200px; margin: auto"></p>

        <p style="min-width: 200px; margin: auto"></p>
        <p style="max-width: 50px; margin: auto"></p>
        <p style="min-width: 50px; margin: auto"></p>

        <p style="width: 70%"></p>
      </div>
    ''')
    html, = page.children
    assert html.element_tag == 'html'
    body, = html.children
    assert body.element_tag == 'body'
    assert body.width == 120

    divs = body.children

    paragraphs = []
    for div in divs:
        assert isinstance(div, boxes.BlockBox)
        assert div.element_tag == 'div'
        assert div.width == 100
        for paragraph in div.children:
            assert isinstance(paragraph, boxes.BlockBox)
            assert paragraph.element_tag == 'p'
            assert paragraph.padding_left == 2
            assert paragraph.padding_right == 2
            assert paragraph.border_left_width == 1
            assert paragraph.border_right_width == 1
            paragraphs.append(paragraph)

    assert len(paragraphs) == 15

    # width is 'auto'
    assert paragraphs[0].width == 94
    assert paragraphs[0].margin_left == 0
    assert paragraphs[0].margin_right == 0

    # No 'auto', over-constrained equation with ltr, the initial
    # 'margin-right: 0' was ignored.
    assert paragraphs[1].width == 50
    assert paragraphs[1].margin_left == 0

    # No 'auto', over-constrained equation with rtl, the initial
    # 'margin-left: 0' was ignored.
    assert paragraphs[2].width == 50
    assert paragraphs[2].margin_right == 0

    # width is 'auto'
    assert paragraphs[3].width == 64
    assert paragraphs[3].margin_left == 20

    # margin-right is 'auto'
    assert paragraphs[4].width == 50
    assert paragraphs[4].margin_left == 20

    # margin-left is 'auto'
    assert paragraphs[5].width == 50
    assert paragraphs[5].margin_left == 24

    # Both margins are 'auto', remaining space is split in half
    assert paragraphs[6].width == 50
    assert paragraphs[6].margin_left == 22

    # width is 'auto', other 'auto' are set to 0
    assert paragraphs[7].width == 74
    assert paragraphs[7].margin_left == 20

    # width is 'auto', other 'auto' are set to 0
    assert paragraphs[8].width == 74
    assert paragraphs[8].margin_left == 0

    # width is 'auto', other 'auto' are set to 0
    assert paragraphs[9].width == 94
    assert paragraphs[9].margin_left == 0

    # sum of non-auto initially is too wide, set auto values to 0
    assert paragraphs[10].width == 200
    assert paragraphs[10].margin_left == 0

    # Constrained by min-width, same as above
    assert paragraphs[11].width == 200
    assert paragraphs[11].margin_left == 0

    # Constrained by max-width, same as paragraphs[6]
    assert paragraphs[12].width == 50
    assert paragraphs[12].margin_left == 22

    # NOT constrained by min-width
    assert paragraphs[13].width == 94
    assert paragraphs[13].margin_left == 0

    # 70%
    assert paragraphs[14].width == 70
    assert paragraphs[14].margin_left == 0


@assert_no_logs
def test_block_heights_p():
    page, = parse('''
      <style>
        @page { margin: 0; size: 100px 20000px }
        html, body { margin: 0 }
        div { margin: 4px; border: 2px solid; padding: 4px }
        /* Use top margins so that margin collapsing doesn't change result */
        p { margin: 16px 0 0; border: 4px solid; padding: 8px; height: 50px }
      </style>
      <div>
        <p></p>
        <!-- Not in normal flow: don't contribute to the parent’s height -->
        <p style="position: absolute"></p>
        <p style="float: left"></p>
      </div>
      <div> <p></p> <p></p> <p></p> </div>
      <div style="height: 20px"> <p></p> </div>
      <div style="height: 120px"> <p></p> </div>
      <div style="max-height: 20px"> <p></p> </div>
      <div style="min-height: 120px"> <p></p> </div>
      <div style="min-height: 20px"> <p></p> </div>
      <div style="max-height: 120px"> <p></p> </div>
    ''')
    html, = page.children
    body, = html.children
    heights = [div.height for div in body.children]
    assert heights == [90, 90 * 3, 20, 120, 20, 120, 90, 90]


@assert_no_logs
def test_block_heights_img():
    page, = parse('''
      <style>
        body { height: 200px; font-size: 0 }
      </style>
      <div>
        <img src=pattern.png style="height: 40px">
      </div>
      <div style="height: 10%">
        <img src=pattern.png style="height: 40px">
      </div>
      <div style="max-height: 20px">
        <img src=pattern.png style="height: 40px">
      </div>
      <div style="max-height: 10%">
        <img src=pattern.png style="height: 40px">
      </div>
      <div style="min-height: 20px"></div>
      <div style="min-height: 10%"></div>
    ''')
    html, = page.children
    body, = html.children
    heights = [div.height for div in body.children]
    assert heights == [40, 20, 20, 20, 20, 20]


@assert_no_logs
def test_block_heights_img_no_body_height():
    # Same but with no height on body: percentage *-height is ignored
    page, = parse('''
      <style>
        body { font-size: 0 }
      </style>
        <div>
          <img src=pattern.png style="height: 40px">
        </div>
        <div style="height: 10%">
          <img src=pattern.png style="height: 40px">
        </div>
        <div style="max-height: 20px">
          <img src=pattern.png style="height: 40px">
        </div>
        <div style="max-height: 10%">
          <img src=pattern.png style="height: 40px">
        </div>
        <div style="min-height: 20px"></div>
        <div style="min-height: 10%"></div>
    ''')
    html, = page.children
    body, = html.children
    heights = [div.height for div in body.children]
    assert heights == [40, 40, 20, 40, 20, 0]


@assert_no_logs
def test_block_percentage_heights_no_html_height():
    page, = parse('''
      <style>
        html, body { margin: 0 }
        body { height: 50% }
      </style>
    ''')
    html, = page.children
    assert html.element_tag == 'html'
    body, = html.children
    assert body.element_tag == 'body'

    # Since html’s height depend on body’s, body’s 50% means 'auto'
    assert body.height == 0


@assert_no_logs
def test_block_percentage_heights():
    page, = parse('''
      <style>
        html, body { margin: 0 }
        html { height: 300px }
        body { height: 50% }
      </style>
    ''')
    html, = page.children
    assert html.element_tag == 'html'
    body, = html.children
    assert body.element_tag == 'body'

    # This time the percentage makes sense
    assert body.height == 150


@assert_no_logs
@pytest.mark.parametrize('size', (
    ('width: 10%; height: 1000px',),
    ('max-width: 10%; max-height: 1000px; height: 2000px',),
    ('width: 5%; min-width: 10%; min-height: 1000px',),
    ('width: 10%; height: 1000px; min-width: auto; max-height: none',),
))
def test_box_sizing(size):
    # http://www.w3.org/TR/css3-ui/#box-sizing
    page, = parse('''
      <style>
        @page { size: 100000px }
        body { width: 10000px; margin: 0 }
        div { %s; margin: 100px; padding: 10px; border: 1px solid }
      </style>
      <div></div>

      <div style="box-sizing: content-box"></div>
      <div style="box-sizing: padding-box"></div>
      <div style="box-sizing: border-box"></div>
    ''' % size)
    html, = page.children
    body, = html.children
    div_1, div_2, div_3, div_4 = body.children
    for div in div_1, div_2:
        assert div.style['box_sizing'] == 'content-box'
        assert div.width == 1000
        assert div.height == 1000
        assert div.padding_width() == 1020
        assert div.padding_height() == 1020
        assert div.border_width() == 1022
        assert div.border_height() == 1022
        assert div.margin_height() == 1222
        # margin_width() is the width of the containing block

    # padding-box
    assert div_3.style['box_sizing'] == 'padding-box'
    assert div_3.width == 980  # 1000 - 20
    assert div_3.height == 980
    assert div_3.padding_width() == 1000
    assert div_3.padding_height() == 1000
    assert div_3.border_width() == 1002
    assert div_3.border_height() == 1002
    assert div_3.margin_height() == 1202

    # border-box
    assert div_4.style['box_sizing'] == 'border-box'
    assert div_4.width == 978  # 1000 - 20 - 2
    assert div_4.height == 978
    assert div_4.padding_width() == 998
    assert div_4.padding_height() == 998
    assert div_4.border_width() == 1000
    assert div_4.border_height() == 1000
    assert div_4.margin_height() == 1200


@assert_no_logs
@pytest.mark.parametrize('size', (
    ('width: 0; height: 0'),
    ('max-width: 0; max-height: 0'),
    ('min-width: 0; min-height: 0; width: 0; height: 0'),
))
def test_box_sizing_zero(size):
    # http://www.w3.org/TR/css3-ui/#box-sizing
    page, = parse('''
      <style>
        @page { size: 100000px }
        body { width: 10000px; margin: 0 }
        div { %s; margin: 100px; padding: 10px; border: 1px solid }
      </style>
      <div></div>

      <div style="box-sizing: content-box"></div>
      <div style="box-sizing: padding-box"></div>
      <div style="box-sizing: border-box"></div>
    ''' % size)
    html, = page.children
    body, = html.children
    for div in body.children:
        assert div.width == 0
        assert div.height == 0
        assert div.padding_width() == 20
        assert div.padding_height() == 20
        assert div.border_width() == 22
        assert div.border_height() == 22
        assert div.margin_height() == 222
        # margin_width() is the width of the containing block


COLLAPSING = (
    ('10px', '15px', 15),  # not 25
    # "The maximum of the absolute values of the negative adjoining margins is
    # deducted from the maximum of the positive adjoining margins"
    ('-10px', '15px', 5),
    ('10px', '-15px', -5),
    ('-10px', '-15px', -15),
    ('10px', 'auto', 10),  # 'auto' is 0
)
NOT_COLLAPSING = (
    ('10px', '15px', 25),
    ('-10px', '15px', 5),
    ('10px', '-15px', -5),
    ('-10px', '-15px', -25),
    ('10px', 'auto', 10),  # 'auto' is 0
)


@pytest.mark.parametrize('margin_1, margin_2, result', COLLAPSING)
def test_vertical_space_1(margin_1, margin_2, result):
    # Siblings
    page, = parse('''
      <style>
        p { font: 20px/1 serif } /* block height == 20px */
        #p1 { margin-bottom: %s }
        #p2 { margin-top: %s }
      </style>
      <p id=p1>Lorem ipsum
      <p id=p2>dolor sit amet
    ''' % (margin_1, margin_2))
    html, = page.children
    body, = html.children
    p1, p2 = body.children
    p1_bottom = p1.content_box_y() + p1.height
    p2_top = p2.content_box_y()
    assert p2_top - p1_bottom == result


@pytest.mark.parametrize('margin_1, margin_2, result', COLLAPSING)
def test_vertical_space_2(margin_1, margin_2, result):
    # Not siblings, first is nested
    page, = parse('''
      <style>
        p { font: 20px/1 serif } /* block height == 20px */
        #p1 { margin-bottom: %s }
        #p2 { margin-top: %s }
      </style>
      <div>
        <p id=p1>Lorem ipsum
      </div>
      <p id=p2>dolor sit amet
    ''' % (margin_1, margin_2))
    html, = page.children
    body, = html.children
    div, p2 = body.children
    p1, = div.children
    p1_bottom = p1.content_box_y() + p1.height
    p2_top = p2.content_box_y()
    assert p2_top - p1_bottom == result


@pytest.mark.parametrize('margin_1, margin_2, result', COLLAPSING)
def test_vertical_space_3(margin_1, margin_2, result):
    # Not siblings, second is nested
    page, = parse('''
      <style>
        p { font: 20px/1 serif } /* block height == 20px */
        #p1 { margin-bottom: %s }
        #p2 { margin-top: %s }
      </style>
      <p id=p1>Lorem ipsum
      <div>
        <p id=p2>dolor sit amet
      </div>
    ''' % (margin_1, margin_2))
    html, = page.children
    body, = html.children
    p1, div = body.children
    p2, = div.children
    p1_bottom = p1.content_box_y() + p1.height
    p2_top = p2.content_box_y()
    assert p2_top - p1_bottom == result


@pytest.mark.parametrize('margin_1, margin_2, result', COLLAPSING)
def test_vertical_space_4(margin_1, margin_2, result):
    # Not siblings, second is doubly nested
    page, = parse('''
      <style>
        p { font: 20px/1 serif } /* block height == 20px */
        #p1 { margin-bottom: %s }
        #p2 { margin-top: %s }
      </style>
      <p id=p1>Lorem ipsum
      <div>
        <div>
            <p id=p2>dolor sit amet
        </div>
      </div>
    ''' % (margin_1, margin_2))
    html, = page.children
    body, = html.children
    p1, div1 = body.children
    div2, = div1.children
    p2, = div2.children
    p1_bottom = p1.content_box_y() + p1.height
    p2_top = p2.content_box_y()
    assert p2_top - p1_bottom == result


@pytest.mark.parametrize('margin_1, margin_2, result', COLLAPSING)
def test_vertical_space_5(margin_1, margin_2, result):
    # Collapsing with children
    page, = parse('''
      <style>
        p { font: 20px/1 serif } /* block height == 20px */
        #div1 { margin-top: %s }
        #div2 { margin-top: %s }
      </style>
      <p>Lorem ipsum
      <div id=div1>
        <div id=div2>
          <p id=p2>dolor sit amet
        </div>
      </div>
    ''' % (margin_1, margin_2))
    html, = page.children
    body, = html.children
    p1, div1 = body.children
    div2, = div1.children
    p2, = div2.children
    p1_bottom = p1.content_box_y() + p1.height
    p2_top = p2.content_box_y()
    # Parent and element edge are the same:
    assert div1.border_box_y() == p2.border_box_y()
    assert div2.border_box_y() == p2.border_box_y()
    assert p2_top - p1_bottom == result


@pytest.mark.parametrize('margin_1, margin_2, result', NOT_COLLAPSING)
def test_vertical_space_6(margin_1, margin_2, result):
    # Block formatting context: Not collapsing with children
    page, = parse('''
      <style>
        p { font: 20px/1 serif } /* block height == 20px */
        #div1 { margin-top: %s; overflow: hidden }
        #div2 { margin-top: %s }
      </style>
      <p>Lorem ipsum
      <div id=div1>
        <div id=div2>
          <p id=p2>dolor sit amet
        </div>
      </div>
    ''' % (margin_1, margin_2))
    html, = page.children
    body, = html.children
    p1, div1 = body.children
    div2, = div1.children
    p2, = div2.children
    p1_bottom = p1.content_box_y() + p1.height
    p2_top = p2.content_box_y()
    assert p2_top - p1_bottom == result


@pytest.mark.parametrize('margin_1, margin_2, result', COLLAPSING)
def test_vertical_space_7(margin_1, margin_2, result):
    # Collapsing through an empty div
    page, = parse('''
      <style>
        p { font: 20px/1 serif } /* block height == 20px */
        #p1 { margin-bottom: %s }
        #p2 { margin-top: %s }
        div { margin-bottom: %s; margin-top: %s }
      </style>
      <p id=p1>Lorem ipsum
      <div></div>
      <p id=p2>dolor sit amet
    ''' % (2 * (margin_1, margin_2)))
    html, = page.children
    body, = html.children
    p1, div, p2 = body.children
    p1_bottom = p1.content_box_y() + p1.height
    p2_top = p2.content_box_y()
    assert p2_top - p1_bottom == result


@pytest.mark.parametrize('margin_1, margin_2, result', NOT_COLLAPSING)
def test_vertical_space_8(margin_1, margin_2, result):
    # The root element does not collapse
    page, = parse('''
      <style>
        html { margin-top: %s }
        body { margin-top: %s }
      </style>
      <p>Lorem ipsum
    ''' % (margin_1, margin_2))
    html, = page.children
    body, = html.children
    p1, = body.children
    p1_top = p1.content_box_y()
    # Vertical space from y=0
    assert p1_top == result


@pytest.mark.parametrize('margin_1, margin_2, result', COLLAPSING)
def test_vertical_space_9(margin_1, margin_2, result):
    # <body> DOES collapse
    page, = parse('''
      <style>
        body { margin-top: %s }
        div { margin-top: %s }
      </style>
      <div>
        <p>Lorem ipsum
    ''' % (margin_1, margin_2))
    html, = page.children
    body, = html.children
    div, = body.children
    p1, = div.children
    p1_top = p1.content_box_y()
    # Vertical space from y=0
    assert p1_top == result


@assert_no_logs
def test_box_decoration_break_block_slice():
    # http://www.w3.org/TR/css3-background/#the-box-decoration-break
    page_1, page_2 = parse('''
      <style>
        @page { size: 100px }
        p { padding: 2px; border: 3px solid; margin: 5px }
        img { display: block; height: 40px }
      </style>
      <p>
        <img src=pattern.png>
        <img src=pattern.png>
        <img src=pattern.png>
        <img src=pattern.png>''')
    html, = page_1.children
    body, = html.children
    paragraph, = body.children
    img_1, img_2 = paragraph.children
    assert paragraph.position_y == 0
    assert paragraph.margin_top == 5
    assert paragraph.border_top_width == 3
    assert paragraph.padding_top == 2
    assert paragraph.content_box_y() == 10
    assert img_1.position_y == 10
    assert img_2.position_y == 50
    assert paragraph.height == 90
    assert paragraph.margin_bottom == 0
    assert paragraph.border_bottom_width == 0
    assert paragraph.padding_bottom == 0
    assert paragraph.margin_height() == 100

    html, = page_2.children
    body, = html.children
    paragraph, = body.children
    img_1, img_2 = paragraph.children
    assert paragraph.position_y == 0
    assert paragraph.margin_top == 0
    assert paragraph.border_top_width == 0
    assert paragraph.padding_top == 0
    assert paragraph.content_box_y() == 0
    assert img_1.position_y == 0
    assert img_2.position_y == 40
    assert paragraph.height == 80
    assert paragraph.padding_bottom == 2
    assert paragraph.border_bottom_width == 3
    assert paragraph.margin_bottom == 5
    assert paragraph.margin_height() == 90


@assert_no_logs
def test_box_decoration_break_block_clone():
    # http://www.w3.org/TR/css3-background/#the-box-decoration-break
    page_1, page_2 = parse('''
      <style>
        @page { size: 100px }
        p { padding: 2px; border: 3px solid; margin: 5px;
            box-decoration-break: clone }
        img { display: block; height: 40px }
      </style>
      <p>
        <img src=pattern.png>
        <img src=pattern.png>
        <img src=pattern.png>
        <img src=pattern.png>''')
    html, = page_1.children
    body, = html.children
    paragraph, = body.children
    img_1, img_2 = paragraph.children
    assert paragraph.position_y == 0
    assert paragraph.margin_top == 5
    assert paragraph.border_top_width == 3
    assert paragraph.padding_top == 2
    assert paragraph.content_box_y() == 10
    assert img_1.position_y == 10
    assert img_2.position_y == 50
    assert paragraph.height == 80
    # TODO: bottom margin should be 0
    # https://www.w3.org/TR/css-break-3/#valdef-box-decoration-break-clone
    # "Cloned margins are truncated on block-level boxes."
    # See https://github.com/Kozea/WeasyPrint/issues/115
    assert paragraph.margin_bottom == 5
    assert paragraph.border_bottom_width == 3
    assert paragraph.padding_bottom == 2
    assert paragraph.margin_height() == 100

    html, = page_2.children
    body, = html.children
    paragraph, = body.children
    img_1, img_2 = paragraph.children
    assert paragraph.position_y == 0
    assert paragraph.margin_top == 0
    assert paragraph.border_top_width == 3
    assert paragraph.padding_top == 2
    assert paragraph.content_box_y() == 5
    assert img_1.position_y == 5
    assert img_2.position_y == 45
    assert paragraph.height == 80
    assert paragraph.padding_bottom == 2
    assert paragraph.border_bottom_width == 3
    assert paragraph.margin_bottom == 5
    assert paragraph.margin_height() == 95


@assert_no_logs
def test_box_decoration_break_clone_bottom_padding():
    page_1, page_2 = parse('''
      <style>
        @page { size: 80px; margin: 0 }
        div { height: 20px }
        article { padding: 12px; box-decoration-break: clone }
      </style>
      <article>
        <div>a</div>
        <div>b</div>
        <div>c</div>
      </article>''')
    html, = page_1.children
    body, = html.children
    article, = body.children
    assert article.height == 80 - 2 * 12
    div_1, div_2 = article.children
    assert div_1.position_y == 12
    assert div_2.position_y == 12 + 20

    html, = page_2.children
    body, = html.children
    article, = body.children
    assert article.height == 20
    div, = article.children
    assert div.position_y == 12


@pytest.mark.xfail
@assert_no_logs
def test_box_decoration_break_slice_bottom_padding():  # pragma: no cover
    # Last div fits in first, but not article's padding. As it is impossible to
    # break between a parent and its last child, put last child on next page.
    # TODO: at the end of block_container_layout, we should check that the box
    # with its bottom border/padding doesn't cross the bottom line. If it does,
    # we should re-render the box with a max_position_y including the bottom
    # border/padding.
    page_1, page_2 = parse('''
      <style>
        @page { size: 80px; margin: 0 }
        div { height: 20px }
        article { padding: 12px; box-decoration-break: slice }
      </style>
      <article>
        <div>a</div>
        <div>b</div>
        <div>c</div>
      </article>''')
    html, = page_1.children
    body, = html.children
    article, = body.children
    assert article.height == 80 - 12
    div_1, div_2 = article.children
    assert div_1.position_y == 12
    assert div_2.position_y == 12 + 20

    html, = page_2.children
    body, = html.children
    article, = body.children
    assert article.height == 20
    div, = article.children
    assert div.position_y == 0


@assert_no_logs
def test_overflow_auto():
    page, = parse('''
      <article style="overflow: auto">
        <div style="float: left; height: 50px; margin: 10px">bla bla bla</div>
          toto toto''')
    html, = page.children
    body, = html.children
    article, = body.children
    assert article.height == 50 + 10 + 10


@assert_no_logs
def test_box_margin_top_repagination():
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/943
    page_1, page_2 = parse('''
      <style>
        @page { size: 50px }
        :root { line-height: 1; font-size: 10px }
        a::before { content: target-counter(attr(href), page) }
        div { margin: 20px 0 0; background: yellow }
      </style>
      <p><a href="#title"></a></p>
      <div>1<br/>1<br/>2<br/>2</div>
      <h1 id="title">title</h1>
    ''')
    html, = page_1.children
    body, = html.children
    p, div = body.children
    assert div.margin_top == 20
    assert div.padding_box_y() == 10 + 20

    html, = page_2.children
    body, = html.children
    div, h1 = body.children
    assert div.margin_top == 0
    assert div.padding_box_y() == 0


@assert_no_logs
def test_continue_discard():
    page_1, = parse('''
      <style>
        @page { size: 80px; margin: 0 }
        div { display: inline-block; width: 100%; height: 25px }
        article { continue: discard; border: 1px solid; line-height: 1 }
      </style>
      <article>
        <div>a</div>
        <div>b</div>
        <div>c</div>
        <div>d</div>
        <div>e</div>
        <div>f</div>
      </article>''')
    html, = page_1.children
    body, = html.children
    article, = body.children
    assert article.height == 3 * 25
    div_1, div_2, div_3 = article.children
    assert div_1.position_y == 1
    assert div_2.position_y == 1 + 25
    assert div_3.position_y == 1 + 25 * 2
    assert article.border_bottom_width == 1


@assert_no_logs
def test_continue_discard_children():
    page_1, = parse('''
      <style>
        @page { size: 80px; margin: 0 }
        div { display: inline-block; width: 100%; height: 25px }
        section { border: 1px solid }
        article { continue: discard; border: 1px solid; line-height: 1 }
      </style>
      <article>
        <section>
          <div>a</div>
          <div>b</div>
          <div>c</div>
          <div>d</div>
          <div>e</div>
          <div>f</div>
        </section>
      </article>''')
    html, = page_1.children
    body, = html.children
    article, = body.children
    assert article.height == 2 + 3 * 25
    section, = article.children
    assert section.height == 3 * 25
    div_1, div_2, div_3 = section.children
    assert div_1.position_y == 2
    assert div_2.position_y == 2 + 25
    assert div_3.position_y == 2 + 25 * 2
    assert article.border_bottom_width == 1
