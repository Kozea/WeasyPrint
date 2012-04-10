# coding: utf8
"""
    weasyprint.tests.test_draw
    --------------------------

    Test the final, drawn results and compare PNG images pixel per pixel.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import contextlib
import os.path
import tempfile
import shutil
import itertools
from io import BytesIO

import pystacia

from ..compat import xrange
from ..utils import ensure_url
from .testing_utils import (
    resource_filename, TestPNGDocument, FONTS, assert_no_logs, capture_logs)


# Short variable names are OK here
# pylint: disable=C0103

_ = b'\xff\xff\xff\xff'  # white
r = b'\xff\x00\x00\xff'  # red
B = b'\x00\x00\xff\xff'  # blue
BYTES_PER_PIXELS = 4
PIXEL_FORMAT = 'rgba(%i, %i, %i, %i)'


def format_pixel(pixels, width, x, y):  # pragma: no cover
    """Return the pixel color as ``#RRGGBB``."""
    start = (y * width + x) * BYTES_PER_PIXELS
    end = start + BYTES_PER_PIXELS
    pixel_bytes = pixels[start:end]
    # Py2/3 compat:
    pixel_ints = tuple(ord(byte) for byte in pixel_bytes.decode('latin1'))
    return PIXEL_FORMAT % pixel_ints


def assert_pixels(name, expected_width, expected_height, expected_lines, html):
    """Helper testing the size of the image and the pixels values."""
    assert len(expected_lines) == expected_height
    assert len(expected_lines[0]) == expected_width * BYTES_PER_PIXELS
    expected_raw = b''.join(expected_lines)
    _doc, lines = html_to_pixels(name, expected_width, expected_height, html)
    assert_pixels_equal(name, expected_width, expected_height, lines,
                        expected_raw)


def assert_same_rendering(expected_width, expected_height, documents):
    """
    Render HTML documents to PNG and check that they render the same,
    pixel-per-pixel.

    Each document is passed as a (name, html_source) tuple.
    """
    lines_list = []

    for name, html in documents:
        _doc, lines = html_to_pixels(
            name, expected_width, expected_height, html)
        lines_list.append((name, lines))

    _name, reference = lines_list[0]
    for name, lines in lines_list[1:]:
        assert_pixels_equal(name, expected_width, expected_height,
                            reference, lines)


def assert_different_renderings(expected_width, expected_height, documents):
    """
    Render HTML documents to PNG and check that no two documents render
    the same.

    Each document is passed as a (name, html_source) tuple.
    """
    lines_list = []

    for name, html in documents:
        _doc, lines = html_to_pixels(
            name, expected_width, expected_height, html)
        lines_list.append((name, lines))

    for i, (name_1, lines_1) in enumerate(lines_list):
        for name_2, lines_2 in lines_list[i + 1:]:
            if lines_1 == lines_2:  # pragma: no cover
                # Same as "assert lines_1 != lines_2" but the output of
                # the assert hook would be gigantic and useless.
                assert False, '%s and %s are the same' % (name_1, name_2)


def write_png(basename, lines, width, height):  # pragma: no cover
    """Take a pixel matrix and write a PNG file."""
    directory = os.path.join(os.path.dirname(__file__), 'test_results')
    if not os.path.isdir(directory):
        os.mkdir(directory)
    filename = os.path.join(directory, basename + '.png')

    with contextlib.closing(pystacia.read_raw(
            lines, 'rgba', width, height, depth=8)) as image:
        image.write(filename)


def html_to_pixels(name, expected_width, expected_height, html):
    """
    Render an HTML document to PNG, checks its size and return pixel data.

    Also return the document to aid debugging.
    """
    document = TestPNGDocument(html,
        # Dummy filename, but in the right directory.
        base_url=resource_filename('<test>'))
    lines = document_to_pixels(document, name, expected_width, expected_height)
    return document, lines


def document_to_pixels(document, name, expected_width, expected_height):
    """
    Render an HTML document to PNG, checks its size and return pixel data.
    """
    file_like = BytesIO()
    document.write_to(file_like)
    assert len(document.pages) == 1

    with contextlib.closing(pystacia.read_blob(file_like.getvalue())) as image:
        assert image.size == (expected_width, expected_height), name
        raw = image.get_raw('rgba')['raw']
        assert len(raw) == expected_width * expected_height * BYTES_PER_PIXELS
        return raw


def assert_pixels_equal(name, width, height, lines, expected_lines):
    """
    Take 2 matrices of height by width pixels and assert that they
    are the same.
    """
    if lines != expected_lines:  # pragma: no cover
        write_png(name + '.expected', expected_lines, width, height)
        write_png(name, lines, width, height)
        for y in xrange(height):
            for x in xrange(width):
                pixel = format_pixel(lines, width, x, y)
                expected_pixel = format_pixel(expected_lines, width, x, y)
                assert pixel == expected_pixel , (
                    'Pixel (%i, %i) in %s: expected %s, got %s' % (
                    x, y, name, expected_pixel, pixel))


