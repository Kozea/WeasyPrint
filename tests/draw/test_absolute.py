"""Test how absolutes are drawn."""

import pytest

from ..testing_utils import assert_no_logs


@assert_no_logs
def test_absolute_split_1(assert_pixels):
    assert_pixels('''
        BBBBRRRRRRRR____
        BBBBRRRRRRRR____
        BBBBRR__________
        BBBBRR__________
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 16px 2px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div.split {
                color: blue;
                left: 0;
                position: absolute;
                top: 0;
                width: 4px;
            }
        </style>
        <div class="split">aa aa</div>
        <div>bbbbbb bbb</div>
    ''')


@assert_no_logs
def test_absolute_split_2(assert_pixels):
    assert_pixels('''
        RRRRRRRRRRRRBBBB
        RRRRRRRRRRRRBBBB
        RRRR________BBBB
        RRRR________BBBB
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 16px 2px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div.split {
                color: blue;
                position: absolute;
                top: 0;
                right: 0;
                width: 4px;
            }
        </style>
        <div class="split">aa aa</div>
        <div>bbbbbb bb</div>
    ''')


@assert_no_logs
def test_absolute_split_3(assert_pixels):
    assert_pixels('''
        BBBBRRRRRRRR____
        BBBBRRRRRRRR____
        RRRRRRRRRR______
        RRRRRRRRRR______
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 16px 2px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div.split {
                color: blue;
                position: absolute;
                top: 0;
                left: 0;
                width: 4px;
            }
        </style>
        <div class="split">aa</div>
        <div>bbbbbb bbbbb</div>
    ''')


@assert_no_logs
def test_absolute_split_4(assert_pixels):
    assert_pixels('''
        RRRRRRRRRRRRBBBB
        RRRRRRRRRRRRBBBB
        RRRRRRRRRR______
        RRRRRRRRRR______
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 16px 2px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div.split {
                color: blue;
                position: absolute;
                top: 0;
                right: 0;
                width: 4px;
            }
        </style>
        <div class="split">aa</div>
        <div>bbbbbb bbbbb</div>
    ''')


@assert_no_logs
def test_absolute_split_5(assert_pixels):
    assert_pixels('''
        BBBBRRRR____gggg
        BBBBRRRR____gggg
        BBBBRRRRRR__gggg
        BBBBRRRRRR__gggg
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 16px 2px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div.split {
                color: blue;
                position: absolute;
                top: 0;
                left: 0;
                width: 4px;
            }
            div.split2 {
                color: green;
                position: absolute;
                top: 0;
                right: 0;
                width: 4px;
        </style>
        <div class="split">aa aa</div>
        <div class="split2">cc cc</div>
        <div>bbbb bbbbb</div>
    ''')


@assert_no_logs
def test_absolute_split_6(assert_pixels):
    assert_pixels('''
        BBBBRRRR____gggg
        BBBBRRRR____gggg
        BBBBRRRRRR______
        BBBBRRRRRR______
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 16px 2px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div.split {
                color: blue;
                position: absolute;
                width: 4px;
            }
            div.split2 {
                color: green;
                position: absolute;
                top: 0;
                right: 0;
                width: 4px;
        </style>
        <div class="split">aa aa</div>
        <div class="split2">cc</div>
        <div>bbbb bbbbb</div>
    ''')


@assert_no_logs
def test_absolute_split_7(assert_pixels):
    assert_pixels('''
        BBBBRRRRRRRRgggg
        BBBBRRRRRRRRgggg
        ____RRRR____gggg
        ____RRRR____gggg
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 16px 2px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div.split {
                color: blue;
                position: absolute;
                width: 4px;
            }
            div.split2 {
                color: green;
                position: absolute;
                top: 0;
                right: 0;
                width: 4px;
            }
            div.push {
                margin-left: 4px;
            }
        </style>
        <div class="split">aa</div>
        <div class="split2">cc cc</div>
        <div class="push">bbbb bb</div>
    ''')


@assert_no_logs
def test_absolute_split_8(assert_pixels):
    assert_pixels('''
        ______
        ______
        ______
        ______
        __RR__
        __RR__
        ______
        ______
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                margin: 2px 0;
                size: 6px 8px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div {
                position: absolute;
                left: 2px;
                top: 2px;
                width: 2px;
            }
        </style>
        <div>a a a a</div>
    ''')


