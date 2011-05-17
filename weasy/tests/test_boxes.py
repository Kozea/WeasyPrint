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


from attest import Tests, assert_hook
from cssutils.css import PropertyValue

from . import parse_html
from .. import boxes
from .. import css



suite = Tests()


@suite.test
def test_box_tree():
    document = parse_html('doc1.html')
    css.annotate_document(document)
    # Make sure the HTML4 stylesheet is applied.
    # TODO: this should be in test_css*
    assert document.head.style.display == 'none'
    
    box_tree = boxes.dom_to_box(document)
    
    # TODO
