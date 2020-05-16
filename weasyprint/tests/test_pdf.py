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

from .. import Attachment
from ..urls import path2url
from .testing_utils import (
    FakeHTML, assert_no_logs, capture_logs, resource_filename)

# Top of the page is 297mm ~= 842pt
TOP = 842
# Right of the page is 210mm ~= 595pt
RIGHT = 595

# TODO: fix tests
pdf = None


def assert_rect_almost_equal(rect, values):
    """Test that PDF rect string equals given values.

    We avoid rounding errors by allowing a delta of 1, as both WeasyPrint and
    cairo round coordinates in unpredictable ways.

    """
    if isinstance(rect, bytes):
        rect = rect.decode('ascii')
    for a, b in zip(rect.strip(' []').split(), values):
        assert abs(int(a) - b) <= 1


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
def test_links_none():
    pdf = FakeHTML(string='<body>').write_pdf()
    assert b'Annots' not in pdf


@assert_no_logs
def test_links():
    fileobj = io.BytesIO()
    FakeHTML(string='''
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
    ''', base_url=resource_filename('<inline HTML>')).write_pdf(target=fileobj)
    pdf_file = pdf.PDFFile(fileobj)
    links = [
        annot for page in pdf_file.pages
        for annot in page.get_indirect_dict_array('Annots', pdf_file)]

    # 30pt wide (like the image), 20pt high (like line-height)
    assert links[0].get_value('URI', '(.*)') == b'(http://weasyprint.org)'
    assert links[0].get_value('S', '(.*)') == b'/URI'
    assert_rect_almost_equal(
        links[0].get_value('Rect', '(.*)'), (0, TOP - 20, 30, TOP))

    # The image itself: 30*30pt
    assert links[1].get_value('URI', '(.*)') == b'(http://weasyprint.org)'
    assert links[1].get_value('S', '(.*)') == b'/URI'
    assert_rect_almost_equal(
        links[1].get_value('Rect', '(.*)'), (0, TOP - 30, 30, TOP))

    # 32pt wide (image + 2 * 1pt of border), 20pt high
    # TODO: replace these commented tests now that we use named destinations
    # assert links[2].get_value('Subtype', '(.*)') == b'/Link'
    # dest = links[2].get_value('Dest', '(.*)').strip(b'[]').split()
    # assert dest[-4] == b'/XYZ'
    # assert [round(float(value)) for value in dest[-3:]] == […]
    assert_rect_almost_equal(
        links[2].get_value('Rect', '(.*)'),
        (10, TOP - 100 - 20, 10 + 32, TOP - 100))

    # The image itself: 32*32pt
    # TODO: same as above
    # assert links[3].get_value('Subtype', '(.*)') == b'/Link'
    # dest = links[3].get_value('Dest', '(.*)').strip(b'[]').split()
    # assert dest[-4] == b'/XYZ'
    # assert [round(float(value)) for value in dest[-3:]] == […]
    assert_rect_almost_equal(
        links[3].get_value('Rect', '(.*)'),
        (10, TOP - 100 - 32, 10 + 32, TOP - 100))

    # 100% wide (block), 30pt high
    assert links[4].get_value('Subtype', '(.*)') == b'/Link'
    dest = links[4].get_value('Dest', '(.*)').strip(b'[]').split()
    assert dest == [b'(hello)']
    names = (
        pdf_file.catalog
        .get_indirect_dict('Names', pdf_file)
        .get_indirect_dict('Dests', pdf_file)
        .byte_string).decode('ascii')
    assert_rect_almost_equal(
        re.search(
            '\\(hello\\) \\[\\d+ \\d+ R /XYZ (\\d+ \\d+ \\d+)]', names
        ).group(1),
        (0, TOP - 200, 0))
    assert_rect_almost_equal(
        links[4].get_value('Rect', '(.*)'), (0, TOP - 30, RIGHT, TOP))

    # 100% wide (block), 0pt high
    fileobj = io.BytesIO()
    FakeHTML(
        string='<a href="../lipsum" style="display: block"></a>a',
        base_url='http://weasyprint.org/foo/bar/').write_pdf(target=fileobj)
    pdf_file = pdf.PDFFile(fileobj)
    link, = [
        annot for page in pdf_file.pages
        for annot in page.get_indirect_dict_array('Annots', pdf_file)]
    assert (
        link.get_value('URI', '(.*)') == b'(http://weasyprint.org/foo/lipsum)')
    assert link.get_value('S', '(.*)') == b'/URI'
    assert_rect_almost_equal(
        link.get_value('Rect', '(.*)'), (0, TOP, RIGHT, TOP))


