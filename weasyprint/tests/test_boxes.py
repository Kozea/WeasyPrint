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

from .testing_utils import resource_filename, TestPNGDocument, assert_no_logs
from ..css import validation
from ..formatting_structure import boxes, build, counters


SUITE = Tests()
SUITE.context(assert_no_logs)


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


def test_no_log(test_function):
    """Add a test function to the suite, and check that is produces no log."""
    SUITE.test(assert_no_logs(test_function))


def serialize(box_list):
    """Transform a box list into a structure easier to compare for testing."""
    return [
        (
            box.element_tag,
            ('Anon'
                 if box.style.anonymous and
                       type(box) not in (boxes.TextBox, boxes.LineBox)
                 else ''
             ) + type(box).__name__[:-3],
            (
            # All concrete boxes are either text, replaced, column or parent.
            box.text if isinstance(box, boxes.TextBox)
            else '<replaced>' if isinstance(box, boxes.ReplacedBox)
            else serialize(getattr(box, 'column_groups', ()) + box.children)))
        for box in box_list
    ]


def unwrap_html_body(box):
    """Test that the box tree starts with a ``<html>`` and a ``<body>`` blocks.

    Remove them to simplify further tests. These are always at the root
    of HTML documents.

    """
    assert box.element_tag == 'html'
    assert isinstance(box, boxes.BlockBox)
    assert len(box.children) == 1

    box = box.children[0]
    assert isinstance(box, boxes.BlockBox)
    assert box.element_tag == 'body'

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
                ('img', 'InlineReplaced', '<replaced>'),
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
        if child.style.anonymous:
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
                    ('img', 'InlineReplaced', '<replaced>'),
                    ('strong', 'Text', ' sit')]),
                ('p', 'Text', '.')])]),
        ('pre', 'Block', [
            ('pre', 'Line', [
                # pre
                ('pre', 'Text', u'\t\xA0\xA0foo\n')])]),
        ('pre', 'Block', [
            ('pre', 'Line', [
                # pre-wrap
                ('pre', 'Text', u'\t\xA0\xA0\u200Bfoo\n')])]),
        ('pre', 'Block', [
            ('pre', 'Line', [
                # pre-line
                ('pre', 'Text', u'foo\n')])])])


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

    def assert_page_margins(page_type, top, right, bottom, left):
        """Check the page margin values."""
        style = document.style_for(page_type)
        assert style.margin_top == top
        assert style.margin_right == right
        assert style.margin_bottom == bottom
        assert style.margin_left == left

    assert_page_margins('first_left_page', top=20, right=3, bottom=3, left=10)
    assert_page_margins('first_right_page', top=20, right=10, bottom=3, left=3)
    assert_page_margins('left_page', top=10, right=3, bottom=3, left=10)
    assert_page_margins('right_page', top=10, right=10, bottom=3, left=3)


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
                    ('col', 'TableColumn', [])]),
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
    # Rule XXX (not in the spec): column groups have at least one column child
    assert_tree(parse_all('''
        <span style="display: table-column-group">
            1
            <em style="display: table-column">
                2
                <strong>3</strong>
            </em>
            <strong>4</strong>
        </span>
        <ins style="display: table-column-group"></ins>
    '''), [
        ('body', 'AnonBlock', [
            ('body', 'AnonTable', [
                ('span', 'TableColumnGroup', [
                    ('em', 'TableColumn', [])]),
                ('ins', 'TableColumnGroup', [
                    ('ins', 'AnonTableColumn', [])])])])])

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
                    ('col', 'TableColumn', [])]),
                ('colgroup', 'TableColumnGroup', [
                    ('colgroup', 'AnonTableColumn', [])])])])])


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
    assert grid == [(0, [0, 1]), (2, [2, 3]), (4, [4, 5, 6]), (7, [7])]


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


