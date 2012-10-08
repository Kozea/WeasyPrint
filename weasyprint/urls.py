# coding: utf8
"""
    weasyprint.utils
    ----------------

    Various utility functions and classes.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import re
import sys
import codecs
import os.path
import mimetypes

from . import VERSION_STRING
from .logger import LOGGER
from .compat import (
    urljoin, urlsplit, quote, unquote, unquote_to_bytes, urlopen_contenttype,
    Request, parse_email, pathname2url, unicode, base64_decode)


# Unlinke HTML, CSS and PNG, the SVG MIME type is not always builtin
# in some Python version and therefore not reliable.
if sys.version_info[0] >= 3:
    mimetypes.add_type('image/svg+xml', '.svg')
else:
    # Native strings required.
    mimetypes.add_type(b'image/svg+xml', b'.svg')


# getfilesystemencoding() on Linux is sometimes stupid...
FILESYSTEM_ENCODING = sys.getfilesystemencoding() or 'utf-8'
try:
    if codecs.lookup(FILESYSTEM_ENCODING).name == 'ascii':
        FILESYSTEM_ENCODING = 'utf-8'
except LookupError:
    FILESYSTEM_ENCODING = 'utf-8'


# See http://stackoverflow.com/a/11687993/1162888
# Both are needed in Python 3 as the re module does not like to mix
UNICODE_SCHEME_RE = re.compile('^([a-z][a-z0-1.+-]+):', re.I)
BYTES_SCHEME_RE = re.compile(b'^([a-z][a-z0-1.+-]+):', re.I)


def iri_to_uri(url):
    """Turn an IRI that can contain any Unicode character into an ASII-only
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
    """Return file URL of `path`"""
    path = os.path.abspath(path)
    if os.path.isdir(path):
        # Make sure directory names have a trailing slash.
        # Otherwise relative URIs are resolved from the parent directory.
        path += os.path.sep
    if isinstance(path, unicode):
        path = path.encode(FILESYSTEM_ENCODING)
    path = pathname2url(path)
    if path.startswith('///'):
        # On Windows pathname2url(r'C:\foo') is apparently '///C:/foo'
        # That enough slashes already.
        return 'file:' + path
    else:
        return 'file://' + path


def url_is_absolute(url):
    return bool(
        (UNICODE_SCHEME_RE if isinstance(url, unicode) else BYTES_SCHEME_RE)
        .match(url))


def get_url_attribute(element, attr_name):
    """Get the URI corresponding to the ``attr_name`` attribute.

    Return ``None`` if:

    * the attribute is empty or missing or,
    * the value is a relative URI but the document has no base URI.

    Otherwise, return an absolute URI.

    """
    value = element.get(attr_name, '').strip()
    if value:
        return url_join(element.base_url, value, '<%s %s="%s"> at line %d',
            element.tag, attr_name, value, element.sourceline)


def url_join(base_url, url, context, *args):
    """Like urllib.urljoin, but issue a warning and return None if base_url
    is required but missing.

    """
    if url_is_absolute(url):
        return iri_to_uri(url)
    elif base_url:
        return iri_to_uri(urljoin(base_url, url))
    else:
        LOGGER.warn('Relative URI reference without a base URI: ' + context,
                    *args)
        return None


def get_link_attribute(element, attr_name):
    """Return ('external', absolute_uri) or
    ('internal', unquoted_fragment_id) or None.

    """
    attr_value = element.get(attr_name, '').strip()
    if attr_value.startswith('#'):
        # Do not require a base_url when the value is just a fragment.
        return 'internal', unquote(attr_value[1:])
    else:
        uri = get_url_attribute(element, attr_name)
        if uri and element.base_url:
            parsed = urlsplit(uri)
            # Compare with fragments removed
            if parsed[:-1] == urlsplit(element.base_url)[:-1]:
                return 'internal', unquote(parsed.fragment)
            else:
                return 'external', uri


