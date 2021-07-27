"""
    weasyprint.tests.test_draw.svg.test_gradients
    ------------------------------------------

    Test how SVG simple gradients are drawn.

"""

import pytest

from ...testing_utils import assert_no_logs
from .. import assert_pixels


@assert_no_logs
def test_linear_gradient():
    assert_pixels('linear_gradient', 10, 10, '''
        BBBBBBBBBB
        BBBBBBBBBB
        BBBBBBBBBB
        BBBBBBBBBB
        BBBBBBBBBB
        RRRRRRRRRR
        RRRRRRRRRR
        RRRRRRRRRR
        RRRRRRRRRR
        RRRRRRRRRR
    ''', '''
      <style>
        @page { size: 10px }
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1"
            gradientUnits="objectBoundingBox">
            <stop stop-color="blue" offset="50%"></stop>
            <stop stop-color="red" offset="50%"></stop>
          </linearGradient>
        </defs>
        <rect x="0" y="0" width="10" height="10" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_linear_gradient_userspace():
    assert_pixels('linear_gradient_userspace', 10, 10, '''
        BBBBBBBBBB
        BBBBBBBBBB
        BBBBBBBBBB
        BBBBBBBBBB
        BBBBBBBBBB
        RRRRRRRRRR
        RRRRRRRRRR
        RRRRRRRRRR
        RRRRRRRRRR
        RRRRRRRRRR
    ''', '''
      <style>
        @page { size: 10px }
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="0" y2="10"
            gradientUnits="userSpaceOnUse">
            <stop stop-color="blue" offset="50%"></stop>
            <stop stop-color="red" offset="50%"></stop>
          </linearGradient>
        </defs>
        <rect x="0" y="0" width="10" height="10" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_linear_gradient_multicolor():
    assert_pixels('linear_gradient_multicolor', 10, 8, '''
        BBBBBBBBBB
        BBBBBBBBBB
        RRRRRRRRRR
        RRRRRRRRRR
        GGGGGGGGGG
        GGGGGGGGGG
        vvvvvvvvvv
        vvvvvvvvvv
    ''', '''
      <style>
        @page { size: 10px 8px }
        svg { display: block }
      </style>
      <svg width="10px" height="8px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1"
            gradientUnits="objectBoundingBox">
            <stop stop-color="blue" offset="25%"></stop>
            <stop stop-color="red" offset="25%"></stop>
            <stop stop-color="red" offset="50%"></stop>
            <stop stop-color="lime" offset="50%"></stop>
            <stop stop-color="lime" offset="75%"></stop>
            <stop stop-color="rgb(128,0,128)" offset="75%"></stop>
          </linearGradient>
        </defs>
        <rect x="0" y="0" width="10" height="8" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_linear_gradient_multicolor_userspace():
    assert_pixels('linear_gradient_multicolor_userspace', 10, 8, '''
        BBBBBBBBBB
        BBBBBBBBBB
        RRRRRRRRRR
        RRRRRRRRRR
        GGGGGGGGGG
        GGGGGGGGGG
        vvvvvvvvvv
        vvvvvvvvvv
    ''', '''
      <style>
        @page { size: 10px 8px }
        svg { display: block }
      </style>
      <svg width="10px" height="8px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="0" y2="8"
            gradientUnits="userSpaceOnUse">
            <stop stop-color="blue" offset="25%"></stop>
            <stop stop-color="red" offset="25%"></stop>
            <stop stop-color="red" offset="50%"></stop>
            <stop stop-color="lime" offset="50%"></stop>
            <stop stop-color="lime" offset="75%"></stop>
            <stop stop-color="rgb(128,0,128)" offset="75%"></stop>
          </linearGradient>
        </defs>
        <rect x="0" y="0" width="10" height="8" fill="url(#grad)" />
      </svg>
    ''')


@pytest.mark.xfail
@assert_no_logs
def test_linear_gradient_transform():
    assert_pixels('linear_gradient_transform', 10, 8, '''
        BBBBBBBBBB
        RRRRRRRRRR
        GGGGGGGGGG
        vvvvvvvvvv
        vvvvvvvvvv
        vvvvvvvvvv
        vvvvvvvvvv
        vvvvvvvvvv
    ''', '''
      <style>
        @page { size: 10px 8px}
        svg { display: block }
      </style>
      <svg width="10px" height="8px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1"
            gradientUnits="objectBoundingBox" gradientTransform="scale(0.5)">
            <stop stop-color="blue" offset="25%"></stop>
            <stop stop-color="red" offset="25%"></stop>
            <stop stop-color="red" offset="50%"></stop>
            <stop stop-color="lime" offset="50%"></stop>
            <stop stop-color="lime" offset="75%"></stop>
            <stop stop-color="rgb(128,0,128)" offset="75%"></stop>
          </linearGradient>
        </defs>
        <rect x="0" y="0" width="10" height="8" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_linear_gradient_repeat():
    assert_pixels('linear_gradient_repeat', 10, 16, '''
        BBBBBBBBBB
        BBBBBBBBBB
        RRRRRRRRRR
        RRRRRRRRRR
        GGGGGGGGGG
        GGGGGGGGGG
        vvvvvvvvvv
        vvvvvvvvvv
        BBBBBBBBBB
        BBBBBBBBBB
        RRRRRRRRRR
        RRRRRRRRRR
        GGGGGGGGGG
        GGGGGGGGGG
        vvvvvvvvvv
        vvvvvvvvvv
    ''', '''
      <style>
        @page { size: 10px 16px }
        svg { display: block }
      </style>
      <svg width="11px" height="16px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="0" y2="0.5"
            gradientUnits="objectBoundingBox" spreadMethod="repeat">
            <stop stop-color="blue" offset="25%"></stop>
            <stop stop-color="red" offset="25%"></stop>
            <stop stop-color="red" offset="50%"></stop>
            <stop stop-color="lime" offset="50%"></stop>
            <stop stop-color="lime" offset="75%"></stop>
            <stop stop-color="rgb(128,0,128)" offset="75%"></stop>
          </linearGradient>
        </defs>
        <rect x="0" y="0" width="11" height="16" fill="url(#grad)" />
      </svg>
    ''')


@pytest.mark.xfail
@assert_no_logs
def test_linear_gradient_repeat_long():
    assert_pixels('linear_gradient_repeat_long', 10, 16, '''
        BBBBBBBBBB
        RRRRRRRRRR
        GGGGGGGGGG
        vvvvvvvvvv
        BBBBBBBBBB
        RRRRRRRRRR
        GGGGGGGGGG
        vvvvvvvvvv
        BBBBBBBBBB
        RRRRRRRRRR
        GGGGGGGGGG
        vvvvvvvvvv
        BBBBBBBBBB
        RRRRRRRRRR
        GGGGGGGGGG
        vvvvvvvvvv
    ''', '''
      <style>
        @page { size: 10px 16px }
        svg { display: block }
      </style>
      <svg width="11px" height="16px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="0" y2="0.25"
            gradientUnits="objectBoundingBox" spreadMethod="repeat">
            <stop stop-color="blue" offset="25%"></stop>
            <stop stop-color="red" offset="25%"></stop>
            <stop stop-color="red" offset="50%"></stop>
            <stop stop-color="lime" offset="50%"></stop>
            <stop stop-color="lime" offset="75%"></stop>
            <stop stop-color="rgb(128,0,128)" offset="75%"></stop>
          </linearGradient>
        </defs>
        <rect x="0" y="0" width="11" height="16" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_linear_gradient_reflect():
    assert_pixels('linear_gradient_reflect', 10, 16, '''
        BBBBBBBBBB
        BBBBBBBBBB
        RRRRRRRRRR
        RRRRRRRRRR
        GGGGGGGGGG
        GGGGGGGGGG
        vvvvvvvvvv
        vvvvvvvvvv
        vvvvvvvvvv
        vvvvvvvvvv
        GGGGGGGGGG
        GGGGGGGGGG
        RRRRRRRRRR
        RRRRRRRRRR
        BBBBBBBBBB
        BBBBBBBBBB
    ''', '''
      <style>
        @page { size: 10px 16px }
        svg { display: block }
      </style>
      <svg width="11px" height="16px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="0" y2="0.5"
            gradientUnits="objectBoundingBox" spreadMethod="reflect">
            <stop stop-color="blue" offset="25%"></stop>
            <stop stop-color="red" offset="25%"></stop>
            <stop stop-color="red" offset="50%"></stop>
            <stop stop-color="lime" offset="50%"></stop>
            <stop stop-color="lime" offset="75%"></stop>
            <stop stop-color="rgb(128,0,128)" offset="75%"></stop>
          </linearGradient>
        </defs>
        <rect x="0" y="0" width="11" height="16" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_radial_gradient():
    assert_pixels('radial_gradient', 10, 10, '''
        rrrrrrrrrr
        rrrrrrrrrr
        rrrrBBrrrr
        rrrBBBBrrr
        rrBBBBBBrr
        rrBBBBBBrr
        rrrBBBBrrr
        rrrrBBrrrr
        rrrrrrrrrr
        rrrrrrrrrr
    ''', '''
      <style>
        @page { size: 10px }
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <radialGradient id="grad" cx="0.5" cy="0.5" r="0.5"
            fx="0.5" fy="0.5" fr="0.2"
            gradientUnits="objectBoundingBox">
            <stop stop-color="blue" offset="25%"></stop>
            <stop stop-color="red" offset="25%"></stop>
          </radialGradient>
        </defs>
        <rect x="0" y="0" width="10" height="10" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_radial_gradient_userspace():
    assert_pixels('radial_gradient_userspace', 10, 10, '''
        rrrrrrrrrr
        rrrrrrrrrr
        rrrrBBrrrr
        rrrBBBBrrr
        rrBBBBBBrr
        rrBBBBBBrr
        rrrBBBBrrr
        rrrrBBrrrr
        rrrrrrrrrr
        rrrrrrrrrr
    ''', '''
      <style>
        @page { size: 10px }
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <radialGradient id="grad" cx="5" cy="5" r="5" fx="5" fy="5" fr="2"
            gradientUnits="userSpaceOnUse">
            <stop stop-color="blue" offset="25%"></stop>
            <stop stop-color="red" offset="25%"></stop>
          </radialGradient>
        </defs>
        <rect x="0" y="0" width="10" height="10" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_radial_gradient_multicolor():
    assert_pixels('radial_gradient_multicolor', 10, 10, '''
        rrrrrrrrrr
        rrrGGGGrrr
        rrGGBBGGrr
        rGGBBBBGGr
        rGBBBBBBGr
        rGBBBBBBGr
        rGGBBBBGGr
        rrGGBBGGrr
        rrrGGGGrrr
        rrrrrrrrrr
    ''', '''
      <style>
        @page { size: 10px }
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <radialGradient id="grad" cx="0.5" cy="0.5" r="0.5"
            fx="0.5" fy="0.5" fr="0.2"
            gradientUnits="objectBoundingBox">
            <stop stop-color="blue" offset="33%"></stop>
            <stop stop-color="lime" offset="33%"></stop>
            <stop stop-color="lime" offset="66%"></stop>
            <stop stop-color="red" offset="66%"></stop>
          </radialGradient>
        </defs>
        <rect x="0" y="0" width="10" height="10" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_radial_gradient_multicolor_userspace():
    assert_pixels('radial_gradient_multicolor_userspace', 10, 10, '''
        rrrrrrrrrr
        rrrGGGGrrr
        rrGGBBGGrr
        rGGBBBBGGr
        rGBBBBBBGr
        rGBBBBBBGr
        rGGBBBBGGr
        rrGGBBGGrr
        rrrGGGGrrr
        rrrrrrrrrr
    ''', '''
      <style>
        @page { size: 10px }
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <radialGradient id="grad" cx="5" cy="5" r="5"
            fx="5" fy="5" fr="2"
            gradientUnits="userSpaceOnUse">
            <stop stop-color="blue" offset="33%"></stop>
            <stop stop-color="lime" offset="33%"></stop>
            <stop stop-color="lime" offset="66%"></stop>
            <stop stop-color="red" offset="66%"></stop>
          </radialGradient>
        </defs>
        <rect x="0" y="0" width="10" height="10" fill="url(#grad)" />
      </svg>
    ''')


@pytest.mark.xfail
@assert_no_logs
def test_radial_gradient_repeat():
    assert_pixels('radial_gradient_repeat', 10, 10, '''
        GBrrrrrrBG
        BrrGGGGrrB
        rrGGBBGGrr
        rGGBBBBGGr
        rGBBBBBBGr
        rGBBBBBBGr
        rGGBBBBGGr
        rrGGBBGGrr
        BrrGGGGrrB
        GBrrrrrrBG
    ''', '''
      <style>
        @page { size: 10px }
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <radialGradient id="grad" cx="0.5" cy="0.5" r="0.5"
            fx="0.5" fy="0.5" fr="0.2"
            gradientUnits="objectBoundingBox" spreadMethod="repeat">
            <stop stop-color="blue" offset="33%"></stop>
            <stop stop-color="lime" offset="33%"></stop>
            <stop stop-color="lime" offset="66%"></stop>
            <stop stop-color="red" offset="66%"></stop>
          </radialGradient>
        </defs>
        <rect x="0" y="0" width="10" height="10" fill="url(#grad)" />
      </svg>
    ''')


@pytest.mark.xfail
@assert_no_logs
def test_radial_gradient_reflect():
    assert_pixels('radial_gradient_reflect', 10, 10, '''
        BGrrrrrrGB
        GrrGGGGrrG
        rrGGBBGGrr
        rGGBBBBGGr
        rGBBBBBBGr
        rGBBBBBBGr
        rGGBBBBGGr
        rrGGBBGGrr
        GrrGGGGrrG
        BGrrrrrrGB
    ''', '''
      <style>
        @page { size: 10px }
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <radialGradient id="grad" cx="0.5" cy="0.5" r="0.5"
            fx="0.5" fy="0.5" fr="0.2"
            gradientUnits="objectBoundingBox" spreadMethod="reflect">
            <stop stop-color="blue" offset="33%"></stop>
            <stop stop-color="lime" offset="33%"></stop>
            <stop stop-color="lime" offset="66%"></stop>
            <stop stop-color="red" offset="66%"></stop>
          </radialGradient>
        </defs>
        <rect x="0" y="0" width="10" height="10" fill="url(#grad)" />
      </svg>
    ''')