@assert_no_logs
def test_absolute_split_9(assert_pixels):
    assert_pixels('''
        ______
        ______
        BBRRBB
        BBRRBB
        BBRR__
        BBRR__
        ______
        ______
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                margin: 2px 0;
                size: 6px 8px;
            }
            body {
                color: blue;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div {
                color: red;
                position: absolute;
                left: 2px;
                top: 0;
                width: 2px;
            }
        </style>
        aaa a<div>a a a a</div>
    ''')


@assert_no_logs
def test_absolute_split_10(assert_pixels):
    assert_pixels('''
        BB____
        BB____
        __RR__
        __RR__
        __RR__
        __RR__

        BBRR__
        BBRR__
        __RR__
        __RR__
        ______
        ______
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 6px;
            }
            body {
                color: blue;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div {
                color: red;
                position: absolute;
                left: 2px;
                top: 2px;
                width: 2px;
            }
            div + article {
                break-before: page;
            }
        </style>
        <article>a</article>
        <div>a a a a</div>
        <article>a</article>
    ''')


@assert_no_logs
def test_absolute_split_11(assert_pixels):
    assert_pixels('''
        BBBBBB
        BBBBBB
        BBRRBB
        BBRRBB
        __RR__
        __RR__
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 6px;
            }
            body {
                color: blue;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div {
                bottom: 0;
                color: red;
                position: absolute;
                left: 2px;
                width: 2px;
            }
        </style>
        aaa aaa<div>a a</div>
    ''')


@assert_no_logs
def test_absolute_split_12(assert_pixels):
    assert_pixels('''
        BBBBBB__
        BBBBBB__
        ________
        ________
        ________
        ________
        ________
        ________
        BB______
        BB______
        BBRR____
        BBRR____
        BBRRRR__
        BBRRRR__
        BBRRRRRR
        BBRRRRRR
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 8px;
            }
            body {
                color: blue;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div {
                break-inside: avoid;
            }
            section {
                left: 2px;
                position: absolute;
                color: red;
            }
        </style>
        aaa
        <div>
          a
          <section>x<br>xx<br>xxx</section>
          <br>
          a<br>
          a<br>
          a
        </div>
    ''')


@pytest.mark.xfail
@assert_no_logs
def test_absolute_next_page(assert_pixels):
    # TODO: currently, the layout of absolute boxes forces to render a box,
    # even when it doesn’t fit in the page. This workaround avoids placeholders
    # with no box. Instead, we should remove these placeholders, or avoid
    # crashes when they’re rendered.
    assert_pixels('''
        RRRRRRRRRR______
        RRRRRRRRRR______
        RRRRRRRRRR______
        RRRRRRRRRR______
        BBBBBBRRRR______
        BBBBBBRRRR______
        BBBBBB__________
        ________________
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 16px 4px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div.split {
                color: blue;
                position: absolute;
                font-size: 3px;
            }
        </style>
        aaaaa aaaaa
        <div class="split">bb</div>
        aaaaa
    ''')


@assert_no_logs
def test_absolute_rtl_1(assert_pixels):
    assert_pixels('''
        __________RRRRRR
        __________RRRRRR
        ________________
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 16px 3px;
            }
            body {
                direction: rtl;
            }
            div {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
                position: absolute;
            }
        </style>
        <div>bbb</div>
    ''')


@assert_no_logs
def test_absolute_rtl_2(assert_pixels):
    assert_pixels('''
        ________________
        _________RRRRRR_
        _________RRRRRR_
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 16px 3px;
            }
            body {
                direction: rtl;
            }
            div {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
                padding: 1px;
                position: absolute;
            }
        </style>
        <div>bbb</div>
    ''')


@assert_no_logs
def test_absolute_rtl_3(assert_pixels):
    assert_pixels('''
        ________________
        RRRRRR__________
        RRRRRR__________
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 16px 3px;
            }
            body {
                direction: rtl;
            }
            div {
                bottom: 0;
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                left: 0;
                line-height: 1;
                position: absolute;
            }
        </style>
        <div>bbb</div>
    ''')


