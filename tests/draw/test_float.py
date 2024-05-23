"""Test how floats are drawn."""

import pytest

from ..testing_utils import assert_no_logs


@assert_no_logs
def test_float(assert_pixels):
    assert_pixels('''
        rBBB__aaaa
        BBBB__aaaa
        BBBB__aaaa
        BBBB__aaaa
        __________
    ''', '''
      <style>
        @page { size: 10px 5px }
      </style>
      <div>
        <img style="float: left" src="pattern.png">
        <img style="float: right" src="blue.jpg">
      </div>
    ''')


@assert_no_logs
def test_float_rtl(assert_pixels):
    assert_pixels('''
        rBBB__aaaa
        BBBB__aaaa
        BBBB__aaaa
        BBBB__aaaa
        __________
    ''', '''
      <style>
        @page { size: 10px 5px }
      </style>
      <div style="direction: rtl">
        <img style="float: left" src="pattern.png">
        <img style="float: right" src="blue.jpg">
      </div>
    ''')


@assert_no_logs
def test_float_inline(assert_pixels):
    assert_pixels('''
        rBBBGG_____aaaa
        BBBBGG_____aaaa
        BBBB_______aaaa
        BBBB_______aaaa
        _______________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page { size: 15px 5px }
        body { font-family: weasyprint; font-size: 2px; line-height: 1;
               color: lime }
      </style>
      <div>
        <img style="float: left" src="pattern.png">
        <img style="float: right" src="blue.jpg">
        <span>a</span>
      </div>
    ''')


@assert_no_logs
def test_float_inline_rtl(assert_pixels):
    assert_pixels('''
        rBBB_____GGaaaa
        BBBB_____GGaaaa
        BBBB_______aaaa
        BBBB_______aaaa
        _______________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page { size: 15px 5px }
        body { font-family: weasyprint; font-size: 2px; line-height: 1;
               color: lime }
      </style>
      <div style="direction: rtl">
        <img style="float: left" src="pattern.png">
        <img style="float: right" src="blue.jpg">
        <span>a</span>
      </div>
    ''')


@assert_no_logs
def test_float_inline_block(assert_pixels):
    assert_pixels('''
        rBBBGG_____aaaa
        BBBBGG_____aaaa
        BBBB_______aaaa
        BBBB_______aaaa
        _______________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page { size: 15px 5px }
        body { font-family: weasyprint; font-size: 2px; line-height: 1;
               color: lime }
      </style>
      <div>
        <img style="float: left" src="pattern.png">
        <img style="float: right" src="blue.jpg">
        <span style="display: inline-block">a</span>
      </div>
    ''')


@assert_no_logs
def test_float_inline_block_rtl(assert_pixels):
    assert_pixels('''
        rBBB_____GGaaaa
        BBBB_____GGaaaa
        BBBB_______aaaa
        BBBB_______aaaa
        _______________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page { size: 15px 5px }
        body { font-family: weasyprint; font-size: 2px; line-height: 1;
               color: lime }
      </style>
      <div style="direction: rtl">
        <img style="float: left" src="pattern.png">
        <img style="float: right" src="blue.jpg">
        <span style="display: inline-block">a</span>
      </div>
    ''')


@assert_no_logs
def test_float_table(assert_pixels):
    assert_pixels('''
        rBBBGG_____aaaa
        BBBBGG_____aaaa
        BBBB_______aaaa
        BBBB_______aaaa
        _______________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page { size: 15px 5px }
        body { font-family: weasyprint; font-size: 2px; line-height: 1;
               color: lime }
      </style>
      <div>
        <img style="float: left" src="pattern.png">
        <img style="float: right" src="blue.jpg">
        <table><tbody><tr><td>a</td></tr></tbody></table>
      </div>
    ''')


