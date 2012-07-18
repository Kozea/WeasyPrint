# coding: utf8
"""
    weasyprint.tests.test_api
    -------------------------

    Test the public API.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import os
import io
import sys
import contextlib
import threading
import shutil
import tempfile

import pystacia
import lxml.html
import pytest

from .testing_utils import (
    resource_filename, assert_no_logs, capture_logs, TEST_UA_STYLESHEET)
from ..compat import urljoin, urlencode, urlparse_uses_relative
from .. import HTML, CSS, default_url_fetcher
from .. import __main__
from .. import navigator


CHDIR_LOCK = threading.Lock()

@contextlib.contextmanager
def chdir(path):
    """Change the current directory in a context manager."""
    with CHDIR_LOCK:
        old_dir = os.getcwd()
        try:
            os.chdir(path)
            yield
        finally:
            os.chdir(old_dir)


@contextlib.contextmanager
def temp_directory():
    """Context manager that gives the path to a new temporary directory.

    Remove everything on exiting the context.

    """
    directory = tempfile.mkdtemp()
    try:
        yield directory
    finally:
        shutil.rmtree(directory)


def read_file(filename):
    """Shortcut for reading a file."""
    with open(filename, 'rb') as fd:
        return fd.read()


def write_file(filename, content):
    """Shortcut for reading a file."""
    with open(filename, 'wb') as fd:
        fd.write(content)


class TestHTML(HTML):
    """Like HTML, but with the testing (smaller) UA stylesheet"""
    def _ua_stylesheet(self):
        return [TEST_UA_STYLESHEET]


def _test_resource(class_, basename, check, **kwargs):
    """Common code for testing the HTML and CSS classes."""
    absolute_filename = resource_filename(basename)
    check(class_(absolute_filename, **kwargs))
    check(class_(guess=absolute_filename, **kwargs))
    check(class_(filename=absolute_filename, **kwargs))
    check(class_('file://' + absolute_filename, **kwargs))
    check(class_(guess='file://' + absolute_filename, **kwargs))
    check(class_(url='file://' + absolute_filename, **kwargs))
    with open(absolute_filename, 'rb') as fd:
        check(class_(fd, **kwargs))
    with open(absolute_filename, 'rb') as fd:
        check(class_(guess=fd, **kwargs))
    with open(absolute_filename, 'rb') as fd:
        check(class_(file_obj=fd, **kwargs))
    with open(absolute_filename, 'rb') as fd:
        content = fd.read()
    with chdir(os.path.dirname(__file__)):
        relative_filename = os.path.join('resources', basename)
        check(class_(relative_filename, **kwargs))
        check(class_(string=content, base_url=relative_filename, **kwargs))
        encoding = kwargs.get('encoding') or 'utf8'
        check(class_(string=content.decode(encoding),  # unicode
                        base_url=relative_filename, **kwargs))
    with pytest.raises(TypeError):
        class_(filename='foo', url='bar')


@assert_no_logs
def test_html_parsing():
    """Test the constructor for the HTML class."""
    def check_doc1(html):
        """Check that a parsed HTML document looks like resources/doc1.html"""
        assert html.root_element.tag == 'html'
        assert [child.tag for child in html.root_element] == ['head', 'body']
        _head, body = html.root_element
        assert [child.tag for child in body] == ['h1', 'p', 'ul']
        h1 = body[0]
        assert h1.text == 'WeasyPrint test document (with Ünicōde)'
        url = urljoin(h1.base_url, 'pattern.png')
        assert url.startswith('file:')
        assert url.endswith('weasyprint/tests/resources/pattern.png')

    _test_resource(TestHTML, 'doc1.html', check_doc1)
    _test_resource(TestHTML, 'doc1-utf32.html', check_doc1, encoding='utf32')

    filename = resource_filename('doc1.html')
    check_doc1(TestHTML(tree=lxml.html.parse(filename), base_url=filename))


@assert_no_logs
def test_css_parsing():
    """Test the constructor for the CSS class."""
    def check_css(css):
        """Check that a parsed stylsheet looks like resources/utf8-test.css"""
        # Using 'encoding' adds a CSSCharsetRule
        rule = css.stylesheet.rules[-1]
        assert rule.selector.as_css() == 'h1::before'
        content, background = rule.declarations

        assert content.name == 'content'
        string, = content.value
        assert string.value == 'I løvë Unicode'

        assert background.name == 'background-image'
        url_value, = background.value
        assert url_value.type == 'URI'
        url = urljoin(css.base_url, url_value.value)
        assert url.startswith('file:')
        assert url.endswith('weasyprint/tests/resources/pattern.png')

    _test_resource(CSS, 'utf8-test.css', check_css)
    _test_resource(CSS, 'latin1-test.css', check_css, encoding='latin1')


def check_png_pattern(png_bytes, x2=False):
    from .test_draw import _, r, B, assert_pixels_equal
    if x2:
        expected_pixels = [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+r+r+B+B+B+B+B+B+_+_+_+_,
            _+_+_+_+r+r+B+B+B+B+B+B+_+_+_+_,
            _+_+_+_+B+B+B+B+B+B+B+B+_+_+_+_,
            _+_+_+_+B+B+B+B+B+B+B+B+_+_+_+_,
            _+_+_+_+B+B+B+B+B+B+B+B+_+_+_+_,
            _+_+_+_+B+B+B+B+B+B+B+B+_+_+_+_,
            _+_+_+_+B+B+B+B+B+B+B+B+_+_+_+_,
            _+_+_+_+B+B+B+B+B+B+B+B+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]
        size = 16
    else:
        expected_pixels = [
            _+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_,
            _+_+r+B+B+B+_+_,
            _+_+B+B+B+B+_+_,
            _+_+B+B+B+B+_+_,
            _+_+B+B+B+B+_+_,
            _+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_,
        ]
        size = 8
    with contextlib.closing(pystacia.read_blob(png_bytes)) as image:
        assert image.size == (size, size)
        pixels = image.get_raw('rgba')['raw']
    assert_pixels_equal('api_png', size, size,
                        pixels, b''.join(expected_pixels))


@assert_no_logs
def test_python_render():
    """Test rendering with the Python API."""
    html = TestHTML(string='<body><img src=pattern.png>',
        base_url=resource_filename('dummy.html'))
    css = CSS(string='''
        @page { margin: 2px; size: 8px; background: #fff }
        body { margin: 0; font-size: 0 }
        img { image-rendering: optimizeSpeed }
    ''')

    png_bytes = html.write_png(stylesheets=[css])
    pdf_bytes = html.write_pdf(stylesheets=[css])
    assert png_bytes.startswith(b'\211PNG\r\n\032\n')
    assert pdf_bytes.startswith(b'%PDF')

    check_png_pattern(png_bytes)
    # TODO: check PDF content? How?

    class fake_file(object):
        def __init__(self):
            self.chunks = []
            self.write = self.chunks.append

        def getvalue(self):
            return b''.join(self.chunks)
    png_file = fake_file()
    html.write_png(png_file, stylesheets=[css])
    assert png_file.getvalue() == png_bytes
    pdf_file = fake_file()
    html.write_pdf(pdf_file, stylesheets=[css])
    assert pdf_file.getvalue() == pdf_bytes

    with temp_directory() as temp:
        png_filename = os.path.join(temp, '1.png')
        pdf_filename = os.path.join(temp, '1.pdf')
        html.write_png(png_filename, stylesheets=[css])
        html.write_pdf(pdf_filename, stylesheets=[css])
        assert read_file(png_filename) == png_bytes
        assert read_file(pdf_filename) == pdf_bytes

        png_filename = os.path.join(temp, '2.png')
        pdf_filename = os.path.join(temp, '2.pdf')
        with open(png_filename, 'wb') as png_file:
            html.write_png(png_file, stylesheets=[css])
        with open(pdf_filename, 'wb') as pdf_file:
            html.write_pdf(pdf_file, stylesheets=[css])
        assert read_file(png_filename) == png_bytes
        assert read_file(pdf_filename) == pdf_bytes

    x2_png_bytes = html.write_png(stylesheets=[css], resolution=192)
    check_png_pattern(x2_png_bytes, x2=True)

    pages = list(html.get_png_pages(stylesheets=[css]))
    assert pages == [(8, 8, png_bytes)]
    pages = list(html.get_png_pages(stylesheets=[css], resolution=192))
    assert pages == [(16, 16, x2_png_bytes)]


@assert_no_logs
def test_command_line_render():
    """Test rendering with the command-line API."""
    css = b'''
        @page { margin: 2px; size: 8px; background: #fff }
        body { margin: 0; font-size: 0 }
    '''
    html = b'<body><img src=pattern.png>'
    combined = b'<style>' + css + b'</style>' + html
    linked = b'<link rel=stylesheet href=style.css>' + html

    with chdir(resource_filename('')):
        # Reference
        document = TestHTML(string=combined, base_url='dummy.html')
        png_bytes = document.write_png()
        pdf_bytes = document.write_pdf()
    check_png_pattern(png_bytes)

    def run(args, stdin=b''):
        stdin = io.BytesIO(stdin)
        stdout = io.BytesIO()
        try:
            __main__.HTML = TestHTML
            __main__.main(args.split(), stdin=stdin, stdout=stdout)
        finally:
            __main__.HTML = HTML
        return stdout.getvalue()

    with temp_directory() as temp:
        with chdir(temp):
            pattern_bytes = read_file(resource_filename('pattern.png'))
            write_file('pattern.png', pattern_bytes)
            write_file('no_css.html', html)
            write_file('combined.html', combined)
            write_file('combined-utf32.html',
                combined.decode('ascii').encode('utf32'))
            write_file('linked.html', linked)
            write_file('style.css', css)

            run('combined.html out1.png')
            run('combined.html out2.pdf')
            assert read_file('out1.png') == png_bytes
            assert read_file('out2.pdf') == pdf_bytes

            run('combined-utf32.html out3.png --encoding utf32')
            assert read_file('out3.png') == png_bytes

            combined_absolute = os.path.join(temp, 'combined.html')
            run(combined_absolute + ' out4.png')
            assert read_file('out4.png') == png_bytes

            combined_url = 'file://{0}/{1}'.format(temp, 'combined.html')
            run(combined_url + ' out5.png')
            assert read_file('out5.png') == png_bytes

            run('linked.html out6.png')  # test relative URLs
            assert read_file('out6.png') == png_bytes

            run('combined.html out7 -f png')
            run('combined.html out8 --format pdf')
            assert read_file('out7') == png_bytes
            assert read_file('out8') == pdf_bytes

            run('no_css.html out9.png')
            run('no_css.html out10.png -s style.css')
            assert read_file('out9.png') != png_bytes
            assert read_file('out10.png') == png_bytes

            stdout = run('--format png combined.html -')
            assert stdout == png_bytes

            run('- out11.png', stdin=combined)
            check_png_pattern(read_file('out11.png'))
            assert read_file('out11.png') == png_bytes

            stdout = run('--format png - -', stdin=combined)
            assert stdout == png_bytes


@assert_no_logs
def test_unicode_filenames():
    """Test non-ASCII filenames both in Unicode or bytes form."""
    # Replicate pattern.png in CSS so that base_url does not matter.
    html = b'''
        <style>
            @page { margin: 2px; size: 8px; background: #fff }
            html { background: #00f; }
            body { background: #f00; width: 1px; height: 1px; }
        </style>
        <body>
    '''
    png_bytes = TestHTML(string=html).write_png()
    check_png_pattern(png_bytes)
    # Remember we have __future__.unicode_literals
    unicode_filename = 'Unicödé'
    with temp_directory() as temp:
        with chdir(temp):
            write_file(unicode_filename, html)
            assert os.listdir('.') == [unicode_filename]
            # This should be independent of the encoding used by the filesystem
            bytes_filename, = os.listdir(b'.')

            assert TestHTML(unicode_filename).write_png() == png_bytes
            assert TestHTML(bytes_filename).write_png() == png_bytes

            os.remove(unicode_filename)
            assert os.listdir('.') == []

            TestHTML(string=html).write_png(unicode_filename)
            assert read_file(bytes_filename) == png_bytes

            # Surface.write_to_png does not accept bytes filenames
            # on Python 3
            if sys.version_info[0] < 3:
                os.remove(unicode_filename)
                assert os.listdir('.') == []

                TestHTML(string=html).write_png(bytes_filename)
                assert read_file(unicode_filename) == png_bytes


def wsgi_client(path_info, qs_args=None):
    start_response_calls = []
    def start_response(status, headers):
        start_response_calls.append((status, headers))
    environ = {'PATH_INFO': path_info,
               'QUERY_STRING': urlencode(qs_args or {})}
    response = b''.join(navigator.app(environ, start_response))
    assert len(start_response_calls) == 1
    status, headers = start_response_calls[0]
    return status, dict(headers), response


@assert_no_logs
def test_navigator():
    with temp_directory() as temp:
        status, headers, body = wsgi_client('/favicon.ico')
        assert status == '200 OK'
        assert headers['Content-Type'] == 'image/x-icon'
        assert body == read_file(navigator.FAVICON)

        status, headers, body = wsgi_client('/lipsum')
        assert status == '404 Not Found'

        status, headers, body = wsgi_client('/')
        body = body.decode('utf8')
        assert status == '200 OK'
        assert headers['Content-Type'].startswith('text/html;')
        assert '<title>WeasyPrint Navigator</title>' in body
        assert '<img' not in body
        assert '></a>' not in body

        filename = os.path.join(temp, 'test.html')
        write_file(filename, b'''
            <h1 id=foo><a href="http://weasyprint.org">Lorem ipsum</a></h1>
            <h2><a href="#foo">bar</a></h2>
        ''')

        for status, headers, body in [
            wsgi_client('/view/file://' + filename),
            wsgi_client('/', {'url': 'file://' + filename}),
        ]:
            body = body.decode('utf8')
            assert status == '200 OK'
            assert headers['Content-Type'].startswith('text/html;')
            assert '<title>WeasyPrint Navigator</title>' in body
            assert '<img src="data:image/png;base64,' in body
            assert ' name="foo"></a>' in body
            assert ' href="#foo"></a>' in body
            assert ' href="/view/http://weasyprint.org"></a>' in body

        status, headers, body = wsgi_client('/pdf/file://' + filename)
        assert status == '200 OK'
        assert headers['Content-Type'] == 'application/pdf'
        assert body.startswith(b'%PDF')
        assert (b'/A << /Type /Action /S /URI /URI '
                b'(http://weasyprint.org) >>') in body
        lipsum = '\ufeffLorem ipsum'.encode('utf-16-be')
        assert (b'<< /Title (' + lipsum +
                b')\n/A << /Type /Action /S /GoTo') in body


# Make relative URL references work with our custom URL scheme.
urlparse_uses_relative.append('weasyprint-custom')

@assert_no_logs
def test_url_fetcher():
    pattern_png = read_file(resource_filename('pattern.png'))
    def fetcher(url):
        if url == 'weasyprint-custom:foo/pattern':
            return dict(string=pattern_png, mime_type='image/png')
        elif url == 'weasyprint-custom:foo/bar.css':
            return dict(string='body { background: url(pattern)')
        else:
            return default_url_fetcher(url)

    base_url = resource_filename('dummy.html')
    css = CSS(string='''
        @page { size: 8px; margin: 2px; background: #fff }
        body { margin: 0; font-size: 0 }
    ''', base_url=base_url)
    def test(html):
        html = TestHTML(string=html, url_fetcher=fetcher, base_url=base_url)
        check_png_pattern(html.write_png(stylesheets=[css]))

    test('<body><img src="pattern.png">')  # Test a "normal" URL
    test('<body><img src="weasyprint-custom:foo/pattern">')
    test('<body style="background: url(weasyprint-custom:foo/pattern)">')
    test('<body><li style="list-style: inside '
            'url(weasyprint-custom:foo/pattern)">')
    test('<link rel=stylesheet href="weasyprint-custom:foo/bar.css"><body>')
    test('<style>@import "weasyprint-custom:foo/bar.css";</style><body>')

    with capture_logs() as logs:
        with pytest.raises(AssertionError):
            test('<body><img src="custom:foo/bar">')
    assert len(logs) == 1
    assert logs[0].startswith('WARNING: Error for image at custom:foo/bar')
