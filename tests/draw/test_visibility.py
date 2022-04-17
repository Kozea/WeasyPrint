"""Test visibility."""

from ..testing_utils import assert_no_logs
from . import assert_pixels

visibility_source = '''
  <style>
    @page { size: 12px 7px }
    body { background: #fff; font: 1px/1 serif }
    img { margin: 1px 0 0 1px; }
    %s
  </style>
  <div>
    <img src="pattern.png">
    <span><img src="pattern.png"></span>
  </div>'''


@assert_no_logs
def test_visibility_1():
    assert_pixels('visibility_reference', 12, 7, '''
        ____________
        _rBBB_rBBB__
        _BBBB_BBBB__
        _BBBB_BBBB__
        _BBBB_BBBB__
        ____________
        ____________
    ''', visibility_source % '')


@assert_no_logs
def test_visibility_2():
    assert_pixels('visibility_hidden', 12, 7, '''
        ____________
        ____________
        ____________
        ____________
        ____________
        ____________
        ____________
    ''', visibility_source % 'div { visibility: hidden }')


@assert_no_logs
def test_visibility_3():
    assert_pixels('visibility_mixed', 12, 7, '''
        ____________
        ______rBBB__
        ______BBBB__
        ______BBBB__
        ______BBBB__
        ____________
        ____________
    ''', visibility_source % 'div { visibility: hidden } '
                             'span { visibility: visible }')


@assert_no_logs
def test_visibility_4():
    assert_pixels('visibility_hidden_page', 12, 7, '''
        ____________
        _rBBB_rBBB__
        _BBBB_BBBB__
        _BBBB_BBBB__
        _BBBB_BBBB__
        ____________
        ____________
    ''', visibility_source % '@page { visibility: hidden; background: red }')
