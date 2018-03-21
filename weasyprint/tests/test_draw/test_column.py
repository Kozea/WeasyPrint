"""
    weasyprint.tests.test_draw.test_column
    --------------------------------------

    Test how columns are drawn.

    :copyright: Copyright 2011-2018 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from . import _, a, assert_pixels, r
from ..testing_utils import assert_no_logs, requires


@assert_no_logs
@requires('cairo', (1, 14, 0))
def test_column_rule_1():
    assert_pixels('solid', 5, 3, [
        a + _ + r + _ + a,
        a + _ + r + _ + a,
        _ + _ + _ + _ + _,
    ], '''
      <style>
        img { display: inline-block; width: 1px; height: 1px }
        div { columns: 2; column-rule-style: solid;
              column-rule-width: 1px; column-gap: 3px;
              column-rule-color: red }
        body { margin: 0; font-size: 0; background: white}
        @page { margin: 0; size: 5px 3px }
      </style>
      <div>
        <img src=blue.jpg>
        <img src=blue.jpg>
        <img src=blue.jpg>
        <img src=blue.jpg>
      </div>''')


@assert_no_logs
@requires('cairo', (1, 14, 0))
def test_column_rule_2():
    assert_pixels('dotted', 5, 3, [
        a + _ + r + _ + a,
        a + _ + _ + _ + a,
        a + _ + r + _ + a,
    ], '''
      <style>
        img { display: inline-block; width: 1px; height: 1px }
        div { columns: 2; column-rule-style: dotted;
              column-rule-width: 1px; column-gap: 3px;
              column-rule-color: red }
        body { margin: 0; font-size: 0; background: white}
        @page { margin: 0; size: 5px 3px }
      </style>
      <div>
        <img src=blue.jpg>
        <img src=blue.jpg>
        <img src=blue.jpg>
        <img src=blue.jpg>
        <img src=blue.jpg>
        <img src=blue.jpg>
      </div>''')