@assert_no_logs
def test_relative_links():
    # Relative URI reference without a base URI: allowed for anchors
    fileobj = io.BytesIO()
    FakeHTML(
        string='<a href="../lipsum" style="display: block"></a>a',
        base_url=None).write_pdf(target=fileobj)
    pdf_file = pdf.PDFFile(fileobj)
    annots = pdf_file.pages[0].get_indirect_dict_array('Annots', pdf_file)[0]
    assert annots.get_value('URI', '(.*)') == b'(../lipsum)'
    assert annots.get_value('S', '(.*)') == b'/URI'
    assert_rect_almost_equal(
        annots.get_value('Rect', '(.*)'), (0, TOP, RIGHT, TOP))


@assert_no_logs
def test_relative_links_missing_base():
    # Relative URI reference without a base URI: not supported for -weasy-link
    fileobj = io.BytesIO()
    with capture_logs() as logs:
        FakeHTML(
            string='<div style="-weasy-link: url(../lipsum)">',
            base_url=None).write_pdf(target=fileobj)
    pdf_file = pdf.PDFFile(fileobj)
    with pytest.raises(AttributeError):
        pdf_file.pages[0].get_indirect_dict_array('Annots', pdf_file)
    assert len(logs) == 1
    assert 'WARNING: Ignored `-weasy-link: url("../lipsum")`' in logs[0]
    assert 'Relative URI reference without a base URI' in logs[0]


@assert_no_logs
def test_relative_links_internal():
    # Internal URI reference without a base URI: OK
    fileobj = io.BytesIO()
    FakeHTML(
        string='<a href="#lipsum" id="lipsum" style="display: block"></a>a',
        base_url=None).write_pdf(target=fileobj)
    pdf_file = pdf.PDFFile(fileobj)
    annots = pdf_file.pages[0].get_indirect_dict_array('Annots', pdf_file)[0]
    dest = annots.get_value('Dest', '(.*)')
    assert dest == b'(lipsum)'
    names = (
        pdf_file.catalog
        .get_indirect_dict('Names', pdf_file)
        .get_indirect_dict('Dests', pdf_file)
        .byte_string).decode('ascii')
    assert_rect_almost_equal(
        re.search(
            '\\(lipsum\\) \\[\\d+ \\d+ R /XYZ (\\d+ \\d+ \\d+)]', names
        ).group(1),
        (0, TOP, 0))
    assert_rect_almost_equal(
        annots.get_value('Rect', '(.*)'), (0, TOP, RIGHT, TOP))


@assert_no_logs
def test_relative_links_anchors():
    fileobj = io.BytesIO()
    FakeHTML(
        string='<div style="-weasy-link: url(#lipsum)" id="lipsum"></div>a',
        base_url=None).write_pdf(target=fileobj)
    pdf_file = pdf.PDFFile(fileobj)
    annots = pdf_file.pages[0].get_indirect_dict_array('Annots', pdf_file)[0]
    dest = annots.get_value('Dest', '(.*)')
    assert dest == b'(lipsum)'
    names = (
        pdf_file.catalog
        .get_indirect_dict('Names', pdf_file)
        .get_indirect_dict('Dests', pdf_file)
        .byte_string).decode('ascii')
    assert_rect_almost_equal(
        re.search(
            '\\(lipsum\\) \\[\\d+ \\d+ R /XYZ (\\d+ \\d+ \\d+)]', names
        ).group(1),
        (0, TOP, 0))
    assert_rect_almost_equal(
        annots.get_value('Rect', '(.*)'), (0, TOP, RIGHT, TOP))


@assert_no_logs
def test_missing_links():
    fileobj = io.BytesIO()
    with capture_logs() as logs:
        FakeHTML(string='''
          <style> a { display: block; height: 15pt } </style>
          <a href="#lipsum"></a>
          <a href="#missing" id="lipsum"></a>a
        ''', base_url=None).write_pdf(target=fileobj)
    pdf_file = pdf.PDFFile(fileobj)
    annots = pdf_file.pages[0].get_indirect_dict_array('Annots', pdf_file)[0]
    dest = annots.get_value('Dest', '(.*)')
    assert dest == b'(lipsum)'
    names = (
        pdf_file.catalog
        .get_indirect_dict('Names', pdf_file)
        .get_indirect_dict('Dests', pdf_file)
        .byte_string).decode('ascii')
    assert_rect_almost_equal(
        re.search(
            '\\(lipsum\\) \\[\\d+ \\d+ R /XYZ (\\d+ \\d+ \\d+)]', names
        ).group(1),
        (0, TOP - 15, 0))
    assert_rect_almost_equal(
        annots.get_value('Rect', '(.*)'), (0, TOP - 15, RIGHT, TOP))
    assert len(logs) == 1
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
