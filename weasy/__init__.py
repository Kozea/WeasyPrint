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
WeasyPrint
==========

WeasyPrint converts web documents, mainly HTML documents with CSS, to PDF.

"""

import argparse
from .version import VERSION


__version__ = VERSION
__all__ = ['main']


FORMATS = {
    'pdf': 'PDFDocument',
    'png': 'PNGDocument',
}


def _join(sequence, key=lambda x: x):
    """Return a string of the sorted elements of ``sequence``.

    The two last elements are separated by ' or ', the other ones are separated
    by ', '.

    If a ``key`` function is given, this function is applied to the elements of
    ``sequence`` before joining them.

    """
    sequence = sorted(sequence)
    last = key(sequence[-1])
    if len(sequence) == 1:
        return last
    else:
        return ' or '.join([', '.join(map(key, sequence[:-1])), last])


def main():
    """Parse command-line arguments and convert the given document."""
    extensions = _join(FORMATS, lambda x: '.' + x)

    parser = argparse.ArgumentParser(
        description='Renders web pages into ' + _join(FORMATS, str.upper))
    parser.add_argument('--version', action='version',
                        version='WeasyPrint version %s' % VERSION,
                        help='Print WeasyPrint’s version number and exit.')
    parser.add_argument('-e', '--encoding',
                        help='Character encoding of the input')
    parser.add_argument('-f', '--format', choices=FORMATS,
                        help='Output format. Can be ommited if `output` '
                             'ends with ' + extensions)
    parser.add_argument('-s', '--stylesheet', action='append',
                        help='Apply a user stylesheet to the document. '
                             'May be given multiple times.')
    parser.add_argument('input',
        help='URL or filename of the HTML input, or - for stdin')
    parser.add_argument('output',
        help='Filename where output is written, or - for stdout')

    args = parser.parse_args()

    # Import here so that these are not needed for --version and --help
    import sys
    import cssutils

    from . import document
    from .utils import ensure_url

    if args.format is None:
        for file_format in FORMATS:
            if args.output.endswith('.' + file_format):
                args.format = file_format
                break
        else:
            parser.error(
                'Either sepecify a format with -f or choose an '
                'output filename that ends in ' + extensions)

    if args.input == '-':
        args.input = sys.stdin

    if args.output == '-':
        args.output = sys.stdout

    users_stylesheets = [
        cssutils.parseUrl(ensure_url(filename_or_url))
        for filename_or_url in args.stylesheet or []]

    document_class = getattr(document, FORMATS[args.format])
    doc = document_class.from_file(args.input, encoding=args.encoding,
        user_stylesheets=users_stylesheets)
    doc.write_to(args.output)
