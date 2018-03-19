"""
    weasyprint.tests.test_draw.test_opacity
    ---------------------------------------

    Test opacity.

    :copyright: Copyright 2011-2018 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from . import assert_same_rendering
from ..testing_utils import assert_no_logs

opacity_source = '''
    <style>
        @page { size: 60px 60px }
        body { margin: 0; background: #fff }
        div { background: #000; width: 20px; height: 20px }
    </style>
    %s'''


@assert_no_logs
def test_opacity_1():
    assert_same_rendering(60, 60, [
        ('opacity_0_reference', opacity_source % '''
            <div></div>
        '''),
        ('opacity_0', opacity_source % '''
            <div></div>
            <div style="opacity: 0"></div>
        '''),
    ])


@assert_no_logs
def test_opacity_2():
    assert_same_rendering(60, 60, [
        ('opacity_color_reference', opacity_source % '''
            <div style="background: rgb(102, 102, 102)"></div>
        '''),
        ('opacity_color', opacity_source % '''
            <div style="opacity: 0.6"></div>
        '''),
    ])


@assert_no_logs
def test_opacity_3():
    assert_same_rendering(60, 60, [
        ('opacity_multiplied_reference', opacity_source % '''
            <div style="background: rgb(102, 102, 102)"></div>
        '''),
        ('opacity_multiplied', opacity_source % '''
            <div style="opacity: 0.6"></div>
        '''),
        ('opacity_multiplied_2', opacity_source % '''
            <div style="background: none; opacity: 0.666666">
                <div style="opacity: 0.9"></div>
            </div>
        '''),  # 0.9 * 0.666666 == 0.6
    ])
