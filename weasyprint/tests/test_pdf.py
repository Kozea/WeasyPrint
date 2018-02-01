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
from pdfrw import PdfReader

from .. import Attachment
from ..images import CAIRO_HAS_MIME_DATA
from ..urls import path2url
from .testing_utils import (
    FakeHTML, assert_no_logs, capture_logs, resource_filename, temp_directory)

# Top of the page is 297mm ~= 842pt
TOP = 842
# Right of the page is 210mm ~= 595pt
RIGHT = 595


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

    fileobj.seek(0)
    sizes = [page.MediaBox for page in PdfReader(fileobj).Root.Pages.Kids]
    assert sizes == [
        ['0', '0', '100', '100'],
        ['0', '0', '200', '10'],
        ['0', '0', '3.14', '987654321']
    ]


@assert_no_logs
def test_page_size():
    pdf_bytes = FakeHTML(string='<style>@page{size:3in 4in').write_pdf()
    pdf = PdfReader(fdata=pdf_bytes)
    assert pdf.Root.Pages.Kids[0].MediaBox == ['0', '0', '216', '288']

    pdf_bytes = FakeHTML(string='<style>@page{size:3in 4in').write_pdf(
        zoom=1.5)
    pdf = PdfReader(fdata=pdf_bytes)
    assert pdf.Root.Pages.Kids[0].MediaBox == ['0', '0', '324', '432']


@assert_no_logs
def test_bookmarks():
    """Test the structure of the document bookmarks."""
    pdf_bytes = FakeHTML(string='''
        <h1>a</h1>  #
        <h4>b</h4>  ####
        <h3>c</h3>  ###
        <h2>d</h2>  ##
        <h1>e</h1>  #
    ''').write_pdf()
    outlines = PdfReader(fdata=pdf_bytes).Root.Outlines
    # a
    # |_ b
    # |_ c
    # L_ d
    # e
    assert outlines.Count == '5'
    assert outlines.First.Title == '(a)'
    assert outlines.First.First.Title == '(b)'
    assert outlines.First.First.Next.Title == '(c)'
    assert outlines.First.First.Next.Next.Title == '(d)'
    assert outlines.First.Last.Title == '(d)'
    assert outlines.First.Next.Title == '(e)'
    assert outlines.Last.Title == '(e)'

    pdf_bytes = FakeHTML(string='<body>').write_pdf()
    assert PdfReader(fdata=pdf_bytes).Root.Outlines is None

    pdf_bytes = FakeHTML(string='<h1>a nbsp…</h1>').write_pdf()
    outlines = PdfReader(fdata=pdf_bytes).Root.Outlines
    assert outlines.First.Title.decode() == 'a nbsp…'

    pdf_bytes = FakeHTML(string='''
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
    ''').write_pdf()
    outlines = PdfReader(fdata=pdf_bytes).Root.Outlines
    # 1
    # 2
    # |_ 3
    # |_ 4
    # |  L_ 5
    # L_ 6
    # 7
    # L_ 8
    #    L_ 9
    # 10
    # L_ 11
    assert outlines.Count == '11'
    assert outlines.First.Title == '(Title 1)'
    assert outlines.First.Next.Title == '(Title 2)'
    assert outlines.First.Next.Count == '5'
    assert outlines.First.Next.First.Title == '(Title 3)'
    assert outlines.First.Next.First.Parent.Title == '(Title 2)'
    assert outlines.First.Next.First.Next.Title == '(Title 4)'
    assert outlines.First.Next.First.Next.Count == '2'
    assert outlines.First.Next.First.Next.First.Title == '(Title 5)'
    assert outlines.First.Next.First.Next.Last.Title == '(Title 5)'
    assert outlines.First.Next.First.Next.Next.Title == '(Title 6)'
    assert outlines.First.Next.Last.Title == '(Title 6)'
    assert outlines.First.Next.Next.Title == '(Title 7)'
    assert outlines.First.Next.Next.Count == '3'
    assert outlines.First.Next.Next.First.Title == '(Title 8)'
    assert outlines.First.Next.Next.Last.Title == '(Title 8)'
    assert outlines.First.Next.Next.Last.Count == '2'
    assert outlines.First.Next.Next.First.First.Title == '(Title 9)'
    assert outlines.First.Next.Next.First.Last.Title == '(Title 9)'
    assert outlines.First.Next.Next.Next.Title == '(Title 10)'
    assert outlines.Last.Title == '(Title 10)'
    assert outlines.Last.First.Title == '(Title 11)'
    assert outlines.Last.Last.Title == '(Title 11)'

    pdf_bytes = FakeHTML(string='''
        <h2>1</h2> level 1
        <h4>2</h4> level 2
        <h2>3</h2> level 1
        <h3>4</h3> level 2
        <h4>5</h4> level 3
    ''').write_pdf()
    outlines = PdfReader(fdata=pdf_bytes).Root.Outlines
    # 1
    # L_ 2
    # 3
    # L_ 4
    #    L_ 5
    assert outlines.Count == '5'
    assert outlines.First.Title == '(1)'
    assert outlines.First.First.Title == '(2)'
    assert outlines.Last.Title == '(3)'
    assert outlines.Last.First.Title == '(4)'
    assert outlines.Last.First.First.Title == '(5)'

    pdf_bytes = FakeHTML(string='''
        <h2>1</h2> h2 level 1
        <h4>2</h4> h4 level 2
        <h3>3</h3> h3 level 2
        <h5>4</h5> h5 level 3
        <h1>5</h1> h1 level 1
        <h2>6</h2> h2 level 2
        <h2>7</h2> h2 level 2
        <h4>8</h4> h4 level 3
        <h1>9</h1> h1 level 1
    ''').write_pdf()
    # 1
    # |_ 2
    # L_ 3
    #    L_ 4
    # 5
    # |_ 6
    # L_ 7
    #    L_ 8
    # 9
    outlines = PdfReader(fdata=pdf_bytes).Root.Outlines
    assert outlines.Count == '9'
    assert outlines.First.Title == '(1)'
    assert outlines.First.First.Title == '(2)'
    assert outlines.First.First.Next.Title == '(3)'
    assert outlines.First.First.Next.First.Title == '(4)'
    assert outlines.First.Next.Title == '(5)'
    assert outlines.First.Next.First.Title == '(6)'
    assert outlines.First.Next.First.Next.Title == '(7)'
    assert outlines.First.Next.First.Next.First.Title == '(8)'
    assert outlines.Last.Title == '(9)'

    # Reference for the next test. zoom=1
    pdf_bytes = FakeHTML(string='<h2>a</h2>').write_pdf()
    outlines = PdfReader(fdata=pdf_bytes).Root.Outlines
    assert outlines.First.Title == '(a)'
    y = float(outlines.First.A.D[3])

    pdf_bytes = FakeHTML(string='<h2>a</h2>').write_pdf(zoom=1.5)
    outlines = PdfReader(fdata=pdf_bytes).Root.Outlines
    assert outlines.First.Title == '(a)'
    assert round(float(outlines.First.A.D[3])) == round(y * 1.5)


