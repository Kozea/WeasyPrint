"""Tests for footnotes layout."""

import pytest

from ..testing_utils import assert_no_logs, render_pages, tree_position


@assert_no_logs
def test_inline_footnote():
    page, = render_pages('''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 9px 7px;
            }
            div {
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            span {
                float: footnote;
            }
        </style>
        <div>abc<span>de</span></div>''')
    html, footnote_area = page.children
    body, = html.children
    div, = body.children
    div_textbox, footnote_call = div.children[0].children
    assert div_textbox.text == 'abc'
    assert footnote_call.children[0].text == '1'
    assert div_textbox.position_y == 0

    footnote_marker, footnote_textbox = (
        footnote_area.children[0].children[0].children)
    assert footnote_marker.children[0].text == '1.'
    assert footnote_textbox.text == 'de'
    assert footnote_area.position_y == 5


@assert_no_logs
def test_block_footnote():
    page, = render_pages('''
        <style>
         @font-face {src: url(weasyprint.otf); font-family: weasyprint}
         @page {
             size: 9px 7px;
         }
         div {
             font-family: weasyprint;
             font-size: 2px;
             line-height: 1;
         }
         div.footnote {
             float: footnote;
         }
        </style>
        <div>abc<div class="footnote">de</div></div>''')
    html, footnote_area = page.children
    body, = html.children
    div, = body.children
    div_textbox, footnote_call = div.children[0].children
    assert div_textbox.text == 'abc'
    assert footnote_call.children[0].text == '1'
    assert div_textbox.position_y == 0
    footnote_marker, footnote_textbox = (
     footnote_area.children[0].children[0].children)
    assert footnote_marker.children[0].text == '1.'
    assert footnote_textbox.text == 'de'
    assert footnote_area.position_y == 5


@assert_no_logs
def test_long_footnote():
    page, = render_pages('''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 9px 7px;
            }
            div {
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            span {
                float: footnote;
            }
        </style>
        <div>abc<span>de f</span></div>''')
    html, footnote_area = page.children
    body, = html.children
    div, = body.children
    div_textbox, footnote_call = div.children[0].children
    assert div_textbox.text == 'abc'
    assert footnote_call.children[0].text == '1'
    assert div_textbox.position_y == 0
    footnote_line1, footnote_line2 = footnote_area.children[0].children
    footnote_marker, footnote_content1 = footnote_line1.children
    footnote_content2 = footnote_line2.children[0]
    assert footnote_marker.children[0].text == '1.'
    assert footnote_content1.text == 'de'
    assert footnote_area.position_y == 3
    assert footnote_content2.text == 'f'
    assert footnote_content2.position_y == 5


@pytest.mark.xfail
@assert_no_logs
def test_after_marker_footnote():
    # TODO: this syntax is in the specification, but we’re currently limited to
    # one pseudo element per selector, according to CSS 2.1:
    # https://drafts.csswg.org/css2/#selector-syntax
    # and Selectors Level 3:
    # https://drafts.csswg.org/selectors-3/#selector-syntax
    # This limitation doesn’t exist anymore in Selectors Level 4:
    # https://drafts.csswg.org/selectors-4/#typedef-compound-selector
    page, = render_pages('''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 9px 7px;
            }
            div {
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            span {
                float: footnote;
            }
            ::footnote-marker::after {
                content: '|';
            }
        </style>
        <div>abc<span>de</span></div>''')
    html, footnote_area = page.children
    footnote_marker, _ = footnote_area.children[0].children[0].children
    assert footnote_marker.children[0].text == '1.|'


@assert_no_logs
def test_several_footnote():
    page1, page2, = render_pages('''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 9px 7px;
            }
            div {
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            span {
                float: footnote;
            }
        </style>
        <div>abcd e<span>fg</span> hijk l<span>mn</span></div>''')
    html1, footnote_area1 = page1.children
    body1, = html1.children
    div1, = body1.children
    div1_line1, div1_line2 = div1.children
    assert div1_line1.children[0].text == 'abcd'
    div1_line2_text, div1_footnote_call = div1.children[1].children
    assert div1_line2_text.text == 'e'
    assert div1_footnote_call.children[0].text == '1'
    footnote_marker1, footnote_textbox1 = (
        footnote_area1.children[0].children[0].children)
    assert footnote_marker1.children[0].text == '1.'
    assert footnote_textbox1.text == 'fg'

    html2, footnote_area2 = page2.children
    body2, = html2.children
    div2, = body2.children
    div2_line1, div2_line2 = div2.children
    assert div2_line1.children[0].text == 'hijk'
    div2_line2_text, div2_footnote_call = div2.children[1].children
    assert div2_line2_text.text == 'l'
    assert div2_footnote_call.children[0].text == '2'
    footnote_marker2, footnote_textbox2 = (
        footnote_area2.children[0].children[0].children)
    assert footnote_marker2.children[0].text == '2.'
    assert footnote_textbox2.text == 'mn'


