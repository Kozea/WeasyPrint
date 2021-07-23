"""
    weasyprint.tests.test_draw.svg.test_shapes
    ------------------------------------------

    Test how SVG simple shapes are drawn.

"""

from ...testing_utils import assert_no_logs
from .. import assert_pixels


@assert_no_logs
def test_rect_stroke():
    assert_pixels('rect_stroke', 9, 9, '''
        _________
        _RRRRRRR_
        _RRRRRRR_
        _RR___RR_
        _RR___RR_
        _RR___RR_
        _RRRRRRR_
        _RRRRRRR_
        _________
    ''', '''
      <style>
        @page { size: 9px }
        svg { display: block }
      </style>
      <svg width="9px" height="9px" xmlns="http://www.w3.org/2000/svg">
        <rect x="2" y="2" width="5" height="5"
              stroke-width="2" stroke="red" fill="none" />
      </svg>
    ''')


@assert_no_logs
def test_rect_fill():
    assert_pixels('rect_fill', 9, 9, '''
        _________
        _________
        __RRRRR__
        __RRRRR__
        __RRRRR__
        __RRRRR__
        __RRRRR__
        _________
        _________
    ''', '''
      <style>
        @page { size: 9px }
        svg { display: block }
      </style>
      <svg width="9px" height="9px" xmlns="http://www.w3.org/2000/svg">
        <rect x="2" y="2" width="5" height="5" fill="red" />
      </svg>
    ''')


@assert_no_logs
def test_rect_stroke_fill():
    assert_pixels('rect_stroke_fill', 9, 9, '''
        _________
        _RRRRRRR_
        _RRRRRRR_
        _RRBBBRR_
        _RRBBBRR_
        _RRBBBRR_
        _RRRRRRR_
        _RRRRRRR_
        _________
    ''', '''
      <style>
        @page { size: 9px }
        svg { display: block }
      </style>
      <svg width="9px" height="9px" xmlns="http://www.w3.org/2000/svg">
        <rect x="2" y="2" width="5" height="5"
              stroke-width="2" stroke="red" fill="blue" />
      </svg>
    ''')


@assert_no_logs
def test_rect_round():
    assert_pixels('rect_round', 9, 9, '''
        _zzzzzzz_
        zzzzzzzzz
        zzRRRRRzz
        zzRRRRRzz
        zzRRRRRzz
        zzRRRRRzz
        zzRRRRRzz
        zzzzzzzzz
        _zzzzzzz_
    ''', '''
      <style>
        @page { size: 9px }
        svg { display: block }
      </style>
      <svg width="9px" height="9px" xmlns="http://www.w3.org/2000/svg">
        <rect width="9" height="9" fill="red" rx="4" ry="4" />
      </svg>
    ''')


@assert_no_logs
def test_rect_round_zero():
    assert_pixels('rect_round_zero', 9, 9, '''
        RRRRRRRRR
        RRRRRRRRR
        RRRRRRRRR
        RRRRRRRRR
        RRRRRRRRR
        RRRRRRRRR
        RRRRRRRRR
        RRRRRRRRR
        RRRRRRRRR
    ''', '''
      <style>
        @page { size: 9px }
        svg { display: block }
      </style>
      <svg width="9px" height="9px" xmlns="http://www.w3.org/2000/svg">
        <rect width="9" height="9" fill="red" rx="0" ry="4" />
      </svg>
    ''')


@assert_no_logs
def test_line():
    assert_pixels('line', 9, 9, '''
        _________
        _________
        _________
        _________
        RRRRRR___
        RRRRRR___
        _________
        _________
        _________
    ''', '''
      <style>
        @page { size: 9px }
        svg { display: block }
      </style>
      <svg width="9px" height="9px" xmlns="http://www.w3.org/2000/svg">
        <line x1="0" y1="5" x2="6" y2="5"
          stroke="red" stroke-width="2"/>
      </svg>
    ''')


@assert_no_logs
def test_polyline():
    assert_pixels('polyline', 9, 9, '''
        _________
        RRRRRR___
        RRRRRR___
        RR__RR___
        RR__RR___
        RR__RR___
        _________
        _________
        _________
    ''', '''
      <style>
        @page { size: 9px }
        svg { display: block }
      </style>
      <svg width="9px" height="9px" xmlns="http://www.w3.org/2000/svg">
        <polyline points="1,6, 1,2, 5,2, 5,6"
          stroke="red" stroke-width="2" fill="none"/>
      </svg>
    ''')


@assert_no_logs
def test_polyline_fill():
    assert_pixels('polyline_fill', 9, 9, '''
        _________
        RRRRRR___
        RRRRRR___
        RRBBRR___
        RRBBRR___
        RRBBRR___
        _________
        _________
        _________
    ''', '''
      <style>
        @page { size: 9px }
        svg { display: block }
      </style>
      <svg width="9px" height="9px" xmlns="http://www.w3.org/2000/svg">
        <polyline points="1,6, 1,2, 5,2, 5,6"
          stroke="red" stroke-width="2" fill="blue"/>
      </svg>
    ''')


