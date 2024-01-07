"""Test overflow and clipping."""

import pytest

from ..testing_utils import assert_no_logs


@assert_no_logs
def test_overflow_1(assert_pixels):
    # See test_images
    assert_pixels('''
        ________
        ________
        __rBBB__
        __BBBB__
        ________
        ________
        ________
        ________
    ''', '''
      <style>
        @page { size: 8px }
        body { margin: 2px 0 0 2px; font-size: 0 }
        div { height: 2px; overflow: hidden }
      </style>
      <div><img src="pattern.png"></div>''')


@assert_no_logs
def test_overflow_2(assert_pixels):
    # <body> is only 1px high, but its overflow is propageted to the viewport
    # ie. the padding edge of the page box.
    assert_pixels('''
        ________
        ________
        __rBBB__
        __BBBB__
        __BBBB__
        ________
        ________
        ________
    ''', '''
      <style>
        @page { size: 8px; margin: 2px 2px 3px 2px }
        body { height: 1px; overflow: hidden; font-size: 0 }
      </style>
      <div><img src="pattern.png"></div>''')


@assert_no_logs
def test_overflow_3(assert_pixels):
    # Assert that the border is not clipped by overflow: hidden
    assert_pixels('''
        ________
        ________
        __BBBB__
        __B__B__
        __B__B__
        __BBBB__
        ________
        ________
    ''', '''
      <style>
        @page { size: 8px; margin: 2px; }
        div { width: 2px; height: 2px; overflow: hidden;
              border: 1px solid blue; }
      </style>
      <div></div>''')


@assert_no_logs
def test_overflow_4(assert_pixels):
    # Assert that the page margins aren't clipped by body's overflow
    assert_pixels('''
        rr______
        rr______
        __BBBB__
        __BBBB__
        __BBBB__
        __BBBB__
        ________
        ________
    ''', '''
      <style>
        @page {
          size: 8px;
          margin: 2px;
          background:#fff;
          @top-left-corner { content: ''; background:#f00; } }
        body { overflow: auto; background:#00f; }
      </style>
      ''')


@assert_no_logs
def test_overflow_5(assert_pixels):
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/2026
    assert_pixels('''
        BBBBBB__
        BBBBBB__
        BBBB____
        BBBB____
        BBBB____
        ________
        ________
        ________
    ''', '''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 8px }
        body { font-family: weasyprint; line-height: 1; font-size: 2px }
        p { color: blue }
      </style>
      <p>abc</p>
      <p style="height: 3px; overflow: hidden">ab<br>ab<br>ab<br>ab</p>
      ''')


@assert_no_logs
@pytest.mark.parametrize('number, css, pixels', (
    (1, '5px, 5px, 9px, auto', '''
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______rBBBrBg_
        ______BBBBBBg_
        ______BBBBBBg_
        ______BBBBBBg_
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
    '''),
    (2, '5px, 5px, auto, 10px', '''
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______rBBBr___
        ______BBBBB___
        ______BBBBB___
        ______BBBBB___
        ______rBBBr___
        ______BBBBB___
        ______ggggg___
        ______________
        ______________
        ______________
    '''),
    (3, '5px, auto, 9px, 10px', '''
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        _grBBBrBBBr___
        _gBBBBBBBBB___
        _gBBBBBBBBB___
        _gBBBBBBBBB___
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
    '''),
    (4, 'auto, 5px, 9px, 10px', '''
        ______________
        ______ggggg___
        ______rBBBr___
        ______BBBBB___
        ______BBBBB___
        ______BBBBB___
        ______rBBBr___
        ______BBBBB___
        ______BBBBB___
        ______BBBBB___
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
    '''),
))
def test_clip(assert_pixels, number, css, pixels):
    assert_pixels(pixels, '''
      <style>
        @page { size: 14px 16px }
        div { margin: 1px; border: 1px green solid;
              background: url(pattern.png);
              position: absolute; /* clip only applies on abspos */
              top: 0; bottom: 2px; left: 0; right: 0;
              clip: rect(%s); }
      </style>
      <div>''' % css)
