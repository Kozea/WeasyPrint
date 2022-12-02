"""Test how SVG simple gradients are drawn."""

import pytest

from ...testing_utils import assert_no_logs


@assert_no_logs
def test_linear_gradient(assert_pixels):
    assert_pixels('''
        __________
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _RRRRRRRR_
        _RRRRRRRR_
        _RRRRRRRR_
        _RRRRRRRR_
        __________
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
        <rect x="1" y="1" width="8" height="8" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_linear_gradient_userspace(assert_pixels):
    assert_pixels('''
        __________
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _BBBBBBBB_
        _RRRRRRRR_
        _RRRRRRRR_
        _RRRRRRRR_
        _RRRRRRRR_
        __________
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
        <rect x="1" y="1" width="8" height="8" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_linear_gradient_multicolor(assert_pixels):
    assert_pixels('''
        __________
        BBBBBBBBBB
        BBBBBBBBBB
        RRRRRRRRRR
        RRRRRRRRRR
        GGGGGGGGGG
        GGGGGGGGGG
        vvvvvvvvvv
        vvvvvvvvvv
        __________
    ''', '''
      <style>
        @page { size: 10px 10px }
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
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
        <rect x="0" y="1" width="10" height="8" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_linear_gradient_multicolor_userspace(assert_pixels):
    assert_pixels('''
        __________
        BBBBBBBBBB
        BBBBBBBBBB
        RRRRRRRRRR
        RRRRRRRRRR
        GGGGGGGGGG
        GGGGGGGGGG
        vvvvvvvvvv
        vvvvvvvvvv
        __________
    ''', '''
      <style>
        @page { size: 10px 10px }
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="0" y2="10"
            gradientUnits="userSpaceOnUse">
            <stop stop-color="blue" offset="30%"></stop>
            <stop stop-color="red" offset="30%"></stop>
            <stop stop-color="red" offset="50%"></stop>
            <stop stop-color="lime" offset="50%"></stop>
            <stop stop-color="lime" offset="70%"></stop>
            <stop stop-color="rgb(128,0,128)" offset="70%"></stop>
          </linearGradient>
        </defs>
        <rect x="0" y="1" width="10" height="8" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_linear_gradient_transform(assert_pixels):
    assert_pixels('''
        __________
        BBBBBBBBBB
        BBBBBBBBBB
        BBBBBBBBBB
        BBBBBBBBBB
        BBBBBBBBBB
        RRRRRRRRRR
        GGGGGGGGGG
        vvvvvvvvvv
        __________
    ''', '''
      <style>
        @page { size: 10px 10px}
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1"
            gradientUnits="objectBoundingBox"
            gradientTransform="matrix(0.5, 0, 0, 0.5, 0, 0.5)">
            <stop stop-color="blue" offset="25%"></stop>
            <stop stop-color="red" offset="25%"></stop>
            <stop stop-color="red" offset="50%"></stop>
            <stop stop-color="lime" offset="50%"></stop>
            <stop stop-color="lime" offset="75%"></stop>
            <stop stop-color="rgb(128,0,128)" offset="75%"></stop>
          </linearGradient>
        </defs>
        <rect x="0" y="1" width="10" height="8" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_linear_gradient_transform_repeat(assert_pixels):
    assert_pixels('''
        __________
        BBBBBBBBBB
        RRRRRRRRRR
        GGGGGGGGGG
        vvvvvvvvvv
        BBBBBBBBBB
        RRRRRRRRRR
        GGGGGGGGGG
        vvvvvvvvvv
        __________
    ''', '''
      <style>
        @page { size: 10px 10px}
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1"
            gradientUnits="objectBoundingBox" spreadMethod="repeat"
            gradientTransform="matrix(0.5, 0, 0, 0.5, 0, 0.5)">
            <stop stop-color="blue" offset="25%"></stop>
            <stop stop-color="red" offset="25%"></stop>
            <stop stop-color="red" offset="50%"></stop>
            <stop stop-color="lime" offset="50%"></stop>
            <stop stop-color="lime" offset="75%"></stop>
            <stop stop-color="rgb(128,0,128)" offset="75%"></stop>
          </linearGradient>
        </defs>
        <rect x="0" y="1" width="10" height="8" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_linear_gradient_transform_userspace(assert_pixels):
    assert_pixels('''
        __________
        BBBBBBBBBB
        BBBBBBBBBB
        BBBBBBBBBB
        BBBBBBBBBB
        BBBBBBBBBB
        RRRRRRRRRR
        GGGGGGGGGG
        vvvvvvvvvv
        __________
    ''', '''
      <style>
        @page { size: 10px 10px}
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="0" y2="8"
            gradientUnits="userSpaceOnUse"
            gradientTransform="matrix(0.5, 0, 0, 0.5, 0, 5)">
            <stop stop-color="blue" offset="25%"></stop>
            <stop stop-color="red" offset="25%"></stop>
            <stop stop-color="red" offset="50%"></stop>
            <stop stop-color="lime" offset="50%"></stop>
            <stop stop-color="lime" offset="75%"></stop>
            <stop stop-color="rgb(128,0,128)" offset="75%"></stop>
          </linearGradient>
        </defs>
        <rect x="0" y="1" width="10" height="8" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_linear_gradient_transform_repeat_userspace(assert_pixels):
    assert_pixels('''
        __________
        BBBBBBBBBB
        RRRRRRRRRR
        GGGGGGGGGG
        vvvvvvvvvv
        BBBBBBBBBB
        RRRRRRRRRR
        GGGGGGGGGG
        vvvvvvvvvv
        __________
    ''', '''
      <style>
        @page { size: 10px 10px}
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="0" y2="8"
            gradientUnits="userSpaceOnUse" spreadMethod="repeat"
            gradientTransform="matrix(0.5, 0, 0, 0.5, 0, 5)">
            <stop stop-color="blue" offset="25%"></stop>
            <stop stop-color="red" offset="25%"></stop>
            <stop stop-color="red" offset="50%"></stop>
            <stop stop-color="lime" offset="50%"></stop>
            <stop stop-color="lime" offset="75%"></stop>
            <stop stop-color="rgb(128,0,128)" offset="75%"></stop>
          </linearGradient>
        </defs>
        <rect x="0" y="1" width="10" height="8" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_linear_gradient_repeat(assert_pixels):
    assert_pixels('''
        __________
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
        __________
    ''', '''
      <style>
        @page { size: 10px 18px }
        svg { display: block }
      </style>
      <svg width="11px" height="18px" xmlns="http://www.w3.org/2000/svg">
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
        <rect x="0" y="1" width="11" height="16" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_linear_gradient_repeat_long(assert_pixels):
    assert_pixels('''
        __________
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
        __________
    ''', '''
      <style>
        @page { size: 10px 18px }
        svg { display: block }
      </style>
      <svg width="11px" height="18px" xmlns="http://www.w3.org/2000/svg">
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
        <rect x="0" y="1" width="11" height="16" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_linear_gradient_repeat_userspace(assert_pixels):
    assert_pixels('''
        __________
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
        __________
    ''', '''
      <style>
        @page { size: 10px 18px }
        svg { display: block }
      </style>
      <svg width="11px" height="18px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="grad" x1="0" y1="1" x2="0" y2="9"
            gradientUnits="userSpaceOnUse" spreadMethod="repeat">
            <stop stop-color="blue" offset="25%"></stop>
            <stop stop-color="red" offset="25%"></stop>
            <stop stop-color="red" offset="50%"></stop>
            <stop stop-color="lime" offset="50%"></stop>
            <stop stop-color="lime" offset="75%"></stop>
            <stop stop-color="rgb(128,0,128)" offset="75%"></stop>
          </linearGradient>
        </defs>
        <rect x="0" y="1" width="11" height="16" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_linear_gradient_reflect(assert_pixels):
    assert_pixels('''
        __________
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
        __________
    ''', '''
      <style>
        @page { size: 10px 18px }
        svg { display: block }
      </style>
      <svg width="11px" height="18px" xmlns="http://www.w3.org/2000/svg">
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
        <rect x="0" y="1" width="11" height="16" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_linear_gradient_reflect_userspace(assert_pixels):
    assert_pixels('''
        __________
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
        __________
    ''', '''
      <style>
        @page { size: 10px 18px }
        svg { display: block }
      </style>
      <svg width="11px" height="18px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="grad" x1="0" y1="1" x2="0" y2="9"
            gradientUnits="userSpaceOnUse" spreadMethod="reflect">
            <stop stop-color="blue" offset="25%"></stop>
            <stop stop-color="red" offset="25%"></stop>
            <stop stop-color="red" offset="50%"></stop>
            <stop stop-color="lime" offset="50%"></stop>
            <stop stop-color="lime" offset="75%"></stop>
            <stop stop-color="rgb(128,0,128)" offset="75%"></stop>
          </linearGradient>
        </defs>
        <rect x="0" y="1" width="11" height="16" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_linear_gradient_inherit_attributes(assert_pixels):
    assert_pixels('''
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
          <linearGradient id="parent" x1="0" y1="0" x2="0" y2="1"
            gradientUnits="objectBoundingBox">
          </linearGradient>
          <linearGradient id="grad" href="#parent">
            <stop stop-color="blue" offset="50%"></stop>
            <stop stop-color="red" offset="50%"></stop>
          </linearGradient>
        </defs>
        <rect x="0" y="0" width="10" height="10" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_linear_gradient_inherit_children(assert_pixels):
    assert_pixels('''
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
          <linearGradient id="parent">
            <stop stop-color="blue" offset="50%"></stop>
            <stop stop-color="red" offset="50%"></stop>
          </linearGradient>
          <linearGradient id="grad" href="#parent"
            x1="0" y1="0" x2="0" y2="1" gradientUnits="objectBoundingBox">
          </linearGradient>
        </defs>
        <rect x="0" y="0" width="10" height="10" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_linear_gradient_inherit_no_override(assert_pixels):
    assert_pixels('''
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
          <linearGradient id="parent"
            x1="1" y1="1" x2="1" y2="0" gradientUnits="userSpaceOnUse">
            <stop stop-color="red" offset="50%"></stop>
            <stop stop-color="blue" offset="50%"></stop>
          </linearGradient>
          <linearGradient id="grad" href="#parent"
            x1="0" y1="0" x2="0" y2="1" gradientUnits="objectBoundingBox">
            <stop stop-color="blue" offset="50%"></stop>
            <stop stop-color="red" offset="50%"></stop>
          </linearGradient>
        </defs>
        <rect x="0" y="0" width="10" height="10" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_radial_gradient(assert_pixels):
    assert_pixels('''
        ____________
        _rrrrrrrrrr_
        _rrrrrrrrrr_
        _rrrrBBrrrr_
        _rrrBBBBrrr_
        _rrBBBBBBrr_
        _rrBBBBBBrr_
        _rrrBBBBrrr_
        _rrrrBBrrrr_
        _rrrrrrrrrr_
        _rrrrrrrrrr_
        ____________
    ''', '''
      <style>
        @page { size: 12px }
        svg { display: block }
      </style>
      <svg width="12px" height="12px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <radialGradient id="grad" cx="0.5" cy="0.5" r="0.5"
            fx="0.5" fy="0.5" fr="0.2"
            gradientUnits="objectBoundingBox">
            <stop stop-color="blue" offset="25%"></stop>
            <stop stop-color="red" offset="25%"></stop>
          </radialGradient>
        </defs>
        <rect x="1" y="1" width="10" height="10" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_radial_gradient_userspace(assert_pixels):
    assert_pixels('''
        ____________
        _rrrrrrrrrr_
        _rrrrrrrrrr_
        _rrrrBBrrrr_
        _rrrBBBBrrr_
        _rrBBBBBBrr_
        _rrBBBBBBrr_
        _rrrBBBBrrr_
        _rrrrBBrrrr_
        _rrrrrrrrrr_
        _rrrrrrrrrr_
        ____________
    ''', '''
      <style>
        @page { size: 12px }
        svg { display: block }
      </style>
      <svg width="12px" height="12px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <radialGradient id="grad" cx="6" cy="6" r="5" fx="6" fy="6" fr="2"
            gradientUnits="userSpaceOnUse">
            <stop stop-color="blue" offset="25%"></stop>
            <stop stop-color="red" offset="25%"></stop>
          </radialGradient>
        </defs>
        <rect x="1" y="1" width="10" height="10" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_radial_gradient_multicolor(assert_pixels):
    assert_pixels('''
        ____________
        _rrrrrrrrrr_
        _rrrGGGGrrr_
        _rrGGBBGGrr_
        _rGGBBBBGGr_
        _rGBBBBBBGr_
        _rGBBBBBBGr_
        _rGGBBBBGGr_
        _rrGGBBGGrr_
        _rrrGGGGrrr_
        _rrrrrrrrrr_
        ____________
    ''', '''
      <style>
        @page { size: 12px }
        svg { display: block }
      </style>
      <svg width="12px" height="12px" xmlns="http://www.w3.org/2000/svg">
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
        <rect x="1" y="1" width="10" height="10" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_radial_gradient_multicolor_userspace(assert_pixels):
    assert_pixels('''
        ____________
        _rrrrrrrrrr_
        _rrrGGGGrrr_
        _rrGGBBGGrr_
        _rGGBBBBGGr_
        _rGBBBBBBGr_
        _rGBBBBBBGr_
        _rGGBBBBGGr_
        _rrGGBBGGrr_
        _rrrGGGGrrr_
        _rrrrrrrrrr_
        ____________
    ''', '''
      <style>
        @page { size: 12px }
        svg { display: block }
      </style>
      <svg width="12px" height="12px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <radialGradient id="grad" cx="6" cy="6" r="5"
            fx="6" fy="6" fr="2"
            gradientUnits="userSpaceOnUse">
            <stop stop-color="blue" offset="33%"></stop>
            <stop stop-color="lime" offset="33%"></stop>
            <stop stop-color="lime" offset="66%"></stop>
            <stop stop-color="red" offset="66%"></stop>
          </radialGradient>
        </defs>
        <rect x="1" y="1" width="10" height="10" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_radial_gradient_repeat(assert_pixels):
    assert_pixels('''
        ____________
        _GBBrrrrBBG_
        _BrrGGGGrrB_
        _BrGBBBBGrB_
        _rGBBrrBBGr_
        _rGBrGGrBGr_
        _rGBrGGrBGr_
        _rGBBrrBBGr_
        _BrGBBBBGrB_
        _BrrGGGGrrB_
        _GBBrrrrBBG_
        ____________
    ''', '''
      <style>
        @page { size: 12px }
        svg { display: block }
      </style>
      <svg width="12px" height="12px" xmlns="http://www.w3.org/2000/svg">
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
        <rect x="1" y="1" width="10" height="10" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_radial_gradient_reflect(assert_pixels):
    assert_pixels('''
        ____________
        _GrrrrrrrrG_
        _rrrGGGGrrr_
        _rrGBBBBGrr_
        _rGBBBBBBGr_
        _rGBBGGBBGr_
        _rGBBGGBBGr_
        _rGBBBBBBGr_
        _rrGBBBBGrr_
        _rrrGGGGrrr_
        _GrrrrrrrrG_
        ____________
    ''', '''
      <style>
        @page { size: 12px }
        svg { display: block }
      </style>
      <svg width="12px" height="12px" xmlns="http://www.w3.org/2000/svg">
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
        <rect x="1" y="1" width="10" height="10" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_radial_gradient_inherit_attributes(assert_pixels):
    assert_pixels('''
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
          <radialGradient id="parent" cx="0.5" cy="0.5" r="0.5"
            fx="0.5" fy="0.5" fr="0.2"
            gradientUnits="objectBoundingBox">
          </radialGradient>
          <radialGradient id="grad" href="#parent">
            <stop stop-color="blue" offset="25%"></stop>
            <stop stop-color="red" offset="25%"></stop>
          </radialGradient>
        </defs>
        <rect x="0" y="0" width="10" height="10" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_radial_gradient_inherit_children(assert_pixels):
    assert_pixels('''
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
          <radialGradient id="parent">
            <stop stop-color="blue" offset="25%"></stop>
            <stop stop-color="red" offset="25%"></stop>
          </radialGradient>
          <radialGradient id="grad" href="#parent"
            cx="0.5" cy="0.5" r="0.5" fx="0.5" fy="0.5" fr="0.2"
            gradientUnits="objectBoundingBox">
          </radialGradient>
        </defs>
        <rect x="0" y="0" width="10" height="10" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_radial_gradient_inherit_no_override(assert_pixels):
    assert_pixels('''
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
          <radialGradient id="parent" cx="5" cy="5" r="5" fx="5" fy="5" fr="2"
            gradientUnits="userSpaceOnUse">
            <stop stop-color="red" offset="25%"></stop>
            <stop stop-color="blue" offset="25%"></stop>
          </radialGradient>
          <radialGradient id="grad" href="#parent" cx="0.5" cy="0.5" r="0.5"
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
def test_gradient_opacity(assert_pixels):
    assert_pixels('''
        BBBBBBBBBB
        BBBBBBBBBB
        BBBBBBBBBB
        BBBBBBBBBB
        BBBBBBBBBB
        ssssssssss
        ssssssssss
        ssssssssss
        ssssssssss
        ssssssssss
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
            <stop stop-color="red" stop-opacity="0.502" offset="50%"></stop>
          </linearGradient>
        </defs>
        <rect x="0" y="0" width="10" height="10" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
@pytest.mark.parametrize('url', ('#grad\'', '\'#gra', '!', '#'))
def test_gradient_bad_url(assert_pixels, url):
    assert_pixels('''
        __________
        __________
        __________
        __________
        __________
        __________
        __________
        __________
        __________
        __________
    ''', '''
      <style>
        @page { size: 10px }
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1"
            gradientUnits="objectBoundingBox">
            <stop stop-color="blue"></stop>
          </linearGradient>
        </defs>
        <rect x="0" y="0" width="10" height="10" fill="url(%s)" />
      </svg>
    ''' % url)
