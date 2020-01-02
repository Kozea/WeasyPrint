"""
    weasyprint.tests.layout.inline_block
    ------------------------------------

    Tests for inline blocks layout.

"""

from ..test_boxes import render_pages as parse
from ..testing_utils import assert_no_logs


@assert_no_logs
def test_inline_block_sizes():
    page, = parse('''
      <style>
        @page { margin: 0; size: 200px 2000px }
        body { margin: 0 }
        div { display: inline-block; }
      </style>
      <div> </div>
      <div>a</div>
      <div style="margin: 10px; height: 100px"></div>
      <div style="margin-left: 10px; margin-top: -50px;
                  padding-right: 20px;"></div>
      <div>
        Ipsum dolor sit amet,
        consectetur adipiscing elit.
        Sed sollicitudin nibh
        et turpis molestie tristique.
      </div>
      <div style="width: 100px; height: 100px;
                  padding-left: 10px; margin-right: 10px;
                  margin-top: -10px; margin-bottom: 50px"></div>
      <div style="font-size: 0">
        <div style="min-width: 10px; height: 10px"></div>
        <div style="width: 10%">
          <div style="width: 10px; height: 10px"></div>
        </div>
      </div>
      <div style="min-width: 185px">foo</div>
      <div style="max-width: 10px
        ">Supercalifragilisticexpialidocious</div>''')
    html, = page.children
    assert html.element_tag == 'html'
    body, = html.children
    assert body.element_tag == 'body'
    assert body.width == 200

    line_1, line_2, line_3, line_4 = body.children

    # First line:
    # White space in-between divs ends up preserved in TextBoxes
    div_1, _, div_2, _, div_3, _, div_4, _ = line_1.children

    # First div, one ignored space collapsing with next space
    assert div_1.element_tag == 'div'
    assert div_1.width == 0

    # Second div, one letter
    assert div_2.element_tag == 'div'
    assert 0 < div_2.width < 20

    # Third div, empty with margin
    assert div_3.element_tag == 'div'
    assert div_3.width == 0
    assert div_3.margin_width() == 20
    assert div_3.height == 100

    # Fourth div, empty with margin and padding
    assert div_4.element_tag == 'div'
    assert div_4.width == 0
    assert div_4.margin_width() == 30

    # Second line:
    div_5, _ = line_2.children

    # Fifth div, long text, full-width div
    assert div_5.element_tag == 'div'
    assert len(div_5.children) > 1
    assert div_5.width == 200

    # Third line:
    div_6, _, div_7, _ = line_3.children

    # Sixth div, empty div with fixed width and height
    assert div_6.element_tag == 'div'
    assert div_6.width == 100
    assert div_6.margin_width() == 120
    assert div_6.height == 100
    assert div_6.margin_height() == 140

    # Seventh div
    assert div_7.element_tag == 'div'
    assert div_7.width == 20
    child_line, = div_7.children
    # Spaces have font-size: 0, they get removed
    child_div_1, child_div_2 = child_line.children
    assert child_div_1.element_tag == 'div'
    assert child_div_1.width == 10
    assert child_div_2.element_tag == 'div'
    assert child_div_2.width == 2
    grandchild, = child_div_2.children
    assert grandchild.element_tag == 'div'
    assert grandchild.width == 10

    div_8, _, div_9 = line_4.children
    assert div_8.width == 185
    assert div_9.width == 10


@assert_no_logs
def test_inline_block_sizes_hinting():
    # Previously, the hinting for in shrink-to-fit did not match that
    # of the layout, which often resulted in a line break just before
    # the last word.
    page, = parse('''
        <p style="display: inline-block">Lorem ipsum dolor sit amet …</p>''')
    html, = page.children
    body, = html.children
    outer_line, = body.children
    paragraph, = outer_line.children
    inner_lines = paragraph.children
    assert len(inner_lines) == 1
    text_box, = inner_lines[0].children
    assert text_box.text == 'Lorem ipsum dolor sit amet …'