@assert_no_logs
def test_absolute_rtl_4(assert_pixels):
    assert_pixels('''
        ________________
        _________RRRRRR_
        _________RRRRRR_
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 16px 3px;
            }
            body {
                direction: rtl;
            }
            div {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
                position: absolute;
                right: 1px;
                top: 1px;
            }
        </style>
        <div>bbb</div>
    ''')


@assert_no_logs
def test_absolute_rtl_5(assert_pixels):
    assert_pixels('''
        RRRRRR__________
        RRRRRR__________
        ________________
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 16px 3px;
            }
            div {
                color: red;
                direction: rtl;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
                position: absolute;
            }
        </style>
        <div>bbb</div>
    ''')


@assert_no_logs
def test_absolute_pages_counter(assert_pixels):
    assert_pixels('''
        ______
        _RR___
        _RR___
        _RR___
        _RR___
        _____B
        ______
        _RR___
        _RR___
        _BB___
        _BB___
        _____B
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                font-family: weasyprint;
                margin: 1px;
                size: 6px 6px;
                @bottom-right-corner {
                    color: blue;
                    content: counter(pages);
                    font-size: 1px;
                }
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div {
                color: blue;
                position: absolute;
            }
        </style>
        a a a <div>a a</div>
    ''')


@assert_no_logs
def test_absolute_pages_counter_orphans(assert_pixels):
    assert_pixels('''
        ______
        _RR___
        _RR___
        _RR___
        _RR___
        ______
        ______
        ______
        _____B
        ______
        _RR___
        _RR___
        _BB___
        _BB___
        _GG___
        _GG___
        ______
        _____B
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                font-family: weasyprint;
                margin: 1px;
                size: 6px 9px;
                @bottom-right-corner {
                    color: blue;
                    content: counter(pages);
                    font-size: 1px;
                }
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
                orphans: 2;
                widows: 2;
            }
            div {
                color: blue;
                position: absolute;
            }
            div ~ div {
                color: lime;
            }
        </style>
        a a a <div>a a a</div> a <div>a a a</div>
    ''')


@assert_no_logs
def test_absolute_in_inline(assert_pixels):
    assert_pixels('''
        ______
        _GG___
        _GG___
        _GG___
        _GG___
        ______
        ______
        ______
        ______

        ______
        _RR___
        _RR___
        _RR___
        _RR___
        _BB___
        _BB___
        ______
        ______
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                margin: 1px;
                size: 6px 9px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
                orphans: 2;
                widows: 2;
            }
            p {
                color: lime;
            }
            div {
                color: blue;
                position: absolute;
            }
        </style>
        <p>a a</p> a a <div>a</div>
    ''')


@assert_no_logs
def test_fixed_in_inline(assert_pixels):
    assert_pixels('''
        ______
        _GG___
        _GG___
        _GG___
        _GG___
        _BB___
        _BB___
        ______
        ______

        ______
        _RR___
        _RR___
        _RR___
        _RR___
        _BB___
        _BB___
        ______
        ______
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                margin: 1px;
                size: 6px 9px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
                orphans: 2;
                widows: 2;
            }
            p {
                color: lime;
            }
            div {
                color: blue;
                position: fixed;
            }
        </style>
        <p>a a</p> a a <div>a</div>
    ''')


@assert_no_logs
def test_absolute_image_background(assert_pixels):
    assert_pixels('''
        ____
        _RBB
        _BBB
        _BBB
    ''', '''
        <style>
          @page {
            size: 4px;
          }
          img {
            background: blue;
            position: absolute;
            top: 1px;
            left: 1px;
          }
        </style>
        <img src="pattern-transparent.svg" />
    ''')


@assert_no_logs
def test_absolute_in_absolute_break(assert_pixels):
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/2134
    assert_pixels('''
        BBBB
        BBBB
        BBBB
        BBBB
        BBBB

        BBBB
        BBBB
        BBBB
        BBBB
        BBBB

        BBBB
        BBBB
        RRRR
        RRRR
        RRRR

        RRRR
        RRRR
        ____
        ____
        ____
    ''', '''
        <style>
          @page {
            size: 4px 5px;
          }
          body {
            font-size: 2px;
            line-height: 1;
          }
          div {
            position: absolute;
            width: 100%;
          }
        </style>
        <div style="background: blue">
          <br><br><br><br>
          <div style="background: red">
            <br><br>
          </div>
        </div>
        <br><br><br><br><br><br><br>
    ''')