def ensure_url(string):
    """Get a ``scheme://path`` URL from ``string``.

    If ``string`` looks like an URL, return it unchanged. Otherwise assume a
    filename and convert it to a ``file://`` URL.

    """
    return string if url_is_absolute(string) else path2url(string)


def safe_base64_decode(data):
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
        data += b'='* missing_padding
    return base64_decode(data)


def open_data_url(url):
    """Decode URLs with the 'data' scheme. urllib can handle them
    in Python 2, but that is broken in Python 3.

    Inspired from Python 2.7.2’s urllib.py.

    """
    # syntax of data URLs:
    # dataurl   := "data:" [ mediatype ] [ ";base64" ] "," data
    # mediatype := [ type "/" subtype ] *( ";" parameter )
    # data      := *urlchar
    # parameter := attribute "=" value
    try:
        header, data = url.split(',', 1)
    except ValueError:
        raise IOError('bad data URL')
    header = header[5:]  # len('data:') == 5
    if header:
        semi = header.rfind(';')
        if semi >= 0 and '=' not in header[semi:]:
            content_type = header[:semi]
            encoding = header[semi+1:]
        else:
            content_type = header
            encoding = ''
        message = parse_email('Content-type: ' + content_type)
        mime_type = message.get_content_type()
        charset = message.get_content_charset()
    else:
        mime_type = 'text/plain'
        charset = 'US-ASCII'
        encoding = ''

    data = unquote_to_bytes(data)
    if encoding == 'base64':
        data = safe_base64_decode(data)

    return dict(string=data, mime_type=mime_type, encoding=charset,
                redirected_url=url)


def default_url_fetcher(url):
    """Fetch an external resource such as an image or stylesheet.

    Another callable with the same signature can be given as the
    :obj:`url_fetcher` argument to :class:`HTML` or :class:`CSS`.
    (See :ref:`url-fetchers`.)

    :type url: Unicode string
    :param url: The URL of the resource to fetch
    :raises: any exception to indicate failure. Failures are logged
        as warnings, with the string representation of the exception
        in the message.
    :returns: In case of success, a dict with the following keys:

        * One of ``string`` (a byte string) or ``file_obj`` (a file-like object)
        * Optionally: ``mime_type``, a MIME type extracted eg. from a
          *Content-Type* header. If not provided, the type is guessed from the
          file extension in the URL.
        * Optionally: ``encoding``, a character encoding extracted eg. from a
          *charset* parameter in a *Content-Type* header
        * Optionally: ``redirected_url``, the actual URL of the ressource in case
          there were eg. HTTP redirects.

        If a ``file_obj`` key is given, it is the caller’s responsability to call
        ``file_obj.close()``.

    """
    if url.startswith('data:'):
        return open_data_url(url)
    elif UNICODE_SCHEME_RE.match(url):
        url = iri_to_uri(url)
        result, mime_type, charset = urlopen_contenttype(Request(
            url, headers={'User-Agent': VERSION_STRING}))
        return dict(file_obj=result, redirected_url=result.geturl(),
                    mime_type=mime_type, encoding=charset)
    else:
        raise ValueError('Not an absolute URI: %r' % url)


def wrap_url_fetcher(url_fetcher):
    """Decorate an url_fetcher to fill in optional data.

    url_fetcher itself can be None, in which case the default fetcher is used.
    In a result dict, redirected_url defaults to the original URL. If not
    provided, mime_type is guessed from the path extension in the URL.

    """
    if url_fetcher is None:
        return default_url_fetcher

    def wrapped_fetcher(url):
        result = url_fetcher(url)
        result.setdefault('redirected_url', url)
        if 'mime_type' not in result:
            path = urlsplit(result['redirected_url']).path
            mime_type, _ = mimetypes.guess_type(path)
            result['mime_type'] = mime_type or 'application/octet-stream'
        return result
    return wrapped_fetcher
