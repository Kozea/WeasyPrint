"""Test the public API."""

import contextlib
import gzip
import io
import os
import sys
import threading
import unicodedata
import wsgiref.simple_server
import zlib
from functools import partial
from pathlib import Path
from urllib.parse import urljoin, uses_relative

import pytest
from PIL import Image

from weasyprint import CSS, HTML, __main__, default_url_fetcher
from weasyprint.pdf.anchors import resolve_links
from weasyprint.urls import path2url

from .draw import parse_pixels
from .testing_utils import FakeHTML, assert_no_logs, capture_logs, resource_path

try:
    # Available in Python 3.11+
    from contextlib import chdir
except ImportError:
    # Backported from Python 3.11
    from contextlib import AbstractContextManager

    class chdir(AbstractContextManager):  # noqa: N801
        def __init__(self, path):
            self.path = path
            self._old_cwd = []

        def __enter__(self):
            self._old_cwd.append(os.getcwd())
            os.chdir(self.path)

        def __exit__(self, *excinfo):
            os.chdir(self._old_cwd.pop())


def _test_resource(class_, name, check, **kwargs):
    """Common code for testing the HTML and CSS classes."""
    absolute_path = resource_path(name)
    absolute_filename = str(absolute_path)
    url = path2url(absolute_path)
    check(class_(absolute_path, **kwargs))
    check(class_(absolute_filename, **kwargs))
    check(class_(guess=absolute_path, **kwargs))
    check(class_(guess=absolute_filename, **kwargs))
    check(class_(filename=absolute_path, **kwargs))
    check(class_(filename=absolute_filename, **kwargs))
    check(class_(url, **kwargs))
    check(class_(guess=url, **kwargs))
    url = path2url(absolute_filename.encode())
    check(class_(url=url, **kwargs))
    with absolute_path.open('rb') as fd:
        check(class_(fd, **kwargs))
    with absolute_path.open('rb') as fd:
        check(class_(guess=fd, **kwargs))
    with absolute_path.open('rb') as fd:
        check(class_(file_obj=fd, **kwargs))
    content = absolute_path.read_bytes()
    with chdir(Path(__file__).parent):
        relative_path = Path('resources') / name
        relative_filename = str(relative_path)
        check(class_(relative_path, **kwargs))
        check(class_(relative_filename, **kwargs))
        kwargs.pop('base_url', None)
        check(class_(string=content, base_url=relative_filename, **kwargs))
        encoding = kwargs.pop('encoding', 'utf-8')
        with absolute_path.open('r', encoding=encoding) as fd:
            check(class_(file_obj=fd, **kwargs))
        check(class_(
            string=content.decode(encoding), base_url=relative_filename,
            **kwargs))
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
        assert url.endswith('tests/resources/pattern.png')
    else:
        assert html.base_url is None


def _run(args, stdin=b''):
    stdin = io.BytesIO(stdin)
    stdout = io.BytesIO()
    HTML = partial(FakeHTML, force_uncompressed_pdf=False)  # noqa: N806
    __main__.main(args.split(), stdin=stdin, stdout=stdout, HTML=HTML)
    return stdout.getvalue()


class FakeFile:
    def __init__(self):
        self.chunks = []

    def write(self, data):
        self.chunks.append(bytes(data[:]))

    def getvalue(self):
        return b''.join(self.chunks)


def _png_size(png_bytes):
    image = Image.open(io.BytesIO(png_bytes))
    return image.width, image.height


def _round_meta(pages):
    """Eliminate errors of floating point arithmetic for metadata."""
    for page in pages:
        anchors = page.anchors
        for anchor_name, (pos_x, pos_y) in anchors.items():
            anchors[anchor_name] = round(pos_x, 6), round(pos_y, 6)
        links = page.links
        for i, link in enumerate(links):
            link_type, target, rectangle, box = link
            pos_x, pos_y, width, height = rectangle
            link = (
                link_type, target,
                (round(pos_x, 6), round(pos_y, 6),
                 round(width, 6), round(height, 6)),
                box)
            links[i] = link
        bookmarks = page.bookmarks
        for i, (level, label, (pos_x, pos_y), state) in enumerate(bookmarks):
            bookmarks[i] = (
                level, label, (round(pos_x, 6), round(pos_y, 6)), state)


