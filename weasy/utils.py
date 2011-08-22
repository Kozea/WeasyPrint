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
import functools
from urlparse import urljoin, urlparse

from cssutils.helper import path2url


class MultiFunction(object):
    """Callable with different behaviours depending on the first argument type.

    This object takes ``__name__``, ``__module__`` and ``__doc__`` from
    ``base_function`` if it is given, but does not use its body.

    """
    def __init__(self, base_function=None):
        self.implementations = {}
        if base_function:
            functools.update_wrapper(self, base_function)

    def register(self, cls):
        def decorator(function):
            self.implementations[cls] = function
            return function
        return decorator

    def __call__(self, obj, *args, **kwargs):
        for cls in type(obj).mro():
            implementation = self.implementations.get(cls)
            if implementation:
                return implementation(obj, *args, **kwargs)
        raise NotImplementedError('No implementation for %r' % type(obj))


def get_url_attribute(element, key):
    """Get the URL corresponding to the ``key`` attribute of ``element``.

    The retrieved URL is absolute, even if the URL in the element is relative.

    """
    return urljoin(element.base_url, element.get(key).strip())


def ensure_url(string):
    """Get a ``scheme://path`` URL from ``string``.

    If ``string`` looks like an URL, return it unchanged. Otherwise assume a
    filename and convert it to a ``file://`` URL.

    """
    return string if urlparse(string).scheme else path2url(string)


def urllib_fetcher(url):
    """URL fetcher for cssutils.

    This fetcher is based on urllib instead of urllib2, since urllib has
    support for the "data" URL scheme.

    """
    result = urllib.urlopen(url)
    info = result.info()
    if info.gettype() != 'text/css':
        # TODO: add a warning
        return None
    charset = info.getparam('charset')
    return charset, result.read()
