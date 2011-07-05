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
from ..formatting_structure import boxes, build
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
    box = parse('<p>')
    assert isinstance(box, boxes.PageBox)
    layout.compute_dimensions(box)
    assert int(box.outer_width) == 793  # A4: 210 mm in pixels
    assert int(box.outer_height) == 1122  # A4: 297 mm in pixels

    box = parse('<style>@page { margin: 10px 10% 20% 1in }</style>')
    assert isinstance(box, boxes.PageBox)
    layout.compute_dimensions(box, width=200, height=300)
    assert box.outer_width == 200
    assert box.outer_height == 300
    assert box.position_x == 96 # 1 inch
    assert box.position_y == 10 # 10px
    assert box.width == 84 # 200px - 10% - 1 inch
    assert box.height == 230 # 300px - 10px - 20%
