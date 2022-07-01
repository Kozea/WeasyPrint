"""Test how pages are drawn."""

import pytest

from ..testing_utils import assert_no_logs


@assert_no_logs
@pytest.mark.parametrize('rule, pixels', (
    ('2n', '_R_R_R_R_R'),
    ('even', '_R_R_R_R_R'),
    ('2n+1', 'R_R_R_R_R_'),
    ('odd', 'R_R_R_R_R_'),
    ('2n+3', '__R_R_R_R_'),
    ('n', 'RRRRRRRRRR'),
    ('n-1', 'RRRRRRRRRR'),
    ('-n+3', 'RRR_______'),
    ('-2n+3', 'R_R_______'),
    ('-n-3', '__________'),
    ('3', '__R_______'),
    ('0n+0', '__________'),
))
def test_nth_page(assert_pixels, rule, pixels):
    assert_pixels('\n'.join(pixels), '''
      <style>
        @page { size: 1px 1px }
        @page:nth(%s) { background: red }
        p { break-after: page }
      </style>
    ''' % rule + 10 * '<p></p>')