@assert_no_logs
def test_reported_footnote_1():
    page1, page2, = render_pages('''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 9px 7px;
            }
            div {
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            span {
                float: footnote;
            }
        </style>
        <div>abc<span>f1</span> hij<span>f2</span></div>''')
    html1, footnote_area1 = page1.children
    body1, = html1.children
    div1, = body1.children
    div_line1, div_line2 = div1.children
    div_line1_text, div_footnote_call1 = div_line1.children
    assert div_line1_text.text == 'abc'
    assert div_footnote_call1.children[0].text == '1'
    div_line2_text, div_footnote_call2 = div_line2.children
    assert div_line2_text.text == 'hij'
    assert div_footnote_call2.children[0].text == '2'

    footnote_marker1, footnote_textbox1 = (
        footnote_area1.children[0].children[0].children)
    assert footnote_marker1.children[0].text == '1.'
    assert footnote_textbox1.text == 'f1'

    html2, footnote_area2 = page2.children
    assert not html2.children
    footnote_marker2, footnote_textbox2 = (
        footnote_area2.children[0].children[0].children)
    assert footnote_marker2.children[0].text == '2.'
    assert footnote_textbox2.text == 'f2'


@assert_no_logs
def test_reported_footnote_2():
    page1, page2, = render_pages('''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 9px 7px;
            }
            div {
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            span {
                float: footnote;
            }
        </style>
        <div>abc<span>f1</span> hij<span>f2</span> wow</div>''')
    html1, footnote_area1 = page1.children
    body1, = html1.children
    div1, = body1.children
    div_line1, div_line2 = div1.children
    div_line1_text, div_footnote_call1 = div_line1.children
    assert div_line1_text.text == 'abc'
    assert div_footnote_call1.children[0].text == '1'
    div_line2_text, div_footnote_call2 = div_line2.children
    assert div_line2_text.text == 'hij'
    assert div_footnote_call2.children[0].text == '2'
    footnote_marker1, footnote_textbox1 = (
        footnote_area1.children[0].children[0].children)
    assert footnote_marker1.children[0].text == '1.'
    assert footnote_textbox1.text == 'f1'

    html2, footnote_area2 = page2.children
    body2, = html2.children
    div2, = body2.children
    div2_line, = div2.children
    assert div2_line.children[0].text == 'wow'
    footnote_marker2, footnote_textbox2 = (
        footnote_area2.children[0].children[0].children)
    assert footnote_marker2.children[0].text == '2.'
    assert footnote_textbox2.text == 'f2'


@assert_no_logs
def test_reported_footnote_3():
    page1, page2, = render_pages('''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 9px 10px;
            }
            div {
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            span {
                float: footnote;
            }
        </style>
        <div>
          abc<span>1</span>
          def<span>v long 2</span>
          ghi<span>3</span>
        </div>''')
    html1, footnote_area1 = page1.children
    body1, = html1.children
    div1, = body1.children
    line1, line2, line3 = div1.children
    assert line1.children[0].text == 'abc'
    assert line1.children[1].children[0].text == '1'
    assert line2.children[0].text == 'def'
    assert line2.children[1].children[0].text == '2'
    assert line3.children[0].text == 'ghi'
    assert line3.children[1].children[0].text == '3'
    footnote1, = footnote_area1.children
    assert footnote1.children[0].children[0].children[0].text == '1.'
    assert footnote1.children[0].children[1].text == '1'

    html2, footnote_area2 = page2.children
    footnote2, footnote3 = footnote_area2.children
    assert footnote2.children[0].children[0].children[0].text == '2.'
    assert footnote2.children[0].children[1].text == 'v'
    assert footnote2.children[1].children[0].text == 'long'
    assert footnote2.children[2].children[0].text == '2'
    assert footnote3.children[0].children[0].children[0].text == '3.'
    assert footnote3.children[0].children[1].text == '3'


