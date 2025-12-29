"""Command-line interface to WeasyPrint."""

import argparse
import logging
import platform
import sys
from functools import partial

import pydyf

from . import DEFAULT_OPTIONS, HTML, LOGGER, __version__
from .pdf import VARIANTS
from .text.ffi import pango
from .urls import default_url_fetcher


class PrintInfo(argparse.Action):
    def __call__(*_, **__):
        # TODO: ignore check at block-level when available.
        # https://github.com/astral-sh/ruff/issues/3711
        uname = platform.uname()
        print('System:', uname.system)  # noqa: T201
        print('Machine:', uname.machine)  # noqa: T201
        print('Version:', uname.version)  # noqa: T201
        print('Release:', uname.release)  # noqa: T201
        print()  # noqa: T201
        print('WeasyPrint version:', __version__)  # noqa: T201
        print('Python version:', sys.version.split()[0])  # noqa: T201
        print('Pydyf version:', pydyf.__version__)  # noqa: T201
        print('Pango version:', pango.pango_version())  # noqa: T201
        sys.exit()


class Parser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        self._arguments = {}
        super().__init__(*args, **kwargs)

    def add_argument(self, *args, **kwargs):
        super().add_argument(*args, **kwargs)
        key = args[-1].lstrip('-')
        kwargs['flags'] = args
        kwargs['positional'] = args[-1][0] != '-'
        self._arguments[key] = kwargs

    @property
    def docstring(self):
        self._arguments['help'] = self._arguments.pop('help')
        data = []
        for key, args in self._arguments.items():
            data.append('.. option:: ')
            action = args.get('action', 'store')
            for flag in args['flags']:
                data.append(flag)
                if not args['positional'] and action in ('store', 'append'):
                    data.append(f' <{key}>')
                data.append(', ')
            data[-1] = '\n\n'
            data.append(f'  {args["help"][0].upper()}{args["help"][1:]}.\n\n')
            if 'choices' in args:
                choices = ", ".join(args['choices'])
                data.append(f'  Possible choices: {choices}.\n\n')
            if action == 'append':
                data.append('  This option can be passed multiple times.\n\n')
        return ''.join(data)


PARSER = Parser(prog='weasyprint', description='Render web pages to PDF.')
PARSER.add_argument(
    'input', help='URL or filename of the HTML input, or - for stdin')
PARSER.add_argument(
    'output', help='filename where output is written, or - for stdout')
PARSER.add_argument(
    '-e', '--encoding', help='force the input character encoding')
PARSER.add_argument(
    '-s', '--stylesheet', action='append', dest='stylesheets',
    help='URL or filename for a user CSS stylesheet')
PARSER.add_argument(
    '-m', '--media-type',
    help='media type to use for @media, defaults to print')
PARSER.add_argument(
    '-u', '--base-url',
    help='base for relative URLs in the HTML input, defaults to the '
    'input’s own filename or URL or the current directory for stdin')
PARSER.add_argument(
    '-a', '--attachment', action='append', dest='attachments',
    help='URL or filename of a file to attach to the PDF document')
PARSER.add_argument('--pdf-identifier', help='PDF file identifier')
PARSER.add_argument(
    '--pdf-variant', choices=VARIANTS, help='PDF variant to generate')
PARSER.add_argument('--pdf-version', help='PDF version number')
PARSER.add_argument(
    '--pdf-forms', action='store_true', help='include PDF forms')
PARSER.add_argument(
    '--pdf-tags', action='store_true', help='tag PDF for accessibility')
PARSER.add_argument(
    '--uncompressed-pdf', action='store_true',
    help='do not compress PDF content, mainly for debugging purpose')
PARSER.add_argument(
    '--custom-metadata', action='store_true',
    help='include custom HTML meta tags in PDF metadata')
PARSER.add_argument(
    '-p', '--presentational-hints', action='store_true',
    help='follow HTML presentational hints')
PARSER.add_argument(
    '--srgb', action='store_true',
    help='include sRGB color profile')
PARSER.add_argument(
    '--optimize-images', action='store_true',
    help='optimize size of embedded images with no quality loss')
PARSER.add_argument(
    '-j', '--jpeg-quality', type=int,
    help='JPEG quality between 0 (worst) to 95 (best)')
PARSER.add_argument(
    '--full-fonts', action='store_true',
    help='embed unmodified font files when possible')
PARSER.add_argument(
    '--hinting', action='store_true',
    help='keep hinting information in embedded fonts')
PARSER.add_argument(
    '-c', '--cache-folder', dest='cache',
    help='store cache on disk instead of memory, folder is '
    'created if needed and cleaned after the PDF is generated')
PARSER.add_argument(
    '-D', '--dpi', type=int,
    help='set maximum resolution of images embedded in the PDF')
PARSER.add_argument(
    '-v', '--verbose', action='store_true',
    help='show warnings and information messages')
PARSER.add_argument(
    '-d', '--debug', action='store_true', help='show debugging messages')
PARSER.add_argument(
    '-q', '--quiet', action='store_true', help='hide logging messages')
PARSER.add_argument(
    '--version', action='version',
    version=f'WeasyPrint version {__version__}',
    help='print WeasyPrint’s version number and exit')
PARSER.add_argument(
    '-i', '--info', action=PrintInfo, nargs=0,
    help='print system information and exit')
PARSER.add_argument(
    '-t', '--timeout', type=int,
    help='set timeout in seconds for HTTP requests')
PARSER.add_argument(
    '--allowed-protocols', dest='allowed_protocols',
    help='only authorize comma-separated list of protocols for fetching URLs')
PARSER.set_defaults(**DEFAULT_OPTIONS)


def main(argv=None, stdout=None, stdin=None, HTML=HTML):  # noqa: N803
    """The ``weasyprint`` program takes at least two arguments:

    .. code-block:: sh

        weasyprint [options] <input> <output>

    """
    args = PARSER.parse_args(argv)

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

    url_fetcher = default_url_fetcher
    if args.timeout is not None:
        url_fetcher = partial(default_url_fetcher, timeout=args.timeout)
    if args.allowed_protocols is not None:
        protocols = {
            protocol.strip().lower() for protocol in args.allowed_protocols.split(',')}
        url_fetcher = partial(url_fetcher, allowed_protocols=protocols)

    options = {
        key: value for key, value in vars(args).items() if key in DEFAULT_OPTIONS}

    # Default to logging to stderr.
    if args.debug:
        LOGGER.setLevel(logging.DEBUG)
    elif args.verbose:
        LOGGER.setLevel(logging.INFO)
    if not args.quiet:
        handler = logging.StreamHandler()
        if args.debug:
            # Add extra information when debug logging
            handler.setFormatter(
                logging.Formatter(
                    '%(levelname)s: %(filename)s:%(lineno)d '
                    '(%(funcName)s): %(message)s'))
        else:
            handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        LOGGER.addHandler(handler)

    html = HTML(
        source, base_url=args.base_url, encoding=args.encoding,
        media_type=args.media_type, url_fetcher=url_fetcher)
    html.write_pdf(output, **options)


main.__doc__ += '\n\n' + PARSER.docstring


if __name__ == '__main__':  # pragma: no cover
    main()
