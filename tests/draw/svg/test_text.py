"""
    weasyprint.tests.test_draw.svg.test_text
    ----------------------------------------

    Test how SVG text is drawn.

"""

import pytest

from ...testing_utils import assert_no_logs
from .. import assert_pixels


@assert_no_logs
def test_text_fill():
    assert_pixels('text_fill', 20, 2, '''
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    ''', '''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="1" font-family="weasyprint" font-size="2" fill="blue">
          ABC DEF
        </text>
      </svg>
    ''')


@pytest.mark.xfail
@assert_no_logs
def test_text_stroke():
    assert_pixels('text_fill', 20, 4, '''
        BBBBBBBBBBBB________
        BBBBBBBBBBBB________
        BBBBBBBBBBBB________
        BBBBBBBBBBBB________
    ''', '''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 20px 4px }
        svg { display: block }
      </style>
      <svg width="20px" height="4px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="2" font-family="weasyprint" font-size="2"
              fill="transparent" stroke="black" stroke-width="2">
          A B C
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_x():
    assert_pixels('text_x', 20, 2, '''
        BB__BB_BBBB_________
        BB__BB_BBBB_________
    ''', '''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="0 4 7" y="1" font-family="weasyprint" font-size="2"
              fill="blue">
          ABCD
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_y():
    assert_pixels('text_y', 30, 10, '''
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        BBBBBBBBBB_____BBBBB__________
        BBBBBBBBBB_____BBBBB__________
        BBBBBBBBBB_____BBBBB__________
        BBBBBBBBBB_____BBBBB__________
        BBBBBBBBBB_____BBBBB__________
    ''', '''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 30px 10px }
        svg { display: block }
      </style>
      <svg width="30px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="9 9 4 9 4" font-family="weasyprint" font-size="5"
              fill="blue">
          ABCDEF
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_xy():
    assert_pixels('text_xy', 30, 10, '''
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        BBBBB__________BBBBB__________
        BBBBB__________BBBBB__________
        BBBBB__________BBBBB__________
        BBBBB__________BBBBB__________
        BBBBB__________BBBBB__________
    ''', '''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 30px 10px }
        svg { display: block }
      </style>
      <svg width="30px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <text x="0 10" y="9 4 9 4" font-family="weasyprint" font-size="5"
              fill="blue">
          ABCDE
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_dx():
    assert_pixels('text_dx', 20, 2, '''
        BB__BB_BBBB_________
        BB__BB_BBBB_________
    ''', '''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text dx="0 2 1" y="1" font-family="weasyprint" font-size="2"
              fill="blue">
          ABCD
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_dy():
    assert_pixels('text_dy', 30, 10, '''
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        BBBBBBBBBB_____BBBBB__________
        BBBBBBBBBB_____BBBBB__________
        BBBBBBBBBB_____BBBBB__________
        BBBBBBBBBB_____BBBBB__________
        BBBBBBBBBB_____BBBBB__________
    ''', '''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 30px 10px }
        svg { display: block }
      </style>
      <svg width="30px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" dy="9 0 -5 5 -5" font-family="weasyprint" font-size="5"
              fill="blue">
          ABCDEF
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_dx_dy():
    assert_pixels('text_dx_dy', 30, 10, '''
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        BBBBB__________BBBBB__________
        BBBBB__________BBBBB__________
        BBBBB__________BBBBB__________
        BBBBB__________BBBBB__________
        BBBBB__________BBBBB__________
    ''', '''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 30px 10px }
        svg { display: block }
      </style>
      <svg width="30px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <text dx="0 5" dy="9 -5 5 -5" font-family="weasyprint" font-size="5"
              fill="blue">
          ABCDE
        </text>
      </svg>
    ''')
