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


import functools


class MultiFunction(object):
    """
    A callable with different implementations depending on the type of the
    first argument.
    
    This objects takes __name__, __module__ and __doc__ from base_function
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
        raise NotImplementedError
