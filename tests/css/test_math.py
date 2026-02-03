"""Test CSS math functions."""

from math import isclose

import pytest

from weasyprint.css.validation.properties import PROPERTIES

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
    'calc(100px',
    'max(100px)',
    'max(30%, 2em, 100px)',
    'max(-30%, -2em, 10em)',
    'calc(max(-1, 1, 2) * 50px)',
    'min(100px)',
    'min(100%, 20em, 100px)',
    'calc(min(4, 2) * 50px)',
    'calc(sqrt(4) * 50px)',
    'calc(pow(2, 2) * 25px)',
    'calc(hypot(2) * 50px)',
    'calc(hypot(3, 4) * 20px)',
    'calc(hypot(2px) * 50)',
    'calc(hypot(3px, 4px) * 20)',
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
    'round(nearest, 100px)',
    'round(down, 195px, 100px)',
    'round(up, 5px, 100px)',
    'round(to-zero, 195px, 100px)',
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


@assert_no_logs
@pytest.mark.parametrize('width', [
    'calc',
    '(calc)',
    'calc(',
    'calc()',
    'calc("100px")',
    'calc(100)',
    'calc(100px 100px)',
    'calc(100px, 100px)',
    'calc(100px * 100px)',
    'calc(100 * 100)',
    'calc(0.1)',
    'calc(-1)',
    'min()',
    'min(10)',
    'min("10px")',
    'min(10, 5px)',
    'calc(min(1, 5px) * 10px)',
    'max()',
    'max(10)',
    'max("10px")',
    'max(10, 50px)',
    'calc(max(100, 5px) * 10px)',
    'clamp()',
    'clamp(10px)',
    'clamp(10px, 50px)',
    'clamp(10px, 50px, 100px, 200px)',
    'clamp(10px, "50px", 100px)',
    'round()',
    'round(100)',
    'round(100, 10)',
    'round(nearest, 100, 10)',
    'round(100px, 10)',
    'round(100px, "10px")',
    'round(nearest, 100px, 10)',
    'round(100px, 10px, 1)',
    'round(nearest, 100px, 10px, 1)',
    'round(unknown, 100px)',
    'round(unknown, 100px, 10px)',
    'mod()',
    'mod(10px)',
    'mod(100px, 10)',
    'mod(100px, "10px")',
    'calc(mod(300px, 200) * -1)',
    'mod(100px, 10px, 1px)',
    'rem()',
    'rem(10px)',
    'rem(100px, 10)',
    'rem(100px, "10px")',
    'calc(rem(300px, 200) * -1)',
    'rem(100px, 10px, 1px)',
    'sin()',
    'sin(10)',
    'sin(10%)',
    'sin(10deg)',
    'calc(sin(10) * 1)',
    'cos()',
    'cos(10)',
    'cos(10%)',
    'cos(10deg)',
    'calc(cos(10) * 1)',
    'tan()',
    'tan(10)',
    'tan(10%)',
    'tan(10deg)',
    'calc(tan(10) * 1)',
    'asin()',
    'asin(0)',
    'asin(0.5)',
    'asin(50deg)',
    'calc(sin(asin(50deg)) * 200px)',
    'calc(sin(asin(0.5)) * 200)',
    'calc(sin(asin(0.5, 2)) * 200px)',
    'calc(sin(asin(5)) * 200px)',
    'acos()',
    'acos(0)',
    'acos(0.5)',
    'acos(50deg)',
    'calc(cos(acos(50deg)) * 200px)',
    'calc(cos(acos(0.5)) * 200)',
    'calc(cos(acos(0.5, 2)) * 200px)',
    'calc(cos(acos(5)) * 200px)',
    'atan()',
    'atan(0)',
    'atan(0.5)',
    'atan(50deg)',
    'calc(tan(atan(50deg)) * 200px)',
    'calc(tan(atan(0.5)) * 200)',
    'calc(tan(atan(0.5, 2)) * 200px)',
    'atan2()',
    'atan2(0.5)',
    'atan2(0.5, 1)',
    'atan2(50deg, 1)',
    'calc(tan(atan2(50deg, 1)) * 200px)',
    'calc(tan(atan2(0.5, 1)) * 200)',
    'pow()',
    'pow(4, 3)',
    'pow(4px, 3)',
    'pow(4, 3, 4)',
    'sqrt()',
    'sqrt(4)',
    'sqrt(4px)',
    'sqrt(4, 2)',
    'hypoth()',
    'hypoth(3)',
    'hypoth(3, 4)',
    'log()',
    'log(10)',
    'log(10px)',
    'log(10, 10)',
    'log(10px, 10)',
    'log(10, 10, 10)',
    'exp()',
    'exp(10)',
    'exp(10px)',
    'exp(10, 10)',
    'exp(10px, 10)',
    'exp(10, 10, 10)',
    'abs()',
    'abs(10)',
    'abs(10px, 100)',
    'sign()',
    'sign(10)',
    'sign(10px)',
    'sign(10px, 10)',
])
def test_math_functions_error(width):
    with capture_logs() as logs:
        page, = render_pages('''
          <style>body { font-size: 10px; width: 200px }</style>
          <div style="--one: 1; height: 1px; width: %s"></div>
        ''' % width)
    assert len(logs) == 1


@pytest.mark.parametrize('css_property', PROPERTIES)
def test_math_functions_percentage_and_font_unit(css_property):
    with capture_logs() as math_logs:
        render_pages(f'''
          <div style="{css_property}: calc(50% + 1em)"></div>
        ''')
    with capture_logs() as logs:
        render_pages(f'''
          <div style="{css_property}: 50%"></div>
        ''')
        if not logs:
            # Happens when property accepts percentages but not lengths.
            render_pages(f'''
              <div style="{css_property}: 1em"></div>
            ''')
    assert len(math_logs) == len(logs)


@pytest.mark.parametrize('display', [
    'block', 'inline', 'flex', 'grid',
    'list', 'list-item',
    'table', 'table-row-group', 'table-cell',
    'inline-block', 'inline-table', 'inline-flex', 'inline-grid',
])
def test_math_functions_display_size(display):
    # Regression test for #2673.
    render_pages(f'''
    <div style="display: {display};
     min-width: calc(50% + 1em); max-width: calc(50% + 1em); width: calc(50% + 1em);
     min-height: calc(50% + 1em); max-height: calc(50% + 1em); height: calc(50% + 1em)
    ">
      <div style="
       min-width: calc(50% + 1em); max-width: calc(50% + 1em); width: calc(50% + 1em);
       min-height: calc(50% + 1em); max-height: calc(50% + 1em); height: calc(50% + 1em)
      "></div>
    </div>
    ''')


@assert_no_logs
def test_math_functions_gradient():
    render_pages('''
      <div style="width: 10px; height: 10px; background: linear-gradient(
        blue calc(20% + 1em),
        red calc(80% + 1em))"></div>
    ''')


@pytest.mark.xfail
@assert_no_logs
def test_math_functions_color():
    render_pages('''
      <div style="width: 10px; height: 10px;
                  background: rgba(10, 20, calc(30), calc(80%))"></div>
    ''')


@pytest.mark.xfail
@assert_no_logs
def test_math_functions_gradient_color():
    render_pages('''
      <div style="width: 10px; height: 10px; background: linear-gradient(
        rgba(10, 20, calc(30), calc(80%)) 10%,
        hsl(calc(10 + 10), 20%, 20%) 80%"></div>
    ''')
