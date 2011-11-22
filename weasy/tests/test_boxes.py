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


PROPER_CHILDREN = dict((key, tuple(map(tuple, value))) for key, value in {
    # Children can be of *any* type in *one* of the lists.
    boxes.BlockContainerBox: [[boxes.BlockLevelBox], [boxes.LineBox]],
    boxes.LineBox: [[boxes.InlineLevelBox]],
    boxes.InlineBox: [[boxes.InlineLevelBox]],
    boxes.TableBox: [[boxes.TableCaptionBox,
                      boxes.TableColumnGroupBox, boxes.TableColumnBox,
                      boxes.TableRowGroupBox, boxes.TableRowBox]],
    boxes.InlineTableBox: [[boxes.TableCaptionBox,
                            boxes.TableColumnGroupBox, boxes.TableColumnBox,
                            boxes.TableRowGroupBox, boxes.TableRowBox]],
    boxes.TableColumnGroupBox: [[boxes.TableColumnBox]],
    boxes.TableRowGroupBox: [[boxes.TableRowBox]],
    boxes.TableRowBox: [[boxes.TableCellBox]],
}.iteritems())


def serialize(box_list):
    """Transform a box list into a structure easier to compare for testing."""
    return [
        (
            box.element.tag,
            ('Anon' if box.anonymous and type(box) not in (boxes.TextBox,
                boxes.LineBox) else '') + type(box).__name__[:-3],
            (
            # All concrete boxes are either text, replaced, column or parent.
            box.text if isinstance(box, boxes.TextBox)
            else '<replaced>' if isinstance(box, boxes.ReplacedBox)
            else '<column>' if isinstance(box, boxes.TableColumnBox)
            else serialize(getattr(box, 'column_groups', ()) + box.children)))
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
        box, = build.dom_to_box(document, document.dom)
        return box


def parse_all(html_content):
    """Like parse() but also run all corrections on boxes."""
    document = TestPNGDocument.from_string(html_content)
    document.base_url = resource_filename('<test>')
    box = build.build_formatting_structure(document)
    sanity_checks(box)
    return box


def assert_tree(box, expected):
    """Check the box tree equality.

    The obtained result is prettified in the message in case of failure.

    box: a Box object, starting with <html> and <body> blocks.
    expected: a list of serialized <body> children as returned by to_lists().

    """
    assert to_lists(box) == expected


def sanity_checks(box):
    """Check that the rules regarding boxes are met.

    This is not required and only helps debugging.

    - A block container can contain either only block-level boxes or
      only line boxes;
    - Line boxes and inline boxes can only contain inline-level boxes.

    """
    if not isinstance(box, boxes.ParentBox):
        return

    for class_ in type(box).mro():
        if class_ in PROPER_CHILDREN:
            acceptable_types_lists = PROPER_CHILDREN[class_]
            break
    else:
        raise TypeError

    assert any(
        all(isinstance(child, acceptable_types) for child in box.children)
        for acceptable_types in acceptable_types_lists
    ), (box, box.children)

    for child in box.children:
        sanity_checks(child)


@SUITE.test
def test_box_tree():
    """Test the creation of trees from HTML strings."""
    assert_tree(parse('<p>'), [('p', 'Block', [])])
    assert_tree(parse('''
        <style>
            span { display: inline-block }
        </style>
        <p>Hello <em>World <img src="pattern.png"><span>Lipsum</span></em>!</p>
    '''), [
        ('p', 'Block', [
            ('p', 'Text', 'Hello '),
            ('em', 'Inline', [
                ('em', 'Text', 'World '),
                ('img', 'InlineLevelReplaced', '<replaced>'),
                ('span', 'InlineBlock', [
                    ('span', 'Text', 'Lipsum')])]),
            ('p', 'Text', '!')])])


@SUITE.test
def test_html_entities():
    """Test the management of HTML entities."""
    for quote in ['"', '&quot;', '&#x22;', '&#34;']:
        assert_tree(parse('<p>{}abc{}'.format(quote, quote)), [
            ('p', 'Block', [
                ('p', 'Text', '"abc"')])])


@SUITE.test
def test_inline_in_block():
    """Test the management of inline boxes in block boxes."""
    source = '<div>Hello, <em>World</em>!\n<p>Lipsum.</p></div>'
    expected = [
        ('div', 'Block', [
            ('div', 'AnonBlock', [
                ('div', 'Line', [
                    ('div', 'Text', 'Hello, '),
                    ('em', 'Inline', [
                        ('em', 'Text', 'World')]),
                    ('div', 'Text', '!\n')])]),
            ('p', 'Block', [
                ('p', 'Line', [
                    ('p', 'Text', 'Lipsum.')])])])]

    box = parse(source)
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
        ('body', 'Line', [
            ('p', 'InlineBlock', [
                ('p', 'Line', [
                    ('p', 'Text', 'Lorem '),
                    ('em', 'Inline', [
                        ('em', 'Text', 'ipsum '),
                        ('strong', 'Inline', [
                            ('strong', 'Text', 'dolor '),
                            ('span', 'Block', [  # This block is "pulled up"
                                ('span', 'Line', [
                                    ('span', 'Text', 'sit')])]),
                            # No whitespace processing here.
                            ('strong', 'Text', '\n    '),
                            ('span', 'Block', [  # This block is "pulled up"
                                ('span', 'Line', [
                                    ('span', 'Text', 'amet,')])])]),
                        ('span', 'Block', [  # This block is "pulled up"
                            ('span', 'Line', [
                                ('em', 'Inline', [
                                    ('em', 'Text', 'consectetur'),
                                    ('div', 'Block', []),
                                    ])])])])])])])])

    box = build.block_in_inline(box)
    assert_tree(box, [
        ('body', 'Line', [
            ('p', 'InlineBlock', [
                ('p', 'AnonBlock', [
                    ('p', 'Line', [
                        ('p', 'Text', 'Lorem '),
                        ('em', 'Inline', [
                            ('em', 'Text', 'ipsum '),
                            ('strong', 'Inline', [
                                ('strong', 'Text', 'dolor ')])])])]),
                ('span', 'Block', [
                    ('span', 'Line', [
                        ('span', 'Text', 'sit')])]),
                ('p', 'AnonBlock', [
                    ('p', 'Line', [
                        ('em', 'Inline', [
                            ('strong', 'Inline', [
                                # Whitespace processing not done yet.
                                ('strong', 'Text', '\n    ')])])])]),
                ('span', 'Block', [
                    ('span', 'Line', [
                        ('span', 'Text', 'amet,')])]),

                ('p', 'AnonBlock', [
                    ('p', 'Line', [
                        ('em', 'Inline', [
                            ('strong', 'Inline', [])])])]),
                ('span', 'Block', [
                    ('span', 'AnonBlock', [
                        ('span', 'Line', [
                            ('em', 'Inline', [
                                ('em', 'Text', 'consectetur')])])]),
                    ('div', 'Block', []),
                    ('span', 'AnonBlock', [
                        ('span', 'Line', [
                            ('em', 'Inline', [])])])]),
                ('p', 'AnonBlock', [
                    ('p', 'Line', [
                        ('em', 'Inline', [])])])])])])


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
        if child.anonymous:
            assert child.style.margin_top == 0
        else:
            assert child.style.margin_top == 42


