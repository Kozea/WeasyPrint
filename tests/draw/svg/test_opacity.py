"""Test how opacity is handled for SVG."""

import pytest

from ...testing_utils import assert_no_logs

opacity_source = '''
  <style>
    @page { size: 9px }
    svg { display: block }
  </style>
  <svg width="9px" height="9px" xmlns="http://www.w3.org/2000/svg">%s</svg>'''


@assert_no_logs
def test_opacity(assert_same_renderings):
    assert_same_renderings(
        opacity_source % '''
            <rect x="2" y="2" width="5" height="5" stroke-width="2"
                  stroke="rgb(127, 255, 127)" fill="rgb(127, 127, 255)" />
        ''',
        opacity_source % '''
            <rect x="2" y="2" width="5" height="5" stroke-width="2"
                  stroke="lime" fill="blue" opacity="0.5" />
        ''',
    )


@assert_no_logs
def test_fill_opacity(assert_same_renderings):
    assert_same_renderings(
        opacity_source % '''
            <rect x="2" y="2" width="5" height="5"
                  fill="blue" opacity="0.5" />
            <rect x="2" y="2" width="5" height="5" stroke-width="2"
                  stroke="lime" fill="transparent" />
        ''',
        opacity_source % '''
            <rect x="2" y="2" width="5" height="5" stroke-width="2"
                  stroke="lime" fill="blue" fill-opacity="0.5" />
        ''',
    )


@pytest.mark.xfail
@assert_no_logs
def test_stroke_opacity(assert_same_renderings):
    # TODO: This test (and the other ones) fail because of a difference between
    # the PDF and the SVG specifications: transparent borders have to be drawn
    # on top of the shape filling in SVG but not in PDF. See:
    # - PDF-1.7 11.7.4.4 Note 2
    # - https://www.w3.org/TR/SVG2/render.html#PaintingShapesAndText
    assert_same_renderings(
        '''
            <rect x="2" y="2" width="5" height="5"
                  fill="blue" />
            <rect x="2" y="2" width="5" height="5" stroke-width="2"
                  stroke="lime" fill="transparent" opacity="0.5" />
        ''',
        opacity_source % '''
            <rect x="2" y="2" width="5" height="5" stroke-width="2"
                  stroke="lime" fill="blue" stroke-opacity="0.5" />
        ''',
    )


@pytest.mark.xfail
@assert_no_logs
def test_stroke_fill_opacity(assert_same_renderings):
    assert_same_renderings(
        opacity_source % '''
            <rect x="2" y="2" width="5" height="5"
                  fill="blue" opacity="0.5" />
            <rect x="2" y="2" width="5" height="5" stroke-width="2"
                  stroke="lime" fill="transparent" opacity="0.5" />
        ''',
        opacity_source % '''
            <rect x="2" y="2" width="5" height="5" stroke-width="2"
                  stroke="lime" fill="blue"
                  stroke-opacity="0.5" fill-opacity="0.5" />
        ''',
    )


@pytest.mark.xfail
@assert_no_logs
def test_pattern_gradient_stroke_fill_opacity(assert_same_renderings):
    assert_same_renderings(
        opacity_source % '''
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
        ''',
        opacity_source % '''
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
        ''',
        tolerance=1,
    )


@assert_no_logs
def test_translate_opacity(assert_same_renderings):
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/1976
    assert_same_renderings(
        opacity_source % '''
            <rect transform="translate(2, 2)" width="5" height="5"
                  fill="blue" opacity="0.5" />
        ''',
        opacity_source % '''
            <rect x="2" y="2" width="5" height="5"
                  fill="blue" opacity="0.5" />
        ''',
    )
