"""
    weasyprint.tests.test_draw.svg.test_paths
    ------------------------------------------

    Test how SVG simple paths are drawn.

"""

from ...testing_utils import assert_no_logs
from .. import assert_pixels


@assert_no_logs
def test_path_Hh():
    assert_pixels('path_Hh', 10, 10, '''
        BBBBBBBB__
        BBBBBBBB__
        __________
        RRRRRRRR__
        RRRRRRRR__
        __________
        GGGGGGGG__
        GGGGGGGG__
        BBBBBBBB__
        BBBBBBBB__
    ''', '''
      <style>
        @page { size: 10px }
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <path d="M 0 1 H 8 H 1"
          stroke="blue" stroke-width="2" fill="none"/>
        <path d="M 0 4 H 8 4"
          stroke="red" stroke-width="2" fill="none"/>
        <path d="M 0 7 h 8 h 0"
          stroke="lime" stroke-width="2" fill="none"/>
        <path d="M 0 9 h 8 0"
          stroke="blue" stroke-width="2" fill="none"/>
      </svg>
    ''')


@assert_no_logs
def test_path_Vv():
    assert_pixels('path_Vv', 10, 10, '''
        BB____GG__
        BB____GG__
        BB____GG__
        BB____GG__
        ___RR_____
        ___RR_____
        ___RR___BB
        ___RR___BB
        ___RR___BB
        ___RR___BB
    ''', '''
      <style>
        @page { size: 10px }
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <path d="M 1 0 V 1 V 4"
          stroke="blue" stroke-width="2" fill="none"/>
        <path d="M 4 6 V 4 10"
          stroke="red" stroke-width="2" fill="none"/>
        <path d="M 7 0 v 0 v 4"
          stroke="lime" stroke-width="2" fill="none"/>
        <path d="M 9 6 v 0 4"
          stroke="blue" stroke-width="2" fill="none"/>
      </svg>
    ''')


@assert_no_logs
def test_path_Ll():
    assert_pixels('path_Ll', 10, 10, '''
        ______RR__
        ______RR__
        ______RR__
        ___BB_RR__
        ___BB_RR__
        ___BB_RR__
        ___BB_____
        ___BB_____
        ___BB_____
        ___BB_____
    ''', '''
      <style>
        @page { size: 10px }
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <path d="M 4 3 L 4 10"
          stroke="blue" stroke-width="2" fill="none"/>
        <path d="M 7 0 l 0 6"
          stroke="red" stroke-width="2" fill="none"/>
      </svg>
    ''')


@assert_no_logs
def test_path_Zz():
    assert_pixels('path_Zz', 10, 10, '''
        BBBBBBB___
        BBBBBBB___
        BB___BB___
        BB___BB___
        BBBBBBB___
        BBBBBBB___
        ____RRRRRR
        ____RRRRRR
        ____RR__RR
        ____RRRRRR
    ''', '''
      <style>
        @page { size: 10px }
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <path d="M 1 1 H 6 V 5 H 1 Z"
          stroke="blue" stroke-width="2" fill="none"/>
        <path d="M 9 10 V 7 H 5 V 10 z"
          stroke="red" stroke-width="2" fill="none"/>
      </svg>
    ''')


@assert_no_logs
def test_path_Zz_fill():
    assert_pixels('path_Zz_fill', 10, 10, '''
        BBBBBBB___
        BBBBBBB___
        BBGGGBB___
        BBGGGBB___
        BBBBBBB___
        BBBBBBB___
        ____RRRRRR
        ____RRRRRR
        ____RRGGRR
        ____RRRRRR
    ''', '''
      <style>
        @page { size: 10px }
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <path d="M 1 1 H 6 V 5 H 1 Z"
          stroke="blue" stroke-width="2" fill="lime"/>
        <path d="M 9 10 V 7 H 5 V 10 z"
          stroke="red" stroke-width="2" fill="lime"/>
      </svg>
    ''')
