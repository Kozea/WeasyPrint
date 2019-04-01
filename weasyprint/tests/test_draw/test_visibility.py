"""
    weasyprint.tests.test_draw.test_visibility
    ------------------------------------------

    Test visibility.

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from ..testing_utils import assert_no_logs
from . import B, _, assert_pixels, r

visibility_source = '''
  <style>
    @page { size: 12px 7px }
    body { background: #fff; font: 1px/1 serif }
    img { margin: 1px 0 0 1px; }
    %(extra_css)s
  </style>
  <div>
    <img src="pattern.png">
    <span><img src="pattern.png"></span>
  </div>'''


@assert_no_logs
def test_visibility_1():
    assert_pixels('visibility_reference', 12, 7, [
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + r + B + B + B + _ + r + B + B + B + _ + _,
        _ + B + B + B + B + _ + B + B + B + B + _ + _,
        _ + B + B + B + B + _ + B + B + B + B + _ + _,
        _ + B + B + B + B + _ + B + B + B + B + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
    ], visibility_source % {'extra_css': ''})


@assert_no_logs
def test_visibility_2():
    assert_pixels('visibility_hidden', 12, 7, [
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
    ], visibility_source % {'extra_css': 'div { visibility: hidden }'})


@assert_no_logs
def test_visibility_3():
    assert_pixels('visibility_mixed', 12, 7, [
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + r + B + B + B + _ + _,
        _ + _ + _ + _ + _ + _ + B + B + B + B + _ + _,
        _ + _ + _ + _ + _ + _ + B + B + B + B + _ + _,
        _ + _ + _ + _ + _ + _ + B + B + B + B + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
        _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _ + _,
    ], visibility_source % {'extra_css': '''div { visibility: hidden }
                                 span { visibility: visible } '''})
