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


import attest
from attest import Tests, assert_hook
from .. import utils


suite = Tests()


@suite.test
def test_multifunction():

    @utils.MultiFunction
    def foo():
        "Hello, docstrings!"

    assert foo.__name__ == 'foo'
    assert foo.__doc__ == 'Hello, docstrings!'
    assert foo.__module__ == __name__

    @foo.register(int)
    def handle_int(value):
        return 'got an int'

    @foo.register(basestring)
    def handle_string(value):
        return 'got a string'

    assert foo(4) == 'got an int'

    # An implementation is also used when registered on an ancestor class.
    string = 'Oh, hi.'
    assert type(string) is not basestring
    assert basestring in type(string).mro()
    assert foo(string) == 'got a string'

    # Nothing was registered for float.
    with attest.raises(NotImplementedError):
        foo(1.2)
