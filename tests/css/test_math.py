"""Test CSS math functions."""

from math import isclose

import pytest

from weasyprint.css.validation.properties import PROPERTIES

from ..testing_utils import assert_no_logs, capture_logs, render_pages


@assert_no_logs
@pytest.mark.parametrize('width', [
    'calc(100px)',
    'calc(10em)',
    'calc(50vw)',
    'calc(20pvh)',
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
    'calc(tan(min(45deg, 60deg)) * 100px)',
    'calc(tan(max(45deg, 30deg)) * 100px)',
    'clamp(50px, 100px, 200px)',
    'clamp(100px, 250px, 50px)',
    'calc(clamp(1, 2, 3) * 50px)',
    'calc(clamp(1, 5, 2) * 50px)',
    'calc(clamp(2, 5, 1) * 50px)',
    'calc(tan(clamp(30deg, 45deg, 60deg)) * 100px)',
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
      <style>
        @page { size: 400px 500px; margin: 100px }
        body { font-size: 10px; width: 200px }
      </style>
      <div style="--one: 1; height: 1px; width: %s"></div>
    ''' % width)
    html, = page.children
    body, = html.children
    div, = body.children
    assert isclose(div.width, 100)


@assert_no_logs
@pytest.mark.parametrize(('width', 'reference'), [
    # A positive numerator over zero is +infinity, ...
    ('calc(100px / 0)', 'calc(infinity * 1px)'),
    ('calc(50px / 0)', 'calc(infinity * 1px)'),
    ('calc(10em / 0)', 'calc(infinity * 1px)'),
    # ... a negative numerator is -infinity, ...
    ('calc(-100px / 0)', 'calc(-infinity * 1px)'),
    # ... and zero over zero is NaN.
    ('calc(0px / 0)', 'calc(nan * 1px)'),
    # The divisor may evaluate to zero rather than being a literal zero.
    ('calc(100px / (1 - 1))', 'calc(infinity * 1px)'),
    # The resulting infinity keeps propagating through later operations.
    ('calc(100px / 0 + 100px)', 'calc(infinity * 1px)'),
    ('calc(-1px / 0 * 100)', 'calc(-infinity * 1px)'),
])
def test_calc_division_by_zero(width, reference):
    # A division by zero inside calc() resolves to +/-infinity or NaN
    # (IEEE-754), as required by CSS Values and Units 4, instead of raising a
    # ZeroDivisionError. The result must match the equivalent calc(infinity *
    # ...) / calc(nan * ...) expression that WeasyPrint already supports.
    def render(value):
        page, = render_pages(
            '<div style="font-size: 10px; height: 1px; width: %s"></div>'
            % value)
        html, = page.children
        body, = html.children
        div, = body.children
        return div.width
    assert render(width) == render(reference)


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
    'calc(calc(100unknown))',
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
    'calc(100* - max(56px, 1rem)',
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


@assert_no_logs
@pytest.mark.parametrize('line_height', [
    'calc(50% + 1em)',
    'calc(100% + 2px)',
    'calc(1.2em + 2px)',
    'calc(1.5 * 1)',
])
def test_math_functions_line_height(line_height):
    # Regression test for #2812.
    render_pages(f'<p style="line-height: {line_height}">Hello</p>')


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
def test_math_functions_hyphenate():
    render_pages('''
      <div lang="en"
        style="hyphens: auto; hyphenate-limit-zone: calc(1em + 100%); width: 2em">
        absolute
      </div>
    ''')


@assert_no_logs
def test_math_functions_gradient():
    render_pages('''
      <div style="width: 10px; height: 10px; background: linear-gradient(
        blue calc(20% + 1em),
        red calc(80% + 1em))"></div>
    ''')


@assert_no_logs
def test_math_functions_color():
    render_pages('''
      <div style="width: 10px; height: 10px;
                  background: rgba(10, 20, calc(30), calc(80%))"></div>
    ''')


@assert_no_logs
def test_math_functions_gradient_color():
    render_pages('''
      <div style="width: 10px; height: 10px; background: linear-gradient(
        rgba(10, 20, calc(30), calc(80%)) 10%,
        hsl(calc(10 + 10), 20%, 20%) 80%"></div>
    ''')


COLOR_PROPERTIES = (
    'color', 'background_color', 'border_top_color', 'border_right_color',
    'border_bottom_color', 'border_left_color', 'column_rule_color',
    'outline_color', 'text_decoration_color')


def _computed_colors(declaration):
    page, = render_pages(f'<div style="{declaration}">a</div>')
    html, = page.children
    body, = html.children
    div, = body.children
    return [str(div.style[name]) for name in COLOR_PROPERTIES]


@assert_no_logs
@pytest.mark.parametrize(('color', 'reference'), [
    # Numbers, percentages and angles, in each channel of each color function.
    ('rgb(calc(10 + 10), 20, 30)', 'rgb(20, 20, 30)'),
    ('rgb(calc(10% * 2), 20%, 30%)', 'rgb(20%, 20%, 30%)'),
    ('rgba(10, 20, 30, calc(0.25 * 2))', 'rgba(10, 20, 30, 0.5)'),
    ('rgba(10, 20, calc(30), calc(80%))', 'rgba(10, 20, 30, 80%)'),
    ('hsl(calc(10 + 10), 20%, 20%)', 'hsl(20, 20%, 20%)'),
    ('hsl(calc(10deg + 10deg), 20%, 20%)', 'hsl(20deg, 20%, 20%)'),
    ('hsl(20, calc(10% * 2), 20%)', 'hsl(20, 20%, 20%)'),
    ('hsla(20, 20%, 20%, calc(0.5))', 'hsla(20, 20%, 20%, 0.5)'),
    ('hwb(calc(10 + 10) 20% 30%)', 'hwb(20 20% 30%)'),
    ('lab(calc(50%) 40 50)', 'lab(50% 40 50)'),
    ('lch(calc(50%) 40 50)', 'lch(50% 40 50)'),
    ('oklab(calc(0.5) 0.1 0.1)', 'oklab(0.5 0.1 0.1)'),
    ('oklch(calc(0.5) 0.1 50)', 'oklch(0.5 0.1 50)'),
    ('color(srgb calc(0.1 + 0.1) 0.2 0.3)', 'color(srgb 0.2 0.2 0.3)'),
    ('device-cmyk(calc(0.1 + 0.1) 0.2 0.3 0.4)', 'device-cmyk(0.2 0.2 0.3 0.4)'),
    # Every math function, not just calc().
    ('rgb(min(20, 40), 20, 30)', 'rgb(20, 20, 30)'),
    ('rgb(max(10, 20), 20, 30)', 'rgb(20, 20, 30)'),
    ('rgb(clamp(10, 20, 30), 20, 30)', 'rgb(20, 20, 30)'),
    ('rgb(clamp(20, 5, 30), 20, 30)', 'rgb(20, 20, 30)'),
    ('rgb(clamp(1, 50, 20), 20, 30)', 'rgb(20, 20, 30)'),
    ('rgb(clamp(10%, 20%, 30%), 20%, 30%)', 'rgb(20%, 20%, 30%)'),
    ('hsl(min(20deg, 30deg), 20%, 20%)', 'hsl(20deg, 20%, 20%)'),
    ('hsl(max(10deg, 20deg), 20%, 20%)', 'hsl(20deg, 20%, 20%)'),
    ('hsl(clamp(10deg, 20deg, 30deg), 20%, 20%)', 'hsl(20deg, 20%, 20%)'),
    ('rgb(round(19.6), 20, 30)', 'rgb(20, 20, 30)'),
    ('rgb(mod(50, 30), 20, 30)', 'rgb(20, 20, 30)'),
    ('rgb(abs(-20), 20, 30)', 'rgb(20, 20, 30)'),
    ('rgb(sqrt(400), 20, 30)', 'rgb(20, 20, 30)'),
    ('rgb(pow(2, 2), 20, 30)', 'rgb(4, 20, 30)'),
    ('rgb(hypot(12, 16), 20, 30)', 'rgb(20, 20, 30)'),
    ('rgb(calc(20 * exp(0)), 20, 30)', 'rgb(20, 20, 30)'),
    ('rgb(calc(10 * log(100, 10)), 20, 30)', 'rgb(20, 20, 30)'),
    ('rgb(calc(20 * sign(3)), 20, 30)', 'rgb(20, 20, 30)'),
    ('rgb(calc(20 * sin(90deg)), 20, 30)', 'rgb(20, 20, 30)'),
    ('rgb(calc(calc(10) + 10), 20, 30)', 'rgb(20, 20, 30)'),
    ('rgb(calc(20 + pi * 0), 20, 30)', 'rgb(20, 20, 30)'),
    ('light-dark(rgb(calc(10 + 10), 20, 30), blue)',
     'light-dark(rgb(20, 20, 30), blue)'),
])
def test_math_functions_color_value(color, reference):
    # A math function in a color must give the same result as the value it
    # evaluates to, as required by CSS Values and Units 4.
    assert _computed_colors(f'color: {color}') == (
        _computed_colors(f'color: {reference}'))


@assert_no_logs
@pytest.mark.parametrize('css_property', [
    'color', 'background-color', 'border-top-color', 'border-right-color',
    'border-bottom-color', 'border-left-color', 'border-block-start-color',
    'border-block-end-color', 'border-inline-start-color',
    'border-inline-end-color', 'column-rule-color', 'outline-color',
    'text-decoration-color',
])
def test_math_functions_color_property(css_property):
    assert _computed_colors(f'{css_property}: rgb(calc(10 + 10), 20, 30)') == (
        _computed_colors(f'{css_property}: rgb(20, 20, 30)'))


@assert_no_logs
@pytest.mark.parametrize(('shorthand', 'suffix'), [
    ('background', ''),
    ('border', '1px solid '),
    ('border-top', '1px solid '),
    ('outline', '1px solid '),
    ('column-rule', '1px solid '),
    ('text-decoration', 'underline '),
])
def test_math_functions_color_shorthand(shorthand, suffix):
    assert _computed_colors(
        f'{shorthand}: {suffix}rgb(calc(10 + 10), 20, 30)') == (
            _computed_colors(f'{shorthand}: {suffix}rgb(20, 20, 30)'))


@pytest.mark.parametrize('color', [
    # Colors take no length, so these can never be resolved.
    'rgb(calc(1em), 0, 0)',
    'rgb(calc(10px), 0, 0)',
    'rgb(calc(10px + 1em), 0, 0)',
    'rgb(calc(100%), calc(1em), 0)',
    'hsl(calc(1em), 20%, 20%)',
    'rgb(min(1px, 2), 0, 0)',
    'rgb(clamp(1px, 2, 3), 0, 0)',
    # Resolving math must not make invalid syntax valid.
    'rgb(calc(10, 20), 20, 30)',
    'rgb(calc(10)% 20 30)',
    'lab(calc(20 + 30)% 40 50)',
    'notacolor(calc(20), 20, 30)',
    'light-dark(calc(1em), red)',
    'light-dark(calc(1em), red, red)',
])
def test_math_functions_color_error(color):
    with capture_logs() as logs:
        render_pages(f'<div style="color: {color}">a</div>')
    assert len(logs) == 1


@assert_no_logs
@pytest.mark.parametrize(('stops', 'reference'), [
    ('rgb(calc(10 + 10), 20, 30) 10%, blue 80%', 'rgb(20, 20, 30) 10%, blue 80%'),
    ('rgb(calc(10 + 10), 20, 30), blue', 'rgb(20, 20, 30), blue'),
    ('rgba(10, 20, calc(30), calc(80%)) 10%, hsl(calc(10 + 10), 20%, 20%) 80%',
     'rgba(10, 20, 30, 80%) 10%, hsl(20, 20%, 20%) 80%'),
])
def test_math_functions_gradient_color_stops(stops, reference):
    def gradient_colors(value):
        page, = render_pages(
            f'<div style="width: 10px; height: 10px;'
            f' background: linear-gradient({value})">a</div>')
        html, = page.children
        body, = html.children
        div, = body.children
        (_, gradient), = div.style['background_image']
        return [str(color) for color in gradient.colors]
    assert gradient_colors(stops) == gradient_colors(reference)


@assert_no_logs
def test_math_image_min_content_calc():
    render_pages('''
      <table>
        <td>
          <img src="pattern.png" style="
            height: calc(10% + 1em);
            width: calc(10% + 1em);
            max-height: calc(10% + 1em);
            max-width: calc(10% + 1em);
            min-height: calc(10% + 1em);
            min-width: calc(10% + 1em);
          ">
    ''')


@assert_no_logs
def test_math_image_min_content_auto_width_calc():
    render_pages('''
      <table>
        <td>
          <img src="pattern.png" style="
            height: calc(10% + 1em);
            max-height: calc(10% + 1em);
            max-width: calc(10% + 1em);
            min-height: calc(10% + 1em);
            min-width: calc(10% + 1em);
          ">
    ''')


@assert_no_logs
def test_math_image_min_content_auto_width_height_calc():
    render_pages('''
      <table>
        <td>
          <img src="pattern.png" style="
            max-height: calc(10% + 1em);
            max-width: calc(10% + 1em);
            min-height: calc(10% + 1em);
            min-width: calc(10% + 1em);
          ">
    ''')


@assert_no_logs
def test_math_table_margin():
    render_pages('<table style="margin: calc(1em + 10%)">')


@assert_no_logs
def test_math_grid_padding():
    render_pages('''
      <article style="display: grid">
        <div style="box-sizing: border-box; border: 1px solid;
                    padding: calc(2px + 10%); width: 7px">a</div>
      </article>
    ''')


@assert_no_logs
def test_math_table_column():
    render_pages('''
      <table style="width: 200px">
        <colgroup style="width: calc(1em + 10%)">
          <col />
        </colgroup>
        <col style="width: calc(1em + 10%)" />
        <tbody>
          <tr>
            <td>a</td>
            <td>a</td>
          </tr>
        </tbody>
      </table>
    ''')


@assert_no_logs
def test_math_border_spacing_em():
    render_pages('''
      <table style="
          --spacing: 1em; --border-spacing: calc(var(--spacing) * 5);
          border-spacing: var(--border-spacing) var(--border-spacing)">
        <tbody>
          <tr>
            <td>a</td>
            <td>a</td>
          </tr>
        </tbody>
      </table>
    ''')


@assert_no_logs
def test_math_vertical_align_table_percent():
    render_pages('''
      <table><tr><td style="vertical-align: calc(1em + 1%)">abc
    ''')


@assert_no_logs
def test_math_vertical_align_inline_percent():
    render_pages('''
      <span style="vertical-align: calc(1em + 1%)">abc
    ''')


@assert_no_logs
def test_math_vertical_align_page_percent():
    render_pages('''
      <style>@page{@top-left{content: "a"; vertical-align: calc(1em + 1%)}}</style>
      <body>abc
    ''')
