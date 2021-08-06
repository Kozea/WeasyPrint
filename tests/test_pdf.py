"""
    weasyprint.tests.test_pdf
    -------------------------

    Test PDF-related code, including metadata, bookmarks and hyperlinks.

"""

import hashlib
import io
import os
import re
from codecs import BOM_UTF16_BE

import pytest
from weasyprint import Attachment
from weasyprint.urls import path2url

from .testing_utils import (
    FakeHTML, assert_no_logs, capture_logs, resource_filename)

# Top and right positions in points, rounded to the default float precision of
# 6 digits, a rendered by pydyf
TOP = round(297 * 72 / 25.4, 6)
RIGHT = round(210 * 72 / 25.4, 6)


@assert_no_logs
@pytest.mark.parametrize('zoom', (1, 1.5, 0.5))
def test_page_size_zoom(zoom):
    pdf = FakeHTML(string='<style>@page{size:3in 4in').write_pdf(zoom=zoom)
    assert '/MediaBox [ 0 0 {} {} ]'.format(
        int(216 * zoom), int(288 * zoom)).encode('ascii') in pdf


@assert_no_logs
def test_bookmarks_1():
    pdf = FakeHTML(string='''
      <h1>a</h1>  #
      <h4>b</h4>  ####
      <h3>c</h3>  ###
      <h2>d</h2>  ##
      <h1>e</h1>  #
    ''').write_pdf()
    # a
    # |_ b
    # |_ c
    # L_ d
    # e
    assert re.findall(b'/Count ([0-9-]*)', pdf)[-1] == b'5'
    assert re.findall(b'/Title \\((.*)\\)', pdf) == [
        b'a', b'b', b'c', b'd', b'e']


@assert_no_logs
def test_bookmarks_2():
    pdf = FakeHTML(string='<body>').write_pdf()
    assert b'Outlines' not in pdf


@assert_no_logs
def test_bookmarks_3():
    pdf = FakeHTML(string='<h1>a nbsp…</h1>').write_pdf()
    assert re.findall(b'/Title <(.*)>', pdf) == [
        b'feff006100a0006e0062007300702026']


@assert_no_logs
def test_bookmarks_4():
    pdf = FakeHTML(string='''
      <style>
        * { height: 90pt; margin: 0 0 10pt 0 }
      </style>
      <h1>1</h1>
      <h1>2</h1>
      <h2 style="position: relative; left: 20pt">3</h2>
      <h2>4</h2>
      <h3>5</h3>
      <span style="display: block; page-break-before: always"></span>
      <h2>6</h2>
      <h1>7</h1>
      <h2>8</h2>
      <h3>9</h3>
      <h1>10</h1>
      <h2>11</h2>
    ''').write_pdf()
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
    assert re.findall(b'/Title \\((.*)\\)', pdf) == [
        str(i).encode('ascii') for i in range(1, 12)]
    counts = re.findall(b'/Count ([0-9-]*)', pdf)
    counts.pop(0)  # Page count
    outlines = counts.pop()
    assert outlines == b'11'
    assert counts == [
        b'0', b'4', b'0', b'1', b'0', b'0', b'2', b'1', b'0', b'1', b'0']


@assert_no_logs
def test_bookmarks_5():
    pdf = FakeHTML(string='''
      <h2>1</h2> level 1
      <h4>2</h4> level 2
      <h2>3</h2> level 1
      <h3>4</h3> level 2
      <h4>5</h4> level 3
    ''').write_pdf()
    # 1
    # L_ 2
    # 3
    # L_ 4
    #    L_ 5
    assert re.findall(b'/Title \\((.*)\\)', pdf) == [
        str(i).encode('ascii') for i in range(1, 6)]
    counts = re.findall(b'/Count ([0-9-]*)', pdf)
    counts.pop(0)  # Page count
    outlines = counts.pop()
    assert outlines == b'5'
    assert counts == [b'1', b'0', b'2', b'1', b'0']


