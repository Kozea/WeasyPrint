#!/usr/bin/env python
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
from array import array
import png


def filename(directory, basename):
    return os.path.join(os.path.dirname(__file__), directory,
                        basename + '.png')


def make(basename, lines, directory='expected_results'):
    writer = png.Writer(width=len(lines[0]) / 3, height=len(lines), alpha=False)
    with open(filename(directory, basename), 'wb') as fd:
        writer.write(fd, lines)


def make_all():
    _ = white = array('B', [255, 255, 255])
    r = red = array('B', [255, 0, 0])
    B = blue = array('B', [0, 0, 255])

    make('blocks', [
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
    ])

    make('all_blue', 10 * [10 * blue])

    make('pattern', [
        r+B+B+B,
        B+B+B+B,
        B+B+B+B,
        B+B+B+B,
    ], 'resources')

    make('background_repeat', [
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
   ])

    make('background_no_repeat', [
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
   ])


if __name__ == '__main__':
    make_all()