@assert_no_logs
def test_canvas_background():
    """Test the background applied on ``<html>`` and/or ``<body>`` tags."""
    assert_pixels('all_blue', 10, 10, (10 * [10 * B]), '''
        <style>
            @page { -weasy-size: 10px }
            /* body’s background propagates to the whole canvas */
            body { margin: 2px; background: #00f; height: 5px }
        </style>
        <body>
    ''')

    assert_pixels('blocks', 10, 10, [
        r+r+r+r+r+r+r+r+r+r,
        r+r+r+r+r+r+r+r+r+r,
        r+r+B+B+B+B+B+B+r+r,
        r+r+B+B+B+B+B+B+r+r,
        r+r+B+B+B+B+B+B+r+r,
        r+r+B+B+B+B+B+B+r+r,
        r+r+B+B+B+B+B+B+r+r,
        r+r+r+r+r+r+r+r+r+r,
        r+r+r+r+r+r+r+r+r+r,
        r+r+r+r+r+r+r+r+r+r,
     ], '''
        <style>
            @page { -weasy-size: 10px }
            /* html’s background propagates to the whole canvas */
            html { padding: 1px; background: #f00 }
            /* html has a background, so body’s does not propagate */
            body { margin: 1px; background: #00f; height: 5px }
        </style>
        <body>
    ''')