@SUITE.test
def test_whitespace():
    """Test the management of white spaces."""
    # TODO: test more cases
    # http://www.w3.org/TR/CSS21/text.html#white-space-model
    assert_tree(parse_all('''
        <p>Lorem \t\r\n  ipsum\t<strong>  dolor
            <img src=pattern.png> sit</strong>.</p>
        <pre>\t  foo\n</pre>
        <pre style="white-space: pre-wrap">\t  foo\n</pre>
        <pre style="white-space: pre-line">\t  foo\n</pre>
    '''), [
        ('p', 'Block', [
            ('p', 'Line', [
                ('p', 'Text', 'Lorem ipsum '),
                ('strong', 'Inline', [
                    ('strong', 'Text', 'dolor '),
                    ('img', 'InlineLevelReplaced', '<replaced>'),
                    ('strong', 'Text', ' sit')]),
                ('p', 'Text', '.')])]),
        ('body', 'AnonBlock', [
            ('body', 'Line', [
                ('body', 'Text', ' ')])]),
        ('pre', 'Block', [
            ('pre', 'Line', [
                # pre
                ('pre', 'Text', u'\t\xA0\xA0foo\n')])]),
        ('body', 'AnonBlock', [
            ('body', 'Line', [
                ('body', 'Text', ' ')])]),
        ('pre', 'Block', [
            ('pre', 'Line', [
                # pre-wrap
                ('pre', 'Text', u'\t\xA0\xA0\u200Bfoo\n')])]),
        ('body', 'AnonBlock', [
            ('body', 'Line', [
                ('body', 'Text', ' ')])]),
        ('pre', 'Block', [
            ('pre', 'Line', [
                # pre-line
                ('pre', 'Text', u' foo\n')])])])


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
    """Test the text-transform property."""
    assert_tree(parse_all('''
        <style>
            p { text-transform: capitalize }
            p+p { text-transform: uppercase }
            p+p+p { text-transform: lowercase }
            p+p+p+p { text-transform: none }
        </style>
<p>heLLo wOrlD!</p><p>heLLo wOrlD!</p><p>heLLo wOrlD!</p><p>heLLo wOrlD!</p>
    '''), [
        ('p', 'Block', [
            ('p', 'Line', [
                ('p', 'Text', 'Hello World!')])]),
        ('p', 'Block', [
            ('p', 'Line', [
                ('p', 'Text', 'HELLO WORLD!')])]),
        ('p', 'Block', [
            ('p', 'Line', [
                ('p', 'Text', 'hello world!')])]),
        ('p', 'Block', [
            ('p', 'Line', [
                ('p', 'Text', 'heLLo wOrlD!')])]),
    ])


