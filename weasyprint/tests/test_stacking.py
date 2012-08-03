# coding: utf8
"""
    weasyprint.tests.stacking
    -------------------------

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
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


def serialize_box(box):
    return '%s %s' % (box.element_tag, box.sourceline)


def serialize_stacking(context):
    return (
        serialize_box(context.box),
        [serialize_box(b) for b in context.blocks_and_cells],
        [serialize_stacking(c) for c in context.zero_z_contexts],
    )


@assert_no_logs
def test_nested():
    page, = parse('''\
        <p id=lorem></p>
        <div style="position: relative">
            <p id=lipsum></p>
        </p>
    ''')
    assert to_lists(page) == (
        'html 1',
        ['body 1', 'p 1'],
        [(
            'div 2',
            ['p 3'],
            [])])

    page, = parse('''\
        <div style="position: relative">
            <p style="position: relative"></p>
        </div>
    ''')
    assert to_lists(page) == (
        'html 1',
        ['body 1'],
        [('div 1', [], []),  # In this order
         ('p 2', [], [])])


@assert_no_logs
def test_image_contexts():
    page, = parse('''\
        <body>Some text: <img style="position: relative" src=pattern.png>
    ''')
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
