"""
    weasyprint.tests.test_draw.svg.test_visibility
    ----------------------------------------------

    Test how the visibility is controlled with "visibility" and "display"
    attributes.

"""

from ...testing_utils import assert_no_logs
from .. import assert_pixels


@assert_no_logs
def test_visibility_visible():
    assert_pixels('visibility_visible', 9, 9, '''
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
        <rect visibility="visible"
              x="2" y="2" width="5" height="5" fill="red" />
      </svg>
    ''')


@assert_no_logs
def test_visibility_hidden():
    assert_pixels('visibility_hidden', 9, 9, '''
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
        <rect visibility="hidden"
              x="2" y="2" width="5" height="5" fill="red" />
      </svg>
    ''')


@assert_no_logs
def test_visibility_inherit_hidden():
    assert_pixels('visibility_inherit_hidden', 9, 9, '''
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
        <g visibility="hidden">
          <rect x="2" y="2" width="5" height="5" fill="red" />
        </g>
      </svg>
    ''')


@assert_no_logs
def test_visibility_inherit_visible():
    assert_pixels('visibility_inherit_visible', 9, 9, '''
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
        <g visibility="hidden">
          <rect visibility="visible"
                x="2" y="2" width="5" height="5" fill="red" />
        </g>
      </svg>
    ''')


@assert_no_logs
def test_display_inline():
    assert_pixels('display_inline', 9, 9, '''
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
        <rect display="inline"
              x="2" y="2" width="5" height="5" fill="red" />
      </svg>
    ''')


@assert_no_logs
def test_display_none():
    assert_pixels('display_none', 9, 9, '''
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
        <rect display="none"
              x="2" y="2" width="5" height="5" fill="red" />
      </svg>
    ''')


@assert_no_logs
def test_display_inherit_none():
    assert_pixels('display_inherit_none', 9, 9, '''
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
        <g display="none">
          <rect x="2" y="2" width="5" height="5" fill="red" />
        </g>
      </svg>
    ''')


@assert_no_logs
def test_display_inherit_inline():
    assert_pixels('display_inherit_inline', 9, 9, '''
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
        <g display="none">
          <rect display="inline"
                x="2" y="2" width="5" height="5" fill="red" />
        </g>
      </svg>
    ''')
