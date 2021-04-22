"""
    weasyprint.tests.stacking
    -------------------------

    Test CSS stacking contexts.

"""

import pytest
from weasyprint.stacking import StackingContext

from .draw import assert_pixels
from .testing_utils import assert_no_logs, render_pages, serialize

z_index_source = '''
  <style>
    @page { size: 10px }
    body { background: white }
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


@assert_no_logs
@pytest.mark.parametrize('z_indexes, color', (
    ((3, 2, 1), 'R'),
    ((1, 2, 3), 'G'),
    ((1, 2, -3), 'B'),
    ((1, 2, 'auto'), 'B'),
    ((-1, 'auto', -2), 'B'),
))
def test_z_index(z_indexes, color):
    assert_pixels(
        'z_index_%s_%s_%s' % z_indexes, 10, 10, '\n'.join([color * 10] * 10),
        z_index_source % z_indexes)