@SUITE.test
def test_tables():
    # Rules in http://www.w3.org/TR/CSS21/tables.html#anonymous-boxes
    # Rule 1.3
    # Also table model: http://www.w3.org/TR/CSS21/tables.html#model
    assert_tree(parse_all('''
        <table>
            <tr>
                <th>foo</th>
                <th>bar</th>
            </tr>
            <tfoot></tfoot>
            <thead><th></th></thead>
            <caption style="caption-side: bottom"></caption>
            <thead></thead>
            <col></col>
            <caption>top caption</caption>
            <tr>
                <td>baz</td>
            </tr>
        </table>
    '''), [
        ('table', 'AnonBlock', [
            ('caption', 'TableCaption', [
                ('caption', 'Line', [
                    ('caption', 'Text', 'top caption')])]),
            ('table', 'Table', [
                ('table', 'AnonTableColumnGroup', [
                    ('col', 'TableColumn', '<column>')]),
                ('thead', 'TableRowGroup', [
                    ('thead', 'AnonTableRow', [
                        ('th', 'TableCell', [])])]),
                ('table', 'AnonTableRowGroup', [
                    ('tr', 'TableRow', [
                        ('th', 'TableCell', [
                            ('th', 'Line', [
                                ('th', 'Text', 'foo')])]),
                        ('th', 'TableCell', [
                            ('th', 'Line', [
                                ('th', 'Text', 'bar')])])])]),
                ('thead', 'TableRowGroup', []),
                ('table', 'AnonTableRowGroup', [
                    ('tr', 'TableRow', [
                        ('td', 'TableCell', [
                            ('td', 'Line', [
                                ('td', 'Text', 'baz')])])])]),
                ('tfoot', 'TableRowGroup', [])]),
            ('caption', 'TableCaption', [])])])

    # Rules 1.4 and 3.1
    assert_tree(parse_all('''
        <span style="display: table-cell">foo</span>
        <span style="display: table-cell">bar</span>
    '''), [
        ('body', 'AnonBlock', [
            ('body', 'AnonTable', [
                ('body', 'AnonTableRowGroup', [
                    ('body', 'AnonTableRow', [
                        ('span', 'TableCell', [
                            ('span', 'Line', [
                                ('span', 'Text', 'foo')])]),
                        ('span', 'TableCell', [
                            ('span', 'Line', [
                                ('span', 'Text', 'bar')])])])])])])])

    # http://www.w3.org/TR/CSS21/tables.html#anonymous-boxes
    # Rules 1.1 and 1.2
    assert_tree(parse_all('''
        <span style="display: table-column-group">
            1
            <em style="display: table-column">
                2
                <strong>3</strong>
            </em>
            <strong>4</strong>
        </span>
    '''), [
        ('body', 'AnonBlock', [
            ('body', 'AnonTable', [
                ('span', 'TableColumnGroup', [
                    ('em', 'TableColumn', '<column>')])])])])

    # Rules 2.1 then 2.3
    assert_tree(parse_all('<table>foo <div></div></table>'), [
        ('table', 'AnonBlock', [
            ('table', 'Table', [
                ('table', 'AnonTableRowGroup', [
                    ('table', 'AnonTableRow', [
                        ('table', 'AnonTableCell', [
                            ('table', 'AnonBlock', [
                                ('table', 'Line', [
                                    ('table', 'Text', 'foo ')])]),
                            ('div', 'Block', [])])])])])])])

    # Rule 2.2
    assert_tree(parse_all('<thead><div></div><td></td></thead>'), [
        ('body', 'AnonBlock', [
            ('body', 'AnonTable', [
                ('thead', 'TableRowGroup', [
                    ('thead', 'AnonTableRow', [
                        ('thead', 'AnonTableCell', [
                            ('div', 'Block', [])]),
                        ('td', 'TableCell', [])])])])])])

    # TODO: re-enable this once we support inline-table
#    # Rule 3.2
#    assert_tree(parse_all('<span><tr></tr></span>'), [
#        ('body', 'Line', [
#            ('span', 'Inline', [
#                ('span', 'AnonInlineBlock', [
#                    ('span', 'AnonInlineTable', [
#                        ('span', 'AnonTableRowGroup', [
#                            ('tr', 'TableRow', [])])])])])])])