@assert_no_logs
def test_float_table_rtl(assert_pixels):
    assert_pixels('''
        rBBB_____GGaaaa
        BBBB_____GGaaaa
        BBBB_______aaaa
        BBBB_______aaaa
        _______________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page { size: 15px 5px }
        body { font-family: weasyprint; font-size: 2px; line-height: 1;
               color: lime }
      </style>
      <div style="direction: rtl">
        <img style="float: left" src="pattern.png">
        <img style="float: right" src="blue.jpg">
        <table><tbody><tr><td>a</td></tr></tbody></table>
      </div>
    ''')


@assert_no_logs
def test_float_inline_table(assert_pixels):
    assert_pixels('''
        rBBBGG_____aaaa
        BBBBGG_____aaaa
        BBBB_______aaaa
        BBBB_______aaaa
        _______________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page { size: 15px 5px }
        table { display: inline-table }
        body { font-family: weasyprint; font-size: 2px; line-height: 1;
               color: lime }
      </style>
      <div>
        <img style="float: left" src="pattern.png">
        <img style="float: right" src="blue.jpg">
        <table><tbody><tr><td>a</td></tr></tbody></table>
      </div>
    ''')


@assert_no_logs
def test_float_inline_table_rtl(assert_pixels):
    assert_pixels('''
        rBBB_____GGaaaa
        BBBB_____GGaaaa
        BBBB_______aaaa
        BBBB_______aaaa
        _______________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page { size: 15px 5px }
        table { display: inline-table }
        body { font-family: weasyprint; font-size: 2px; line-height: 1;
               color: lime }
      </style>
      <div style="direction: rtl">
        <img style="float: left" src="pattern.png">
        <img style="float: right" src="blue.jpg">
        <table><tbody><tr><td>a</td></tr></tbody></table>
      </div>
    ''')


@assert_no_logs
def test_float_replaced_block(assert_pixels):
    assert_pixels('''
        rBBBaaaa___rBBB
        BBBBaaaa___BBBB
        BBBBaaaa___BBBB
        BBBBaaaa___BBBB
        _______________
    ''', '''
      <style>
        @page { size: 15px 5px }
      </style>
      <div>
        <img style="float: left" src="pattern.png">
        <img style="float: right" src="pattern.png">
        <img style="display: block" src="blue.jpg">
      </div>
    ''')


@assert_no_logs
def test_float_replaced_block_rtl(assert_pixels):
    assert_pixels('''
        rBBB___aaaarBBB
        BBBB___aaaaBBBB
        BBBB___aaaaBBBB
        BBBB___aaaaBBBB
        _______________
    ''', '''
      <style>
        @page { size: 15px 5px }
      </style>
      <div style="direction: rtl">
        <img style="float: left" src="pattern.png">
        <img style="float: right" src="pattern.png">
        <img style="display: block" src="blue.jpg">
      </div>
    ''')


@pytest.mark.xfail
@assert_no_logs
def test_float_replaced_inline(assert_pixels):
    assert_pixels('''
        rBBBaaaa___rBBB
        BBBBaaaa___BBBB
        BBBBaaaa___BBBB
        BBBBaaaa___BBBB
        _______________
    ''', '''
      <style>
        @page { size: 15px 5px }
        body { line-height: 1px }
      </style>
      <div>
        <img style="float: left" src="pattern.png">
        <img style="float: right" src="pattern.png">
        <img src="blue.jpg">
      </div>
    ''')


@pytest.mark.xfail
@assert_no_logs
def test_float_replaced_inline_rtl(assert_pixels):
    assert_pixels('''
        rBBB___aaaarBBB
        BBBB___aaaaBBBB
        BBBB___aaaaBBBB
        BBBB___aaaaBBBB
        _______________
    ''', '''
      <style>
        @page { size: 15px 5px }
        body { line-height: 1px }
      </style>
      <div style="direction: rtl">
        <img style="float: left" src="pattern.png">
        <img style="float: right" src="pattern.png">
        <img src="blue.jpg">
      </div>
    ''')


@assert_no_logs
def test_float_margin(assert_pixels):
    assert_pixels('''
        BBBBRRRRRRRRRR__
        BBBBRRRRRRRRRR__
        __RRRRRRRRRR____
        __RRRRRRRRRR____
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
                float: left;
                width: 4px;
            }
            div.pushed {
                margin-left: 2px;
            }
        </style>
        <div class="split">aa</div>
        <div class="pushed">bbbbb bbbbb</div>''')


