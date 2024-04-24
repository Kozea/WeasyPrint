"""Test how images are drawn in SVG."""

import pytest

from weasyprint.urls import path2url

from ...testing_utils import assert_no_logs, resource_path


@assert_no_logs
def test_image_svg(assert_pixels):
    assert_pixels('''
        ____
        ____
        __B_
        ____
    ''', '''
      <style>
        @page { size: 4px 4px }
        svg { display: block }
      </style>
      <svg width="4px" height="4px" xmlns="http://www.w3.org/2000/svg">
        <svg x="1" y="1" width="2" height="2" viewBox="0 0 10 10">
          <rect x="5" y="5" width="5" height="5" fill="blue" />
        </svg>
      </svg>
    ''')


@assert_no_logs
def test_image_svg_viewbox(assert_pixels):
    assert_pixels('''
        ____
        ____
        __B_
        ____
    ''', '''
      <style>
        @page { size: 4px 4px }
        svg { display: block }
      </style>
      <svg viewBox="0 0 4 4" xmlns="http://www.w3.org/2000/svg">
        <svg x="1" y="1" width="2" height="2" viewBox="10 10 10 10">
          <rect x="15" y="15" width="5" height="5" fill="blue" />
        </svg>
      </svg>
    ''')


@assert_no_logs
def test_image_svg_align_default(assert_pixels):
    assert_pixels('''
        __BRRR__
        __BRRR__
        __RRRG__
        __RRRG__
        ________
        ________
        ________
        ________
    ''', '''
      <style>
        @page { size: 8px 8px }
        svg { display: block }
      </style>
      <svg width="8px" height="4px" viewBox="0 0 4 4"
           xmlns="http://www.w3.org/2000/svg">
        <rect width="4" height="4" fill="red" />
        <rect width="1" height="2" fill="blue" />
        <rect x="3" y="2" width="1" height="2" fill="lime" />
      </svg>
    ''')


@assert_no_logs
def test_image_svg_align_none(assert_pixels):
    assert_pixels('''
        BBRRRRRR
        BBRRRRRR
        RRRRRRGG
        RRRRRRGG
        ________
        ________
        ________
        ________
    ''', '''
      <style>
        @page { size: 8px 8px }
        svg { display: block }
      </style>
      <svg width="8px" height="4px" viewBox="0 0 4 4"
           preserveAspectRatio="none"
           xmlns="http://www.w3.org/2000/svg">
        <rect width="4" height="4" fill="red" />
        <rect width="1" height="2" fill="blue" />
        <rect x="3" y="2" width="1" height="2" fill="lime" />
      </svg>
    ''')


@assert_no_logs
def test_image_svg_align_meet_x(assert_pixels):
    assert_pixels('''
        ____BRRR
        ____BRRR
        ____RRRG
        ____RRRG
        ________
        ________
        ________
        ________
    ''', '''
      <style>
        @page { size: 8px 8px }
        svg { display: block }
      </style>
      <svg width="8px" height="4px" viewBox="0 0 4 4"
           preserveAspectRatio="xMaxYMax meet"
           xmlns="http://www.w3.org/2000/svg">
        <rect width="4" height="4" fill="red" />
        <rect width="1" height="2" fill="blue" />
        <rect x="3" y="2" width="1" height="2" fill="lime" />
      </svg>
    ''')


@assert_no_logs
def test_image_svg_align_meet_y(assert_pixels):
    assert_pixels('''
        ________
        ________
        ________
        ________
        BRRR____
        BRRR____
        RRRG____
        RRRG____
    ''', '''
      <style>
        @page { size: 8px 8px }
        svg { display: block }
      </style>
      <svg width="4px" height="8px" viewBox="0 0 4 4"
           preserveAspectRatio="xMaxYMax meet"
           xmlns="http://www.w3.org/2000/svg">
        <rect width="4" height="4" fill="red" />
        <rect width="1" height="2" fill="blue" />
        <rect x="3" y="2" width="1" height="2" fill="lime" />
      </svg>
    ''')


@assert_no_logs
def test_image_svg_align_slice_x(assert_pixels):
    assert_pixels('''
        BBRRRRRR
        BBRRRRRR
        BBRRRRRR
        BBRRRRRR
        ________
        ________
        ________
        ________
    ''', '''
      <style>
        @page { size: 8px 8px }
        svg { display: block; overflow: hidden }
      </style>
      <svg width="8px" height="4px" viewBox="0 0 4 4"
           preserveAspectRatio="xMinYMin slice"
           xmlns="http://www.w3.org/2000/svg">
        <rect width="4" height="4" fill="red" />
        <rect width="1" height="2" fill="blue" />
        <rect x="3" y="2" width="1" height="2" fill="lime" />
      </svg>
    ''')


@assert_no_logs
def test_image_svg_align_slice_y(assert_pixels):
    assert_pixels('''
        BBRR____
        BBRR____
        BBRR____
        BBRR____
        RRRR____
        RRRR____
        RRRR____
        RRRR____
    ''', '''
      <style>
        @page { size: 8px 8px }
        svg { display: block; overflow: hidden }
      </style>
      <svg width="4px" height="8px" viewBox="0 0 4 4"
           preserveAspectRatio="xMinYMin slice"
           xmlns="http://www.w3.org/2000/svg">
        <rect width="4" height="4" fill="red" />
        <rect width="1" height="2" fill="blue" />
        <rect x="3" y="2" width="1" height="2" fill="lime" />
      </svg>
    ''')


@pytest.mark.xfail
@assert_no_logs
def test_image_svg_percentage(assert_pixels):
    assert_pixels('''
        ____
        ____
        __B_
        ____
    ''', '''
      <style>
        @page { size: 4px 4px }
        svg { display: block }
      </style>
      <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
        <svg x="1" y="1" width="50%" height="50%" viewBox="0 0 10 10">
          <rect x="5" y="5" width="5" height="5" fill="blue" />
        </svg>
      </svg>
    ''')


def test_image_svg_wrong(assert_pixels):
    assert_pixels('''
        ____
        ____
        ____
        ____
    ''', '''
      <style>
        @page { size: 4px 4px }
        svg { display: block }
      </style>
      <svg width="4px" height="4px" xmlns="http://www.w3.org/2000/svg">
        <That’s bad!
      </svg>
    ''')


@assert_no_logs
def test_image_image(assert_pixels):
    assert_pixels('''
        rBBB
        BBBB
        BBBB
        BBBB
    ''', '''
      <style>
        @page { size: 4px 4px }
        svg { display: block }
      </style>
      <svg width="4px" height="4px" xmlns="http://www.w3.org/2000/svg">
        <image xlink:href="%s" />
      </svg>
    ''' % path2url(resource_path('pattern.png')))


def test_image_image_wrong(assert_pixels):
    assert_pixels('''
        ____
        ____
        ____
        ____
    ''', '''
      <style>
        @page { size: 4px 4px }
        svg { display: block }
      </style>
      <svg width="4px" height="4px" xmlns="http://www.w3.org/2000/svg">
        <image xlink:href="it doesn’t exist, mouhahahaha" />
      </svg>
    ''')