@assert_no_logs
def test_reported_sequential_footnote():
    pages = render_pages('''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 9px 7px;
            }
            div {
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            span {
                float: footnote;
            }
        </style>
        <div>
            a<span>b</span><span>c</span><span>d</span><span>e</span>
        </div>''')

    positions = [
        tree_position(pages, lambda box: getattr(box, 'text', None) == letter)
        for letter in 'abcde']
    assert sorted(positions) == positions


@assert_no_logs
def test_reported_sequential_footnote_second_line():
    pages = render_pages('''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 9px 7px;
            }
            div {
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            span {
                float: footnote;
            }
        </style>
        <div>
            aaa a<span>b</span><span>c</span><span>d</span><span>e</span>
        </div>''')

    positions = [
        tree_position(pages, lambda box: getattr(box, 'text', None) == letter)
        for letter in 'abc']
    assert sorted(positions) == positions


@assert_no_logs
@pytest.mark.parametrize('css, tail', (
    ('p { break-inside: avoid }', '<br>e<br>f'),
    ('p { widows: 4 }', '<br>e<br>f'),
    ('p + p { break-before: avoid }', '</p><p>e<br>f'),
    ('p + p { break-before: avoid }', '<span>y</span><span>z</span></p><p>e'),
))
def test_footnote_area_after_call(css, tail):
    pages = render_pages('''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 9px 10px;
                margin: 0;
            }
            body {
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
                orphans: 2;
                widows: 2;
                margin: 0;
            }
            span {
                float: footnote;
            }
            %s
        </style>
        <div>a<br>b</div>
        <p>c<br>d<span>x</span>%s</p>''' % (css, tail))

    footnote_call = tree_position(
        pages, lambda box: box.element_tag == 'p::footnote-call')
    footnote_area = tree_position(
        pages, lambda box: type(box).__name__ == 'FootnoteAreaBox')
    assert footnote_call < footnote_area


@assert_no_logs
def test_footnote_display_inline():
    page, = render_pages('''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 9px 50px;
            }
            div {
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            span {
                float: footnote;
                footnote-display: inline;
            }
        </style>
        <div>abc<span>d</span> fgh<span>i</span></div>''')
    html, footnote_area = page.children
    body, = html.children
    div, = body.children
    div_line1, div_line2 = div.children
    div_textbox1, footnote_call1 = div_line1.children
    div_textbox2, footnote_call2 = div_line2.children
    assert div_textbox1.text == 'abc'
    assert div_textbox2.text == 'fgh'
    assert footnote_call1.children[0].text == '1'
    assert footnote_call2.children[0].text == '2'
    line = footnote_area.children[0]
    footnote_mark1, footnote_textbox1 = line.children[0].children
    footnote_mark2, footnote_textbox2 = line.children[1].children
    assert footnote_mark1.children[0].text == '1.'
    assert footnote_textbox1.text == 'd'
    assert footnote_mark2.children[0].text == '2.'
    assert footnote_textbox2.text == 'i'


@assert_no_logs
def test_footnote_longer_than_space_left():
    page1, page2 = render_pages('''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 9px 7px;
            }
            div {
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            span {
                float: footnote;
            }
        </style>
        <div>abc<span>def ghi jkl</span></div>''')
    html1, = page1.children
    body1, = html1.children
    div, = body1.children
    div_textbox, footnote_call = div.children[0].children
    assert div_textbox.text == 'abc'
    assert footnote_call.children[0].text == '1'

    html2, footnote_area = page2.children
    assert not html2.children
    footnote_line1, footnote_line2, footnote_line3 = (
        footnote_area.children[0].children)
    footnote_marker, footnote_content1 = footnote_line1.children
    footnote_content2 = footnote_line2.children[0]
    footnote_content3 = footnote_line3.children[0]
    assert footnote_marker.children[0].text == '1.'
    assert footnote_content1.text == 'def'
    assert footnote_content2.text == 'ghi'
    assert footnote_content3.text == 'jkl'


