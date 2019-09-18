"""
    weasyprint.tests.test_boxes
    ---------------------------

    Test that the "before layout" box tree is correctly constructed.

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import functools

import pytest

from .. import images
from ..css import PageType, get_all_computed_styles
from ..css.targets import TargetCollector
from ..formatting_structure import boxes, build, counters
from ..layout.pages import set_page_type_computed_styles
from .testing_utils import BASE_URL, FakeHTML, assert_no_logs, capture_logs

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
    return [(
        box.element_tag,
        type(box).__name__[:-3],
        # All concrete boxes are either text, replaced, column or parent.
        (box.text if isinstance(box, boxes.TextBox)
            else '<replaced>' if isinstance(box, boxes.ReplacedBox)
            else serialize(
                getattr(box, 'column_groups', ()) + tuple(box.children))))
            for box in box_list]


def _parse_base(html_content, base_url=BASE_URL):
    document = FakeHTML(string=html_content, base_url=base_url)
    style_for = get_all_computed_styles(document)
    get_image_from_uri = functools.partial(
        images.get_image_from_uri, {}, document.url_fetcher)
    target_collector = TargetCollector()
    return (
        document.etree_element, style_for, get_image_from_uri, base_url,
        target_collector)


def parse(html_content):
    """Parse some HTML, apply stylesheets and transform to boxes."""
    box, = build.element_to_box(*_parse_base(html_content))
    return box


def parse_all(html_content, base_url=BASE_URL):
    """Like parse() but also run all corrections on boxes."""
    box = build.build_formatting_structure(*_parse_base(
        html_content, base_url))
    _sanity_checks(box)
    return box


def render_pages(html_content):
    """Lay out a document and return a list of PageBox objects."""
    return [p._page_box for p in FakeHTML(
            string=html_content, base_url=BASE_URL
            ).render(enable_hinting=True).pages]


def assert_tree(box, expected):
    """Check the box tree equality.

    The obtained result is prettified in the message in case of failure.

    box: a Box object, starting with <html> and <body> blocks.
    expected: a list of serialized <body> children as returned by to_lists().

    """
    assert box.element_tag == 'html'
    assert isinstance(box, boxes.BlockBox)
    assert len(box.children) == 1

    box = box.children[0]
    assert isinstance(box, boxes.BlockBox)
    assert box.element_tag == 'body'

    assert serialize(box.children) == expected


def _sanity_checks(box):
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
        all(isinstance(child, acceptable_types) or
            not child.is_in_normal_flow()
            for child in box.children)
        for acceptable_types in acceptable_types_lists
    ), (box, box.children)

    for child in box.children:
        _sanity_checks(child)


def _get_grid(html):
    html = parse_all(html)
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    return tuple(
        [[(style, width, color) if width else None
          for _score, (style, width, color) in column]
         for column in grid]
        for grid in table.collapsed_border_grid)


@assert_no_logs
def test_box_tree():
    assert_tree(parse('<p>'), [('p', 'Block', [])])
    assert_tree(parse('''
      <style>
        span { display: inline-block }
      </style>
      <p>Hello <em>World <img src="pattern.png"><span>L</span></em>!</p>'''), [
          ('p', 'Block', [
            ('p', 'Text', 'Hello '),
            ('em', 'Inline', [
                ('em', 'Text', 'World '),
                ('img', 'InlineReplaced', '<replaced>'),
                ('span', 'InlineBlock', [
                    ('span', 'Text', 'L')])]),
            ('p', 'Text', '!')])])


@assert_no_logs
def test_html_entities():
    for quote in ['"', '&quot;', '&#x22;', '&#34;']:
        assert_tree(parse('<p>{0}abc{1}'.format(quote, quote)), [
            ('p', 'Block', [
                ('p', 'Text', '"abc"')])])


@assert_no_logs
def test_inline_in_block_1():
    source = '<div>Hello, <em>World</em>!\n<p>Lipsum.</p></div>'
    expected = [
        ('div', 'Block', [
            ('div', 'Block', [
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


@assert_no_logs
def test_inline_in_block_2():
    source = '<div><p>Lipsum.</p>Hello, <em>World</em>!\n</div>'
    expected = [
        ('div', 'Block', [
            ('p', 'Block', [
                ('p', 'Line', [
                    ('p', 'Text', 'Lipsum.')])]),
            ('div', 'Block', [
                ('div', 'Line', [
                    ('div', 'Text', 'Hello, '),
                    ('em', 'Inline', [
                        ('em', 'Text', 'World')]),
                    ('div', 'Text', '!\n')])])])]
    box = parse(source)
    box = build.inline_in_block(box)
    assert_tree(box, expected)


@assert_no_logs
def test_inline_in_block_3():
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


@assert_no_logs
def test_inline_in_block_4():
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
    box = parse('''
      <style>
        p { display: inline-block; }
        span, i { display: block; }
      </style>
      <p>Lorem <em>ipsum <strong>dolor <span>sit</span>
      <span>amet,</span></strong><span><em>conse<i>''')
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
                            ('strong', 'Text', '\n      '),
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
                ('p', 'Block', [
                    ('p', 'Line', [
                        ('p', 'Text', 'Lorem '),
                        ('em', 'Inline', [
                            ('em', 'Text', 'ipsum '),
                            ('strong', 'Inline', [
                                ('strong', 'Text', 'dolor ')])])])]),
                ('span', 'Block', [
                    ('span', 'Line', [
                        ('span', 'Text', 'sit')])]),
                ('p', 'Block', [
                    ('p', 'Line', [
                        ('em', 'Inline', [
                            ('strong', 'Inline', [
                                # Whitespace processing not done yet.
                                ('strong', 'Text', '\n      ')])])])]),
                ('span', 'Block', [
                    ('span', 'Line', [
                        ('span', 'Text', 'amet,')])]),

                ('p', 'Block', [
                    ('p', 'Line', [
                        ('em', 'Inline', [
                            ('strong', 'Inline', [])])])]),
                ('span', 'Block', [
                    ('span', 'Block', [
                        ('span', 'Line', [
                            ('em', 'Inline', [
                                ('em', 'Text', 'conse')])])]),
                    ('i', 'Block', []),
                    ('span', 'Block', [
                        ('span', 'Line', [
                            ('em', 'Inline', [])])])]),
                ('p', 'Block', [
                    ('p', 'Line', [
                        ('em', 'Inline', [])])])])])])


@assert_no_logs
def test_styles():
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
        assert child.style['color'] == (0, 0, 1, 1)  # blue
        # Only non-anonymous boxes have margins
        assert child.style['margin_top'] in ((0, 'px'), (42, 'px'))


@assert_no_logs
def test_whitespace():
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
                ('pre', 'Text', '\t  foo\n')])]),
        ('pre', 'Block', [
            ('pre', 'Line', [
                # pre-wrap
                ('pre', 'Text', '\t  foo\n')])]),
        ('pre', 'Block', [
            ('pre', 'Line', [
                # pre-line
                ('pre', 'Text', ' foo\n')])])])


@assert_no_logs
@pytest.mark.parametrize('page_type, top, right, bottom, left', (
    (PageType(side='left', first=True, index=0, blank=None, name=None),
     20, 3, 3, 10),
    (PageType(side='right', first=True, index=0, blank=None, name=None),
     20, 10, 3, 3),
    (PageType(side='left', first=None, index=1, blank=None, name=None),
     10, 3, 3, 10),
    (PageType(side='right', first=None, index=1, blank=None, name=None),
     10, 10, 3, 3),
    (PageType(side='right', first=None, index=1, blank=None, name='name'),
     5, 10, 3, 15),
    (PageType(side='right', first=None, index=2, blank=None, name='name'),
     5, 10, 1, 15),
    (PageType(side='right', first=None, index=8, blank=None, name='name'),
     5, 10, 2, 15),
))
def test_page_style(page_type, top, right, bottom, left):
    document = FakeHTML(string='''
      <style>
        @page { margin: 3px }
        @page name { margin-left: 15px; margin-top: 5px }
        @page :nth(3) { margin-bottom: 1px }
        @page :nth(5n+4) { margin-bottom: 2px }
        @page :first { margin-top: 20px }
        @page :right { margin-right: 10px; margin-top: 10px }
        @page :left { margin-left: 10px; margin-top: 10px }
      </style>
    ''')
    style_for = get_all_computed_styles(document)

    # Force the generation of the style for this page type as it's generally
    # only done during the rendering.
    set_page_type_computed_styles(page_type, document, style_for)

    style = style_for(page_type)
    assert style['margin_top'] == (top, 'px')
    assert style['margin_right'] == (right, 'px')
    assert style['margin_bottom'] == (bottom, 'px')
    assert style['margin_left'] == (left, 'px')


@assert_no_logs
def test_images_1():
    with capture_logs() as logs:
        result = parse_all('''
          <p><img src=pattern.png
            /><img alt="No src"
            /><img src=inexistent.jpg alt="Inexistent src" /></p>
        ''')
    assert len(logs) == 1
    assert 'ERROR: Failed to load image' in logs[0]
    assert 'inexistent.jpg' in logs[0]
    assert_tree(result, [
        ('p', 'Block', [
            ('p', 'Line', [
                ('img', 'InlineReplaced', '<replaced>'),
                ('img', 'Inline', [
                    ('img', 'Text', 'No src')]),
                ('img', 'Inline', [
                    ('img', 'Text', 'Inexistent src')])])])])


@assert_no_logs
def test_images_2():
    with capture_logs() as logs:
        result = parse_all('<p><img src=pattern.png alt="No base_url">',
                           base_url=None)
    assert len(logs) == 1
    assert 'ERROR: Relative URI reference without a base URI' in logs[0]
    assert_tree(result, [
        ('p', 'Block', [
            ('p', 'Line', [
                ('img', 'Inline', [
                    ('img', 'Text', 'No base_url')])])])])


@assert_no_logs
def test_tables_1():
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
        ('x-table', 'Block', [
            ('x-caption', 'TableCaption', [
                ('x-caption', 'Line', [
                    ('x-caption', 'Text', 'top caption')])]),
            ('x-table', 'Table', [
                ('x-table', 'TableColumnGroup', [
                    ('x-col', 'TableColumn', [])]),
                ('x-thead', 'TableRowGroup', [
                    ('x-thead', 'TableRow', [
                        ('x-th', 'TableCell', [])])]),
                ('x-table', 'TableRowGroup', [
                    ('x-tr', 'TableRow', [
                        ('x-th', 'TableCell', [
                            ('x-th', 'Line', [
                                ('x-th', 'Text', 'foo')])]),
                        ('x-th', 'TableCell', [
                            ('x-th', 'Line', [
                                ('x-th', 'Text', 'bar')])])])]),
                ('x-thead', 'TableRowGroup', []),
                ('x-table', 'TableRowGroup', [
                    ('x-tr', 'TableRow', [
                        ('x-td', 'TableCell', [
                            ('x-td', 'Line', [
                                ('x-td', 'Text', 'baz')])])])]),
                ('x-tfoot', 'TableRowGroup', [])]),
            ('x-caption', 'TableCaption', [])])])


@assert_no_logs
def test_tables_2():
    # Rules 1.4 and 3.1
    assert_tree(parse_all('''
      <span style="display: table-cell">foo</span>
      <span style="display: table-cell">bar</span>
    '''), [
        ('body', 'Block', [
            ('body', 'Table', [
                ('body', 'TableRowGroup', [
                    ('body', 'TableRow', [
                        ('span', 'TableCell', [
                            ('span', 'Line', [
                                ('span', 'Text', 'foo')])]),
                        ('span', 'TableCell', [
                            ('span', 'Line', [
                                ('span', 'Text', 'bar')])])])])])])])


@assert_no_logs
def test_tables_3():
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
        ('body', 'Block', [
            ('body', 'Table', [
                ('span', 'TableColumnGroup', [
                    ('em', 'TableColumn', [])]),
                ('ins', 'TableColumnGroup', [
                    ('ins', 'TableColumn', [])])])])])


@assert_no_logs
def test_tables_4():
    # Rules 2.1 then 2.3
    assert_tree(parse_all('<x-table>foo <div></div></x-table>'), [
        ('x-table', 'Block', [
            ('x-table', 'Table', [
                ('x-table', 'TableRowGroup', [
                    ('x-table', 'TableRow', [
                        ('x-table', 'TableCell', [
                            ('x-table', 'Block', [
                                ('x-table', 'Line', [
                                    ('x-table', 'Text', 'foo ')])]),
                            ('div', 'Block', [])])])])])])])


@assert_no_logs
def test_tables_5():
    # Rule 2.2
    assert_tree(parse_all('<x-thead style="display: table-header-group">'
                          '<div></div><x-td></x-td></x-thead>'), [
        ('body', 'Block', [
            ('body', 'Table', [
                ('x-thead', 'TableRowGroup', [
                    ('x-thead', 'TableRow', [
                        ('x-thead', 'TableCell', [
                            ('div', 'Block', [])]),
                        ('x-td', 'TableCell', [])])])])])])


@assert_no_logs
def test_tables_6():
    # Rule 3.2
    assert_tree(parse_all('<span><x-tr></x-tr></span>'), [
        ('body', 'Line', [
            ('span', 'Inline', [
                ('span', 'InlineBlock', [
                    ('span', 'InlineTable', [
                        ('span', 'TableRowGroup', [
                            ('x-tr', 'TableRow', [])])])])])])])


@assert_no_logs
def test_tables_7():
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
                ('span', 'InlineBlock', [
                    ('span', 'InlineTable', [
                        ('span', 'TableRowGroup', [
                            ('span', 'TableRow', [
                                ('em', 'TableCell', []),
                                ('em', 'TableCell', [])])])])]),
                ('span', 'Text', ' ')])])])


@assert_no_logs
def test_tables_8():
    # Rule 3.2
    assert_tree(parse_all('<x-tr></x-tr>\t<x-tr></x-tr>'), [
        ('body', 'Block', [
            ('body', 'Table', [
                ('body', 'TableRowGroup', [
                    ('x-tr', 'TableRow', []),
                    ('x-tr', 'TableRow', [])])])])])


@assert_no_logs
def test_tables_9():
    assert_tree(parse_all('<x-col></x-col>\n<x-colgroup></x-colgroup>'), [
        ('body', 'Block', [
            ('body', 'Table', [
                ('body', 'TableColumnGroup', [
                    ('x-col', 'TableColumn', [])]),
                ('x-colgroup', 'TableColumnGroup', [
                    ('x-colgroup', 'TableColumn', [])])])])])


@assert_no_logs
def test_table_style():
    html = parse_all('<table style="margin: 1px; padding: 2px"></table>')
    body, = html.children
    wrapper, = body.children
    table, = wrapper.children
    assert isinstance(wrapper, boxes.BlockBox)
    assert isinstance(table, boxes.TableBox)
    assert wrapper.style['margin_top'] == (1, 'px')
    assert wrapper.style['padding_top'] == (0, 'px')
    assert table.style['margin_top'] == (0, 'px')
    assert table.style['padding_top'] == (2, 'px')


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
    widths = [col.style['width'] for col in colgroup.children]
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
def test_colspan_rowspan_1():
    # +---+---+---+
    # | A | B | C | X
    # +---+---+---+
    # | D |     E | X
    # +---+---+   +---+
    # |  F ...|   |   |   <-- overlap
    # +---+---+---+   +
    # | H | X   X | G |
    # +---+---+   +   +
    # | I | J | X |   |
    # +---+---+   +---+

    # X: empty cells
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
        [0, 3],
        [0],
        [0, 1],
    ]
    assert [[c.colspan for c in row.children] for row in group.children] == [
        [1, 1, 1],
        [1, 2],
        [2, 1],
        [1],
        [1, 1],
    ]
    assert [[c.rowspan for c in row.children] for row in group.children] == [
        [1, 1, 1],
        [1, 2],
        [1, 3],
        [1],
        [1, 1],
    ]


@assert_no_logs
def test_colspan_rowspan_2():
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
def test_before_after_1():
    assert_tree(parse_all('''
      <style>
        p:before { content: normal }
        div:before { content: none }
        section::before { color: black }
      </style>
      <p></p>
      <div></div>
      <section></section>
    '''), [
        # No content in pseudo-element, no box generated
        ('p', 'Block', []),
        ('div', 'Block', []),
        ('section', 'Block', [])])


@assert_no_logs
def test_before_after_2():
    assert_tree(parse_all('''
      <style>
        p:before { content: 'a' 'b' }
        p::after { content: 'd' 'e' }
      </style>
      <p> c </p>
    '''), [
        ('p', 'Block', [
            ('p', 'Line', [
                ('p::before', 'Inline', [
                    ('p::before', 'Text', 'ab')]),
                ('p', 'Text', ' c '),
                ('p::after', 'Inline', [
                    ('p::after', 'Text', 'de')])])])])


@assert_no_logs
def test_before_after_3():
    assert_tree(parse_all('''
      <style>
        a[href]:before { content: '[' attr(href) '] ' }
      </style>
      <p><a href="some url">some text</a></p>
    '''), [
        ('p', 'Block', [
            ('p', 'Line', [
                ('a', 'Inline', [
                    ('a::before', 'Inline', [
                        ('a::before', 'Text', '[some url] ')]),
                    ('a', 'Text', 'some text')])])])])


@assert_no_logs
def test_before_after_4():
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
                    ('q::before', 'Inline', [
                        ('q::before', 'Text', '« ')]),
                    ('q', 'Text', 'Lorem ipsum '),
                    ('q', 'Inline', [
                        ('q::before', 'Inline', [
                            ('q::before', 'Text', '“ ')]),
                        ('q', 'Text', 'dolor'),
                        ('q::after', 'Inline', [
                            ('q::after', 'Text', ' ”')])]),
                    ('q', 'Text', ' sit amet'),
                    ('q::after', 'Inline', [
                        ('q::after', 'Text', ' »')])])])])])


@assert_no_logs
def test_before_after_5():
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
                    ('p::before', 'Inline', [
                        ('p::before', 'Text', 'a'),
                        ('p::before', 'InlineReplaced', '<replaced>'),
                        ('p::before', 'Text', 'b')]),
                    ('p', 'Text', 'c')])])])
    assert len(logs) == 1
    assert 'nested-function(' in logs[0]
    assert 'invalid value' in logs[0]


@assert_no_logs
def test_counters_1():
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
                ('p::before', 'Inline', [
                    ('p::before', 'Text', counter)])])])
        for counter in '0 1 3  2 4 6  -11 -9 -7  44 46 48'.split()])


@assert_no_logs
def test_counters_2():
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
                    ('li::marker', 'Inline', [
                        ('li::marker', 'Text', '1. ')])])]),
            ('li', 'Block', [
                ('li', 'Line', [
                    ('li::marker', 'Inline', [
                        ('li::marker', 'Text', '2. ')])])]),
            ('li', 'Block', [
                ('li', 'Line', [
                    ('li::marker', 'Inline', [
                        ('li::marker', 'Text', '3. ')])])]),
            ('li', 'Block', [
                ('li', 'Block', [
                    ('li', 'Line', [
                        ('li::marker', 'Inline', [
                            ('li::marker', 'Text', '4. ')])])]),
                ('ol', 'Block', [
                    ('li', 'Block', [
                        ('li', 'Line', [
                            ('li::marker', 'Inline', [
                                ('li::marker', 'Text', '1. ')])])]),
                    ('li', 'Block', [
                        ('li', 'Line', [
                            ('li::marker', 'Inline', [
                                ('li::marker', 'Text', '1. ')])])]),
                    ('li', 'Block', [
                        ('li', 'Line', [
                            ('li::marker', 'Inline', [
                                ('li::marker', 'Text', '2. ')])])])])]),
            ('li', 'Block', [
                ('li', 'Line', [
                    ('li::marker', 'Inline', [
                        ('li::marker', 'Text', '5. ')])])])])])


@assert_no_logs
def test_counters_3():
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
                    ('p::marker', 'Inline', [
                        ('p::marker', 'Text', '1. ')])])]),
            ('p', 'Block', [
                ('p', 'Line', [
                    ('p::marker', 'Inline', [
                        ('p::marker', 'Text', '2. ')])])]),
            ('p', 'Block', [
                ('p', 'Line', [
                    ('p::marker', 'Inline', [
                        ('p::marker', 'Text', '-55. ')])])])]),
        ('p', 'Block', [
            ('p', 'Line', [
                ('p::marker', 'Inline', [
                    ('p::marker', 'Text', '1. ')])])])])


@assert_no_logs
def test_counters_4():
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
            ('section', 'Block', [
                ('section', 'Line', [
                    ('section::before', 'Inline', [])])]),
            ('h1', 'Block', [
                ('h1', 'Line', [
                    ('h1::before', 'Inline', [
                        ('h1::before', 'Text', '1')])])]),
            ('h1', 'Block', [
                ('h1', 'Line', [
                    ('h1::before', 'Inline', [
                        ('h1::before', 'Text', '2')])])]),
            ('section', 'Block', [
                ('section', 'Block', [
                    ('section', 'Line', [
                        ('section::before', 'Inline', [])])]),
                ('h1', 'Block', [
                    ('h1', 'Line', [
                        ('h1::before', 'Inline', [
                            ('h1::before', 'Text', '2.1')])])]),
                ('h1', 'Block', [
                    ('h1', 'Line', [
                        ('h1::before', 'Inline', [
                            ('h1::before', 'Text', '2.2')])])])]),
            ('h1', 'Block', [
                ('h1', 'Line', [
                    ('h1::before', 'Inline', [
                        ('h1::before', 'Text', '3')])])])])])


@assert_no_logs
def test_counters_5():
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
                ('p::before', 'Inline', [
                    ('p::before', 'Text', '0')])])])])


@assert_no_logs
def test_counters_6():
    # counter-increment may interfere with display: list-item
    assert_tree(parse_all('''
      <p style="counter-increment: c;
                display: list-item; list-style: inside decimal">'''), [
        ('p', 'Block', [
            ('p', 'Line', [
                ('p::marker', 'Inline', [
                    ('p::marker', 'Text', '0. ')])])])])


@assert_no_logs
def test_counters_7():
    # Test that counters are case-sensitive
    # See https://github.com/Kozea/WeasyPrint/pull/827
    assert_tree(parse_all('''
      <style>
        p { counter-increment: p 2 }
        p:before { content: counter(p) '.' counter(P); }
      </style>
      <p></p>
      <p style="counter-increment: P 3"></p>
      <p></p>'''), [
        ('p', 'Block', [
            ('p', 'Line', [
                ('p::before', 'Inline', [
                    ('p::before', 'Text', counter)])])])
        for counter in '2.0 2.3 4.3'.split()])


@assert_no_logs
def test_counters_8():
    assert_tree(parse_all('''
      <style>
        p:before { content: 'a'; display: list-item }
      </style>
      <p></p>
      <p></p>'''), 2 * [
        ('p', 'Block', [
          ('p::before', 'Block', [
            ('p::marker', 'Block', [
              ('p::marker', 'Line', [
                ('p::marker', 'Text', '• ')])]),
            ('p::before', 'Block', [
                ('p::before', 'Line', [
                    ('p::before', 'Text', 'a')])])])])])


@assert_no_logs
def test_counter_styles_1():
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
                ('p::before', 'Inline', [
                    ('p::before', 'Text', counter)])])])
        for counter in '--  •  ◦  ▪  -7'.split()])


@assert_no_logs
def test_counter_styles_2():
    assert_tree(parse_all('''
      <style>
        p { counter-increment: p }
        p::before { content: counter(p, decimal-leading-zero); }
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
                ('p::before', 'Inline', [
                    ('p::before', 'Text', counter)])])])
        for counter in '''-1986 -1985  -11 -10 -09 -08  -01 00 01 02  09 10 11
                            99 100 101  4135 4136'''.split()])


@assert_no_logs
def test_counter_styles_3():
    # Same test as above, but short-circuit HTML and boxes
    assert [counters.format(value, 'decimal-leading-zero') for value in [
        -1986, -1985,
        -11, -10, -9, -8,
        -1, 0, 1, 2,
        9, 10, 11,
        99, 100, 101,
        4135, 4136
    ]] == '''
        -1986 -1985  -11 -10 -09 -08  -01 00 01 02  09 10 11
        99 100 101  4135 4136
    '''.split()


@assert_no_logs
def test_counter_styles_4():
    # Now that we’re confident that they do the same, use the shorter form.

    # http://test.csswg.org/suites/css2.1/20110323/html4/content-counter-007.htm
    assert [counters.format(value, 'lower-roman') for value in [
        -1986, -1985,
        -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
        49, 50,
        389, 390,
        3489, 3490, 3491,
        4999, 5000, 5001
    ]] == '''
        -1986 -1985  -1 0 i ii iii iv v vi vii viii ix x xi xii
        xlix l  ccclxxxix cccxc  mmmcdlxxxix mmmcdxc mmmcdxci
        mmmmcmxcix  5000 5001
    '''.split()


@assert_no_logs
def test_counter_styles_5():
    # http://test.csswg.org/suites/css2.1/20110323/html4/content-counter-008.htm
    assert [counters.format(value, 'upper-roman') for value in [
        -1986, -1985,
        -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
        49, 50,
        389, 390,
        3489, 3490, 3491,
        4999, 5000, 5001
    ]] == '''
        -1986 -1985  -1 0 I II III IV V VI VII VIII IX X XI XII
        XLIX L  CCCLXXXIX CCCXC  MMMCDLXXXIX MMMCDXC MMMCDXCI
        MMMMCMXCIX 5000 5001
    '''.split()


@assert_no_logs
def test_counter_styles_6():
    assert [counters.format(value, 'lower-alpha') for value in [
        -1986, -1985,
        -1, 0, 1, 2, 3, 4,
        25, 26, 27, 28, 29,
        2002, 2003
    ]] == '''
        -1986 -1985  -1 0 a b c d  y z aa ab ac bxz bya
    '''.split()


@assert_no_logs
def test_counter_styles_7():
    assert [counters.format(value, 'upper-alpha') for value in [
        -1986, -1985,
        -1, 0, 1, 2, 3, 4,
        25, 26, 27, 28, 29,
        2002, 2003
    ]] == '''
        -1986 -1985  -1 0 A B C D  Y Z AA AB AC BXZ BYA
    '''.split()


@assert_no_logs
def test_counter_styles_8():
    assert [counters.format(value, 'lower-latin') for value in [
        -1986, -1985,
        -1, 0, 1, 2, 3, 4,
        25, 26, 27, 28, 29,
        2002, 2003
    ]] == '''
        -1986 -1985  -1 0 a b c d  y z aa ab ac bxz bya
    '''.split()


@assert_no_logs
def test_counter_styles_9():
    assert [counters.format(value, 'upper-latin') for value in [
        -1986, -1985,
        -1, 0, 1, 2, 3, 4,
        25, 26, 27, 28, 29,
        2002, 2003
    ]] == '''
        -1986 -1985  -1 0 A B C D  Y Z AA AB AC BXZ BYA
    '''.split()


@assert_no_logs
def test_counter_styles_10():
    # http://test.csswg.org/suites/css2.1/20110323/html4/content-counter-009.htm
    assert [counters.format(value, 'georgian') for value in [
        -1986, -1985,
        -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
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


@assert_no_logs
def test_counter_styles_11():
    # http://test.csswg.org/suites/css2.1/20110323/html4/content-counter-010.htm
    assert [counters.format(value, 'armenian') for value in [
        -1986, -1985,
        -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
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
def test_margin_box_string_set_1():
    # Test that both pages get string in the `bottom-center` margin box
    page_1, page_2 = render_pages('''
      <style>
        @page {
          @bottom-center { content: string(text_header) }
        }
        p {
          string-set: text_header content();
        }
        .page {
          page-break-before: always;
        }
      </style>
      <p>first assignment</p>
      <div class="page"></div>
    ''')

    html, bottom_center = page_2.children
    line_box, = bottom_center.children
    text_box, = line_box.children
    assert text_box.text == 'first assignment'

    html, bottom_center = page_1.children
    line_box, = bottom_center.children
    text_box, = line_box.children
    assert text_box.text == 'first assignment'


@assert_no_logs
def test_margin_box_string_set_2():
    def simple_string_set_test(content_val, extra_style=""):
        page_1, = render_pages('''
          <style>
            @page {
              @top-center { content: string(text_header) }
            }
            p {
              string-set: text_header content(%(content_val)s);
            }
            %(extra_style)s
          </style>
          <p>first assignment</p>
        ''' % dict(content_val=content_val, extra_style=extra_style))

        html, top_center = page_1.children
        line_box, = top_center.children
        text_box, = line_box.children
        if content_val in ('before', 'after'):
            assert text_box.text == 'pseudo'
        else:
            assert text_box.text == 'first assignment'

    # Test each accepted value of `content()` as an arguemnt to `string-set`
    for value in ('', 'text', 'before', 'after'):
        if value in ('before', 'after'):
            extra_style = "p:%s{content: 'pseudo'}" % value
            simple_string_set_test(value, extra_style)
        else:
            simple_string_set_test(value)


@assert_no_logs
def test_margin_box_string_set_3():
    # Test `first` (default value) ie. use the first assignment on the page
    page_1, = render_pages('''
      <style>
        @page {
          @top-center { content: string(text_header, first) }
        }
        p {
          string-set: text_header content();
        }
      </style>
      <p>first assignment</p>
      <p>Second assignment</p>
    ''')

    html, top_center = page_1.children
    line_box, = top_center.children
    text_box, = line_box.children
    assert text_box.text == 'first assignment'


@assert_no_logs
def test_margin_box_string_set_4():
    # test `first-except` ie. exclude from page on which value is assigned
    page_1, page_2 = render_pages('''
      <style>
        @page {
          @top-center { content: string(header_nofirst, first-except) }
        }
        p{
          string-set: header_nofirst content();
        }
        .page{
          page-break-before: always;
        }
      </style>
      <p>first_excepted</p>
      <div class="page"></div>
    ''')
    html, top_center = page_1.children
    assert len(top_center.children) == 0

    html, top_center = page_2.children
    line_box, = top_center.children
    text_box, = line_box.children
    assert text_box.text == 'first_excepted'


@assert_no_logs
def test_margin_box_string_set_5():
    # Test `last` ie. use the most-recent assignment
    page_1, = render_pages('''
      <style>
        @page {
          @top-center { content: string(header_last, last) }
        }
        p {
          string-set: header_last content();
        }
      </style>
      <p>String set</p>
      <p>Second assignment</p>
    ''')

    html, top_center = page_1.children[:2]
    line_box, = top_center.children

    text_box, = line_box.children
    assert text_box.text == 'Second assignment'


@assert_no_logs
def test_margin_box_string_set_6():
    # Test multiple complex string-set values
    page_1, = render_pages('''
      <style>
        @page {
          @top-center { content: string(text_header, first) }
          @bottom-center { content: string(text_footer, last) }
        }
        html { counter-reset: a }
        body { counter-increment: a }
        ul { counter-reset: b }
        li {
          counter-increment: b;
          string-set:
            text_header content(before) "-" content() "-" content(after)
                        counter(a, upper-roman) '.' counters(b, '|'),
            text_footer content(before) '-' attr(class)
                        counters(b, '|') "/" counter(a, upper-roman);
        }
        li:before { content: 'before!' }
        li:after { content: 'after!' }
        li:last-child:before { content: 'before!last' }
        li:last-child:after { content: 'after!last' }
      </style>
      <ul>
        <li class="firstclass">first
        <li>
          <ul>
            <li class="secondclass">second
    ''')

    html, top_center, bottom_center = page_1.children
    top_line_box, = top_center.children
    top_text_box, = top_line_box.children
    assert top_text_box.text == 'before!-first-after!I.1'
    bottom_line_box, = bottom_center.children
    bottom_text_box, = bottom_line_box.children
    assert bottom_text_box.text == 'before!last-secondclass2|1/I'


def test_margin_box_string_set_7():
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/722
    page_1, = render_pages('''
      <style>
        img { string-set: left attr(alt) }
        img + img { string-set: right attr(alt) }
        @page { @top-left  { content: '[' string(left)  ']' }
                @top-right { content: '{' string(right) '}' } }
      </style>
      <img src=pattern.png alt="Chocolate">
      <img src=no_such_file.png alt="Cake">
    ''')

    html, top_left, top_right = page_1.children
    left_line_box, = top_left.children
    left_text_box, = left_line_box.children
    assert left_text_box.text == '[Chocolate]'
    right_line_box, = top_right.children
    right_text_box, = right_line_box.children
    assert right_text_box.text == '{Cake}'


@assert_no_logs
def test_margin_box_string_set_8():
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/726
    page_1, page_2, page_3 = render_pages('''
      <style>
        @page { @top-left  { content: '[' string(left) ']' } }
        p { page-break-before: always }
        .initial { string-set: left 'initial' }
        .empty   { string-set: left ''        }
        .space   { string-set: left ' '       }
      </style>

      <p class="initial">Initial</p>
      <p class="empty">Empty</p>
      <p class="space">Space</p>
    ''')
    html, top_left = page_1.children
    left_line_box, = top_left.children
    left_text_box, = left_line_box.children
    assert left_text_box.text == '[initial]'

    html, top_left = page_2.children
    left_line_box, = top_left.children
    left_text_box, = left_line_box.children
    assert left_text_box.text == '[]'

    html, top_left = page_3.children
    left_line_box, = top_left.children
    left_text_box, = left_line_box.children
    assert left_text_box.text == '[ ]'


@assert_no_logs
def test_margin_box_string_set_9():
    # Test that named strings are case-sensitive
    # See https://github.com/Kozea/WeasyPrint/pull/827
    page_1, = render_pages('''
      <style>
        @page {
          @top-center {
            content: string(text_header, first)
                     ' ' string(TEXT_header, first)
          }
        }
        p { string-set: text_header content() }
        div { string-set: TEXT_header content() }
      </style>
      <p>first assignment</p>
      <div>second assignment</div>
    ''')

    html, top_center = page_1.children
    line_box, = top_center.children
    text_box, = line_box.children
    assert text_box.text == 'first assignment second assignment'


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


black = (0, 0, 0, 1)
red = (1, 0, 0, 1)
green = (0, 1, 0, 1)  # lime in CSS
blue = (0, 0, 1, 1)
yellow = (1, 1, 0, 1)
black_3 = ('solid', 3, black)
red_1 = ('solid', 1, red)
yellow_5 = ('solid', 5, yellow)
green_5 = ('solid', 5, green)
dashed_blue_5 = ('dashed', 5, blue)


@assert_no_logs
def test_border_collapse_1():
    html = parse_all('<table></table>')
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    assert isinstance(table, boxes.TableBox)
    assert not hasattr(table, 'collapsed_border_grid')

    grid = _get_grid('<table style="border-collapse: collapse"></table>')
    assert grid == ([], [])


@assert_no_logs
def test_border_collapse_2():
    vertical_borders, horizontal_borders = _get_grid('''
      <style>td { border: 1px solid red }</style>
      <table style="border-collapse: collapse; border: 3px solid black">
        <tr> <td>A</td> <td>B</td> </tr>
        <tr> <td>C</td> <td>D</td> </tr>
      </table>
    ''')
    assert vertical_borders == [
        [black_3, red_1, black_3],
        [black_3, red_1, black_3],
    ]
    assert horizontal_borders == [
        [black_3, black_3],
        [red_1, red_1],
        [black_3, black_3],
    ]


@assert_no_logs
def test_border_collapse_3():
    # hidden vs. none
    vertical_borders, horizontal_borders = _get_grid('''
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


@assert_no_logs
def test_border_collapse_4():
    vertical_borders, horizontal_borders = _get_grid('''
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


@assert_no_logs
def test_border_collapse_5():
    # rowspan and colspan
    vertical_borders, horizontal_borders = _get_grid('''
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


@assert_no_logs
@pytest.mark.parametrize('html', (
    '<html style="display: none">',
    '<html style="display: none">abc',
    '<html style="display: none"><p>abc',
    '<body style="display: none"><p>abc',
))
def test_display_none_root(html):
    box = parse_all(html)
    assert box.style['display'] == 'block'
    assert not box.children
