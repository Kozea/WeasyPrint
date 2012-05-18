# coding: utf8
"""
    weasyprint.tests.test_metadata
    ------------------------------

    Test metadata of the document (bookmarks, links and destinations).

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from .. import HTML
from ..document import PDFDocument


def get_bookmarks(html):
    document = HTML(string=html)._get_document(PDFDocument, [])
    root, bookmarks = document._get_bookmarks()
    for bookmark in bookmarks:
        bookmark.pop('destination')
        bookmark.pop('label')
    return root, bookmarks


def test_bookmarks():
    """Test the structure of the document bookmarks.

    Warning: the PDF output of this structure is not tested.

    """
    root, bookmarks = get_bookmarks('''
        <h1>1</h1>
        <h1>2</h1>
        <h2>3</h2>
        <h2>4</h2>
        <h3>5</h3>
        <h2>6</h2>
        <h1>7</h1>
        <h2>8</h2>
        <h3>9</h3>
        <h1>10</h1>
        <h2>11</h2>
    ''')
    assert root == dict(count=11, first=1, last=10)
    assert bookmarks == [
        dict(count=0, first=None, last=None, next=2, parent=0, prev=None),
        dict(count=4, first=3, last=6, next=7, parent=0, prev=1),
        dict(count=0, first=None, last=None, next=4, parent=2, prev=None),
        dict(count=1, first=5, last=5, next=6, parent=2, prev=3),
        dict(count=0, first=None, last=None, next=None, parent=4, prev=None),
        dict(count=0, first=None, last=None, next=None, parent=2, prev=4),
        dict(count=2, first=8, last=8, next=10, parent=0, prev=2),
        dict(count=1, first=9, last=9, next=None, parent=7, prev=None),
        dict(count=0, first=None, last=None, next=None, parent=8, prev=None),
        dict(count=1, first=11, last=11, next=None, parent=0, prev=7),
        dict(count=0, first=None, last=None, next=None, parent=10, prev=None)]

    root, bookmarks = get_bookmarks('''
        <h2>1</h2> level 1
        <h4>2</h4> level 2
        <h2>3</h2> level 1
        <h3>4</h3> level 2
        <h4>5</h4> level 3
    ''')
    assert root == dict(count=5, first=1, last=3)
    assert bookmarks == [
        dict(count=1, first=2, last=2, next=3, parent=0, prev=None),
        dict(count=0, first=None, last=None, next=None, parent=1, prev=None),
        dict(count=2, first=4, last=4, next=None, parent=0, prev=1),
        dict(count=1, first=5, last=5, next=None, parent=3, prev=None),
        dict(count=0, first=None, last=None, next=None, parent=4, prev=None)]

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
    ''')
    assert root == dict(count=9, first=1, last=9)
    assert bookmarks == [
        dict(count=3, first=2, last=3, next=5, parent=0, prev=None),
        dict(count=0, first=None, last=None, next=3, parent=1, prev=None),
        dict(count=1, first=4, last=4, next=None, parent=1, prev=2),
        dict(count=0, first=None, last=None, next=None, parent=3, prev=None),
        dict(count=3, first=6, last=7, next=9, parent=0, prev=1),
        dict(count=0, first=None, last=None, next=7, parent=5, prev=None),
        dict(count=1, first=8, last=8, next=None, parent=5, prev=6),
        dict(count=0, first=None, last=None, next=None, parent=7, prev=None),
        dict(count=0, first=None, last=None, next=None, parent=0, prev=5)]
