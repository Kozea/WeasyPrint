# coding: utf8
"""
    weasyprint.tests.test_boxes
    ---------------------------

    Test that the "before layout" box tree is correctly constructed.

    :copyright: Copyright 2011-2013 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import functools
import pprint
import difflib

from .testing_utils import (
    resource_filename, TestHTML, assert_no_logs, capture_logs)
from ..css import get_all_computed_styles
from .. import images
from ..formatting_structure import boxes, build, counters


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
}.items())


def serialize(box_list):
    """Transform a box list into a structure easier to compare for testing."""
    return [
        (box.element_tag,
         ('Anon' if (box.style.anonymous and
                     type(box) not in (boxes.TextBox, boxes.LineBox))
          else '') + type(box).__name__[:-3],
         # All concrete boxes are either text, replaced, column or parent.
         (box.text if isinstance(box, boxes.TextBox)
          else '<replaced>' if isinstance(box, boxes.ReplacedBox)
          else serialize(getattr(box, 'column_groups', ()) + box.children)))
        for box in box_list]


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


def _parse_base(
        html_content,
        # Dummy filename, but in the right directory.
        base_url=resource_filename('<test>')):
    document = TestHTML(string=html_content, base_url=base_url)
    style_for = get_all_computed_styles(document)
    get_image_from_uri = functools.partial(
        images.get_image_from_uri, {}, document.url_fetcher)
    return document.root_element, style_for, get_image_from_uri


def parse(html_content):
    """Parse some HTML, apply stylesheets and transform to boxes."""
    box, = build.element_to_box(*_parse_base(html_content))
    return box


def parse_all(html_content, base_url=resource_filename('<test>')):
    """Like parse() but also run all corrections on boxes."""
    box = build.build_formatting_structure(*_parse_base(
        html_content, base_url))
    sanity_checks(box)
    return box


def render_pages(html_content):
    """Lay out a document and return a list of PageBox objects."""
    return [p._page_box for p in TestHTML(
            string=html_content, base_url=resource_filename('<test>')
            ).render(enable_hinting=True).pages]


def assert_tree(box, expected):
    """Check the box tree equality.

    The obtained result is prettified in the message in case of failure.

    box: a Box object, starting with <html> and <body> blocks.
    expected: a list of serialized <body> children as returned by to_lists().

    """
    lists = to_lists(box)
    if lists != expected:
        print(''.join(difflib.unified_diff(
            *(pprint.pformat(v).splitlines(keepends=True)
              for v in [lists, expected]),
            n=9999)))
        assert lists == expected


def sanity_checks(box):
    """Check that the rules regarding boxes are met.

    This is not required and only helps debugging.

    - A block container can contain either only block-level boxes or
      only line boxes;
    - Line boxes and inline boxes can only contain inline-level boxes.

    """
    if not isinstance(box, boxes.ParentBox):
        return

    acceptable_types_lists = None  # raises when iterated
    for class_ in type(box).mro():
        if class_ in PROPER_CHILDREN:
            acceptable_types_lists = PROPER_CHILDREN[class_]
            break

    assert any(
        all(isinstance(child, acceptable_types)
            or not child.is_in_normal_flow()
            for child in box.children)
        for acceptable_types in acceptable_types_lists
    ), (box, box.children)

    for child in box.children:
        sanity_checks(child)


@assert_no_logs
def test_box_tree():
    """Test the creation of trees from HTML strings."""
    assert_tree(parse('<p>'), [('p', 'Block', [])])
    assert_tree(parse(
        '''
        <style>
            span { display: inline-block }
        </style>
        <p>Hello <em>World <img src="pattern.png"><span>L</span></em>!</p>'''),
        [('p', 'Block', [
            ('p', 'Text', 'Hello '),
            ('em', 'Inline', [
                ('em', 'Text', 'World '),
                ('img', 'InlineReplaced', '<replaced>'),
                ('span', 'InlineBlock', [
                    ('span', 'Text', 'L')])]),
            ('p', 'Text', '!')])])


@assert_no_logs
def test_html_entities():
    """Test the management of HTML entities."""
    for quote in ['"', '&quot;', '&#x22;', '&#34;']:
        assert_tree(parse('<p>{0}abc{1}'.format(quote, quote)), [
            ('p', 'Block', [
                ('p', 'Text', '"abc"')])])


@assert_no_logs
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

    source = '<div><p>Lipsum.</p>Hello, <em>World</em>!\n</div>'
    expected = [
        ('div', 'Block', [
            ('p', 'Block', [
                ('p', 'Line', [
                    ('p', 'Text', 'Lipsum.')])]),
            ('div', 'AnonBlock', [
                ('div', 'Line', [
                    ('div', 'Text', 'Hello, '),
                    ('em', 'Inline', [
                        ('em', 'Text', 'World')]),
                    ('div', 'Text', '!\n')])])])]
    box = parse(source)
    box = build.inline_in_block(box)
    assert_tree(box, expected)

    # Absolutes are left in the lines to get their static position later.
    source = '''<p>Hello <em style="position:absolute;
                                    display: block">World</em>!</p>'''
    expected = [
        ('p', 'Block', [
            ('p', 'Line', [
                ('p', 'Text', 'Hello '),
                ('em', 'Block', [
                    ('em', 'Line', [
                        ('em', 'Text', 'World')])]),
                ('p', 'Text', '!')])])]
    box = parse(source)
    box = build.inline_in_block(box)
    assert_tree(box, expected)
    box = build.block_in_inline(box)
    assert_tree(box, expected)

    # Floats are pull to the top of their containing blocks
    source = '<p>Hello <em style="float: left">World</em>!</p>'
    box = parse(source)
    box = build.inline_in_block(box)
    box = build.block_in_inline(box)
    assert_tree(box, [
        ('p', 'Block', [
            ('p', 'Line', [
                ('p', 'Text', 'Hello '),
                ('em', 'Block', [
                    ('em', 'Line', [
                        ('em', 'Text', 'World')])]),
                ('p', 'Text', '!')])])])


@assert_no_logs
def test_block_in_inline():
    """Test the management of block boxes in inline boxes."""
    box = parse('''
<style>
    p { display: inline-block; }
    span, i { display: block; }
</style>
<p>Lorem <em>ipsum <strong>dolor <span>sit</span>
    <span>amet,</span></strong><span><em>conse<i></i></em></span></em></p>''')
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
                                    ('em', 'Text', 'conse'),
                                    ('i', 'Block', [])])])])])])])])])

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
                                ('em', 'Text', 'conse')])])]),
                    ('i', 'Block', []),
                    ('span', 'AnonBlock', [
                        ('span', 'Line', [
                            ('em', 'Inline', [])])])]),
                ('p', 'AnonBlock', [
                    ('p', 'Line', [
                        ('em', 'Inline', [])])])])])])


@assert_no_logs
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
        assert child.style.color == (0, 0, 1, 1)  # blue
        # Only non-anonymous boxes have margins
        if child.style.anonymous:
            assert child.style.margin_top == (0, 'px')
        else:
            assert child.style.margin_top == (42, 'px')


@assert_no_logs
def test_whitespace():
    """Test the management of white spaces."""
    # TODO: test more cases
    # http://www.w3.org/TR/CSS21/text.html#white-space-model
    assert_tree(parse_all('''
        <p>Lorem \t\r\n  ipsum\t<strong>  dolor
            <img src=pattern.png> sit
            <span style="position: absolute"></span> <em> amet </em>
            consectetur</strong>.</p>
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
                    ('strong', 'Text', ' sit '),
                    ('span', 'Block', []),
                    ('em', 'Inline', [
                        ('em', 'Text', 'amet ')]),
                    ('strong', 'Text', 'consectetur')]),
                ('p', 'Text', '.')])]),
        ('pre', 'Block', [
            ('pre', 'Line', [
                # pre
                ('pre', 'Text', '\t\xA0\xA0foo\n')])]),
        ('pre', 'Block', [
            ('pre', 'Line', [
                # pre-wrap
                ('pre', 'Text', '\t\xA0\xA0\u200Bfoo\n')])]),
        ('pre', 'Block', [
            ('pre', 'Line', [
                # pre-line
                ('pre', 'Text', ' foo\n')])])])


@assert_no_logs
def test_page_style():
    """Test the management of page styles."""
    style_for = get_all_computed_styles(TestHTML(string='''
        <style>
            @page { margin: 3px }
            @page :first { margin-top: 20px }
            @page :right { margin-right: 10px; margin-top: 10px }
            @page :left { margin-left: 10px; margin-top: 10px }
        </style>
    '''))

    def assert_page_margins(page_type, top, right, bottom, left):
        """Check the page margin values."""
        style = style_for(page_type)
        assert style.margin_top == (top, 'px')
        assert style.margin_right == (right, 'px')
        assert style.margin_bottom == (bottom, 'px')
        assert style.margin_left == (left, 'px')

    assert_page_margins('first_left_page', top=20, right=3, bottom=3, left=10)
    assert_page_margins('first_right_page', top=20, right=10, bottom=3, left=3)
    assert_page_margins('left_page', top=10, right=3, bottom=3, left=10)
    assert_page_margins('right_page', top=10, right=10, bottom=3, left=3)


@assert_no_logs
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


@assert_no_logs
def test_images():
    """Test images that may or may not be available."""
    with capture_logs() as logs:
        result = parse_all('''
            <p><img src=pattern.png
                /><img alt="No src"
                /><img src=inexistent.jpg alt="Inexistent src" /></p>
        ''')
    assert len(logs) == 1
    assert 'WARNING: Failed to load image' in logs[0]
    assert 'inexistent.jpg' in logs[0]
    assert_tree(result, [
        ('p', 'Block', [
            ('p', 'Line', [
                ('img', 'InlineReplaced', '<replaced>'),
                ('img', 'Inline', [
                    ('img', 'Text', 'No src')]),
                ('img', 'Inline', [
                    ('img', 'Text', 'Inexistent src')])])])])

    with capture_logs() as logs:
        result = parse_all('<p><img src=pattern.png alt="No base_url">',
                           base_url=None)
    assert len(logs) == 1
    assert 'WARNING: Relative URI reference without a base URI' in logs[0]
    assert_tree(result, [
        ('p', 'Block', [
            ('p', 'Line', [
                ('img', 'Inline', [
                    ('img', 'Text', 'No base_url')])])])])


@assert_no_logs
def test_tables():
    # Rules in http://www.w3.org/TR/CSS21/tables.html#anonymous-boxes
    # Rule 1.3
    # Also table model: http://www.w3.org/TR/CSS21/tables.html#model
    assert_tree(parse_all('''
        <x-table>
            <x-tr>
                <x-th>foo</x-th>
                <x-th>bar</x-th>
            </x-tr>
            <x-tfoot></x-tfoot>
            <x-thead><x-th></x-th></x-thead>
            <x-caption style="caption-side: bottom"></x-caption>
            <x-thead></x-thead>
            <x-col></x-col>
            <x-caption>top caption</x-caption>
            <x-tr>
                <x-td>baz</x-td>
            </x-tr>
        </x-table>
    '''), [
        ('x-table', 'AnonBlock', [
            ('x-caption', 'TableCaption', [
                ('x-caption', 'Line', [
                    ('x-caption', 'Text', 'top caption')])]),
            ('x-table', 'Table', [
                ('x-table', 'AnonTableColumnGroup', [
                    ('x-col', 'TableColumn', [])]),
                ('x-thead', 'TableRowGroup', [
                    ('x-thead', 'AnonTableRow', [
                        ('x-th', 'TableCell', [])])]),
                ('x-table', 'AnonTableRowGroup', [
                    ('x-tr', 'TableRow', [
                        ('x-th', 'TableCell', [
                            ('x-th', 'Line', [
                                ('x-th', 'Text', 'foo')])]),
                        ('x-th', 'TableCell', [
                            ('x-th', 'Line', [
                                ('x-th', 'Text', 'bar')])])])]),
                ('x-thead', 'TableRowGroup', []),
                ('x-table', 'AnonTableRowGroup', [
                    ('x-tr', 'TableRow', [
                        ('x-td', 'TableCell', [
                            ('x-td', 'Line', [
                                ('x-td', 'Text', 'baz')])])])]),
                ('x-tfoot', 'TableRowGroup', [])]),
            ('x-caption', 'TableCaption', [])])])

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
    assert_tree(parse_all('<x-table>foo <div></div></x-table>'), [
        ('x-table', 'AnonBlock', [
            ('x-table', 'Table', [
                ('x-table', 'AnonTableRowGroup', [
                    ('x-table', 'AnonTableRow', [
                        ('x-table', 'AnonTableCell', [
                            ('x-table', 'AnonBlock', [
                                ('x-table', 'Line', [
                                    ('x-table', 'Text', 'foo ')])]),
                            ('div', 'Block', [])])])])])])])

    # Rule 2.2
    assert_tree(parse_all('<x-thead style="display: table-header-group">'
                          '<div></div><x-td></x-td></x-thead>'), [
        ('body', 'AnonBlock', [
            ('body', 'AnonTable', [
                ('x-thead', 'TableRowGroup', [
                    ('x-thead', 'AnonTableRow', [
                        ('x-thead', 'AnonTableCell', [
                            ('div', 'Block', [])]),
                        ('x-td', 'TableCell', [])])])])])])

    # TODO: re-enable this once we support inline-table
    # Rule 3.2
    assert_tree(parse_all('<span><x-tr></x-tr></span>'), [
        ('body', 'Line', [
            ('span', 'Inline', [
                ('span', 'AnonInlineBlock', [
                    ('span', 'AnonInlineTable', [
                        ('span', 'AnonTableRowGroup', [
                            ('x-tr', 'TableRow', [])])])])])])])

    # Rule 3.1
    # Also, rule 1.3 does not apply: whitespace before and after is preserved
    assert_tree(parse_all('''
        <span>
            <em style="display: table-cell"></em>
            <em style="display: table-cell"></em>
        </span>
    '''), [
        ('body', 'Line', [
            ('span', 'Inline', [
                # Whitespace is preserved in table handling, then collapsed
                # into a single space.
                ('span', 'Text', ' '),
                ('span', 'AnonInlineBlock', [
                    ('span', 'AnonInlineTable', [
                        ('span', 'AnonTableRowGroup', [
                            ('span', 'AnonTableRow', [
                                ('em', 'TableCell', []),
                                ('em', 'TableCell', [])])])])]),
                ('span', 'Text', ' ')])])])

    # Rule 3.2
    assert_tree(parse_all('<x-tr></x-tr>\t<x-tr></x-tr>'), [
        ('body', 'AnonBlock', [
            ('body', 'AnonTable', [
                ('body', 'AnonTableRowGroup', [
                    ('x-tr', 'TableRow', []),
                    ('x-tr', 'TableRow', [])])])])])

    assert_tree(parse_all('<x-col></x-col>\n<x-colgroup></x-colgroup>'), [
        ('body', 'AnonBlock', [
            ('body', 'AnonTable', [
                ('body', 'AnonTableColumnGroup', [
                    ('x-col', 'TableColumn', [])]),
                ('x-colgroup', 'TableColumnGroup', [
                    ('x-colgroup', 'AnonTableColumn', [])])])])])


@assert_no_logs
def test_table_style():
    html = parse_all('<table style="margin: 1px; padding: 2px"></table>')
    body, = html.children
    wrapper, = body.children
    table, = wrapper.children
    assert isinstance(wrapper, boxes.BlockBox)
    assert isinstance(table, boxes.TableBox)
    assert wrapper.style.margin_top == (1, 'px')
    assert wrapper.style.padding_top == (0, 'px')
    assert table.style.margin_top == (0, 'px')
    assert table.style.padding_top == (2, 'px')


@assert_no_logs
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
    assert widths == [(10, 'px'), (10, 'px'), (10, 'px'), 'auto', 'auto']
    assert [col.grid_x for col in colgroup.children] == [0, 1, 2, 3, 4]
    # copies, not the same box object
    assert colgroup.children[0] is not colgroup.children[1]


@assert_no_logs
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


@assert_no_logs
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

    # A cell box cannot extend beyond the last row box of a table.
    html = parse_all('''
        <table>
            <tr>
                <td rowspan=5></td>
                <td></td>
            </tr>
            <tr>
                <td></td>
            </tr>
        </table>
    ''')
    body, = html.children
    wrapper, = body.children
    table, = wrapper.children
    group, = table.children
    assert [[c.grid_x for c in row.children] for row in group.children] == [
        [0, 1],
        [1],
    ]
    assert [[c.colspan for c in row.children] for row in group.children] == [
        [1, 1],
        [1],
    ]
    assert [[c.rowspan for c in row.children] for row in group.children] == [
        [2, 1],  # Not 5
        [1],
    ]


@assert_no_logs
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

    assert_tree(parse_all('''
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
                        ('q:before', 'Text', '« ')]),
                    ('q', 'Text', 'Lorem ipsum '),
                    ('q', 'Inline', [
                        ('q:before', 'Inline', [
                            ('q:before', 'Text', '“ ')]),
                        ('q', 'Text', 'dolor'),
                        ('q:after', 'Inline', [
                            ('q:after', 'Text', ' ”')])]),
                    ('q', 'Text', ' sit amet'),
                    ('q:after', 'Inline', [
                        ('q:after', 'Text', ' »')])])])])])
    with capture_logs() as logs:
        assert_tree(parse_all('''
            <style>
                p:before {
                    content: 'a' url(pattern.png) 'b';

                    /* Invalid, ignored in favor of the one above.
                       Regression test: this used to crash: */
                    content: some-function(nested-function(something));
                }
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
    assert len(logs) == 1
    assert 'nested-function(' in logs[0]
    assert 'invalid value' in logs[0]


@assert_no_logs
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
        <p></p>'''), [
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
        </ol>'''), [
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
        <p></p>'''), [
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
            <section><h1></h1>
                <h1></h1>
                <section><h1></h1>
                    <h1></h1>
                </section>
                <h1></h1>
            </section>
        </body>'''), [
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

    assert_tree(parse_all('''
        <style>
            p:before { content: counter(c) }
        </style>
        <div>
            <span style="counter-reset: c">
                Scope created now, deleted after the div
            </span>
        </div>
        <p></p>'''), [
        ('div', 'Block', [
            ('div', 'Line', [
                ('span', 'Inline', [
                    ('span', 'Text',
                     'Scope created now, deleted after the div ')])])]),
        ('p', 'Block', [
            ('p', 'Line', [
                ('p:before', 'Inline', [
                    ('p:before', 'Text', '0')])])])])

    # counter-increment may interfere with display: list-item
    assert_tree(parse_all('''
        <p style="counter-increment: c;
                  display: list-item; list-style: inside decimal">'''), [
        ('p', 'Block', [
            ('p', 'Line', [
                ('p::marker', 'Text', '0.')])])])


@assert_no_logs
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
        for counter in '--  •  ◦  ▪  -7'.split()])

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
        for counter in '''-1986 -1985  -11 -10 -09 -08  -01 00 01 02  09 10 11
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
    ]] == '''
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
    ]] == '''
        -1986 -1985  -1 0 Ա
        Բ Գ Դ Ե Զ Է Ը Թ Ժ ԺԱ ԺԲ
        Ի Լ Խ Ծ Կ Հ Ձ Ղ Ճ
        Մ Յ Ն Շ Ո Չ Պ Ջ Ռ
        Ս Վ Տ Ր Ց Ւ Փ Ք
        ՔՋՂԹ 10000 10001
    '''.split()


@assert_no_logs
def test_margin_boxes():
    """
    Test that the correct margin boxes are created.
    """
    page_1, page_2 = render_pages('''
        <style>
            @page {
                /* Make the page content area only 10px high and wide,
                   so every word in <p> end up on a page of its own. */
                size: 30px;
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
    assert page_1.children[0].element_tag == 'html'
    assert page_2.children[0].element_tag == 'html'

    margin_boxes_1 = [box.at_keyword for box in page_1.children[1:]]
    margin_boxes_2 = [box.at_keyword for box in page_2.children[1:]]
    assert margin_boxes_1 == ['@top-center', '@bottom-left',
                              '@bottom-left-corner']
    assert margin_boxes_2 == ['@top-center']

    html, top_center = page_2.children
    line_box, = top_center.children
    text_box, = line_box.children
    assert text_box.text == 'Title'


@assert_no_logs
def test_page_counters():
    """Test page-based counters."""
    pages = render_pages('''
        <style>
            @page {
                /* Make the page content area only 10px high and wide,
                   so every word in <p> end up on a page of its own. */
                size: 30px;
                margin: 10px;
                @bottom-center {
                    content: "Page " counter(page) " of " counter(pages) ".";
                }
            }
        </style>
        <p>lorem ipsum dolor
    ''')
    for page_number, page in enumerate(pages, 1):
        html, bottom_center = page.children
        line_box, = bottom_center.children
        text_box, = line_box.children
        assert text_box.text == 'Page {0} of 3.'.format(page_number)


@assert_no_logs
def test_border_collapse():
    html = parse_all('<table></table>')
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    assert isinstance(table, boxes.TableBox)
    assert not hasattr(table, 'collapsed_border_grid')

    def get_grid(html):
        html = parse_all(html)
        body, = html.children
        table_wrapper, = body.children
        table, = table_wrapper.children
        return tuple(
            [[(style, width, color) if width else None
              for _score, (style, width, color) in column]
             for column in grid]
            for grid in table.collapsed_border_grid)

    grid = get_grid('<table style="border-collapse: collapse"></table>')
    assert grid == ([], [])

    black = (0, 0, 0, 1)
    red = (1, 0, 0, 1)
    green = (0, 1, 0, 1)  # lime in CSS
    blue = (0, 0, 1, 1)
    yellow = (1, 1, 0, 1)

    vertical_borders, horizontal_borders = get_grid('''
        <style>td { border: 1px solid red }</style>
        <table style="border-collapse: collapse; border: 3px solid black">
            <tr> <td>A</td> <td>B</td> </tr>
            <tr> <td>C</td> <td>D</td> </tr>
        </table>
    ''')
    black_3 = ('solid', 3, black)
    red_1 = ('solid', 1, red)
    assert vertical_borders == [
        [black_3, red_1, black_3],
        [black_3, red_1, black_3],
    ]
    assert horizontal_borders == [
        [black_3, black_3],
        [red_1, red_1],
        [black_3, black_3],
    ]

    # hidden vs. none
    vertical_borders, horizontal_borders = get_grid('''
        <style>table, td { border: 3px solid }</style>
        <table style="border-collapse: collapse">
            <tr> <td>A</td> <td style="border-style: hidden">B</td> </tr>
            <tr> <td>C</td> <td style="border-style: none">D</td> </tr>
        </table>
    ''')
    assert vertical_borders == [
        [black_3, None, None],
        [black_3, black_3, black_3],
    ]
    assert horizontal_borders == [
        [black_3, None],
        [black_3, None],
        [black_3, black_3],
    ]

    yellow_5 = ('solid', 5, yellow)
    green_5 = ('solid', 5, green)
    dashed_blue_5 = ('dashed', 5, blue)
    vertical_borders, horizontal_borders = get_grid('''
        <style>td { border: 1px solid red }</style>
        <table style="border-collapse: collapse; border: 5px solid yellow">
            <col style="border: 3px solid black" />
            <tr> <td></td> <td></td> <td></td> </tr>
            <tr> <td></td> <td style="border: 5px dashed blue"></td>
                 <td style="border: 5px solid lime"></td> </tr>
            <tr> <td></td> <td></td> <td></td> </tr>
            <tr> <td></td> <td></td> <td></td> </tr>
        </table>
    ''')
    assert vertical_borders == [
        [yellow_5, black_3, red_1, yellow_5],
        [yellow_5, dashed_blue_5, green_5, green_5],
        [yellow_5, black_3, red_1, yellow_5],
        [yellow_5, black_3, red_1, yellow_5],
    ]
    assert horizontal_borders == [
        [yellow_5, yellow_5, yellow_5],
        [red_1, dashed_blue_5, green_5],
        [red_1, dashed_blue_5, green_5],
        [red_1, red_1, red_1],
        [yellow_5, yellow_5, yellow_5],
    ]

    # rowspan and colspan
    vertical_borders, horizontal_borders = get_grid('''
        <style>col, tr { border: 3px solid }</style>
        <table style="border-collapse: collapse">
            <col /><col /><col />
            <tr> <td rowspan=2></td> <td></td> <td></td> </tr>
            <tr>                     <td colspan=2></td> </tr>
        </table>
    ''')
    assert vertical_borders == [
        [black_3, black_3, black_3, black_3],
        [black_3, black_3, None, black_3],
    ]
    assert horizontal_borders == [
        [black_3, black_3, black_3],
        [None, black_3, black_3],
        [black_3, black_3, black_3],
    ]
