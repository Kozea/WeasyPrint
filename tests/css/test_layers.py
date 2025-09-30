"""Test CSS layers."""

import pytest

from ..testing_utils import assert_no_logs, render_pages


@assert_no_logs
@pytest.mark.parametrize('style', [
    '@layer { div { width: 100px } }',
    '@layer a { div { width: 100px } }',
    '''
    div { width: 100px }
    @layer a { div { width: 200px } }
    ''',
    '''
    @layer { div { width: 200px } }
    @layer a { div { width: 100px } }
    ''',
    '''
    @layer a { div { width: 200px } }
    @layer { div { width: 100px } }
    ''',
    '''
    @layer a { div { width: 200px } }
    @layer a { div { width: 100px } }
    ''',
    '''
    @layer a { div { width: 100px } }
    @layer a.b { div { width: 200px } }
    ''',
    '''
    @layer a.b { div { width: 200px } }
    @layer a { div { width: 100px } }
    ''',
    '''
    @layer a { div { width: 200px } }
    @layer b { div { width: 100px } }
    ''',
    '''
    @layer b, a;
    @layer a { div { width: 100px } }
    @layer b { div { width: 200px } }
    ''',
    '''
    @layer b;
    @layer a { div { width: 100px } }
    @layer b { div { width: 200px } }
    ''',
    '''
    @import url(data:text/css,div{width:100px});
    @layer a { div { width: 200px } }
    ''',
    '''
    @import url(data:text/css,div{width:200px}) layer;
    @layer a { div { width: 100px } }
    ''',
    '''
    @import url(data:text/css,div{width:200px}) layer(b);
    @layer a { div { width: 100px } }
    ''',
    '''
    @import url(data:text/css,div{width:100px}) layer(a);
    @layer a.b { div { width: 200px } }
    ''',
    '''
    @import url(data:text/css,div{width:200px}) layer(a.b);
    @layer a { div { width: 100px } }
    ''',
    '''
    @layer a { div { width: 100px } }
    @import url(data:text/css,div{width:200px}) layer(a.b);
    ''',
])
def test_layers(style):
    page, = render_pages('''
      <style>
        %s
      </style>
      <div>abc</div>
    ''' % style)
    html, = page.children
    body, = html.children
    div, = body.children
    assert div.width == 100
