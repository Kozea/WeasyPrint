# coding: utf8

#  WeasyPrint converts web documents (HTML, CSS, ...) to PDF.
#  Copyright (C) 2011-2012 Simon Sapin and contributors.
#  See AUTHORS for more details.
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
Python 2/3 compatibility.

"""

from __future__ import division, unicode_literals

import io
import sys
import email
import contextlib


if sys.version_info[0] >= 3:
    # Python 3
    from urllib.parse import urljoin, urlparse, unquote_to_bytes
    from urllib.request import urlopen, Request
    from array import array

    basestring = str
    xrange = range
    iteritems = dict.items


    def urlopen_contenttype(url):
        """Return (file_obj, mime_type, encoding)"""
        result = urlopen(url)
        info = result.info()
        mime_type = info.get_content_type()
        charset = info.get_param('charset')
        # Using here result.fp gives 'ValueError: read of closed file'
        return result, mime_type, charset


    def parse_email(data):
        if isinstance(data, bytes):
            data = data.decode('utf8')
        return email.message_from_string(data)

else:
    # Python 2
    from urlparse import urljoin, urlparse, unquote
    from urllib2 import urlopen, Request
    from array import array as _array

    basestring = basestring
    xrange = xrange
    iteritems = dict.iteritems


    def array(typecode, initializer):
        return _array(typecode.encode('ascii'), initializer)


    def urlopen_contenttype(url):
        """Return (file_obj, mime_type, encoding)"""
        result = urlopen(url)
        info = result.info()
        mime_type = info.gettype()
        charset = info.getparam('charset')
        return result.fp, mime_type, charset


    def unquote_to_bytes(data):
        if isinstance(data, unicode):
            data = data.encode('ascii')
        return unquote(data)


    def parse_email(data):
        if isinstance(data, unicode):
            data = data.encode('utf8')
        return email.message_from_string(data)
