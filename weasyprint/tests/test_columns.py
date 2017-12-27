# coding: utf-8
"""
    weasyprint.tests.columns
    ------------------------

    Tests for multicolumn layout.

    :copyright: Copyright 2011-2017 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from .test_boxes import render_pages as parse
from .testing_utils import assert_no_logs


@assert_no_logs
def test_columns():
    """Test standard cases for column-width, column-count and columns."""
    for css in (
            'columns: 4',
            'columns: 100px',
            'columns: 4 100px',
            'columns: 100px 4',
            'column-width: 100px',
            'column-count: 4'):
        page, = parse('''
            <style>
                div { %s; column-gap: 0 }
                body { margin: 0; font-family: "ahem" }
                @page { margin: 0; size: 400px 1000px }
            </style>
            <div>
                Ipsum dolor sit amet,
                consectetur adipiscing elit.
                Sed sollicitudin nibh
                et turpis molestie tristique.
            </div>
        ''' % css)

        html, = page.children
        body, = html.children
        div, = body.children
        columns = div.children
        assert len(columns) == 4
        assert [column.width for column in columns] == [100, 100, 100, 100]
        assert [column.position_x for column in columns] == [0, 100, 200, 300]
        assert [column.position_y for column in columns] == [0, 0, 0, 0]


def test_column_gap():
    """Test standard cases for column-gap."""
    for value, width in {
            'normal': 16,  # "normal" is 1em = 16px
            'unknown': 16,  # default value is normal
            '15px': 15,
            '40%': 16,  # percentages are not allowed
            '-1em': 16,  # negative values are not allowed
    }.items():
        page, = parse('''
            <style>
                div { columns: 3; column-gap: %s }
                body { margin: 0; font-family: "ahem" }
                @page { margin: 0; size: 300px 1000px }
            </style>
            <div>
                Ipsum dolor sit amet,
                consectetur adipiscing elit.
                Sed sollicitudin nibh
                et turpis molestie tristique.
            </div>
        ''' % value)

        html, = page.children
        body, = html.children
        div, = body.children
        columns = div.children
        assert len(columns) == 3
        assert [column.width for column in columns] == (
            3 * [100 - 2 * width / 3])
        assert [column.position_x for column in columns] == (
            [0, 100 + width / 3, 200 + 2 * width / 3])
        assert [column.position_y for column in columns] == [0, 0, 0]


@assert_no_logs
def test_columns_multipage():
    """Test columns split among multiple pages."""
    page1, page2 = parse('''
        <style>
            div { columns: 2; column-gap: 1px }
            body { margin: 0; font-family: "ahem";
                   font-size: 1px; line-height: 1px }
            @page { margin: 0; size: 3px 2px }
        </style>
        <div>a b c d e f g</div>
    ''')

    html, = page1.children
    body, = html.children
    div, = body.children
    columns = div.children
    assert len(columns) == 2
    assert len(columns[0].children) == 2
    assert len(columns[1].children) == 2
    columns[0].children[0].children[0].text == 'a'
    columns[0].children[1].children[0].text == 'b'
    columns[1].children[0].children[0].text == 'c'
    columns[1].children[1].children[0].text == 'd'

    html, = page2.children
    body, = html.children
    div, = body.children
    columns = div.children
    assert len(columns) == 2
    assert len(columns[0].children) == 2
    assert len(columns[1].children) == 1
    columns[0].children[0].children[0].text == 'e'
    columns[0].children[1].children[0].text == 'f'
    columns[1].children[0].children[0].text == 'g'


@assert_no_logs
def test_columns_not_enough_content():
    """Test when there are too many columns."""
    page, = parse('''
        <style>
            div { columns: 5; column-gap: 0 }
            body { margin: 0; font-family: "ahem" }
            @page { margin: 0; size: 5px; font-size: 1px }
        </style>
        <div>a b c</div>
    ''')

    html, = page.children
    body, = html.children
    div, = body.children
    assert div.width == 5
    columns = div.children
    assert len(columns) == 3
    assert [column.width for column in columns] == [1, 1, 1]
    assert [column.position_x for column in columns] == [0, 1, 2]
    assert [column.position_y for column in columns] == [0, 0, 0]


@assert_no_logs
def test_columns_empty():
    """Test when there's no content in columns."""
    page, = parse('''
        <style>
            div { columns: 3 }
            body { margin: 0; font-family: "ahem" }
            @page { margin: 0; size: 3px; font-size: 1px }
        </style>
        <div></div>
    ''')

    html, = page.children
    body, = html.children
    div, = body.children
    assert div.width == 3
    assert div.height == 0
    columns = div.children
    assert len(columns) == 0


@assert_no_logs
def test_columns_fixed_height():
    """Test columns with fixed height."""
    # TODO: we should test when the height is too small
    for prop in ('height', 'min-height'):
        page, = parse('''
            <style>
                div { columns: 4; column-gap: 0; %s: 10px }
                body { margin: 0; font-family: "ahem"; line-height: 1px }
                @page { margin: 0; size: 4px 50px; font-size: 1px }
            </style>
            <div>a b c</div>
        ''' % prop)

        html, = page.children
        body, = html.children
        div, = body.children
        assert div.width == 4
        columns = div.children
        assert len(columns) == 3
        assert [column.width for column in columns] == [1, 1, 1]
        assert [column.height for column in columns] == [10, 10, 10]
        assert [column.position_x for column in columns] == [0, 1, 2]
        assert [column.position_y for column in columns] == [0, 0, 0]


@assert_no_logs
def test_columns_relative():
    """Test columns with position: relative."""
    page, = parse('''
        <style>
            article { position: absolute; top: 3px }
            div { columns: 4; column-gap: 0; position: relative;
                  top: 1px; left: 2px }
            body { margin: 0; font-family: "ahem"; line-height: 1px }
            @page { margin: 0; size: 4px 50px; font-size: 1px }
        </style>
        <div>a b c d<article>e</article></div>
    ''')

    html, = page.children
    body, = html.children
    div, = body.children
    assert div.width == 4
    columns = div.children
    assert [column.width for column in columns] == [1, 1, 1, 1]
    assert [column.position_x for column in columns] == [2, 3, 4, 5]
    assert [column.position_y for column in columns] == [1, 1, 1, 1]
    column4 = columns[-1]
    column_line, = column4.children
    _, absolute_article = column_line.children
    absolute_line, = absolute_article.children
    span, = absolute_line.children
    assert span.position_x == 5  # Default position of the 4th column
    assert span.position_y == 4  # div's 1px + span's 3px
