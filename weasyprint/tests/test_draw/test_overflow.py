"""
    weasyprint.tests.test_draw.test_overflow
    ----------------------------------------

    Test overflow and clipping.

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import pytest

from ..testing_utils import assert_no_logs, requires
from . import assert_pixels


@assert_no_logs
def test_overflow_1():
    # See test_images
    assert_pixels('inline_image_overflow', 8, 8, '''
        ________
        ________
        __rBBB__
        __BBBB__
        ________
        ________
        ________
        ________
    ''', '''
      <style>
        @page { size: 8px }
        body { margin: 2px 0 0 2px; background: #fff; font-size:0 }
        div { height: 2px; overflow: hidden }
      </style>
      <div><img src="pattern.png"></div>''')


@assert_no_logs
def test_overflow_2():
    # <body> is only 1px high, but its overflow is propageted to the viewport
    # ie. the padding edge of the page box.
    assert_pixels('inline_image_viewport_overflow', 8, 8, '''
        ________
        ________
        __rBBB__
        __BBBB__
        __BBBB__
        ________
        ________
        ________
    ''', '''
      <style>
        @page { size: 8px; background: #fff;
                margin: 2px;
                padding-bottom: 2px;
                border-bottom: 1px transparent solid; }
        body { height: 1px; overflow: hidden; font-size: 0 }
      </style>
      <div><img src="pattern.png"></div>''')


@assert_no_logs
def test_overflow_3():
    # Assert that the border is not clipped by overflow: hidden
    assert_pixels('border_box_overflow', 8, 8, '''
        ________
        ________
        __BBBB__
        __B__B__
        __B__B__
        __BBBB__
        ________
        ________
    ''', '''
      <style>
        @page { size: 8px; background: #fff; margin: 2px; }
        div { width: 2px; height: 2px; overflow: hidden;
              border: 1px solid blue; }
      </style>
      <div></div>''')


@assert_no_logs
@requires('cairo', (1, 12, 0))
@pytest.mark.parametrize('number, css, pixels', (
    (1, '5px, 5px, 9px, auto', '''
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______rBBBrBg_
        ______BBBBBBg_
        ______BBBBBBg_
        ______BBBBBBg_
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
    '''),
    (2, '5px, 5px, auto, 10px', '''
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        ______rBBBr___
        ______BBBBB___
        ______BBBBB___
        ______BBBBB___
        ______rBBBr___
        ______BBBBB___
        ______ggggg___
        ______________
        ______________
        ______________
    '''),
    (3, '5px, auto, 9px, 10px', '''
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
        _grBBBrBBBr___
        _gBBBBBBBBB___
        _gBBBBBBBBB___
        _gBBBBBBBBB___
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
    '''),
    (4, 'auto, 5px, 9px, 10px', '''
        ______________
        ______ggggg___
        ______rBBBr___
        ______BBBBB___
        ______BBBBB___
        ______BBBBB___
        ______rBBBr___
        ______BBBBB___
        ______BBBBB___
        ______BBBBB___
        ______________
        ______________
        ______________
        ______________
        ______________
        ______________
    '''),
))
def test_clip(number, css, pixels):
    assert_pixels('background_repeat_clipped_%s' % number, 14, 16, pixels, '''
      <style>
        @page { size: 14px 16px; background: #fff }
        div { margin: 1px; border: 1px green solid;
              background: url(pattern.png);
              position: absolute; /* clip only applies on abspos */
              top: 0; bottom: 2px; left: 0; right: 0;
              clip: rect(%s); }
      </style>
      <div>''' % css)