@assert_no_logs
def test_polygon():
    assert_pixels('polygon', 9, 9, '''
        _________
        RRRRRR___
        RRRRRR___
        RR__RR___
        RR__RR___
        RRRRRR___
        RRRRRR___
        _________
        _________
    ''', '''
      <style>
        @page { size: 9px }
        svg { display: block }
      </style>
      <svg width="9px" height="9px" xmlns="http://www.w3.org/2000/svg">
        <polygon points="1,6, 1,2, 5,2, 5,6"
          stroke="red" stroke-width="2" fill="none"/>
      </svg>
    ''')


@assert_no_logs
def test_polygon_fill():
    assert_pixels('polygon_fill', 9, 9, '''
        _________
        RRRRRR___
        RRRRRR___
        RRBBRR___
        RRBBRR___
        RRRRRR___
        RRRRRR___
        _________
        _________
    ''', '''
      <style>
        @page { size: 9px }
        svg { display: block }
      </style>
      <svg width="9px" height="9px" xmlns="http://www.w3.org/2000/svg">
        <polygon points="1,6, 1,2, 5,2, 5,6"
          stroke="red" stroke-width="2" fill="blue"/>
      </svg>
    ''')


@assert_no_logs
def test_circle_stroke():
    assert_pixels('circle_stroke', 10, 10, '''
        __________
        __RRRRRR__
        _RRRRRRRR_
        _RRRRRRRR_
        _RRR__RRR_
        _RRR__RRR_
        _RRRRRRRR_
        _RRRRRRRR_
        __RRRRRR__
        __________
    ''', '''
      <style>
        @page { size: 10px }
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <circle cx="5" cy="5" r="3"
          stroke="red" stroke-width="2" fill="none"/>
      </svg>
    ''')


@assert_no_logs
def test_circle_fill():
    assert_pixels('circle_fill', 10, 10, '''
        __________
        __RRRRRR__
        _RRRRRRRR_
        _RRRRRRRR_
        _RRRBBRRR_
        _RRRBBRRR_
        _RRRRRRRR_
        _RRRRRRRR_
        __RRRRRR__
        __________
    ''', '''
      <style>
        @page { size: 10px }
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <circle cx="5" cy="5" r="3"
          stroke="red" stroke-width="2" fill="blue"/>
      </svg>
    ''')


@assert_no_logs
def test_ellipse_stroke():
    assert_pixels('ellipse_stroke', 10, 10, '''
        __________
        __RRRRRR__
        _RRRRRRRR_
        _RRRRRRRR_
        _RRR__RRR_
        _RRR__RRR_
        _RRRRRRRR_
        _RRRRRRRR_
        __RRRRRR__
        __________
    ''', '''
      <style>
        @page { size: 10px }
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <ellipse cx="5" cy="5" rx="3" ry="3"
          stroke="red" stroke-width="2" fill="none"/>
      </svg>
    ''')


@assert_no_logs
def test_ellipse_fill():
    assert_pixels('ellipse_fill', 10, 10, '''
        __________
        __RRRRRR__
        _RRRRRRRR_
        _RRRRRRRR_
        _RRRBBRRR_
        _RRRBBRRR_
        _RRRRRRRR_
        _RRRRRRRR_
        __RRRRRR__
        __________
    ''', '''
      <style>
        @page { size: 10px }
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <ellipse cx="5" cy="5" rx="3" ry="3"
          stroke="red" stroke-width="2" fill="blue"/>
      </svg>
    ''')


@assert_no_logs
def test_rect_in_g():
    assert_pixels('rect_in_g', 9, 9, '''
        RRRRR____
        RRRRR____
        RRRRR____
        RRRRR____
        RRRRR____
        _________
        _________
        _________
        _________
    ''', '''
      <style>
        @page { size: 9px }
        svg { display: block }
      </style>
      <svg width="9px" height="9px" xmlns="http://www.w3.org/2000/svg">
        <g x="5" y="5">
          <rect width="5" height="5" fill="red" />
        </g>
      </svg>
    ''')


@assert_no_logs
def test_rect_x_y_in_g():
    assert_pixels('rect_x_y_in_g', 9, 9, '''
        _________
        _________
        __RRRRR__
        __RRRRR__
        __RRRRR__
        __RRRRR__
        __RRRRR__
        _________
        _________
    ''', '''
      <style>
        @page { size: 9px }
        svg { display: block }
      </style>
      <svg width="9px" height="9px" xmlns="http://www.w3.org/2000/svg">
        <g x="5" y="5">
          <rect x="2" y="2" width="5" height="5" fill="red" />
        </g>
      </svg>
    ''')


@assert_no_logs
def test_rect_stroke_zero():
    assert_pixels('rect_stroke_zero', 9, 9, '''
        _________
        _________
        _________
        _________
        _________
        _________
        _________
        _________
        _________
    ''', '''
      <style>
        @page { size: 9px }
        svg { display: block }
      </style>
      <svg width="9px" height="9px" xmlns="http://www.w3.org/2000/svg">
        <rect x="2" y="2" width="5" height="5"
              stroke-width="0" stroke="red" fill="none" />
      </svg>
    ''')