@SUITE.test
def test_before_after():
    """Test the :before and :after pseudo-elements."""
    assert_tree(parse_all('''
        <style>
            p:before { content: normal }
            div:before { content: none }
            section:before { color: black }
        </style>
        <p></p>
        <div></div>
        <section></section>
    '''), [
        # No content in pseudo-element, no box generated
        ('p', 'Block', []),
        ('div', 'Block', []),
        ('section', 'Block', [])])

    assert_tree(parse_all('''
        <style>
            p:before { content: 'a' 'b' }
            p:after { content: 'd' 'e' }
        </style>
        <p>
            c
        </p>
    '''), [
        ('p', 'Block', [
            ('p', 'Line', [
                ('p:before', 'Inline', [
                    ('p:before', 'Text', 'ab')]),
                ('p', 'Text', ' c '),
                ('p:after', 'Inline', [
                    ('p:after', 'Text', 'de')])])])])

    assert_tree(parse_all('''
        <style>
            a[href]:before { content: '[' attr(href) '] ' }
        </style>
        <p><a href="some url">some text</a></p>
    '''), [
        ('p', 'Block', [
            ('p', 'Line', [
                ('a', 'Inline', [
                    ('a:before', 'Inline', [
                        ('a:before', 'Text', '[some url] ')]),
                    ('a', 'Text', 'some text')])])])])

    assert_tree(parse_all(u'''
        <style>
            body { quotes: '«' '»' '“' '”' }
            q:before { content: open-quote ' '}
            q:after { content: ' ' close-quote }
        </style>
        <p><q>Lorem ipsum <q>dolor</q> sit amet</q></p>
    '''), [
        ('p', 'Block', [
            ('p', 'Line', [
                ('q', 'Inline', [
                    ('q:before', 'Inline', [
                        ('q:before', 'Text', u'« ')]),
                    ('q', 'Text', 'Lorem ipsum '),
                    ('q', 'Inline', [
                        ('q:before', 'Inline', [
                            ('q:before', 'Text', u'“ ')]),
                        ('q', 'Text', 'dolor'),
                        ('q:after', 'Inline', [
                            ('q:after', 'Text', u' ”')])]),
                    ('q', 'Text', ' sit amet'),
                    ('q:after', 'Inline', [
                        ('q:after', 'Text', u' »')])])])])])

    assert_tree(parse_all('''
        <style>
            p:before { content: 'a' url(pattern.png) 'b'}
        </style>
        <p>c</p>
    '''), [
        ('p', 'Block', [
            ('p', 'Line', [
                ('p:before', 'Inline', [
                    ('p:before', 'Text', 'a'),
                    ('p:before', 'AnonInlineReplaced', '<replaced>'),
                    ('p:before', 'Text', 'b')]),
                ('p', 'Text', 'c')])])])


