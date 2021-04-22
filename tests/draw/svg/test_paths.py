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


@assert_no_logs
def test_path_Cc():
    assert_pixels('path_Cc', 10, 10, '''
        __________
        __________
        __________
        __________
        __BBB_____
        __BBB_____
        __________
        __RRR_____
        __RRR_____
        __________
    ''', '''
      <style>
        @page { size: 10px }
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <path d="M 2 5 C 2 5 3 5 5 5"
          stroke="blue" stroke-width="2" fill="none"/>
        <path d="M 2 8 c 0 0 1 0 3 0"
          stroke="red" stroke-width="2" fill="none"/>
      </svg>
    ''')


@assert_no_logs
def test_path_Ss():
    assert_pixels('path_Ss', 10, 10, '''
        __________
        __________
        __________
        __________
        __BBB_____
        __BBB_____
        __________
        __RRR_____
        __RRR_____
        __________
    ''', '''
      <style>
        @page { size: 10px }
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <path d="M 2 5 S 3 5 5 5"
          stroke="blue" stroke-width="2" fill="none"/>
        <path d="M 2 8 s 1 0 3 0"
          stroke="red" stroke-width="2" fill="none"/>
      </svg>
    ''')


@assert_no_logs
def test_path_CcSs():
    assert_pixels('path_CcSs', 10, 12, '''
        __BBBBBB__
        __BBBBBBB_
        _____BBBB_
        __RRRRRR__
        __RRRRRRR_
        _____RRRR_
        __GGGGGG__
        __GGGGGGG_
        _____GGGG_
        __BBBBBB__
        __BBBBBBB_
        _____BBBB_
    ''', '''
      <style>
        @page { size: 10px 12px }
        svg { display: block }
      </style>
      <svg width="10px" height="12px" xmlns="http://www.w3.org/2000/svg">
        <path d="M 2 1 C 2 1 3 1 5 1 S 8 3 8 1"
          stroke="blue" stroke-width="2" fill="none"/>
        <path d="M 2 4 C 2 4 3 4 5 4 s 3 2 1 0"
          stroke="red" stroke-width="2" fill="none"/>
        <path d="M 2 7 c 0 0 1 0 3 0 S 8 9 8 7"
          stroke="lime" stroke-width="2" fill="none"/>
        <path d="M 2 10 c 0 0 1 0 3 0 s 3 2 1 0"
          stroke="blue" stroke-width="2" fill="none"/>
      </svg>
    ''')


@assert_no_logs
def test_path_Qq():
    assert_pixels('path_Qq', 10, 10, '''
        __________
        __________
        __________
        __________
        __BBBB____
        __BBBB____
        __________
        __RRRR____
        __RRRR____
        __________
    ''', '''
      <style>
        @page { size: 10px }
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <path d="M 2 5 Q 4 5 6 5"
          stroke="blue" stroke-width="2" fill="none"/>
        <path d="M 2 8 q 2 0 4 0"
          stroke="red" stroke-width="2" fill="none"/>
      </svg>
    ''')


@assert_no_logs
def test_path_Tt():
    assert_pixels('path_Tt', 10, 10, '''
        __________
        __________
        __________
        __________
        __BBBB____
        __BBBB____
        __________
        __RRRR____
        __RRRR____
        __________
    ''', '''
      <style>
        @page { size: 10px }
        svg { display: block }
      </style>
      <svg width="10px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <path d="M 2 5 T 6 5"
          stroke="blue" stroke-width="2" fill="none"/>
        <path d="M 2 8 t 4 0"
          stroke="red" stroke-width="2" fill="none"/>
      </svg>
    ''')


@assert_no_logs
def test_path_QqTt():
    assert_pixels('path_QqTt', 12, 12, '''
        _BBBB_______
        BBBBBBB_____
        BBBBBBBB__BB
        BB__BBBBBBBB
        _____BBBBBBB
        _______BBBB_
        _RRRR_______
        RRRRRRR_____
        RRRRRRRR__RR
        RR__RRRRRRRR
        _____RRRRRRR
        _______RRRR_
    ''', '''
      <style>
        @page { size: 12px }
        svg { display: block }
      </style>
      <svg width="12px" height="12px" xmlns="http://www.w3.org/2000/svg">
        <path d="M 0 3 Q 3 0 6 3 T 12 3"
          stroke="blue" stroke-width="2" fill="none"/>
        <path d="M 0 9 Q 3 6 6 9 t 6 0"
          stroke="red" stroke-width="2" fill="none"/>
      </svg>
    ''')


@assert_no_logs
def test_path_QqTt2():
    assert_pixels('path_QqTt2', 12, 12, '''
        _BBBB_______
        BBBBBBB_____
        BBBBBBBB__BB
        BB__BBBBBBBB
        _____BBBBBBB
        _______BBBB_
        _RRRR_______
        RRRRRRR_____
        RRRRRRRR__RR
        RR__RRRRRRRR
        _____RRRRRRR
        _______RRRR_
    ''', '''
      <style>
        @page { size: 12px }
        svg { display: block }
      </style>
      <svg width="12px" height="12px" xmlns="http://www.w3.org/2000/svg">
        <path d="M 0 3 q 3 -3 6 0 T 12 3"
          stroke="blue" stroke-width="2" fill="none"/>
        <path d="M 0 9 q 3 -3 6 0 t 6 0"
          stroke="red" stroke-width="2" fill="none"/>
      </svg>
    ''')


