"""
    weasyprint.tests.test_draw.test_list
    ------------------------------------

    Test how lists are drawn.

"""

import pytest

from ..testing_utils import SANS_FONTS, assert_no_logs
from . import assert_pixels


@assert_no_logs
@pytest.mark.parametrize('position, pixels', (
    ('outside',
     #  ++++++++++++++      ++++  <li> horizontal margins: 7px 2px
     #                ######      <li> width: 12 - 7 - 2 = 3px
     #              --            list marker margin: 0.5em = 2px
     #      ********              list marker image is 4px wide
     '''
        ____________
        ____________
        ___rBBB_____
        ___BBBB_____
        ___BBBB_____
        ___BBBB_____
        ____________
        ____________
        ____________
        ____________
     '''),
    ('inside',
     #  ++++++++++++++      ++++  <li> horizontal margins: 7px 2px
     #                ######      <li> width: 12 - 7 - 2 = 3px
     #                ********    list marker image is 4px wide: overflow
     '''
        ____________
        ____________
        _______rBBB_
        _______BBBB_
        _______BBBB_
        _______BBBB_
        ____________
        ____________
        ____________
        ____________
     ''')
))
def test_list_style_image(position, pixels):
    assert_pixels('list_style_image_' + position, 12, 10, pixels, '''
      <style>
        @page { size: 12px 10px }
        body { margin: 0; background: white; font-family: %s }
        ul { margin: 2px 2px 0 7px; list-style: url(pattern.png) %s;
             font-size: 2px }
      </style>
      <ul><li></li></ul>''' % (SANS_FONTS, position))


@assert_no_logs
def test_list_style_image_none():
    assert_pixels('list_style_none', 10, 10, '''
        __________
        __________
        __________
        __________
        __________
        __________
        __________
        __________
        __________
        __________
    ''', '''
      <style>
        @page { size: 10px }
        body { margin: 0; background: white; font-family: %s }
        ul { margin: 0 0 0 5px; list-style: none; font-size: 2px; }
      </style>
      <ul><li>''' % (SANS_FONTS,))
