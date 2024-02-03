"""Test opacity."""

from ..testing_utils import assert_no_logs

opacity_source = '''
    <style>
        @page { size: 60px 60px }
        div { background: #000; width: 20px; height: 20px }
    </style>
    %s'''


@assert_no_logs
def test_opacity_zero(assert_same_renderings):
    assert_same_renderings(
        opacity_source % '<div></div>',
        opacity_source % '<div></div><div style="opacity: 0"></div>',
        opacity_source % '<div></div><div style="opacity: 0%"></div>',
    )


@assert_no_logs
def test_opacity_normal_range(assert_same_renderings):
    assert_same_renderings(
        opacity_source % '<div style="background: rgb(102, 102, 102)"></div>',
        opacity_source % '<div style="opacity: 0.6"></div>',
        opacity_source % '<div style="opacity: 60%"></div>',
        opacity_source % '<div style="opacity: 60.0%"></div>',
    )


@assert_no_logs
def test_opacity_nested(assert_same_renderings):
    assert_same_renderings(
        opacity_source % '<div style="background: rgb(102, 102, 102)"></div>',
        opacity_source % '<div style="opacity: 0.6"></div>',
        opacity_source % '''
          <div style="background: none; opacity: 0.666666">
            <div style="opacity: 0.9"></div>
          </div>
        ''',  # 0.9 * 0.666666 == 0.6
    )


@assert_no_logs
def test_opacity_percent_clamp_down(assert_same_renderings):
    assert_same_renderings(
        opacity_source % '<div></div>',
        opacity_source % '<div style="opacity: 1.2"></div>',
        opacity_source % '<div style="opacity: 120%"></div>',
    )


@assert_no_logs
def test_opacity_percent_clamp_up(assert_same_renderings):
    assert_same_renderings(
        opacity_source % '<div></div>',
        opacity_source % '<div></div><div style="opacity: -0.2"></div>',
        opacity_source % '<div></div><div style="opacity: -20%"></div>',
    )
