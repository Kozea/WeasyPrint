"""Test CSS nesting."""

import pytest

from ..testing_utils import assert_no_logs, render_pages


@assert_no_logs
@pytest.mark.parametrize('style', (
    'div { p { width: 10px } }',
    'p { div & { width: 10px } }',
    'p { width: 20px; div & { width: 10px } }',
    'p { div & { width: 10px } width: 20px }',
    'div { & { & { p { & { width: 10px } } } } }',
    '@media print { div { p { width: 10px } } }',
    'div { em, p { width: 10px } }',
    'p { a, div & { width: 10px } }',
))
def test_nesting_block(style):
    page, = render_pages('''
      <style>%s</style>
      <div><p></p></div><p></p>
    ''' % style)
    html, = page.children
    body, = html.children
    div, p = body.children
    div_p, = div.children
    assert div_p.width == 10
    assert p.width != 10
