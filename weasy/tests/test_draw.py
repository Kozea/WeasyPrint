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
from io import BytesIO
from array import array

import png
from attest import Tests, assert_hook

from .test_layout import parse
from .. import draw


suite = Tests()


def make_filename(dirname, basename):
    return os.path.join(os.path.dirname(__file__), dirname, basename + '.png')


def test_pixels(name, html):
    reader = png.Reader(filename=make_filename('expected_results', name))
    expected_width, expected_height, expected_lines, expected_meta = \
        reader.read()
    expected_lines = list(expected_lines)

    pages = parse(html)
    assert len(pages) == 1
    filename = make_filename('test_results', name)
    draw.draw_page_to_png(pages[0], filename)
    reader = png.Reader(filename=filename)
    width, height, lines, meta = reader.read()
    lines = list(lines)

    for meta_ in [meta, expected_meta]:
        assert meta_['greyscale'] == False
        assert meta_['alpha'] == True
        assert meta_['bitdepth'] == 8

    assert width == expected_width
    assert height == height
    assert width > 0
    assert height > 0
    assert len(lines) == height
    assert len(lines[0]) == width * 4
    assert lines == expected_lines


@suite.test
def test_png():
    test_pixels('blocks', '''
        <style>
            @page { size: 10px }
            body { margin: 2px; background-color: #00f; height: 5px }
        </style>
        <body>
    ''')
