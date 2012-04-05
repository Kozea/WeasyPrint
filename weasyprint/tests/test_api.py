# coding: utf8
"""
    weasyprint.tests.test_api
    -------------------------

    Test the public API.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import sys
import os
import io
import contextlib
import threading
import shutil
import tempfile

import pystacia

from .testing_utils import (
    resource_filename, assert_no_logs, TEST_UA_STYLESHEET)
from ..compat import urljoin
from .. import HTML, CSS
from .. import __main__


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


def check_png_pattern(png_bytes):
    with contextlib.closing(pystacia.read_blob(png_bytes)) as image:
        assert image.size == (8, 8)
        lines = image.get_raw('rgba')['raw']
    from .test_draw import _, r, B, assert_pixels_equal
    assert_pixels_equal('api_png', 8, 8, lines, b''.join([
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+r+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
    ]))


@assert_no_logs
def test_python_render():
    """Test rendering with the Python API."""
    html = TestHTML(string='<body><img src=pattern.png>',
        base_url=resource_filename('dummy.html'))
    css = CSS(string='''
        @page { margin: 2px; -weasy-size: 8px; background: #fff }
        body { margin: 0; }
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


@assert_no_logs
def test_command_line_render():
    """Test rendering with the command-line API."""
    css = b'''
        @page { margin: 2px; -weasy-size: 8px; background: #fff }
        body { margin: 0; }
    '''
    html = b'<body><img src=pattern.png>'
    combined = b'<style>' + css + b'</style>' + html
    linked = b'<link rel=stylesheet href=style.css>' + html

    with chdir(resource_filename('')):
        # Reference
        png_bytes = TestHTML(string=combined, base_url='dummy.html').write_png()
        pdf_bytes = TestHTML(string=combined, base_url='dummy.html').write_pdf()
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
