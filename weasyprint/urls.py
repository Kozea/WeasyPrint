"""Various utility functions and classes for URL management."""

import codecs
import contextlib
import os.path
import re
import sys
import traceback
import zlib
from gzip import GzipFile
from pathlib import Path
from urllib.parse import quote, unquote, urljoin, urlsplit
from urllib.request import Request, pathname2url, urlopen

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
    url = url.encode(
        FILESYSTEM_ENCODING if url.startswith('file:') else 'utf-8')
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
    wants_trailing_slash = path.endswith(os.path.sep) or path.endswith('/')
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


def default_url_fetcher(url, timeout=10, ssl_context=None):
    """Fetch an external resource such as an image or stylesheet.

    Another callable with the same signature can be given as the
    ``url_fetcher`` argument to :class:`HTML` or :class:`CSS`.
    (See :ref:`URL Fetchers`.)

    :param str url:
        The URL of the resource to fetch.
    :param int timeout:
        The number of seconds before HTTP requests are dropped.
    :param ssl.SSLContext ssl_context:
        An SSL context used for HTTP requests.
    :raises: An exception indicating failure, e.g. :obj:`ValueError` on
        syntactically invalid URL.
    :returns: A :obj:`dict` with the following keys:

        * One of ``string`` (a :obj:`bytestring <bytes>`) or ``file_obj``
          (a :term:`file object`).
        * Optionally: ``mime_type``, a MIME type extracted e.g. from a
          *Content-Type* header. If not provided, the type is guessed from the
          file extension in the URL.
        * Optionally: ``encoding``, a character encoding extracted e.g. from a
          *charset* parameter in a *Content-Type* header
        * Optionally: ``redirected_url``, the actual URL of the resource
          if there were e.g. HTTP redirects.
        * Optionally: ``filename``, the filename of the resource. Usually
          derived from the *filename* parameter in a *Content-Disposition*
          header

        If a ``file_obj`` key is given, it is the caller’s responsibility
        to call ``file_obj.close()``. The default function used internally to
        fetch data in WeasyPrint tries to close the file object after
        retreiving; but if this URL fetcher is used elsewhere, the file object
        has to be closed manually.

    """
    if UNICODE_SCHEME_RE.match(url):
        # See https://bugs.python.org/issue34702
        if url.startswith('file://'):
            url = url.split('?')[0]

        url = iri_to_uri(url)
        response = urlopen(
            Request(url, headers=HTTP_HEADERS), timeout=timeout,
            context=ssl_context)
        response_info = response.info()
        result = {
            'redirected_url': response.geturl(),
            'mime_type': response_info.get_content_type(),
            'encoding': response_info.get_param('charset'),
            'filename': response_info.get_filename(),
        }
        content_encoding = response_info.get('Content-Encoding')
        if content_encoding == 'gzip':
            result['file_obj'] = StreamingGzipFile(fileobj=response)
        elif content_encoding == 'deflate':
            data = response.read()
            try:
                result['string'] = zlib.decompress(data)
            except zlib.error:
                # Try without zlib header or checksum
                result['string'] = zlib.decompress(data, -15)
        else:
            result['file_obj'] = response
        return result
    else:  # pragma: no cover
        raise ValueError('Not an absolute URI: %r' % url)


class URLFetchingError(IOError):
    """Some error happened when fetching an URL."""


@contextlib.contextmanager
def fetch(url_fetcher, url):
    """Call an url_fetcher, fill in optional data, and clean up."""
    try:
        result = url_fetcher(url)
    except Exception as exception:
        raise URLFetchingError(f'{type(exception).__name__}: {exception}')
    result.setdefault('redirected_url', url)
    result.setdefault('mime_type', None)
    if 'file_obj' in result:
        try:
            yield result
        finally:
            try:
                result['file_obj'].close()
            except Exception:  # pragma: no cover
                # May already be closed or something.
                # This is just cleanup anyway: log but make it non-fatal.
                LOGGER.warning(
                    'Error when closing stream for %s:\n%s',
                    url, traceback.format_exc())
    else:
        yield result
