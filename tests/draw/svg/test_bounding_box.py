"""
    weasyprint.tests.test_draw.svg.test_bounding_box
    ------------------------------------------------

    Test how bounding boxes are defined for SVG tags.

"""

import pytest

from ...testing_utils import assert_no_logs
from .. import assert_pixels


@assert_no_logs
def test_bounding_box_rect():
    assert_pixels('bounding_box_rect', 5, 5, '''
        BBBBB
        BBBBR
        BBBRR
        BBRRR
        BRRRR
    ''', '''
      <style>
        @page { size: 5px }
        svg { display: block }
      </style>
      <svg width="5px" height="5px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="1" y2="1"
            gradientUnits="objectBoundingBox">
            <stop stop-color="blue" offset="55%"></stop>
            <stop stop-color="red" offset="55%"></stop>
          </linearGradient>
        </defs>
        <rect x="0" y="0" width="5" height="5" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_bounding_box_circle():
    assert_pixels('bounding_box_circle', 10, 10, '''
        __________
        __BBBBBB__
        _BBBBBBBR_
        _BBBBBBRR_
        _BBBBBRRR_
        _BBBBRRRR_
        _BBBRRRRR_
        _BBRRRRRR_
        __RRRRRR__
        __________
    ''', '''
      <style>
        @page { size: 10px }
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="1" y2="1"
            gradientUnits="objectBoundingBox">
            <stop stop-color="blue" offset="55%"></stop>
            <stop stop-color="red" offset="55%"></stop>
          </linearGradient>
        </defs>
        <circle cx="5" cy="5" r="4" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_bounding_box_ellipse():
    assert_pixels('bounding_box_ellipse', 10, 10, '''
        __________
        __BBBBBB__
        _BBBBBBBR_
        _BBBBBBRR_
        _BBBBBRRR_
        _BBBBRRRR_
        _BBBRRRRR_
        _BBRRRRRR_
        __RRRRRR__
        __________
    ''', '''
      <style>
        @page { size: 10px }
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="1" y2="1"
            gradientUnits="objectBoundingBox">
            <stop stop-color="blue" offset="55%"></stop>
            <stop stop-color="red" offset="55%"></stop>
          </linearGradient>
        </defs>
        <ellipse cx="5" cy="5" rx="4" ry="4" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_bounding_box_line():
    assert_pixels('bounding_box_line', 5, 5, '''
        BB___
        BBB__
        _BBR_
        __RRR
        ___RR
    ''', '''
      <style>
        @page { size: 5px }
        svg { display: block }
      </style>
      <svg width="5px" height="5px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="1" y2="1"
            gradientUnits="objectBoundingBox">
            <stop stop-color="blue" offset="60%"></stop>
            <stop stop-color="red" offset="60%"></stop>
          </linearGradient>
        </defs>
        <line x1="0" y1="0" x2="5" y2="5"
              stroke-width="1" stroke="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_bounding_box_polygon():
    assert_pixels('bounding_box_polygon', 5, 5, '''
        BBBBB
        BBBBR
        BBBRR
        BBRRR
        BRRRR
    ''', '''
      <style>
        @page { size: 5px }
        svg { display: block }
      </style>
      <svg width="5px" height="5px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="1" y2="1"
            gradientUnits="objectBoundingBox">
            <stop stop-color="blue" offset="55%"></stop>
            <stop stop-color="red" offset="55%"></stop>
          </linearGradient>
        </defs>
        <polygon points="0 0 0 5 5 5 5 0" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_bounding_box_polyline():
    assert_pixels('bounding_box_polyline', 5, 5, '''
        BBBBB
        BBBBR
        BBBRR
        BBRRR
        BRRRR
    ''', '''
      <style>
        @page { size: 5px }
        svg { display: block }
      </style>
      <svg width="5px" height="5px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="1" y2="1"
            gradientUnits="objectBoundingBox">
            <stop stop-color="blue" offset="55%"></stop>
            <stop stop-color="red" offset="55%"></stop>
          </linearGradient>
        </defs>
        <polyline points="0 0 0 5 5 5 5 0" fill="url(#grad)" />
      </svg>
    ''')


@pytest.mark.xfail
@assert_no_logs
def test_bounding_box_text():
    assert_pixels('bounding_box_text', 2, 2, '''
        BB
        BR
    ''', '''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 2px }
        svg { display: block }
      </style>
      <svg width="2px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="1" y2="1"
            gradientUnits="objectBoundingBox">
            <stop stop-color="blue" offset="55%"></stop>
            <stop stop-color="red" offset="55%"></stop>
          </linearGradient>
        </defs>
        <text x="0" y="1" font-family="weasyprint" font-size="2"
              fill="url(#grad)">
          A
        </text>
      </svg>
    ''')


@assert_no_logs
def test_bounding_box_path_hv():
    assert_pixels('bounding_box_path_hv', 5, 5, '''
        BBBBB
        BBBBR
        BBBRR
        BBRRR
        BRRRR
    ''', '''
      <style>
        @page { size: 5px }
        svg { display: block }
      </style>
      <svg width="5px" height="5px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="1" y2="1"
            gradientUnits="objectBoundingBox">
            <stop stop-color="blue" offset="55%"></stop>
            <stop stop-color="red" offset="55%"></stop>
          </linearGradient>
        </defs>
        <path d="m 5 0 v 5 h -5 V 0 H 5 z" fill="url(#grad)" />
      </svg>
    ''')


@assert_no_logs
def test_bounding_box_path_l():
    assert_pixels('bounding_box_path_l', 5, 5, '''
        BBBBB
        BBBBR
        BBBRR
        BBRRR
        BRRRR
    ''', '''
      <style>
        @page { size: 5px }
        svg { display: block }
      </style>
      <svg width="5px" height="5px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="1" y2="1"
            gradientUnits="objectBoundingBox">
            <stop stop-color="blue" offset="55%"></stop>
            <stop stop-color="red" offset="55%"></stop>
          </linearGradient>
        </defs>
        <path d="M 5 0 l 0 5 l -5 0 L 0 0 z" fill="url(#grad)" />
      </svg>
    ''')


@pytest.mark.xfail
@assert_no_logs
def test_bounding_box_path_c():
    assert_pixels('bounding_box_path_c', 5, 5, '''
        BBB__
        BBR__
        _____
        BBB__
        BBR__
    ''', '''
      <style>
        @page { size: 5px }
        svg { display: block }
      </style>
      <svg width="5px" height="5px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="1" y2="1"
            gradientUnits="objectBoundingBox">
            <stop stop-color="blue" offset="55%"></stop>
            <stop stop-color="red" offset="55%"></stop>
          </linearGradient>
        </defs>
        <g fill="none" stroke="url(#grad)" stroke-width="2">
          <path d="M 0 1 C 0 1 1 1 3 1" />
          <path d="M 0 4 c 0 0 1 0 3 0" />
        </g>
      </svg>
    ''')


@pytest.mark.xfail
@assert_no_logs
def test_bounding_box_path_s():
    assert_pixels('bounding_box_path_s', 5, 5, '''
        BBB__
        BBR__
        _____
        BBB__
        BBR__
    ''', '''
      <style>
        @page { size: 5px }
        svg { display: block }
      </style>
      <svg width="5px" height="5px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="1" y2="1"
            gradientUnits="objectBoundingBox">
            <stop stop-color="blue" offset="55%"></stop>
            <stop stop-color="red" offset="55%"></stop>
          </linearGradient>
        </defs>
        <g fill="none" stroke="url(#grad)" stroke-width="2">
          <path d="M 0 1 S 1 1 3 1" />
          <path d="M 0 4 s 1 0 3 0" />
        </g>
      </svg>
    ''')
