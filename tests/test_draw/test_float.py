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