@SUITE.test
def test_counters():
    """Test counter-reset, counter-increment, content: counter() counters()"""
    assert_tree(parse_all('''
        <style>
            p { counter-increment: p 2 }
            p:before { content: counter(p); }
            p:nth-child(1) { counter-increment: none; }
            p:nth-child(2) { counter-increment: p; }
        </style>
        <p></p>
        <p></p>
        <p></p>
        <p style="counter-reset: p 117 p"></p>
        <p></p>
        <p></p>
        <p style="counter-reset: p -13"></p>
        <p></p>
        <p></p>
        <p style="counter-reset: p 42"></p>
        <p></p>
        <p></p>
    '''), [
        ('p', 'Block', [
            ('p', 'Line', [
                ('p:before', 'Inline', [
                    ('p:before', 'Text', counter)])])])
        for counter in '0 1 3  2 4 6  -11 -9 -7  44 46 48'.split()])

    assert_tree(parse_all('''
        <ol style="list-style-position: inside">
            <li></li>
            <li></li>
            <li></li>
            <li><ol>
                <li></li>
                <li style="counter-increment: none"></li>
                <li></li>
            </ol></li>
            <li></li>
        </ol>
    '''), [
        ('ol', 'Block', [
            ('li', 'Block', [
                ('li', 'Line', [
                    ('li::marker', 'Text', '1.')])]),
            ('li', 'Block', [
                ('li', 'Line', [
                    ('li::marker', 'Text', '2.')])]),
            ('li', 'Block', [
                ('li', 'Line', [
                    ('li::marker', 'Text', '3.')])]),
            ('li', 'Block', [
                ('li', 'AnonBlock', [
                    ('li', 'Line', [
                        ('li::marker', 'Text', '4.')])]),
                ('ol', 'Block', [
                    ('li', 'Block', [
                        ('li', 'Line', [
                            ('li::marker', 'Text', '1.')])]),
                    ('li', 'Block', [
                        ('li', 'Line', [
                            ('li::marker', 'Text', '1.')])]),
                    ('li', 'Block', [
                        ('li', 'Line', [
                            ('li::marker', 'Text', '2.')])])])]),
            ('li', 'Block', [
                ('li', 'Line', [
                    ('li::marker', 'Text', '5.')])])])])

    assert_tree(parse_all('''
        <style>
            p { display: list-item; list-style: inside decimal }
        </style>
        <div>
            <p></p>
            <p></p>
            <p style="counter-reset: list-item 7 list-item -56"></p>
        </div>
        <p></p>
    '''), [
        ('div', 'Block', [
            ('p', 'Block', [
                ('p', 'Line', [
                    ('p::marker', 'Text', '1.')])]),
            ('p', 'Block', [
                ('p', 'Line', [
                    ('p::marker', 'Text', '2.')])]),
            ('p', 'Block', [
                ('p', 'Line', [
                    ('p::marker', 'Text', '-55.')])])]),
        ('p', 'Block', [
            ('p', 'Line', [
                ('p::marker', 'Text', '1.')])])])

    assert_tree(parse_all('''
        <style>
            section:before { counter-reset: h; content: '' }
            h1:before { counter-increment: h; content: counters(h, '.') }
        </style>
        <body>
            <section>
                <h1></h1>
                <h1></h1>
                <section>
                    <h1></h1>
                    <h1></h1>
                </section>
                <h1></h1>
            </section>
        </body>
    '''), [
        ('section', 'Block', [
            ('section', 'AnonBlock', [
                ('section', 'Line', [
                    ('section:before', 'Inline', [])])]),
            ('h1', 'Block', [
                ('h1', 'Line', [
                    ('h1:before', 'Inline', [
                        ('h1:before', 'Text', '1')])])]),
            ('h1', 'Block', [
                ('h1', 'Line', [
                    ('h1:before', 'Inline', [
                        ('h1:before', 'Text', '2')])])]),
            ('section', 'Block', [
                ('section', 'AnonBlock', [
                    ('section', 'Line', [
                        ('section:before', 'Inline', [])])]),
                ('h1', 'Block', [
                    ('h1', 'Line', [
                        ('h1:before', 'Inline', [
                            ('h1:before', 'Text', '2.1')])])]),
                ('h1', 'Block', [
                    ('h1', 'Line', [
                        ('h1:before', 'Inline', [
                            ('h1:before', 'Text', '2.2')])])])]),
            ('h1', 'Block', [
                ('h1', 'Line', [
                    ('h1:before', 'Inline', [
                        ('h1:before', 'Text', '3')])])])])])


