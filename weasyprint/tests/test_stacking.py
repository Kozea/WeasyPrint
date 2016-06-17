# coding: utf-8
"""
    weasyprint.tests.stacking
    -------------------------

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from ..stacking import StackingContext
from .test_boxes import serialize
from .test_layout import parse
from .testing_utils import assert_no_logs


def to_lists(page):
    html, = page.children
    return serialize_stacking(StackingContext.from_box(html, page))


def serialize_stacking(context):
    return (
        context.box.element_tag,
        [b.element_tag for b in context.blocks_and_cells],
        [serialize_stacking(c) for c in context.zero_z_contexts],
    )


@assert_no_logs
def test_nested():
    page, = parse('''\
        <p id=lorem></p>
        <div style="position: relative">
            <p id=lipsum></p>
        </div>
    ''')
    assert to_lists(page) == (
        'html',
        ['body', 'p'],
        [(
            'div',
            ['p'],
            [])])

    page, = parse('''\
        <div style="position: relative">
            <p style="position: relative"></p>
        </div>
    ''')
    assert to_lists(page) == (
        'html',
        ['body'],
        [('div', [], []),  # In this order
         ('p', [], [])])


@assert_no_logs
def test_image_contexts():
    page, = parse('''
        <body>Some text: <img style="position: relative" src=pattern.png>''')
    html, = page.children
    context = StackingContext.from_box(html, page)
    # The image is *not* in this context:
    assert serialize([context.box]) == [
        ('html', 'Block', [
            ('body', 'Block', [
                ('body', 'Line', [
                    ('body', 'Text', 'Some text: ')])])])]
    # ... but in a sub-context:
    assert serialize(c.box for c in context.zero_z_contexts) == [
        ('img', 'InlineReplaced', '<replaced>')]
