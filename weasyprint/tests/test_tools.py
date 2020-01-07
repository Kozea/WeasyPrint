"""
    weasyprint.tests.test_tools
    ---------------------------

    Test WeasyPrint Web tools.

"""

import io
from urllib.parse import urlencode

import cairocffi as cairo
import pytest

from ..tools import navigator, renderer
from ..urls import URLFetchingError, path2url
from .testing_utils import assert_no_logs


def wsgi_client(module, path_info, query_string_args=None, method='GET'):
    start_response_calls = []

    def start_response(status, headers):
        start_response_calls.append((status, headers))
    environ = {'REQUEST_METHOD': method, 'PATH_INFO': path_info}
    query_string = urlencode(query_string_args or {})
    if method == 'POST':
        environ['wsgi.input'] = io.BytesIO(query_string.encode('utf-8'))
        environ['CONTENT_LENGTH'] = len(query_string.encode('utf-8'))
    else:
        environ['QUERY_STRING'] = query_string
    response = b''.join(module.app(environ, start_response))
    assert len(start_response_calls) == 1
    status, headers = start_response_calls[0]
    return status, dict(headers), response


@assert_no_logs
def test_navigator(tmpdir):
    status, headers, body = wsgi_client(navigator, '/lipsum')
    assert status == '404 Not Found'

    status, headers, body = wsgi_client(navigator, '/')
    body = body.decode('utf8')
    assert status == '200 OK'
    assert headers['Content-Type'].startswith('text/html;')
    assert '<title>WeasyPrint Navigator</title>' in body
    assert '<img' not in body
    assert '></a>' not in body

    test_file = tmpdir.join('test.html')
    test_file.write(b'''
        <h1 id=foo><a href="http://weasyprint.org">Lorem ipsum</a></h1>
        <h2><a href="#foo">bar</a></h2>
    ''')

    url = path2url(test_file.strpath)
    for status, headers, body in [
        wsgi_client(navigator, '/view/' + url),
        wsgi_client(navigator, '/', {'url': url}),
    ]:
        body = body.decode('utf8')
        assert status == '200 OK'
        assert headers['Content-Type'].startswith('text/html;')
        assert '<title>WeasyPrint Navigator</title>' in body
        assert '<img src="data:image/png;base64,' in body
        assert ' name="foo"></a>' in body
        assert ' href="#foo"></a>' in body
        assert ' href="/view/http://weasyprint.org"></a>' in body

    status, headers, body = wsgi_client(navigator, '/pdf/' + url)
    assert status == '200 OK'
    assert headers['Content-Type'] == 'application/pdf'
    assert body.startswith(b'%PDF')
    if cairo.cairo_version() < 11504:  # pragma: no cover
        return
    assert b'/URI (http://weasyprint.org)' in body
    assert b'/Title (Lorem ipsum)' in body

    status, headers, body = wsgi_client(navigator, '/pdf/' + url)
    assert status == '200 OK'
    assert headers['Content-Type'] == 'application/pdf'
    assert body.startswith(b'%PDF')

    with pytest.raises(URLFetchingError):
        wsgi_client(navigator, '/pdf/' + 'test.example')

    with pytest.raises(URLFetchingError):
        wsgi_client(navigator, '/pdf/' + 'test.example', {'test': 'test'})


@assert_no_logs
def test_renderer():
    status, headers, body = wsgi_client(renderer, '/lipsum')
    assert status == '404 Not Found'

    status, headers, body_1 = wsgi_client(renderer, '/')
    assert b'data:image/png;base64,iVBO' in body_1

    status, headers, body_2 = wsgi_client(
        renderer, '/', {'content': renderer.DEFAULT_CONTENT}, method='POST')
    assert body_1 == body_2

    status, headers, body_3 = wsgi_client(
        renderer, '/', {'content': 'abc'}, method='POST')
    assert b'data:image/png;base64,iVBO' in body_3
    assert body_1 != body_3

    status, headers, body_4 = wsgi_client(
        renderer, '/render', {'content': 'abc'}, method='POST')
    assert body_4.startswith(b'iVBO')
    assert body_4 in body_3

    status, headers, body_5 = wsgi_client(
        renderer, '/render', {'content': 'def'}, method='POST')
    assert body_5.startswith(b'iVBO')
    assert body_5 not in body_3
