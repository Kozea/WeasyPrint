"""
    weasyprint.tests.test_api
    -------------------------

    Test the public API.

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import gzip
import io
import math
import os
import sys
import unicodedata
import zlib
from pathlib import Path
from urllib.parse import urljoin, uses_relative

import cairocffi as cairo
import py
import pytest

from .. import CSS, HTML, __main__, default_url_fetcher
from ..urls import path2url
from .test_draw import assert_pixels_equal, image_to_pixels, parse_pixels
from .testing_utils import (
    FakeHTML, assert_no_logs, capture_logs, http_server, resource_filename)


def _test_resource(class_, basename, check, **kwargs):
    """Common code for testing the HTML and CSS classes."""
    absolute_filename = resource_filename(basename)
    absolute_path = Path(absolute_filename)
    url = path2url(absolute_filename)
    check(class_(absolute_filename, **kwargs))
    check(class_(absolute_path, **kwargs))
    check(class_(guess=absolute_filename, **kwargs))
    check(class_(guess=absolute_path, **kwargs))
    check(class_(filename=absolute_filename, **kwargs))
    check(class_(filename=absolute_path, **kwargs))
    check(class_(url, **kwargs))
    check(class_(guess=url, **kwargs))
    check(class_(url=url, **kwargs))
    with open(absolute_filename, 'rb') as fd:
        check(class_(fd, **kwargs))
    with open(absolute_filename, 'rb') as fd:
        check(class_(guess=fd, **kwargs))
    with open(absolute_filename, 'rb') as fd:
        check(class_(file_obj=fd, **kwargs))
    with open(absolute_filename, 'rb') as fd:
        content = fd.read()
    py.path.local(os.path.dirname(__file__)).chdir()
    relative_filename = os.path.join('resources', basename)
    relative_path = Path(relative_filename)
    check(class_(relative_filename, **kwargs))
    check(class_(relative_path, **kwargs))
    check(class_(string=content, base_url=relative_filename, **kwargs))
    encoding = kwargs.get('encoding') or 'utf8'
    check(class_(string=content.decode(encoding),  # unicode
                 base_url=relative_filename, **kwargs))
    with pytest.raises(TypeError):
        class_(filename='foo', url='bar')


def _check_doc1(html, has_base_url=True):
    """Check that a parsed HTML document looks like resources/doc1.html"""
    root = html.etree_element
    assert root.tag == 'html'
    assert [child.tag for child in root] == ['head', 'body']
    _head, body = root
    assert [child.tag for child in body] == ['h1', 'p', 'ul', 'div']
    h1, p, ul, div = body
    assert h1.text == 'WeasyPrint test document (with Ünicōde)'
    if has_base_url:
        url = urljoin(html.base_url, 'pattern.png')
        assert url.startswith('file:')
        assert url.endswith('weasyprint/tests/resources/pattern.png')
    else:
        assert html.base_url is None


def _run(args, stdin=b''):
    stdin = io.BytesIO(stdin)
    stdout = io.BytesIO()
    try:
        __main__.HTML = FakeHTML
        __main__.main(args.split(), stdin=stdin, stdout=stdout)
    finally:
        __main__.HTML = HTML
    return stdout.getvalue()


class _fake_file(object):
    def __init__(self):
        self.chunks = []

    def write(self, data):
        self.chunks.append(bytes(data[:]))

    def getvalue(self):
        return b''.join(self.chunks)


def _png_size(result):
    png_bytes, width, height = result
    surface = cairo.ImageSurface.create_from_png(io.BytesIO(png_bytes))
    assert (surface.get_width(), surface.get_height()) == (width, height)
    return width, height


def _round_meta(pages):
    """Eliminate errors of floating point arithmetic for metadata.
    (eg. 49.99999999999994 instead of 50)

    """
    for page in pages:
        anchors = page.anchors
        for anchor_name, (pos_x, pos_y) in anchors.items():
            anchors[anchor_name] = round(pos_x, 6), round(pos_y, 6)
        links = page.links
        for i, link in enumerate(links):
            link_type, target, (pos_x, pos_y, width, height) = link
            link = (
                link_type, target, (round(pos_x, 6), round(pos_y, 6),
                                    round(width, 6), round(height, 6)))
            links[i] = link
        bookmarks = page.bookmarks
        for i, (level, label, (pos_x, pos_y), state) in enumerate(bookmarks):
            bookmarks[i] = (level, label,
                            (round(pos_x, 6), round(pos_y, 6)), state)


@assert_no_logs
def test_html_parsing():
    """Test the constructor for the HTML class."""
    _test_resource(FakeHTML, 'doc1.html', _check_doc1)
    _test_resource(FakeHTML, 'doc1_UTF-16BE.html', _check_doc1,
                   encoding='UTF-16BE')

    py.path.local(os.path.dirname(__file__)).chdir()
    filename = os.path.join('resources', 'doc1.html')
    with open(filename, encoding='utf-8') as fd:
        string = fd.read()
    _check_doc1(FakeHTML(string=string, base_url=filename))
    _check_doc1(FakeHTML(string=string), has_base_url=False)
    string_with_meta = string.replace(
        '<meta', '<base href="resources/"><meta')
    _check_doc1(FakeHTML(string=string_with_meta, base_url='.'))


@assert_no_logs
def test_css_parsing():
    """Test the constructor for the CSS class."""
    def check_css(css):
        """Check that a parsed stylsheet looks like resources/utf8-test.css"""
        # Using 'encoding' adds a CSSCharsetRule
        h1_rule, = css.matcher.lower_local_name_selectors['h1']
        assert h1_rule[3] == 'before'
        assert h1_rule[4][0][0] == 'content'
        assert h1_rule[4][0][1][0][1] == 'I løvë Unicode'
        assert h1_rule[4][1][0] == 'background_image'
        assert h1_rule[4][1][1][0][0] == 'url'
        assert h1_rule[4][1][1][0][1].startswith('file:')
        assert h1_rule[4][1][1][0][1].endswith(
            'weasyprint/tests/resources/pattern.png')

    _test_resource(CSS, 'utf8-test.css', check_css)
    _test_resource(CSS, 'latin1-test.css', check_css, encoding='latin1')


def check_png_pattern(png_bytes, x2=False, blank=False, rotated=False):
    if blank:
        expected_pixels = '''
            ________
            ________
            ________
            ________
            ________
            ________
            ________
            ________
        '''
        size = 8
    elif x2:
        expected_pixels = '''
            ________________
            ________________
            ________________
            ________________
            ____rrBBBBBB____
            ____rrBBBBBB____
            ____BBBBBBBB____
            ____BBBBBBBB____
            ____BBBBBBBB____
            ____BBBBBBBB____
            ____BBBBBBBB____
            ____BBBBBBBB____
            ________________
            ________________
            ________________
            ________________
        '''
        size = 16
    elif rotated:
        expected_pixels = '''
            ________
            ________
            __BBBB__
            __BBBB__
            __BBBB__
            __rBBB__
            ________
            ________
        '''
        size = 8
    else:
        expected_pixels = '''
            ________
            ________
            __rBBB__
            __BBBB__
            __BBBB__
            __BBBB__
            ________
            ________
        '''
        size = 8
    surface = cairo.ImageSurface.create_from_png(io.BytesIO(png_bytes))
    assert_pixels_equal('api_png', size, size,
                        image_to_pixels(surface, size, size),
                        b"".join(parse_pixels(expected_pixels)))


@assert_no_logs
def test_python_render(tmpdir):
    """Test rendering with the Python API."""
    base_url = resource_filename('dummy.html')
    html_string = '<body><img src=pattern.png>'
    css_string = '''
        @page { margin: 2px; size: 8px; background: #fff }
        body { margin: 0; font-size: 0 }
        img { image-rendering: pixelated }

        @media screen { img { transform: rotate(-90deg) } }
    '''
    html = FakeHTML(string=html_string, base_url=base_url)
    css = CSS(string=css_string)

    png_bytes = html.write_png(stylesheets=[css])
    pdf_bytes = html.write_pdf(stylesheets=[css])
    assert png_bytes.startswith(b'\211PNG\r\n\032\n')
    assert pdf_bytes.startswith(b'%PDF')
    check_png_pattern(png_bytes)
    # TODO: check PDF content? How?

    png_file = _fake_file()
    html.write_png(png_file, stylesheets=[css])
    assert png_file.getvalue() == png_bytes
    pdf_file = _fake_file()
    html.write_pdf(pdf_file, stylesheets=[css])
    # assert pdf_file.read_binary() == pdf_bytes

    png_file = tmpdir.join('1.png')
    pdf_file = tmpdir.join('1.pdf')
    html.write_png(png_file.strpath, stylesheets=[css])
    html.write_pdf(pdf_file.strpath, stylesheets=[css])
    assert png_file.read_binary() == png_bytes
    # assert pdf_file.read_binary() == pdf_bytes

    png_file = tmpdir.join('2.png')
    pdf_file = tmpdir.join('2.pdf')
    with open(png_file.strpath, 'wb') as png_fd:
        html.write_png(png_fd, stylesheets=[css])
    with open(pdf_file.strpath, 'wb') as pdf_fd:
        html.write_pdf(pdf_fd, stylesheets=[css])
    assert png_file.read_binary() == png_bytes
    # assert pdf_file.read_binary() == pdf_bytes

    x2_png_bytes = html.write_png(stylesheets=[css], resolution=192)
    check_png_pattern(x2_png_bytes, x2=True)

    screen_css = CSS(string=css_string, media_type='screen')
    rotated_png_bytes = html.write_png(stylesheets=[screen_css])
    check_png_pattern(rotated_png_bytes, rotated=True)

    assert FakeHTML(
        string=html_string, base_url=base_url, media_type='screen'
    ).write_png(
        stylesheets=[io.BytesIO(css_string.encode('utf8'))]
    ) == rotated_png_bytes
    assert FakeHTML(
        string='<style>%s</style>%s' % (css_string, html_string),
        base_url=base_url, media_type='screen'
    ).write_png() == rotated_png_bytes


@assert_no_logs
def test_command_line_render(tmpdir):
    css = b'''
        @page { margin: 2px; size: 8px; background: #fff }
        @media screen { img { transform: rotate(-90deg) } }
        body { margin: 0; font-size: 0 }
    '''
    html = b'<body><img src=pattern.png>'
    combined = b'<style>' + css + b'</style>' + html
    linked = b'<link rel=stylesheet href=style.css>' + html

    py.path.local(resource_filename('')).chdir()
    # Reference
    html_obj = FakeHTML(string=combined, base_url='dummy.html')
    # pdf_bytes = html_obj.write_pdf()
    png_bytes = html_obj.write_png()
    x2_png_bytes = html_obj.write_png(resolution=192)
    rotated_png_bytes = FakeHTML(string=combined, base_url='dummy.html',
                                 media_type='screen').write_png()
    empty_png_bytes = FakeHTML(
        string=b'<style>' + css + b'</style>').write_png()
    check_png_pattern(png_bytes)
    check_png_pattern(rotated_png_bytes, rotated=True)
    check_png_pattern(empty_png_bytes, blank=True)

    tmpdir.chdir()
    with open(resource_filename('pattern.png'), 'rb') as pattern_fd:
        pattern_bytes = pattern_fd.read()
    tmpdir.join('pattern.png').write_binary(pattern_bytes)
    tmpdir.join('no_css.html').write_binary(html)
    tmpdir.join('combined.html').write_binary(combined)
    tmpdir.join('combined-UTF-16BE.html').write_binary(
        combined.decode('ascii').encode('UTF-16BE'))
    tmpdir.join('linked.html').write_binary(linked)
    tmpdir.join('style.css').write_binary(css)

    _run('combined.html out1.png')
    _run('combined.html out2.pdf')
    assert tmpdir.join('out1.png').read_binary() == png_bytes
    # TODO: check PDF content? How?
    # assert tmpdir.join('out2.pdf').read_binary() == pdf_bytes

    _run('combined-UTF-16BE.html out3.png --encoding UTF-16BE')
    assert tmpdir.join('out3.png').read_binary() == png_bytes

    _run(tmpdir.join('combined.html').strpath + ' out4.png')
    assert tmpdir.join('out4.png').read_binary() == png_bytes

    _run(path2url(tmpdir.join('combined.html').strpath) + ' out5.png')
    assert tmpdir.join('out5.png').read_binary() == png_bytes

    _run('linked.html out6.png')  # test relative URLs
    assert tmpdir.join('out6.png').read_binary() == png_bytes

    _run('combined.html out7 -f png')
    _run('combined.html out8 --format pdf')
    assert tmpdir.join('out7').read_binary() == png_bytes
    # assert tmpdir.join('out8').read_binary(), pdf_bytes

    _run('no_css.html out9.png')
    _run('no_css.html out10.png -s style.css')
    assert tmpdir.join('out9.png').read_binary() != png_bytes
    # assert tmpdir.join('out10.png').read_binary() == png_bytes

    stdout = _run('--format png combined.html -')
    assert stdout == png_bytes

    _run('- out11.png', stdin=combined)
    check_png_pattern(tmpdir.join('out11.png').read_binary())
    assert tmpdir.join('out11.png').read_binary() == png_bytes

    stdout = _run('--format png - -', stdin=combined)
    assert stdout == png_bytes

    _run('combined.html out13.png --media-type screen')
    _run('combined.html out12.png -m screen')
    _run('linked.html out14.png -m screen')
    assert tmpdir.join('out12.png').read_binary() == rotated_png_bytes
    assert tmpdir.join('out13.png').read_binary() == rotated_png_bytes
    assert tmpdir.join('out14.png').read_binary() == rotated_png_bytes

    stdout = _run('-f pdf combined.html -')
    assert stdout.count(b'attachment') == 0
    stdout = _run('-f pdf -a pattern.png combined.html -')
    assert stdout.count(b'attachment') == 1
    stdout = _run('-f pdf -a style.css -a pattern.png combined.html -')
    assert stdout.count(b'attachment') == 2

    stdout = _run('-f png -r 192 linked.html -')
    assert stdout == x2_png_bytes
    stdout = _run('-f png --resolution 192 linked.html -')
    assert _run('linked.html - -f png --resolution 192') == x2_png_bytes
    assert stdout == x2_png_bytes

    os.mkdir('subdirectory')
    py.path.local('subdirectory').chdir()
    with capture_logs() as logs:
        stdout = _run('--format png - -', stdin=combined)
    assert len(logs) == 1
    assert logs[0].startswith('ERROR: Failed to load image')
    assert stdout == empty_png_bytes

    stdout = _run('--format png --base-url .. - -', stdin=combined)
    assert stdout == png_bytes


@assert_no_logs
def test_unicode_filenames(tmpdir):
    """Test non-ASCII filenames both in Unicode or bytes form."""
    # Replicate pattern.png in CSS so that base_url does not matter.
    html = b'''
        <style>
            @page { margin: 2px; size: 8px; background: #fff }
            html { background: #00f; }
            body { background: #f00; width: 1px; height: 1px }
        </style>
        <body>
    '''
    png_bytes = FakeHTML(string=html).write_png()
    check_png_pattern(png_bytes)
    unicode_filename = 'Unicödé'
    if sys.platform.startswith('darwin'):
        unicode_filename = unicodedata.normalize('NFD', unicode_filename)

    tmpdir.chdir()
    tmpdir.join(unicode_filename).write(html)
    bytes_file, = tmpdir.listdir()
    assert bytes_file.basename == unicode_filename

    assert FakeHTML(unicode_filename).write_png() == png_bytes
    assert FakeHTML(bytes_file.strpath).write_png() == png_bytes

    os.remove(unicode_filename)
    assert tmpdir.listdir() == []

    FakeHTML(string=html).write_png(unicode_filename)
    assert bytes_file.read_binary() == png_bytes


@assert_no_logs
def test_low_level_api():
    html = FakeHTML(string='<body>')
    css = CSS(string='''
        @page { margin: 2px; size: 8px; background: #fff }
        html { background: #00f; }
        body { background: #f00; width: 1px; height: 1px }
    ''')
    pdf_bytes = html.write_pdf(stylesheets=[css])
    assert pdf_bytes.startswith(b'%PDF')
    # TODO: check PDF content? How?
    # assert html.render([css]).write_pdf() == pdf_bytes

    png_bytes = html.write_png(stylesheets=[css])
    document = html.render([css], enable_hinting=True)
    page, = document.pages
    assert page.width == 8
    assert page.height == 8
    assert document.write_png() == (png_bytes, 8, 8)
    assert document.copy([page]).write_png() == (png_bytes, 8, 8)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 8, 8)
    page.paint(cairo.Context(surface))
    file_obj = io.BytesIO()
    surface.write_to_png(file_obj)
    check_png_pattern(file_obj.getvalue())

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 8, 8)
    context = cairo.Context(surface)
    # Rotate at the center
    context.translate(4, 4)
    context.rotate(-math.pi / 2)
    context.translate(-4, -4)
    page.paint(context)
    file_obj = io.BytesIO()
    surface.write_to_png(file_obj)
    check_png_pattern(file_obj.getvalue(), rotated=True)

    document = html.render([css], enable_hinting=True)
    page, = document.pages
    assert (page.width, page.height) == (8, 8)
    png_bytes, width, height = document.write_png(resolution=192)
    assert (width, height) == (16, 16)
    check_png_pattern(png_bytes, x2=True)

    document = html.render([css], enable_hinting=True)
    page, = document.pages
    assert (page.width, page.height) == (8, 8)
    # A resolution that is not multiple of 96:
    assert _png_size(document.write_png(resolution=145.2)) == (13, 13)

    document = FakeHTML(string='''
        <style>
            @page:first { size: 5px 10px } @page { size: 6px 4px }
            p { page-break-before: always }
        </style>
        <p></p>
        <p></p>
    ''').render()
    page_1, page_2 = document.pages
    assert (page_1.width, page_1.height) == (5, 10)
    assert (page_2.width, page_2.height) == (6, 4)

    result = document.write_png()
    # (Max of both widths, Sum of both heights)
    assert _png_size(result) == (6, 14)
    assert document.copy([page_1, page_2]).write_png() == result
    assert _png_size(document.copy([page_1]).write_png()) == (5, 10)
    assert _png_size(document.copy([page_2]).write_png()) == (6, 4)


@pytest.mark.parametrize('html, expected_by_page, expected_tree, round', (
    ('''
        <style>* { height: 10px }</style>
        <h1>a</h1>
        <h4 style="page-break-after: always">b</h4>
        <h3 style="position: relative; top: 2px; left: 3px">c</h3>
        <h2>d</h2>
        <h1>e</h1>
    ''', [
        [(1, 'a', (0, 0), 'open'), (4, 'b', (0, 10), 'open')],
        [(3, 'c', (3, 2), 'open'), (2, 'd', (0, 10), 'open'),
         (1, 'e', (0, 20), 'open')],
    ], [
        ('a', (0, 0, 0), [
            ('b', (0, 0, 10), [], 'open'),
            ('c', (1, 3, 2), [], 'open'),
            ('d', (1, 0, 10), [], 'open')], 'open'),
        ('e', (1, 0, 20), [], 'open'),
    ], False),
    ('''
        <style>
            * { height: 90px; margin: 0 0 10px 0 }
        </style>
        <h1>Title 1</h1>
        <h1>Title 2</h1>
        <h2 style="position: relative; left: 20px">Title 3</h2>
        <h2>Title 4</h2>
        <h3>Title 5</h3>
        <span style="display: block; page-break-before: always"></span>
        <h2>Title 6</h2>
        <h1>Title 7</h1>
        <h2>Title 8</h2>
        <h3>Title 9</h3>
        <h1>Title 10</h1>
        <h2>Title 11</h2>
    ''', [
        [
            (1, 'Title 1', (0, 0), 'open'),
            (1, 'Title 2', (0, 100), 'open'),
            (2, 'Title 3', (20, 200), 'open'),
            (2, 'Title 4', (0, 300), 'open'),
            (3, 'Title 5', (0, 400), 'open')
        ], [
            (2, 'Title 6', (0, 100), 'open'),
            (1, 'Title 7', (0, 200), 'open'),
            (2, 'Title 8', (0, 300), 'open'),
            (3, 'Title 9', (0, 400), 'open'),
            (1, 'Title 10', (0, 500), 'open'),
            (2, 'Title 11', (0, 600), 'open')
        ],
    ], [
        ('Title 1', (0, 0, 0), [], 'open'),
        ('Title 2', (0, 0, 100), [
            ('Title 3', (0, 20, 200), [], 'open'),
            ('Title 4', (0, 0, 300), [
                ('Title 5', (0, 0, 400), [], 'open')], 'open'),
            ('Title 6', (1, 0, 100), [], 'open')], 'open'),
        ('Title 7', (1, 0, 200), [
            ('Title 8', (1, 0, 300), [
                ('Title 9', (1, 0, 400), [], 'open')], 'open')], 'open'),
        ('Title 10', (1, 0, 500), [
            ('Title 11', (1, 0, 600), [], 'open')], 'open'),
    ], False),
    ('''
        <style>* { height: 10px }</style>
        <h2>A</h2> <p>depth 1</p>
        <h4>B</h4> <p>depth 2</p>
        <h2>C</h2> <p>depth 1</p>
        <h3>D</h3> <p>depth 2</p>
        <h4>E</h4> <p>depth 3</p>
    ''', [[
        (2, 'A', (0, 0), 'open'),
        (4, 'B', (0, 20), 'open'),
        (2, 'C', (0, 40), 'open'),
        (3, 'D', (0, 60), 'open'),
        (4, 'E', (0, 80), 'open'),
    ]], [
        ('A', (0, 0, 0), [
            ('B', (0, 0, 20), [], 'open')], 'open'),
        ('C', (0, 0, 40), [
            ('D', (0, 0, 60), [
                ('E', (0, 0, 80), [], 'open')], 'open')], 'open'),
    ], False),
    ('''
        <style>* { height: 10px; font-size: 0 }</style>
        <h2>A</h2> <p>h2 depth 1</p>
        <h4>B</h4> <p>h4 depth 2</p>
        <h3>C</h3> <p>h3 depth 2</p>
        <h5>D</h5> <p>h5 depth 3</p>
        <h1>E</h1> <p>h1 depth 1</p>
        <h2>F</h2> <p>h2 depth 2</p>
        <h2>G</h2> <p>h2 depth 2</p>
        <h4>H</h4> <p>h4 depth 3</p>
        <h1>I</h1> <p>h1 depth 1</p>
    ''', [[
        (2, 'A', (0, 0), 'open'),
        (4, 'B', (0, 20), 'open'),
        (3, 'C', (0, 40), 'open'),
        (5, 'D', (0, 60), 'open'),
        (1, 'E', (0, 70), 'open'),
        (2, 'F', (0, 90), 'open'),
        (2, 'G', (0, 110), 'open'),
        (4, 'H', (0, 130), 'open'),
        (1, 'I', (0, 150), 'open'),
    ]], [
        ('A', (0, 0, 0), [
            ('B', (0, 0, 20), [], 'open'),
            ('C', (0, 0, 40), [
                ('D', (0, 0, 60), [], 'open')], 'open')], 'open'),
        ('E', (0, 0, 70), [
            ('F', (0, 0, 90), [], 'open'),
            ('G', (0, 0, 110), [
                ('H', (0, 0, 130), [], 'open')], 'open')], 'open'),
        ('I', (0, 0, 150), [], 'open'),
    ], False),
    ('<h1>é', [
        [(1, 'é', (0, 0), 'open')]
    ], [
        ('é', (0, 0, 0), [], 'open')
    ], False),
    ('''
        <h1 style="transform: translateX(50px)">!
    ''', [
        [(1, '!', (50, 0), 'open')]
    ], [
        ('!', (0, 50, 0), [], 'open')
    ], False),
    ('''
        <style>
          img { display: block; bookmark-label: attr(alt); bookmark-level: 1 }
        </style>
        <img src="%s" alt="Chocolate" />
    ''' % path2url(resource_filename('pattern.png')),
     [[(1, 'Chocolate', (0, 0), 'open')]],
     [('Chocolate', (0, 0, 0), [], 'open')], False),
    ('''
        <h1 style="transform-origin: 0 0;
                   transform: rotate(90deg) translateX(50px)">!
    ''', [[(1, '!', (0, 50), 'open')]], [('!', (0, 0, 50), [], 'open')], True),
    ('''
        <body style="transform-origin: 0 0; transform: rotate(90deg)">
        <h1 style="transform: translateX(50px)">!
    ''', [[(1, '!', (0, 50), 'open')]], [('!', (0, 0, 50), [], 'open')], True),
))
@assert_no_logs
def test_assert_bookmarks(html, expected_by_page, expected_tree, round):
    document = FakeHTML(string=html).render()
    if round:
        _round_meta(document.pages)
    assert [p.bookmarks for p in document.pages] == expected_by_page
    assert document.make_bookmark_tree() == expected_tree


@assert_no_logs
def test_links():
    def assert_links(html, expected_links_by_page, expected_anchors_by_page,
                     expected_resolved_links,
                     base_url=resource_filename('<inline HTML>'),
                     warnings=(), round=False):
        with capture_logs() as logs:
            document = FakeHTML(string=html, base_url=base_url).render()
            if round:
                _round_meta(document.pages)
            resolved_links = list(document.resolve_links())
        assert len(logs) == len(warnings)
        for message, expected in zip(logs, warnings):
            assert expected in message
        assert [p.links for p in document.pages] == expected_links_by_page
        assert [p.anchors for p in document.pages] == expected_anchors_by_page
        assert resolved_links == expected_resolved_links

    assert_links('''
        <style>
            body { font-size: 10px; line-height: 2; width: 200px }
            p { height: 90px; margin: 0 0 10px 0 }
            img { width: 30px; vertical-align: top }
        </style>
        <p><a href="http://weasyprint.org"><img src=pattern.png></a></p>
        <p style="padding: 0 10px"><a
            href="#lipsum"><img style="border: solid 1px"
                                src=pattern.png></a></p>
        <p id=hello>Hello, World</p>
        <p id=lipsum>
            <a style="display: block; page-break-before: always; height: 30px"
               href="#hel%6Co"></a>
        </p>
    ''', [
        [
            ('external', 'http://weasyprint.org', (0, 0, 30, 20)),
            ('external', 'http://weasyprint.org', (0, 0, 30, 30)),
            ('internal', 'lipsum', (10, 100, 32, 20)),
            ('internal', 'lipsum', (10, 100, 32, 32))
        ],
        [('internal', 'hello', (0, 0, 200, 30))],
    ], [
        {'hello': (0, 200)},
        {'lipsum': (0, 0)}
    ], [
        (
            [
                ('external', 'http://weasyprint.org', (0, 0, 30, 20)),
                ('external', 'http://weasyprint.org', (0, 0, 30, 30)),
                ('internal', 'lipsum', (10, 100, 32, 20)),
                ('internal', 'lipsum', (10, 100, 32, 32))
            ],
            [('hello', 0, 200)],
        ),
        (
            [
                ('internal', 'hello', (0, 0, 200, 30))
            ],
            [('lipsum', 0, 0)]),
    ])

    assert_links(
        '''
            <body style="width: 200px">
            <a href="../lipsum/é_%E9" style="display: block; margin: 10px 5px">
        ''', [[('external', 'http://weasyprint.org/foo/lipsum/%C3%A9_%E9',
                (5, 10, 190, 0))]],
        [{}], [([('external', 'http://weasyprint.org/foo/lipsum/%C3%A9_%E9',
                  (5, 10, 190, 0))], [])],
        base_url='http://weasyprint.org/foo/bar/')
    assert_links(
        '''
            <body style="width: 200px">
            <div style="display: block; margin: 10px 5px;
                        -weasy-link: url(../lipsum/é_%E9)">
        ''', [[('external', 'http://weasyprint.org/foo/lipsum/%C3%A9_%E9',
                (5, 10, 190, 0))]],
        [{}], [([('external', 'http://weasyprint.org/foo/lipsum/%C3%A9_%E9',
                  (5, 10, 190, 0))], [])],
        base_url='http://weasyprint.org/foo/bar/')

    # Relative URI reference without a base URI: allowed for links
    assert_links(
        '''
            <body style="width: 200px">
            <a href="../lipsum" style="display: block; margin: 10px 5px">
        ''', [[('external', '../lipsum', (5, 10, 190, 0))]], [{}],
        [([('external', '../lipsum', (5, 10, 190, 0))], [])], base_url=None)

    # Relative URI reference without a base URI: not supported for -weasy-link
    assert_links(
        '''
            <body style="width: 200px">
            <div style="-weasy-link: url(../lipsum);
                        display: block; margin: 10px 5px">
        ''', [[]], [{}], [([], [])], base_url=None, warnings=[
            'WARNING: Ignored `-weasy-link: url("../lipsum")` at 1:1, '
            'Relative URI reference without a base URI'])

    # Internal or absolute URI reference without a base URI: OK
    assert_links(
        '''
            <body style="width: 200px">
            <a href="#lipsum" id="lipsum"
                style="display: block; margin: 10px 5px"></a>
            <a href="http://weasyprint.org/" style="display: block"></a>
        ''', [[('internal', 'lipsum', (5, 10, 190, 0)),
               ('external', 'http://weasyprint.org/', (0, 10, 200, 0))]],
        [{'lipsum': (5, 10)}],
        [([('internal', 'lipsum', (5, 10, 190, 0)),
           ('external', 'http://weasyprint.org/', (0, 10, 200, 0))],
          [('lipsum', 5, 10)])],
        base_url=None)

    assert_links(
        '''
            <body style="width: 200px">
            <div style="-weasy-link: url(#lipsum);
                        margin: 10px 5px" id="lipsum">
        ''',
        [[('internal', 'lipsum', (5, 10, 190, 0))]],
        [{'lipsum': (5, 10)}],
        [([('internal', 'lipsum', (5, 10, 190, 0))], [('lipsum', 5, 10)])],
        base_url=None)

    assert_links(
        '''
            <style> a { display: block; height: 15px } </style>
            <body style="width: 200px">
                <a href="#lipsum"></a>
                <a href="#missing" id="lipsum"></a>
        ''',
        [[('internal', 'lipsum', (0, 0, 200, 15)),
          ('internal', 'missing', (0, 15, 200, 15))]],
        [{'lipsum': (0, 15)}],
        [([('internal', 'lipsum', (0, 0, 200, 15))], [('lipsum', 0, 15)])],
        base_url=None,
        warnings=[
            'ERROR: No anchor #missing for internal URI reference'])

    assert_links(
        '''
            <body style="width: 100px; transform: translateY(100px)">
            <a href="#lipsum" id="lipsum" style="display: block; height: 20px;
                transform: rotate(90deg) scale(2)">
        ''',
        [[('internal', 'lipsum', (30, 10, 40, 200))]],
        [{'lipsum': (70, 10)}],
        [([('internal', 'lipsum', (30, 10, 40, 200))], [('lipsum', 70, 10)])],
        round=True)


# Make relative URL references work with our custom URL scheme.
uses_relative.append('weasyprint-custom')


@assert_no_logs
def test_url_fetcher():
    filename = resource_filename('pattern.png')
    with open(filename, 'rb') as pattern_fd:
        pattern_png = pattern_fd.read()

    def fetcher(url):
        if url == 'weasyprint-custom:foo/%C3%A9_%e9_pattern':
            return dict(string=pattern_png, mime_type='image/png')
        elif url == 'weasyprint-custom:foo/bar.css':
            return dict(string='body { background: url(é_%e9_pattern)',
                        mime_type='text/css')
        else:
            return default_url_fetcher(url)

    base_url = resource_filename('dummy.html')
    css = CSS(string='''
        @page { size: 8px; margin: 2px; background: #fff }
        body { margin: 0; font-size: 0 }
    ''', base_url=base_url)

    def test(html, blank=False):
        html = FakeHTML(string=html, url_fetcher=fetcher, base_url=base_url)
        check_png_pattern(html.write_png(stylesheets=[css]), blank=blank)

    test('<body><img src="pattern.png">')  # Test a "normal" URL
    test('<body><img src="%s">' % Path(filename).as_uri())
    test('<body><img src="%s?ignored">' % Path(filename).as_uri())
    test('<body><img src="weasyprint-custom:foo/é_%e9_pattern">')
    test('<body style="background: url(weasyprint-custom:foo/é_%e9_pattern)">')
    test('<body><li style="list-style: inside '
         'url(weasyprint-custom:foo/é_%e9_pattern)">')
    test('<link rel=stylesheet href="weasyprint-custom:foo/bar.css"><body>')
    test('<style>@import "weasyprint-custom:foo/bar.css";</style><body>')

    with capture_logs() as logs:
        test('<body><img src="custom:foo/bar">', blank=True)
    assert len(logs) == 1
    assert logs[0].startswith(
        'ERROR: Failed to load image at "custom:foo/bar"')

    def fetcher_2(url):
        assert url == 'weasyprint-custom:%C3%A9_%e9.css'
        return dict(string='', mime_type='text/css')
    FakeHTML(string='<link rel=stylesheet href="weasyprint-custom:'
                    'é_%e9.css"><body>', url_fetcher=fetcher_2).render()


@assert_no_logs
def test_html_meta():
    def assert_meta(html, **meta):
        meta.setdefault('title', None)
        meta.setdefault('authors', [])
        meta.setdefault('keywords', [])
        meta.setdefault('generator', None)
        meta.setdefault('description', None)
        meta.setdefault('created', None)
        meta.setdefault('modified', None)
        meta.setdefault('attachments', [])
        assert vars(FakeHTML(string=html).render().metadata) == meta

    assert_meta('<body>')
    assert_meta(
        '''
            <meta name=author content="I Me &amp; Myself">
            <meta name=author content="Smith, John">
            <title>Test document</title>
            <h1>Another title</h1>
            <meta name=generator content="Human after all">
            <meta name=dummy content=ignored>
            <meta name=dummy>
            <meta content=ignored>
            <meta>
            <meta name=keywords content="html ,\tcss,
                                         pdf,css">
            <meta name=dcterms.created content=2011-04>
            <meta name=dcterms.created content=2011-05>
            <meta name=dcterms.modified content=2013>
            <meta name=keywords content="Python; cairo">
            <meta name=description content="Blah… ">
        ''',
        authors=['I Me & Myself', 'Smith, John'],
        title='Test document',
        generator='Human after all',
        keywords=['html', 'css', 'pdf', 'Python; cairo'],
        description="Blah… ",
        created='2011-04',
        modified='2013')
    assert_meta(
        '''
            <title>One</title>
            <meta name=Author>
            <title>Two</title>
            <title>Three</title>
            <meta name=author content=Me>
        ''',
        title='One',
        authors=['', 'Me'])


@assert_no_logs
def test_http():
    def gzip_compress(data):
        file_obj = io.BytesIO()
        gzip_file = gzip.GzipFile(fileobj=file_obj, mode='wb')
        gzip_file.write(data)
        gzip_file.close()
        return file_obj.getvalue()

    with http_server({
        '/gzip': lambda env: (
            (gzip_compress(b'<html test=ok>'), [('Content-Encoding', 'gzip')])
            if 'gzip' in env.get('HTTP_ACCEPT_ENCODING', '') else
            (b'<html test=accept-encoding-header-fail>', [])
        ),
        '/deflate': lambda env: (
            (zlib.compress(b'<html test=ok>'),
             [('Content-Encoding', 'deflate')])
            if 'deflate' in env.get('HTTP_ACCEPT_ENCODING', '') else
            (b'<html test=accept-encoding-header-fail>', [])
        ),
        '/raw-deflate': lambda env: (
            # Remove zlib header and checksum
            (zlib.compress(b'<html test=ok>')[2:-4],
             [('Content-Encoding', 'deflate')])
            if 'deflate' in env.get('HTTP_ACCEPT_ENCODING', '') else
            (b'<html test=accept-encoding-header-fail>', [])
        ),
    }) as root_url:
        assert HTML(root_url + '/gzip').etree_element.get('test') == 'ok'
        assert HTML(root_url + '/deflate').etree_element.get('test') == 'ok'
        assert HTML(
            root_url + '/raw-deflate').etree_element.get('test') == 'ok'
