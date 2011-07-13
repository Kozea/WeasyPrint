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


def filename(basename):
    return os.path.join(os.path.dirname(__file__), 'expected_results',
                        basename + '.png')


def make(basename, lines):
    writer = png.Writer(width=len(lines[0]) / 4, height=len(lines), alpha=True)
    with open(filename(basename), 'wb') as fd:
        writer.write(fd, lines)


def make_all():
    transparent = array('B', [0, 0, 0, 0])
    blue = array('B', [0, 0, 255, 255])

    transparent_line = transparent * 10

    make('blocks',
        2 * [transparent_line] +
        5 * [2 * transparent + 6 * blue + 2 * transparent] +
        3 * [transparent_line])


if __name__ == '__main__':
    make_all()
