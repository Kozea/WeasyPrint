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

VERSION = '0.6dev'
__version__ = VERSION


# No import here. For this module, do them in functions/methods instead.
# (This reduces the work for eg. 'weasyprint --help')


class HTML(object):
    def __init__(self, filename_or_url=None, filename=None, url=None,
                 file_obj=None, string=None, encoding=None, base_url=None):
        """Fetch and parse an HTML document.

        Only one of :obj:`filename_or_url`, :obj:`filename`, :obj:`url`,
        :obj:`file_obj` or :obj:`string` should be given.

        :param filename_or_url:
            Same as :obj:`url` if this looks like an URL, a filename otherwise
        :param filename:
            Path to a file in the local filesystem
        :param url:
            An HTTP or FTP URL. Other schemes may or may not be supported.
        :param file_obj:
            A file-like object with a :meth:`~file.read` method.
        :param string:
            A byte or Unicode string.

        :param encoding:
            Force the document encoding.
        """
        import lxml.html
        from .utils import ensure_url

        source_type, source, base_url = _select_source(
            filename_or_url, filename, url, file_obj, string, base_url)

        if source_type == 'string':
            parse = lxml.html.document_fromstring
        else:
            parse = lxml.html.parse
            if source_type != 'file_obj':
                # If base_url is None we want the used base URL to be
                # an URL, not a filename.
                source = ensure_url(source)
        parser = lxml.html.HTMLParser(encoding=encoding)
        result = parse(source, base_url=base_url, parser=parser)
        if source_type == 'string':
            self.root_element = result
        else:
            self.root_element = result.getroot()

    def _ua_stylesheet(self):
        from .css import HTML5_UA_STYLESHEET
        return [HTML5_UA_STYLESHEET]

    def _write(self, document_class, target, stylesheets):
        document_class(
            self.root_element,
            user_stylesheets=list(_parse_stylesheets(stylesheets)),
            user_agent_stylesheets=self._ua_stylesheet(),
        ).write_to(target)

    def write_pdf(self, target=None, stylesheets=None):
        """Render the document to PDF.

        :param target:
            a filename, file-like object, or :obj:`None`.
        :param stylesheets:
            a list of user stylsheets, as :class:`CSS` objects
        :returns:
            If :obj:`target` is :obj:`None`, a PDF byte string.
        """
        from .document import PDFDocument
        return self._write(PDFDocument, target, stylesheets)

    def write_png(self, target=None, stylesheets=None):
        """Render the document to PNG.

        :param target:
            a filename, file-like object, or :obj:`None`.
        :param stylesheets:
            a list of user stylsheets, as :class:`CSS` objects
        :returns:
            If :obj:`target` is :obj:`None`, a PNG byte string.
        """
        from .document import PNGDocument
        return self._write(PNGDocument, target, stylesheets)


class CSS(object):
    def __init__(self, filename_or_url=None, filename=None, url=None,
                 file_obj=None, string=None, encoding=None, base_url=None):
        """Fetch and parse a CSS stylesheet.

        Only one of :obj:`filename_or_url`, :obj:`filename`, :obj:`url`,
        :obj:`file_obj` or :obj:`string` should be given.

        :param filename_or_url:
            Same as :obj:`url` if this looks like an URL, a filename otherwise
        :param filename:
            Path to a file in the local filesystem
        :param url:
            An HTTP or FTP URL. Other schemes may or may not be supported.
        :param file_obj:
            A file-like object with a :meth:`~file.read` method.
        :param string:
            A byte or Unicode string.

        :param encoding:
            Force the document encoding.
        """
        from .css import PARSER

        source_type, source, base_url = _select_source(
            filename_or_url, filename, url, file_obj, string, base_url)

        if source_type == 'file_obj':
            source = source.read()
            source_type = 'string'
        parser = {'filename': PARSER.parseFile, 'url': PARSER.parseUrl,
                  'string': PARSER.parseString}[source_type]
        self.stylesheet = parser(source, encoding=encoding, href=base_url)


def _select_source(filename_or_url, filename, url, file_obj, string, base_url):
    """Check that only one of the argument is not None, and return which."""
    from .utils import ensure_url
    if base_url is not None:
        base_url = ensure_url(base_url)

    nones = [filename_or_url is None, filename is None, url is None,
             file_obj is None, string is None]
    if nones == [False, True, True, True, True]:
        import urlparse
        if urlparse.urlparse(filename_or_url).scheme:
            return 'url', filename_or_url, base_url
        else:
            return 'filename', filename_or_url, base_url
    if nones == [True, False, True, True, True]:
        return 'filename', filename, base_url
    if nones == [True, True, False, True, True]:
        return 'url', url, base_url
    if nones == [True, True, True, False, True]:
        return 'file_obj', file_obj, base_url
    if nones == [True, True, True, True, False]:
        return 'string', string, base_url

    raise TypeError('Expected only one source, got %i' % nones.count(False))


def _parse_stylesheets(stylesheets):
    """Yield parsed cssutils stylesheets.

    Accept :obj:`None` or a list of filenames, urls or CSS objects.

    """
    if stylesheets is None:
        return
    for css in stylesheets:
        if hasattr(css, 'stylesheet'):
            yield css.stylesheet
        else:
            yield CSS(css).stylesheet
