"""
    weasyprint.tests.test_draw.test_gradient
    ----------------------------------------

    Test how gradients are drawn.

    :copyright: Copyright 2011-2018 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from . import B, V, _, assert_pixels, html_to_pixels, r, v
from ..testing_utils import assert_no_logs, requires


@assert_no_logs
@requires('cairo', (1, 14, 0))
def test_linear_gradients_1():
    assert_pixels('linear_gradient', 5, 9, [
        _ + _ + _ + _ + _,
        _ + _ + _ + _ + _,
        _ + _ + _ + _ + _,
        B + B + B + B + B,
        B + B + B + B + B,
        r + r + r + r + r,
        r + r + r + r + r,
        r + r + r + r + r,
        r + r + r + r + r,
    ], '''<style>@page { size: 5px 9px; background: linear-gradient(
      white, white 3px, blue 0, blue 5px, red 0, red
    )''')


@assert_no_logs
@requires('cairo', (1, 14, 0))
def test_linear_gradients_2():
    assert_pixels('linear_gradient', 5, 9, [
        _ + _ + _ + _ + _,
        _ + _ + _ + _ + _,
        _ + _ + _ + _ + _,
        B + B + B + B + B,
        B + B + B + B + B,
        r + r + r + r + r,
        r + r + r + r + r,
        r + r + r + r + r,
        r + r + r + r + r,
    ], '''<style>@page { size: 5px 9px; background: linear-gradient(
      white 3px, blue 0, blue 5px, red 0
    )''')


@assert_no_logs
@requires('cairo', (1, 14, 0))
def test_linear_gradients_3():
    assert_pixels('linear_gradient', 9, 5, [
        _ + _ + _ + B + B + r + r + r + r,
        _ + _ + _ + B + B + r + r + r + r,
        _ + _ + _ + B + B + r + r + r + r,
        _ + _ + _ + B + B + r + r + r + r,
        _ + _ + _ + B + B + r + r + r + r,
    ], '''<style>@page { size: 9px 5px; background: linear-gradient(
      to right, white 3px, blue 0, blue 5px, red 0
    )''')


@assert_no_logs
@requires('cairo', (1, 14, 0))
def test_linear_gradients_4():
    assert_pixels('linear_gradient', 10, 5, [
        B + B + B + B + B + B + r + r + r + r,
        B + B + B + B + B + B + r + r + r + r,
        B + B + B + B + B + B + r + r + r + r,
        B + B + B + B + B + B + r + r + r + r,
        B + B + B + B + B + B + r + r + r + r,
    ], '''<style>@page { size: 10px 5px; background: linear-gradient(
      to right, blue 5px, blue 6px, red 6px, red 9px
    )''')


@assert_no_logs
@requires('cairo', (1, 14, 0))
def test_linear_gradients_5():
    assert_pixels('linear_gradient', 10, 5, [
        r + B + r + r + r + B + r + r + r + B,
        r + B + r + r + r + B + r + r + r + B,
        r + B + r + r + r + B + r + r + r + B,
        r + B + r + r + r + B + r + r + r + B,
        r + B + r + r + r + B + r + r + r + B,
    ], '''<style>@page { size: 10px 5px; background: repeating-linear-gradient(
      to right, blue 50%, blue 60%, red 60%, red 90%
    )''')


@assert_no_logs
@requires('cairo', (1, 14, 0))
def test_linear_gradients_6():
    assert_pixels('linear_gradient', 9, 5, [
        B + B + B + r + r + r + r + r + r,
        B + B + B + r + r + r + r + r + r,
        B + B + B + r + r + r + r + r + r,
        B + B + B + r + r + r + r + r + r,
        B + B + B + r + r + r + r + r + r,
    ], '''<style>@page { size: 9px 5px; background: linear-gradient(
      to right, blue 3px, blue 3px, red 3px, red 3px
    )''')


@assert_no_logs
@requires('cairo', (1, 14, 0))
def test_linear_gradients_7():
    assert_pixels('linear_gradient', 9, 5, [
        v + v + v + v + v + v + v + v + v,
        v + v + v + v + v + v + v + v + v,
        v + v + v + v + v + v + v + v + v,
        v + v + v + v + v + v + v + v + v,
        v + v + v + v + v + v + v + v + v,
    ], '''<style>@page { size: 9px 5px; background: repeating-linear-gradient(
      to right, blue 3px, blue 3px, red 3px, red 3px
    )''')


@assert_no_logs
@requires('cairo', (1, 14, 0))
def test_linear_gradients_8():
    assert_pixels('linear_gradient', 9, 5, [
        V + V + V + V + V + V + V + V + V,
        V + V + V + V + V + V + V + V + V,
        V + V + V + V + V + V + V + V + V,
        V + V + V + V + V + V + V + V + V,
        V + V + V + V + V + V + V + V + V,
    ], '''
      <style>
        @page { size: 9px 5px; background: repeating-linear-gradient(
                  to right, blue 50%, blue 60%, red 60%, red 90%);
        background-size: 1px 1px''')


@assert_no_logs
def test_radial_gradients_1():
    assert_pixels('radial_gradient', 6, 6, [
        B + B + B + B + B + B,
        B + B + B + B + B + B,
        B + B + B + B + B + B,
        B + B + B + B + B + B,
        B + B + B + B + B + B,
        B + B + B + B + B + B,
    ], '''<style>@page { size: 6px; background:
      radial-gradient(red -30%, blue -10%)''')


@assert_no_logs
def test_radial_gradients_2():
    assert_pixels('radial_gradient', 6, 6, [
        r + r + r + r + r + r,
        r + r + r + r + r + r,
        r + r + r + r + r + r,
        r + r + r + r + r + r,
        r + r + r + r + r + r,
        r + r + r + r + r + r,
    ], '''<style>@page { size: 6px; background:
      radial-gradient(red 110%, blue 130%)''')


@assert_no_logs
def test_radial_gradients_3():
    for thin, gradient in ((False, 'red 20%, blue 80%'),
                           (True, 'red 50%, blue 50%')):
        _, pixels = html_to_pixels(
            'radial_gradient_' + gradient, 10, 16,
            '<style>@page { size: 10px 16px; background: radial-gradient(%s)'
            % gradient)

        def pixel(x, y):
            i = (x + 10 * y) * 4
            return pixels[i:i + 4]
        assert pixel(0, 0) == B
        assert pixel(9, 0) == B
        assert pixel(0, 15) == B
        assert pixel(9, 15) == B
        assert pixel(4, 7) == r
        assert pixel(4, 8) == r
        assert pixel(5, 7) == r
        assert pixel(5, 8) == r
        assert (pixel(3, 5) not in (B, r)) ^ thin
        assert (pixel(3, 9) not in (B, r)) ^ thin
        assert (pixel(7, 5) not in (B, r)) ^ thin
        assert (pixel(7, 9) not in (B, r)) ^ thin
