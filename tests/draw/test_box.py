"""
    weasyprint.tests.test_draw.test_box
    -----------------------------------

    Test how boxes, borders, outlines are drawn.

"""

import itertools

import pytest
from weasyprint import HTML

from ..testing_utils import assert_no_logs
from . import PIXELS_BY_CHAR, assert_different_renderings, assert_pixels


@assert_no_logs
def test_borders(margin='10px', prop='border'):
    """Test the rendering of borders"""
    source = '''
      <style>
        @page { size: 140px 110px }
        html { background: #fff }
        body { width: 100px; height: 70px;
               margin: %s; %s: 10px %s blue }
      </style>
      <body>'''

    # Do not test the exact rendering of earch border style but at least
    # check that they do not do the same.
    assert_different_renderings(140, 110, [
        (f'{prop}_{border_style}', source % (margin, prop, border_style))
        for border_style in [
            'none', 'solid', 'dashed', 'dotted', 'double',
            'inset', 'outset', 'groove', 'ridge']])

    css_margin = margin
    width = 140
    height = 110
    margin = 10
    border = 10
    solid_pixels = [PIXELS_BY_CHAR['_'] for i in range(width * height)]
    for x in range(margin, width - margin):
        for y in itertools.chain(
                range(margin, margin + border),
                range(height - margin - border, height - margin)):
            solid_pixels[y * width + x] = PIXELS_BY_CHAR['B']
    for y in range(margin, height - margin):
        for x in itertools.chain(
                range(margin, margin + border),
                range(width - margin - border, width - margin)):
            solid_pixels[y * width + x] = PIXELS_BY_CHAR['B']
    assert_pixels(
        f'{prop}_solid', 140, 110, solid_pixels,
        source % (css_margin, prop, 'solid'))


@assert_no_logs
def test_outlines():
    return test_borders(margin='20px', prop='outline')


@assert_no_logs
@pytest.mark.parametrize('border_style', ('none', 'solid', 'dashed', 'dotted'))
def test_small_borders_1(border_style):
    # Regression test for ZeroDivisionError on dashed or dotted borders
    # smaller than a dash/dot.
    # https://github.com/Kozea/WeasyPrint/issues/49
    html = '''
      <style>
        @page { size: 50px 50px }
        html { background: #fff }
        body { margin: 5px; height: 0; border: 10px %s blue }
      </style>
      <body>''' % border_style
    HTML(string=html).write_pdf()


@assert_no_logs
@pytest.mark.parametrize('border_style', ('none', 'solid', 'dashed', 'dotted'))
def test_small_borders_2(border_style):
    # Regression test for ZeroDivisionError on dashed or dotted borders
    # smaller than a dash/dot.
    # https://github.com/Kozea/WeasyPrint/issues/146
    html = '''
      <style>
        @page { size: 50px 50px }
        html { background: #fff }
        body { height: 0; width: 0; border-width: 1px 0; border-style: %s }
      </style>
      <body>''' % border_style
    HTML(string=html).write_pdf()


@assert_no_logs
def test_em_borders():
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/1378
    html = '<body style="border: 1em solid">'
    HTML(string=html).write_pdf()


@assert_no_logs
def test_margin_boxes():
    assert_pixels('margin_boxes', 15, 15, '''
        _______________
        _GGG______BBBB_
        _GGG______BBBB_
        _______________
        _____RRRR______
        _____RRRR______
        _____RRRR______
        _____RRRR______
        _______________
        _bbb______gggg_
        _bbb______gggg_
        _bbb______gggg_
        _bbb______gggg_
        _bbb______gggg_
        _______________
    ''', '''
      <style>
        html { height: 100% }
        body { background: #f00; height: 100% }
        @page {
          size: 15px;
          margin: 4px 6px 7px 5px;
          background: white;

          @top-left-corner {
            margin: 1px;
            content: " ";
            background: #0f0;
          }
          @top-right-corner {
            margin: 1px;
            content: " ";
            background: #00f;
          }
          @bottom-right-corner {
            margin: 1px;
            content: " ";
            background: #008000;
          }
          @bottom-left-corner {
            margin: 1px;
            content: " ";
            background: #000080;
          }
        }
      </style>
      <body>''')


@assert_no_logs
def test_display_inline_block_twice():
    # Regression test for inline blocks displayed twice.
    # https://github.com/Kozea/WeasyPrint/issues/880
    html = '<div style="background: red; display: inline-block">'
    document = HTML(string=html).render()
    assert document.write_pdf() == document.write_pdf()
