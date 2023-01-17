"""Command-line interface to WeasyPrint."""

import argparse
import logging
import platform
import sys

import pydyf

from . import HTML, LOGGER, __version__
from .pdf import VARIANTS
from .text.ffi import pango


class PrintInfo(argparse.Action):
    def __call__(*_, **__):
        uname = platform.uname()
        print('System:', uname.system)
        print('Machine:', uname.machine)
        print('Version:', uname.version)
        print('Release:', uname.release)
        print()
        print('WeasyPrint version:', __version__)
        print('Python version:', sys.version.split()[0])
        print('Pydyf version:', pydyf.__version__)
        print('Pango version:', pango.pango_version())
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

        Force the input character encoding (e.g. ``-e utf-8``).

    .. option:: -s <filename_or_URL>, --stylesheet <filename_or_URL>

        Filename or URL of a user cascading stylesheet (see
        :ref:`Stylesheet Origins`) to add to the document
        (e.g. ``-s print.css``). Multiple stylesheets are allowed.

    .. option:: -m <type>, --media-type <type>

        Set the media type to use for ``@media``. Defaults to ``print``.

    .. option:: -u <URL>, --base-url <URL>

        Set the base for relative URLs in the HTML input.
        Defaults to the input’s own URL, or the current directory for stdin.

    .. option:: -a <file>, --attachment <file>

        Adds an attachment to the document. The attachment is included in the
        PDF output. This option can be used multiple times.

    .. option:: --pdf-identifier <identifier>

        PDF file identifier, used to check whether two different files
        are two different versions of the same original document.

    .. option:: --pdf-variant <variant-name>

        PDF variant to generate (e.g. ``--pdf-variant pdf/a-3b``).

    .. option:: --pdf-version <version-number>

        PDF version number (default is 1.7).

    .. option:: --custom-metadata

        Include custom HTML meta tags in PDF metadata.

    .. option:: -p, --presentational-hints

        Follow `HTML presentational hints
        <https://www.w3.org/TR/html/rendering.html\
        #the-css-user-agent-style-sheet-and-presentational-hints>`_.

    .. option:: -O <type>, --optimize-size <type>

        Optimize the size of generated documents. Supported types are
        ``images``, ``fonts``, ``all`` and ``none``. This option can be used
        multiple times, ``all`` adds all allowed values, ``none`` removes all
        previously set values.

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
        prog='weasyprint', description='Render web pages to PDF.')
    parser.add_argument(
        '--version', action='version',
        version=f'WeasyPrint version {__version__}',
        help='print WeasyPrint’s version number and exit')
    parser.add_argument(
        '-i', '--info', action=PrintInfo, nargs=0,
        help='print system information and exit')
    parser.add_argument(
        '-e', '--encoding', help='character encoding of the input')
    parser.add_argument(
        '-s', '--stylesheet', action='append',
        help='URL or filename for a user CSS stylesheet, '
        'may be given multiple times')
    parser.add_argument(
        '-m', '--media-type', default='print',
        help='media type to use for @media, defaults to print')
    parser.add_argument(
        '-u', '--base-url',
        help='base for relative URLs in the HTML input, defaults to the '
        'input’s own filename or URL or the current directory for stdin')
    parser.add_argument(
        '-a', '--attachment', action='append',
        help='URL or filename of a file to attach to the PDF document')
    parser.add_argument('--pdf-identifier', help='PDF file identifier')
    parser.add_argument(
        '--pdf-variant', choices=VARIANTS, help='PDF variant to generate')
    parser.add_argument('--pdf-version', help='PDF version number')
    parser.add_argument(
        '--pdf-forms', action='store_true', help='Include PDF forms')
    parser.add_argument(
        '--custom-metadata', action='store_true',
        help='include custom HTML meta tags in PDF metadata')
    parser.add_argument(
        '-p', '--presentational-hints', action='store_true',
        help='follow HTML presentational hints')
    parser.add_argument(
        '-O', '--optimize-size', action='append',
        help='optimize output size for specified features',
        choices=('images', 'fonts', 'all', 'none'), default=['fonts'])
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help='show warnings and information messages')
    parser.add_argument(
        '-d', '--debug', action='store_true', help='show debugging messages')
    parser.add_argument(
        '-q', '--quiet', action='store_true', help='hide logging messages')
    parser.add_argument(
        'input', help='URL or filename of the HTML input, or - for stdin')
    parser.add_argument(
        'output', help='filename where output is written, or - for stdout')

    args = parser.parse_args(argv)

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

    optimize_size = set()
    for arg in args.optimize_size:
        if arg == 'none':
            optimize_size.clear()
        elif arg == 'all':
            optimize_size |= {'images', 'fonts'}
        else:
            optimize_size.add(arg)

    kwargs = {
        'stylesheets': args.stylesheet,
        'presentational_hints': args.presentational_hints,
        'optimize_size': tuple(optimize_size),
        'attachments': args.attachment,
        'identifier': args.pdf_identifier,
        'variant': args.pdf_variant,
        'version': args.pdf_version,
        'forms': args.pdf_forms,
        'custom_metadata': args.custom_metadata,
    }

    # Default to logging to stderr.
    if args.debug:
        LOGGER.setLevel(logging.DEBUG)
    elif args.verbose:
        LOGGER.setLevel(logging.INFO)
    if not args.quiet:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        LOGGER.addHandler(handler)

    html = HTML(
        source, base_url=args.base_url, encoding=args.encoding,
        media_type=args.media_type)
    html.write_pdf(output, **kwargs)


if __name__ == '__main__':  # pragma: no cover
    main()