@assert_no_logs
def test_background_image():
    """Test background images."""
    # pattern.png looks like this:

    #    r+B+B+B,
    #    B+B+B+B,
    #    B+B+B+B,
    #    B+B+B+B,

    for name, css, pixels in [
        ('repeat', '', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+r+B+B+B+r+B+B+B+r+B+_+_,
            _+_+B+B+B+B+B+B+B+B+B+B+_+_,
            _+_+B+B+B+B+B+B+B+B+B+B+_+_,
            _+_+B+B+B+B+B+B+B+B+B+B+_+_,
            _+_+r+B+B+B+r+B+B+B+r+B+_+_,
            _+_+B+B+B+B+B+B+B+B+B+B+_+_,
            _+_+B+B+B+B+B+B+B+B+B+B+_+_,
            _+_+B+B+B+B+B+B+B+B+B+B+_+_,
            _+_+r+B+B+B+r+B+B+B+r+B+_+_,
            _+_+B+B+B+B+B+B+B+B+B+B+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('repeat_x', 'repeat-x', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+r+B+B+B+r+B+B+B+r+B+_+_,
            _+_+B+B+B+B+B+B+B+B+B+B+_+_,
            _+_+B+B+B+B+B+B+B+B+B+B+_+_,
            _+_+B+B+B+B+B+B+B+B+B+B+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('repeat_y', 'repeat-y', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+r+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+r+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+r+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),

        ('left_top', 'no-repeat 0 0%', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+r+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('center_top', 'no-repeat 50% 0px', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+r+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('right_top', 'no-repeat 6px top', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+r+B+B+B+_+_,
            _+_+_+_+_+_+_+_+B+B+B+B+_+_,
            _+_+_+_+_+_+_+_+B+B+B+B+_+_,
            _+_+_+_+_+_+_+_+B+B+B+B+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('left_center', 'no-repeat left center', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+r+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('center_left', 'no-repeat center left', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+r+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('center_center', 'no-repeat 3px 3px', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+r+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('right_center', 'no-repeat 100% 50%', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+r+B+B+B+_+_,
            _+_+_+_+_+_+_+_+B+B+B+B+_+_,
            _+_+_+_+_+_+_+_+B+B+B+B+_+_,
            _+_+_+_+_+_+_+_+B+B+B+B+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),

        ('left_bottom', 'no-repeat 0% bottom', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+r+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('center_bottom', 'no-repeat center 6px', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+r+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('bottom_center', 'no-repeat bottom center', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+r+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('right_bottom', 'no-repeat 6px 100%', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+r+B+B+B+_+_,
            _+_+_+_+_+_+_+_+B+B+B+B+_+_,
            _+_+_+_+_+_+_+_+B+B+B+B+_+_,
            _+_+_+_+_+_+_+_+B+B+B+B+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),

        ('repeat_x_1px_2px', 'repeat-x 1px 2px', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+B+r+B+B+B+r+B+B+B+r+_+_,
            _+_+B+B+B+B+B+B+B+B+B+B+_+_,
            _+_+B+B+B+B+B+B+B+B+B+B+_+_,
            _+_+B+B+B+B+B+B+B+B+B+B+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('repeat_y_2px_1px', 'repeat-y 2px 1px', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+B+B+B+B+_+_+_+_+_+_,
            _+_+_+_+r+B+B+B+_+_+_+_+_+_,
            _+_+_+_+B+B+B+B+_+_+_+_+_+_,
            _+_+_+_+B+B+B+B+_+_+_+_+_+_,
            _+_+_+_+B+B+B+B+_+_+_+_+_+_,
            _+_+_+_+r+B+B+B+_+_+_+_+_+_,
            _+_+_+_+B+B+B+B+_+_+_+_+_+_,
            _+_+_+_+B+B+B+B+_+_+_+_+_+_,
            _+_+_+_+B+B+B+B+_+_+_+_+_+_,
            _+_+_+_+r+B+B+B+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),

        ('fixed', 'no-repeat fixed', [
            # The image is actually here:
            #######
            _+_+_+_+_+_+_+_+_+_+_+_+_+_, #
            _+_+_+_+_+_+_+_+_+_+_+_+_+_, #
            _+_+B+B+_+_+_+_+_+_+_+_+_+_, #
            _+_+B+B+_+_+_+_+_+_+_+_+_+_, #
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('fixed_right', 'no-repeat fixed right 3px', [
                                #######
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+r+B+_+_, #
            _+_+_+_+_+_+_+_+_+_+B+B+_+_, #
            _+_+_+_+_+_+_+_+_+_+B+B+_+_, #
            _+_+_+_+_+_+_+_+_+_+B+B+_+_, #
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('fixed_center_center', 'no-repeat fixed 50% center', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+r+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
    ]:
        assert_pixels('background_' + name, 14, 16, pixels, '''
            <style>
                @page { -weasy-size: 14px 16px }
                html { background: #fff }
                body { margin: 2px; height: 10px;
                       background: url(pattern.png) %s }
                p { background: none }
            </style>
            <body>
            <p>&nbsp;
        ''' % (css,))


@assert_no_logs
def test_background_origin():
    """Test the background-origin property."""
    def test_value(value, pixels, css=None):
        assert_pixels('background_origin_' + value, 12, 12, pixels, '''
            <style>
                @page { -weasy-size: 12px }
                html { background: #fff }
                body { margin: 1px; padding: 1px; height: 6px;
                       border: 1px solid  transparent;
                       background: url(pattern.png) bottom right no-repeat;
                       background-origin: %s }
            </style>
            <body>
        ''' % (css or value,))

    test_value('border-box', [
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+r+B+B+B+_,
        _+_+_+_+_+_+_+B+B+B+B+_,
        _+_+_+_+_+_+_+B+B+B+B+_,
        _+_+_+_+_+_+_+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
    ])
    test_value('padding-box', [
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+r+B+B+B+_+_,
        _+_+_+_+_+_+B+B+B+B+_+_,
        _+_+_+_+_+_+B+B+B+B+_+_,
        _+_+_+_+_+_+B+B+B+B+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
    ])
    test_value('content-box', [
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+r+B+B+B+_+_+_,
        _+_+_+_+_+B+B+B+B+_+_+_,
        _+_+_+_+_+B+B+B+B+_+_+_,
        _+_+_+_+_+B+B+B+B+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
    ])

    test_value('border-box_clip', [
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+r+B+_+_+_,
        _+_+_+_+_+_+_+B+B+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
    ], css='border-box; background-clip: content-box')



@assert_no_logs
def test_background_clip():
    """Test the background-clip property."""
    def test_value(value, pixels):
        assert_pixels('background_clip_' + value, 8, 8, pixels, '''
            <style>
                @page { -weasy-size: 8px }
                html { background: #fff }
                body { margin: 1px; padding: 1px; height: 2px;
                       border: 1px solid  transparent;
                       background: #00f; background-clip : %s }
            </style>
            <body>
        ''' % (value,))

    test_value('border-box', [
        _+_+_+_+_+_+_+_,
        _+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+_,
        _+_+_+_+_+_+_+_,
    ])
    test_value('padding-box', [
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
    ])
    test_value('content-box', [
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+B+B+_+_+_,
        _+_+_+B+B+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
    ])


@assert_no_logs
def test_background_size():
    """Test the background-size property."""
    assert_pixels('background_size', 12, 12, [
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+r+r+B+B+B+B+B+B+_,
        _+_+_+r+r+B+B+B+B+B+B+_,
        _+_+_+B+B+B+B+B+B+B+B+_,
        _+_+_+B+B+B+B+B+B+B+B+_,
        _+_+_+B+B+B+B+B+B+B+B+_,
        _+_+_+B+B+B+B+B+B+B+B+_,
        _+_+_+B+B+B+B+B+B+B+B+_,
        _+_+_+B+B+B+B+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { -weasy-size: 12px }
            html { background: #fff }
            body { margin: 1px; height: 10px;
                   /* Use nearest neighbor algorithm for image resizing: */
                   -weasy-image-rendering: optimizeSpeed;
                   background: url(pattern.png) bottom right no-repeat;
                   background-size: 8px }
        </style>
        <body>
    ''')

    assert_pixels('background_size_auto', 12, 12, [
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+r+B+B+B+_,
        _+_+_+_+_+_+_+B+B+B+B+_,
        _+_+_+_+_+_+_+B+B+B+B+_,
        _+_+_+_+_+_+_+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { -weasy-size: 12px }
            html { background: #fff }
            body { margin: 1px; height: 10px;
                   /* Use nearest neighbor algorithm for image resizing: */
                   -weasy-image-rendering: optimizeSpeed;
                   background: url(pattern.png) bottom right no-repeat;
                   background-size: auto }
        </style>
        <body>
    ''')

    assert_pixels('background_size_contain', 14, 10, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+r+r+B+B+B+B+B+B+_+_+_+_+_,
        _+r+r+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { -weasy-size: 14px 10px }
            html { background: #fff }
            body { margin: 1px; height: 8px;
                   /* Use nearest neighbor algorithm for image resizing: */
                   -weasy-image-rendering: optimizeSpeed;
                   background: url(pattern.png) no-repeat;
                   background-size: contain }
        </style>
        <body>
    ''')

    assert_pixels('background_size_mixed', 14, 10, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+r+r+B+B+B+B+B+B+_+_+_+_+_,
        _+r+r+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { -weasy-size: 14px 10px }
            html { background: #fff }
            body { margin: 1px; height: 8px;
                   /* Use nearest neighbor algorithm for image resizing: */
                   -weasy-image-rendering: optimizeSpeed;
                   background: url(pattern.png) no-repeat;
                   background-size: auto 8px;
                   clip: auto; /* no-op to cover more validation */ }
        </style>
        <body>
    ''')

    assert_pixels('background_size_double', 14, 10, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+r+r+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { -weasy-size: 14px 10px }
            html { background: #fff }
            body { margin: 1px; height: 8px;
                   /* Use nearest neighbor algorithm for image resizing: */
                   -weasy-image-rendering: optimizeSpeed;
                   background: url(pattern.png) no-repeat;
                   background-size: 8px 4px;
                   clip: auto; /* no-op to cover more validation */ }
        </style>
        <body>
    ''')

    assert_pixels('background_size_cover', 14, 10, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+r+r+r+B+B+B+B+B+B+B+B+B+_,
        _+r+r+r+B+B+B+B+B+B+B+B+B+_,
        _+r+r+r+B+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { -weasy-size: 14px 10px }
            html { background: #fff }
            body { margin: 1px; height: 8px;
                   /* Use nearest neighbor algorithm for image resizing: */
                   -weasy-image-rendering: optimizeSpeed;
                   background: url(pattern.png) no-repeat;
                   background-size: cover }
        </style>
        <body>
    ''')


@assert_no_logs
def test_list_style_image():
    """Test images as list markers."""
    for position, pixels in [
        ('outside', [
        #   ++++++++++++++      ++++  <li> horizontal margins: 7px 2px
        #                 ######      <li> width: 12 - 7 - 2 = 3px
        #               --            list marker margin: 0.5em = 2px
        #       ********              list marker image is 4px wide
            _+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_,
            _+_+r+B+B+B+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('inside', [
        #   ++++++++++++++      ++++  <li> horizontal margins: 7px 2px
        #                 ######      <li> width: 12 - 7 - 2 = 3px
        #                 ********    list marker image is 4px wide: overflow
            _+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+r+B+B+B+_,
            _+_+_+_+_+_+_+B+B+B+B+_,
            _+_+_+_+_+_+_+B+B+B+B+_,
            _+_+_+_+_+_+_+B+B+B+B+_,
            _+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_,
        ])
    ]:
        assert_pixels('list_style_image_' + position, 12, 10, pixels, '''
            <style>
                @page { -weasy-size: 12px 10px }
                body { margin: 0; background: white; font-family: %s }
                ul { margin: 2px 2px 0 7px; list-style: url(pattern.png) %s;
                     font-size: 2px }
            </style>
            <ul><li></li></ul>
        ''' % (FONTS, position))

    assert_pixels('list_style_none', 10, 10, [
            _+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_,
        ], '''
            <style>
                @page { -weasy-size: 10px }
                body { margin: 0; background: white; font-family: %s }
                ul { margin: 0 0 0 5px; list-style: none; font-size: 2px; }
            </style>
            <ul><li>
        ''' % (FONTS,))


@assert_no_logs
def test_images():
    """Test images sizes, positions and pixels."""
    centered_image = [
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+r+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
    ]
    # JPG is lossy...
    b = b'\x00\x00\xfe\xff'
    blue_image = [
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+b+b+b+b+_+_,
        _+_+b+b+b+b+_+_,
        _+_+b+b+b+b+_+_,
        _+_+b+b+b+b+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
    ]
    no_image = [
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
    ]
    for filename, image in [
            ('pattern.svg', centered_image),
            ('pattern.png', centered_image),
            ('pattern.palette.png', centered_image),
            ('pattern.gif', centered_image),
            ('blue.jpg', blue_image)]:
        assert_pixels('inline_image_' + filename, 8, 8, image, '''
            <style>
                @page { -weasy-size: 8px }
                body { margin: 2px 0 0 2px; background: #fff }
            </style>
            <div><img src="%s"></div>
        ''' % filename)
    assert_pixels('block_image', 8, 8, centered_image, '''
        <style>
            @page { -weasy-size: 8px }
            body { margin: 0; background: #fff }
            img { display: block; margin: 2px auto 0 }
        </style>
        <div><img src="pattern.png"></div>
    ''')
    with capture_logs() as logs:
        assert_pixels('image_not_found', 8, 8, no_image, '''
            <style>
                @page { -weasy-size: 8px }
                body { margin: 0; background: #fff }
                img { display: block; margin: 2px auto 0 }
            </style>
            <div><img src="inexistent1.png" alt=""></div>
        ''')
    assert len(logs) == 1
    assert 'WARNING: Error for image' in logs[0]
    assert 'inexistent1.png' in logs[0]
    assert_pixels('image_no_src', 8, 8, no_image, '''
        <style>
            @page { -weasy-size: 8px }
            body { margin: 0; background: #fff }
            img { display: block; margin: 2px auto 0 }
        </style>
        <div><img alt=""></div>
    ''')
    with capture_logs() as logs:
        assert_same_rendering(200, 30, [
            ('image_alt_text_reference', '''
                <style>
                    @page { -weasy-size: 200px 30px }
                    body { margin: 0; background: #fff }
                </style>
                <div>Hello, world!</div>
            '''),
            ('image_alt_text_not_found', '''
                <style>
                    @page { -weasy-size: 200px 30px }
                    body { margin: 0; background: #fff }
                </style>
                <div><img src="inexistent2.png" alt="Hello, world!"></div>
            '''),
            ('image_alt_text_no_src', '''
                <style>
                    @page { -weasy-size: 200px 30px }
                    body { margin: 0; background: #fff }
                </style>
                <div><img alt="Hello, world!"></div>
            '''),
        ])
    assert len(logs) == 1
    assert 'WARNING: Error for image' in logs[0]
    assert 'inexistent2.png' in logs[0]


@assert_no_logs
def test_visibility():
    source = '''
        <style>
            @page { -weasy-size: 12px 7px }
            body { background: #fff; font: 1px/1 serif }
            img { margin: 1px 0 0 1px; }
            %(extra_css)s
        </style>
        <div>
            <img src="pattern.png">
            <span><img src="pattern.png"></span>
        </div>
    '''
    assert_pixels('visibility_reference', 12, 7, [
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+r+B+B+B+_+r+B+B+B+_+_,
        _+B+B+B+B+_+B+B+B+B+_+_,
        _+B+B+B+B+_+B+B+B+B+_+_,
        _+B+B+B+B+_+B+B+B+B+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
    ], source % {'extra_css': ''})

    assert_pixels('visibility_hidden', 12, 7, [
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
    ], source % {'extra_css': 'div { visibility: hidden }'})

    assert_pixels('visibility_mixed', 12, 7, [
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+r+B+B+B+_+_,
        _+_+_+_+_+_+B+B+B+B+_+_,
        _+_+_+_+_+_+B+B+B+B+_+_,
        _+_+_+_+_+_+B+B+B+B+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
    ], source % {'extra_css': '''div { visibility: hidden }
                                 span { visibility: visible } '''})


@assert_no_logs
def test_tables():
    source = '''
        <style>
            @page { -weasy-size: 28px }
            html { background: #fff; }
            table { margin: 1px; padding: 1px; border-spacing: 1px;
                    border: 1px solid transparent }
            td { width: 2px; height: 2px; padding: 1px;
                 border: 1px solid transparent }
            %(extra_css)s
        </style>
        <table>
            <colgroup>
                <col>
                <col>
            </colgroup>
            <col>
            <thead>
                <tr>
                    <td></td>
                    <td rowspan=2></td>
                    <td></td>
                </tr>
                <tr>
                    <td colspan=2></td>
                    <td></td>
                </tr>
            </thead>
            <tr>
                <td></td>
                <td></td>
            </tr>
        </table>
    '''
    r = b'\xff\x7f\x7f\xff'  # rgba(255, 0, 0, 0.5) above #fff
    R = b'\xff\x3f\x3f\xff'  # r above r above #fff
    assert_pixels('table_borders', 28, 28, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+B+_,
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+B+_,
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+B+_,
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+_+_+_+_+r+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+r+R+r+r+r+r+R+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+r+_+_+_+_+_+_+r+_+_+_+_+R+_+r+_+_+_+_+r+_+_+B+_,
        _+B+_+_+r+_+_+_+_+_+_+r+_+_+_+_+R+_+r+_+_+_+_+r+_+_+B+_,
        _+B+_+_+r+_+_+_+_+_+_+r+_+_+_+_+R+_+r+_+_+_+_+r+_+_+B+_,
        _+B+_+_+r+_+_+_+_+_+_+r+_+_+_+_+R+_+r+_+_+_+_+r+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+r+R+R+R+R+R+R+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ], source % {'extra_css': '''
        table { border-color: #00f; table-layout: fixed }
        td { border-color: rgba(255, 0, 0, 0.5) }
    '''})

    assert_pixels('table_td_backgrounds', 28, 28, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+r+R+R+R+R+R+R+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+r+R+R+R+R+R+R+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+r+R+R+R+R+R+R+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+r+R+R+R+R+R+R+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+r+R+R+R+R+R+R+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+r+R+R+R+R+R+R+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ], source % {'extra_css': '''
        table { border-color: #00f; table-layout: fixed }
        td { background: rgba(255, 0, 0, 0.5) }
    '''})

    g = b'\x7f\xff\x7f\xff'  # rgba(0, 255, 0, 0.5) above #fff
    G = b'\x7f\xbf\x3f\xff'  # g above r above #fff
                                         # Not the same as r above g above #fff
    assert_pixels('table_column_backgrounds', 28, 28, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+r+G+G+G+G+G+G+_+g+g+g+g+g+g+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+r+G+G+G+G+G+G+_+g+g+g+g+g+g+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+r+G+G+G+G+G+G+_+g+g+g+g+g+g+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+r+G+G+G+G+G+G+_+g+g+g+g+g+g+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+r+G+G+G+G+G+G+_+g+g+g+g+g+g+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+r+G+G+G+G+G+G+_+g+g+g+g+g+g+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+r+G+G+G+G+G+G+_+g+g+g+g+g+g+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+r+G+G+G+G+G+G+_+g+g+g+g+g+g+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+r+G+G+G+G+G+G+_+g+g+g+g+g+g+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+r+G+G+G+G+G+G+_+g+g+g+g+g+g+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+r+G+G+G+G+G+G+_+g+g+g+g+g+g+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+r+G+G+G+G+G+G+_+g+g+g+g+g+g+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+r+G+G+G+G+G+G+_+g+g+g+g+g+g+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+r+G+G+G+G+G+G+_+g+g+g+g+g+g+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+r+G+G+G+G+G+G+_+g+g+g+g+g+g+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+r+G+G+G+G+G+G+_+g+g+g+g+g+g+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+r+G+G+G+G+G+G+_+g+g+g+g+g+g+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+r+G+G+G+G+G+G+_+g+g+g+g+g+g+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+r+G+G+G+G+G+G+_+g+g+g+g+g+g+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+r+G+G+G+G+G+G+_+g+g+g+g+g+g+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ], source % {'extra_css': '''
        table { border-color: #00f; table-layout: fixed }
        colgroup { background: rgba(255, 0, 0, 0.5) }
        col { background: rgba(0, 255, 0, 0.5) }
    '''})

    assert_pixels('table_row_backgrounds', 28, 28, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+_+_+B+_,
        _+B+_+_+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+G+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+_+_+B+_,
        _+B+_+_+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+_+_+B+_,
        _+B+_+_+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+_+_+B+_,
        _+B+_+_+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+_+_+B+_,
        _+B+_+_+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+_+_+B+_,
        _+B+_+_+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ], source % {'extra_css': '''
        table { border-color: #00f; table-layout: fixed }
        thead { background: rgba(255, 0, 0, 0.5) }
        tr { background: rgba(0, 255, 0, 0.5) }
    '''})



@assert_no_logs
def test_before_after():
    assert_same_rendering(300, 30, [
        ('pseudo_before', '''
            <style>
                @page { -weasy-size: 300px 30px }
                body { margin: 0; background: #fff }
                a[href]:before { content: '[' '' attr(href) '] ' }
            </style>
            <p><a href="some url">some content</p>
        '''),
        ('pseudo_before_reference', '''
            <style>
                @page { -weasy-size: 300px 30px }
                body { margin: 0; background: #fff }
            </style>
            <p><a href="another url">[some url] some content</p>
        ''')
    ])

    assert_same_rendering(500, 30, [
        ('pseudo_quotes', '''
            <style>
                @page { -weasy-size: 500px 30px }
                body { margin: 0; background: #fff; quotes: '«' '»' '“' '”' }
                q:before { content: open-quote ' '}
                q:after { content: ' ' close-quote }
            </style>
            <p><q>Lorem ipsum <q>dolor</q> sit amet</q></p>
        '''),
        ('pseudo_quotes_reference', '''
            <style>
                @page { -weasy-size: 500px 30px }
                body { margin: 0; background: #fff }
            </style>
            <p>« Lorem ipsum “ dolor ” sit amet »</p>
        ''')
    ])

    assert_same_rendering(100, 30, [
        ('pseudo_url', '''
            <style>
                @page { -weasy-size: 100px 30px }
                body { margin: 0; background: #fff; }
                p:before { content: 'a' url(pattern.png) 'b'}
            </style>
            <p>c</p>
        '''),
        ('pseudo_url_reference', '''
            <style>
                @page { -weasy-size: 100px 30px }
                body { margin: 0; background: #fff }
            </style>
            <p>a<img src="pattern.png" alt="Missing image">bc</p>
        ''')
    ])


@assert_no_logs
def test_borders():
    """Test the rendering of borders"""
    source = '''
        <style>
            @page { -weasy-size: 140px 110px }
            html { background: #fff }
            body { margin: 10px; width: 100px; height: 70px;
                   border: 10px %(border_style)s blue }
        </style>
        <body>
    '''

    # Do not test the exact rendering of earch border style but at least
    # check that they do not do the same.
    assert_different_renderings(140, 110, [
        ('border_' + border_style, source % {'border_style': border_style})
        for border_style in [
            'none', 'solid', 'dashed', 'dotted', 'double',
            'inset', 'outset', 'groove', 'ridge',
        ]
    ])

    width = 140
    height = 110
    margin = 10
    border = 10
    solid_pixels = [[_] * width for y in xrange(height)]
    for x in xrange(margin, width - margin):
        for y in itertools.chain(
                range(margin, margin + border),
                range(height - margin - border, height - margin)):
            solid_pixels[y][x] = B
    for y in xrange(margin, height - margin):
        for x in itertools.chain(
                range(margin, margin + border),
                range(width - margin - border, width - margin)):
            solid_pixels[y][x] = B
    solid_pixels = [b''.join(line) for line in solid_pixels]
    assert_pixels(
        'border_solid', 140, 110, solid_pixels,
        source % {'border_style': 'solid'}
    )


@assert_no_logs
def test_margin_boxes():
    """Test the rendering of margin boxes"""
    _ = b'\xff\xff\xff\xff'  # white
    R = b'\xff\x00\x00\xff'  # red
    G = b'\x00\xff\x00\xff'  # green
    B = b'\x00\x00\xff\xff'  # blue
    g = b'\x00\x80\x00\xff'  # half green
    b = b'\x00\x00\x80\xff'  # half blue
    assert_pixels('margin_boxes', 15, 15, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+G+G+G+_+_+_+_+_+_+B+B+B+B+_,
        _+G+G+G+_+_+_+_+_+_+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+R+R+R+R+_+_+_+_+_+_,
        _+_+_+_+_+R+R+R+R+_+_+_+_+_+_,
        _+_+_+_+_+R+R+R+R+_+_+_+_+_+_,
        _+_+_+_+_+R+R+R+R+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+b+b+b+_+_+_+_+_+_+g+g+g+g+_,
        _+b+b+b+_+_+_+_+_+_+g+g+g+g+_,
        _+b+b+b+_+_+_+_+_+_+g+g+g+g+_,
        _+b+b+b+_+_+_+_+_+_+g+g+g+g+_,
        _+b+b+b+_+_+_+_+_+_+g+g+g+g+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            html { height: 100% }
            body { background: #f00; height: 100% }
            @page {
                -weasy-size: 15px;
                margin: 4px 6px 7px 5px;
                background: white;

                @top-left-corner {
                    margin: 1px;
                    content: " ";
                    background: #0f0;
                }
                @top-right-corner {
                    margin: 1px;
                    content: " ";
                    background: #00f;
                }
                @bottom-right-corner {
                    margin: 1px;
                    content: " ";
                    background: #008000;
                }
                @bottom-left-corner {
                    margin: 1px;
                    content: " ";
                    background: #000080;
                }
            }
        </style>
        <body>
    ''')


@assert_no_logs
def test_unicode():
    """Test non-ASCII filenames (URLs)"""
    text = 'I løvë Unicode'
    style = '''
        @page {
            -weasy-size: 200px 50px;
        }
        p { color: blue }
    '''
    _doc, expected_lines = html_to_pixels('unicode_reference', 200, 50, '''
        <style>{0}</style>
        <p><img src="pattern.png"> {1}</p>
    '''.format(style, text))

    temp = tempfile.mkdtemp(prefix=text + '-')
    try:
        stylesheet = os.path.join(temp, 'style.css')
        image = os.path.join(temp, 'pattern.png')
        html = os.path.join(temp, 'doc.html')
        with open(stylesheet, 'wb') as fd:
            fd.write(style.encode('utf8'))
        with open(resource_filename('pattern.png'), 'rb') as fd:
            image_content = fd.read()
        with open(image, 'wb') as fd:
            fd.write(image_content)
        with open(html, 'wb') as fd:
            html_content = '''
                <link rel=stylesheet href="{0}">
                <p><img src="{1}"> {2}</p>
            '''.format(
                ensure_url(stylesheet), ensure_url(image), text
            )
            fd.write(html_content.encode('utf8'))

        # TODO: change this back to actually read from a file
        document = TestPNGDocument(html_content)
        lines = document_to_pixels(document, 'unicode', 200, 50)
        assert_pixels_equal('unicode', 200, 50, lines, expected_lines)
    finally:
        shutil.rmtree(temp)


@assert_no_logs
def test_overflow():
    """Test the overflow property."""
    # See test_images
    assert_pixels('inline_image_overflow', 8, 8, [
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+r+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { -weasy-size: 8px }
            body { margin: 2px 0 0 2px; background: #fff }
            div { height: 2px; overflow: hidden }
        </style>
        <div><img src="pattern.png"></div>
    ''')

    # <body> is only 1px high, but its overflow is propageted to the viewport
    # ie. the padding edge of the page box.
    assert_pixels('inline_image_viewport_overflow', 8, 8, [
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+r+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { -weasy-size: 8px; background: #fff;
                    margin: 2px;
                    padding-bottom: 2px;
                    border-bottom: 1px transparent solid; }
            body { height: 1px;
                   overflow: hidden }
        </style>
        <div><img src="pattern.png"></div>
    ''')


@assert_no_logs
def test_clip():
    """Test the clip property."""
    num = [0]
    def clip(css, pixels):
        num[0] += 1
        name = 'background_repeat_clipped_%s' % num[0]
        assert_pixels(name, 14, 16, pixels, '''
            <style>
                @page { -weasy-size: 14px 16px; background: #fff }
                div { margin: 1px; height: 10px;
                      border: 1px green solid;
                      background: url(pattern.png);
                      clip: rect(%s); }
            </style>
            <div>
        ''' % (css,))

    print('test_draw.test_clip() is known to fail with cairo 1.10, '
          'try with 1.12.')

    g = b'\x00\x80\x00\xff'  # green
    clip('5px, 5px, 9px, auto', [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+r+B+B+B+r+B+g+_,
        _+_+_+_+_+_+B+B+B+B+B+B+g+_,
        _+_+_+_+_+_+B+B+B+B+B+B+g+_,
        _+_+_+_+_+_+B+B+B+B+B+B+g+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,

    ])
    clip('5px, 5px, auto, 10px', [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+r+B+B+B+r+_+_+_,
        _+_+_+_+_+_+B+B+B+B+B+_+_+_,
        _+_+_+_+_+_+B+B+B+B+B+_+_+_,
        _+_+_+_+_+_+B+B+B+B+B+_+_+_,
        _+_+_+_+_+_+r+B+B+B+r+_+_+_,
        _+_+_+_+_+_+B+B+B+B+B+_+_+_,
        _+_+_+_+_+_+g+g+g+g+g+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,

    ])
    clip('5px, auto, 9px, 10px', [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+g+r+B+B+B+r+B+B+B+r+_+_+_,
        _+g+B+B+B+B+B+B+B+B+B+_+_+_,
        _+g+B+B+B+B+B+B+B+B+B+_+_+_,
        _+g+B+B+B+B+B+B+B+B+B+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,

    ])
    clip('auto, 5px, 9px, 10px', [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+g+g+g+g+g+_+_+_,
        _+_+_+_+_+_+r+B+B+B+r+_+_+_,
        _+_+_+_+_+_+B+B+B+B+B+_+_+_,
        _+_+_+_+_+_+B+B+B+B+B+_+_+_,
        _+_+_+_+_+_+B+B+B+B+B+_+_+_,
        _+_+_+_+_+_+r+B+B+B+r+_+_+_,
        _+_+_+_+_+_+B+B+B+B+B+_+_+_,
        _+_+_+_+_+_+B+B+B+B+B+_+_+_,
        _+_+_+_+_+_+B+B+B+B+B+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,

    ])



@assert_no_logs
def test_opacity():
    """Test the opacity property."""
    template = '''
        <style>
            @page { -weasy-size: 200px 60px }
            body { margin: 0; background: #fff }
        </style>
        %s
    '''
    assert_same_rendering(200, 60, [
        ('opacity_0_reference', template % '''
            <div>Hello, world!</div>
            <div style="opacity: 0">Lorem ipsum</div>
        '''),
        ('opacity_0', template % '''
            <div>Hello, world!</div>
        '''),
    ])
    assert_same_rendering(200, 60, [
        ('opacity_color_reference', template % '''
            <div style="color: rgb(102, 102, 102)">Hello, world!</div>
        '''),
        ('opacity_color', template % '''
            <div style="color: black; opacity: 0.6">Hello, world!</div>
        '''),
    ])
    assert_same_rendering(200, 60, [
        ('opacity_multiplied_reference', template % '''
            <div style="color: transparent;
                background: rgb(102, 102, 102)">Hello, world!</div>
        '''),
        ('opacity_multiplied', template % '''
            <div style="color: transparent;
                background: black; opacity: 0.6">Hello, world!</div>
        '''),
        ('opacity_multiplied_2', template % '''
            <div style="opacity: 0.666666">
            <div style="color: transparent;
                background: black; opacity: 0.9">Hello, world!</div>
        '''),  #  0.9 * 0.666666 == 0.6
    ])


@assert_no_logs
def test_2d_transform():
    """Test 2D transformations."""
    assert_pixels('image_rotate90', 8, 8, [
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+B+B+B+r+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { -weasy-size: 8px; margin: 2px; background: #fff; }
            div { -weasy-transform: rotate(90deg); }
        </style>
        <div><img src="pattern.png"></div>
    ''')

    assert_pixels('image_reflection', 8, 8, [
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+B+B+B+r+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { -weasy-size: 8px; margin: 2px; background: #fff; }
            div { -weasy-transform: matrix(-1, 0, 0, 1, 0, 0); }
        </style>
        <div><img src="pattern.png"></div>
    ''')

    assert_pixels('image_translate', 8, 8, [
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+r+B+B+B+_,
        _+_+_+B+B+B+B+_,
        _+_+_+B+B+B+B+_,
        _+_+_+B+B+B+B+_,
    ], '''
        <style>
            @page { -weasy-size: 8px; margin: 2px; background: #fff; }
            div { -weasy-transform: translate(1px, 2px); }
        </style>
        <div><img src="pattern.png"></div>
    ''')

    assert_pixels('image_translate_percentage', 8, 8, [
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+r+B+B+B+_,
        _+_+_+B+B+B+B+_,
        _+_+_+B+B+B+B+_,
        _+_+_+B+B+B+B+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { -weasy-size: 8px; margin: 2px; background: #fff; }
            div { -weasy-transform: translate(25%, 0); }
        </style>
        <div><img src="pattern.png"></div>
    ''')

    assert_pixels('image_translateX', 8, 8, [
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+r+B+B,
        _+_+_+_+_+B+B+B,
        _+_+_+_+_+B+B+B,
        _+_+_+_+_+B+B+B,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { -weasy-size: 8px; margin: 2px; background: #fff; }
            div { -weasy-transform: translateX(0.25em); font-size: 12px; }
        </style>
        <div><img src="pattern.png"></div>
    ''')

    assert_pixels('image_translateY', 8, 8, [
        _+_+_+_+_+_+_+_,
        _+_+r+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { -weasy-size: 8px; margin: 2px; background: #fff; }
            div { -weasy-transform: translateY(-1px); }
        </style>
        <div><img src="pattern.png"></div>
    ''')

    assert_pixels('image_scale', 10, 10, [
        _+_+_+_+_+_+_+_+_+_,
        _+r+r+B+B+B+B+B+B+_,
        _+r+r+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { -weasy-size: 10px; margin: 2px; background: #fff; }
            div { -weasy-transform: scale(2, 2);
                  -weasy-transform-origin: 1px 1px;
                  -weasy-image-rendering: optimizeSpeed; }
        </style>
        <div><img src="pattern.png"></div>
    ''')

    assert_pixels('image_scale12', 10, 10, [
        _+_+_+_+_+_+_+_+_+_,
        _+_+r+B+B+B+_+_+_+_,
        _+_+r+B+B+B+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { -weasy-size: 10px; margin: 2px; background: #fff; }
            div { -weasy-transform: scale(1, 2);
                  -weasy-transform-origin: 1px 1px;
                  -weasy-image-rendering: optimizeSpeed; }
        </style>
        <div><img src="pattern.png"></div>
    ''')

    assert_pixels('image_scaleY', 10, 10, [
        _+_+_+_+_+_+_+_+_+_,
        _+_+r+B+B+B+_+_+_+_,
        _+_+r+B+B+B+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { -weasy-size: 10px; margin: 2px; background: #fff; }
            div { -weasy-transform: scaleY(2);
                  -weasy-transform-origin: 1px 1px;
                  -weasy-image-rendering: optimizeSpeed; }
        </style>
        <div><img src="pattern.png"></div>
    ''')

    assert_pixels('image_scaleX', 10, 10, [
        _+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
        _+r+r+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { -weasy-size: 10px; margin: 2px; background: #fff; }
            div { -weasy-transform: scaleX(2);
                  -weasy-transform-origin: 1px 1px;
                  -weasy-image-rendering: optimizeSpeed; }
        </style>
        <div><img src="pattern.png"></div>
    ''')
