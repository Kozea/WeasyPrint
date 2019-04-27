"""
    weasyprint.tests.test_draw.test_transform
    -----------------------------------------

    Test transformations.

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from ..testing_utils import assert_no_logs
from . import B, _, assert_pixels, r


@assert_no_logs
def test_2d_transform_1():
    assert_pixels('image_rotate90', 8, 8, [
        _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + B + B + B + r + _ + _,
        _ + _ + B + B + B + B + _ + _,
        _ + _ + B + B + B + B + _ + _,
        _ + _ + B + B + B + B + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _,
    ], '''
      <style>
        @page { size: 8px; margin: 2px; background: #fff; }
        div { transform: rotate(90deg); font-size: 0 }
      </style>
      <div><img src="pattern.png"></div>''')


@assert_no_logs
def test_2d_transform_2():
    assert_pixels('image_translateX_rotate90', 12, 12, [
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + B + B + B + r + _ + _ + _,
        _ + _ + _ + _ + _ + B + B + B + B + _ + _ + _,
        _ + _ + _ + _ + _ + B + B + B + B + _ + _ + _,
        _ + _ + _ + _ + _ + B + B + B + B + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
    ], '''
      <style>
        @page { size: 12px; margin: 2px; background: #fff; }
        div { transform: translateX(3px) rotate(90deg);
              font-size: 0; width: 4px }
      </style>
      <div><img src="pattern.png"></div>''')


@assert_no_logs
def test_2d_transform_3():
    # A translateX after the rotation is actually a translateY
    assert_pixels('image_rotate90_translateX', 12, 12, [
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + B + B + B + r + _ + _ + _ + _ + _ + _,
        _ + _ + B + B + B + B + _ + _ + _ + _ + _ + _,
        _ + _ + B + B + B + B + _ + _ + _ + _ + _ + _,
        _ + _ + B + B + B + B + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
    ], '''
      <style>
        @page { size: 12px; margin: 2px; background: #fff; }
        div { transform: rotate(90deg) translateX(3px);
              font-size: 0; width: 4px }
      </style>
      <div><img src="pattern.png"></div>''')


@assert_no_logs
def test_2d_transform_4():
    assert_pixels('nested_rotate90_translateX', 12, 12, [
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + B + B + B + r + _ + _ + _ + _ + _ + _,
        _ + _ + B + B + B + B + _ + _ + _ + _ + _ + _,
        _ + _ + B + B + B + B + _ + _ + _ + _ + _ + _,
        _ + _ + B + B + B + B + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
    ], '''
      <style>
        @page { size: 12px; margin: 2px; background: #fff; }
        div { transform: rotate(90deg); font-size: 0; width: 4px }
        img { transform: translateX(3px) }
      </style>
      <div><img src="pattern.png"></div>''')


@assert_no_logs
def test_2d_transform_5():
    assert_pixels('image_reflection', 8, 8, [
        _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + B + B + B + r + _ + _,
        _ + _ + B + B + B + B + _ + _,
        _ + _ + B + B + B + B + _ + _,
        _ + _ + B + B + B + B + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _,
    ], '''
      <style>
        @page { size: 8px; margin: 2px; background: #fff; }
        div { transform: matrix(-1, 0, 0, 1, 0, 0); font-size: 0 }
      </style>
      <div><img src="pattern.png"></div>''')


@assert_no_logs
def test_2d_transform_6():
    assert_pixels('image_translate', 8, 8, [
        _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + r + B + B + B + _,
        _ + _ + _ + B + B + B + B + _,
        _ + _ + _ + B + B + B + B + _,
        _ + _ + _ + B + B + B + B + _,
    ], '''
      <style>
        @page { size: 8px; margin: 2px; background: #fff; }
        div { transform: translate(1px, 2px); font-size: 0 }
      </style>
      <div><img src="pattern.png"></div>''')


@assert_no_logs
def test_2d_transform_7():
    assert_pixels('image_translate_percentage', 8, 8, [
        _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + r + B + B + B + _,
        _ + _ + _ + B + B + B + B + _,
        _ + _ + _ + B + B + B + B + _,
        _ + _ + _ + B + B + B + B + _,
        _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _,
    ], '''
      <style>
        @page { size: 8px; margin: 2px; background: #fff; }
        div { transform: translate(25%, 0); font-size: 0 }
      </style>
      <div><img src="pattern.png"></div>''')


@assert_no_logs
def test_2d_transform_8():
    assert_pixels('image_translateX', 8, 8, [
        _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + r + B + B,
        _ + _ + _ + _ + _ + B + B + B,
        _ + _ + _ + _ + _ + B + B + B,
        _ + _ + _ + _ + _ + B + B + B,
        _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _,
    ], '''
      <style>
        @page { size: 8px; margin: 2px; background: #fff; }
        div { transform: translateX(0.25em); font-size: 12px }
        div div { font-size: 0 }
      </style>
      <div><div><img src="pattern.png"></div></div>''')


@assert_no_logs
def test_2d_transform_9():
    assert_pixels('image_translateY', 8, 8, [
        _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + r + B + B + B + _ + _,
        _ + _ + B + B + B + B + _ + _,
        _ + _ + B + B + B + B + _ + _,
        _ + _ + B + B + B + B + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _,
    ], '''
      <style>
        @page { size: 8px; margin: 2px; background: #fff; }
        div { transform: translateY(-1px); font-size: 0 }
      </style>
      <div><img src="pattern.png"></div>''')


@assert_no_logs
def test_2d_transform_10():
    assert_pixels('image_scale', 10, 10, [
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + r + r + B + B + B + B + B + B + _,
        _ + r + r + B + B + B + B + B + B + _,
        _ + B + B + B + B + B + B + B + B + _,
        _ + B + B + B + B + B + B + B + B + _,
        _ + B + B + B + B + B + B + B + B + _,
        _ + B + B + B + B + B + B + B + B + _,
        _ + B + B + B + B + B + B + B + B + _,
        _ + B + B + B + B + B + B + B + B + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
    ], '''
      <style>
        @page { size: 10px; margin: 2px; background: #fff; }
        div { transform: scale(2, 2);
              transform-origin: 1px 1px;
              image-rendering: pixelated;
              font-size: 0 }
      </style>
      <div><img src="pattern.png"></div>''')


@assert_no_logs
def test_2d_transform_11():
    assert_pixels('image_scale12', 10, 10, [
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + r + B + B + B + _ + _ + _ + _,
        _ + _ + r + B + B + B + _ + _ + _ + _,
        _ + _ + B + B + B + B + _ + _ + _ + _,
        _ + _ + B + B + B + B + _ + _ + _ + _,
        _ + _ + B + B + B + B + _ + _ + _ + _,
        _ + _ + B + B + B + B + _ + _ + _ + _,
        _ + _ + B + B + B + B + _ + _ + _ + _,
        _ + _ + B + B + B + B + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
    ], '''
      <style>
        @page { size: 10px; margin: 2px; background: #fff; }
        div { transform: scale(1, 2);
              transform-origin: 1px 1px;
              image-rendering: pixelated;
              font-size: 0 }
      </style>
      <div><img src="pattern.png"></div>''')


@assert_no_logs
def test_2d_transform_12():
    assert_pixels('image_scaleY', 10, 10, [
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + r + B + B + B + _ + _ + _ + _,
        _ + _ + r + B + B + B + _ + _ + _ + _,
        _ + _ + B + B + B + B + _ + _ + _ + _,
        _ + _ + B + B + B + B + _ + _ + _ + _,
        _ + _ + B + B + B + B + _ + _ + _ + _,
        _ + _ + B + B + B + B + _ + _ + _ + _,
        _ + _ + B + B + B + B + _ + _ + _ + _,
        _ + _ + B + B + B + B + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
    ], '''
      <style>
        @page { size: 10px; margin: 2px; background: #fff; }
        div { transform: scaleY(2);
              transform-origin: 1px 1px;
              image-rendering: pixelated;
              font-size: 0 }
      </style>
      <div><img src="pattern.png"></div>''')


@assert_no_logs
def test_2d_transform_13():
    assert_pixels('image_scaleX', 10, 10, [
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + r + r + B + B + B + B + B + B + _,
        _ + B + B + B + B + B + B + B + B + _,
        _ + B + B + B + B + B + B + B + B + _,
        _ + B + B + B + B + B + B + B + B + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
    ], '''
      <style>
        @page { size: 10px; margin: 2px; background: #fff; }
        div { transform: scaleX(2);
              transform-origin: 1px 1px;
              image-rendering: pixelated;
              font-size: 0 }
      </style>
      <div><img src="pattern.png"></div>''')
