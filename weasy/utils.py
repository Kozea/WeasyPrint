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

try:
    from urlparse import urljoin, urlparse
except ImportError:
    # Python 3
    from urllib.parse import urljoin, urlparse

import functools

from cssutils.helper import path2url


class MultiFunction(object):
    """
    A callable with different implementations depending on the type of the
    first argument.

    This object takes __name__, __module__ and __doc__ from base_function
    if it is given, but does not use it’s body.
    """

    def __init__(self, base_function=None):
        self.implementations = {}
        if base_function:
            functools.update_wrapper(self, base_function)

    def register(self, class_):
        def decorator(function):
            self.implementations[class_] = function
            return function
        return decorator

    def __call__(self, obj, *args, **kwargs):
        for class_ in type(obj).mro():
            implementation = self.implementations.get(class_)
            if implementation:
                return implementation(obj, *args, **kwargs)
        raise NotImplementedError('No implementation for %r' % type(obj))


def get_url_attribute(element, key):
    """
    Get a (possibly relative) URL from an element attribute and return
    the absolute URL.
    """
    return urljoin(element.base_url, element.get(key).strip())


def ensure_url(filename_or_url):
    """
    If the argument looks like an URL, return it unchanged. Otherwise assume
    a filename and convert it to a file:// URL.
    """
    if urlparse(filename_or_url).scheme:
        return filename_or_url
    else:
        return path2url(filename_or_url)
