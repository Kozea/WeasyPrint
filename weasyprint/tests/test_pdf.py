"""
    weasyprint.tests.test_pdf
    -------------------------

    Test PDF-related code, including metadata, bookmarks and hyperlinks.

"""

import hashlib
import io
import os
import re

import cairocffi
import pytest

from .. import Attachment, pdf
from ..urls import path2url
from .testing_utils import (
    FakeHTML, assert_no_logs, capture_logs, requires, resource_filename)

# Top of the page is 297mm ~= 842pt
TOP = 842
# Right of the page is 210mm ~= 595pt
RIGHT = 595


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
@pytest.mark.parametrize('width, height', (
    (100, 100),
    (200, 10),
    (3.14, 987654321),
))
def test_pdf_parser(width, height):
    fileobj = io.BytesIO()
    surface = cairocffi.PDFSurface(fileobj, 1, 1)
    surface.set_size(width, height)
    surface.show_page()
    surface.finish()

    sizes = [page.get_value('MediaBox', '\\[(.+?)\\]').strip()
             for page in pdf.PDFFile(fileobj).pages]
    assert sizes == ['0 0 {} {}'.format(width, height).encode('ascii')]


@assert_no_logs
@pytest.mark.parametrize('zoom', (1, 1.5, 0.5))
def test_page_size_zoom(zoom):
    pdf_bytes = FakeHTML(
        string='<style>@page{size:3in 4in').write_pdf(zoom=zoom)
    assert '/MediaBox [ 0 0 {} {} ]'.format(
        int(216 * zoom), int(288 * zoom)).encode('ascii') in pdf_bytes


@assert_no_logs
@requires('cairo', (1, 15, 4))
def test_bookmarks_1():
    fileobj = io.BytesIO()
    FakeHTML(string='''
      <h1>a</h1>  #
      <h4>b</h4>  ####
      <h3>c</h3>  ###
      <h2>d</h2>  ##
      <h1>e</h1>  #
    ''').write_pdf(target=fileobj)
    # a
    # |_ b
    # |_ c
    # L_ d
    # e
    pdf_file = pdf.PDFFile(fileobj)
    outlines = pdf_file.catalog.get_indirect_dict('Outlines', pdf_file)
    assert outlines.get_type() == 'Outlines'
    assert outlines.get_value('Count', '(.*)') == b'-5'
    o1 = outlines.get_indirect_dict('First', pdf_file)
    assert o1.get_value('Title', '(.*)') == b'(a)'
    o11 = o1.get_indirect_dict('First', pdf_file)
    assert o11.get_value('Title', '(.*)') == b'(b)'
    o12 = o11.get_indirect_dict('Next', pdf_file)
    assert o12.get_value('Title', '(.*)') == b'(c)'
    o13 = o12.get_indirect_dict('Next', pdf_file)
    assert o13.get_value('Title', '(.*)') == b'(d)'
    o2 = o1.get_indirect_dict('Next', pdf_file)
    assert o2.get_value('Title', '(.*)') == b'(e)'


@assert_no_logs
def test_bookmarks_2():
    fileobj = io.BytesIO()
    FakeHTML(string='<body>').write_pdf(target=fileobj)
    pdf_file = pdf.PDFFile(fileobj)
    with pytest.raises(AttributeError):
        pdf_file.catalog.get_indirect_dict('Outlines', pdf_file)


@assert_no_logs
@requires('cairo', (1, 15, 4))
def test_bookmarks_3():
    fileobj = io.BytesIO()
    FakeHTML(string='<h1>a nbsp…</h1>').write_pdf(target=fileobj)
    pdf_file = pdf.PDFFile(fileobj)
    outlines = pdf_file.catalog.get_indirect_dict('Outlines', pdf_file)
    o1 = outlines.get_indirect_dict('First', pdf_file)
    # <FEFF006100A0006E0062007300702026> is the PDF representation of a nbsp…
    assert (
        o1.get_value('Title', '(.*)') == b'<FEFF006100A0006E0062007300702026>')