@assert_no_logs
def test_float_split_1(assert_pixels):
    assert_pixels('''
        BBBBRRRRRRRRRRRR
        BBBBRRRRRRRRRRRR
        BBBBRRRR________
        BBBBRRRR________
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
                float: left;
                width: 4px;
            }
        </style>
        <div class="split">aa aa</div>
        <div>bbbbbb bb</div>''')


@assert_no_logs
def test_float_split_2(assert_pixels):
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
            float: right;
            width: 4px;
          }
        </style>
        <div class="split">aa aa</div>
        <div>bbbbbb bb</div>''')


@assert_no_logs
def test_float_split_3(assert_pixels):
    assert_pixels('''
        BBBBRRRRRRRRRRRR
        BBBBRRRRRRRRRRRR
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
                float: left;
                width: 4px;
            }
        </style>
        <div class="split">aa</div>
        <div>bbbbbb bbbbb</div>''')


@assert_no_logs
def test_float_split_4(assert_pixels):
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
                float: right;
                width: 4px;
            }
        </style>
        <div class="split">aa</div>
        <div>bbbbbb bbbbb</div>''')


@assert_no_logs
def test_float_split_5(assert_pixels):
    assert_pixels('''
        BBBBRRRRRRRRgggg
        BBBBRRRRRRRRgggg
        BBBBRRRR____gggg
        BBBBRRRR____gggg
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
                float: left;
                width: 4px;
            }
            div.split2 {
                color: green;
                float: right;
                width: 4px;
        </style>
        <div class="split">aa aa</div>
        <div class="split2">cc cc</div>
        <div>bbbb bb</div>''')


@assert_no_logs
def test_float_split_6(assert_pixels):
    assert_pixels('''
        BBBBRRRRRRRRgggg
        BBBBRRRRRRRRgggg
        BBBBRRRR________
        BBBBRRRR________
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
                float: left;
                width: 4px;
            }
            div.split2 {
                color: green;
                float: right;
                width: 4px;
        </style>
        <div class="split">aa aa</div>
        <div class="split2">cc</div>
        <div>bbbb bb</div>''')


@assert_no_logs
def test_float_split_7(assert_pixels):
    assert_pixels('''
        BBBBRRRRRRRRgggg
        BBBBRRRRRRRRgggg
        RRRR________gggg
        RRRR________gggg
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
                float: left;
                width: 4px;
            }
            div.split2 {
                color: green;
                float: right;
                width: 4px;
        </style>
        <div class="split">aa</div>
        <div class="split2">cc cc</div>
        <div>bbbb bb</div>''')


@assert_no_logs
def test_float_split_8(assert_pixels):
    assert_pixels('''
        BBBB__RRRRRRRRRR
        BBBB__RRRRRRRRRR
        BBBB__RRRR______
        BBBB__RRRR______
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
                float: left;
                margin-right: 2px;
                width: 4px;
            }
        </style>
        <div class="split">aa aa</div>
        <div>bbbbb bb</div>''')


@assert_no_logs
def test_float_split_9(assert_pixels):
    assert_pixels('''
        RRRRRRRRRRBBBB__
        RRRRRRRRRRBBBB__
        RRRR______BBBB__
        RRRR______BBBB__
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
                float: right;
                margin-right: 2px;
                width: 4px;
            }
        </style>
        <div class="split">aa aa</div>
        <div>bbbbb bb</div>''')


@assert_no_logs
def test_float_split_10(assert_pixels):
    assert_pixels('''
        RRRRRRRRRR______
        RRRRRRRRRR______
        RRRRRRRRRR______
        RRRRRRRRRR______
        ________________
        RRRRRR____BBBB__
        RRRRRR____BBBB__
        RRRRRR____BBBB__
        RRRRRR____BBBB__
        ________________
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 16px 5px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div.split {
                color: blue;
                float: right;
                margin-right: 2px;
                width: 4px;
            }
        </style>
        <div>bbbbb bbbbb</div>
        <div class="split">aa aa</div>
        <div>bbb bbb</div>''')


