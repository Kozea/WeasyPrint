"""Test the currentColor value."""

import pytest

from ..testing_utils import assert_no_logs


@assert_no_logs
def test_current_color_1(assert_pixels):
    assert_pixels('GG\nGG', '''
      <style>
        @page { size: 2px }
        html, body { height: 100%; margin: 0 }
        html { color: red; background: currentColor }
        body { color: lime; background: inherit }
      </style>
      <body>''')


@assert_no_logs
def test_current_color_2(assert_pixels):
    assert_pixels('GG\nGG', '''
      <style>
        @page { size: 2px }
        html { color: red; border-color: currentColor }
        body { color: lime; border: 1px solid; border-color: inherit;
               margin: 0 }
      </style>
      <body>''')


@assert_no_logs
def test_current_color_3(assert_pixels):
    assert_pixels('GG\nGG', '''
      <style>
        @page { size: 2px }
        html { color: red; outline-color: currentColor }
        body { color: lime; outline: 1px solid; outline-color: inherit;
               margin: 1px }
      </style>
      <body>''')


@assert_no_logs
def test_current_color_4(assert_pixels):
    assert_pixels('GG\nGG', '''
      <style>
        @page { size: 2px }
        html { color: red; border-color: currentColor; }
        body { margin: 0 }
        table { border-collapse: collapse;
                color: lime; border: 1px solid; border-color: inherit }
      </style>
      <table><td>''')


@assert_no_logs
def test_current_color_svg_1(assert_pixels):
    assert_pixels('KK\nKK', '''
      <style>
        @page { size: 2px }
        svg { display: block }
      </style>
      <svg xmlns="http://www.w3.org/2000/svg"
           width="2" height="2" fill="currentColor">
        <rect width="2" height="2"></rect>
      </svg>''')


@pytest.mark.xfail
@assert_no_logs
def test_current_color_svg_2(assert_pixels):
    assert_pixels('GG\nGG', '''
      <style>
        @page { size: 2px }
        svg { display: block }
        body { color: lime }
      </style>
      <svg xmlns="http://www.w3.org/2000/svg"
           width="2" height="2">
        <rect width="2" height="2" fill="currentColor"></rect>
      </svg>''')


@assert_no_logs
def test_current_color_variable(assert_pixels):
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/2010
    assert_pixels('GG\nGG', '''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        @page { size: 2px }
        html { color: lime; font-family: weasyprint; --var: currentColor }
        div { color: var(--var); font-size: 2px; line-height: 1 }
      </style>
      <div>aa''')


@assert_no_logs
def test_current_color_variable_border(assert_pixels):
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/2010
    assert_pixels('GG\nGG', '''
      <style>
        @page { size: 2px }
        html { color: lime; --var: currentColor }
        div { color: var(--var); width: 0; height: 0; border: 1px solid }
      </style>
      <div>''')
