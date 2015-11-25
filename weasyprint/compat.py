# coding: utf-8
"""
    weasyprint.compat
    -----------------

    Workarounds for compatibility with Python 2 and 3 in the same code base.

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import sys
import email


__all__ = ['Request', 'base64_decode', 'base64_encode', 'basestring',
           'ints_from_bytes', 'iteritems', 'izip', 'parse_email', 'parse_qs',
           'pathname2url', 'quote', 'unicode', 'unquote', 'unquote_to_bytes',
           'urlencode', 'urljoin', 'urlopen', 'urllib_get_content_type',
           'urllib_get_charset', 'urllib_get_filename',
           'urlparse_uses_relative', 'urlsplit', 'xrange']


if sys.version_info[0] >= 3:
    # Python 3
    from urllib.parse import (
        urljoin, urlsplit, quote, unquote, unquote_to_bytes, parse_qs,
        urlencode, uses_relative as urlparse_uses_relative)
    from urllib.request import urlopen, Request, pathname2url
    from array import array
    from base64 import (decodebytes as base64_decode,
                        encodebytes as base64_encode)

    unicode = str
    basestring = str
    xrange = range
    iteritems = dict.items
    izip = zip

    def urllib_get_content_type(urlobj):
        return urlobj.info().get_content_type()

    def urllib_get_charset(urlobj):
        return urlobj.info().get_param('charset')

    def urllib_get_filename(urlobj):
        return urlobj.info().get_filename()

    def parse_email(data):
        if isinstance(data, bytes):
            data = data.decode('utf8')
        return email.message_from_string(data)

    def ints_from_bytes(byte_string):
        """Return a list of ints from a byte string"""
        return list(byte_string)

else:
    # Python 2
    from urlparse import (urljoin, urlsplit, parse_qs,
                          uses_relative as urlparse_uses_relative)
    from urllib2 import urlopen, Request
    from urllib import pathname2url, quote, unquote, urlencode
    from array import array as _array
    from itertools import izip, imap
    from base64 import (decodestring as base64_decode,
                        encodestring as base64_encode)

    unicode = unicode
    basestring = basestring
    xrange = xrange
    iteritems = dict.iteritems

    def array(typecode, initializer):
        return _array(typecode.encode('ascii'), initializer)

    def urllib_get_content_type(urlobj):
        return urlobj.info().gettype()

    def urllib_get_charset(urlobj):
        return urlobj.info().getparam('charset')

    def urllib_get_filename(urlobj):
        return None

    def unquote_to_bytes(data):
        if isinstance(data, unicode):
            data = data.encode('ascii')
        return unquote(data)

    def parse_email(data):
        if isinstance(data, unicode):
            data = data.encode('utf8')
        return email.message_from_string(data)

    def ints_from_bytes(byte_string):
        """Return a list of ints from a byte string"""
        return imap(ord, byte_string)


if sys.version_info >= (3, 2):
    from gzip import GzipFile

    class StreamingGzipFile(GzipFile):
        def __init__(self, fileobj):
            GzipFile.__init__(self, fileobj=fileobj)
            self.fileobj_to_close = fileobj

        def close(self):
            GzipFile.close(self)
            self.fileobj_to_close.close()

        # Inform html5lib to not rely on these:
        seek = tell = None
else:
    # On older Python versions, GzipFile requires .seek() and .tell()
    # which file-like objects for HTTP response do not have.
    # http://bugs.python.org/issue11608
    StreamingGzipFile = None
