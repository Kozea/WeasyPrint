"""Test CSS stacking contexts."""

import pytest

from weasyprint.stacking import StackingContext

from .testing_utils import assert_no_logs, render_pages, serialize

z_index_source = '''
  <style>
    @page { size: 10px }
    div, div * { width: 10px; height: 10px; position: absolute }
    article { background: red; z-index: %s }
    section { background: blue; z-index: %s }
    nav { background: lime; z-index: %s }
  </style>
  <div>
    <article></article>
    <section></section>
    <nav></nav>
  </div>'''


def flatten_blocks_and_cells(blocks_and_cells):
    for block, blocks_and_cells in blocks_and_cells.items():
        yield block.element_tag
        yield from flatten_blocks_and_cells(blocks_and_cells)


def serialize_stacking(context):
    return (
        context.box.element_tag,
        list(flatten_blocks_and_cells(context.blocks_and_cells)),
        [serialize_stacking(context) for context in context.zero_z_contexts])


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


@assert_no_logs
@pytest.mark.parametrize('z_indexes, color', (
    ((3, 2, 1), 'R'),
    ((1, 2, 3), 'G'),
    ((1, 2, -3), 'B'),
    ((1, 2, 'auto'), 'B'),
    ((-1, 'auto', -2), 'B'),
))
def test_z_index(assert_pixels, z_indexes, color):
    assert_pixels('\n'.join([color * 10] * 10), z_index_source % z_indexes)