@assert_no_logs
def test_path_Aa():
    assert_pixels('path_Aa', 12, 12, '''
        __BBBB______
        _BBBBB______
        BBBBBB______
        BBBB________
        BBB_________
        BBB____RRRR_
        ______RRRRR_
        _____RRRRRR_
        _____RRRR___
        _____RRR____
        _____RRR____
        ____________
    ''', '''
      <style>
        @page { size: 12px }
        svg { display: block }
      </style>
      <svg width="12px" height="12px" xmlns="http://www.w3.org/2000/svg">
        <path d="M 1 6 A 5 5 0 0 1 6 1"
          stroke="blue" stroke-width="2" fill="none"/>
        <path d="M 6 11 a 5 5 0 0 1 5 -5"
          stroke="red" stroke-width="2" fill="none"/>
      </svg>
    ''')


@assert_no_logs
def test_path_Aa2():
    assert_pixels('path_Aa2', 12, 12, '''
        ______GGGG__
        ______GGGGG_
        ______GGGGGG
        ________GGGG
        _________GGG
        _________GGG
        GGG______GGG
        GGG______GGG
        GGGG____GGGG
        GGGGGGGGGGGG
        _GGGGGGGGGG_
        __GGGGGGGG__
    ''', '''
      <style>
        @page { size: 12px }
        svg { display: block }
      </style>
      <svg width="12px" height="12px" xmlns="http://www.w3.org/2000/svg">
        <path d="M 1 6 A 5 5 0 1 0 6 1"
          stroke="lime" stroke-width="2" fill="none"/>
      </svg>
    ''')


@assert_no_logs
def test_path_Aa3():
    assert_pixels('path_Aa3', 12, 12, '''
        ______GGGG__
        ______GGGGG_
        ______GGGGGG
        ________GGGG
        _________GGG
        _________GGG
        GGG______GGG
        GGG______GGG
        GGGG____GGGG
        GGGGGGGGGGGG
        _GGGGGGGGGG_
        __GGGGGGGG__
    ''', '''
      <style>
        @page { size: 12px }
        svg { display: block }
      </style>
      <svg width="12px" height="12px" xmlns="http://www.w3.org/2000/svg">
        <path d="M 1 6 a 5 5 0 1 0 5 -5"
          stroke="lime" stroke-width="2" fill="none"/>
      </svg>
    ''')


@assert_no_logs
def test_path_Aa4():
    assert_pixels('path_Aa4', 12, 12, '''
        ____________
        ____BBB_____
        ____BBB_____
        ___BBBB_____
        _BBBBBB_____
        _BBBBB______
        _BBBB____RRR
        _________RRR
        ________RRRR
        ______RRRRRR
        ______RRRRR_
        ______RRRR__
    ''', '''
      <style>
        @page { size: 12px }
        svg { display: block }
      </style>
      <svg width="12px" height="12px" xmlns="http://www.w3.org/2000/svg">
        <path d="M 1 6 A 5 5 0 0 0 6 1"
          stroke="blue" stroke-width="2" fill="none"/>
        <path d="M 6 11 a 5 5 0 0 0 5 -5"
          stroke="red" stroke-width="2" fill="none"/>
      </svg>
    ''')


@assert_no_logs
def test_path_Aa5():
    assert_pixels('path_Aa5', 12, 12, '''
        __BBBBBBBB__
        _BBBBBBBBBB_
        BBBBBBBBBBBB
        BBBB____BBBB
        BBB______BBB
        BBB______BBB
        BBB_________
        BBB_________
        BBBB________
        BBBBBB______
        _BBBBB______
        __BBBB______
    ''', '''
      <style>
        @page { size: 12px }
        svg { display: block }
      </style>
      <svg width="12px" height="12px" xmlns="http://www.w3.org/2000/svg">
        <path d="M 6 11 A 5 5 0 1 1 11 6"
          stroke="blue" stroke-width="2" fill="none"/>
      </svg>
    ''')


@assert_no_logs
def test_path_Aa6():
    assert_pixels('path_Aa6', 12, 12, '''
        __BBBBBBBB__
        _BBBBBBBBBB_
        BBBBBBBBBBBB
        BBBB____BBBB
        BBB______BBB
        BBB______BBB
        BBB_________
        BBB_________
        BBBB________
        BBBBBB______
        _BBBBB______
        __BBBB______
    ''', '''
      <style>
        @page { size: 12px }
        svg { display: block }
      </style>
      <svg width="12px" height="12px" xmlns="http://www.w3.org/2000/svg">
        <path d="M 6 11 a 5 5 0 1 1 5 -5"
          stroke="blue" stroke-width="2" fill="none"/>
      </svg>
    ''')


@assert_no_logs
def test_path_Aa7():
    assert_pixels('path_Aa7', 12, 12, '''
        ____________
        ____________
        ____________
        ____________
        ____________
        ____________
        GGG______GGG
        GGG______GGG
        GGGG____GGGG
        GGGGGGGGGGGG
        _GGGGGGGGGG_
        __GGGGGGGG__
    ''', '''
      <style>
        @page { size: 12px }
        svg { display: block }
      </style>
      <svg width="12px" height="12px" xmlns="http://www.w3.org/2000/svg">
        <path d="M 1 6 A 5 5 0 0 0 11 6"
          stroke="lime" stroke-width="2" fill="none"/>
      </svg>
    ''')
