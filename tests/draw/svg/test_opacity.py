"""
    weasyprint.tests.test_draw.svg.test_opacity
    -------------------------------------------

    Test how opacity is handled for SVG.

"""

import pytest

from ...testing_utils import assert_no_logs
from .. import assert_same_rendering

# TODO: xfail tests fail because of GhostScript and are supposed to work with
# real PDF files.

opacity_source = '''
  <style>
    @page { size: 9px }
    svg { display: block }
  </style>
  <svg width="9px" height="9px" xmlns="http://www.w3.org/2000/svg">%s</svg>'''


@assert_no_logs
def test_opacity():
    assert_same_rendering(9, 9, (
        ('opacity_reference', opacity_source % '''
            <rect x="2" y="2" width="5" height="5" stroke-width="2"
                  stroke="rgb(127, 255, 127)" fill="rgb(127, 127, 255)" />
        '''),
        ('opacity', opacity_source % '''
            <rect x="2" y="2" width="5" height="5" stroke-width="2"
                  stroke="lime" fill="blue" opacity="0.5" />
        '''),
    ))


@assert_no_logs
def test_fill_opacity():
    assert_same_rendering(9, 9, (
        ('fill_opacity_reference', opacity_source % '''
            <rect x="2" y="2" width="5" height="5"
                  fill="blue" opacity="0.5" />
            <rect x="2" y="2" width="5" height="5" stroke-width="2"
                  stroke="lime" fill="transparent" />
        '''),
        ('fill_opacity', opacity_source % '''
            <rect x="2" y="2" width="5" height="5" stroke-width="2"
                  stroke="lime" fill="blue" fill-opacity="0.5" />
        '''),
    ))


@pytest.mark.xfail
@assert_no_logs
def test_stroke_opacity():
    assert_same_rendering(9, 9, (
        ('stroke_opacity_reference', opacity_source % '''
            <rect x="2" y="2" width="5" height="5"
                  fill="blue" />
            <rect x="2" y="2" width="5" height="5" stroke-width="2"
                  stroke="lime" fill="transparent" opacity="0.5" />
        '''),
        ('stroke_opacity', opacity_source % '''
            <rect x="2" y="2" width="5" height="5" stroke-width="2"
                  stroke="lime" fill="blue" stroke-opacity="0.5" />
        '''),
    ))


@pytest.mark.xfail
@assert_no_logs
def test_stroke_fill_opacity():
    assert_same_rendering(9, 9, (
        ('stroke_fill_opacity_reference', opacity_source % '''
            <rect x="2" y="2" width="5" height="5"
                  fill="blue" opacity="0.5" />
            <rect x="2" y="2" width="5" height="5" stroke-width="2"
                  stroke="lime" fill="transparent" opacity="0.5" />
        '''),
        ('stroke_fill_opacity', opacity_source % '''
            <rect x="2" y="2" width="5" height="5" stroke-width="2"
                  stroke="lime" fill="blue"
                  stroke-opacity="0.5" fill-opacity="0.5" />
        '''),
    ))


@pytest.mark.xfail
@assert_no_logs
def test_pattern_gradient_stroke_fill_opacity():
    assert_same_rendering(9, 9, (
        ('pattern_gradient_stroke_fill_opacity_reference', opacity_source % '''
            <defs>
              <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1"
                              gradientUnits="objectBoundingBox">
                <stop stop-color="black" offset="42.86%"></stop>
                <stop stop-color="green" offset="42.86%"></stop>
              </linearGradient>
              <pattern id="pat" x="0" y="0" width="2" height="2"
                       patternUnits="userSpaceOnUse"
                       patternContentUnits="userSpaceOnUse">
                <rect x="0" y="0" width="1" height="1" fill="blue" />
                <rect x="0" y="1" width="1" height="1" fill="red" />
                <rect x="1" y="0" width="1" height="1" fill="red" />
                <rect x="1" y="1" width="1" height="1" fill="blue" />
              </pattern>
            </defs>
            <rect x="2" y="2" width="5" height="5"
                  fill="url(#pat)" opacity="0.5" />
            <rect x="2" y="2" width="5" height="5" stroke-width="2"
                  stroke="url(#grad)" fill="transparent" opacity="0.5" />
        '''),
        ('pattern_gradient_stroke_fill_opacity', opacity_source % '''
            <defs>
              <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1"
                              gradientUnits="objectBoundingBox">
                <stop stop-color="black" offset="42.86%"></stop>
                <stop stop-color="green" offset="42.86%"></stop>
              </linearGradient>
              <pattern id="pat" x="0" y="0" width="2" height="2"
                       patternUnits="userSpaceOnUse"
                       patternContentUnits="userSpaceOnUse">
                <rect x="0" y="0" width="1" height="1" fill="blue" />
                <rect x="0" y="1" width="1" height="1" fill="red" />
                <rect x="1" y="0" width="1" height="1" fill="red" />
                <rect x="1" y="1" width="1" height="1" fill="blue" />
              </pattern>
            </defs>
            <rect x="2" y="2" width="5" height="5" stroke-width="2"
                  stroke="url(#grad)" fill="url(#pat)"
                  stroke-opacity="0.5" fill-opacity="0.5" />
        '''),
    ))
