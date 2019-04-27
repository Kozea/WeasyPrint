"""
    weasyprint.tests.test_draw.test_box
    -----------------------------------

    Test how boxes, borders, outlines are drawn.

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import itertools

from ... import HTML
from ..testing_utils import assert_no_logs
from . import B, G, R, _, assert_different_renderings, assert_pixels, b, g


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
        ('%s_%s' % (prop, border_style), source % (margin, prop, border_style))
        for border_style in [
            'none', 'solid', 'dashed', 'dotted', 'double',
            'inset', 'outset', 'groove', 'ridge']])

    css_margin = margin
    width = 140
    height = 110
    margin = 10
    border = 10
    solid_pixels = [[_] * width for y in range(height)]
    for x in range(margin, width - margin):
        for y in itertools.chain(
                range(margin, margin + border),
                range(height - margin - border, height - margin)):
            solid_pixels[y][x] = B
    for y in range(margin, height - margin):
        for x in itertools.chain(
                range(margin, margin + border),
                range(width - margin - border, width - margin)):
            solid_pixels[y][x] = B
    solid_pixels = [b''.join(line) for line in solid_pixels]
    assert_pixels(
        prop + '_solid', 140, 110, solid_pixels,
        source % (css_margin, prop, 'solid'))


@assert_no_logs
def test_outlines():
    return test_borders(margin='20px', prop='outline')


@assert_no_logs
def test_small_borders_1():
    # Regression test for ZeroDivisionError on dashed or dotted borders
    # smaller than a dash/dot.
    # https://github.com/Kozea/WeasyPrint/issues/49
    html = '''
      <style>
        @page { size: 50px 50px }
        html { background: #fff }
        body { margin: 5px; height: 0; border: 10px %s blue }
      </style>
      <body>'''
    for style in ['none', 'solid', 'dashed', 'dotted']:
        HTML(string=html % style).write_image_surface()


@assert_no_logs
def test_small_borders_2():
    # Regression test for ZeroDivisionError on dashed or dotted borders
    # smaller than a dash/dot.
    # https://github.com/Kozea/WeasyPrint/issues/146
    html = '''
      <style>
        @page { size: 50px 50px }
        html { background: #fff }
        body { height: 0; width: 0; border-width: 1px 0; border-style: %s }
      </style>
      <body>'''
    for style in ['none', 'solid', 'dashed', 'dotted']:
        HTML(string=html % style).write_image_surface()


@assert_no_logs
def test_margin_boxes():
    assert_pixels('margin_boxes', 15, 15, [
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + G + G + G + _ + _ + _ + _ + _ + _ + B + B + B + B + _,
        _ + G + G + G + _ + _ + _ + _ + _ + _ + B + B + B + B + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + R + R + R + R + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + R + R + R + R + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + R + R + R + R + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + R + R + R + R + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + b + b + b + _ + _ + _ + _ + _ + _ + g + g + g + g + _,
        _ + b + b + b + _ + _ + _ + _ + _ + _ + g + g + g + g + _,
        _ + b + b + b + _ + _ + _ + _ + _ + _ + g + g + g + g + _,
        _ + b + b + b + _ + _ + _ + _ + _ + _ + g + g + g + g + _,
        _ + b + b + b + _ + _ + _ + _ + _ + _ + g + g + g + g + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
    ], '''
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
