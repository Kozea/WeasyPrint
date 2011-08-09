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


import sys
import argparse

from . import document


FORMATS = {
    'pdf': document.PDFDocument,
    'png': document.PNGDocument,
}


def _join(sequence, key=lambda x: x):
    sequence = sorted(sequence)
    last = key(sequence[-1])
    if len(sequence) == 1:
        return last
    else:
        return ' or '.join([', '.join(map(key, sequence[:-1])), last])


def main():
    parser = argparse.ArgumentParser(
        description='Renders web pages into ' + _join(FORMATS, str.upper))
    parser.add_argument('-e', '--encoding',
                        help='Character encoding of the input')
    parser.add_argument('-f', '--format', choices=FORMATS,
                        help='Output format')
    parser.add_argument('input',
        help='URL or filename of the HTML input, or - for stdin')
    parser.add_argument('output',
        help='Filename where output is written, or - for stdout')

    args = parser.parse_args()

    if args.format is None:
        for format in FORMATS:
            if args.output.endswith('.' + format):
                args.format = format
                break
        else:
            parser.error(
                'Either sepecify a format with -f or choose an '
                'output filename that ends in ' +
                _join(FORMATS, lambda x: '.' + x))

    if args.input == '-':
        args.input = sys.stdin

    if args.output == '-':
        args.output = sys.stdout

    document_class = FORMATS[args.format]
    document = document_class.from_file(args.input, encoding=args.encoding)
    document.write_to(args.output)