#    # Rule 3.1
#    # Also, rule 1.3 does not apply: whitespace before and after is preserved
#    assert_tree(parse_all('''
#        <span>
#            <em style="display: table-cell"></em>
#            <em style="display: table-cell"></em>
#        </span>
#    '''), [
#        ('body', 'Line', [
#            ('span', 'Inline', [
#                # Whitespace is preserved in table handling, then collapsed
#                # into a single space.
#                ('span', 'Text', ' '),
#                ('span', 'AnonInlineBlock', [
#                    ('span', 'AnonInlineTable', [
#                        ('span', 'AnonTableRowGroup', [
#                            ('span', 'AnonTableRow', [
#                                ('em', 'TableCell', []),
#                                ('em', 'TableCell', [])])])])]),
#                ('span', 'Text', ' ')])])])

    # Rule 3.2
    assert_tree(parse_all('<tr></tr>\t<tr></tr>'), [
        ('body', 'AnonBlock', [
            ('body', 'AnonTable', [
                ('body', 'AnonTableRowGroup', [
                    ('tr', 'TableRow', []),
                    ('tr', 'TableRow', [])])])])])
    assert_tree(parse_all('<col></col>\n<colgroup></colgroup>'), [
        ('body', 'AnonBlock', [
            ('body', 'AnonTable', [
                ('body', 'AnonTableColumnGroup', [
                    ('col', 'TableColumn', '<column>')]),
                ('colgroup', 'TableColumnGroup', [])])])])


@SUITE.test
def test_table_style():
    html = parse_all('<table style="margin: 1px; padding: 2px"></table>')
    body, = html.children
    wrapper, = body.children
    table, = wrapper.children
    assert isinstance(wrapper, boxes.BlockBox)
    assert isinstance(table, boxes.TableBox)
    assert wrapper.style.margin_top == 1
    assert wrapper.style.padding_top == 0
    assert table.style.margin_top == 0
    assert table.style.padding_top == 2


@SUITE.test
def test_column_style():
    html = parse_all('''
        <table>
            <col span=3 style="width: 10px"></col>
            <col span=2></col>
        </table>
    ''')
    body, = html.children
    wrapper, = body.children
    table, = wrapper.children
    colgroup, = table.column_groups
    widths = [col.style.width for col in colgroup.children]
    assert widths == [10, 10, 10, 'auto', 'auto']
    assert [col.grid_x for col in colgroup.children] == [0, 1, 2, 3, 4]
    # copies, not the same box object
    assert colgroup.children[0] is not colgroup.children[1]


@SUITE.test
def test_nested_grid_x():
    html = parse_all('''
        <table>
            <col span=2></col>
            <colgroup span=2></colgroup>
            <colgroup>
                <col></col>
                <col span=2></col>
            </colgroup>
            <col></col>
        </table>
    ''')
    body, = html.children
    wrapper, = body.children
    table, = wrapper.children
    grid = [(colgroup.grid_x, [col.grid_x for col in colgroup.children])
            for colgroup in table.column_groups]
    assert grid == [(0, [0, 1]), (2, []), (4, [4, 5, 6]), (7, [7])]


@SUITE.test
def test_colspan_rowspan():
    """
    +---+---+---+
    | A | B | C | #
    +---+---+---+
    | D |     E | #
    +---+---+   +---+
    |  F ...|   |   |   <-- overlap
    +---+---+---+   +
    | H | #   # | G |
    +---+---+   +   +
    | I | J | # |   |
    +---+---+   +---+

    # empty cells

    """
    html = parse_all('''
        <table>
            <tr>
                <td>A <td>B <td>C
            </tr>
            <tr>
                <td>D <td colspan=2 rowspan=2>E
            </tr>
            <tr>
                <td colspan=2>F <td rowspan=0>G
            </tr>
            <tr>
                <td>H
            </tr>
            <tr>
                <td>I <td>J
            </tr>
        </table>
    ''')
    body, = html.children
    wrapper, = body.children
    table, = wrapper.children
    group, = table.children
    assert [[c.grid_x for c in row.children] for row in group.children] == [
        [0, 1, 2],
        [0, 1],
        [0,      3],
        [0],
        [0, 1],
    ]
    assert [[c.colspan for c in row.children] for row in group.children] == [
        [1, 1, 1],
        [1, 2],
        [2,      1],
        [1],
        [1, 1],
    ]
    assert [[c.rowspan for c in row.children] for row in group.children] == [
        [1, 1, 1],
        [1, 2],
        [1,      3],
        [1],
        [1, 1],
    ]
