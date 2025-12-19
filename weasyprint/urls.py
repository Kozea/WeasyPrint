"""Various utility functions and classes for URL management."""

import codecs
import contextlib
import os.path
import re
import sys
import traceback
import warnings
import zlib
from gzip import GzipFile
from io import BytesIO, StringIO
from pathlib import Path
from urllib.parse import quote, unquote, urljoin, urlsplit
from urllib.request import Request, pathname2url, url2pathname, urlopen

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
    path = pathname2url(path)
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
        "please use URLFetcher instead.",
        category=DeprecationWarning)
    fetcher = URLFetcher(timeout, ssl_context, http_headers, allowed_protocols)
    return fetcher.fetch(url)


class URLFetchingError(IOError):
    """Some error happened when fetching an URL."""


class FatalURLFetchingError(IOError):
    """Some error happened when fetching an URL and must stop the rendering."""


class URLFetcher:
    """Fetcher of external resources such as images or stylesheets.

    Another class inheriting from this class, with a ``fetch`` method that has a
    compatible signature, can be given as the ``url_fetcher`` argument to :class:`HTML`
    or :class:`CSS`. (See :ref:`URL Fetchers`.)

    """

    def __init__(self, timeout=10, ssl_context=None, http_headers=None,
                 allowed_protocols=None, **kwargs):
        #: The number of seconds before HTTP requests are dropped.
        self.timeout = timeout
        #: An SSL context used for HTTP requests.
        self.ssl_context = ssl_context
        #: Additional HTTP headers used for HTTP requests.
        self.http_headers = http_headers
        #: A set of authorized protocols.
        self.allowed_protocols = allowed_protocols

    def fetch(self, url):
        """Fetch a given URL.

        :raises: An exception indicating failure, e.g. :obj:`ValueError` on
            syntactically invalid URL.
        :returns: A :obj:`URLFetcherResource` instance, or a :obj:`dict` that can
            be splatted into the constructor.

        """

        # Discard URLs with no or invalid protocol.
        if not UNICODE_SCHEME_RE.match(url):  # pragma: no cover
            raise ValueError(f'Not an absolute URI: {url}')


        # Discard URLs with forbidden protocol.
        if self.allowed_protocols is not None:
            if url.split('://', 1)[0].lower() not in self.allowed_protocols:
                raise ValueError(f'URI uses disallowed protocol: {url}')

        # Remove query and fragment parts from file URLs.
        # See https://bugs.python.org/issue34702.
        if url.lower().startswith('file://'):
            url = url.split('?')[0]
            path = url2pathname(url.removeprefix('file:'))
        else:
            path = None

        # Transform Unicode IRI to ASCII URI.
        url = iri_to_uri(url)

        # Define HTTP headers.
        if self.http_headers is not None:
            http_headers = {**HTTP_HEADERS, **self.http_headers}
        else:
            http_headers = HTTP_HEADERS

        # Open URL.
        response = urlopen(
            Request(url, headers=http_headers), timeout=self.timeout,
            context=self.ssl_context)
        resource_args = {
            'url': response.url,
            'mime_type': response.headers.get_content_type(),
            'encoding': response.headers.get_param('charset'),
            'filename': response.headers.get_filename(),
            'path': path,
        }

        # Decompress response.
        content_encoding = response.headers.get('Content-Encoding')
        if content_encoding == 'gzip':
            resource_args['file_obj'] = StreamingGzipFile(fileobj=response)
        elif content_encoding == 'deflate':
            data = response.read()
            try:
                resource_args['string'] = zlib.decompress(data)
            except zlib.error:
                # Try without zlib header or checksum.
                resource_args['string'] = zlib.decompress(data, -15)
        else:
            resource_args['file_obj'] = response

        return URLFetcherResource(**resource_args)

    def __call__(self, url):
        return self.fetch(url)


class URLFetcherResource:
    """The result of a URL fetcher invocation."""
    def __init__(self, url, string=None, file_obj=None, mime_type=None,
                 encoding=None, filename=None, path=None, **kwargs):
        """Constructs a new instance from a string or file-like object.

        If a ``file_obj`` is given, it is the caller’s responsibility
        to call ``file_obj.close()``. The default function used internally to
        fetch data in WeasyPrint tries to close the file object after
        retreiving; but if this URL fetcher is used elsewhere, the file object
        has to be closed manually.

        """

        #: The string or file-like object passed to the constructor.
        if string is None:
            assert file_obj is not None, 'string or file_obj must be given'
            self.file_obj = file_obj
        elif isinstance(string, str):
            self.file_obj = StringIO(string)
        else:
            self.file_obj = BytesIO(string)
        #: The URL of the resource.
        self.url = url
        #: An optional MIME type extracted e.g. from a *Content-Type* header. If not
        #: provided, the type is guessed from the file extension in the URL.
        self.mime_type = mime_type
        #: An optional character encoding, extracted from a *charset* parameter in a
        #: *Content-Type* header.
        self.encoding = encoding
        #: The possible filename of the resource, usually derived from the *filename*
        #: parameter in a *Content-Disposition* : header.
        self.filename = filename
        #: The path of the resource, if it is stored on the local filesystem.
        self.path = path


@contextlib.contextmanager
def fetch(url_fetcher, url):
    """Fetch an ``url`` with ```url_fetcher``, fill in optional data, and clean up.

    Fatal errors must raise a ``FatalURLFetchingError`` that stops the rendering. All
    other exceptions are catched and raise an ``URLFetchingError``, that is usually
    catched by the code that fetches the resource and emits a warning.

    """

    try:
        resource = url_fetcher(url)
    except FatalURLFetchingError as exception:
        raise exception
    except Exception as exception:
        raise URLFetchingError(f'{type(exception).__name__}: {exception}')

    if isinstance(resource, dict):
        warnings.warn(
            "Returning dicts in URL fetchers is deprecated and will be removed "
            "in WeasyPrint 69.0, please return URLFetcherResource instead.",
            category=DeprecationWarning)
        if 'url' not in resource:
            resource['url'] = resource.get('redirected_url', url)
        resource = URLFetcherResource(**resource)

    assert isinstance(resource, URLFetcherResource), (
        'URL fetcher must return either a dict or a URLFetcherResource instance')

    try:
        yield resource
    finally:
        try:
            resource.file_obj.close()
        except Exception:  # pragma: no cover
            # May already be closed or something.
            # This is just cleanup anyway: log but make it non-fatal.
            LOGGER.warning(
                'Error when closing stream for %s:\n%s',
                url, traceback.format_exc())
