# coding: utf8
"""
    weasyprint.__main__
    -------------------

    Command-line interface to WeasyPrint.

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

# No __future__.unicode_literals here.
# Native strings are fine with argparse, unicode makes --help crash on 2.6.

import sys
import argparse

from . import VERSION, HTML


def main(argv=None, stdout=None, stdin=None):
    """The ``weasyprint`` program takes at least two arguments:

    .. code-block:: sh

        weasyprint [options] <input> <output>

    The input is a filename or URL to an HTML document, or ``-`` to read
    HTML from stdin. The output is a filename, or ``-`` to write to stdout.

    Options can be mixed anywhere before, between or after the input and
    output:

    .. option:: -e <input_encoding>, --encoding <input_encoding>

        Force the input character encoding (eg. ``-e utf8``).

    .. option:: -f <output_format>, --format <output_format>

        Choose the output file format among PDF and PNG (eg. ``-f png``).
        Required if the output is not a ``.pdf`` or ``.png`` filename.

    .. option:: -s <filename_or_URL>, --stylesheet <filename_or_URL>

        Filename or URL of a user CSS stylesheet (see
        :ref:`stylesheet-origins`\.) to add to the document.
        (eg. ``-s print.css``). Multiple stylesheets are allowed.

    .. option:: -r <dpi>, --resolution <dpi>

        For PNG output only. Set the resolution in PNG pixel per CSS inch.
        Defaults to 96, which means that PNG pixels match CSS pixels.

    .. option:: --base-url <URL>

        Set the base for relative URLs in the HTML input.
        Defaults to the input’s own URL, or the current directory for stdin.

    .. option:: -m <type>, --media-type <type>

        Set the media type to use for ``@media``. Defaults to ``print``.

    .. option:: -a <file>, --attachment <file>

        Adds an attachment to the document which is included in the PDF output.
        This option can be added multiple times to attach more files.

    .. option:: --version

        Show the version number. Other options and arguments are ignored.

    .. option:: -h, --help

        Show the command-line usage. Other options and arguments are ignored.

    """
    parser = argparse.ArgumentParser(
        prog='weasyprint', description='Renders web pages to PDF or PNG.')
    parser.add_argument('--version', action='version',
                        version='WeasyPrint version %s' % VERSION,
                        help="Print WeasyPrint's version number and exit.")
    parser.add_argument('-e', '--encoding',
                        help='Character encoding of the input')
    parser.add_argument('-f', '--format', choices=['pdf', 'png'],
                        help='Output format. Can be ommited if `output` '
                             'ends with a .pdf or .png extension.')
    parser.add_argument('-s', '--stylesheet', action='append',
                        help='URL or filename for a user CSS stylesheet. '
                             'May be given multiple times.')
    parser.add_argument('-m', '--media-type', default='print',
                        help='Media type to use for @media, defaults to print')
    parser.add_argument('-r', '--resolution', type=float,
                        help='PNG only: the resolution in pixel per CSS inch. '
                             'Defaults to 96, one PNG pixel per CSS pixel.')
    parser.add_argument('--base-url',
                        help='Base for relative URLs in the HTML input. '
                             "Defaults to the input's own filename or URL "
                             'or the current directory for stdin.')
    parser.add_argument('-a', '--attachment', action='append',
                        help='URL or filename of a file '
                             'to attach to the PDF document')
    parser.add_argument(
        'input', help='URL or filename of the HTML input, or - for stdin')
    parser.add_argument(
        'output', help='Filename where output is written, or - for stdout')

    args = parser.parse_args(argv)

    if args.format is None:
        output_lower = args.output.lower()
        if output_lower.endswith('.pdf'):
            format_ = 'pdf'
        elif output_lower.endswith('.png'):
            format_ = 'png'
        else:
            parser.error(
                'Either sepecify a format with -f or choose an '
                'output filename that ends in .pdf or .png')
    else:
        format_ = args.format.lower()

    if args.input == '-':
        if stdin is None:
            stdin = sys.stdin
        # stdin.buffer on Py3, stdin on Py2
        source = getattr(stdin, 'buffer', stdin)
        if not args.base_url:
            args.base_url = '.'  # current directory
    else:
        source = args.input

    if args.output == '-':
        if stdout is None:
            stdout = sys.stdout
        # stdout.buffer on Py3, stdout on Py2
        output = getattr(stdout, 'buffer', stdout)
    else:
        output = args.output

    kwargs = {'stylesheets': args.stylesheet}
    if args.resolution:
        if format_ == 'png':
            kwargs['resolution'] = args.resolution
        else:
            parser.error('--resolution only applies for the PNG format.')

    if args.attachment:
        if format_ == 'pdf':
            kwargs['attachments'] = args.attachments
        else:
            parser.error('--attachment only applies for the PDF format.')

    html = HTML(source, base_url=args.base_url, encoding=args.encoding,
                media_type=args.media_type)
    getattr(html, 'write_' + format_)(output, **kwargs)


if __name__ == '__main__':  # pragma: no cover
    main()
