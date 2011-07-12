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


def get_pixels(name, html):
    pages = parse(html)
    assert len(pages) == 1
    filename = os.path.join(os.path.dirname(__file__), 'test_results',
                            name + '.png')
    draw.draw_page_to_png(pages[0], filename)
    reader = png.Reader(filename=filename)
    width, height, pixels, meta = reader.read()
    assert meta['greyscale'] == False
    assert meta['alpha'] == True
    assert meta['bitdepth'] == 8
    return width, height, pixels


@suite.test
def test_png():
    width, height, lines = get_pixels('blocks', '''
        <style>
            @page { size: 10px }
            body { margin: 2px; background-color: #00f; height: 5px }
        </style>
        <body>
    ''')
    assert width == 10
    assert height == 10
    # RGBA
    transparent = array('B', [0, 0, 0, 0])
    blue = array('B', [0, 0, 255, 255])
    for i, line in enumerate(lines):
        print i
        if 2 <= i < 7:
            assert line == transparent * 2 + blue * 6 + transparent * 2
        else:
            assert line == transparent * 10
    assert i == 9 # There are 10 lines for i 0..9