@assert_no_logs
@requires('cairo', (1, 15, 4))
def test_bookmarks_4():
    fileobj = io.BytesIO()
    FakeHTML(string='''
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
    ''').write_pdf(target=fileobj)
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
    pdf_file = pdf.PDFFile(fileobj)
    outlines = pdf_file.catalog.get_indirect_dict('Outlines', pdf_file)
    assert outlines.get_type() == 'Outlines'
    assert outlines.get_value('Count', '(.*)') == b'-11'
    o1 = outlines.get_indirect_dict('First', pdf_file)
    assert o1.get_value('Title', '(.*)') == b'(Title 1)'
    o2 = o1.get_indirect_dict('Next', pdf_file)
    assert o2.get_value('Title', '(.*)') == b'(Title 2)'
    assert o2.get_value('Count', '(.*)') == b'4'
    o3 = o2.get_indirect_dict('First', pdf_file)
    assert o3.get_value('Title', '(.*)') == b'(Title 3)'
    o4 = o3.get_indirect_dict('Next', pdf_file)
    assert o4.get_value('Title', '(.*)') == b'(Title 4)'
    assert o4.get_value('Count', '(.*)') == b'1'
    o5 = o4.get_indirect_dict('First', pdf_file)
    assert o5.get_value('Title', '(.*)') == b'(Title 5)'
    o6 = o4.get_indirect_dict('Next', pdf_file)
    assert o6.get_value('Title', '(.*)') == b'(Title 6)'
    o7 = o2.get_indirect_dict('Next', pdf_file)
    assert o7.get_value('Title', '(.*)') == b'(Title 7)'
    assert o7.get_value('Count', '(.*)') == b'2'
    o8 = o7.get_indirect_dict('First', pdf_file)
    assert o8.get_value('Title', '(.*)') == b'(Title 8)'
    assert o8.get_value('Count', '(.*)') == b'1'
    o9 = o8.get_indirect_dict('First', pdf_file)
    assert o9.get_value('Title', '(.*)') == b'(Title 9)'
    o10 = o7.get_indirect_dict('Next', pdf_file)
    assert o10.get_value('Title', '(.*)') == b'(Title 10)'
    assert o10.get_value('Count', '(.*)') == b'1'
    o11 = o10.get_indirect_dict('First', pdf_file)
    assert o11.get_value('Title', '(.*)') == b'(Title 11)'


@assert_no_logs
@requires('cairo', (1, 15, 4))
def test_bookmarks_5():
    fileobj = io.BytesIO()
    FakeHTML(string='''
      <h2>1</h2> level 1
      <h4>2</h4> level 2
      <h2>3</h2> level 1
      <h3>4</h3> level 2
      <h4>5</h4> level 3
    ''').write_pdf(target=fileobj)
    # 1
    # L_ 2
    # 3
    # L_ 4
    #    L_ 5
    pdf_file = pdf.PDFFile(fileobj)
    outlines = pdf_file.catalog.get_indirect_dict('Outlines', pdf_file)
    assert outlines.get_type() == 'Outlines'
    assert outlines.get_value('Count', '(.*)') == b'-5'
    o1 = outlines.get_indirect_dict('First', pdf_file)
    assert o1.get_value('Title', '(.*)') == b'(1)'
    o2 = o1.get_indirect_dict('First', pdf_file)
    assert o2.get_value('Title', '(.*)') == b'(2)'
    o3 = o1.get_indirect_dict('Next', pdf_file)
    assert o3.get_value('Title', '(.*)') == b'(3)'
    o4 = o3.get_indirect_dict('First', pdf_file)
    assert o4.get_value('Title', '(.*)') == b'(4)'
    o5 = o4.get_indirect_dict('First', pdf_file)
    assert o5.get_value('Title', '(.*)') == b'(5)'


@assert_no_logs
@requires('cairo', (1, 15, 4))
def test_bookmarks_6():
    fileobj = io.BytesIO()
    FakeHTML(string='''
      <h2>1</h2> h2 level 1
      <h4>2</h4> h4 level 2
      <h3>3</h3> h3 level 2
      <h5>4</h5> h5 level 3
      <h1>5</h1> h1 level 1
      <h2>6</h2> h2 level 2
      <h2>7</h2> h2 level 2
      <h4>8</h4> h4 level 3
      <h1>9</h1> h1 level 1
    ''').write_pdf(target=fileobj)
    # 1
    # |_ 2
    # L_ 3
    #    L_ 4
    # 5
    # |_ 6
    # L_ 7
    #    L_ 8
    # 9
    pdf_file = pdf.PDFFile(fileobj)
    outlines = pdf_file.catalog.get_indirect_dict('Outlines', pdf_file)
    assert outlines.get_type() == 'Outlines'
    assert outlines.get_value('Count', '(.*)') == b'-9'
    o1 = outlines.get_indirect_dict('First', pdf_file)
    assert o1.get_value('Title', '(.*)') == b'(1)'
    o2 = o1.get_indirect_dict('First', pdf_file)
    assert o2.get_value('Title', '(.*)') == b'(2)'
    o3 = o2.get_indirect_dict('Next', pdf_file)
    assert o3.get_value('Title', '(.*)') == b'(3)'
    o4 = o3.get_indirect_dict('First', pdf_file)
    assert o4.get_value('Title', '(.*)') == b'(4)'
    o5 = o1.get_indirect_dict('Next', pdf_file)
    assert o5.get_value('Title', '(.*)') == b'(5)'
    o6 = o5.get_indirect_dict('First', pdf_file)
    assert o6.get_value('Title', '(.*)') == b'(6)'
    o7 = o6.get_indirect_dict('Next', pdf_file)
    assert o7.get_value('Title', '(.*)') == b'(7)'
    o8 = o7.get_indirect_dict('First', pdf_file)
    assert o8.get_value('Title', '(.*)') == b'(8)'
    o9 = o5.get_indirect_dict('Next', pdf_file)
    assert o9.get_value('Title', '(.*)') == b'(9)'