@assert_no_logs
def test_links():
    pdf_bytes = FakeHTML(string='<body>').write_pdf()
    assert PdfReader(fdata=pdf_bytes).Root.Pages.Kids[0].Annots is None

    pdf_bytes = FakeHTML(string='''
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
    ''', base_url=resource_filename('<inline HTML>')).write_pdf()
    links = [
        annot for page in PdfReader(fdata=pdf_bytes).Root.Pages.Kids
        for annot in page.Annots]

    # 30pt wide (like the image), 20pt high (like line-height)
    assert links[0].A == {
        '/URI': '(http://weasyprint.org)', '/S': '/URI', '/Type': '/Action'}
    assert [round(float(value)) for value in links[0].Rect] == [
        0, TOP, 30, TOP - 20]
    # The image itself: 30*30pt
    assert links[1].A == {
        '/URI': '(http://weasyprint.org)', '/S': '/URI', '/Type': '/Action'}
    assert [round(float(value)) for value in links[1].Rect] == [
        0, TOP, 30, TOP - 30]

    # 32pt wide (image + 2 * 1pt of border), 20pt high
    assert links[2].A.S == '/GoTo'
    assert links[2].A.Type == '/Action'
    assert links[2].A.D[1] == '/XYZ'
    assert round(float(links[2].A.D[3])) == TOP
    assert [round(float(value)) for value in links[2].Rect] == [
        10, TOP - 100, 10 + 32, TOP - 100 - 20]
    # The image itself: 32*32pt
    assert links[3].A.S == '/GoTo'
    assert links[3].A.Type == '/Action'
    assert links[3].A.D[1] == '/XYZ'
    assert round(float(links[3].A.D[3])) == TOP
    assert [round(float(value)) for value in links[3].Rect] == [
        10, TOP - 100, 10 + 32, TOP - 100 - 32]

    # 100% wide (block), 30pt high
    assert links[4].A.S == '/GoTo'
    assert links[4].A.Type == '/Action'
    assert links[4].A.D[1] == '/XYZ'
    assert round(float(links[4].A.D[3])) == TOP - 200
    assert [round(float(value)) for value in links[4].Rect] == [
        0, TOP, RIGHT, TOP - 30]

    # 100% wide (block), 0pt high
    pdf_bytes = FakeHTML(
        string='<a href="../lipsum" style="display: block">',
        base_url='http://weasyprint.org/foo/bar/').write_pdf()
    link, = [
        annot for page in PdfReader(fdata=pdf_bytes).Root.Pages.Kids
        for annot in page.Annots]
    assert link.A == {
        '/URI': '(http://weasyprint.org/foo/lipsum)',
        '/S': '/URI',
        '/Type': '/Action',
    }
    assert [round(float(value)) for value in link.Rect] == [0, TOP, RIGHT, TOP]


