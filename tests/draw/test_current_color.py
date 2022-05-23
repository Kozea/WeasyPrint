"""Test the currentColor value."""

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