@assert_no_logs
@requires('cairo', (1, 15, 4))
def test_bookmarks_7():
    # Reference for the next test. zoom=1
    fileobj = io.BytesIO()
    FakeHTML(string='<h2>a</h2>').write_pdf(target=fileobj)
    pdf_file = pdf.PDFFile(fileobj)
    outlines = pdf_file.catalog.get_indirect_dict('Outlines', pdf_file)
    assert outlines.get_type() == 'Outlines'
    o1 = outlines.get_indirect_dict('First', pdf_file)
    assert o1.get_value('Title', '(.*)') == b'(a)'
    y = float(o1.get_value('Dest', '\\[(.+?)\\]').strip().split()[-2])

    fileobj = io.BytesIO()
    FakeHTML(string='<h2>a</h2>').write_pdf(zoom=1.5, target=fileobj)
    pdf_file = pdf.PDFFile(fileobj)
    pdf_file = pdf.PDFFile(fileobj)
    outlines = pdf_file.catalog.get_indirect_dict('Outlines', pdf_file)
    assert outlines.get_type() == 'Outlines'
    o1 = outlines.get_indirect_dict('First', pdf_file)
    assert o1.get_value('Title', '(.*)') == b'(a)'
    assert (
        float(o1.get_value('Dest', '\\[(.+?)\\]').strip().split()[-2]) ==
        round(y * 1.5))


@assert_no_logs
@requires('cairo', (1, 15, 4))
def test_bookmarks_8():
    fileobj = io.BytesIO()
    FakeHTML(string='''
      <h1>a</h1>
      <h2>b</h2>
      <h3>c</h3>
      <h2 style="bookmark-state: closed">d</h2>
      <h3>e</h3>
      <h4>f</h4>
      <h1>g</h1>
    ''').write_pdf(target=fileobj)
    # a
    # |_ b
    # |  |_ c
    # |_ d (closed)
    # |  |_ e
    # |     |_ f
    # g
    pdf_file = pdf.PDFFile(fileobj)
    outlines = pdf_file.catalog.get_indirect_dict('Outlines', pdf_file)
    assert outlines.get_type() == 'Outlines'
    # d is closed, the number of displayed outlines is len(a, b, c, d, g) == 5
    assert outlines.get_value('Count', '(.*)') == b'-5'
    o1 = outlines.get_indirect_dict('First', pdf_file)
    assert o1.get_value('Title', '(.*)') == b'(a)'
    o11 = o1.get_indirect_dict('First', pdf_file)
    assert o11.get_value('Title', '(.*)') == b'(b)'
    o111 = o11.get_indirect_dict('First', pdf_file)
    assert o111.get_value('Title', '(.*)') == b'(c)'
    o12 = o11.get_indirect_dict('Next', pdf_file)
    assert o12.get_value('Title', '(.*)') == b'(d)'
    o121 = o12.get_indirect_dict('First', pdf_file)
    assert o121.get_value('Title', '(.*)') == b'(e)'
    o1211 = o121.get_indirect_dict('First', pdf_file)
    assert o1211.get_value('Title', '(.*)') == b'(f)'
    o2 = o1.get_indirect_dict('Next', pdf_file)
    assert o2.get_value('Title', '(.*)') == b'(g)'


