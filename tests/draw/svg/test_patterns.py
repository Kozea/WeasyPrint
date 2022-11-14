"""Test how SVG simple patterns are drawn."""

from ...testing_utils import assert_no_logs


@assert_no_logs
def test_pattern(assert_pixels):
    assert_pixels('''
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
def test_pattern_2(assert_pixels):
    assert_pixels('''
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
def test_pattern_3(assert_pixels):
    assert_pixels('''
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
def test_pattern_4(assert_pixels):
    assert_pixels('''
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


@assert_no_logs
def test_pattern_inherit_attributes(assert_pixels):
    assert_pixels('''
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
          <pattern id="parent" x="0" y="0" width="4" height="4"
            patternUnits="userSpaceOnUse"
            patternContentUnits="userSpaceOnUse">
          </pattern>
          <pattern id="pat" href="#parent">
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
def test_pattern_inherit_children(assert_pixels):
    assert_pixels('''
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
          <pattern id="parent">
            <rect x="0" y="0" width="2" height="2" fill="blue" />
            <rect x="0" y="2" width="2" height="2" fill="red" />
            <rect x="2" y="0" width="2" height="2" fill="red" />
            <rect x="2" y="2" width="2" height="2" fill="blue" />
          </pattern>
          <pattern id="pat" href="#parent" x="0" y="0" width="4" height="4"
            patternUnits="userSpaceOnUse" patternContentUnits="userSpaceOnUse">
          </pattern>
        </defs>
        <rect x="0" y="0" width="8" height="8" fill="url(#pat)" />
      </svg>
    ''')


@assert_no_logs
def test_pattern_inherit_no_override(assert_pixels):
    assert_pixels('''
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
          <pattern id="parent" x="1" y="1" width="3" height="3"
            patternUnits="objectBoundingBox"
            patternContentUnits="objectBoundingBox">
            <rect x="0" y="0" width="2" height="2" fill="green" />
            <rect x="0" y="2" width="2" height="2" fill="green" />
            <rect x="2" y="0" width="2" height="2" fill="yellow" />
            <rect x="2" y="2" width="2" height="2" fill="yellow" />
          </pattern>
          <pattern id="pat" href="#parent" x="0" y="0" width="4" height="4"
            patternUnits="userSpaceOnUse" patternContentUnits="userSpaceOnUse">
            <rect x="0" y="0" width="2" height="2" fill="blue" />
            <rect x="0" y="2" width="2" height="2" fill="red" />
            <rect x="2" y="0" width="2" height="2" fill="red" />
            <rect x="2" y="2" width="2" height="2" fill="blue" />
          </pattern>
        </defs>
        <rect x="0" y="0" width="8" height="8" fill="url(#pat)" />
      </svg>
    ''')
