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
WeasyPrint testing suite.

"""

import os.path
import logging

from cssutils import parseFile

from ..document import PNGDocument


logging.getLogger('WEASYPRINT').addHandler(logging.StreamHandler())


# TODO: find a way to not depend on a specific font
FONTS = u"Liberation Sans, Arial"
TEST_USER_AGENT_STYLESHEETS = (
    parseFile(os.path.join(
        os.path.dirname(__file__), '..', 'css', 'tests_ua.css'
    )),
)


class TestPNGDocument(PNGDocument):
    """Like PNGDocument, but with a different user-agent stylesheet.

    This stylesheet is shorter, which makes tests faster.

    """
    def __init__(self, dom, user_stylesheets=None,
                 user_agent_stylesheets=TEST_USER_AGENT_STYLESHEETS):
        super(TestPNGDocument, self).__init__(
            dom, user_stylesheets, user_agent_stylesheets)


def resource_filename(basename):
    """Return the absolute path of the resource called ``basename``."""
    return os.path.join(os.path.dirname(__file__), 'resources', basename)