@assert_no_logs
@requires('cairo', (1, 15, 4))
def test_bookmarks_9():
    fileobj = io.BytesIO()
    FakeHTML(string='''
      <h1 style="bookmark-label: 'h1 on page ' counter(page)">a</h1>
    ''').write_pdf(target=fileobj)
    # h1 on page 1
    pdf_file = pdf.PDFFile(fileobj)
    outlines = pdf_file.catalog.get_indirect_dict('Outlines', pdf_file)
    assert outlines.get_type() == 'Outlines'
    assert outlines.get_value('Count', '(.*)') == b'-1'
    o1 = outlines.get_indirect_dict('First', pdf_file)
    assert o1.get_value('Title', '(.*)') == b'(h1 on page 1)'


@assert_no_logs
@requires('cairo', (1, 15, 4))
def test_bookmarks_10():
    fileobj = io.BytesIO()
    FakeHTML(string='''
      <style>
      div:before, div:after {
         content: '';
         bookmark-level: 1;
         bookmark-label: 'x';
      }
      </style>
      <div>a</div>
    ''').write_pdf(target=fileobj)
    # x
    # x
    pdf_file = pdf.PDFFile(fileobj)
    outlines = pdf_file.catalog.get_indirect_dict('Outlines', pdf_file)
    assert outlines.get_type() == 'Outlines'
    assert outlines.get_value('Count', '(.*)') == b'-2'
    o1 = outlines.get_indirect_dict('First', pdf_file)
    assert o1.get_value('Title', '(.*)') == b'(x)'
    o2 = o1.get_indirect_dict('Next', pdf_file)
    assert o2.get_value('Title', '(.*)') == b'(x)'


@assert_no_logs
@requires('cairo', (1, 15, 4))
def test_bookmarks_11():
    fileobj = io.BytesIO()
    FakeHTML(string='''
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
    ''').write_pdf(target=fileobj)
    # a
    # b
    pdf_file = pdf.PDFFile(fileobj)
    outlines = pdf_file.catalog.get_indirect_dict('Outlines', pdf_file)
    assert outlines.get_type() == 'Outlines'
    assert outlines.get_value('Count', '(.*)') == b'-2'
    o1 = outlines.get_indirect_dict('First', pdf_file)
    assert o1.get_value('Title', '(.*)') == b'(a)'
    o2 = o1.get_indirect_dict('Next', pdf_file)
    assert o2.get_value('Title', '(.*)') == b'(b)'


@assert_no_logs
def test_links_none():
    fileobj = io.BytesIO()
    FakeHTML(string='<body>').write_pdf(target=fileobj)
    pdf_file = pdf.PDFFile(fileobj)
    with pytest.raises(AttributeError):
        pdf_file.pages[0].get_indirect_dict_array('Annots', pdf_file)


@assert_no_logs
@requires('cairo', (1, 15, 4))
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
@requires('cairo', (1, 15, 4))
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
@requires('cairo', (1, 15, 4))
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
@requires('cairo', (1, 15, 4))
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
@requires('cairo', (1, 15, 4))
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
@requires('cairo', (1, 15, 4))
def test_document_info():
    fileobj = io.BytesIO()
    FakeHTML(string='''
      <meta name=author content="I Me &amp; Myself">
      <title>Test document</title>
      <h1>Another title</h1>
      <meta name=generator content="Human after all">
      <meta name=keywords content="html ,\tcss,
                                   pdf,css">
      <meta name=description content="Blah… ">
      <meta name=dcterms.created content=2011-04-21T23:00:00Z>
      <meta name=dcterms.modified content=2013-07-21T23:46+01:00>
    ''').write_pdf(target=fileobj)
    info = pdf.PDFFile(fileobj).info
    assert info.get_value('Author', '(.*)') == b'(I Me & Myself)'
    assert info.get_value('Title', '(.*)') == b'(Test document)'
    assert info.get_value('Creator', '(.*)') == (
        b'<FEFF00480075006D0061006E00A00061006600740065007200A00061006C006C>')
    assert info.get_value('Keywords', '(.*)') == b'(html, css, pdf)'
    assert info.get_value('Subject', '(.*)') == (
        b'<FEFF0042006C0061006820260020>')
    assert info.get_value('CreationDate', '(.*)') == b"(20110421230000+00'00)"
    assert info.get_value('ModDate', '(.*)') == b"(20130721234600+01'00)"


