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
