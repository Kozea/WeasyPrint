# coding: utf8

#  WeasyPrint converts web documents (HTML, CSS, ...) to PDF.
#  Copyright (C) 2011  Simon Sapin
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""
Test the drawing functions.

"""

import os.path
from array import array

import png
from attest import Tests, assert_hook  # pylint: disable=W0611

from . import resource_filename, TestPNGDocument, FONTS

# Short variable names are OK here
# pylint: disable=C0103

_ = array('B', [255, 255, 255, 255])  # white
r = array('B', [255, 0, 0, 255])  # red
B = array('B', [0, 0, 255, 255])  # blue
BYTES_PER_PIXELS = 4

SUITE = Tests()


def make_filename(dirname, basename):
    """Return the filename of the output image."""
    return os.path.join(os.path.dirname(__file__), dirname, basename + '.png')


def format_pixel(lines, x, y):
    """Return the pixel color as ``#RRGGBB``."""
    start = BYTES_PER_PIXELS * x
    end = BYTES_PER_PIXELS * (x + 1)
    pixel = lines[y][start:end]
    return ('#' + BYTES_PER_PIXELS * '%02x') % tuple(pixel)


def test_pixels(name, expected_width, expected_height, expected_lines, html):
    """Helper testing the size of the image and the pixels values."""
    write_pixels('expected_results', name, expected_width, expected_height,
                 expected_lines)
    _doc, lines = html_to_png(name, expected_width, expected_height, html)
    assert_pixels_equal(name, expected_width, expected_height, lines,
                        expected_lines)


def test_same_rendering(expected_width, expected_height, *documents):
    """
    Render two or more HTML documents to PNG and check that the pixels
    are the same.

    Each document is passed as a (name, html) tuple.
    """
    lines_list = []

    for name, html in documents:
        _doc, lines = html_to_png(name, expected_width, expected_height, html)
        write_pixels('test_results', name, expected_width, expected_height,
                     lines)
        lines_list.append((name, lines))

    _name, reference = lines_list[0]
    for name, lines in lines_list[1:]:
        assert_pixels_equal(name, expected_width, expected_height,
                            reference, lines)


def write_pixels(directory, name, expected_width, expected_height, lines):
    """
    Check the size of a pixel matrix and write it to a PNG file.
    """
    assert len(lines) == expected_height, name
    assert len(lines[0]) == BYTES_PER_PIXELS * expected_width, name

    filename = make_filename(directory, name)
    writer = png.Writer(width=expected_width, height=expected_height,
                        alpha=True)
    with open(filename, 'wb') as fd:
        writer.write(fd, lines)


def html_to_png(name, expected_width, expected_height, html):
    """
    Render an HTML document to PNG, checks its size and return pixel data.

    Also return the document to aid debugging.
    """
    document = TestPNGDocument.from_string(html)
    # Dummy filename, but in the right directory.
    document.base_url = resource_filename('<test>')
    filename = make_filename('test_results', name)
    document.write_to(filename)
    assert len(document.pages) == 1

    reader = png.Reader(filename=filename)
    width, height, lines, meta = reader.asRGBA()
    lines = list(lines)

    assert width == expected_width, name
    assert height == expected_height, name
    assert meta['greyscale'] == False, name
    assert meta['alpha'] == True, name
    assert meta['bitdepth'] == 8, name
    assert len(lines) == height, name
    assert len(lines[0]) == width * BYTES_PER_PIXELS, name
    return document, lines


def assert_pixels_equal(name, width, height, lines, expected_lines):
    """
    Take 2 matrices of height by width pixels and assert that they
    are the same.
    """
    if lines != expected_lines:
        for y in xrange(height):
            for x in xrange(width):
                pixel = format_pixel(lines, x, y)
                expected_pixel = format_pixel(expected_lines, x, y)
                assert pixel == expected_pixel, \
                    'Pixel (%i, %i) does not match in %s' % (x, y, name)


