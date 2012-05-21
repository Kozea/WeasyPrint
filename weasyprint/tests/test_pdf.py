# coding: utf8
"""
    weasyprint.tests.test_metadata
    ------------------------------

    Test metadata of the document (bookmarks, links and destinations).

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import io

import cairo

from .. import HTML
from ..document import PDFDocument
from .. import pdf
from .testing_utils import assert_no_logs


@assert_no_logs
def test_pdf_parser():
    fileobj = io.BytesIO()
    surface = cairo.PDFSurface(fileobj, 1, 1)
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


def get_metadata(html):
    document = HTML(string=html)._get_document(PDFDocument, [])
    return pdf.gather_metadata(document)


def get_bookmarks(html, structure_only=False):
    (root, bookmarks), links, destinations = get_metadata(html)
    for bookmark in bookmarks:
        if structure_only:
            bookmark.pop('destination')
            bookmark.pop('label')
        else:
            # Eliminate errors of floating point arithmetic
            # (eg. 499.99999999999994 instead of 500)
            p, x, y = bookmark['destination']
            bookmark['destination'] = p, round(x, 6), round(y, 6)
    return root, bookmarks


@assert_no_logs
def test_bookmarks():
    """Test the structure of the document bookmarks.

    Warning: the PDF output of this structure is not tested.

    """
    root, bookmarks = get_bookmarks('''
        <style>
            @page { -weasy-size: 1000pt; margin: 0 }
            * { height: 90pt; margin: 0 0 10pt 0; page-break-inside: auto }
        </style>
        <h1>Title 1</h1>
        <h1>Title 2</h1>
        <div style="margin-left: 50pt"><h2>Title 3</h2></div>
        <h2>Title 4</h2>
        <h3>Title 5<span style="display: block;
                                page-break-before: always"></span></h3>
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
             label='Title 1', destination=(0, 0, 1000)),
        dict(Count=4, First=3, Last=6, Next=7, Parent=0, Prev=1,
             label='Title 2', destination=(0, 0, 900)),
        dict(Count=0, First=None, Last=None, Next=4, Parent=2, Prev=None,
             label='Title 3', destination=(0, 50, 800)),
        dict(Count=1, First=5, Last=5, Next=6, Parent=2, Prev=3,
             label='Title 4', destination=(0, 0, 700)),
        dict(Count=0, First=None, Last=None, Next=None, Parent=4, Prev=None,
             label='Title 5', destination=(0, 0, 600)),
        dict(Count=0, First=None, Last=None, Next=None, Parent=2, Prev=4,
             label='Title 6', destination=(1, 0, 900)),
        dict(Count=2, First=8, Last=8, Next=10, Parent=0, Prev=2,
             label='Title 7', destination=(1, 0, 800)),
        dict(Count=1, First=9, Last=9, Next=None, Parent=7, Prev=None,
             label='Title 8', destination=(1, 0, 700)),
        dict(Count=0, First=None, Last=None, Next=None, Parent=8, Prev=None,
             label='Title 9', destination=(1, 0, 600)),
        dict(Count=1, First=11, Last=11, Next=None, Parent=0, Prev=7,
             label='Title 10', destination=(1, 0, 500)),
        dict(Count=0, First=None, Last=None, Next=None, Parent=10, Prev=None,
             label='Title 11', destination=(1, 0, 400))]

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