@assert_no_logs
def test_footnote_longer_than_page():
    # Nothing is defined for this use case in the specification. In WeasyPrint,
    # the content simply overflows.
    page1, page2 = render_pages('''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 9px 7px;
            }
            div {
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            span {
                float: footnote;
            }
        </style>
        <div>abc<span>def ghi jkl mno</span></div>''')
    html1, = page1.children
    body1, = html1.children
    div, = body1.children
    div_textbox, footnote_call = div.children[0].children
    assert div_textbox.text == 'abc'
    assert footnote_call.children[0].text == '1'

    html2, footnote_area2 = page2.children
    assert not html2.children
    footnote_line1, footnote_line2, footnote_line3, footnote_line4 = (
        footnote_area2.children[0].children)
    footnote_marker1, footnote_content1 = footnote_line1.children
    footnote_content2 = footnote_line2.children[0]
    footnote_content3 = footnote_line3.children[0]
    footnote_content4 = footnote_line4.children[0]
    assert footnote_marker1.children[0].text == '1.'
    assert footnote_content1.text == 'def'
    assert footnote_content2.text == 'ghi'
    assert footnote_content3.text == 'jkl'
    assert footnote_content4.text == 'mno'


@assert_no_logs
def test_footnote_policy_line():
    page1, page2 = render_pages('''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 9px 9px;
            }
            div {
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
                orphans: 2;
                widows: 2;
            }
            span {
                float: footnote;
                footnote-policy: line;
            }
        </style>
        <div>abc def ghi jkl<span>1</span></div>''')
    html, = page1.children
    body, = html.children
    div, = body.children
    linebox1, linebox2 = div.children
    assert linebox1.children[0].text == 'abc'
    assert linebox2.children[0].text == 'def'

    html, footnote_area = page2.children
    body, = html.children
    div, = body.children
    linebox1, linebox2 = div.children
    assert linebox1.children[0].text == 'ghi'
    assert linebox2.children[0].text == 'jkl'
    assert linebox2.children[1].children[0].text == '1'

    footnote_marker, footnote_textbox = (
        footnote_area.children[0].children[0].children)
    assert footnote_marker.children[0].text == '1.'
    assert footnote_textbox.text == '1'


@assert_no_logs
def test_footnote_policy_block():
    page1, page2 = render_pages('''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 9px 9px;
            }
            div {
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            span {
                float: footnote;
                footnote-policy: block;
            }
        </style>
        <div>abc</div><div>def ghi jkl<span>1</span></div>''')
    html, = page1.children
    body, = html.children
    div, = body.children
    linebox1, = div.children
    assert linebox1.children[0].text == 'abc'

    html, footnote_area = page2.children
    body, = html.children
    div, = body.children
    linebox1, linebox2, linebox3 = div.children
    assert linebox1.children[0].text == 'def'
    assert linebox2.children[0].text == 'ghi'
    assert linebox3.children[0].text == 'jkl'
    assert linebox3.children[1].children[0].text == '1'

    footnote_marker, footnote_textbox = (
        footnote_area.children[0].children[0].children)
    assert footnote_marker.children[0].text == '1.'
    assert footnote_textbox.text == '1'


@assert_no_logs
def test_footnote_repagination():
    page, = render_pages('''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 9px 7px;
            }
            div {
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div::after {
                content: counter(pages);
            }
            span {
                float: footnote;
            }
        </style>
        <div>ab<span>de</span></div>''')
    html, footnote_area = page.children
    body, = html.children
    div, = body.children
    div_textbox, footnote_call, div_after = div.children[0].children
    assert div_textbox.text == 'ab'
    assert footnote_call.children[0].text == '1'
    assert div_textbox.position_y == 0
    assert div_after.children[0].text == '1'

    footnote_marker, footnote_textbox = (
        footnote_area.children[0].children[0].children)
    assert footnote_marker.children[0].text == '1.'
    assert footnote_textbox.text == 'de'
    assert footnote_area.position_y == 5


@assert_no_logs
def test_reported_footnote_repagination():
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/1700
    page1, page2 = render_pages('''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 5px;
            }
            div {
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            span {
                float: footnote;
            }
            a::after {
                content: target-counter(attr(href), page);
            }
        </style>
        <div><a href="#i">a</a> bb<span>de</span> <i id="i">fg</i></div>''')
    html, = page1.children
    body, = html.children
    div, = body.children
    line1, line2 = div.children
    a, = line1.children
    assert a.children[0].text == 'a'
    assert a.children[1].children[0].text == '2'
    b, footnote_call, _ = line2.children
    assert b.text == 'bb'
    assert footnote_call.children[0].text == '1'

    html, footnote_area = page2.children
    body, = html.children
    div, = body.children
    line1, = div.children
    i, = line1.children
    assert i.children[0].text == 'fg'

    footnote_marker, footnote_textbox = (
        footnote_area.children[0].children[0].children)
    assert footnote_marker.children[0].text == '1.'
    assert footnote_textbox.text == 'de'
    assert footnote_area.position_y == 3