@assert_no_logs
@requires('cairo', (1, 15, 4))
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

    fileobj = io.BytesIO()
    FakeHTML(
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
        target=fileobj,
        attachments=[
            Attachment('data:,oob attachment', description='Hello'),
            'data:,raw URL',
            io.BytesIO(b'file like obj')
        ]
    )
    pdf_bytes = fileobj.getvalue()
    assert (
        '<{}>'.format(hashlib.md5(b'hi there').hexdigest()).encode('ascii')
        in pdf_bytes)
    assert b'/F ()' in pdf_bytes
    assert (
        b'/UF (\xfe\xff\x00a\x00t\x00t\x00a\x00c\x00h\x00m\x00e\x00n'
        b'\x00t\x00.\x00b\x00i\x00n)' in pdf_bytes)
    assert (
        b'/Desc (\xfe\xff\x00s\x00o\x00m\x00e\x00 \x00f\x00i\x00l\x00e'
        b'\x00 \x00a\x00t\x00t\x00a\x00c\x00h\x00m\x00e\x00n\x00t\x00 '
        b'\x00\xe4\x00\xf6\x00\xfc)' in pdf_bytes)

    assert hashlib.md5(adata).hexdigest().encode('ascii') in pdf_bytes
    assert (
        os.path.basename(absolute_tmp_file).encode('utf-16-be')
        in pdf_bytes)

    assert hashlib.md5(rdata).hexdigest().encode('ascii') in pdf_bytes
    assert (
        os.path.basename(relative_tmp_file).encode('utf-16-be')
        in pdf_bytes)

    assert (
        hashlib.md5(b'oob attachment').hexdigest().encode('ascii')
        in pdf_bytes)
    assert b'/Desc (\xfe\xff\x00H\x00e\x00l\x00l\x00o)' in pdf_bytes
    assert (
        hashlib.md5(b'raw URL').hexdigest().encode('ascii')
        in pdf_bytes)
    assert (
        hashlib.md5(b'file like obj').hexdigest().encode('ascii')
        in pdf_bytes)

    assert b'/EmbeddedFiles' in pdf_bytes
    assert b'/Outlines' in pdf_bytes


@assert_no_logs
def test_attachments_data():
    fileobj = io.BytesIO()
    FakeHTML(string='''
      <title>Test document 2</title>
      <meta charset="utf-8">
      <link rel="attachment" href="data:,some data">
    ''').write_pdf(target=fileobj)
    md5 = '<{}>'.format(hashlib.md5(b'some data').hexdigest()).encode('ascii')
    assert md5 in fileobj.getvalue()


@assert_no_logs
@requires('cairo', (1, 15, 4))
def test_attachments_none():
    fileobj = io.BytesIO()
    FakeHTML(string='''
      <title>Test document 3</title>
      <meta charset="utf-8">
      <h1>Heading</h1>
    ''').write_pdf(target=fileobj)
    pdf_bytes = fileobj.getvalue()
    assert b'Names' not in pdf_bytes
    assert b'Outlines' in pdf_bytes


@assert_no_logs
def test_attachments_none_empty():
    fileobj = io.BytesIO()
    FakeHTML(string='''
      <title>Test document 3</title>
      <meta charset="utf-8">
    ''').write_pdf(target=fileobj)
    pdf_bytes = fileobj.getvalue()
    assert b'Names' not in pdf_bytes
    assert b'Outlines' not in pdf_bytes


@assert_no_logs
def test_annotations():
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


@pytest.mark.parametrize('style, media, bleed, trim', (
    ('bleed: 30pt; size: 10pt',
     [0, 0, 70, 70],
     [20.0, 20.0, 50.0, 50.0],
     [30.0, 30.0, 40.0, 40.0]),
    ('bleed: 15pt 3pt 6pt 18pt; size: 12pt 15pt',
     [0, 0, 33, 36],
     [8.0, 5.0, 33.0, 36.0],
     [18.0, 15.0, 30.0, 30.0]),
))
@assert_no_logs
def test_bleed(style, media, bleed, trim):
    fileobj = io.BytesIO()
    FakeHTML(string='''
      <title>Test document</title>
      <style>@page { %s }</style>
      <body>test
    ''' % style).write_pdf(target=fileobj)
    pdf_bytes = fileobj.getvalue()
    assert (
        '/MediaBox [ {} {} {} {} ]'.format(*media).encode('ascii')
        in pdf_bytes)
    assert (
        '/BleedBox [ {} {} {} {} ]'.format(*bleed).encode('ascii')
        in pdf_bytes)
    assert (
        '/TrimBox [ {} {} {} {} ]'.format(*trim).encode('ascii')
        in pdf_bytes)
