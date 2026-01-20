"""Test how SVG text is drawn."""

from ...testing_utils import assert_no_logs


@assert_no_logs
def test_text_fill(assert_pixels):
    assert_pixels('''
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    ''', '''
      <style>
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
        @page { font-size: 1px; size: 20em 4em }
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
def test_text_anchor_middle_tspan_head_tail(assert_pixels):
    assert_pixels('''
        ____BBBBRRRRRRBB____
        ____BBBBRRRRRRBB____
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="10" y="1.5" font-family="weasyprint" font-size="2" fill="blue"
              text-anchor="middle">
          AA<tspan fill="red">ABC</tspan>A
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_anchor_end_tspan_head_tail(assert_pixels):
    assert_pixels('''
        ______BBBBRRRRRRBB__
        ______BBBBRRRRRRBB__
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="18" y="1.5" font-family="weasyprint" font-size="2" fill="blue"
              text-anchor="end">
          AA<tspan fill="red">ABC</tspan>A
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_anchor_middle_end_tspan(assert_pixels):
    assert_pixels('''
        _______BBBBBB_______
        _______BBBBBB_______
        ____________BBBBBB__
        ____________BBBBBB__
    ''', '''
      <style>
        @page { size: 20px 4px }
        svg { display: block }
      </style>
      <svg width="20px" height="4px" xmlns="http://www.w3.org/2000/svg">
        <text x="10" y="10" font-family="weasyprint" font-size="2" fill="blue">
          <tspan x="10" y="1.5" text-anchor="middle">ABC</tspan>
          <tspan x="18" y="3.5" text-anchor="end">ABC</tspan>
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_tspan_anchor_non_text(assert_pixels):
    # Regression test for #2375.
    assert_pixels('''
        _______BBBBBB_______
        _______BBBBBB_______
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" text-anchor="end"
           xmlns="http://www.w3.org/2000/svg">
        <text x="10" y="10" font-family="weasyprint" font-size="2" text-anchor="start">
          <tspan x="10" y="1.5" text-anchor="middle" fill="blue">ABC</tspan>
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
def test_text_font_face(assert_pixels):
    assert_pixels('''
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <style>
            @font-face {
              font-family: "SVGFont";
              src: url(weasyprint.otf);
            }
          </style>
        </defs>
        <text x="0" y="1.5" font-family="SVGFont" font-size="2" fill="blue">
          ABC DEF
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_font_face_css(assert_pixels):
    assert_pixels('''
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <style>
            @font-face {
              font-family: "SVGFont";
              src: url(weasyprint.otf);
            }
            text { font-family: "SVGFont" }
          </style>
        </defs>
        <text x="0" y="1.5" font-size="2" fill="blue">
          ABC DEF
        </text>
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


@assert_no_logs
def test_font_shorthand(assert_pixels):
    assert_pixels('''
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="1.5" style="font: 2px 'weasyprint'" fill="blue">
          ABC DEF
        </text>
      </svg>
    ''',
    )


@assert_no_logs
def test_font_shorthand_inheritance_from_parent(assert_pixels):
    assert_pixels('''
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <g style="font: 2px weasyprint">
          <text x="0" y="1.5" fill="blue" font="bad">
            <tspan>ABC DEF</tspan>
          </text>
        </g>
      </svg>
    ''',
    )


@assert_no_logs
def test_explicit_properties_override_parent_shorthand(assert_pixels):
    assert_pixels('''
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <g font="  28px Times New Roman  ">
          <text x="0" y="1.5" font-size="2px" font-family="weasyprint" fill="blue">
            ABC DEF
          </text>
        </g>
      </svg>
    ''',
    )


@assert_no_logs
def test_font_shorthand_overrides_explicit_parent_properties(assert_pixels):
    assert_pixels('''
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <g font-size="18px" font-family="weasyprint">
          <text x="0" y="1.5" style="font: 2px weasyprint" fill="blue">
            ABC DEF
          </text>
        </g>
      </svg>
    ''',
    )


@assert_no_logs
def test_child_font_shorthand_overrides_parent_shorthand(assert_pixels):
    assert_pixels('''
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <g font="   34px    sans   ">
          <text x="0" y="1.5" style="font: 2px    weasyprint" fill="blue">
            ABC DEF
          </text>
        </g>
      </svg>
    ''',
    )


@assert_no_logs
def test_mixed_explicit_and_shorthand_across_levels(assert_pixels):
    assert_pixels('''
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <g font-size="40px" font-family="sans-serif">
          <g style="font: 30px sans">
            <text x="0" y="1.5" font-size="2px" font-family="weasyprint" fill="blue">
              ABC DEF
            </text>
          </g>
        </g>
      </svg>
    ''',
    )


@assert_no_logs
def test_text_fill_opacity(assert_pixels):
    # Regression text for #2665.
    assert_pixels('''
        ______
        _ssss_
        _ssss_
        _ssss_
        _ssss_
        ______
    ''', '''
      <style>
        @page { size: 6px 6px }
        svg { display: block }
      </style>
      <svg width="6px" height="6px" xmlns="http://www.w3.org/2000/svg">
        <text x="1" y="4" font="4px weasyprint" fill="red" opacity="0.5">
          A
        </text>
      </svg>
    ''')
