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
from lxml import html

from . import parse_html
from .. import boxes
from .. import css



suite = Tests()


def serialize(box):
    """
    Transform a box tree into a structure easier to compare for testing.
    """
    if isinstance(box, boxes.TextBox):
        content = box.text
    else:
        content = [serialize(child) for child in box.children]
    type_ = {
        boxes.BlockLevelBox: 'block',
        boxes.InlineLevelBox: 'inline',
        boxes.TextBox: 'text',
    }[box.__class__]
    return box.element.tag, type_, content


def unwrap_html_body(box):
    """
    Test that the box tree starts with an <html> block and a <body> block
    and remove them to simplify further tests. These are always at the root
    of HTML documents.
    """
    tag, type_, content = box
    assert tag == 'html'
    assert type_ == 'block'
    assert len(content) == 1
    
    tag, type_, content = content[0]
    assert tag == 'body'
    assert type_ == 'block'
    return content


def parse(html_content):
    """
    Parse some HTML, apply stylesheets, transform to boxes, serialize.
    """
    document = html.document_fromstring(html_content)
    css.annotate_document(document)
    box_tree = boxes.dom_to_box(document)
    return unwrap_html_body(serialize(box_tree))


@suite.test
def test_box_tree():
    assert parse('<p>') == [('p', 'block', [])]
    assert parse('<p>Hello <em>World</em>!</p>') == [
        ('p', 'block', [
            ('p', 'text', 'Hello '),
            ('em', 'inline', [
                ('em', 'text', 'World')]),
            ('p', 'text', '!')])]

