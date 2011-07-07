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

import os.path
from lxml import html
from cssutils.helper import path2url
from attest import Tests


def resource_filename(basename):
    return os.path.join(os.path.dirname(__file__), 'resources', basename)


def parse_html(filename):
    """Parse an HTML file from the test resources and resolve relative URL."""
    document = html.parse(path2url(resource_filename(filename))).getroot()
    return document


all = Tests('.'.join((__name__, mod, 'suite'))
            for mod in ('test_css',
                        'test_css_properties',
                        'test_boxes',
                        'test_utils',
                        'test_layout',
                        'test_text'))