@assert_no_logs
def test_relative_links():
    # Relative URI reference without a base URI: allowed for anchors
    pdf_bytes = FakeHTML(
        string='<a href="../lipsum" style="display: block">',
        base_url=None).write_pdf()
    link, = PdfReader(fdata=pdf_bytes).Root.Pages.Kids[0].Annots
    assert link.A == {'/URI': '(../lipsum)', '/S': '/URI', '/Type': '/Action'}
    assert [round(float(value)) for value in link.Rect] == [0, TOP, RIGHT, TOP]

    # Relative URI reference without a base URI: not supported for -weasy-link
    with capture_logs() as logs:
        pdf_bytes = FakeHTML(
            string='<div style="-weasy-link: url(../lipsum)">',
            base_url=None).write_pdf()
    assert PdfReader(fdata=pdf_bytes).Root.Pages.Kids[0].Annots is None
    assert len(logs) == 1
    assert 'WARNING: Ignored `-weasy-link: url("../lipsum")`' in logs[0]
    assert 'Relative URI reference without a base URI' in logs[0]

    # Internal URI reference without a base URI: OK
    pdf_bytes = FakeHTML(
        string='<a href="#lipsum" id="lipsum" style="display: block">',
        base_url=None).write_pdf()
    link, = PdfReader(fdata=pdf_bytes).Root.Pages.Kids[0].Annots
    assert link.A.S == '/GoTo'
    assert link.A.Type == '/Action'
    assert link.A.D[1] == '/XYZ'
    assert round(float(link.A.D[3])) == TOP
    assert [round(float(value)) for value in link.Rect] == [0, TOP, RIGHT, TOP]

    pdf_bytes = FakeHTML(
        string='<div style="-weasy-link: url(#lipsum)" id="lipsum">',
        base_url=None).write_pdf()
    link, = PdfReader(fdata=pdf_bytes).Root.Pages.Kids[0].Annots
    assert link.A.S == '/GoTo'
    assert link.A.Type == '/Action'
    assert link.A.D[1] == '/XYZ'
    assert round(float(link.A.D[3])) == TOP
    assert [round(float(value)) for value in link.Rect] == [0, TOP, RIGHT, TOP]


@assert_no_logs
def test_missing_links():
    with capture_logs() as logs:
        pdf_bytes = FakeHTML(string='''
            <style> a { display: block; height: 15pt; } </style>
            <body>
                <a href="#lipsum"></a>
                <a href="#missing" id="lipsum"></a>
        ''', base_url=None).write_pdf()
    link, = PdfReader(fdata=pdf_bytes).Root.Pages.Kids[0].Annots
    assert link.A.S == '/GoTo'
    assert link.A.Type == '/Action'
    assert link.A.D[1] == '/XYZ'
    assert round(float(link.A.D[3])) == TOP - 15
    assert [round(float(value)) for value in link.Rect] == [
        0, TOP, RIGHT, TOP - 15]
    assert len(logs) == 1
    assert 'ERROR: No anchor #missing for internal URI reference' in logs[0]


@assert_no_logs
def test_jpeg():
    if not CAIRO_HAS_MIME_DATA:
        pytest.xfail()

    def render(html):
        return FakeHTML(base_url=resource_filename('dummy.html'),
                        string=html).write_pdf()
    assert b'/Filter /DCTDecode' not in render('<img src="pattern.gif">')
    # JPEG-encoded image, embedded in PDF:
    assert b'/Filter /DCTDecode' in render('<img src="blue.jpg">')


