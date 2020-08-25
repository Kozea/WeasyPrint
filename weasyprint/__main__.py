"""
    weasyprint.__main__
    -------------------

    Command-line interface to WeasyPrint.

"""

import argparse
import logging
import platform
import sys

import cairosvg

from . import HTML, LOGGER, VERSION
from .text import cairo, pango


class PrintInfo(argparse.Action):
    def __call__(*_, **__):
        uname = platform.uname()
        print('System:', uname.system)
        print('Machine:', uname.machine)
        print('Version:', uname.version)
        print('Release:', uname.release)
        print()
        print('WeasyPrint version:', VERSION)
        print('Python version:', sys.version.split()[0])
        print('Cairo version:', cairo.cairo_version())
        print('Pango version:', pango.pango_version())
        print('CairoSVG version:', cairosvg.__version__)
        sys.exit()


def main(argv=None, stdout=None, stdin=None):
    """The ``weasyprint`` program takes at least two arguments:

    .. code-block:: sh

        weasyprint [options] <input> <output>

    The input is a filename or URL to an HTML document, or ``-`` to read
    HTML from stdin. The output is a filename, or ``-`` to write to stdout.

    Options can be mixed anywhere before, between, or after the input and
    output.

    .. option:: -e <input_encoding>, --encoding <input_encoding>

        Force the input character encoding (e.g. ``-e utf8``).

    .. option:: -f <output_format>, --format <output_format>

        Choose the output file format among PDF and PNG (e.g. ``-f png``).
        Required if the output is not a ``.pdf`` or ``.png`` filename.

    .. option:: -s <filename_or_URL>, --stylesheet <filename_or_URL>

        Filename or URL of a user cascading stylesheet (see
        :ref:`stylesheet-origins`) to add to the document
        (e.g. ``-s print.css``). Multiple stylesheets are allowed.

    .. option:: -m <type>, --media-type <type>

        Set the media type to use for ``@media``. Defaults to ``print``.

    .. option:: -r <dpi>, --resolution <dpi>

        For PNG output only. Set the resolution in PNG pixel per CSS inch.
        Defaults to 96, which means that PNG pixels match CSS pixels.

    .. option:: -u <URL>, --base-url <URL>

        Set the base for relative URLs in the HTML input.
        Defaults to the input’s own URL, or the current directory for stdin.

    .. option:: -a <file>, --attachment <file>

        Adds an attachment to the document.  The attachment is
        included in the PDF output.  This option can be used multiple
        times.

    .. option:: -p, --presentational-hints

        Follow `HTML presentational hints
        <https://www.w3.org/TR/html/rendering.html\
        #the-css-user-agent-style-sheet-and-presentational-hints>`_.

    .. option:: -o, --optimize-images

        Try to optimize the size of embedded images.

    .. option:: -v, --verbose

        Show warnings and information messages.

    .. option:: -d, --debug

        Show debugging messages.

    .. option:: -q, --quiet

        Hide logging messages.

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
    parser.add_argument('-i', '--info', action=PrintInfo, nargs=0,
                        help='Print system information and exit.')
    parser.add_argument('-e', '--encoding',
                        help='Character encoding of the input')
    parser.add_argument('-f', '--format', choices=['pdf', 'png'],
                        help='Output format. Can be omitted if `output` '
                             'ends with a .pdf or .png extension.')
    parser.add_argument('-s', '--stylesheet', action='append',
                        help='URL or filename for a user CSS stylesheet. '
                             'May be given multiple times.')
    parser.add_argument('-m', '--media-type', default='print',
                        help='Media type to use for @media, defaults to print')
    parser.add_argument('-r', '--resolution', type=float,
                        help='PNG only: the resolution in pixel per CSS inch. '
                             'Defaults to 96, one PNG pixel per CSS pixel.')
    parser.add_argument('-u', '--base-url',
                        help='Base for relative URLs in the HTML input. '
                             "Defaults to the input's own filename or URL "
                             'or the current directory for stdin.')
    parser.add_argument('-a', '--attachment', action='append',
                        help='URL or filename of a file '
                             'to attach to the PDF document')
    parser.add_argument('-p', '--presentational-hints', action='store_true',
                        help='Follow HTML presentational hints.')
    parser.add_argument('-o', '--optimize-images', action='store_true',
                        help='Try to optimize the size of embedded images.')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Show warnings and information messages.')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Show debugging messages.')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Hide logging messages.')
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
                'Either specify a format with -f or choose an '
                'output filename that ends in .pdf or .png')
    else:
        format_ = args.format.lower()

    if args.input == '-':
        source = stdin or sys.stdin.buffer
        if args.base_url is None:
            args.base_url = '.'  # current directory
        elif args.base_url == '':
            args.base_url = None  # no base URL
    else:
        source = args.input

    if args.output == '-':
        output = stdout or sys.stdout.buffer
    else:
        output = args.output

    kwargs = {
        'stylesheets': args.stylesheet,
        'presentational_hints': args.presentational_hints,
        'optimize_images': args.optimize_images}
    if args.resolution:
        if format_ == 'png':
            kwargs['resolution'] = args.resolution
        else:
            parser.error('--resolution only applies for the PNG format.')

    if args.attachment:
        if format_ == 'pdf':
            kwargs['attachments'] = args.attachment
        else:
            parser.error('--attachment only applies for the PDF format.')

    # Default to logging to stderr.
    if args.debug:
        LOGGER.setLevel(logging.DEBUG)
    elif args.verbose:
        LOGGER.setLevel(logging.INFO)
    if not args.quiet:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        LOGGER.addHandler(handler)

    html = HTML(source, base_url=args.base_url, encoding=args.encoding,
                media_type=args.media_type)
    getattr(html, 'write_' + format_)(output, **kwargs)


if __name__ == '__main__':  # pragma: no cover
    main()
