# coding: utf8
"""
    weasyprint.__main__
    -------------------

    Command-line interface to WeasyPrint.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import sys
import argparse

from . import VERSION, HTML


def main(argv=None, stdout=sys.stdout, stdin=sys.stdin):
    """Parse command-line arguments and convert the given document."""
    format_values = ['pdf', 'png']
    formats = 'PDF or PNG'
    extensions = '.pdf or .png'

    parser = argparse.ArgumentParser(prog='weasyprint',
        description='Renders web pages into ' + formats)
    parser.add_argument('--version', action='version',
                        version='WeasyPrint version %s' % VERSION,
                        help='Print WeasyPrint’s version number and exit.')
    parser.add_argument('-e', '--encoding',
                        help='Character encoding of the input')
    parser.add_argument('-f', '--format', choices=format_values,
                        help='Output format. Can be ommited if `output` '
                             'ends with ' + extensions)
    parser.add_argument('-s', '--stylesheet', action='append',
                        help='Apply a user stylesheet to the document. '
                             'May be given multiple times.')
    parser.add_argument('input',
        help='URL or filename of the HTML input, or - for stdin')
    parser.add_argument('output',
        help='Filename where output is written, or - for stdout')

    args = parser.parse_args(argv)

    if args.format is None:
        output_lower = args.output.lower()
        for file_format in format_values:
            if output_lower.endswith('.' + file_format):
                format_ = file_format
                break
        else:
            parser.error(
                'Either sepecify a format with -f or choose an '
                'output filename that ends in ' + extensions)
    else:
        format_ = args.format.lower()

    if args.input == '-':
        source = getattr(stdin, 'buffer', stdin)
        base_url = '<stdin>' # Dummy filename in the current directory
    else:
        source = args.input
        base_url = args.input

    if args.output == '-':
        output = getattr(stdout, 'buffer', stdout)
    else:
        output = args.output

    html = HTML(source, base_url=base_url, encoding=args.encoding)
    getattr(html, 'write_' + format_)(output, stylesheets=args.stylesheet)


if __name__ == '__main__':  # pragma: no cover
    main()
