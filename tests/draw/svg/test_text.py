"""Test how SVG text is drawn."""

from ...testing_utils import assert_no_logs


@assert_no_logs
def test_text_fill(assert_pixels):
    assert_pixels('''
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    ''', '''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="1.5" font-family="weasyprint" font-size="2" fill="blue">
          ABC DEF
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_stroke(assert_pixels):
    assert_pixels('''
        _BBBBBBBBBBBB_______
        _BBBBBBBBBBBB_______
        _BBBBBBBBBBBB_______
        _BBBBBBBBBBBB_______
    ''', '''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { font-size: 1px; size: 20em 8ex }
        svg { display: block }
      </style>
      <svg width="20px" height="4px" xmlns="http://www.w3.org/2000/svg">
        <text x="2" y="2.5" font-family="weasyprint" font-size="2"
              fill="transparent" stroke="blue" stroke-width="1ex">
          A B C
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_x(assert_pixels):
    assert_pixels('''
        BB__BB_BBBB_________
        BB__BB_BBBB_________
    ''', '''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="0 4 7" y="1.5" font-family="weasyprint" font-size="2"
              fill="blue">
          ABCD
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_y(assert_pixels):
    assert_pixels('''
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
def test_text_xy(assert_pixels):
    assert_pixels('''
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
def test_text_dx(assert_pixels):
    assert_pixels('''
        BB__BB_BBBB_________
        BB__BB_BBBB_________
    ''', '''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text dx="0 2 1" y="1.5" font-family="weasyprint" font-size="2"
              fill="blue">
          ABCD
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_dy(assert_pixels):
    assert_pixels('''
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
def test_text_dx_dy(assert_pixels):
    assert_pixels('''
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


@assert_no_logs
def test_text_anchor_start(assert_pixels):
    assert_pixels('''
        __BBBBBB____________
        __BBBBBB____________
        ____BBBBBB__________
        ____BBBBBB__________
    ''', '''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 20px 4px }
        svg { display: block }
      </style>
      <svg width="20px" height="4px" xmlns="http://www.w3.org/2000/svg">
        <text x="2" y="1.5" font-family="weasyprint" font-size="2"
              fill="blue">
          ABC
        </text>
        <text x="4" y="3.5" font-family="weasyprint" font-size="2"
              fill="blue" text-anchor="start">
          ABC
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_anchor_middle(assert_pixels):
    assert_pixels('''
        _______BBBBBB_______
        _______BBBBBB_______
    ''', '''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="10" y="1.5" font-family="weasyprint" font-size="2"
              fill="blue" text-anchor="middle">
          ABC
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_anchor_end(assert_pixels):
    assert_pixels('''
        ____________BBBBBB__
        ____________BBBBBB__
    ''', '''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="18" y="1.5" font-family="weasyprint" font-size="2"
              fill="blue" text-anchor="end">
          ABC
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_tspan(assert_pixels):
    assert_pixels('''
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    ''', '''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="10" y="10" font-family="weasyprint" font-size="2" fill="blue">
          <tspan x="0" y="1.5">ABC DEF</tspan>
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_tspan_anchor_middle(assert_pixels):
    assert_pixels('''
        _______BBBBBB_______
        _______BBBBBB_______
    ''', '''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="10" y="10" font-family="weasyprint" font-size="2" fill="blue">
          <tspan x="10" y="1.5" text-anchor="middle">ABC</tspan>
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_tspan_anchor_end(assert_pixels):
    assert_pixels('''
        ____________BBBBBB__
        ____________BBBBBB__
    ''', '''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="10" y="10" font-family="weasyprint" font-size="2" fill="blue">
          <tspan x="18" y="1.5" text-anchor="end">ABC</tspan>
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_anchor_middle_tspan(assert_pixels):
    assert_pixels('''
        _______BBBBBB_______
        _______BBBBBB_______
    ''', '''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="10" y="10" font-family="weasyprint" font-size="2" fill="blue"
              text-anchor="middle">
          <tspan x="10" y="1.5">ABC</tspan>
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_anchor_end_tspan(assert_pixels):
    assert_pixels('''
        ____________BBBBBB__
        ____________BBBBBB__
    ''', '''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="10" y="10" font-family="weasyprint" font-size="2" fill="blue"
              text-anchor="end">
          <tspan x="18" y="1.5">ABC</tspan>
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_rotate(assert_pixels):
    assert_pixels('''
        __RR__RR__RR________
        __RR__RR__RR________
        BB__BB__BB__________
        BB__BB__BB__________
    ''', '''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 20px 4px }
        svg { display: block }
      </style>
      <svg width="20px" height="4px" xmlns="http://www.w3.org/2000/svg">
        <text x="2" y="1.5" font-family="weasyprint" font-size="2" fill="red"
          letter-spacing="2">abc</text>
        <text x="2" y="1.5" font-family="weasyprint" font-size="2" fill="blue"
          rotate="180" letter-spacing="2">abc</text>
      </svg>
    ''')


@assert_no_logs
def test_text_text_length(assert_pixels):
    assert_pixels('''
        __RRRRRR____________
        __RRRRRR____________
        __BB__BB__BB________
        __BB__BB__BB________
    ''', '''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 20px 4px }
        svg { display: block }
      </style>
      <svg width="20px" height="4px" xmlns="http://www.w3.org/2000/svg">
        <text x="2" y="1.5" font-family="weasyprint" font-size="2" fill="red">
          abc
        </text>
        <text x="2" y="3.5" font-family="weasyprint" font-size="2" fill="blue"
          textLength="10">abc</text>
      </svg>
    ''')


@assert_no_logs
def test_text_length_adjust_glyphs_only(assert_pixels):
    assert_pixels('''
        __RRRRRR____________
        __RRRRRR____________
        __BBBBBBBBBBBB______
        __BBBBBBBBBBBB______
    ''', '''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 20px 4px }
        svg { display: block }
      </style>
      <svg width="20px" height="4px" xmlns="http://www.w3.org/2000/svg">
        <text x="2" y="1.5" font-family="weasyprint" font-size="2" fill="red">
          abc
        </text>
        <text x="2" y="3.5" font-family="weasyprint" font-size="2" fill="blue"
          textLength="12" lengthAdjust="spacingAndGlyphs">abc</text>
      </svg>
    ''')


@assert_no_logs
def test_text_length_adjust_spacing_and_glyphs(assert_pixels):
    assert_pixels('''
        __RR_RR_RR__________
        __RR_RR_RR__________
        __BBBB__BBBB__BBBB__
        __BBBB__BBBB__BBBB__
    ''', '''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 20px 4px }
        svg { display: block }
      </style>
      <svg width="20px" height="4px" xmlns="http://www.w3.org/2000/svg">
        <text x="2" y="1.5" font-family="weasyprint" font-size="2" fill="red"
          letter-spacing="1">abc</text>
        <text x="2" y="3.5" font-family="weasyprint" font-size="2" fill="blue"
          letter-spacing="1" textLength="16" lengthAdjust="spacingAndGlyphs">
          abc
        </text>
      </svg>
    ''')
