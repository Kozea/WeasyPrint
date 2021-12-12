"""
    weasyprint.tests.test_draw.test_float
    -------------------------------------

    Test how floats are drawn.

"""

import pytest

from ..testing_utils import assert_no_logs
from . import assert_pixels


@assert_no_logs
def test_float():
    assert_pixels('float', 10, 5, '''
        rBBB__aaaa
        BBBB__aaaa
        BBBB__aaaa
        BBBB__aaaa
        __________
    ''', '''
      <style>
        @page { size: 10px 5px; background: white }
      </style>
      <div>
        <img style="float: left" src="pattern.png">
        <img style="float: right" src="blue.jpg">
      </div>
    ''')


@assert_no_logs
def test_float_rtl():
    assert_pixels('float_rtl', 10, 5, '''
        rBBB__aaaa
        BBBB__aaaa
        BBBB__aaaa
        BBBB__aaaa
        __________
    ''', '''
      <style>
        @page { size: 10px 5px; background: white }
      </style>
      <div style="direction: rtl">
        <img style="float: left" src="pattern.png">
        <img style="float: right" src="blue.jpg">
      </div>
    ''')


@assert_no_logs
def test_float_inline():
    assert_pixels('float_inline', 15, 5, '''
        rBBBGG_____aaaa
        BBBBGG_____aaaa
        BBBB_______aaaa
        BBBB_______aaaa
        _______________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page { size: 15px 5px; background: white }
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
def test_float_inline_rtl():
    assert_pixels('float_inline_rtl', 15, 5, '''
        rBBB_____GGaaaa
        BBBB_____GGaaaa
        BBBB_______aaaa
        BBBB_______aaaa
        _______________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page { size: 15px 5px; background: white }
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
def test_float_inline_block():
    assert_pixels('float_inline_block', 15, 5, '''
        rBBBGG_____aaaa
        BBBBGG_____aaaa
        BBBB_______aaaa
        BBBB_______aaaa
        _______________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page { size: 15px 5px; background: white }
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
def test_float_inline_block_rtl():
    assert_pixels('float_inline_block_rtl', 15, 5, '''
        rBBB_____GGaaaa
        BBBB_____GGaaaa
        BBBB_______aaaa
        BBBB_______aaaa
        _______________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page { size: 15px 5px; background: white }
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
def test_float_table():
    assert_pixels('float_table', 15, 5, '''
        rBBBGG_____aaaa
        BBBBGG_____aaaa
        BBBB_______aaaa
        BBBB_______aaaa
        _______________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page { size: 15px 5px; background: white }
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
def test_float_table_rtl():
    assert_pixels('float_table_rtl', 15, 5, '''
        rBBB_____GGaaaa
        BBBB_____GGaaaa
        BBBB_______aaaa
        BBBB_______aaaa
        _______________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page { size: 15px 5px; background: white }
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
def test_float_inline_table():
    assert_pixels('float_inline_table', 15, 5, '''
        rBBBGG_____aaaa
        BBBBGG_____aaaa
        BBBB_______aaaa
        BBBB_______aaaa
        _______________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page { size: 15px 5px; background: white }
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
def test_float_inline_table_rtl():
    assert_pixels('float_inline_table_rtl', 15, 5, '''
        rBBB_____GGaaaa
        BBBB_____GGaaaa
        BBBB_______aaaa
        BBBB_______aaaa
        _______________
    ''', '''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        @page { size: 15px 5px; background: white }
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
def test_float_replaced_block():
    assert_pixels('float_replaced_block', 15, 5, '''
        rBBBaaaa___rBBB
        BBBBaaaa___BBBB
        BBBBaaaa___BBBB
        BBBBaaaa___BBBB
        _______________
    ''', '''
      <style>
        @page { size: 15px 5px; background: white }
      </style>
      <div>
        <img style="float: left" src="pattern.png">
        <img style="float: right" src="pattern.png">
        <img style="display: block" src="blue.jpg">
      </div>
    ''')


@assert_no_logs
def test_float_replaced_block_rtl():
    assert_pixels('float_replaced_block_rtl', 15, 5, '''
        rBBB___aaaarBBB
        BBBB___aaaaBBBB
        BBBB___aaaaBBBB
        BBBB___aaaaBBBB
        _______________
    ''', '''
      <style>
        @page { size: 15px 5px; background: white }
      </style>
      <div style="direction: rtl">
        <img style="float: left" src="pattern.png">
        <img style="float: right" src="pattern.png">
        <img style="display: block" src="blue.jpg">
      </div>
    ''')


@pytest.mark.xfail
@assert_no_logs
def test_float_replaced_inline():
    assert_pixels('float_replaced_inline', 15, 5, '''
        rBBBaaaa___rBBB
        BBBBaaaa___BBBB
        BBBBaaaa___BBBB
        BBBBaaaa___BBBB
        _______________
    ''', '''
      <style>
        @page { size: 15px 5px; background: white }
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
def test_float_replaced_inline_rtl():
    assert_pixels('float_replaced_inline_rtl', 15, 5, '''
        rBBB___aaaarBBB
        BBBB___aaaaBBBB
        BBBB___aaaaBBBB
        BBBB___aaaaBBBB
        _______________
    ''', '''
      <style>
        @page { size: 15px 5px; background: white }
        body { line-height: 1px }
      </style>
      <div style="direction: rtl">
        <img style="float: left" src="pattern.png">
        <img style="float: right" src="pattern.png">
        <img src="blue.jpg">
      </div>
    ''')


@assert_no_logs
def test_float_margin():
    expected_pixels = '''
        BBBBRRRRRRRRRR__
        BBBBRRRRRRRRRR__
        __RRRRRRRRRR____
        __RRRRRRRRRR____
    '''
    html = '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                background: white;
                size: 16px 2px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
                orphans: 1;
                widows: 1;
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
        <div class="pushed">bbbbb bbbbb</div>
    '''
    assert_pixels('float_split_10', 16, 4, expected_pixels, html)


@assert_no_logs
def test_float_split_1():
    expected_pixels = '''
        BBBBRRRRRRRRRRRR
        BBBBRRRRRRRRRRRR
        BBBBRRRR________
        BBBBRRRR________
    '''
    html = '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                background: white;
                size: 16px 2px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
                orphans: 1;
                widows: 1;
            }
            div.split {
                color: blue;
                float: left;
                width: 4px;
            }
        </style>
        <div class="split">aa aa</div>
        <div>bbbbbb bb</div>
    '''
    assert_pixels('float_split_1', 16, 4, expected_pixels, html)


@assert_no_logs
def test_float_split_2():
    expected_pixels = '''
        RRRRRRRRRRRRBBBB
        RRRRRRRRRRRRBBBB
        RRRR________BBBB
        RRRR________BBBB
    '''
    html = '''
        <style>
          @font-face {src: url(weasyprint.otf); font-family: weasyprint}
          @page {
            background: white;
            size: 16px 2px;
          }
          body {
            color: red;
            font-family: weasyprint;
            font-size: 2px;
            line-height: 1;
            orphans: 1;
            widows: 1;
          }
          div.split {
            color: blue;
            float: right;
            width: 4px;
          }
        </style>
        <div class="split">aa aa</div>
        <div>bbbbbb bb</div>
    '''
    assert_pixels('float_split_2', 16, 4, expected_pixels, html)


@assert_no_logs
def test_float_split_3():
    expected_pixels = '''
        BBBBRRRRRRRRRRRR
        BBBBRRRRRRRRRRRR
        RRRRRRRRRR______
        RRRRRRRRRR______
    '''
    html = '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                background: white;
                size: 16px 2px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
                orphans: 1;
                widows: 1;
            }
            div.split {
                color: blue;
                float: left;
                width: 4px;
            }
        </style>
        <div class="split">aa</div>
        <div>bbbbbb bbbbb</div>
    '''
    assert_pixels('float_split_3', 16, 4, expected_pixels, html)


@assert_no_logs
def test_float_split_4():
    expected_pixels = '''
        RRRRRRRRRRRRBBBB
        RRRRRRRRRRRRBBBB
        RRRRRRRRRR______
        RRRRRRRRRR______
    '''
    html = '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                background: white;
                size: 16px 2px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
                orphans: 1;
                widows: 1;
            }
            div.split {
                color: blue;
                float: right;
                width: 4px;
            }
        </style>
        <div class="split">aa</div>
        <div>bbbbbb bbbbb</div>
    '''
    assert_pixels('float_split_4', 16, 4, expected_pixels, html)


@assert_no_logs
def test_float_split_5():
    expected_pixels = '''
        BBBBRRRRRRRRgggg
        BBBBRRRRRRRRgggg
        BBBBRRRR____gggg
        BBBBRRRR____gggg
    '''
    html = '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                background: white;
                size: 16px 2px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
                orphans: 1;
                widows: 1;
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
        <div>bbbb bb</div>
    '''
    assert_pixels('float_split_5', 16, 4, expected_pixels, html)


@assert_no_logs
def test_float_split_6():
    expected_pixels = '''
        BBBBRRRRRRRRgggg
        BBBBRRRRRRRRgggg
        BBBBRRRR________
        BBBBRRRR________
    '''
    html = '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                background: white;
                size: 16px 2px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
                orphans: 1;
                widows: 1;
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
        <div>bbbb bb</div>
    '''
    assert_pixels('float_split_6', 16, 4, expected_pixels, html)


@assert_no_logs
def test_float_split_7():
    expected_pixels = '''
        BBBBRRRRRRRRgggg
        BBBBRRRRRRRRgggg
        RRRR________gggg
        RRRR________gggg
    '''
    html = '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                background: white;
                size: 16px 2px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
                orphans: 1;
                widows: 1;
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
        <div>bbbb bb</div>
    '''
    assert_pixels('float_split_7', 16, 4, expected_pixels, html)


@assert_no_logs
def test_float_split_8():
    expected_pixels = '''
        BBBB__RRRRRRRRRR
        BBBB__RRRRRRRRRR
        BBBB__RRRR______
        BBBB__RRRR______
    '''
    html = '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                background: white;
                size: 16px 2px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
                orphans: 1;
                widows: 1;
            }
            div.split {
                color: blue;
                float: left;
                margin-right: 2px;
                width: 4px;
            }
        </style>
        <div class="split">aa aa</div>
        <div>bbbbb bb</div>
    '''
    assert_pixels('float_split_8', 16, 4, expected_pixels, html)


@assert_no_logs
def test_float_split_9():
    expected_pixels = '''
        RRRRRRRRRRBBBB__
        RRRRRRRRRRBBBB__
        RRRR______BBBB__
        RRRR______BBBB__
    '''
    html = '''
        <style>
            @font-face {src: url(weasyprint.otf); font-family: weasyprint}
            @page {
                background: white;
                size: 16px 2px;
            }
            body {
                color: red;
                font-family: weasyprint;
                font-size: 2px;
                line-height: 1;
                orphans: 1;
                widows: 1;
            }
            div.split {
                color: blue;
                float: right;
                margin-right: 2px;
                width: 4px;
            }
        </style>
        <div class="split">aa aa</div>
        <div>bbbbb bb</div>
    '''
    assert_pixels('float_split_9', 16, 4, expected_pixels, html)
