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
from lxml import html

from .. import boxes
from .. import css


suite = Tests()


def serialize(box_list):
    """
    Transform a box list into a structure easier to compare for testing.
    """
    types = {
        boxes.BlockLevelBox: 'block',
        boxes.InlineLevelBox: 'inline',
        boxes.TextBox: 'text',
        boxes.AnonymousBlockLevelBox: 'anon_block',
        boxes.LineBox: 'line',
    }
    return [
        (box.element.tag, types[box.__class__], (
            box.text if isinstance(box, boxes.TextBox)
            else serialize(box.children)))
        for box in box_list
    ]


def unwrap_html_body(box):
    """
    Test that the box tree starts with an <html> block and a <body> block
    and remove them to simplify further tests. These are always at the root
    of HTML documents.
    """
    assert isinstance(box, boxes.BlockLevelBox)
    assert box.element.tag == 'html'
    assert len(box.children) == 1

    box = box.children[0]
    assert isinstance(box, boxes.BlockLevelBox)
    assert box.element.tag == 'body'
    
    return box.children


def to_lists(box_tree):
    """Serialize and unwrap <html> and <body>."""
    return serialize(unwrap_html_body(box_tree))
    

def parse(html_content):
    """
    Parse some HTML, apply stylesheets, transform to boxes, serialize.
    """
    document = html.document_fromstring(html_content)
    css.annotate_document(document)
    return boxes.dom_to_box(document)


def prettify(tree_list):
    """Special formatting for printing serialized box trees."""
    def lines(tree, indent=0):
        tag, type_, content = tree
        if type_ == 'text':
            yield '%s%s %s %r' % ('    ' * indent, tag, type_, content)
        else:
            yield '%s%s %s' % ('    ' * indent, tag, type_)
            for child in content:
                for line in lines(child, indent + 1):
                    yield line

    return '\n'.join(line for tree in tree_list for line in lines(tree))


def assert_tree(box, expected):
    """
    Test box tree equality with the prettified obtained result in the message
    in case of failure.
    
    box: a Box object, starting with <html> and <body> blocks.
    expected: a list of serialized <body> children as returned by to_lists().
    """
    result = to_lists(box)
    assert result == expected, 'Got\n' + prettify(result)


@suite.test
def test_box_tree():
    assert_tree(parse('<p>'), [('p', 'block', [])])
    assert_tree(parse('<p>Hello <em>World</em>!</p>'), [
        ('p', 'block', [
            ('p', 'text', 'Hello '),
            ('em', 'inline', [
                ('em', 'text', 'World')]),
            ('p', 'text', '!')])])


@suite.test
def test_inline_in_block():
    source = '<div>Hello, <em>World</em>!\n<p>Lipsum.</p></div>'
    expected = [
        ('div', 'block', [
            ('div', 'anon_block', [
                ('div', 'line', [
                    ('div', 'text', 'Hello, '),
                    ('em', 'inline', [
                        ('em', 'text', 'World')]),
                    ('div', 'text', '!\n')])]),
            ('p', 'block', [
                ('p', 'line', [
                    ('p', 'text', 'Lipsum.')])])])]
    
    box = parse(source)
    boxes.inline_in_block(box)
    assert_tree(box, expected)

    box = parse(source)
    # This should be idempotent: doing more than once does not change anything.
    boxes.inline_in_block(box)
    boxes.inline_in_block(box)
    assert_tree(box, expected)


@suite.test
def test_block_in_inline():
    box = parse('''
        <style>
            span { display: block; }
        </style>
        <p>Lorem <em>ipsum <strong>dolor <span>sit</span>
            <span>amet,</span></strong><span>consectetur</span></em></p>''')
    boxes.inline_in_block(box)
    assert_tree(box, [
        ('p', 'block', [
            ('p', 'line', [
                ('p', 'text', 'Lorem '),
                ('em', 'inline', [
                    ('em', 'text', 'ipsum '),
                    ('strong', 'inline', [
                        ('strong', 'text', 'dolor '),
                        ('span', 'block', [ # This block is "pulled up"
                            ('span', 'line', [
                                ('span', 'text', 'sit')])]),
                        # No whitespace processing here.
                        ('strong', 'text', '\n            '),
                        ('span', 'block', [ # This block is "pulled up"
                            ('span', 'line', [
                                ('span', 'text', 'amet,')])])]),
                    ('span', 'block', [ # This block is "pulled up"
                        ('span', 'line', [
                            ('span', 'text', 'consectetur')])])])])])])

    boxes.block_in_inline(box)
    assert_tree(box, [
        ('p', 'block', [
            ('p', 'anon_block', [
                ('p', 'line', [
                    ('p', 'text', 'Lorem '),
                    ('em', 'inline', [
                        ('em', 'text', 'ipsum '),
                        ('strong', 'inline', [
                            ('strong', 'text', 'dolor ')])])])]),
            ('span', 'block', [
                ('span', 'line', [
                    ('span', 'text', 'sit')])]),
            # TODO: this should disapear
            ('p', 'anon_block', [
                ('p', 'line', [
                    ('em', 'inline', [
                        ('strong', 'inline', [
                            # No whitespace processing here.
                            ('strong', 'text', '\n            ')])])])]),
            ('span', 'block', [
                ('span', 'line', [
                    ('span', 'text', 'amet,')])]),
                                    
            ('p', 'anon_block', [
                ('p', 'line', [
                    ('em', 'inline', [
                        ('strong', 'inline', [])])])]),
            ('span', 'block', [
                ('span', 'line', [
                    ('span', 'text', 'consectetur')])]),
            ('p', 'anon_block', [
                ('p', 'line', [
                    ('em', 'inline', [])])])])])


@suite.test
def test_styles():
    box = parse('''
        <style>
            span { display: block; }
            * { margin: 42px }
            html { color: blue }
        </style>
        <p>Lorem <em>ipsum <strong>dolor <span>sit</span>
            <span>amet,</span></strong><span>consectetur</span></em></p>''')
    boxes.inline_in_block(box)
    boxes.block_in_inline(box)
    
    for child in box.descendants():
        # All boxes inherit the color
        assert child.style.color == 'blue'
        # Only non-anonymous boxes have margins
        if isinstance(child, boxes.AnonymousBox):
            assert child.style.margin_top == 0
        else:
            assert child.style.margin_top == 42