@SUITE.test
def test_counter_styles():
    """Test the various counter styles."""
    assert_tree(parse_all('''
        <style>
            body { counter-reset: p -12 }
            p { counter-increment: p }
            p:nth-child(1):before { content: '-' counter(p, none) '-'; }
            p:nth-child(2):before { content: counter(p, disc); }
            p:nth-child(3):before { content: counter(p, circle); }
            p:nth-child(4):before { content: counter(p, square); }
            p:nth-child(5):before { content: counter(p); }
        </style>
        <p></p>
        <p></p>
        <p></p>
        <p></p>
        <p></p>
    '''), [
        ('p', 'Block', [
            ('p', 'Line', [
                ('p:before', 'Inline', [
                    ('p:before', 'Text', counter)])])])
        for counter in u'--  •  ◦  ▪  -7'.split()])

    assert_tree(parse_all('''
        <style>
            p { counter-increment: p }
            p:before { content: counter(p, decimal-leading-zero); }
        </style>
        <p style="counter-reset: p -1987"></p>
        <p></p>
        <p style="counter-reset: p -12"></p>
        <p></p>
        <p></p>
        <p></p>
        <p style="counter-reset: p -2"></p>
        <p></p>
        <p></p>
        <p></p>
        <p style="counter-reset: p 8"></p>
        <p></p>
        <p></p>
        <p style="counter-reset: p 98"></p>
        <p></p>
        <p></p>
        <p style="counter-reset: p 4134"></p>
        <p></p>
    '''), [
        ('p', 'Block', [
            ('p', 'Line', [
                ('p:before', 'Inline', [
                    ('p:before', 'Text', counter)])])])
        for counter in u'''-1986 -1985  -11 -10 -09 -08  -01 00 01 02  09 10 11
                            99 100 101  4135 4136'''.split()])

    # Same test as above, but short-circuit HTML and boxes

    assert [counters.format(value, 'decimal-leading-zero') for value in [
        -1986, -1985,  -11, -10, -9, -8,  -1, 0, 1, 2,  9, 10, 11,
        99, 100, 101,  4135, 4136
    ]] == '''
        -1986 -1985  -11 -10 -09 -08  -01 00 01 02  09 10 11
        99 100 101  4135 4136
    '''.split()

    # Now that we’re confident that they do the same, use the shorter form.

# http://test.csswg.org/suites/css2.1/20110323/html4/content-counter-007.htm
    assert [counters.format(value, 'lower-roman') for value in [
        -1986, -1985,  -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
        49, 50,  389, 390,  3489, 3490, 3491, 4999, 5000, 5001
    ]] == '''
        -1986 -1985  -1 0 i ii iii iv v vi vii viii ix x xi xii
        xlix l  ccclxxxix cccxc  mmmcdlxxxix mmmcdxc mmmcdxci
        mmmmcmxcix  5000 5001
    '''.split()

# http://test.csswg.org/suites/css2.1/20110323/html4/content-counter-008.htm
    assert [counters.format(value, 'upper-roman') for value in [
        -1986, -1985,  -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
        49, 50,  389, 390,  3489, 3490, 3491, 4999, 5000, 5001
    ]] == '''
        -1986 -1985  -1 0 I II III IV V VI VII VIII IX X XI XII
        XLIX L  CCCLXXXIX CCCXC  MMMCDLXXXIX MMMCDXC MMMCDXCI
        MMMMCMXCIX 5000 5001
    '''.split()

    assert [counters.format(value, 'lower-alpha') for value in [
        -1986, -1985,  -1, 0, 1, 2, 3, 4,  25, 26, 27, 28, 29,  2002, 2003
    ]] == '''
        -1986 -1985  -1 0 a b c d  y z aa ab ac bxz bya
    '''.split()

    assert [counters.format(value, 'upper-alpha') for value in [
        -1986, -1985,  -1, 0, 1, 2, 3, 4,  25, 26, 27, 28, 29,  2002, 2003
    ]] == '''
        -1986 -1985  -1 0 A B C D  Y Z AA AB AC BXZ BYA
    '''.split()

    assert [counters.format(value, 'lower-latin') for value in [
        -1986, -1985,  -1, 0, 1, 2, 3, 4,  25, 26, 27, 28, 29,  2002, 2003
    ]] == '''
        -1986 -1985  -1 0 a b c d  y z aa ab ac bxz bya
    '''.split()

    assert [counters.format(value, 'upper-latin') for value in [
        -1986, -1985,  -1, 0, 1, 2, 3, 4,  25, 26, 27, 28, 29,  2002, 2003
    ]] == '''
        -1986 -1985  -1 0 A B C D  Y Z AA AB AC BXZ BYA
    '''.split()

