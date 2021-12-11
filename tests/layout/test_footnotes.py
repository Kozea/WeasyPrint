"""
    weasyprint.tests.layout.footnotes
    ---------------------------------

    Tests for footnotes layout.

"""

import pytest

from ..testing_utils import assert_no_logs, render_pages


@assert_no_logs
def test_inline_footnote():
    page, = render_pages('''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 9px 7px;
                background: white;
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
             background: white;
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
                background: white;
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
                background: white;
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
                background: white;
            }
            div {
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
                orphans: 1;
                widows: 1;
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
                background: white;
            }
            div {
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
                orphans: 1;
                widows: 1;
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
                background: white;
            }
            div {
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
                orphans: 1;
                widows: 1;
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
                background: white;
            }
            div {
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
                orphans: 1;
                widows: 1;
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
def test_footnote_display_inline():
    page, = render_pages('''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 9px 50px;
                background: white;
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
                background: white;
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
                background: white;
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
                background: white;
            }
            div {
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
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
                background: white;
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
                background: white;
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
