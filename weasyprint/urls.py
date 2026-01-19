"""Various utility functions and classes for URL management."""

import codecs
import contextlib
import os.path
import re
import sys
import traceback
import warnings
import zlib
from email.message import EmailMessage
from gzip import GzipFile
from io import BytesIO, StringIO
from pathlib import Path
from urllib import request
from urllib.parse import quote, unquote, urljoin, urlsplit

from . import __version__
from .logger import LOGGER

# See https://stackoverflow.com/a/11687993/1162888
# Both are needed in Python 3 as the re module does not like to mix
# https://datatracker.ietf.org/doc/html/rfc3986#section-3.1
UNICODE_SCHEME_RE = re.compile('^([a-zA-Z][a-zA-Z0-9.+-]+):')
BYTES_SCHEME_RE = re.compile(b'^([a-zA-Z][a-zA-Z0-9.+-]+):')

# getfilesystemencoding() on Linux is sometimes stupid…
FILESYSTEM_ENCODING = sys.getfilesystemencoding()
try:  # pragma: no cover
    if codecs.lookup(FILESYSTEM_ENCODING).name == 'ascii':
        FILESYSTEM_ENCODING = 'utf-8'
except LookupError:  # pragma: no cover
    FILESYSTEM_ENCODING = 'utf-8'

HTTP_HEADERS = {
    'User-Agent': f'WeasyPrint {__version__}',
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate',
}


class StreamingGzipFile(GzipFile):
    def __init__(self, fileobj):
        GzipFile.__init__(self, fileobj=fileobj)
        self.fileobj_to_close = fileobj

    def close(self):
        GzipFile.close(self)
        self.fileobj_to_close.close()

    def seekable(self):
        return False


def iri_to_uri(url):
    """Turn a Unicode IRI into an ASCII-only URI that conforms to RFC 3986."""
    if url.startswith('data:'):
        # Data URIs can be huge, but don’t need this anyway.
        return url
    # Use UTF-8 as per RFC 3987 (IRI), except for file://
    url = url.encode(FILESYSTEM_ENCODING if url.startswith('file:') else 'utf-8')
    # This is a full URI, not just a component. Only %-encode characters
    # that are not allowed at all in URIs. Everthing else is "safe":
    # * Reserved characters: /:?#[]@!$&'()*+,;=
    # * Unreserved characters: ASCII letters, digits and -._~
    #   Of these, only '~' is not in urllib’s "always safe" list.
    # * '%' to avoid double-encoding
    return quote(url, safe=b"/:?#[]@!$&'()*+,;=~%")


def path2url(path):
    """Return file URL of `path`.

    Accepts 'str', 'bytes' or 'Path', returns 'str'.

    """
    # Ensure 'str'
    if isinstance(path, Path):
        path = str(path)
    elif isinstance(path, bytes):
        path = path.decode(FILESYSTEM_ENCODING)
    # If a trailing path.sep is given, keep it
    wants_trailing_slash = path.endswith((os.path.sep, '/'))
    path = os.path.abspath(path)
    if wants_trailing_slash or os.path.isdir(path):
        # Make sure directory names have a trailing slash.
        # Otherwise relative URIs are resolved from the parent directory.
        path += os.path.sep
        wants_trailing_slash = True
    path = request.pathname2url(path)
    # On Windows pathname2url cuts off trailing slash
    if wants_trailing_slash and not path.endswith('/'):
        path += '/'  # pragma: no cover
    if path.startswith('///'):
        # On Windows pathname2url(r'C:\foo') is apparently '///C:/foo'
        # That enough slashes already.
        return f'file:{path}'  # pragma: no cover
    else:
        return f'file://{path}'


def url_is_absolute(url):
    """Return whether an URL (bytes or string) is absolute."""
    scheme = UNICODE_SCHEME_RE if isinstance(url, str) else BYTES_SCHEME_RE
    return bool(scheme.match(url))


def get_url_attribute(element, attr_name, base_url, allow_relative=False):
    """Get the URI corresponding to the ``attr_name`` attribute.

    Return ``None`` if:

    * the attribute is empty or missing or,
    * the value is a relative URI but the document has no base URI and
      ``allow_relative`` is ``False``.

    Otherwise return an URI, absolute if possible.

    """
    value = element.get(attr_name, '').strip()
    if value:
        return url_join(
            base_url or '', value, allow_relative, '<%s %s="%s">',
            (element.tag, attr_name, value))