# http://test.csswg.org/suites/css2.1/20110323/html4/content-counter-009.htm
    assert [counters.format(value, 'georgian') for value in [
        -1986, -1985,  -1, 0, 1,
        2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
        20, 30, 40, 50, 60, 70, 80, 90, 100,
        200, 300, 400, 500, 600, 700, 800, 900, 1000,
        2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000,
        19999, 20000, 20001
    ]] == u'''
        -1986 -1985  -1 0 ა
        ბ გ დ ე ვ ზ ჱ თ ი ია იბ
        კ ლ მ ნ ჲ ო პ ჟ რ
        ს ტ ჳ ფ ქ ღ ყ შ ჩ
        ც ძ წ ჭ ხ ჴ ჯ ჰ ჵ
        ჵჰშჟთ 20000 20001
    '''.split()

# http://test.csswg.org/suites/css2.1/20110323/html4/content-counter-010.htm
    assert [counters.format(value, 'armenian') for value in [
        -1986, -1985,  -1, 0, 1,
        2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
        20, 30, 40, 50, 60, 70, 80, 90, 100,
        200, 300, 400, 500, 600, 700, 800, 900, 1000,
        2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000,
        9999, 10000, 10001
    ]] == u'''
        -1986 -1985  -1 0 Ա
        Բ Գ Դ Ե Զ Է Ը Թ Ժ ԺԱ ԺԲ
        Ի Լ Խ Ծ Կ Հ Ձ Ղ Ճ
        Մ Յ Ն Շ Ո Չ Պ Ջ Ռ
        Ս Վ Տ Ր Ց Ւ Փ Ք
        ՔՋՂԹ 10000 10001
    '''.split()


@SUITE.test
def test_margin_boxes():
    """
    Test that the correct margin boxes are created.
    """
    document = TestPNGDocument.from_string('''
        <style>
            @page {
                /* Make the page content area only 10px high and wide,
                   so every word in <p> end up on a page of its own. */
                -weasy-size: 30px;
                margin: 10px;
                @top-center { content: "Title" }
            }
            @page :first {
                @bottom-left { content: "foo" }
                @bottom-left-corner { content: "baz" }
            }
        </style>
        <p>lorem ipsum
    ''')
    page_1, page_2 = document.pages
    assert page_1.children[0].element_tag == 'html'
    assert page_2.children[0].element_tag == 'html'

    margin_boxes_1 = [box.at_keyword for box in page_1.children[1:]]
    margin_boxes_2 = [box.at_keyword for box in page_2.children[1:]]
    # Order matters, see http://dev.w3.org/csswg/css3-page/#painting
    assert margin_boxes_1 == ['@bottom-left', '@bottom-left-corner',
                              '@top-center']
    assert margin_boxes_2 == ['@top-center']

    html, top_center = page_2.children
    line_box, = top_center.children
    text_box, = line_box.children
    assert text_box.text == 'Title'


@SUITE.test
def test_page_counters():
    """Test page-based counters."""
    document = TestPNGDocument.from_string(u'''
        <style>
            @page {
                /* Make the page content area only 10px high and wide,
                   so every word in <p> end up on a page of its own. */
                -weasy-size: 30px;
                margin: 10px;
                @bottom-center {
                    content: "Page " counter(page) " of " counter(pages) ".";
                }
            }
        </style>
        <p>lorem ipsum dolor
    ''')
    for page_number, page in enumerate(document.pages, 1):
        html, bottom_center = page.children
        line_box, = bottom_center.children
        text_box, = line_box.children
        assert text_box.text == u'Page {} of 3.'.format(page_number)