@assert_no_logs
def test_document_info():
    pdf_bytes = FakeHTML(string='''
        <meta name=author content="I Me &amp; Myself">
        <title>Test document</title>
        <h1>Another title</h1>
        <meta name=generator content="Human after all">
        <meta name=keywords content="html ,\tcss,
                                     pdf,css">
        <meta name=description content="Blah… ">
        <meta name=dcterms.created content=2011-04>
        <meta name=dcterms.modified content=2013-07-21T23:46+01:00>
    ''').write_pdf()
    info = PdfReader(fdata=pdf_bytes).Info
    assert info.Author.decode() == 'I Me & Myself'
    assert info.Title.decode() == 'Test document'
    assert info.Creator.decode() == 'Human after all'
    assert info.Keywords.decode() == 'html, css, pdf'
    assert info.Subject.decode() == 'Blah… '
    assert info.CreationDate.decode() == '201104'
    assert info.ModDate.decode() == "20130721234600+01'00'"


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

            pdf_bytes = FakeHTML(
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
    pdf = PdfReader(fdata=pdf_bytes)
    embedded = pdf.Root.Names.EmbeddedFiles.Names

    assert embedded[1].EF.F.Params.CheckSum == (
        '<{}>'.format(hashlib.md5(b'hi there').hexdigest()))
    assert embedded[1].F.decode() == ''
    assert embedded[1].UF.decode() == 'attachment.bin'
    assert embedded[1].Desc.decode() == 'some file attachment äöü'

    assert embedded[3].EF.F.Params.CheckSum == (
        '<{}>'.format(hashlib.md5(adata).hexdigest()))
    assert embedded[3].UF.decode() == os.path.basename(absolute_tmp_file)

    assert embedded[5].EF.F.Params.CheckSum == (
        '<{}>'.format(hashlib.md5(rdata).hexdigest()))
    assert embedded[5].UF.decode() == os.path.basename(relative_tmp_file)

    assert embedded[7].EF.F.Params.CheckSum == (
        '<{}>'.format(hashlib.md5(b'oob attachment').hexdigest()))
    assert embedded[7].Desc.decode() == 'Hello'

    assert embedded[9].EF.F.Params.CheckSum == (
        '<{}>'.format(hashlib.md5(b'raw URL').hexdigest()))

    assert embedded[11].EF.F.Params.CheckSum == (
        '<{}>'.format(hashlib.md5(b'file like obj').hexdigest()))

    pdf_bytes = FakeHTML(string='''
        <title>Test document 2</title>
        <meta charset="utf-8">
        <link
            rel="attachment"
            href="data:,some data">
    ''').write_pdf()
    pdf = PdfReader(fdata=pdf_bytes)
    embedded = pdf.Root.Names.EmbeddedFiles.Names

    assert embedded[1].EF.F.Params.CheckSum == (
        '<{}>'.format(hashlib.md5(b'some data').hexdigest()))

    pdf_bytes = FakeHTML(string='''
        <title>Test document 3</title>
        <meta charset="utf-8">
        <h1>Heading</h1>
    ''').write_pdf()
    pdf = PdfReader(fdata=pdf_bytes)
    assert pdf.Root.Names is None
    assert pdf.Root.Outlines is not None

    pdf_bytes = FakeHTML(string='''
        <title>Test document 4</title>
        <meta charset="utf-8">
    ''').write_pdf()
    pdf = PdfReader(fdata=pdf_bytes)
    assert pdf.Root.Names is None
    assert pdf.Root.Outlines is None


@assert_no_logs
def test_annotation_files():
    pdf_bytes = FakeHTML(string='''
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


@assert_no_logs
def test_bleed():
    pdf_bytes = FakeHTML(string='''
        <title>Test document</title>
        <style>
            @page { bleed: 30pt; size: 10pt }
        </style>
        <body>test
    ''').write_pdf()

    pdf = PdfReader(fdata=pdf_bytes)
    assert pdf.Root.Pages.Kids[0].MediaBox == ['0', '0', '70', '70']
    assert pdf.Root.Pages.Kids[0].BleedBox == ['20', '20', '50', '50']
    assert pdf.Root.Pages.Kids[0].TrimBox == ['30', '30', '40', '40']

    pdf_bytes = FakeHTML(string='''
        <title>Test document</title>
        <style>
            @page { bleed: 15pt 3pt 6pt 18pt; size: 12pt 15pt }
        </style>
        <body>test
    ''').write_pdf()

    pdf = PdfReader(fdata=pdf_bytes)
    assert pdf.Root.Pages.Kids[0].MediaBox == ['0', '0', '33', '36']
    assert pdf.Root.Pages.Kids[0].BleedBox == ['8', '5', '33', '36']
    assert pdf.Root.Pages.Kids[0].TrimBox == ['18', '15', '30', '30']
