# coding: utf8
"""
    WeasyPrint
    ==========

    WeasyPrint converts web documents to PDF.

    The public API is what is accessible from this "root" packages
    without importing sub-modules.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals


VERSION = '0.14'
__version__ = VERSION

# Used for 'User-Agent' in HTTP and 'Creator' in PDF
VERSION_STRING = 'WeasyPrint %s (http://weasyprint.org/)' % VERSION


from .urls import default_url_fetcher
# Make sure the logger is configured early:
from .logger import LOGGER

# No other import here. For this module, do them in functions/methods instead.
# (This reduces the work for eg. 'weasyprint --help')


class Resource(object):
    """Common API for creating instances of :class:`HTML` or :class:`CSS`.

    You can just create an instance with a positional argument
    (ie. ``HTML(something)``) and it will try to guess if the input is
    a filename, an absolute URL, or a file-like object.

    Alternatively, you can name the argument so that no guessing is
    involved:

    * ``HTML(filename=foo)`` a filename, absolute or relative to
      the current directory.
    * ``HTML(url=foo)`` an absolute, fully qualified URL.
    * ``HTML(file_obj=foo)`` a file-like object: any object with
      a :meth:`read` method.
    * ``HTML(string=foo)`` a string of HTML source.
      (This argument must be named.)

    Specifying multiple inputs is an error: ``HTML(filename=foo, url=bar)``

    Optional, additional named arguments:

    * ``encoding``: force the character encoding
    * ``base_url``: used to resolve relative URLs. If not passed explicitly,
      try to use the input filename, URL, or ``name`` attribute of
      file objects.
    * ``url_fetcher``: override the URL fetcher.

    The URL fetcher is used for resources with an ``url`` input as well as
    linked images and stylesheets. It is a function (or any callable) that
    takes a single parameter (the URL) and should raise any exception to
    indicate failure or return a dict with the following keys:

    * One of ``string`` (a byte string) or ``file_obj`` (a file-like object)
    * Optionally: ``mime_type``, a MIME type extracted eg. from a
      *Content-Type* header. If not provided, the type is guessed from
      the file extension in the URL.
    * Optionally: ``encoding``, a character encoding extracted eg.from a
      *charset* parameter in a *Content-Type* header
    * Optionally: ``redirected_url``, the actual URL of the ressource in case
      there were eg. HTTP redirects.

    URL fetchers can defer to the default fetcher::

        def custom_fetcher(url):
            if url.startswith('dynamic-image:')
                return dict(string=generate_image(url[14:]),
                            mime_type='image/png')
            else:
                return weasyprint.default_url_fetcher(url)

    """


class HTML(Resource):
    """Fetch and parse an HTML document with lxml.

    See :class:`Resource` to create an instance.

    """
    def __init__(self, guess=None, filename=None, url=None, file_obj=None,
                 string=None, tree=None, encoding=None, base_url=None,
                 url_fetcher=default_url_fetcher, media_type='print'):
        import lxml.html
        from .html import find_base_url
        from .urls import wrap_url_fetcher
        url_fetcher = wrap_url_fetcher(url_fetcher)

        source_type, source, base_url, protocol_encoding = _select_source(
            guess, filename, url, file_obj, string, tree, base_url,
            url_fetcher)

        if source_type == 'tree':
            result = source
        else:
            if source_type == 'string':
                parse = lxml.html.document_fromstring
            else:
                parse = lxml.html.parse
            if not encoding:
                encoding = protocol_encoding
            parser = lxml.html.HTMLParser(encoding=encoding)
            result = parse(source, parser=parser)
            if result is None:
                raise ValueError('Error while parsing HTML')
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

    def _ua_stylesheet(self):
        from .html import HTML5_UA_STYLESHEET
        return [HTML5_UA_STYLESHEET]

    def _get_document(self, stylesheets, enable_hinting, ua_stylesheets=None):
        if ua_stylesheets is None:
            ua_stylesheets = self._ua_stylesheet()
        user_stylesheets = [css if hasattr(css, 'rules')
                            else CSS(guess=css, media_type=self.media_type)
                            for css in stylesheets or []]
        from .document import Document
        return Document(self.root_element, enable_hinting, self.url_fetcher,
                        self.media_type, user_stylesheets, ua_stylesheets)

    def write_pdf(self, target=None, stylesheets=None):
        """Render the document to PDF.

        :param target:
            a filename, file-like object, or :obj:`None`.
        :param stylesheets:
            a list of user stylsheets, as :class:`CSS` objects, filenames,
            URLs, or file-like objects
        :returns:
            If :obj:`target` is :obj:`None`, a PDF byte string.
        """
        document = self._get_document(stylesheets, enable_hinting=False)
        return document.write_pdf(target)

    def write_png(self, target=None, stylesheets=None, resolution=None):
        """Render the document to a single PNG image.

        :param target:
            a filename, file-like object, or :obj:`None`.
        :param stylesheets:
            a list of user stylsheets, as :class:`CSS` objects, filenames,
            URLs, or file-like objects
        :returns:
            If :obj:`target` is :obj:`None`, a PNG byte string.
        """
        document = self._get_document(stylesheets, enable_hinting=True)
        return document.write_png(target, resolution)

    def get_png_pages(self, stylesheets=None, resolution=None,
                      _with_pages=False):
        """Render the document to multiple PNG images, one per page.

        :param stylesheets:
            a list of user stylsheets, as :class:`CSS` objects, filenames,
            URLs, or file-like objects
        :returns:
            A generator of ``(width, height, png_bytes)`` tuples, one for
            each page, in order.

        """
        document = self._get_document(stylesheets, enable_hinting=True)
        return document.get_png_pages(resolution, _with_pages)


class CSS(Resource):
    """Fetch and parse a CSS stylesheet.

    See :class:`Resource` to create an instance. A :class:`CSS` object
    is not useful on its own but can be passed to :meth:`HTML.write_pdf` or
    :meth:`HTML.write_png`.

    """
    def __init__(self, guess=None, filename=None, url=None, file_obj=None,
                 string=None, encoding=None, base_url=None,
                 url_fetcher=default_url_fetcher, _check_mime_type=False,
                 media_type='print'):
        from .css import PARSER, preprocess_stylesheet

        source_type, source, base_url, protocol_encoding = _select_source(
            guess, filename, url, file_obj, string, tree=None,
            base_url=base_url, url_fetcher=url_fetcher,
            check_css_mime_type=_check_mime_type,)

        kwargs = dict(linking_encoding=encoding,
                      protocol_encoding=protocol_encoding)
        if source_type == 'string':
            if isinstance(source, bytes):
                method = 'parse_stylesheet_bytes'
            else:
                # unicode, no encoding
                method = 'parse_stylesheet'
                kwargs.clear()
        else:
            # file_obj or filename
            method = 'parse_stylesheet_file'
        # TODO: do not keep this?
        self.stylesheet = getattr(PARSER, method)(source, **kwargs)
        self.base_url = base_url
        self.rules = list(preprocess_stylesheet(
            media_type, base_url, self.stylesheet.rules, url_fetcher))
        for error in self.stylesheet.errors:
            LOGGER.warn(error)


def _select_source(guess=None, filename=None, url=None, file_obj=None,
                   string=None, tree=None, base_url=None,
                   url_fetcher=default_url_fetcher, check_css_mime_type=False):
    """
    Check that only one input is not None, and return it with the
    normalized ``base_url``.

    """
    from .urls import path2url, ensure_url, url_is_absolute
    from .urls import wrap_url_fetcher
    url_fetcher = wrap_url_fetcher(url_fetcher)

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
        return _select_source(
            base_url=base_url, url_fetcher=url_fetcher,
            check_css_mime_type=check_css_mime_type,
            **{type_: guess})
    if nones == [True, False, True, True, True, True]:
        if base_url is None:
            base_url = path2url(filename)
        return 'filename', filename, base_url, None
    if nones == [True, True, False, True, True, True]:
        result = url_fetcher(url)
        if check_css_mime_type and result['mime_type'] != 'text/css':
            LOGGER.warn('Unsupported stylesheet type %s for %s',
                result['mime_type'], result['redirected_url'])
            return 'string', '', base_url, None
        protocol_encoding = result.get('encoding')
        if base_url is None:
            base_url = result.get('redirected_url', url)
        if 'string' in result:
            return 'string', result['string'], base_url, protocol_encoding
        else:
            return 'file_obj', result['file_obj'], base_url, protocol_encoding
    if nones == [True, True, True, False, True, True]:
        if base_url is None:
            # filesystem file objects have a 'name' attribute.
            name = getattr(file_obj, 'name', None)
            # Some streams have a .name like '<stdin>', not a filename.
            if name and not name.startswith('<'):
                base_url = ensure_url(name)
        return 'file_obj', file_obj, base_url, None
    if nones == [True, True, True, True, False, True]:
        return 'string', string, base_url, None
    if nones == [True, True, True, True, True, False]:
        return 'tree', tree, base_url, None

    raise TypeError('Expected exactly one source, got %i' % nones.count(False))