def get_url_tuple(url, base_url):
    """Get tuple describing internal or external URI."""
    if url.startswith('#'):
        return ('internal', unquote(url[1:]))
    elif url_is_absolute(url):
        return ('external', iri_to_uri(url))
    elif base_url:
        return ('external', iri_to_uri(urljoin(base_url, url)))


def url_join(base_url, url, allow_relative, context, context_args):
    """Like urllib.urljoin, but warn if base_url is required but missing."""
    if url_is_absolute(url):
        return iri_to_uri(url)
    elif base_url:
        return iri_to_uri(urljoin(base_url, url))
    elif allow_relative:
        return iri_to_uri(url)
    else:
        LOGGER.error(
            f'Relative URI reference without a base URI: {context}',
            *context_args)
        return None


def get_link_attribute(element, attr_name, base_url):
    """Get the URL value of an element attribute.

    Return ``('external', absolute_uri)``, or ``('internal',
    unquoted_fragment_id)``, or ``None``.

    """
    attr_value = element.get(attr_name, '').strip()
    if attr_value.startswith('#') and len(attr_value) > 1:
        # Do not require a base_url when the value is just a fragment.
        return ('url', ('internal', unquote(attr_value[1:])))
    uri = get_url_attribute(element, attr_name, base_url, allow_relative=True)
    if uri:
        if base_url:
            try:
                parsed = urlsplit(uri)
            except ValueError:
                LOGGER.warning('Malformed URL: %s', uri)
            else:
                try:
                    parsed_base = urlsplit(base_url)
                except ValueError:
                    LOGGER.warning('Malformed base URL: %s', base_url)
                else:
                    # Compare with fragments removed
                    if parsed.fragment and parsed[:-1] == parsed_base[:-1]:
                        return ('url', ('internal', unquote(parsed.fragment)))
        return ('url', ('external', uri))


def ensure_url(string):
    """Get a ``scheme://path`` URL from ``string``.

    If ``string`` looks like an URL, return it unchanged. Otherwise assume a
    filename and convert it to a ``file://`` URL.

    """
    return string if url_is_absolute(string) else path2url(string)


def default_url_fetcher(url, timeout=10, ssl_context=None, http_headers=None,
                        allowed_protocols=None):
    """Fetch an external resource such as an image or stylesheet.

    This function is deprecated, use ``URLFetcher`` instead.

    """
    warnings.warn(
        "default_url_fetcher is deprecated and will be removed in WeasyPrint 69.0, "
        "please use URLFetcher instead. For security reasons, HTTP redirects are not "
        "supported anymore with default_url_fetcher, but are with URLFetcher.\n\nSee "
        "https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#url-fetchers",
        category=DeprecationWarning)
    fetcher = URLFetcher(
        timeout, ssl_context, http_headers, allowed_protocols, allow_redirects=False)
    return fetcher.fetch(url)


@contextlib.contextmanager
def select_source(guess=None, filename=None, url=None, file_obj=None, string=None,
                  base_url=None, url_fetcher=None, check_css_mime_type=False):
    """If only one input is given, return it.

    Yield a file object, the base url, the protocol encoding and the protocol mime-type.

    """
    if base_url is not None:
        base_url = ensure_url(base_url)
    if url_fetcher is None:
        url_fetcher = URLFetcher()

    selected_params = [
        param for param in (guess, filename, url, file_obj, string) if
        param is not None]
    if len(selected_params) != 1:
        source = ', '.join(selected_params) or 'nothing'
        raise TypeError(f'Expected exactly one source, got {source}')
    elif guess is not None:
        kwargs = {
            'base_url': base_url,
            'url_fetcher': url_fetcher,
            'check_css_mime_type': check_css_mime_type,
        }
        if hasattr(guess, 'read'):
            kwargs['file_obj'] = guess
        elif isinstance(guess, Path):
            kwargs['filename'] = guess
        elif url_is_absolute(guess):
            kwargs['url'] = guess
        else:
            kwargs['filename'] = guess
        result = select_source(**kwargs)
        with result as result:
            yield result
    elif filename is not None:
        if base_url is None:
            base_url = path2url(filename)
        with open(filename, 'rb') as file_obj:
            yield file_obj, base_url, None, None
    elif url is not None:
        with fetch(url_fetcher, url) as response:
            if check_css_mime_type and response.content_type != 'text/css':
                LOGGER.error(
                    f'Unsupported stylesheet type {response.content_type} '
                    f'for {response.url}')
                yield StringIO(''), base_url, None, None
            else:
                if base_url is None:
                    base_url = response.url
                yield response, base_url, response.charset, response.content_type
    elif file_obj is not None:
        if base_url is None:
            # filesystem file-like objects have a 'name' attribute.
            name = getattr(file_obj, 'name', None)
            # Some streams have a .name like '<stdin>', not a filename.
            if name and not name.startswith('<'):
                base_url = ensure_url(name)
        yield file_obj, base_url, None, None
    else:
        if isinstance(string, str):
            yield StringIO(string), base_url, None, None
        else:
            yield BytesIO(string), base_url, None, None


