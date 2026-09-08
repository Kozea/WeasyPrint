"""Test SVG units."""

from ...testing_utils import assert_no_logs


@assert_no_logs
def test_units_px(assert_pixels):
    assert_pixels('''
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
        <rect x="2px" y="2px" width="5px" height="5px"
              stroke-width="2px" stroke="red" fill="none" />
      </svg>
    ''')


@assert_no_logs
def test_units_em(assert_pixels):
    assert_pixels('''
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
      <svg width="9px" height="9px" font-size="1px"
           xmlns="http://www.w3.org/2000/svg">
        <rect x="2em" y="2em" width="5em" height="5em"
              stroke-width="2em" stroke="red" fill="none" />
      </svg>
    ''')


@assert_no_logs
def test_units_ex(assert_pixels):
    assert_pixels('''
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
      <svg width="9px" height="9px" font-size="1px"
           xmlns="http://www.w3.org/2000/svg">
        <rect x="4ex" y="4ex" width="10ex" height="10ex"
              stroke-width="4ex" stroke="red" fill="none" />
      </svg>
    ''')


@assert_no_logs
def test_units_unknown(assert_pixels):
    assert_pixels('''
        _RRRRRRR_
        _RR___RR_
        _RR___RR_
        _RR___RR_
        _RRRRRRR_
        _RRRRRRR_
        _________
        _________
        _________
    ''', '''
      <style>
        @page { size: 9px }
        svg { display: block }
      </style>
      <svg width="9px" height="9px" xmlns="http://www.w3.org/2000/svg">
        <rect x="2px" y="2unk" width="5px" height="5px"
              stroke-width="2px" stroke="red" fill="none" />
      </svg>
    ''')


@assert_no_logs
def test_units_percentage(assert_pixels):
    assert_pixels('''
        ________
        ________
        ________
        ________
        ____BB__
        ____BB__
        ________
        ________
    ''', '''
      <style>
        @page { size: 8px }
        svg { display: block }
      </style>
      <svg width="8px" height="8px" xmlns="http://www.w3.org/2000/svg">
        <rect x="50%" y="50%" width="2" height="2" fill="blue" />
      </svg>
    ''')


@assert_no_logs
def test_units_percentage_after_nested_svg(assert_pixels):
    # Percentages must be resolved against the current viewport, not against
    # the viewport of a nested "svg" tag that has already been drawn.
    assert_pixels('''
        RR______
        RR______
        ________
        ________
        ____BB__
        ____BB__
        ________
        ________
    ''', '''
      <style>
        @page { size: 8px }
        svg { display: block }
      </style>
      <svg width="8px" height="8px" xmlns="http://www.w3.org/2000/svg">
        <svg width="100%" height="100%" viewBox="0 0 4 4">
          <rect width="1" height="1" fill="red" />
        </svg>
        <rect x="50%" y="50%" width="2" height="2" fill="blue" />
      </svg>
    ''')


@assert_no_logs
def test_units_percentage_sibling_nested_svg(assert_pixels):
    # Each nested "svg" tag must resolve its own percentages against the
    # parent viewport, including when a sibling has been drawn before.
    assert_pixels('''
        ________
        ________
        __RR____
        __RR____
        ____BB__
        ____BB__
        ________
        ________
    ''', '''
      <style>
        @page { size: 8px }
        svg { display: block }
      </style>
      <svg width="8px" height="8px" xmlns="http://www.w3.org/2000/svg">
        <svg x="25%" y="25%" width="1" height="1" overflow="visible">
          <rect width="2" height="2" fill="red" />
        </svg>
        <svg x="50%" y="50%" width="1" height="1" overflow="visible">
          <rect width="2" height="2" fill="blue" />
        </svg>
      </svg>
    ''')