@assert_no_logs
def test_html_parsing():
    """Test the constructor for the HTML class."""
    _test_resource(FakeHTML, 'doc1.html', _check_doc1)
    _test_resource(
        FakeHTML, 'doc1_UTF-16BE.html', _check_doc1, encoding='UTF-16BE')

    with chdir(Path(__file__).parent):
        path = Path('resources') / 'doc1.html'
        string = path.read_text('utf-8')
        _test_resource(FakeHTML, 'doc1.html', _check_doc1, base_url=path)
        _check_doc1(FakeHTML(string=string, base_url=path))
        _check_doc1(FakeHTML(string=string), has_base_url=False)
        string_with_base = string.replace(
            '<meta', '<base href="resources/"><meta')
        _check_doc1(FakeHTML(string=string_with_base, base_url='.'))
        string_with_no_base = string.replace('<meta', '<base><meta')
        _check_doc1(FakeHTML(string=string_with_no_base), has_base_url=False)


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
        assert h1_rule[4][1][1][0][1].endswith('tests/resources/pattern.png')

    _test_resource(CSS, 'utf8-test.css', check_css)
    _test_resource(CSS, 'latin1-test.css', check_css, encoding='latin1')


def check_png_pattern(assert_pixels_equal, png_bytes, x2=False, blank=False,
                      rotated=False):
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
    image = Image.open(io.BytesIO(png_bytes))
    width, height, pixels = parse_pixels(expected_pixels)
    assert_pixels_equal(width, height, image.getdata(), pixels)


