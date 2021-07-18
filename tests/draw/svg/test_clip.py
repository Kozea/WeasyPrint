"""
    weasyprint.tests.test_draw.svg.test_clip
    ----------------------------------------

    Test clip-path attribute.

"""

import pytest

from ...testing_utils import assert_no_logs
from .. import assert_pixels


@assert_no_logs
def test_clip_path():
    assert_pixels('clip_path', 9, 9, '''
        _________
        _________
        __RRRRR__
        __RBBBR__
        __RBBBR__
        __RBBBR__
        __RRRRR__
        _________
        _________
    ''', '''
      <style>
        @page { size: 9px }
        svg { display: block }
      </style>
      <svg width="9px" height="9px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <clipPath id="clip">
            <rect x="2" y="2" width="5" height="5" />
          </clipPath>
        </defs>
        <rect x="2" y="2" width="5" height="5" stroke-width="2"
              stroke="red" fill="blue" clip-path="url(#clip)" />
      </svg>
    ''')


@assert_no_logs
def test_clip_path_on_group():
    assert_pixels('clip_path_on_group', 9, 9, '''
        _________
        _________
        __BBBB___
        __BRRRR__
        __BRRRR__
        __BRRRR__
        ___RRRR__
        _________
        _________
    ''', '''
      <style>
        @page { size: 9px }
        svg { display: block }
      </style>
      <svg width="9px" height="9px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <clipPath id="clip">
            <rect x="2" y="2" width="5" height="5" />
          </clipPath>
        </defs>
        <g clip-path="url(#clip)">
          <rect x="1" y="1" width="5" height="5" fill="blue" />
          <rect x="3" y="3" width="5" height="5" fill="red" />
        </g>
      </svg>
    ''')


@pytest.mark.xfail
@assert_no_logs
def test_clip_path_group_on_group():
    assert_pixels('clip_path_group_on_group', 9, 9, '''
        _________
        _________
        __BB_____
        __BR_____
        _________
        _____RR__
        _____RR__
        _________
        _________
    ''', '''
      <style>
        @page { size: 9px }
        svg { display: block }
      </style>
      <svg width="9px" height="9px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <clipPath id="clip">
            <rect x="2" y="2" width="2" height="2" />
            <rect x="3" y="3" width="2" height="2" />
          </clipPath>
        </defs>
        <g clip-path="url(#clip)">
          <rect x="1" y="1" width="5" height="5" fill="blue" />
          <rect x="3" y="3" width="5" height="5" fill="red" />
        </g>
      </svg>
    ''')
