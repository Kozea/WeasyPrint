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
Test the CSS boxes.

"""

import contextlib

from attest import Tests, assert_hook  # pylint: disable=W0611

from . import resource_filename
from ..css import validation
from . import TestPNGDocument
from ..formatting_structure import boxes, build


SUITE = Tests()


def serialize(box_list):
    """Transform a box list into a structure easier to compare for testing."""
    types = {
        boxes.TextBox: 'text',
        boxes.LineBox: 'line',
        boxes.BlockBox: 'block',
        boxes.InlineBox: 'inline',
        boxes.InlineBlockBox: 'inline_block',
        boxes.AnonymousBlockBox: 'anon_block',
        boxes.InlineLevelReplacedBox: 'inline_replaced',
    }
    return [
        (box.element.tag, types[box.__class__], (
            # All concrete boxes are either text, replaced or parent.
            box.utf8_text.decode('utf8') if isinstance(box, boxes.TextBox)
            else '<replaced>' if isinstance(box, boxes.ReplacedBox)
            else serialize(box.children)))
        for box in box_list
    ]


def unwrap_html_body(box):
    """Test that the box tree starts with a ``<html>`` and a ``<body>`` blocks.

    Remove them to simplify further tests. These are always at the root
    of HTML documents.

    """
    assert box.element.tag == 'html'
    assert isinstance(box, boxes.BlockBox)
    assert len(box.children) == 1

    box = box.children[0]
    assert isinstance(box, boxes.BlockBox)
    assert box.element.tag == 'body'

    return box.children


def to_lists(box_tree):
    """Serialize and unwrap ``<html>`` and ``<body>``."""
    return serialize(unwrap_html_body(box_tree))


@contextlib.contextmanager
def monkeypatch_validation(replacement):
    """Create a context manager patching the validation mechanism.

    This is useful to change the behaviour of the validation for one property
    not yet supported, without affecting the validation for the other
    properties.

    """
    real_non_shorthand = validation.validate_non_shorthand

    def patched_non_shorthand(*args, **kwargs):
        """Wraps the validator into ``replacement``."""
        return replacement(real_non_shorthand, *args, **kwargs)

    validation.validate_non_shorthand = patched_non_shorthand
    try:
        yield
    finally:
        validation.validate_non_shorthand = real_non_shorthand


def validate_inline_block(real_non_shorthand, name, values, required=False):
    """Fake validator for inline blocks."""
    if name == 'display' and values[0].value == 'inline-block':
        return [(name, 'inline-block')]
    return real_non_shorthand(name, values, required)


def parse(html_content):
    """Parse some HTML, apply stylesheets and transform to boxes."""
    # TODO: remove this patching when inline-block is validated.
    with monkeypatch_validation(validate_inline_block):
        document = TestPNGDocument.from_string(html_content)
        # Dummy filename, but in the right directory.
        document.base_url = resource_filename('<test>')
        return build.dom_to_box(document, document.dom)


def prettify(tree_list):
    """Special formatting for printing serialized box trees."""
    def lines(tree, indent=0):
        """Recursively yield the lines of ``tree`` with ``indentation``."""
        tag, type_, content = tree
        if type_ in ('text', 'inline_replaced'):
            yield '%s%s %s %r' % (4 * ' ' * indent, tag, type_, content)
        else:
            yield '%s%s %s' % (4 * ' ' * indent, tag, type_)
            for child in content:
                for line in lines(child, indent + 1):
                    yield line

    return '\n'.join(line for tree in tree_list for line in lines(tree))


def assert_tree(box, expected):
    """Check the box tree equality.

    The obtained result is prettified in the message in case of failure.

    box: a Box object, starting with <html> and <body> blocks.
    expected: a list of serialized <body> children as returned by to_lists().

    """
    result = to_lists(box)
    assert result == expected, 'Got\n' + prettify(result)


def sanity_checks(box):
    """Check that the rules regarding boxes are met.

    This is not required and only helps debugging.

    - A block container can contain either only block-level boxes or
      only line boxes;
    - Line boxes and inline boxes can only contain inline-level boxes.

    """
    if not isinstance(box, boxes.ParentBox):
        return

    for child in box.children:
        sanity_checks(child)

    if isinstance(box, boxes.BlockContainerBox):
        types = [boxes.BlockLevelBox, boxes.LineBox]
    elif isinstance(box, (boxes.LineBox, boxes.InlineBox)):
        types = [boxes.InlineLevelBox]
    # no other ParentBox concrete subclass

    assert any(
        all(isinstance(child, type_) for child in box.children)
        for type_ in types)


@SUITE.test
def test_box_tree():
    """Test the creation of trees from HTML strings."""
    assert_tree(parse('<p>'), [('p', 'block', [])])
    assert_tree(parse('''
        <style>
            span { display: inline-block }
        </style>
        <p>Hello <em>World <img src="pattern.png"><span>Lipsum</span></em>!</p>
    '''), [
        ('p', 'block', [
            ('p', 'text', 'Hello '),
            ('em', 'inline', [
                ('em', 'text', 'World '),
                ('img', 'inline_replaced', '<replaced>'),
                ('span', 'inline_block', [
                    ('span', 'text', 'Lipsum')])]),
            ('p', 'text', '!')])])


@SUITE.test
def test_html_entities():
    """Test the management of HTML entities."""
    for quote in ['"', '&quot;', '&#x22;', '&#34;']:
        assert_tree(parse('<p>{}abc{}'.format(quote, quote)), [
            ('p', 'block', [
                ('p', 'text', '"abc"')])])


@SUITE.test
def test_inline_in_block():
    """Test the management of inline boxes in block boxes."""
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
    box = build.inline_in_block(box)
    assert_tree(box, expected)

    box = parse(source)
    # This should be idempotent: doing more than once does not change anything.
    box = build.inline_in_block(box)
    box = build.inline_in_block(box)
    assert_tree(box, expected)


@SUITE.test
def test_block_in_inline():
    """Test the management of block boxes in inline boxes."""
    box = parse('''
<style>
    p { display: inline-block; }
    span { display: block; }
</style>
<p>Lorem <em>ipsum <strong>dolor <span>sit</span>
    <span>amet,</span></strong><span><em>consectetur<div/></em></span></em></p>
    ''')
    box = build.inline_in_block(box)
    assert_tree(box, [
        ('body', 'line', [
            ('p', 'inline_block', [
                ('p', 'line', [
                    ('p', 'text', 'Lorem '),
                    ('em', 'inline', [
                        ('em', 'text', 'ipsum '),
                        ('strong', 'inline', [
                            ('strong', 'text', 'dolor '),
                            ('span', 'block', [  # This block is "pulled up"
                                ('span', 'line', [
                                    ('span', 'text', 'sit')])]),
                            # No whitespace processing here.
                            ('strong', 'text', '\n    '),
                            ('span', 'block', [  # This block is "pulled up"
                                ('span', 'line', [
                                    ('span', 'text', 'amet,')])])]),
                        ('span', 'block', [  # This block is "pulled up"
                            ('span', 'line', [
                                ('em', 'inline', [
                                    ('em', 'text', 'consectetur'),
                                    ('div', 'block', []),
                                    ])])])])])])])])

    box = build.block_in_inline(box)
    assert_tree(box, [
        ('body', 'line', [
            ('p', 'inline_block', [
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
                ('p', 'anon_block', [
                    ('p', 'line', [
                        ('em', 'inline', [
                            ('strong', 'inline', [
                                # Whitespace processing not done yet.
                                ('strong', 'text', '\n    ')])])])]),
                ('span', 'block', [
                    ('span', 'line', [
                        ('span', 'text', 'amet,')])]),

                ('p', 'anon_block', [
                    ('p', 'line', [
                        ('em', 'inline', [
                            ('strong', 'inline', [])])])]),
                ('span', 'block', [
                    ('span', 'anon_block', [
                        ('span', 'line', [
                            ('em', 'inline', [
                                ('em', 'text', 'consectetur')])])]),
                    ('div', 'block', []),
                    ('span', 'anon_block', [
                        ('span', 'line', [
                            ('em', 'inline', [])])])]),
                ('p', 'anon_block', [
                    ('p', 'line', [
                        ('em', 'inline', [])])])])])])


@SUITE.test
def test_styles():
    """Test the application of CSS to HTML."""
    box = parse('''
        <style>
            span { display: block; }
            * { margin: 42px }
            html { color: blue }
        </style>
        <p>Lorem <em>ipsum <strong>dolor <span>sit</span>
            <span>amet,</span></strong><span>consectetur</span></em></p>''')
    box = build.inline_in_block(box)
    box = build.block_in_inline(box)

    descendants = list(box.descendants())
    assert len(descendants) == 31
    assert descendants[0] == box

    for child in descendants:
        # All boxes inherit the color
        assert child.style.color.value == 'blue'
        # Only non-anonymous boxes have margins
        if isinstance(child, boxes.AnonymousBox):
            assert child.style.margin_top == 0
        else:
            assert child.style.margin_top == 42


@SUITE.test
def test_whitespace():
    """Test the management of white spaces."""
    # TODO: test more cases
    # http://www.w3.org/TR/CSS21/text.html#white-space-model
    document = TestPNGDocument.from_string('''
        <p>Lorem \t\r\n  ipsum\t<strong>  dolor </strong>.</p>
        <pre>\t  foo\n</pre>
        <pre style="white-space: pre-wrap">\t  foo\n</pre>
        <pre style="white-space: pre-line">\t  foo\n</pre>
        ''')
    box = build.build_formatting_structure(document)
    sanity_checks(box)

    assert_tree(box, [
        ('p', 'block', [
            ('p', 'line', [
                ('p', 'text', 'Lorem ipsum '),
                ('strong', 'inline', [
                    ('strong', 'text', 'dolor ')]),
                ('p', 'text', '.')])]),
        ('body', 'anon_block', [
            ('body', 'line', [
                ('body', 'text', ' ')])]),
        ('pre', 'block', [
            ('pre', 'line', [
                # pre
                ('pre', 'text', u'\t\xA0\xA0foo\n')])]),
        ('body', 'anon_block', [
            ('body', 'line', [
                ('body', 'text', ' ')])]),
        ('pre', 'block', [
            ('pre', 'line', [
                # pre-wrap
                ('pre', 'text', u'\t\xA0\xA0\u200Bfoo\n')])]),
        ('body', 'anon_block', [
            ('body', 'line', [
                ('body', 'text', ' ')])]),
        ('pre', 'block', [
            ('pre', 'line', [
                # pre-line
                ('pre', 'text', u'foo\n')])])])


@SUITE.test
def test_page_style():
    """Test the management of page styles."""
    document = TestPNGDocument.from_string('''
        <style>
            @page { margin: 3px }
            @page :first { margin-top: 20px }
            @page :right { margin-right: 10px; margin-top: 10px }
            @page :left { margin-left: 10px; margin-top: 10px }
        </style>
    ''')

    def assert_page_margins(page_number, top, right, bottom, left):
        """Check the page margin values."""
        page = boxes.PageBox(document, page_number)
        assert page.style.margin_top == top
        assert page.style.margin_right == right
        assert page.style.margin_bottom == bottom
        assert page.style.margin_left == left

    # Odd numbers are :right pages, even are :left. 1 has :first as well
    assert_page_margins(1, top=20, right=10, bottom=3, left=3)
    assert_page_margins(2, top=10, right=3, bottom=3, left=10)
    assert_page_margins(3, top=10, right=10, bottom=3, left=3)
    assert_page_margins(4, top=10, right=3, bottom=3, left=10)
    assert_page_margins(45, top=10, right=10, bottom=3, left=3)
    assert_page_margins(122, top=10, right=3, bottom=3, left=10)


@SUITE.test
def test_text_transform():
    document = TestPNGDocument.from_string('''
        <style>
            p { text-transform: capitalize }
            p+p { text-transform: uppercase }
            p+p+p { text-transform: lowercase }
            p+p+p+p { text-transform: none }
        </style>
<p>heLLo wOrlD!</p><p>heLLo wOrlD!</p><p>heLLo wOrlD!</p><p>heLLo wOrlD!</p>
        ''')
    box = build.build_formatting_structure(document)
    sanity_checks(box)

    assert_tree(box, [
        ('p', 'block', [
            ('p', 'line', [
                ('p', 'text', 'Hello World!')])]),
        ('p', 'block', [
            ('p', 'line', [
                ('p', 'text', 'HELLO WORLD!')])]),
        ('p', 'block', [
            ('p', 'line', [
                ('p', 'text', 'hello world!')])]),
        ('p', 'block', [
            ('p', 'line', [
                ('p', 'text', 'heLLo wOrlD!')])]),
    ])
