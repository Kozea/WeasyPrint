# coding: utf8
"""
    weasyprint.tests.layout
    -----------------------

    Tests for layout, ie. positioning and dimensioning of boxes,
    line breaks, page breaks.

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import math

import pytest

from .testing_utils import FONTS, assert_no_logs, capture_logs, almost_equal
from ..formatting_structure import boxes
from .test_boxes import render_pages as parse

def body_children(page):
    """Take a ``page``  and return its <body>’s children."""
    html, = page.children
    assert html.element_tag == 'html'
    body, = html.children
    assert body.element_tag == 'body'
    return body.children


def outer_area(box):
    """Return the (x, y, w, h) rectangle for the outer area of a box."""
    return (box.position_x, box.position_y,
            box.margin_width(), box.margin_height())


 
@assert_no_logs
def test_page_floating_images_breaks():
    """Test the page breaks."""

    pages = parse('''
        <style>
            @page { size: 100px; margin: 10px }
            img { height: 45px; width:70px; float: left;}
        </style>
        <body>
            <img src=pattern.png>
                    <!-- page break should be here !!! -->
            <img src=pattern.png>
    ''')
    
    assert len(pages) == 2

    page_images = []
    for page in pages:
        images = [_d for _d in page.descendants() if _d.element_tag=='img']
        assert all([img.element_tag == 'img' for img in images])
        assert all([img.position_x == 10 for img in images])
        page_images.append(images)
    positions_y = [[img.position_y for img in images]
                   for images in page_images]
    assert positions_y == [[10], [10]]
 
    
