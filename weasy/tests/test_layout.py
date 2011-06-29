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
import lxml.html

from .. import css
from ..formatting_structure import build
from .. import layout


suite = Tests()


def parse(html_content):
    """
    Parse some HTML, apply stylesheets and transform to boxes.
    """
    document = lxml.html.document_fromstring(html_content)
    css.annotate_document(document)
    return build.build_formatting_structure(document)


@suite.test
def test_compute_dimensions():
    box = parse('<p>Hello, <em>layout</em>!</p>')

    assert layout.compute_dimensions(box) is box
