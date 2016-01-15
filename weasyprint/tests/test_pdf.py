# coding: utf-8
"""
    weasyprint.tests.test_pdf
    -------------------------

    Test PDF-related code, including metadata, bookmarks and hyperlinks.

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import hashlib
import io
import os

import cairocffi
import pytest

from .. import CSS, Attachment
from .. import pdf
from ..images import CAIRO_HAS_MIME_DATA
from ..urls import path2url
from .testing_utils import (
    assert_no_logs, resource_filename, TestHTML, capture_logs, temp_directory)


@assert_no_logs
def test_pdf_parser():
    fileobj = io.BytesIO()
    surface = cairocffi.PDFSurface(fileobj, 1, 1)
    for width, height in [
        (100, 100),
        (200, 10),
        (3.14, 987654321)
    ]:
        surface.set_size(width, height)
        surface.show_page()
    surface.finish()

    sizes = [page.get_value('MediaBox', '\[(.+?)\]').strip()
             for page in pdf.PDFFile(fileobj).pages]
    assert sizes == [b'0 0 100 100', b'0 0 200 10', b'0 0 3.14 987654321']


@assert_no_logs
def test_page_size():
    pdf_bytes = TestHTML(string='<style>@page{size:3in 4in').write_pdf()
    assert b'/MediaBox [ 0 0 216 288 ]' in pdf_bytes

    pdf_bytes = TestHTML(string='<style>@page{size:3in 4in').write_pdf(
        zoom=1.5)
    assert b'/MediaBox [ 0 0 324 432 ]' in pdf_bytes


def get_metadata(html, base_url=resource_filename('<inline HTML>'), zoom=1):
    return pdf.prepare_metadata(
        TestHTML(string=html, base_url=base_url).render(stylesheets=[
            CSS(string='@page { size: 500pt 1000pt; margin: 50pt }')]),
        bookmark_root_id=0, scale=zoom * 0.75)


def get_bookmarks(html, structure_only=False, **kwargs):
    root, bookmarks, _links = get_metadata(html, **kwargs)
    for bookmark in bookmarks:
        if structure_only:
            bookmark.pop('target')
            bookmark.pop('label')
        else:
            # Eliminate errors of floating point arithmetic
            # (eg. 499.99999999999994 instead of 500)
            p, x, y = bookmark['target']
            bookmark['target'] = p, round(x, 6), round(y, 6)
    return root, bookmarks


def get_links(html, **kwargs):
    _root, _bookmarks, links = get_metadata(html, **kwargs)
    for page_links in links:
        for i, (link_type, target, rectangle) in enumerate(page_links):
            if link_type == 'internal':
                page, x, y = target
                target = page, round(x, 6), round(y, 6)
            rectangle = tuple(round(v, 6) for v in rectangle)
            page_links[i] = link_type, target, rectangle
    return links


@assert_no_logs
def test_bookmarks():
    """Test the structure of the document bookmarks.

    Warning: the PDF output of this structure is not tested.

    """
    root, bookmarks = get_bookmarks('''
        <h1>a</h1>  #
        <h4>b</h4>  ####
        <h3>c</h3>  ###
        <h2>d</h2>  ##
        <h1>e</h1>  #
    ''', structure_only=True)
    assert root == dict(Count=5, First=1, Last=5)
    assert bookmarks == [
        dict(Count=3, First=2, Last=4, Next=5, Parent=0, Prev=None),
        dict(Count=0, First=None, Last=None, Next=3, Parent=1, Prev=None),
        dict(Count=0, First=None, Last=None, Next=4, Parent=1, Prev=2),
        dict(Count=0, First=None, Last=None, Next=None, Parent=1, Prev=3),
        dict(Count=0, First=None, Last=None, Next=None, Parent=0, Prev=1)]

    root, bookmarks = get_bookmarks('<body>')
    assert root == dict(Count=0)
    assert bookmarks == []

    root, bookmarks = get_bookmarks('''
        <style>
            * { height: 90pt; margin: 0 0 10pt 0 }
        </style>
        <h1>Title 1</h1>
        <h1>Title 2</h1>
        <h2 style="position: relative; left: 20pt">Title 3</h2>
        <h2>Title 4</h2>
        <h3>Title 5</h3>
        <span style="display: block; page-break-before: always"></span>
        <h2>Title 6</h2>
        <h1>Title 7</h1>
        <h2>Title 8</h2>
        <h3>Title 9</h3>
        <h1>Title 10</h1>
        <h2>Title 11</h2>
    ''')
    assert root == dict(Count=11, First=1, Last=10)
    assert bookmarks == [
        dict(Count=0, First=None, Last=None, Next=2, Parent=0, Prev=None,
             label='Title 1', target=(0, 50, 950)),
        dict(Count=4, First=3, Last=6, Next=7, Parent=0, Prev=1,
             label='Title 2', target=(0, 50, 850)),
        dict(Count=0, First=None, Last=None, Next=4, Parent=2, Prev=None,
             label='Title 3', target=(0, 70, 750)),
        dict(Count=1, First=5, Last=5, Next=6, Parent=2, Prev=3,
             label='Title 4', target=(0, 50, 650)),
        dict(Count=0, First=None, Last=None, Next=None, Parent=4, Prev=None,
             label='Title 5', target=(0, 50, 550)),
        dict(Count=0, First=None, Last=None, Next=None, Parent=2, Prev=4,
             label='Title 6', target=(1, 50, 850)),
        dict(Count=2, First=8, Last=8, Next=10, Parent=0, Prev=2,
             label='Title 7', target=(1, 50, 750)),
        dict(Count=1, First=9, Last=9, Next=None, Parent=7, Prev=None,
             label='Title 8', target=(1, 50, 650)),
        dict(Count=0, First=None, Last=None, Next=None, Parent=8, Prev=None,
             label='Title 9', target=(1, 50, 550)),
        dict(Count=1, First=11, Last=11, Next=None, Parent=0, Prev=7,
             label='Title 10', target=(1, 50, 450)),
        dict(Count=0, First=None, Last=None, Next=None, Parent=10, Prev=None,
             label='Title 11', target=(1, 50, 350))]

    root, bookmarks = get_bookmarks('''
        <h2>1</h2> level 1
        <h4>2</h4> level 2
        <h2>3</h2> level 1
        <h3>4</h3> level 2
        <h4>5</h4> level 3
    ''', structure_only=True)
    assert root == dict(Count=5, First=1, Last=3)
    assert bookmarks == [
        dict(Count=1, First=2, Last=2, Next=3, Parent=0, Prev=None),
        dict(Count=0, First=None, Last=None, Next=None, Parent=1, Prev=None),
        dict(Count=2, First=4, Last=4, Next=None, Parent=0, Prev=1),
        dict(Count=1, First=5, Last=5, Next=None, Parent=3, Prev=None),
        dict(Count=0, First=None, Last=None, Next=None, Parent=4, Prev=None)]

    root, bookmarks = get_bookmarks('''
        <h2>1</h2> h2 level 1
        <h4>2</h4> h4 level 2
        <h3>3</h3> h3 level 2
        <h5>4</h5> h5 level 3
        <h1>5</h1> h1 level 1
        <h2>6</h2> h2 level 2
        <h2>7</h2> h2 level 2
        <h4>8</h4> h4 level 3
        <h1>9</h1> h1 level 1
    ''', structure_only=True)
    assert root == dict(Count=9, First=1, Last=9)
    assert bookmarks == [
        dict(Count=3, First=2, Last=3, Next=5, Parent=0, Prev=None),
        dict(Count=0, First=None, Last=None, Next=3, Parent=1, Prev=None),
        dict(Count=1, First=4, Last=4, Next=None, Parent=1, Prev=2),
        dict(Count=0, First=None, Last=None, Next=None, Parent=3, Prev=None),
        dict(Count=3, First=6, Last=7, Next=9, Parent=0, Prev=1),
        dict(Count=0, First=None, Last=None, Next=7, Parent=5, Prev=None),
        dict(Count=1, First=8, Last=8, Next=None, Parent=5, Prev=6),
        dict(Count=0, First=None, Last=None, Next=None, Parent=7, Prev=None),
        dict(Count=0, First=None, Last=None, Next=None, Parent=0, Prev=5)]

    # Reference for the next test. zoom=1
    root, bookmarks = get_bookmarks('<h2>a</h2>')
    assert root == dict(Count=1, First=1, Last=1)
    assert bookmarks == [
        dict(Count=0, First=None, Last=None, Next=None, Parent=0, Prev=None,
             label='a', target=(0, 50, 950))]

    root, bookmarks = get_bookmarks('<h2>a</h2>', zoom=1.5)
    assert root == dict(Count=1, First=1, Last=1)
    assert bookmarks == [
        dict(Count=0, First=None, Last=None, Next=None, Parent=0, Prev=None,
             label='a', target=(0, 75, 1425))]


@assert_no_logs
def test_links():
    links = get_links('<body>')
    assert links == [[]]

    links = get_links('''
        <style>
            body { margin: 0; font-size: 10pt; line-height: 2 }
            p { display: block; height: 90pt; margin: 0 0 10pt 0 }
            img { width: 30pt; vertical-align: top }
        </style>
        <p><a href="http://weasyprint.org"><img src=pattern.png></a></p>
        <p style="padding: 0 10pt"><a
            href="#lipsum"><img style="border: solid 1pt"
                                src=pattern.png></a></p>
        <p id=hello>Hello, World</p>
        <p id=lipsum>
            <a style="display: block; page-break-before: always; height: 30pt"
               href="#hel%6Co"></a>
        </p>
    ''')
    assert links == [
        [
            # 30pt wide (like the image), 20pt high (like line-height)
            ('external', 'http://weasyprint.org', (50, 950, 80, 930)),
            # The image itself: 30*30pt
            ('external', 'http://weasyprint.org', (50, 950, 80, 920)),

            # 32pt wide (image + 2 * 1pt of border), 20pt high
            ('internal', (1, 50, 950), (60, 850, 92, 830)),
            # The image itself: 32*32pt
            ('internal', (1, 50, 950), (60, 850, 92, 818)),
        ], [
            # 400pt wide (block), 30pt high
            ('internal', (0, 50, 750), (50, 950, 450, 920)),
        ]
    ]

    links = get_links(
        '<a href="../lipsum" style="display: block">',
        base_url='http://weasyprint.org/foo/bar/')
    assert links == [[('external',
                       'http://weasyprint.org/foo/lipsum',
                       (50, 950, 450, 950))]]


@assert_no_logs
def test_relative_links():
    # Relative URI reference without a base URI: not allowed
    with capture_logs() as logs:
        links = get_links(
            '<a href="../lipsum" style="display: block">',
            base_url=None)
    assert links == [[]]
    assert len(logs) == 1
    assert 'WARNING: Relative URI reference without a base URI' in logs[0]

    with capture_logs() as logs:
        links = get_links(
            '<div style="-weasy-link: url(../lipsum)">',
            base_url=None)
    assert links == [[]]
    assert len(logs) == 1
    assert 'WARNING: Ignored `-weasy-link: url(../lipsum)`' in logs[0]
    assert 'Relative URI reference without a base URI' in logs[0]

    # Internal URI reference without a base URI: OK
    links = get_links(
        '<a href="#lipsum" id="lipsum" style="display: block">',
        base_url=None)
    assert links == [[('internal', (0, 50, 950), (50, 950, 450, 950))]]

    links = get_links(
        '<div style="-weasy-link: url(#lipsum)" id="lipsum">',
        base_url=None)
    assert links == [[('internal', (0, 50, 950), (50, 950, 450, 950))]]


@assert_no_logs
def test_missing_links():
    with capture_logs() as logs:
        links = get_links('''
            <style> a { display: block; height: 15pt; } </style>
            <body>
                <a href="#lipsum"></a>
                <a href="#missing" id="lipsum"></a>
        ''', base_url=None)
    assert links == [[('internal', (0, 50, 935), (50, 950, 450, 935))]]
    assert len(logs) == 1
    assert 'WARNING: No anchor #missing for internal URI reference' in logs[0]


@assert_no_logs
def test_jpeg():
    if not CAIRO_HAS_MIME_DATA:
        pytest.xfail()

    def render(html):
        return TestHTML(base_url=resource_filename('dummy.html'),
                        string=html).write_pdf()
    assert b'/Filter /DCTDecode' not in render('<img src="pattern.gif">')
    # JPEG-encoded image, embedded in PDF:
    assert b'/Filter /DCTDecode' in render('<img src="blue.jpg">')


@assert_no_logs
def test_document_info():
    pdf_bytes = TestHTML(string='''
        <meta name=author content="I Me &amp; Myself">
        <title>Test document</title>
        <h1>Another title</h1>
        <meta name=generator content="Human after all">
        <meta name=keywords content="html ,	css,
                                     pdf,css">
        <meta name=description content="Blah… ">
        <meta name=dcterms.created content=2011-04>
        <meta name=dcterms.modified content=2013-07-21T23:46+01:00>
    ''').write_pdf()
    assert (b'/Author (\xfe\xff\x00I\x00 \x00M\x00e\x00 \x00&\x00 \x00'
            b'M\x00y\x00s\x00e\x00l\x00f)' in pdf_bytes)
    assert (b'/Title (\xfe\xff\x00T\x00e\x00s\x00t\x00 \x00d\x00o\x00c'
            b'\x00u\x00m\x00e\x00n\x00t)' in pdf_bytes)
    assert (b'/Creator (\xfe\xff\x00H\x00u\x00m\x00a\x00n\x00\xa0\x00a'
            b'\x00f\x00t\x00e\x00r\x00\xa0\x00a\x00l\x00l)' in pdf_bytes)
    assert (b'/Keywords (\xfe\xff\x00h\x00t\x00m\x00l\x00,\x00 '
            b'\x00c\x00s\x00s\x00,\x00 \x00p\x00d\x00f)' in pdf_bytes)
    assert b'/Subject (\xfe\xff\x00B\x00l\x00a\x00h &\x00 )' in pdf_bytes
    assert b'/CreationDate (D:201104)' in pdf_bytes
    assert b"/ModDate (D:20130721234600+01'00')" in pdf_bytes


@assert_no_logs
def test_embedded_files():
    with temp_directory() as absolute_tmp_dir:
        absolute_tmp_file = os.path.join(absolute_tmp_dir, 'some_file.txt')
        adata = b'12345678'
        with open(absolute_tmp_file, 'wb') as afile:
            afile.write(adata)
        absolute_url = path2url(absolute_tmp_file)
        assert absolute_url.startswith('file://')

        with temp_directory() as relative_tmp_dir:
            relative_tmp_file = os.path.join(relative_tmp_dir, 'äöü.txt')
            rdata = b'abcdefgh'
            with open(relative_tmp_file, 'wb') as rfile:
                rfile.write(rdata)

            pdf_bytes = TestHTML(
                string='''
                    <title>Test document</title>
                    <meta charset="utf-8">
                    <link
                        rel="attachment"
                        title="some file attachment äöü"
                        href="data:,hi%20there">
                    <link rel="attachment" href="{0}">
                    <link rel="attachment" href="{1}">
                    <h1>Heading 1</h1>
                    <h2>Heading 2</h2>
                '''.format(absolute_url, os.path.basename(relative_tmp_file)),
                base_url=relative_tmp_dir,
            ).write_pdf(
                attachments=[
                    Attachment('data:,oob attachment', description='Hello'),
                    'data:,raw URL',
                    io.BytesIO(b'file like obj')
                ]
            )

    assert ((b'<' + hashlib.md5(b'hi there').hexdigest().encode('ascii') +
             b'>') in pdf_bytes)
    assert (b'/F ()' in pdf_bytes)
    assert (b'/UF (\xfe\xff\x00a\x00t\x00t\x00a\x00c\x00h\x00m\x00e\x00n'
            b'\x00t\x00.\x00b\x00i\x00n)' in pdf_bytes)
    assert (b'/Desc (\xfe\xff\x00s\x00o\x00m\x00e\x00 \x00f\x00i\x00l\x00e'
            b'\x00 \x00a\x00t\x00t\x00a\x00c\x00h\x00m\x00e\x00n\x00t\x00 '
            b'\x00\xe4\x00\xf6\x00\xfc)' in pdf_bytes)

    assert hashlib.md5(adata).hexdigest().encode('ascii') in pdf_bytes
    assert (os.path.basename(absolute_tmp_file).encode('utf-16-be')
            in pdf_bytes)

    assert hashlib.md5(rdata).hexdigest().encode('ascii') in pdf_bytes
    assert (os.path.basename(relative_tmp_file).encode('utf-16-be')
            in pdf_bytes)

    assert (hashlib.md5(b'oob attachment').hexdigest().encode('ascii')
            in pdf_bytes)
    assert b'/Desc (\xfe\xff\x00H\x00e\x00l\x00l\x00o)' in pdf_bytes
    assert (hashlib.md5(b'raw URL').hexdigest().encode('ascii')
            in pdf_bytes)
    assert (hashlib.md5(b'file like obj').hexdigest().encode('ascii')
            in pdf_bytes)

    assert b'/EmbeddedFiles' in pdf_bytes
    assert b'/Outlines' in pdf_bytes

    pdf_bytes = TestHTML(string='''
        <title>Test document 2</title>
        <meta charset="utf-8">
        <link
            rel="attachment"
            href="data:,some data">
    ''').write_pdf()

    assert hashlib.md5(b'some data').hexdigest().encode('ascii') in pdf_bytes
    assert b'/EmbeddedFiles' in pdf_bytes
    assert b'/Outlines' not in pdf_bytes

    pdf_bytes = TestHTML(string='''
        <title>Test document 3</title>
        <meta charset="utf-8">
        <h1>Heading</h1>
    ''').write_pdf()

    assert b'/EmbeddedFiles' not in pdf_bytes
    assert b'/Outlines' in pdf_bytes

    pdf_bytes = TestHTML(string='''
        <title>Test document 4</title>
        <meta charset="utf-8">
    ''').write_pdf()

    assert b'/EmbeddedFiles' not in pdf_bytes
    assert b'/Outlines' not in pdf_bytes


@assert_no_logs
def test_annotation_files():
    pdf_bytes = TestHTML(string='''
        <title>Test document</title>
        <meta charset="utf-8">
        <a
            rel="attachment"
            href="data:,some data"
            download>A link that lets you download an attachment</a>
    ''').write_pdf()

    assert hashlib.md5(b'some data').hexdigest().encode('ascii') in pdf_bytes
    assert b'/FileAttachment' in pdf_bytes
    assert b'/EmbeddedFiles' not in pdf_bytes
