# coding: utf8

#  WeasyPrint converts web documents (HTML, CSS, ...) to PDF.
#  Copyright (C) 2011  Simon Sapin
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
Various utils.

"""

import urllib
from urlparse import urljoin, urlparse

from cssutils.helper import path2url

from . import VERSION
from .logging import LOGGER


def get_url_attribute(element, key):
    """Get the URL corresponding to the ``key`` attribute of ``element``.

    The retrieved URL is absolute, even if the URL in the element is relative.

    """
    attr_value = element.get(key)
    if attr_value:
        return urljoin(element.base_url, attr_value.strip())


def ensure_url(string):
    """Get a ``scheme://path`` URL from ``string``.

    If ``string`` looks like an URL, return it unchanged. Otherwise assume a
    filename and convert it to a ``file://`` URL.

    """
    if urlparse(string).scheme:
        return string
    else:
        return path2url(string.encode('utf8'))


class URLopener(urllib.FancyURLopener):
    """Sets the user agent string."""
    # User-Agent
    version = 'WeasyPrint/%s http://weasyprint.org/' % VERSION


def urlopen(url):
    """Fetch an URL and return ``(file_like, mime_type, charset)``.

    It is the caller’s responsability to call ``file_like.close()``.
    """
    file_like = URLopener().open(url)
    info = file_like.info()
    if hasattr(info, 'get_content_type'):
        # Python 3
        mime_type = info.get_content_type()
    else:
        # Python 2
        mime_type = info.gettype()
    if hasattr(info, 'get_param'):
        # Python 3
        charset = info.get_param('charset')
    else:
        # Python 2
        charset = info.getparam('charset')
    return file_like.fp, mime_type, charset


def urllib_fetcher(url):
    """URL fetcher for cssutils.

    This fetcher is based on urllib instead of urllib2, since urllib has
    support for the "data" URL scheme.

    """
    file_like, mime_type, charset = urlopen(url)
    if mime_type != 'text/css':
        LOGGER.warn('Expected `text/css` for stylsheet at %s, got `%s`',
                    url, mime_type)
        return None
    content = file_like.read()
    file_like.close()
    return charset, content
