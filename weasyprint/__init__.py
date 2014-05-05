# coding: utf8
"""
    WeasyPrint
    ==========

    WeasyPrint converts web documents to PDF.

    The public API is what is accessible from this "root" packages
    without importing sub-modules.

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals


VERSION = '0.22'
__version__ = VERSION

# Used for 'User-Agent' in HTTP and 'Creator' in PDF
VERSION_STRING = 'WeasyPrint %s (http://weasyprint.org/)' % VERSION

__all__ = ['HTML', 'CSS', 'Attachment', 'Document', 'Page',
           'default_url_fetcher', 'VERSION']


import contextlib
import html5lib

from .urls import (fetch, default_url_fetcher, path2url, ensure_url,
                   url_is_absolute)
from .compat import unicode
from .logger import LOGGER
# Some import are at the end of the file (after the CSS class) is defined
# to work around circular imports.


class HTML(object):
    """Represents an HTML document parsed by `lxml <http://lxml.de/>`_.

    You can just create an instance with a positional argument:
    ``doc = HTML(something)``
    The class will try to guess if the input is a filename, an absolute URL,
    or a file-like object.

    Alternatively, use **one** named argument so that no guessing is involved:

    :param filename: A filename, relative to the current directory or absolute.
    :param url: An absolute, fully qualified URL.
    :param file_obj: a file-like: any object with a :meth:`~file.read` method.
    :param string: a string of HTML source. (This argument must be named.)
    :param tree: a parsed lxml tree. (This argument must be named.)

    Specifying multiple inputs is an error: ``HTML(filename=foo, url=bar)``
    will raise.

    You can also pass optional named arguments:

    :param encoding: Force the source character encoding.
    :param base_url: The base used to resolve relative URLs
        (eg. in ``<img src="../foo.png">``). If not provided, try to use
        the input filename, URL, or ``name`` attribute of file-like objects.
    :param url_fetcher: a function or other callable
        with the same signature as :func:`default_url_fetcher` called to
        fetch external resources such as stylesheets and images.
        (See :ref:`url-fetchers`.)
    :param media_type: The media type to use for ``@media``.
        Defaults to ``'print'``. **Note:** In some cases like
        ``HTML(string=foo)`` relative URLs will be invalid if ``base_url``
        is not provided.

    """
    def __init__(self, guess=None, filename=None, url=None, file_obj=None,
                 string=None, tree=None, encoding=None, base_url=None,
                 url_fetcher=default_url_fetcher, media_type='print'):
        result = _select_source(
            guess, filename, url, file_obj, string, tree, base_url,
            url_fetcher)
        with result as (source_type, source, base_url, protocol_encoding):
            if source_type == 'tree':
                result = source
            else:
                if not encoding:
                    encoding = protocol_encoding
                if isinstance(source, unicode):
                    encoding = None
                result = html5lib.parse(
                    source, treebuilder='lxml', encoding=encoding,
                    namespaceHTMLElements=False)
                assert result
        base_url = find_base_url(result, base_url)
        if hasattr(result, 'getroot'):
            result.docinfo.URL = base_url
            result = result.getroot()
        else:
            result.getroottree().docinfo.URL = base_url
        self.root_element = result
        self.base_url = base_url
        self.url_fetcher = url_fetcher
        self.media_type = media_type

    def _ua_stylesheets(self):
        return [HTML5_UA_STYLESHEET]

    def _get_metadata(self):
        return get_html_metadata(self.root_element)

    def render(self, stylesheets=None, enable_hinting=False):
        """Lay out and paginate the document, but do not (yet) export it
        to PDF or another format.

        This returns a :class:`~document.Document` object which provides
        access to individual pages and various meta-data.
        See :meth:`write_pdf` to get a PDF directly.

        .. versionadded:: 0.15

        :param stylesheets:
            An optional list of user stylesheets. (See
            :ref:`stylesheet-origins`\.) List elements are :class:`CSS`
            objects, filenames, URLs, or file-like objects.
        :type enable_hinting: bool
        :param enable_hinting:
            Whether text, borders and background should be *hinted* to fall
            at device pixel boundaries. Should be enabled for pixel-based
            output (like PNG) but not vector based output (like PDF).
        :returns: A :class:`~document.Document` object.

        """
        return Document._render(self, stylesheets, enable_hinting)

    def write_pdf(self, target=None, stylesheets=None, zoom=1,
                  attachments=None):
        """Render the document to a PDF file.

        This is a shortcut for calling :meth:`render`, then
        :meth:`Document.write_pdf() <document.Document.write_pdf>`.

        :param target:
            A filename, file-like object, or :obj:`None`.
        :param stylesheets:
            An optional list of user stylesheets. (See
            :ref:`stylesheet-origins`\.) The list’s elements are
            :class:`CSS` objects, filenames, URLs, or file-like objects.
        :type zoom: float
        :param zoom:
            The zoom factor in PDF units per CSS units.
            **Warning**: All CSS units (even physical, like ``cm``)
            are affected.
            For values other than 1, physical CSS units will thus be “wrong”.
            Page size declarations are affected too, even with keyword values
            like ``@page { size: A3 landscape; }``
        :param attachments: A list of additional file attachments for the
            generated PDF document or :obj:`None`. The list's elements are
            :class:`Attachment` objects, filenames, URLs or file-like objects.
        :returns:
            The PDF as byte string if :obj:`target` is not provided or
            :obj:`None`, otherwise :obj:`None` (the PDF is written to
            :obj:`target`.)

        """
        return self.render(stylesheets).write_pdf(target, zoom, attachments)

    def write_image_surface(self, stylesheets=None, resolution=96):
        surface, _width, _height = (
            self.render(stylesheets, enable_hinting=True)
            .write_image_surface(resolution))
        return surface

    def write_png(self, target=None, stylesheets=None, resolution=96):
        """Paint the pages vertically to a single PNG image.

        There is no decoration around pages other than those specified in CSS
        with ``@page`` rules. The final image is as wide as the widest page.
        Each page is below the previous one, centered horizontally.

        This is a shortcut for calling :meth:`render`, then
        :meth:`Document.write_png() <document.Document.write_png>`.

        :param target:
            A filename, file-like object, or :obj:`None`.
        :param stylesheets:
            An optional list of user stylesheets. (See
            :ref:`stylesheet-origins`\.) The list’s elements are
            :class:`CSS` objects, filenames, URLs, or file-like objects.
        :type resolution: float
        :param resolution:
            The output resolution in PNG pixels per CSS inch. At 96 dpi
            (the default), PNG pixels match the CSS ``px`` unit.
        :returns:
            The image as byte string if :obj:`target` is not provided or
            :obj:`None`, otherwise :obj:`None` (the image is written to
            :obj:`target`.)

        """
        png_bytes, _width, _height = (
            self.render(stylesheets, enable_hinting=True)
            .write_png(target, resolution))
        return png_bytes


class CSS(object):
    """Represents a CSS stylesheet parsed by tinycss.

    An instance is created in the same way as :class:`HTML`, except that
    the ``tree`` parameter is not available. All other parameters are the same.

    ``CSS`` objects have no public attribute or method. They are only meant to
    be used in the :meth:`~HTML.write_pdf`, :meth:`~HTML.write_png` and
    :meth:`~HTML.render` methods of :class:`HTML` objects.

    """
    def __init__(self, guess=None, filename=None, url=None, file_obj=None,
                 string=None, encoding=None, base_url=None,
                 url_fetcher=default_url_fetcher, _check_mime_type=False,
                 media_type='print'):
        result = _select_source(
            guess, filename, url, file_obj, string, tree=None,
            base_url=base_url, url_fetcher=url_fetcher,
            check_css_mime_type=_check_mime_type,)
        with result as (source_type, source, base_url, protocol_encoding):
            if source_type == 'string' and not isinstance(source, bytes):
                # unicode, no encoding
                stylesheet = PARSER.parse_stylesheet(source)
            else:
                if source_type == 'file_obj':
                    source = source.read()
                stylesheet = PARSER.parse_stylesheet_bytes(
                    source, linking_encoding=encoding,
                    protocol_encoding=protocol_encoding)
        self.base_url = base_url
        self.rules = list(preprocess_stylesheet(
            media_type, base_url, stylesheet.rules, url_fetcher))
        # TODO: do not keep this self.stylesheet around?
        self.stylesheet = stylesheet
        for error in self.stylesheet.errors:
            LOGGER.warning(error)


class Attachment(object):
    """Represents a file attachment for a PDF document.

    An instance is created in the same way as :class:`HTML`, except that
    the HTML specific parameters are not supported. An optional description can
    be provided with the ``description`` parameter.

    :param description: A description of the attachment to be included in the
        PDF document. May be :obj:`None`

    """
    def __init__(self, guess=None, filename=None, url=None, file_obj=None,
                 string=None, base_url=None, url_fetcher=default_url_fetcher,
                 description=None):
        self.source = _select_source(
            guess, filename, url, file_obj, string, tree=None,
            base_url=base_url, url_fetcher=url_fetcher)
        self.description = description


@contextlib.contextmanager
def _select_source(guess=None, filename=None, url=None, file_obj=None,
                   string=None, tree=None, base_url=None,
                   url_fetcher=default_url_fetcher, check_css_mime_type=False):
    """
    Check that only one input is not None, and return it with the
    normalized ``base_url``.

    """
    if base_url is not None:
        base_url = ensure_url(base_url)

    nones = [guess is None, filename is None, url is None,
             file_obj is None, string is None, tree is None]
    if nones == [False, True, True, True, True, True]:
        if hasattr(guess, 'read'):
            type_ = 'file_obj'
        elif url_is_absolute(guess):
            type_ = 'url'
        else:
            type_ = 'filename'
        result = _select_source(
            base_url=base_url, url_fetcher=url_fetcher,
            check_css_mime_type=check_css_mime_type,
            # Use str() to work around http://bugs.python.org/issue4978
            # See https://github.com/Kozea/WeasyPrint/issues/97
            **{str(type_): guess})
        with result as result:
            yield result
    elif nones == [True, False, True, True, True, True]:
        if base_url is None:
            base_url = path2url(filename)
        with open(filename, 'rb') as file_obj:
            yield 'file_obj', file_obj, base_url, None
    elif nones == [True, True, False, True, True, True]:
        with fetch(url_fetcher, url) as result:
            if check_css_mime_type and result['mime_type'] != 'text/css':
                LOGGER.warning(
                    'Unsupported stylesheet type %s for %s',
                    result['mime_type'], result['redirected_url'])
                yield 'string', '', base_url, None
            else:
                proto_encoding = result.get('encoding')
                if base_url is None:
                    base_url = result.get('redirected_url', url)
                if 'string' in result:
                    yield 'string', result['string'], base_url, proto_encoding
                else:
                    yield (
                        'file_obj', result['file_obj'], base_url,
                        proto_encoding)
    elif nones == [True, True, True, False, True, True]:
        if base_url is None:
            # filesystem file-like objects have a 'name' attribute.
            name = getattr(file_obj, 'name', None)
            # Some streams have a .name like '<stdin>', not a filename.
            if name and not name.startswith('<'):
                base_url = ensure_url(name)
        yield 'file_obj', file_obj, base_url, None
    elif nones == [True, True, True, True, False, True]:
        yield 'string', string, base_url, None
    elif nones == [True, True, True, True, True, False]:
        yield 'tree', tree, base_url, None
    else:
        raise TypeError('Expected exactly one source, got ' + (
            ', '.join(
                name for i, name in enumerate(
                    'guess filename url file_obj string tree'.split())
                if not nones[i]
            ) or 'nothing'
        ))


# Work around circular imports.
from .css import PARSER, preprocess_stylesheet
from .html import find_base_url, HTML5_UA_STYLESHEET, get_html_metadata
from .document import Document, Page