@SUITE.test
def test_canvas_background():
    """Test the background applied on ``<html>`` and/or ``<body>`` tags."""
    test_pixels('all_blue', 10, 10, (10 * [10 * B]), '''
        <style>
            @page { -weasy-size: 10px }
            /* body’s background propagates to the whole canvas */
            body { margin: 2px; background: #00f; height: 5px }
        </style>
        <body>
    ''')

    test_pixels('blocks', 10, 10, [
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
            html { margin: 1px; background: #f00 }
            /* html has a background, so body’s does not propagate */
            body { margin: 1px; background: #00f; height: 5px }
        </style>
        <body>
    ''')


@SUITE.test
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
        test_pixels('background_' + name, 14, 16, pixels, '''
            <style>
                @page { -weasy-size: 14px 16px }
                html { background: #fff }
                body { margin: 2px; height: 10px;
                       background: url(pattern.png) %s }
            </style>
            <body>
        ''' % (css,))


@SUITE.test
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
        test_pixels('list_style_image_' + position, 12, 10, pixels, '''
            <style>
                @page { -weasy-size: 12px 10px }
                body { margin: 0; background: white; font-family: %s }
                ul { margin: 2px 2px 0 7px; list-style: url(pattern.png) %s;
                     font-size: 2px }
            </style>
            <ul><li></li></ul>
        ''' % (FONTS, position))

    test_pixels('list_style_none', 10, 10, [
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


@SUITE.test
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
    V = array('B', [0x65, 0x24, 0xe2, 255])
    v = array('B', [0x35, 0x00, 0xb2, 255])
    u = array('B', [0x36, 0x00, 0xb3, 255])
    b = array('B', [0, 1, 254, 255])
    d = array('B', [0, 0, 254, 255])
    centered_jpg_image = [
        # JPG is lossy...
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+V+v+b+b+_+_,
        _+_+v+u+b+b+_+_,
        _+_+d+d+d+d+_+_,
        _+_+d+d+d+d+_+_,
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
    for format in ['png', 'gif', 'svg', 'jpg']:
        image = centered_jpg_image if format == 'jpg' else centered_image
        test_pixels('inline_image_' + format, 8, 8, image, '''
            <style>
                @page { -weasy-size: 8px }
                body { margin: 2px 0 0 2px; background: #fff }
            </style>
            <div><img src="pattern.%s"></div>
        ''' % format)
    test_pixels('block_image', 8, 8, centered_image, '''
        <style>
            @page { -weasy-size: 8px }
            body { margin: 0; background: #fff }
            img { display: block; margin: 2px auto 0 }
        </style>
        <div><img src="pattern.png"></div>
    ''')
    test_pixels('image_not_found', 8, 8, no_image, '''
        <style>
            @page { -weasy-size: 8px }
            body { margin: 0; background: #fff }
            img { display: block; margin: 2px auto 0 }
        </style>
        <div><img src="inexistent1.png" alt=""></div>
    ''')
    test_pixels('image_no_src', 8, 8, no_image, '''
        <style>
            @page { -weasy-size: 8px }
            body { margin: 0; background: #fff }
            img { display: block; margin: 2px auto 0 }
        </style>
        <div><img alt=""></div>
    ''')
    test_same_rendering(200, 30,
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
    )


@SUITE.test
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
    test_pixels('visibility_reference', 12, 7, [
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+r+B+B+B+_+r+B+B+B+_+_,
        _+B+B+B+B+_+B+B+B+B+_+_,
        _+B+B+B+B+_+B+B+B+B+_+_,
        _+B+B+B+B+_+B+B+B+B+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
    ], source % {'extra_css': ''})

    test_pixels('visibility_hidden', 12, 7, [
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
    ], source % {'extra_css': 'div { visibility: hidden }'})

    test_pixels('visibility_mixed', 12, 7, [
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+r+B+B+B+_+_,
        _+_+_+_+_+_+B+B+B+B+_+_,
        _+_+_+_+_+_+B+B+B+B+_+_,
        _+_+_+_+_+_+B+B+B+B+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
    ], source % {'extra_css': '''div { visibility: hidden }
                                 span { visibility: visible } '''})


@SUITE.test
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
    r = array('B', [255, 127, 127, 255])  # rgba(255, 0, 0, 0.5) above #fff
    R = array('B', [255, 63, 63, 255])  # r above r above #fff
    test_pixels('table_borders', 28, 28, [
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
        table { border-color: #00f }
        td { border-color: rgba(255, 0, 0, 0.5) }
    '''})

    test_pixels('table_td_backgrounds', 28, 28, [
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
        table { border-color: #00f }
        td { background: rgba(255, 0, 0, 0.5) }
    '''})

    g = array('B', [127, 255, 127, 255])  # rgba(0, 255, 0, 0.5) above #fff
    G = array('B', [127, 191, 63, 255])  # g above r above #fff
                                         # Not the same as r above g above #fff
    test_pixels('table_column_backgrounds', 28, 28, [
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
        table { border-color: #00f }
        colgroup { background: rgba(255, 0, 0, 0.5) }
        col { background: rgba(0, 255, 0, 0.5) }
    '''})

    test_pixels('table_row_backgrounds', 28, 28, [
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
        table { border-color: #00f }
        thead { background: rgba(255, 0, 0, 0.5) }
        tr { background: rgba(0, 255, 0, 0.5) }
    '''})



@SUITE.test
def test_before_after():
    test_same_rendering(300, 30,
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
    )

    test_same_rendering(500, 30,
        ('pseudo_quotes', u'''
            <style>
                @page { -weasy-size: 500px 30px }
                body { margin: 0; background: #fff; quotes: '«' '»' '“' '”' }
                q:before { content: open-quote ' '}
                q:after { content: ' ' close-quote }
            </style>
            <p><q>Lorem ipsum <q>dolor</q> sit amet</q></p>
        '''),
        ('pseudo_quotes_reference', u'''
            <style>
                @page { -weasy-size: 500px 30px }
                body { margin: 0; background: #fff }
            </style>
            <p>« Lorem ipsum “ dolor ” sit amet »</p>
        ''')
    )

    test_same_rendering(100, 30,
        ('pseudo_url', u'''
            <style>
                @page { -weasy-size: 100px 30px }
                body { margin: 0; background: #fff; }
                p:before { content: 'a' url(pattern.png) 'b'}
            </style>
            <p>c</p>
        '''),
        ('pseudo_url_reference', u'''
            <style>
                @page { -weasy-size: 100px 30px }
                body { margin: 0; background: #fff }
            </style>
            <p>a<img src="pattern.png" alt="Missing image">bc</p>
        ''')
    )