@assert_no_logs
def test_bookmarks_6():
    pdf = FakeHTML(string='''
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
    assert re.findall(b'/Title \\((.*)\\)', pdf) == [
        str(i).encode('ascii') for i in range(1, 10)]
    counts = re.findall(b'/Count ([0-9-]*)', pdf)
    counts.pop(0)  # Page count
    outlines = counts.pop()
    assert outlines == b'9'
    assert counts == [b'3', b'0', b'1', b'0', b'3', b'0', b'1', b'0', b'0']


@assert_no_logs
def test_bookmarks_7():
    # Reference for the next test. zoom=1
    pdf = FakeHTML(string='<h2>a</h2>').write_pdf()

    assert re.findall(b'/Title \\((.*)\\)', pdf) == [b'a']
    dest, = re.findall(b'/Dest \\[(.*)\\]', pdf)
    y = round(float(dest.strip().split()[-2]))

    pdf = FakeHTML(string='<h2>a</h2>').write_pdf(zoom=1.5)
    assert re.findall(b'/Title \\((.*)\\)', pdf) == [b'a']
    dest, = re.findall(b'/Dest \\[(.*)\\]', pdf)
    assert round(float(dest.strip().split()[-2])) == 1.5 * y


@assert_no_logs
def test_bookmarks_8():
    pdf = FakeHTML(string='''
      <h1>a</h1>
      <h2>b</h2>
      <h3>c</h3>
      <h2 style="bookmark-state: closed">d</h2>
      <h3>e</h3>
      <h4>f</h4>
      <h1>g</h1>
    ''').write_pdf()
    # a
    # |_ b
    # |  |_ c
    # |_ d (closed)
    # |  |_ e
    # |     |_ f
    # g
    assert re.findall(b'/Title \\((.*)\\)', pdf) == [
        b'a', b'b', b'c', b'd', b'e', b'f', b'g']
    counts = re.findall(b'/Count ([0-9-]*)', pdf)
    counts.pop(0)  # Page count
    outlines = counts.pop()
    assert outlines == b'5'
    assert counts == [b'3', b'1', b'0', b'-2', b'1', b'0', b'0']


@assert_no_logs
def test_bookmarks_9():
    pdf = FakeHTML(string='''
      <h1 style="bookmark-label: 'h1 on page ' counter(page)">a</h1>
    ''').write_pdf()
    counts = re.findall(b'/Count ([0-9-]*)', pdf)
    outlines = counts.pop()
    assert outlines == b'1'
    assert re.findall(b'/Title \\((.*)\\)', pdf) == [b'h1 on page 1']


@assert_no_logs
def test_bookmarks_10():
    pdf = FakeHTML(string='''
      <style>
      div:before, div:after {
         content: '';
         bookmark-level: 1;
         bookmark-label: 'x';
      }
      </style>
      <div>a</div>
    ''').write_pdf()
    # x
    # x
    counts = re.findall(b'/Count ([0-9-]*)', pdf)
    outlines = counts.pop()
    assert outlines == b'2'
    assert re.findall(b'/Title \\((.*)\\)', pdf) == [b'x', b'x']


@assert_no_logs
def test_bookmarks_11():
    pdf = FakeHTML(string='''
      <div style="display:inline; white-space:pre;
       bookmark-level:1; bookmark-label:'a'">
      a
      a
      a
      </div>
      <div style="bookmark-level:1; bookmark-label:'b'">
        <div>b</div>
        <div style="break-before:always">c</div>
      </div>
    ''').write_pdf()
    # a
    # b
    counts = re.findall(b'/Count ([0-9-]*)', pdf)
    outlines = counts.pop()
    assert outlines == b'2'
    assert re.findall(b'/Title \\((.*)\\)', pdf) == [b'a', b'b']


@assert_no_logs
def test_links_none():
    pdf = FakeHTML(string='<body>').write_pdf()
    assert b'Annots' not in pdf


@assert_no_logs
def test_links():
    pdf = FakeHTML(string='''
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
           href="#hel%6Co"></a>a
      </p>
    ''', base_url=resource_filename('<inline HTML>')).write_pdf()

    uris = re.findall(b'/URI \\((.*)\\)', pdf)
    types = re.findall(b'/S (.*)', pdf)
    subtypes = re.findall(b'/Subtype (.*)', pdf)
    rects = [
        [float(number) for number in match.split()] for match in re.findall(
            b'/Rect \\[ ([\\d\\.]+ [\\d\\.]+ [\\d\\.]+ [\\d\\.]+) \\]', pdf)]

    # 30pt wide (like the image), 20pt high (like line-height)
    assert uris.pop(0) == b'http://weasyprint.org'
    assert subtypes.pop(0) == b'/Link'
    assert types.pop(0) == b'/URI'
    assert rects.pop(0) == [0, TOP, 30, TOP - 20]

    # The image itself: 30*30pt
    assert uris.pop(0) == b'http://weasyprint.org'
    assert subtypes.pop(0) == b'/Link'
    assert types.pop(0) == b'/URI'
    assert rects.pop(0) == [0, TOP, 30, TOP - 30]

    # 32pt wide (image + 2 * 1pt of border), 20pt high
    assert subtypes.pop(0) == b'/Link'
    assert b'/Dest (lipsum)' in pdf
    link = re.search(
        b'\\(lipsum\\) \\[ \\d+ 0 R /XYZ ([\\d\\.]+ [\\d\\.]+ [\\d\\.]+) ]',
        pdf).group(1)
    assert [float(number) for number in link.split()] == [0, TOP, 0]
    assert rects.pop(0) == [10, TOP - 100, 10 + 32, TOP - 100 - 20]

    # The image itself: 32*32pt
    assert subtypes.pop(0) == b'/Link'
    assert rects.pop(0) == [10, TOP - 100, 10 + 32, TOP - 100 - 32]

    # 100% wide (block), 30pt high
    assert subtypes.pop(0) == b'/Link'
    assert b'/Dest (hello)' in pdf
    link = re.search(
        b'\\(hello\\) \\[ \\d+ 0 R /XYZ ([\\d\\.]+ [\\d\\.]+ [\\d\\.]+) ]',
        pdf).group(1)
    assert [float(number) for number in link.split()] == [0, TOP - 200, 0]
    assert rects.pop(0) == [0, TOP, RIGHT, TOP - 30]


@assert_no_logs
def test_sorted_links():
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/1352
    pdf = FakeHTML(string='''
      <p id="zzz">zzz</p>
      <p id="aaa">aaa</p>
      <a href="#zzz">z</a>
      <a href="#aaa">a</a>
    ''', base_url=resource_filename('<inline HTML>')).write_pdf()
    assert b'(zzz) [' in pdf.split(b'(aaa) [')[-1]


@assert_no_logs
def test_relative_links_no_height():
    # 100% wide (block), 0pt high
    pdf = FakeHTML(
        string='<a href="../lipsum" style="display: block"></a>a',
        base_url='http://weasyprint.org/foo/bar/').write_pdf()
    assert b'/S /URI\n/URI (http://weasyprint.org/foo/lipsum)'
    assert f'/Rect [ 0 {TOP} {RIGHT} {TOP} ]'.encode('ascii') in pdf


@assert_no_logs
def test_relative_links_missing_base():
    # Relative URI reference without a base URI
    pdf = FakeHTML(
        string='<a href="../lipsum" style="display: block"></a>a',
        base_url=None).write_pdf()
    assert b'/S /URI\n/URI (../lipsum)'
    assert f'/Rect [ 0 {TOP} {RIGHT} {TOP} ]'.encode('ascii') in pdf


@assert_no_logs
def test_relative_links_missing_base_link():
    # Relative URI reference without a base URI: not supported for -weasy-link
    with capture_logs() as logs:
        pdf = FakeHTML(
            string='<div style="-weasy-link: url(../lipsum)">',
            base_url=None).write_pdf()
    assert b'/Annots' not in pdf
    assert len(logs) == 1
    assert 'WARNING: Ignored `-weasy-link: url(../lipsum)`' in logs[0]
    assert 'Relative URI reference without a base URI' in logs[0]


@assert_no_logs
def test_relative_links_internal():
    # Internal URI reference without a base URI: OK
    pdf = FakeHTML(
        string='<a href="#lipsum" id="lipsum" style="display: block"></a>a',
        base_url=None).write_pdf()
    assert b'/Dest (lipsum)' in pdf
    link = re.search(
        b'\\(lipsum\\) \\[ \\d+ 0 R /XYZ ([\\d\\.]+ [\\d\\.]+ [\\d\\.]+) ]',
        pdf).group(1)
    assert [float(number) for number in link.split()] == [0, TOP, 0]
    rect = re.search(
        b'/Rect \\[ ([\\d\\.]+ [\\d\\.]+ [\\d\\.]+ [\\d\\.]+) \\]',
        pdf).group(1)
    assert [float(number) for number in rect.split()] == [0, TOP, RIGHT, TOP]


@assert_no_logs
def test_relative_links_anchors():
    pdf = FakeHTML(
        string='<div style="-weasy-link: url(#lipsum)" id="lipsum"></div>a',
        base_url=None).write_pdf()
    assert b'/Dest (lipsum)' in pdf
    link = re.search(
        b'\\(lipsum\\) \\[ \\d+ 0 R /XYZ ([\\d\\.]+ [\\d\\.]+ [\\d\\.]+) ]',
        pdf).group(1)
    assert [float(number) for number in link.split()] == [0, TOP, 0]
    rect = re.search(
        b'/Rect \\[ ([\\d\\.]+ [\\d\\.]+ [\\d\\.]+ [\\d\\.]+) \\]',
        pdf).group(1)
    assert [float(number) for number in rect.split()] == [0, TOP, RIGHT, TOP]


@assert_no_logs
def test_relative_links_different_base():
    pdf = FakeHTML(
        string='<a href="/test/lipsum"></a>a',
        base_url='http://weasyprint.org/foo/bar/').write_pdf()
    assert b'http://weasyprint.org/test/lipsum' in pdf


@assert_no_logs
def test_relative_links_same_base():
    pdf = FakeHTML(
        string='<a id="test" href="/foo/bar/#test"></a>a',
        base_url='http://weasyprint.org/foo/bar/').write_pdf()
    assert b'/Dest (test)' in pdf


@assert_no_logs
def test_missing_links():
    with capture_logs() as logs:
        pdf = FakeHTML(string='''
          <style> a { display: block; height: 15pt } </style>
          <a href="#lipsum"></a>
          <a href="#missing" id="lipsum"></a>
          <a href=""></a>a
        ''', base_url=None).write_pdf()
    assert b'/Dest (lipsum)' in pdf
    assert len(logs) == 1
    link = re.search(
        b'\\(lipsum\\) \\[ \\d+ 0 R /XYZ ([\\d\\.]+ [\\d\\.]+ [\\d\\.]+) ]',
        pdf).group(1)
    assert [float(number) for number in link.split()] == [0, TOP - 15, 0]
    rect = re.search(
        b'/Rect \\[ ([\\d\\.]+ [\\d\\.]+ [\\d\\.]+ [\\d\\.]+) \\]',
        pdf).group(1)
    assert [float(number) for number in rect.split()] == [
        0, TOP, RIGHT, TOP - 15]
    assert 'ERROR: No anchor #missing for internal URI reference' in logs[0]


@assert_no_logs
def test_embed_gif():
    assert b'/Filter /DCTDecode' not in FakeHTML(
        base_url=resource_filename('dummy.html'),
        string='<img src="pattern.gif">').write_pdf()


@assert_no_logs
def test_embed_jpeg():
    # JPEG-encoded image, embedded in PDF:
    assert b'/Filter /DCTDecode' in FakeHTML(
        base_url=resource_filename('dummy.html'),
        string='<img src="blue.jpg">').write_pdf()


@assert_no_logs
def test_embed_image_once():
    # Image repeated multiple times, embedded once
    assert FakeHTML(
        base_url=resource_filename('dummy.html'),
        string='''
          <img src="blue.jpg">
          <div style="background: url(blue.jpg)"></div>
          <img src="blue.jpg">
          <div style="background: url(blue.jpg) no-repeat"></div>
        ''').write_pdf().count(b'/Filter /DCTDecode') == 1


@assert_no_logs
def test_document_info():
    pdf = FakeHTML(string='''
      <meta name=author content="I Me &amp; Myself">
      <title>Test document</title>
      <h1>Another title</h1>
      <meta name=generator content="Human after all">
      <meta name=keywords content="html ,\tcss,
                                   pdf,css">
      <meta name=description content="Blah… ">
      <meta name=dcterms.created content=2011-04-21T23:00:00Z>
      <meta name=dcterms.modified content=2013-07-21T23:46+01:00>
    ''').write_pdf()
    assert b'/Author (I Me & Myself)' in pdf
    assert b'/Title (Test document)' in pdf
    assert (
        b'/Creator <feff00480075006d0061006e00a00061'
        b'006600740065007200a00061006c006c>') in pdf
    assert b'/Keywords (html, css, pdf)' in pdf
    assert b'/Subject <feff0042006c0061006820260020>' in pdf
    assert b'/CreationDate (20110421230000Z)' in pdf
    assert b"/ModDate (20130721234600+01'00)" in pdf


@assert_no_logs
def test_embedded_files_attachments(tmpdir):
    absolute_tmp_file = tmpdir.join('some_file.txt').strpath
    adata = b'12345678'
    with open(absolute_tmp_file, 'wb') as afile:
        afile.write(adata)
    absolute_url = path2url(absolute_tmp_file)
    assert absolute_url.startswith('file://')

    relative_tmp_file = tmpdir.join('äöü.txt').strpath
    rdata = b'abcdefgh'
    with open(relative_tmp_file, 'wb') as rfile:
        rfile.write(rdata)

    pdf = FakeHTML(
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
        base_url=tmpdir.strpath,
    ).write_pdf(
        attachments=[
            Attachment('data:,oob attachment', description='Hello'),
            'data:,raw URL',
            io.BytesIO(b'file like obj')
        ]
    )
    assert (
        '<{}>'.format(hashlib.md5(b'hi there').hexdigest()).encode('ascii')
        in pdf)
    assert b'/F ()' in pdf
    assert b'/UF (attachment.bin)' in pdf
    name = BOM_UTF16_BE + 'some file attachment äöü'.encode('utf-16-be')
    assert b'/Desc <' + name.hex().encode('ascii') + b'>' in pdf

    assert hashlib.md5(adata).hexdigest().encode('ascii') in pdf
    assert os.path.basename(absolute_tmp_file).encode('ascii') in pdf

    assert hashlib.md5(rdata).hexdigest().encode('ascii') in pdf
    name = BOM_UTF16_BE + 'some file attachment äöü'.encode('utf-16-be')
    assert b'/Desc <' + name.hex().encode('ascii') + b'>' in pdf

    assert hashlib.md5(b'oob attachment').hexdigest().encode('ascii') in pdf
    assert b'/Desc (Hello)' in pdf
    assert hashlib.md5(b'raw URL').hexdigest().encode('ascii') in pdf
    assert hashlib.md5(b'file like obj').hexdigest().encode('ascii') in pdf

    assert b'/EmbeddedFiles' in pdf
    assert b'/Outlines' in pdf


@assert_no_logs
def test_attachments_data():
    pdf = FakeHTML(string='''
      <title>Test document 2</title>
      <meta charset="utf-8">
      <link rel="attachment" href="data:,some data">
    ''').write_pdf()
    md5 = '<{}>'.format(hashlib.md5(b'some data').hexdigest()).encode('ascii')
    assert md5 in pdf


@assert_no_logs
def test_attachments_none():
    pdf = FakeHTML(string='''
      <title>Test document 3</title>
      <meta charset="utf-8">
      <h1>Heading</h1>
    ''').write_pdf()
    assert b'Names' not in pdf
    assert b'Outlines' in pdf


@assert_no_logs
def test_attachments_none_empty():
    pdf = FakeHTML(string='''
      <title>Test document 3</title>
      <meta charset="utf-8">
    ''').write_pdf()
    assert b'Names' not in pdf
    assert b'Outlines' not in pdf


@assert_no_logs
def test_annotations():
    pdf = FakeHTML(string='''
      <title>Test document</title>
      <meta charset="utf-8">
      <a
        rel="attachment"
        href="data:,some data"
        download>A link that lets you download an attachment</a>
    ''').write_pdf()

    assert hashlib.md5(b'some data').hexdigest().encode('ascii') in pdf
    assert b'/FileAttachment' in pdf
    assert b'/EmbeddedFiles' not in pdf


@pytest.mark.parametrize('style, media, bleed, trim', (
    ('bleed: 30pt; size: 10pt',
     [-30, -30, 40, 40],
     [-10, -10, 20, 20],
     [0, 0, 10, 10]),
    ('bleed: 15pt 3pt 6pt 18pt; size: 12pt 15pt',
     [-18, -15, 15, 21],
     [-10, -10, 15, 21],
     [0, 0, 12, 15]),
))
@assert_no_logs
def test_bleed(style, media, bleed, trim):
    pdf = FakeHTML(string='''
      <title>Test document</title>
      <style>@page { %s }</style>
      <body>test
    ''' % style).write_pdf()
    assert '/MediaBox [ {} {} {} {} ]'.format(*media).encode('ascii') in pdf
    assert '/BleedBox [ {} {} {} {} ]'.format(*bleed).encode('ascii') in pdf
    assert '/TrimBox [ {} {} {} {} ]'.format(*trim).encode('ascii') in pdf