class URLFetchingError(IOError):
    """Some error happened when fetching an URL."""


class FatalURLFetchingError(BaseException):
    """Some error happened when fetching an URL and must stop the rendering."""


class URLFetcher(request.OpenerDirector):
    """Fetcher of external resources such as images or stylesheets.

    :param int timeout: The number of seconds before HTTP requests are dropped.
    :param ssl.SSLContext ssl_context: An SSL context used for HTTPS requests.
    :param dict http_headers: Additional HTTP headers used for HTTP requests.
    :type allowed_protocols: :term:`sequence`
    :param allowed_protocols: A set of authorized protocols, :obj:`None` means all.
    :param bool allow_redirects: Whether HTTP redirects must be followed.
    :param bool fail_on_errors: Whether HTTP errors should stop the rendering.

    Another class inheriting from this class, with a ``fetch`` method that has a
    compatible signature, can be given as the ``url_fetcher`` argument to
    :class:`weasyprint.HTML` or :class:`weasyprint.CSS`.

    See :ref:`URL Fetchers` for more information and examples.

    """

    def __init__(self, timeout=10, ssl_context=None, http_headers=None,
                 allowed_protocols=None, allow_redirects=True, fail_on_errors=False,
                 **kwargs):
        super().__init__()
        handlers = [
            request.ProxyHandler(), request.UnknownHandler(), request.HTTPHandler(),
            request.HTTPDefaultErrorHandler(), request.FTPHandler(),
            request.FileHandler(), request.HTTPErrorProcessor(), request.DataHandler(),
            request.HTTPSHandler(context=ssl_context)]
        if allow_redirects:
            handlers.append(request.HTTPRedirectHandler())
        for handler in handlers:
            self.add_handler(handler)

        self._timeout = timeout
        self._http_headers = {**HTTP_HEADERS, **(http_headers or {})}
        self._allowed_protocols = allowed_protocols
        self._fail_on_errors = fail_on_errors

    def fetch(self, url, headers=None):
        """Fetch a given URL.

        :returns: A :obj:`URLFetcherResponse` instance.
        :raises: An exception indicating failure, e.g. :obj:`ValueError` on
            syntactically invalid URL. All exceptions are catched internally by
            WeasyPrint, except when they inherit from :obj:`FatalURLFetchingError`.

        """
        # Discard URLs with no or invalid protocol.
        if not UNICODE_SCHEME_RE.match(url):  # pragma: no cover
            raise ValueError(f'Not an absolute URI: {url}')

        # Discard URLs with forbidden protocol.
        if self._allowed_protocols is not None:
            if url.split('://', 1)[0].lower() not in self._allowed_protocols:
                raise ValueError(f'URI uses disallowed protocol: {url}')

        # Remove query and fragment parts from file URLs.
        # See https://bugs.python.org/issue34702.
        if url.lower().startswith('file://'):
            url = url.split('?')[0]

        # Transform Unicode IRI to ASCII URI.
        url = iri_to_uri(url)

        # Open URL.
        headers = {**self._http_headers, **(headers or {})}
        http_request = request.Request(url, headers=headers)
        response = super().open(http_request, timeout=self._timeout)

        # Decompress response.
        body = response
        if 'Content-Encoding' in response.headers:
            content_encoding = response.headers['Content-Encoding']
            del response.headers['Content-Encoding']
            if content_encoding == 'gzip':
                body = StreamingGzipFile(fileobj=response)
            elif content_encoding == 'deflate':
                data = response.read()
                try:
                    body = zlib.decompress(data)
                except zlib.error:
                    # Try without zlib header or checksum.
                    body = zlib.decompress(data, -15)

        return URLFetcherResponse(response.url, body, response.headers, response.status)

    def open(self, url, data=None, timeout=None):
        if isinstance(url, request.Request):
            return self.fetch(url.full_url, url.headers)
        return self.fetch(url)

    def __call__(self, url):
        return self.fetch(url)


