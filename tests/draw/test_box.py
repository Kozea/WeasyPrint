"""Test how boxes, borders, outlines are drawn."""

import itertools

import pytest
from weasyprint import HTML

from ..testing_utils import assert_no_logs


@assert_no_logs
def test_borders(assert_pixels, assert_different_renderings, margin='10px',
                 prop='border'):
    """Test the rendering of borders"""
    source = '''
      <style>
        @page { size: 140px 110px }
        body { width: 100px; height: 70px; margin: %s; %s: 10px %s blue }
      </style>
      <body>'''

    # Do not test the exact rendering of earch border style but at least
    # check that they do not do the same.
    documents = (
        source % (margin, prop, border_style)
        for border_style in (
            'none', 'solid', 'dashed', 'dotted', 'double',
            'inset', 'outset', 'groove', 'ridge'))
    assert_different_renderings(*documents)

    css_margin = margin
    width = 140
    height = 110
    margin = 10
    border = 10
    solid_pixels = [['_'] * width for _ in range(height)]
    for x in range(margin, width - margin):
        for y in itertools.chain(
                range(margin, margin + border),
                range(height - margin - border, height - margin)):
            solid_pixels[y][x] = 'B'
    for y in range(margin, height - margin):
        for x in itertools.chain(
                range(margin, margin + border),
                range(width - margin - border, width - margin)):
            solid_pixels[y][x] = 'B'
    pixels = '\n'.join(''.join(chars) for chars in solid_pixels)
    html = source % (css_margin, prop, 'solid')
    assert_pixels(pixels, html)


@assert_no_logs
def test_outlines(assert_pixels, assert_different_renderings):
    return test_borders(
        assert_pixels, assert_different_renderings,
        margin='20px', prop='outline')


@assert_no_logs
@pytest.mark.parametrize('border_style', ('none', 'solid', 'dashed', 'dotted'))
def test_small_borders_1(border_style):
    # Regression test for ZeroDivisionError on dashed or dotted borders
    # smaller than a dash/dot.
    # https://github.com/Kozea/WeasyPrint/issues/49
    html = '''
      <style>
        @page { size: 50px 50px }
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
def test_borders_box_sizing(assert_pixels):
    assert_pixels('''
        ________
        _RRRRRR_
        _R____R_
        _RRRRRR_
        ________
    ''', '''
      <style>
        @page {
          size: 8px 5px;
        }
        div {
          border: 1px solid red;
          box-sizing: border-box;
          height: 3px;
          margin: 1px;
          min-height: auto;
          min-width: auto;
          width: 6px;
        }
      </style>
      <div></div>
    ''')


@assert_no_logs
def test_margin_boxes(assert_pixels):
    assert_pixels('''
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


@assert_no_logs
def test_draw_border_radius(assert_pixels):
    assert_pixels('''
        ___zzzzz
        __zzzzzz
        _zzzzzzz
        zzzzzzzz
        zzzzzzzz
        zzzzzzzR
        zzzzzzRR
        zzzzzRRR
    ''', '''
      <style>
        @page {
          size: 8px 8px;
        }
        div {
          background: red;
          border-radius: 50% 0 0 0;
          height: 16px;
          width: 16px;
        }
      </style>
      <div></div>
    ''')


@assert_no_logs
def test_draw_split_border_radius(assert_pixels):
    assert_pixels('''
        ___zzzzz
        __zzzzzz
        _zzzzzzz
        zzzzzzzz
        zzzzzzzz
        zzzzzzzz
        zzzzzzRR
        zzzzzRRR

        RRRRRRRR
        RRRRRRRR
        RRRRRRRR
        RRRRRRRR
        RRRRRRRR
        RRRRRRRR
        RRRRRRRR
        RRRRRRRR

        zzzzzzRR
        zzzzzzzR
        zzzzzzzz
        zzzzzzzz
        zzzzzzzz
        zzzzzzzz
        _zzzzzzz
        __zzzzzz
    ''', '''
      <style>
        @page {
          size: 8px 8px;
        }
        div {
          background: red;
          color: transparent;
          border-radius: 8px;
          line-height: 9px;
          width: 16px;
        }
      </style>
      <div>a b c</div>
    ''')
