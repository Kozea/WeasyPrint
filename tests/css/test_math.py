"""Test CSS math functions."""

from math import isclose

import pytest

from ..testing_utils import assert_no_logs, capture_logs, render_pages


@assert_no_logs
@pytest.mark.parametrize('width', [
    'calc(100px)',
    'calc(10em)',
    'calc(50%)',
    'calc(10px + 90px)',
    'calc(5em + 50px)',
    'calc(2 * 5em)',
    'calc(2 * (3em + 20px))',
    'calc(25% * (1 + 1))',
    'calc(20% * (1 + 1) + 20px)',
    'max(100px)',
    'max(30%, 2em, 100px)',
    'max(-30%, -2em, 10em)',
    'min(100px)',
    'min(100%, 20em, 100px)',
    'calc(sqrt(4) * 50px)',
    'calc(pow(2, 2) * 25px)',
    'calc(hypot(2) * 50px)',
    'calc(hypot(3, 4) * 20px)',
    'calc(log(e) * 100px)',
    'calc(log(100, 10) * 50px)',
    'calc(exp(1) / e * 100px)',
    'abs(-100px)',
    'calc(abs(-100) * 1px)',
    'calc(sign(-100) * -100px)',
    'calc(sign(-100px) * -100px)',
    'calc(sqrt(16) * min(25px, 100%))',
    'clamp(calc(-infinity * 1px), 10em, calc(infinity * 1px))',
    'clamp(50px, 10em, 500px)',
    'clamp(100px, 2em, 500px)',
    'clamp(10px, 100em, 10em)',
    'clamp(10px, 100%, 10em)',
    'round(100.4px)',
    'round(145.4px, 100px)',
    'mod(300px, 200px)',
    'calc(mod(300px, -200px) * -1)',
    'calc(mod(-300px, -200px) * -1)',
    'rem(300px, 200px)',
    'rem(300px, -200px)',
    'calc(rem(-300px, -200px) * -1)',
    'calc(sin(30deg) * 200px)',
    'calc(cos(60deg) * 200px)',
    'calc(tan(45deg) * 100px)',
    'calc(tan(calc(pi / 4)) * 100px)',
    'calc(sin(asin(0.5)) * 200px)',
    'calc(cos(acos(0.5)) * 200px)',
    'calc(tan(atan(1)) * 100px)',
    'calc(tan(atan2(1, 1)) * 100px)',
    'calc(100px * var(--one))',
    'calc(50% * var(--one))',
    'calc(100px * sqrt(var(--one)))',
])
def test_math_functions(width):
    page, = render_pages('''
      <style>body { font-size: 10px; width: 200px }</style>
      <div style="--one: 1; height: 1px; width: %s"></div>
    ''' % width)
    html, = page.children
    body, = html.children
    div, = body.children
    assert isclose(div.width, 100)
