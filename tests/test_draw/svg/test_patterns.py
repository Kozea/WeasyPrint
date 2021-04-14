"""
    weasyprint.tests.test_draw.svg.test_patterns
    ------------------------------------------

    Test how SVG simple patterns are drawn.

"""

from ...testing_utils import assert_no_logs
from .. import assert_pixels


@assert_no_logs
def test_pattern():
    assert_pixels('pattern', 8, 8, '''
        BBrrBBrr
        BBrrBBrr
        rrBBrrBB
        rrBBrrBB
        BBrrBBrr
        BBrrBBrr
        rrBBrrBB
        rrBBrrBB
    ''', '''
      <style>
        @page { size: 8px }
        svg { display: block }
      </style>
      <svg width="8px" height="8px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="pat" x="0" y="0" width="4" height="4"
            patternUnits="userSpaceOnUse"
            patternContentUnits="userSpaceOnUse">
            <rect x="0" y="0" width="2" height="2" fill="blue" />
            <rect x="0" y="2" width="2" height="2" fill="red" />
            <rect x="2" y="0" width="2" height="2" fill="red" />
            <rect x="2" y="2" width="2" height="2" fill="blue" />
          </pattern>
        </defs>
        <rect x="0" y="0" width="8" height="8" fill="url(#pat)" />
      </svg>
    ''')


@assert_no_logs
def test_pattern_2():
    assert_pixels('pattern_2', 8, 8, '''
        BBrrBBrr
        BBrrBBrr
        rrBBrrBB
        rrBBrrBB
        BBrrBBrr
        BBrrBBrr
        rrBBrrBB
        rrBBrrBB
    ''', '''
      <style>
        @page { size: 8px }
        svg { display: block }
      </style>
      <svg width="8px" height="8px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="pat" x="0" y="0" width="50%" height="50%"
            patternUnits="objectBoundingBox"
            patternContentUnits="userSpaceOnUse">
            <rect x="0" y="0" width="2" height="2" fill="blue" />
            <rect x="0" y="2" width="2" height="2" fill="red" />
            <rect x="2" y="0" width="2" height="2" fill="red" />
            <rect x="2" y="2" width="2" height="2" fill="blue" />
          </pattern>
        </defs>
        <rect x="0" y="0" width="8" height="8" fill="url(#pat)" />
      </svg>
    ''')


@assert_no_logs
def test_pattern_3():
    assert_pixels('pattern_3', 8, 8, '''
        BBrrBBrr
        BBrrBBrr
        rrBBrrBB
        rrBBrrBB
        BBrrBBrr
        BBrrBBrr
        rrBBrrBB
        rrBBrrBB
    ''', '''
      <style>
        @page { size: 8px }
        svg { display: block }
      </style>
      <svg width="8px" height="8px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="pat" x="0" y="0" width="4" height="4"
            patternUnits="userSpaceOnUse"
            patternContentUnits="userSpaceOnUse">
            <rect x="0" y="0" width="2" height="2" fill="blue" />
            <rect x="0" y="2" width="2" height="2" fill="red" />
            <rect x="2" y="0" width="2" height="2" fill="red" />
            <rect x="2" y="2" width="2" height="2" fill="blue" />
          </pattern>
        </defs>
        <rect x="0" y="0" width="8" height="8" fill="url(#pat)" />
      </svg>
    ''')


@assert_no_logs
def test_pattern_4():
    assert_pixels('pattern_4', 8, 8, '''
        BBrrBBrr
        BBrrBBrr
        rrBBrrBB
        rrBBrrBB
        BBrrBBrr
        BBrrBBrr
        rrBBrrBB
        rrBBrrBB
    ''', '''
      <style>
        @page { size: 8px }
        svg { display: block }
      </style>
      <svg width="8px" height="8px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="pat" x="0" y="0" width="4" height="4"
            patternUnits="userSpaceOnUse"
            patternContentUnits="objectBoundingBox">
            <rect x="0" y="0" width="50%" height="50%" fill="blue" />
            <rect x="0" y="50%" width="50%" height="50%" fill="red" />
            <rect x="50%" y="0" width="50%" height="50%" fill="red" />
            <rect x="50%" y="50%" width="50%" height="50%" fill="blue" />
          </pattern>
        </defs>
        <rect x="0" y="0" width="8" height="8" fill="url(#pat)" />
      </svg>
    ''')