@assert_no_logs
def test_footnote_max_height():
    page1, page2 = render_pages('''
      <style>
          @font-face {src: url(weasyprint.otf); font-family: weasyprint}
          @page {
              size: 12px 6px;

              @footnote {
                  margin-left: 1px;
                  max-height: 4px;
              }
          }
          div {
              font-family: weasyprint;
              font-size: 2px;
              line-height: 1;
          }
          div.footnote {
              float: footnote;
          }
      </style>
      <div>ab<div class="footnote">c</div><div class="footnote">d</div>
      <div class="footnote">e</div></div>
      <div>fg</div>''')
    html1, footnote_area1 = page1.children
    body1, = html1.children
    div, = body1.children
    div_textbox, footnote_call1, footnote_call2, space, footnote_call3 = (
        div.children[0].children)
    assert div_textbox.text == 'ab'
    assert footnote_call1.children[0].text == '1'
    assert footnote_call2.children[0].text == '2'
    assert space.text == ' '
    assert footnote_call3.children[0].text == '3'
    footnote1, footnote2 = footnote_area1.children
    footnote_line1, = footnote1.children
    footnote_marker1, footnote_content1 = footnote_line1.children
    assert footnote_marker1.children[0].text == '1.'
    assert footnote_content1.text == 'c'
    footnote_line2, = footnote2.children
    footnote_marker2, footnote_content2 = footnote_line2.children
    assert footnote_marker2.children[0].text == '2.'
    assert footnote_content2.text == 'd'

    html2, footnote_area2 = page2.children
    body2, = html2.children
    div2, = body2.children
    div_textbox2, = div2.children[0].children
    assert div_textbox2.text == 'fg'
    footnote_line3, = footnote_area2.children[0].children
    footnote_marker3, footnote_content3 = footnote_line3.children
    assert footnote_marker3.children[0].text == '3.'
    assert footnote_content3.text == 'e'


def test_footnote_table_aborted_row():
    page1, page2 = render_pages('''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {size: 10px 35px}
        body {font-family: weasyprint; font-size: 2px}
        tr {height: 10px}
        .footnote {float: footnote}
      </style>
      <table><tbody>
        <tr><td>abc</td></tr>
        <tr><td>abc</td></tr>
        <tr><td>abc</td></tr>
        <tr><td>def<div class="footnote">f</div></td></tr>
      </tbody></table>
    ''')

    html, = page1.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    tbody, = table.children
    for tr in tbody.children:
        td, = tr.children
        line, = td.children
        textbox, = line.children
        assert textbox.text == 'abc'

    html, footnote_area = page2.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    tbody, = table.children
    tr, = tbody.children
    td, = tr.children
    line, = td.children
    textbox, call = line.children
    assert textbox.text == 'def'
    footnote, = footnote_area.children
    line, = footnote.children
    marker, textbox = line.children
    assert textbox.text == 'f'


def test_footnote_table_aborted_group():
    page1, page2 = render_pages('''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page {size: 10px 35px}
        body {font-family: weasyprint; font-size: 2px}
        tr {height: 10px}
        tbody {break-inside: avoid}
        .footnote {float: footnote}
      </style>
      <table>
        <tbody>
          <tr><td>abc</td></tr>
          <tr><td>abc</td></tr>
        </tbody>
        <tbody>
          <tr><td>def<div class="footnote">f</div></td></tr>
          <tr><td>ghi</td></tr>
        </tbody>
      </table>
    ''')

    html, = page1.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    tbody, = table.children
    for tr in tbody.children:
        td, = tr.children
        line, = td.children
        textbox, = line.children
        assert textbox.text == 'abc'

    html, footnote_area = page2.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    tbody, = table.children
    tr1, tr2 = tbody.children
    td, = tr1.children
    line, = td.children
    textbox, call = line.children
    assert textbox.text == 'def'
    td, = tr2.children
    line, = td.children
    textbox, = line.children
    assert textbox.text == 'ghi'
    footnote, = footnote_area.children
    line, = footnote.children
    marker, textbox = line.children
    assert textbox.text == 'f'
