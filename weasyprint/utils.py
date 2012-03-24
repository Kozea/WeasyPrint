# coding: utf8
"""
    weasyprint.utils
    ----------------

    Various utility functions and classes.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import os.path
import io
import base64

from . import VERSION
from .logger import LOGGER
from .compat import (
    urljoin, urlparse, unquote_to_bytes, urlopen_contenttype, Request,
    parse_email, pathname2url)


# TODO: Most of this module is URL-related. Rename it to weasyprint.urls?


HTTP_USER_AGENT = 'WeasyPrint/%s http://weasyprint.org/' % VERSION


def path2url(path):
    """Return file URL of `path`"""
    return 'file:' + pathname2url(os.path.abspath(path))


def get_url_attribute(element, key):
    """Get the URL corresponding to the ``key`` attribute of ``element``.

    The retrieved URL is absolute, even if the URL in the element is relative.

    """
    attr_value = element.get(key)
    if attr_value:
        attr_value = attr_value.strip()
        if attr_value:
            # TODO: support the <base> HTML element, but do not use
            # lxml.html.HtmlElement.make_links_absolute() that changes
            # the tree for content: attr(href)
            return urljoin(element.base_url, attr_value)


def ensure_url(string):
    """Get a ``scheme://path`` URL from ``string``.

    If ``string`` looks like an URL, return it unchanged. Otherwise assume a
    filename and convert it to a ``file://`` URL.

    """
    if urlparse(string).scheme:
        return string
    else:
        return path2url(string.encode('utf8'))


def decode_base64(data):
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
    return base64.decodestring(data)


def parse_data_url(url):
    """Decode URLs with the 'data' stream. urllib can handle them
    in Python 2, but that is broken in Python 3.

    Inspired from the Python 2.7.2’s urllib.py.

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
        data = decode_base64(data)

    return io.BytesIO(data), mime_type, charset


def urlopen(url):
    """Fetch an URL and return ``(file_like, mime_type, charset)``.

    It is the caller’s responsability to call ``file_like.close()``.
    """
    if url.startswith('data:'):
        return parse_data_url(url)
    else:
        return urlopen_contenttype(Request(url,
            headers={'User-Agent': HTTP_USER_AGENT}))


class cached_property(object):
    """A decorator that converts a function into a lazy property. The
    function wrapped is called the first time to retrieve the result
    and then that calculated result is used the next time you access
    the value.

    Stolen from Werkzeug:
    https://github.com/mitsuhiko/werkzeug/blob/7b8d887d33/werkzeug/utils.py#L28

    """

    def __init__(self, func):
        self.__name__ = func.__name__
        self.__module__ = func.__module__
        self.__doc__ = func.__doc__
        self.func = func

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        missing = object()
        value = obj.__dict__.get(self.__name__, missing)
        if value is missing:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value
