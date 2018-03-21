"""
    weasyprint.tests.stacking
    -------------------------

    :copyright: Copyright 2011-2018 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import pytest

from ..stacking import StackingContext
from .test_boxes import render_pages, serialize
from .testing_utils import assert_no_logs


def serialize_stacking(context):
    return (
        context.box.element_tag,
        [b.element_tag for b in context.blocks_and_cells],
        [serialize_stacking(c) for c in context.zero_z_contexts])


@assert_no_logs
@pytest.mark.parametrize('source, contexts', (
    ('''
      <p id=lorem></p>
      <div style="position: relative">
        <p id=lipsum></p>
      </div>''',
     ('html', ['body', 'p'], [('div', ['p'], [])])),
    ('''
      <div style="position: relative">
        <p style="position: relative"></p>
      </div>''',
     ('html', ['body'], [('div', [], []), ('p', [], [])])),
))
def test_nested(source, contexts):
    page, = render_pages(source)
    html, = page.children
    assert serialize_stacking(StackingContext.from_box(html, page)) == contexts


@assert_no_logs
def test_image_contexts():
    page, = render_pages('''
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