@assert_no_logs
def test_python_render(assert_pixels_equal, tmp_path):
    """Test rendering with the Python API."""
    base_url = str(resource_path('dummy.html'))
    html_string = '<body><img src=pattern.png>'
    css_string = '''
        @page { margin: 2px; size: 8px }
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
    check_png_pattern(assert_pixels_equal, png_bytes)

    png_file = FakeFile()
    html.write_png(png_file, stylesheets=[css])
    assert png_file.getvalue() == png_bytes
    pdf_file = FakeFile()
    html.write_pdf(pdf_file, stylesheets=[css])
    assert pdf_file.getvalue().startswith(b'%PDF')

    png_path = tmp_path / '1.png'
    pdf_path = tmp_path / '1.pdf'
    html.write_png(png_path, stylesheets=[css])
    html.write_pdf(pdf_path, stylesheets=[css])
    assert png_path.read_bytes() == png_bytes
    assert pdf_path.read_bytes().startswith(b'%PDF')

    png_path = tmp_path / '2.png'
    pdf_path = tmp_path / '2.pdf'
    with png_path.open('wb') as png_fd:
        html.write_png(png_fd, stylesheets=[css])
    with pdf_path.open('wb') as pdf_fd:
        html.write_pdf(pdf_fd, stylesheets=[css])
    assert png_path.read_bytes() == png_bytes
    assert pdf_path.read_bytes().startswith(b'%PDF')

    x2_png_bytes = html.write_png(stylesheets=[css], resolution=192)
    check_png_pattern(assert_pixels_equal, x2_png_bytes, x2=True)

    screen_css = CSS(string=css_string, media_type='screen')
    rotated_png_bytes = html.write_png(stylesheets=[screen_css])
    check_png_pattern(assert_pixels_equal, rotated_png_bytes, rotated=True)

    assert FakeHTML(
        string=html_string, base_url=base_url, media_type='screen'
    ).write_png(
        stylesheets=[io.BytesIO(css_string.encode())]
    ) == rotated_png_bytes
    assert FakeHTML(
        string=f'<style>{css_string}</style>{html_string}',
        base_url=base_url, media_type='screen'
    ).write_png() == rotated_png_bytes


@assert_no_logs
def test_command_line_render(tmp_path):
    css = b'''
        @page { margin: 2px; size: 8px }
        @media screen { img { transform: rotate(-90deg) } }
        body { margin: 0; font-size: 0 }
    '''
    html = b'<body><img src=pattern.png>'
    combined = b'<style>' + css + b'</style>' + html
    linked = b'<link rel=stylesheet href=style.css>' + html
    not_optimized = b'<body>a<img src="not-optimized.jpg">'

    for name in ('pattern.png', 'not-optimized.jpg'):
        pattern_bytes = resource_path(name).read_bytes()
        (tmp_path / name).write_bytes(pattern_bytes)

    with chdir(tmp_path):
        # Reference
        html_obj = FakeHTML(
            string=combined, base_url='dummy.html',
            force_uncompressed_pdf=False)
        pdf_bytes = html_obj.write_pdf()
        rotated_pdf_bytes = FakeHTML(
            string=combined, base_url='dummy.html',
            media_type='screen', force_uncompressed_pdf=False).write_pdf()

        (tmp_path / 'no_css.html').write_bytes(html)
        (tmp_path / 'combined.html').write_bytes(combined)
        (tmp_path / 'combined-UTF-16BE.html').write_bytes(
            combined.decode().encode('UTF-16BE'))
        (tmp_path / 'linked.html').write_bytes(linked)
        (tmp_path / 'not_optimized.html').write_bytes(not_optimized)
        (tmp_path / 'style.css').write_bytes(css)

        _run('combined.html out2.pdf')
        assert (tmp_path / 'out2.pdf').read_bytes() == pdf_bytes

        _run('combined-UTF-16BE.html out3.pdf --encoding UTF-16BE')
        assert (tmp_path / 'out3.pdf').read_bytes() == pdf_bytes

        _run(f'{(tmp_path / "combined.html")} out4.pdf')
        assert (tmp_path / 'out4.pdf').read_bytes() == pdf_bytes

        _run(f'{path2url((tmp_path / "combined.html"))} out5.pdf')
        assert (tmp_path / 'out5.pdf').read_bytes() == pdf_bytes

        _run('linked.html --debug out6.pdf')  # test relative URLs
        assert (tmp_path / 'out6.pdf').read_bytes() == pdf_bytes

        _run('combined.html --verbose out7')
        _run('combined.html --quiet out8')
        assert (tmp_path / 'out7').read_bytes() == pdf_bytes
        assert (tmp_path / 'out8').read_bytes() == pdf_bytes

        _run('no_css.html out9.pdf')
        _run('no_css.html out10.pdf -s style.css')
        assert (tmp_path / 'out9.pdf').read_bytes() != pdf_bytes
        assert (tmp_path / 'out10.pdf').read_bytes() == pdf_bytes

        stdout = _run('combined.html -')
        assert stdout == pdf_bytes

        _run('- out11.pdf', stdin=combined)
        assert (tmp_path / 'out11.pdf').read_bytes() == pdf_bytes

        stdout = _run('- -', stdin=combined)
        assert stdout == pdf_bytes

        _run('combined.html out13.pdf --media-type screen')
        _run('combined.html out12.pdf -m screen')
        _run('linked.html out14.pdf -m screen')
        assert (tmp_path / 'out12.pdf').read_bytes() == rotated_pdf_bytes
        assert (tmp_path / 'out13.pdf').read_bytes() == rotated_pdf_bytes
        assert (tmp_path / 'out14.pdf').read_bytes() == rotated_pdf_bytes

        os.environ['SOURCE_DATE_EPOCH'] = '0'
        _run('not_optimized.html out15.pdf')
        _run('not_optimized.html out16.pdf --optimize-images')
        _run('not_optimized.html out17.pdf --optimize-images -j 10')
        _run('not_optimized.html out18.pdf --optimize-images -j 10 -D 1')
        _run('not_optimized.html out19.pdf --hinting')
        _run('not_optimized.html out20.pdf --full-fonts')
        _run('not_optimized.html out21.pdf --full-fonts --uncompressed-pdf')
        _run(f'not_optimized.html out22.pdf -c {tmp_path}')
        assert (
            len((tmp_path / 'out18.pdf').read_bytes()) <
            len((tmp_path / 'out17.pdf').read_bytes()) <
            len((tmp_path / 'out16.pdf').read_bytes()) <
            len((tmp_path / 'out15.pdf').read_bytes()) <
            len((tmp_path / 'out19.pdf').read_bytes()) <
            len((tmp_path / 'out20.pdf').read_bytes()) <
            len((tmp_path / 'out21.pdf').read_bytes()))
        assert len({
            (tmp_path / f'out{i}.pdf').read_bytes()
            for i in (15, 22)}) == 1
        os.environ.pop('SOURCE_DATE_EPOCH')

        stdout = _run('combined.html --uncompressed-pdf -')
        assert stdout.count(b'attachment') == 0
        stdout = _run('combined.html --uncompressed-pdf -')
        assert stdout.count(b'attachment') == 0
        stdout = _run('-a pattern.png --uncompressed-pdf combined.html -')
        assert stdout.count(b'attachment') == 1
        stdout = _run(
            '-a style.css -a pattern.png --uncompressed-pdf combined.html -')
        assert stdout.count(b'attachment') == 2

        _run('combined.html out23.pdf --timeout 30')
        assert (tmp_path / 'out23.pdf').read_bytes() == pdf_bytes

    subdirectory = tmp_path / 'subdirectory'
    subdirectory.mkdir()
    with chdir(subdirectory):
        with capture_logs() as logs:
            stdout = _run('- -', stdin=combined)
        assert len(logs) == 1
        assert logs[0].startswith('ERROR: Failed to load image')
        assert stdout.startswith(b'%PDF')

        with capture_logs() as logs:
            stdout = _run('--base-url= - -', stdin=combined)
        assert len(logs) == 1
        assert logs[0].startswith(
            'ERROR: Relative URI reference without a base URI')
        assert stdout.startswith(b'%PDF')

        stdout = _run('--base-url .. - -', stdin=combined)
        assert stdout == pdf_bytes

    with pytest.raises(SystemExit):
        _run('--info')

    with pytest.raises(SystemExit):
        _run('--version')


@pytest.mark.parametrize('version, pdf_version', (
    (1, '1.4'),
    (2, '1.7'),
    (3, '1.7'),
    (4, '2.0'),
))
def test_pdfa(version, pdf_version):
    stdout = _run(
        f'--pdf-variant=pdf/a-{version}b --uncompressed-pdf - -', b'test')
    assert f'PDF-{pdf_version}'.encode() in stdout
    assert f'part="{version}"'.encode() in stdout


@pytest.mark.parametrize('version, pdf_version', (
    (1, '1.4'),
    (2, '1.7'),
    (3, '1.7'),
    (4, '2.0'),
))
def test_pdfa_compressed(version, pdf_version):
    _run(f'--pdf-variant=pdf/a-{version}b - -', b'test')


def test_pdfa1b_cidset():
    stdout = _run('--pdf-variant=pdf/a-1b --uncompressed-pdf - -', b'test')
    assert b'PDF-1.4' in stdout
    assert b'CIDSet' in stdout


def test_pdfua():
    stdout = _run('--pdf-variant=pdf/ua-1 --uncompressed-pdf - -', b'test')
    assert b'part="1"' in stdout


def test_pdfua_compressed():
    _run('--pdf-variant=pdf/ua-1 - -', b'test')


def test_pdf_identifier():
    stdout = _run('--pdf-identifier=abc --uncompressed-pdf - -', b'test')
    assert b'abc' in stdout


def test_pdf_version():
    stdout = _run('--pdf-version=1.4 --uncompressed-pdf - -', b'test')
    assert b'PDF-1.4' in stdout


def test_pdf_custom_metadata():
    stdout = _run(
        '--custom-metadata --uncompressed-pdf - -',
        b'<meta name=key content=value />')
    assert b'/key' in stdout
    assert b'value' in stdout


def test_bad_pdf_custom_metadata():
    stdout = _run(
        '--custom-metadata --uncompressed-pdf - -',
        '<meta name=é content=value />'.encode('latin1'))
    assert b'value' not in stdout


def test_partial_pdf_custom_metadata():
    stdout = _run(
        '--custom-metadata --uncompressed-pdf - -',
        '<meta name=a.b/céd0 content=value />'.encode('latin1'))
    assert b'/abcd0' in stdout
    assert b'value' in stdout


@pytest.mark.parametrize('html, fields', (
    ('<input>', ['/Tx', '/V ()']),
    ('<input value="">', ['/Tx', '/V ()']),
    ('<input type="checkbox">', ['/Btn']),
    ('<textarea></textarea>', ['/Tx', '/V ()']),
    ('<select><option value="a">A</option></select>', ['/Ch', '/Opt']),
    ('<select>'
     '<option value="a">A</option>'
     '<option value="b" selected>B</option>'
     '</select>', ['/Ch', '/Opt', '/V (b)']),
    ('<select multiple>'
     '<option value="a">A</option>'
     '<option value="b" selected>B</option>'
     '<option value="c" selected>C</option>'
     '</select>', ['/Ch', '/Opt', '[(b) (c)]']),
))
def test_pdf_inputs(html, fields):
    stdout = _run('--pdf-forms --uncompressed-pdf - -', html.encode())
    assert b'AcroForm' in stdout
    assert all(field.encode() in stdout for field in fields)
    stdout = _run('--uncompressed-pdf - -', html.encode())
    assert b'AcroForm' not in stdout


@pytest.mark.parametrize('css, with_forms, without_forms', (
    ('appearance: auto', True, True),
    ('appearance: none', False, False),
    ('', True, False),
))
def test_appearance(css, with_forms, without_forms):
    html = f'<input style="{css}">'.encode()
    assert with_forms is (
        b'AcroForm' in _run('--pdf-forms --uncompressed-pdf - -', html))
    assert without_forms is (
        b'AcroForm' in _run(' --uncompressed-pdf - -', html))


def test_appearance_non_input():
    html = '<div style="appearance: auto">'.encode()
    assert b'AcroForm' not in _run('--pdf-forms --uncompressed-pdf - -', html)


def test_reproducible():
    os.environ['SOURCE_DATE_EPOCH'] = '0'
    stdout1 = _run('- -', b'<body>a<img src=pattern.png>')
    stdout2 = _run('- -', b'<body>a<img src=pattern.png>')
    os.environ.pop('SOURCE_DATE_EPOCH')
    assert stdout1 == stdout2


@assert_no_logs
def test_unicode_filenames(assert_pixels_equal, tmp_path):
    """Test non-ASCII filenames both in Unicode or bytes form."""
    # Replicate pattern.png in CSS so that base_url does not matter.
    html = b'''
        <style>
            @page { margin: 2px; size: 8px }
            html { background: #00f; }
            body { background: #f00; width: 1px; height: 1px }
        </style>
        <body>
    '''
    png_bytes = FakeHTML(string=html).write_png()
    check_png_pattern(assert_pixels_equal, png_bytes)
    unicode_filename = 'Unicödé'
    if sys.platform.startswith('darwin'):  # pragma: no cover
        unicode_filename = unicodedata.normalize('NFD', unicode_filename)

    with chdir(tmp_path):
        (tmp_path / unicode_filename).write_bytes(html)
        bytes_file, = tuple(tmp_path.iterdir())
        assert bytes_file.name == unicode_filename

        assert FakeHTML(unicode_filename).write_png() == png_bytes
        assert FakeHTML(bytes_file).write_png() == png_bytes

        os.remove(unicode_filename)
        assert not tuple(tmp_path.iterdir())

        FakeHTML(string=html).write_png(unicode_filename)
        assert bytes_file.read_bytes() == png_bytes


@assert_no_logs
def test_low_level_api(assert_pixels_equal):
    html = FakeHTML(string='<body>')
    css = CSS(string='''
        @page { margin: 2px; size: 8px }
        html { background: #00f; }
        body { background: #f00; width: 1px; height: 1px }
    ''')
    pdf_bytes = html.write_pdf(stylesheets=[css])
    assert pdf_bytes.startswith(b'%PDF')

    png_bytes = html.write_png(stylesheets=[css])
    document = html.render(stylesheets=[css])
    page, = document.pages
    assert page.width == 8
    assert page.height == 8
    assert document.write_png() == png_bytes
    assert document.copy([page]).write_png() == png_bytes

    document = html.render(stylesheets=[css])
    page, = document.pages
    assert (page.width, page.height) == (8, 8)
    png_bytes = document.write_png(resolution=192)
    check_png_pattern(assert_pixels_equal, png_bytes, x2=True)

    document = html.render(stylesheets=[css])
    page, = document.pages
    assert (page.width, page.height) == (8, 8)
    # A resolution that is not multiple of 96:
    assert _png_size(document.write_png(resolution=145.2)) == (12, 12)

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
        <style>h1, h2, h3, h4 { height: 10px }</style>
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
            h1, h2, h3, span { height: 90px; margin: 0 0 10px 0 }
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
    ''' % path2url(resource_path('pattern.png')),
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
    ('''
        <body>
        <h1 style="width: 10px; line-height: 10px;
                   transform: skew(45deg, 45deg)">!
    ''', [[(1, '!', (-5, -5), 'open')]], [('!', (0, -5, -5), [], 'open')],
     True),
))
@assert_no_logs
def test_assert_bookmarks(html, expected_by_page, expected_tree, round):
    document = FakeHTML(string=html).render()
    if round:
        _round_meta(document.pages)
    assert [page.bookmarks for page in document.pages] == expected_by_page
    assert document.make_bookmark_tree() == expected_tree


def simplify_links(links):
    return [
        (link_type, link_target, rectangle)
        for link_type, link_target, rectangle, box in links]


def assert_links(html, links, anchors, resolved_links,
                 base_url=resource_path('<inline HTML>'), warnings=(),
                 round=False):
    with capture_logs() as logs:
        document = FakeHTML(string=html, base_url=base_url).render()
        if round:
            _round_meta(document.pages)
        document_resolved_links = [
            (simplify_links(page_links), page_anchors)
            for page_links, page_anchors in resolve_links(document.pages)]
    assert len(logs) == len(warnings)
    for message, expected in zip(logs, warnings):
        assert expected in message
    document_links = [simplify_links(page.links) for page in document.pages]
    document_anchors = [page.anchors for page in document.pages]
    assert document_links == links
    assert document_anchors == anchors
    assert document_resolved_links == resolved_links


@assert_no_logs
def test_links_1():
    assert_links('''
        <style>
            body { font-size: 10px; line-height: 2; width: 200px }
            p { height: 90px; margin: 0 0 10px 0 }
            img { width: 30px; vertical-align: top }
        </style>
        <p><a href="https://weasyprint.org"><img src=pattern.png></a></p>
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
            ('external', 'https://weasyprint.org', (0, 0, 30, 20)),
            ('external', 'https://weasyprint.org', (0, 0, 30, 30)),
            ('internal', 'lipsum', (10, 100, 42, 120)),
            ('internal', 'lipsum', (10, 100, 42, 132))
        ],
        [('internal', 'hello', (0, 0, 200, 30))],
    ], [
        {'hello': (0, 200)},
        {'lipsum': (0, 0)}
    ], [
        (
            [
                ('external', 'https://weasyprint.org', (0, 0, 30, 20)),
                ('external', 'https://weasyprint.org', (0, 0, 30, 30)),
                ('internal', 'lipsum', (10, 100, 42, 120)),
                ('internal', 'lipsum', (10, 100, 42, 132))
            ],
            [('hello', 0, 200)],
        ),
        (
            [('internal', 'hello', (0, 0, 200, 30))],
            [('lipsum', 0, 0)]),
    ])


@assert_no_logs
def test_links_2():
    assert_links(
        '''
            <body style="width: 200px">
            <a href="../lipsum/é_%E9" style="display: block; margin: 10px 5px">
        ''', [[('external', 'https://weasyprint.org/foo/lipsum/%C3%A9_%E9',
                (5, 10, 195, 10))]],
        [{}], [([('external', 'https://weasyprint.org/foo/lipsum/%C3%A9_%E9',
                  (5, 10, 195, 10))], [])],
        base_url='https://weasyprint.org/foo/bar/')


@assert_no_logs
def test_links_3():
    assert_links(
        '''
            <body style="width: 200px">
            <div style="display: block; margin: 10px 5px;
                        -weasy-link: url(../lipsum/é_%E9)">
        ''', [[('external', 'https://weasyprint.org/foo/lipsum/%C3%A9_%E9',
                (5, 10, 195, 10))]],
        [{}], [([('external', 'https://weasyprint.org/foo/lipsum/%C3%A9_%E9',
                  (5, 10, 195, 10))], [])],
        base_url='https://weasyprint.org/foo/bar/')


@assert_no_logs
def test_links_4():
    # Relative URI reference without a base URI: allowed for links
    assert_links(
        '''
            <body style="width: 200px">
            <a href="../lipsum" style="display: block; margin: 10px 5px">
        ''', [[('external', '../lipsum', (5, 10, 195, 10))]], [{}],
        [([('external', '../lipsum', (5, 10, 195, 10))], [])],
        base_url=None)


@assert_no_logs
def test_links_5():
    # Relative URI reference without a base URI: not supported for -weasy-link
    assert_links(
        '''
            <body style="width: 200px">
            <div style="-weasy-link: url(../lipsum);
                        display: block; margin: 10px 5px">
        ''', [[]], [{}], [([], [])], base_url=None, warnings=[
            'WARNING: Ignored `-weasy-link: url(../lipsum)` at 1:1, '
            'Relative URI reference without a base URI'])


@assert_no_logs
def test_links_6():
    # Internal or absolute URI reference without a base URI: OK
    assert_links(
        '''
            <body style="width: 200px">
            <a href="#lipsum" id="lipsum"
                style="display: block; margin: 10px 5px"></a>
            <a href="https://weasyprint.org/" style="display: block"></a>
        ''', [[
            ('internal', 'lipsum', (5, 10, 195, 10)),
            ('external', 'https://weasyprint.org/', (0, 10, 200, 10))]],
        [{'lipsum': (5, 10)}],
        [([('internal', 'lipsum', (5, 10, 195, 10)),
           ('external', 'https://weasyprint.org/', (0, 10, 200, 10))],
          [('lipsum', 5, 10)])],
        base_url=None)


@assert_no_logs
def test_links_7():
    assert_links(
        '''
            <body style="width: 200px">
            <div style="-weasy-link: url(#lipsum);
                        margin: 10px 5px" id="lipsum">
        ''',
        [[('internal', 'lipsum', (5, 10, 195, 10))]],
        [{'lipsum': (5, 10)}],
        [([('internal', 'lipsum', (5, 10, 195, 10))], [('lipsum', 5, 10)])],
        base_url=None)


@assert_no_logs
def test_links_8():
    assert_links(
        '''
            <style> a { display: block; height: 15px } </style>
            <body style="width: 200px">
                <a href="#lipsum"></a>
                <a href="#missing" id="lipsum"></a>
        ''',
        [[('internal', 'lipsum', (0, 0, 200, 15)),
          ('internal', 'missing', (0, 15, 200, 30))]],
        [{'lipsum': (0, 15)}],
        [([('internal', 'lipsum', (0, 0, 200, 15))], [('lipsum', 0, 15)])],
        base_url=None,
        warnings=[
            'ERROR: No anchor #missing for internal URI reference'])


@assert_no_logs
def test_links_9():
    assert_links(
        '''
            <body style="width: 100px; transform: translateY(100px)">
            <a href="#lipsum" id="lipsum" style="display: block; height: 20px;
                transform: rotate(90deg) scale(2)">
        ''',
        [[('internal', 'lipsum', (30, 10, 70, 210))]],
        [{'lipsum': (70, 10)}],
        [([('internal', 'lipsum', (30, 10, 70, 210))], [('lipsum', 70, 10)])],
        round=True)


@assert_no_logs
def test_links_10():
    # Download for attachment
    assert_links(
        '''
            <body style="width: 200px">
            <a rel=attachment href="pattern.png" download="wow.png"
                style="display: block; margin: 10px 5px">
        ''', [[('attachment', 'pattern.png', (5, 10, 195, 10))]],
        [{}], [([('attachment', 'pattern.png', (5, 10, 195, 10))], [])],
        base_url=None)


@assert_no_logs
def test_links_11():
    # Attachment with missing href
    assert_links(
        '''
            <body style="width: 200px">
            <a rel=attachment download="wow.png"
                style="display: block; margin: 10px 5px">
        ''', [[]], [{}], [([], [])], base_url=None)


@assert_no_logs
def test_links_12():
    # Absolute URI with no fragment and the same base URI: keep external URI
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/1767
    assert_links(
        '''
            <body style="width: 200px">
            <a href="https://weasyprint.org"
               style="display: block; margin: 10px 5px">
        ''',
        [[('external', 'https://weasyprint.org', (5, 10, 195, 10))]], [{}],
        [([('external', 'https://weasyprint.org', (5, 10, 195, 10))], [])],
        base_url='https://weasyprint.org')


# Make relative URL references work with our custom URL scheme.
uses_relative.append('weasyprint-custom')


@assert_no_logs
def test_url_fetcher(assert_pixels_equal):
    path = resource_path('pattern.png')
    pattern_png = path.read_bytes()

    def fetcher(url):
        if url == 'weasyprint-custom:foo/%C3%A9_%e9_pattern':
            return {'string': pattern_png, 'mime_type': 'image/png'}
        elif url == 'weasyprint-custom:foo/bar.css':
            return {
                'string': 'body { background: url(é_%e9_pattern)',
                'mime_type': 'text/css'}
        elif url == 'weasyprint-custom:foo/bar.no':
            return {
                'string': 'body { background: red }',
                'mime_type': 'text/no'}
        else:
            return default_url_fetcher(url)

    base_url = str(resource_path('dummy.html'))
    css = CSS(string='''
        @page { size: 8px; margin: 2px }
        body { margin: 0; font-size: 0 }
    ''', base_url=base_url)

    def test(html, blank=False):
        html = FakeHTML(string=html, url_fetcher=fetcher, base_url=base_url)
        check_png_pattern(
            assert_pixels_equal, html.write_png(stylesheets=[css]),
            blank=blank)

    test('<body><img src="pattern.png">')  # Test a "normal" URL
    test(f'<body><img src="{path.as_uri()}">')
    test(f'<body><img src="{path.as_uri()}?ignored">')
    test('<body><img src="weasyprint-custom:foo/é_%e9_pattern">')
    test('<body style="background: url(weasyprint-custom:foo/é_%e9_pattern)">')
    test('<body><li style="list-style: inside '
         'url(weasyprint-custom:foo/é_%e9_pattern)">')
    test('<link rel=stylesheet href="weasyprint-custom:foo/bar.css"><body>')
    test('<style>@import "weasyprint-custom:foo/bar.css";</style><body>')
    test('<style>@import url(weasyprint-custom:foo/bar.css);</style><body>')
    test('<style>@import url("weasyprint-custom:foo/bar.css");</style><body>')
    test('<link rel=stylesheet href="weasyprint-custom:foo/bar.css"><body>')

    with capture_logs() as logs:
        test('<body><img src="custom:foo/bar">', blank=True)
    assert len(logs) == 1
    assert logs[0].startswith(
        "ERROR: Failed to load image at 'custom:foo/bar'")

    with capture_logs() as logs:
        test(
            '<link rel=stylesheet href="weasyprint-custom:foo/bar.css">'
            '<link rel=stylesheet href="weasyprint-custom:foo/bar.no"><body>')
    assert len(logs) == 1
    assert logs[0].startswith('ERROR: Unsupported stylesheet type text/no')

    def fetcher_2(url):
        assert url == 'weasyprint-custom:%C3%A9_%e9.css'
        return {'string': '', 'mime_type': 'text/css'}
    FakeHTML(
        string='<link rel=stylesheet href="weasyprint-custom:é_%e9.css"><body',
        url_fetcher=fetcher_2).render()


def assert_meta(html, **meta):
    meta.setdefault('title', None)
    meta.setdefault('authors', [])
    meta.setdefault('keywords', [])
    meta.setdefault('generator', None)
    meta.setdefault('description', None)
    meta.setdefault('created', None)
    meta.setdefault('modified', None)
    meta.setdefault('attachments', [])
    meta.setdefault('lang', None)
    meta.setdefault('custom', {})
    assert vars(FakeHTML(string=html).render().metadata) == meta


@assert_no_logs
def test_html_meta_1():
    assert_meta('<body>')


@assert_no_logs
def test_html_meta_2():
    assert_meta(
        '''
            <html lang="en"><head>
            <meta name=author content="I Me &amp; Myself">
            <meta name=author content="Smith, John">
            <title>Test document</title>
            <h1>Another title</h1>
            <meta name=generator content="Human after all">
            <meta name=generator content="Human">
            <meta name=dummy content=ignored>
            <meta name=dummy>
            <meta content=ignored>
            <meta>
            <meta name=keywords content="html ,\tcss,
                                         pdf,css">
            <meta name=dcterms.created content=2011-04>
            <meta name=dcterms.created content=2011-05>
            <meta name=dcterms.modified content=2013>
            <meta name=keywords content="Python; pydyf">
            <meta name=description content="Blah… ">
            <meta name=description content="*Oh-no/">
            <meta name=dcterms.modified content=2012>
            </head></html>
        ''',
        authors=['I Me & Myself', 'Smith, John'],
        title='Test document',
        generator='Human after all',
        keywords=['html', 'css', 'pdf', 'Python; pydyf'],
        description="Blah… ",
        created='2011-04',
        modified='2013',
        lang='en',
        custom={'dummy': 'ignored'})


@assert_no_logs
def test_html_meta_3():
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
def test_html_meta_4():
    with capture_logs() as logs:
        assert_meta(
            '''
                <meta name=dcterms.created content=wrong>
                <meta name=author content=Me>
                <title>Title</title>
            ''',
            title='Title',
            authors=['Me'])
    assert len(logs) == 1
    assert 'Invalid date' in logs[0]


@assert_no_logs
def test_http():
    def gzip_compress(data):
        file_obj = io.BytesIO()
        gzip_file = gzip.GzipFile(fileobj=file_obj, mode='wb')
        gzip_file.write(data)
        gzip_file.close()
        return file_obj.getvalue()

    @contextlib.contextmanager
    def http_server(handlers):
        def wsgi_app(environ, start_response):
            handler = handlers.get(environ['PATH_INFO'])
            if handler:
                status = str('200 OK')
                response, headers = handler(environ)
                headers = [(str(name), str(value)) for name, value in headers]
            else:  # pragma: no cover
                status = str('404 Not Found')
                response = b''
                headers = []
            start_response(status, headers)
            return [response]

        # Port 0: let the OS pick an available port number
        # https://stackoverflow.com/a/1365284/1162888
        server = wsgiref.simple_server.make_server('127.0.0.1', 0, wsgi_app)
        _host, port = server.socket.getsockname()
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            yield f'http://127.0.0.1:{port}'
        finally:
            server.shutdown()
            thread.join()

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
        assert HTML(f'{root_url}/gzip').etree_element.get('test') == 'ok'
        assert HTML(f'{root_url}/deflate').etree_element.get('test') == 'ok'
        assert HTML(
            f'{root_url}/raw-deflate').etree_element.get('test') == 'ok'


@assert_no_logs
def test_page_copy_relative():
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/1473
    document = FakeHTML(string='<div style="position: relative">a').render()
    duplicated_pages = document.copy([*document.pages, *document.pages])
    pngs = duplicated_pages.write_png(split_images=True)
    assert pngs[0] == pngs[1]
