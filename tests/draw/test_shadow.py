"""Test lossless CSS shadow painting."""

from types import SimpleNamespace

import pytest

from weasyprint import HTML
from weasyprint.draw.shadow import _shadow_box

from ..testing_utils import assert_no_logs


@assert_no_logs
def test_box_shadow_outset(assert_pixels):
    """An outer shadow is offset and painted below the box background."""
    assert_pixels('''
        ____________
        ____________
        ____________
        ___RRRR_____
        ___RRRR_____
        ___RRRRBB___
        ___RRRRBB___
        _____BBBB___
        _____BBBB___
        ____________
        ____________
        ____________
    ''', '''
      <style>
        @page { size: 12px; margin: 0 }
        div {
          background: red;
          box-shadow: 2px 2px blue;
          height: 4px;
          left: 3px;
          position: absolute;
          top: 3px;
          width: 4px;
        }
      </style>
      <div></div>
    ''')


@assert_no_logs
def test_box_shadow_outset_transparent_knockout(assert_pixels):
    """Outer shadows stay clipped out of a transparent element's border box."""
    assert_pixels('''
        __________
        __________
        __________
        __________
        ______BB__
        ______BB__
        ____BBBB__
        ____BBBB__
        __________
        __________
    ''', '''
      <style>
        @page { size: 10px; margin: 0 }
        div {
          box-shadow: 2px 2px blue;
          height: 4px;
          left: 2px;
          position: absolute;
          top: 2px;
          width: 4px;
        }
      </style>
      <div></div>
    ''')


@assert_no_logs
def test_box_shadow_inset(assert_pixels):
    """A positive horizontal inset offset casts the shadow from the left edge."""
    assert_pixels('''
        ____________
        ____________
        __BBRRRRRR__
        __BBRRRRRR__
        __BBRRRRRR__
        __BBRRRRRR__
        __BBRRRRRR__
        __BBRRRRRR__
        __BBRRRRRR__
        __BBRRRRRR__
        ____________
        ____________
    ''', '''
      <style>
        @page { size: 12px; margin: 0 }
        div {
          background: red;
          box-shadow: inset 2px 0 blue;
          height: 8px;
          left: 2px;
          position: absolute;
          top: 2px;
          width: 8px;
        }
      </style>
      <div></div>
    ''')


@assert_no_logs
def test_box_shadow_multiple_order(assert_pixels):
    """The first declared shadow is painted over later shadows."""
    assert_pixels('''
        ____________
        ____________
        __RRRRgB____
        __RRRRgB____
        __RRRRgB____
        __RRRRgB____
        ____________
        ____________
    ''', '''
      <style>
        @page { size: 12px 8px; margin: 0 }
        div {
          background: red;
          box-shadow: 1px 0 green, 2px 0 blue;
          height: 4px;
          left: 2px;
          position: absolute;
          top: 2px;
          width: 4px;
        }
      </style>
      <div></div>
    ''')


@assert_no_logs
def test_box_shadow_spread_and_currentcolor(assert_pixels):
    """Spread changes the vector perimeter and omitted colors use currentcolor."""
    assert_pixels('''
        ____________
        _BBBBBBBB___
        _BRRRRRRB___
        _BRRRRRRB___
        _BRRRRRRB___
        _BRRRRRRB___
        _BBBBBBBB___
        ____________
    ''', '''
      <style>
        @page { size: 12px 8px; margin: 0 }
        div {
          background: red;
          box-shadow: 0 0 0 1px;
          color: blue;
          height: 4px;
          left: 2px;
          position: absolute;
          top: 2px;
          width: 6px;
        }
      </style>
      <div></div>
    ''')


@assert_no_logs
def test_box_shadow_rounded(assert_same_renderings):
    """A zero-spread shadow keeps the border box's rounded vector shape."""
    assert_same_renderings('''
      <style>
        @page { size: 20px; margin: 0 }
        div {
          background: red;
          border-radius: 4px;
          box-shadow: 3px 2px blue;
          height: 8px;
          left: 4px;
          position: absolute;
          top: 4px;
          width: 8px;
        }
      </style>
      <div></div>
    ''', '''
      <style>
        @page { size: 20px; margin: 0 }
        div {
          border-radius: 4px;
          height: 8px;
          position: absolute;
          width: 8px;
        }
        .shadow { background: blue; left: 7px; top: 6px }
        .box { background: red; left: 4px; top: 4px }
      </style>
      <div class="shadow"></div><div class="box"></div>
    ''')


@assert_no_logs
def test_box_shadow_inset_negative_spread_rounded():
    """Negative inset spread expands corners using the CSS outset algorithm."""
    corners = ((4, 4),) * 4
    box = SimpleNamespace(rounded_padding_box=lambda: (10, 10, 20, 20, *corners))
    shadow = _shadow_box(box, 10, 10, -8, inset=True)
    coverage = 2 * 4 / 20
    expected_radius = 4 + 8 * (1 - (1 - 4 / 8) ** 3 * (1 - coverage ** 3))
    assert shadow[:4] == (12, 12, 36, 36)
    assert tuple(value for corner in shadow[4:] for value in corner) == (
        pytest.approx((expected_radius,) * 8))


@assert_no_logs
def test_box_shadow_collapsed_table(assert_same_renderings):
    """Collapsed internal table boxes ignore only outer shadows, per CSS."""
    assert_same_renderings('''
      <style>
        table { border-collapse: collapse }
        td {
          background: red;
          box-shadow: 1em 0 blue, inset 0.5em 0 green;
          height: 4em;
          padding: 0;
          width: 4em;
        }
      </style>
      <table><tr><td></td></tr></table>
    ''', '''
      <style>
        table { border-collapse: collapse }
        td {
          background: red;
          box-shadow: inset 0.5em 0 green;
          height: 4em;
          padding: 0;
          width: 4em;
        }
      </style>
      <table><tr><td></td></tr></table>
    ''')


@assert_no_logs
def test_box_shadow_is_vector():
    """Zero-blur shadows add PDF paths without introducing raster images."""
    pdf = HTML(string='''
      <style>
        div {
          background: white;
          border-radius: 1em;
          box-shadow: 1em 1em 0 0.5em black, inset 0.5em 0.5em blue;
          height: 4em;
          width: 4em;
        }
      </style>
      <div></div>
    ''').write_pdf()
    assert b'/Subtype /Image' not in pdf
