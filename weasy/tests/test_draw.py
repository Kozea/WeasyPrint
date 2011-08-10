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


import os.path

import png
from attest import Tests, assert_hook

from . import resource_filename
from ..document import PNGDocument


suite = Tests()


def make_filename(dirname, basename):
    return os.path.join(os.path.dirname(__file__), dirname, basename + '.png')


def test_pixels(name, expected_width, expected_height, html):
    reader = png.Reader(filename=make_filename('expected_results', name))
    width, height, expected_lines, meta = reader.read()
    assert width == expected_width
    assert height == height
    assert meta['greyscale'] == False
    assert meta['alpha'] == False
    assert meta['bitdepth'] == 8
    expected_lines = list(expected_lines)

    document = PNGDocument.from_string(html)
    # Dummy filename, but in the right directory.
    document.base_url = resource_filename('<test>')
    filename = make_filename('test_results', name)
    document.write_to(filename)


    reader = png.Reader(filename=filename)
    width, height, lines, meta = reader.read()
    lines = list(lines)

    assert width == expected_width
    assert height == height
    assert meta['greyscale'] == False
    assert meta['alpha'] == False
    assert meta['bitdepth'] == 8
    assert len(lines) == height
    assert len(lines[0]) == width * 3
    if lines != expected_lines:
        for y in xrange(height):
            for x in xrange(width):
                assert lines[y][3 * x:3 * (x + 1)] == \
                    expected_lines[y][3 * x:3 * (x + 1)], \
                    'Pixel (%i, %i) does not match' % (x, y)

@suite.test
def test_canvas_background():
    test_pixels('all_blue', 10, 10, '''
        <style>
            @page { size: 10px }
            /* body’s background propagates to the whole canvas */
            body { margin: 2px; background: #00f; height: 5px }
        </style>
        <body>
    ''')
    test_pixels('blocks', 10, 10, '''
        <style>
            @page { size: 10px }
            /* html’s background propagates to the whole canvas */
            html { margin: 1px; background: #f00 }
            /* html has a background, so body’s does not propagate */
            body { margin: 1px; background: #00f; height: 5px }
        </style>
        <body>
    ''')


def test_background_repeat(repeat):
    test_pixels('background_' + repeat, 14, 16, '''
        <style>
            @page { size: 14px 16px }
            html { background: #fff }
            body { margin: 2px; height: 10px;
                   background: url(pattern.png) %s }
        </style>
        <body>
    ''' % (repeat,))


@suite.test
def test_background_image():
    test_background_repeat('repeat')
    test_background_repeat('no-repeat')
    test_background_repeat('repeat-y')
    test_background_repeat('repeat-x')
