"""Test CSS shorthands."""

from weasyprint import CSS

from ..testing_utils import assert_no_logs, resource_path


@assert_no_logs
def test_expand_shorthands():
    sheet = CSS(resource_path('sheet2.css'))
    assert list(sheet.matcher.lower_local_name_selectors) == ['li']

    rules = sheet.matcher.lower_local_name_selectors['li'][0][4]
    assert rules[0][0] == 'margin_bottom'
    assert rules[0][1] == (3, 'em')
    assert rules[1][0] == 'margin_top'
    assert rules[1][1] == (2, 'em')
    assert rules[2][0] == 'margin_right'
    assert rules[2][1] == (0, None)
    assert rules[3][0] == 'margin_bottom'
    assert rules[3][1] == (2, 'em')
    assert rules[4][0] == 'margin_left'
    assert rules[4][1] == (0, None)
    assert rules[5][0] == 'margin_left'
    assert rules[5][1] == (4, 'em')

    # TODO: test that the values are correct too.


