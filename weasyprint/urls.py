"""
    weasyprint.utils
    ----------------

    Various utility functions and classes.

    :copyright: Copyright 2011-2018 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import codecs
import contextlib
import email
import gzip
import io
import os.path
import re
import sys
import traceback
import zlib
from base64 import decodebytes
from gzip import GzipFile
from urllib.parse import quote, unquote, urljoin, urlsplit
from urllib.request import Request, pathname2url, urlopen

from . import VERSION_STRING
from .logger import LOGGER

# See http://stackoverflow.com/a/11687993/1162888
# Both are needed in Python 3 as the re module does not like to mix
# http://tools.ietf.org/html/rfc3986#section-3.1
UNICODE_SCHEME_RE = re.compile('^([a-zA-Z][a-zA-Z0-9.+-]+):')
BYTES_SCHEME_RE = re.compile(b'^([a-zA-Z][a-zA-Z0-9.+-]+):')

# getfilesystemencoding() on Linux is sometimes stupid...
FILESYSTEM_ENCODING = sys.getfilesystemencoding()
try:
    if codecs.lookup(FILESYSTEM_ENCODING).name == 'ascii':
        FILESYSTEM_ENCODING = 'utf-8'
except LookupError:
    FILESYSTEM_ENCODING = 'utf-8'


class StreamingGzipFile(GzipFile):
    def __init__(self, fileobj):
        GzipFile.__init__(self, fileobj=fileobj)
        self.fileobj_to_close = fileobj

    def close(self):
        GzipFile.close(self)
        self.fileobj_to_close.close()

    # Inform html5lib to not rely on these:
    seek = tell = None


def parse_email(data):
    if isinstance(data, bytes):
        data = data.decode('utf8')
    return email.message_from_string(data)


def iri_to_uri(url):
    """Turn an IRI that can contain any Unicode character into an ASCII-only
    URI that conforms to RFC 3986.
    """
    if url.startswith('data:'):
        # Data URIs can be huge, but don’t need this anyway.
        return url
    # Use UTF-8 as per RFC 3987 (IRI), except for file://
    url = url.encode(FILESYSTEM_ENCODING
                     if url.startswith('file:') else 'utf-8')
    # This is a full URI, not just a component. Only %-encode characters
    # that are not allowed at all in URIs. Everthing else is "safe":
    # * Reserved characters: /:?#[]@!$&'()*+,;=
    # * Unreserved characters: ASCII letters, digits and -._~
    #   Of these, only '~' is not in urllib’s "always safe" list.
    # * '%' to avoid double-encoding
    return quote(url, safe=b"/:?#[]@!$&'()*+,;=~%")


def path2url(path):
    """Return file URL of `path`.
    Accepts 'str' or 'bytes', returns 'str'
    """
    # Ensure 'str'
    if isinstance(path, bytes):
        path = path.decode(sys.getfilesystemencoding())
    # if a trailing path.sep is given -- keep it
    wants_trailing_slash = path.endswith(os.path.sep) or path.endswith('/')
    path = os.path.abspath(path)
    if wants_trailing_slash or os.path.isdir(path):
        # Make sure directory names have a trailing slash.
        # Otherwise relative URIs are resolved from the parent directory.
        path += os.path.sep
        wants_trailing_slash = True
    path = pathname2url(path)
    # on Windows pathname2url cuts off trailing slash
    if wants_trailing_slash and not path.endswith('/'):
        path += '/'
    if path.startswith('///'):
        # On Windows pathname2url(r'C:\foo') is apparently '///C:/foo'
        # That enough slashes already.
        return 'file:' + path
    else:
        return 'file://' + path


def url_is_absolute(url):
    return bool(
        (UNICODE_SCHEME_RE if isinstance(url, str) else BYTES_SCHEME_RE)
        .match(url))


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
        LOGGER.error('Relative URI reference without a base URI: ' + context,
                     *context_args)
        return None


def get_link_attribute(element, attr_name, base_url):
    """Return ('external', absolute_uri) or
    ('internal', unquoted_fragment_id) or None.

    """
    attr_value = element.get(attr_name, '').strip()
    if attr_value.startswith('#') and len(attr_value) > 1:
        # Do not require a base_url when the value is just a fragment.
        return ('url', ('internal', unquote(attr_value[1:])))
    uri = get_url_attribute(element, attr_name, base_url, allow_relative=True)
    if uri:
        if base_url:
            parsed = urlsplit(uri)
            # Compare with fragments removed
            if parsed[:-1] == urlsplit(base_url)[:-1]:
                return ('url', ('internal', unquote(parsed.fragment)))
        return ('url', ('external', uri))


def ensure_url(string):
    """Get a ``scheme://path`` URL from ``string``.

    If ``string`` looks like an URL, return it unchanged. Otherwise assume a
    filename and convert it to a ``file://`` URL.

    """
    return string if url_is_absolute(string) else path2url(string)


def safe_decodebytes(data):
    """Decode base64, padding being optional.

    "From a theoretical point of view, the padding character is not needed,
     since the number of missing bytes can be calculated from the number
     of Base64 digits."

    https://en.wikipedia.org/wiki/Base64#Padding

    :param data: Base64 data as an ASCII byte string
    :returns: The decoded byte string.

    """
    missing_padding = 4 - len(data) % 4
    if missing_padding:
        data += b'=' * missing_padding
    return decodebytes(data)


HTTP_HEADERS = {
    'User-Agent': VERSION_STRING,
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate',
}


def default_url_fetcher(url, timeout=10):
    """Fetch an external resource such as an image or stylesheet.

    Another callable with the same signature can be given as the
    :obj:`url_fetcher` argument to :class:`HTML` or :class:`CSS`.
    (See :ref:`url-fetchers`.)

    :type url: Unicode string
    :param url: The URL of the resource to fetch.
    :raises: An exception indicating failure, e.g. ``ValueError`` on
        syntactically invalid URL.
    :returns: A dict with the following keys:

        * One of ``string`` (a byte string) or ``file_obj``
          (a file-like object)
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
        to call ``file_obj.close()``.

    """
    if UNICODE_SCHEME_RE.match(url):
        # See https://bugs.python.org/issue34702
        if url.startswith('file://'):
            url = url.split('?')[0]

        url = iri_to_uri(url)
        response = urlopen(Request(url, headers=HTTP_HEADERS), timeout=timeout)
        response_info = response.info()
        result = dict(redirected_url=response.geturl(),
                      mime_type=response_info.get_content_type(),
                      encoding=response_info.get_param('charset'),
                      filename=response_info.get_filename())
        content_encoding = response_info.get('Content-Encoding')
        if content_encoding == 'gzip':
            if StreamingGzipFile is None:
                result['string'] = gzip.GzipFile(
                    fileobj=io.BytesIO(response.read())).read()
                response.close()
            else:
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
    else:
        raise ValueError('Not an absolute URI: %r' % url)


class URLFetchingError(IOError):
    """Some error happened when fetching an URL."""


@contextlib.contextmanager
def fetch(url_fetcher, url):
    """Call an url_fetcher, fill in optional data, and clean up."""
    try:
        result = url_fetcher(url)
    except Exception as exc:
        raise URLFetchingError('%s: %s' % (type(exc).__name__, str(exc)))
    result.setdefault('redirected_url', url)
    result.setdefault('mime_type', None)
    if 'file_obj' in result:
        try:
            yield result
        finally:
            try:
                result['file_obj'].close()
            except Exception:
                # May already be closed or something.
                # This is just cleanup anyway: log but make it non-fatal.
                LOGGER.warning('Error when closing stream for %s:\n%s',
                               url, traceback.format_exc())
    else:
        yield result