@assert_no_logs
def test_float_split_11(assert_pixels):
    assert_pixels('''
        ________________
        _BBBBBBBBBB_____
        _BBBBBBBBBB_____
        _BBBBBBBBBB_____
        _BBBBBBBBBB_____
        ________________
        ________________
        ________________
        _BBBB___________
        _BBBB___________
        _rrrrrrrrrrrrrr_
        _rrrrrrrrrrrrrr_
        ________________
        ________________
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                margin: 1px;
                size: 16px 7px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            div.split {
                color: blue;
                float: right;
            }
        </style>
        <div class="split">aaaaa aaaaa aa</div>
        bbbbbbb''')


@assert_no_logs
def test_float_split_12(assert_pixels):
    assert_pixels('''
        BBBBBBBBBBBBBBBB
        BBBBBBBBBBBBBBBB
        BBBBBBBBBBBBBBBB
        BBBBBBBBBBBBBBBB
        BBBBBBBBBBBBBBBB
        BBBBGG______BBBB
        BBBBGG______BBBB
        BBBB________BBBB
        BBBB________BBBB
        ________________
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 16px 5px;
            }
            body {
                color: lime;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            article {
                background: blue;
                height: 5px;
            }
            div {
                background: red;
                color: blue;
            }
        </style>
        <article></article>
        <section>
          a
          <div style="float: left"><p>aa<p>aa</div>
          <div style="float: right"><p>bb<p>bb</div>''')


@pytest.mark.xfail
@assert_no_logs
def test_float_split_13(assert_pixels):
    assert_pixels('''
        BBBBBBBBBBBBBBBB
        BBBBBBBBBBBBBBBB
        BBBBBBBBBBBBBBBB
        BBBBBBBBBBBBBBBB
        BBBBBBBBBBBBBBBB
        BBBBGG______BBBB
        BBBBGG______BBBB
        BBBB________BBBB
        BBBB________BBBB
        ________________
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 16px 5px;
            }
            body {
                color: lime;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            article {
                background: blue;
                height: 5px;
            }
            div {
                background: red;
                color: blue;
            }
        </style>
        <article></article>
        <section>
          <div style="float: left"><p>a<p>aa</div>
          a
          <div style="float: right"><p>bb<p>bb</div>''')


@assert_no_logs
def test_float_split_14(assert_pixels):
    assert_pixels('''
        BBBBBBBBBBBBBBBB
        BBBBBBBBBBBBBBBB
        BBBBBBBBBBBBBBBB
        BBBBBBBBBBBBBBBB
        BBBBBBBBBBBBBBBB
        BBBBGG______BBBB
        BBBBGG______BBBB
        BBBB________BBBB
        BBBB________BBBB
        ________________
    ''', '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                size: 16px 5px;
            }
            body {
                color: lime;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
            }
            article {
                background: blue;
                height: 5px;
            }
            div {
                background: red;
                color: blue;
            }
        </style>
        <article></article>
        a
        <div style="float: left"><p>aa<p>aa</div>
        <div style="float: right"><p>bb<p>bb</div>''')


@pytest.mark.xfail
@assert_no_logs
def test_float_split_15(assert_pixels):
    assert_pixels('''
        BB__RRRRRRRRRR__
        BB__RRRRRRRRRR__
        BB__RRRRRRRRRR__
        BB__RRRRRRRRRR__
        GGBBRRRRRRRRRR__
        GGBBRRRRRRRRRR__
        GGBBRRRRRRRRRR__
        GGBBRRRRRRRRRR__
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
        </style>
        <div style="float: left; position: relative; color: blue; width: 4px">
          a a a
          <div style="float: left; color: lime; width: 2px">
            a a
          </div>
          a a
        </div>
        <div>bbbbb bbbbb bbbbb bbbbb bbbbb</div>''')