class URLFetcherResponse:
    """The HTTP response of an URL fetcher.

    :param str url: The URL of the HTTP response.
    :type body: :class:`str`, :class:`bytes` or :term:`file object`
    :param body: The body of the HTTP response.
    :type headers: dict or email.message.EmailMessage
    :param headers: The headers of the HTTP response.
    :param str status: The status of the HTTP response.

    Has the same interface as :class:`urllib.response.addinfourl`.

    If a :term:`file object` is given for the body, it is the caller’s responsibility to
    call ``close()`` on it. The default function used internally to fetch data in
    WeasyPrint tries to close the file object after retreiving; but if this URL fetcher
    is used elsewhere, the file object has to be closed manually.

    """
    def __init__(self, url, body=None, headers=None, status='200 OK', **kwargs):
        self.url = url
        self.status = status

        if isinstance(headers, EmailMessage):
            self.headers = headers
        else:
            self.headers = EmailMessage()
            for key, value in (headers or {}).items():
                self.headers[key] = value

        if hasattr(body, 'read'):
            self._file_obj = body
        elif isinstance(body, str):
            self.headers.set_param('charset', 'utf-8')
            self._file_obj = BytesIO(body.encode('utf-8'))
        else:
            self._file_obj = BytesIO(body)

    def read(self, *args, **kwargs):
        return self._file_obj.read(*args, **kwargs)

    def close(self):
        try:
            self._file_obj.close()
        except Exception:  # pragma: no cover
            # May already be closed or something.
            # This is just cleanup anyway: log but make it non-fatal.
            LOGGER.warning(
                'Error when closing stream for %s:\n%s',
                self.url, traceback.format_exc())

    @property
    def path(self):
        if self.url.startswith('file:'):
            return request.url2pathname(self.url.split('?')[0].removeprefix('file:'))

    @property
    def content_type(self):
        return self.headers.get_content_type()

    @property
    def charset(self):
        return self.headers.get_param('charset')


@contextlib.contextmanager
def fetch(url_fetcher, url):
    """Fetch an ``url`` with ```url_fetcher``, fill in optional data, and clean up.

    Fatal errors must raise a ``FatalURLFetchingError`` that stops the rendering. All
    other exceptions are catched and raise an ``URLFetchingError``, that is usually
    catched by the code that fetches the resource and emits a warning.

    """
    try:
        resource = url_fetcher(url)
    except Exception as exception:
        if getattr(url_fetcher, '_fail_on_errors', False):
            raise FatalURLFetchingError(f'Error fetching "{url}"') from exception
        raise URLFetchingError(f'{type(exception).__name__}: {exception}')

    if isinstance(resource, dict):
        warnings.warn(
            "Returning dicts in URL fetchers is deprecated and will be removed "
            "in WeasyPrint 69.0, please return URLFetcherResponse instead.",
            category=DeprecationWarning)
        if 'url' not in resource:
            resource['url'] = resource.get('redirected_url', url)
        resource['body'] = resource.get('file_obj', resource.get('string'))
        content_type = resource.get('mime_type', 'application/octet-stream')
        if charset := resource.get('encoding'):
            content_type += f';{charset}'
        resource['headers'] = {'Content-Type': content_type}
        resource = URLFetcherResponse(**resource)

    assert isinstance(resource, URLFetcherResponse), (
        'URL fetcher must return either a dict or a URLFetcherResponse instance')

    try:
        yield resource
    finally:
        resource.close()
