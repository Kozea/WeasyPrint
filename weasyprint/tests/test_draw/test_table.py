"""
    weasyprint.tests.test_draw.test_tables
    --------------------------------------

    Test how tables are drawn.

    :copyright: Copyright 2011-2018 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from . import B, R, S, _, as_pixel, assert_pixels, p
from ...html import HTML_HANDLERS
from ..testing_utils import assert_no_logs, requires

# rgba(255, 0, 0, 0.5) above #fff
r = as_pixel(b'\xff\x7f\x7f\xff')
# rgba(0, 255, 0, 0.5) above #fff
g = as_pixel(b'\x7f\xff\x7f\xff')
# r above B above #fff.
b = as_pixel(b'\x80\x00\x7f\xff')

# TODO: refactor colspan/rowspan into CSS:
# td, th { column-span: attr(colspan integer) }
HTML_HANDLERS['x-td'] = HTML_HANDLERS['td']
HTML_HANDLERS['x-th'] = HTML_HANDLERS['th']
tables_source = '''
  <style>
    @page { size: 28px; background: #fff }
    x-table { margin: 1px; padding: 1px; border-spacing: 1px;
              border: 1px solid transparent }
    x-td { width: 2px; height: 2px; padding: 1px;
           border: 1px solid transparent }
    %(extra_css)s
  </style>
  <x-table>
    <x-colgroup>
      <x-col></x-col>
      <x-col></x-col>
    </x-colgroup>
    <x-col></x-col>
    <x-tbody>
      <x-tr>
        <x-td></x-td>
        <x-td rowspan=2></x-td>
        <x-td></x-td>
      </x-tr>
      <x-tr>
        <x-td colspan=2></x-td>
        <x-td></x-td>
      </x-tr>
    </x-tbody>
    <x-tr>
      <x-td></x-td>
      <x-td></x-td>
    </x-tr>
  </x-table>
'''


@assert_no_logs
@requires('cairo', (1, 12, 0))
def test_tables_1():
    assert_pixels('table_borders', 28, 28, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+B+_,  # noqa
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+B+_,  # noqa
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+B+_,  # noqa
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+_+r+_+_+_+_+r+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+r+S+r+r+r+r+S+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+r+_+_+_+_+_+_+r+_+_+_+_+S+_+r+_+_+_+_+r+_+_+B+_,  # noqa
        _+B+_+_+r+_+_+_+_+_+_+r+_+_+_+_+S+_+r+_+_+_+_+r+_+_+B+_,  # noqa
        _+B+_+_+r+_+_+_+_+_+_+r+_+_+_+_+S+_+r+_+_+_+_+r+_+_+B+_,  # noqa
        _+B+_+_+r+_+_+_+_+_+_+r+_+_+_+_+S+_+r+_+_+_+_+r+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+r+S+S+S+S+S+S+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
    ], tables_source % {'extra_css': '''
      x-table { border-color: #00f; table-layout: fixed }
      x-td { border-color: rgba(255, 0, 0, 0.5) }
    '''})


@assert_no_logs
@requires('cairo', (1, 12, 0))
def test_tables_2():
    assert_pixels('table_collapsed_borders', 28, 28, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+_+_+_+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+_+_+_+_,  # noqa
        _+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+_+_+_+_,  # noqa
        _+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+_+_+_+_,  # noqa
        _+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+_+_+_+_,  # noqa
        _+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+_+_+_+_,  # noqa
        _+B+B+r+r+r+r+r+_+_+_+_+r+r+r+r+r+B+B+_+_+_+_+_+_+_+_+_,  # noqa
        _+B+B+_+_+_+_+_+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+_+_+_+_,  # noqa
        _+B+B+_+_+_+_+_+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+_+_+_+_,  # noqa
        _+B+B+_+_+_+_+_+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+_+_+_+_,  # noqa
        _+B+B+_+_+_+_+_+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+_+_+_+_,  # noqa
        _+B+B+r+r+r+r+r+r+r+r+r+r+r+r+r+r+B+B+_+_+_+_+_+_+_+_+_,  # noqa
        _+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+_+_+_+_,  # noqa
        _+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+_+_+_+_,  # noqa
        _+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+_+_+_+_,  # noqa
        _+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+_+_+_+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+_+_+_+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
    ], tables_source % {'extra_css': '''
      x-table { border: 2px solid #00f; table-layout: fixed;
                border-collapse: collapse }
      x-td { border-color: #ff7f7f }
    '''})


@assert_no_logs
@requires('cairo', (1, 12, 0))
def test_tables_3():
    assert_pixels('table_collapsed_borders_paged', 28, 52, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+_,  # noqa
        _+g+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+r+r+r+r+r+_+_+_+_+r+r+r+r+r+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+_+_+_+_+_+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+_+_+_+_+_+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+_+_+_+_+_+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+_+_+_+_+_+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+r+r+r+r+r+r+r+r+r+r+r+r+r+r+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+g+_,  # noqa
        _+g+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+g+_,  # noqa
        _+g+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+g+_,  # noqa
        _+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+_,  # noqa
        _+g+_+B+B+r+r+r+r+r+r+r+r+r+r+r+r+r+r+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,  # noqa
        _+g+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+g+_,  # noqa
        _+g+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+g+_,  # noqa
        _+g+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+g+_,  # noqa
        _+g+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+g+_,  # noqa
        _+g+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+g+_,  # noqa
        _+g+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+g+_,  # noqa
        _+g+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+g+_,  # noqa
        _+g+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+g+_,  # noqa
        _+g+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+g+_,  # noqa
        _+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
    ], tables_source % {'extra_css': '''
      x-table { border: solid #00f; border-width: 8px 2px;
                table-layout: fixed; border-collapse: collapse }
      x-td { border-color: #ff7f7f }
      @page { size: 28px 26px; margin: 1px;
              border: 1px solid rgba(0, 255, 0, 0.5); }
    '''})


@assert_no_logs
@requires('cairo', (1, 12, 0))
def test_tables_4():
    assert_pixels('table_td_backgrounds', 28, 28, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+r+S+S+S+S+S+S+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+r+S+S+S+S+S+S+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+r+S+S+S+S+S+S+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+r+S+S+S+S+S+S+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+r+S+S+S+S+S+S+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+r+S+S+S+S+S+S+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
    ], tables_source % {'extra_css': '''
      x-table { border-color: #00f; table-layout: fixed }
      x-td { background: rgba(255, 0, 0, 0.5) }
    '''})


@assert_no_logs
@requires('cairo', (1, 12, 0))
def test_tables_5():
    assert_pixels('table_row_backgrounds', 28, 28, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+b+b+b+b+b+b+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+b+p+p+p+p+p+p+_+b+b+b+b+b+b+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+b+p+p+p+p+p+p+_+b+b+b+b+b+b+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+b+p+p+p+p+p+p+_+b+b+b+b+b+b+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+b+p+p+p+p+p+p+_+b+b+b+b+b+b+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+b+p+p+p+p+p+p+_+b+b+b+b+b+b+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+b+p+p+p+p+p+p+_+b+b+b+b+b+b+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
    ], tables_source % {'extra_css': '''
      x-table { border-color: #00f; table-layout: fixed }
      x-tbody { background: rgba(0, 0, 255, 1) }
      x-tr { background: rgba(255, 0, 0, 0.5) }
    '''})


@assert_no_logs
@requires('cairo', (1, 12, 0))
def test_tables_6():
    assert_pixels('table_column_backgrounds', 28, 28, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+b+b+b+b+b+b+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+b+p+p+p+p+p+p+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+b+p+p+p+p+p+p+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+b+p+p+p+p+p+p+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+b+p+p+p+p+p+p+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+b+p+p+p+p+p+p+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+b+p+p+p+p+p+p+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
    ], tables_source % {'extra_css': '''
      x-table { border-color: #00f; table-layout: fixed }
      x-colgroup { background: rgba(0, 0, 255, 1) }
      x-col { background: rgba(255, 0, 0, 0.5) }
    '''})


@assert_no_logs
@requires('cairo', (1, 12, 0))
def test_tables_7():
    assert_pixels('table_borders_and_row_backgrounds', 28, 28, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+_+B+_,  # noqa
        _+B+_+_+b+B+B+B+B+b+_+b+B+B+B+B+b+_+b+B+B+B+B+b+_+_+B+_,  # noqa
        _+B+_+_+b+B+B+B+B+b+_+b+B+B+B+B+b+_+b+B+B+B+B+b+_+_+B+_,  # noqa
        _+B+_+_+b+B+B+B+B+b+_+b+B+B+B+B+b+_+b+B+B+B+B+b+_+_+B+_,  # noqa
        _+B+_+_+b+B+B+B+B+b+_+b+B+B+B+B+b+_+b+B+B+B+B+b+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+_+b+B+B+B+B+b+_+b+b+b+b+b+b+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+b+B+B+B+B+b+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+r+p+b+b+b+b+p+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+r+_+_+_+_+_+_+b+B+B+B+B+p+_+r+_+_+_+_+r+_+_+B+_,  # noqa
        _+B+_+_+r+_+_+_+_+_+_+b+B+B+B+B+p+_+r+_+_+_+_+r+_+_+B+_,  # noqa
        _+B+_+_+r+_+_+_+_+_+_+b+B+B+B+B+p+_+r+_+_+_+_+r+_+_+B+_,  # noqa
        _+B+_+_+r+_+_+_+_+_+_+b+B+B+B+B+p+_+r+_+_+_+_+r+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+r+p+p+p+p+p+p+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
    ], tables_source % {'extra_css': '''
      x-table { border-color: #00f; table-layout: fixed }
      x-tr:first-child { background: blue }
      x-td { border-color: rgba(255, 0, 0, 0.5) }
    '''})


@assert_no_logs
@requires('cairo', (1, 12, 0))
def test_tables_8():
    assert_pixels('table_borders_and_column_backgrounds', 28, 28, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+b+B+B+B+B+b+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+B+_,  # noqa
        _+B+_+_+b+B+B+B+B+b+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+B+_,  # noqa
        _+B+_+_+b+B+B+B+B+b+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+B+_,  # noqa
        _+B+_+_+b+B+B+B+B+b+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+_+r+_+_+_+_+r+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+b+p+b+b+b+b+p+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+b+B+B+B+B+B+B+b+B+B+B+B+p+_+r+_+_+_+_+r+_+_+B+_,  # noqa
        _+B+_+_+b+B+B+B+B+B+B+b+B+B+B+B+p+_+r+_+_+_+_+r+_+_+B+_,  # noqa
        _+B+_+_+b+B+B+B+B+B+B+b+B+B+B+B+p+_+r+_+_+_+_+r+_+_+B+_,  # noqa
        _+B+_+_+b+B+B+B+B+B+B+b+B+B+B+B+p+_+r+_+_+_+_+r+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+b+p+p+p+p+p+p+_+r+r+r+r+r+r+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+b+B+B+B+B+b+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+b+B+B+B+B+b+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+b+B+B+B+B+b+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+b+B+B+B+B+b+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+b+b+b+b+b+b+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
    ], tables_source % {'extra_css': '''
      x-table { border-color: #00f; table-layout: fixed }
      x-col:first-child { background: blue }
      x-td { border-color: rgba(255, 0, 0, 0.5) }
    '''})


@assert_no_logs
@requires('cairo', (1, 12, 0))
def test_tables_9():
    r = as_pixel(b'\xff\x00\x00\xff')
    assert_pixels('collapsed_border_thead', 22, 36, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,  # noqa
        _+B+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+B+_,  # noqa
        _+B+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+B+_,  # noqa
        _+B+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+B+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,  # noqa
        _+_+r+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+r+_+_,  # noqa
        _+_+r+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+r+_+_,  # noqa
        _+_+r+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+r+_+_,  # noqa
        _+_+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+_+_,  # noqa
        _+_+r+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+r+_+_,  # noqa
        _+_+r+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+r+_+_,  # noqa
        _+_+r+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+r+_+_,  # noqa
        _+_+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,  # noqa
        _+B+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+B+_,  # noqa
        _+B+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+B+_,  # noqa
        _+B+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+B+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,  # noqa
        _+_+r+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+r+_+_,  # noqa
        _+_+r+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+r+_+_,  # noqa
        _+_+r+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+r+_+_,  # noqa
        _+_+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
    ], '''
      <style>
        @page { size: 22px 18px; margin: 1px; background: #fff }
        td { border: 1px red solid; width: 4px; height: 3px; }
      </style>
      <table style="table-layout: fixed; border-collapse: collapse">
        <thead style="border: blue solid; border-width: 2px 3px;
            "><td></td><td></td><td></td></thead>
        <tr><td></td><td></td><td></td></tr>
        <tr><td></td><td></td><td></td></tr>
        <tr><td></td><td></td><td></td></tr>''')


@assert_no_logs
@requires('cairo', (1, 12, 0))
def test_tables_10():
    assert_pixels('collapsed_border_tfoot', 22, 36, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+R+R+R+R+R+R+R+R+R+R+R+R+R+R+R+R+R+R+_+_,  # noqa
        _+_+R+_+_+_+_+_+R+_+_+_+_+R+_+_+_+_+_+R+_+_,  # noqa
        _+_+R+_+_+_+_+_+R+_+_+_+_+R+_+_+_+_+_+R+_+_,  # noqa
        _+_+R+_+_+_+_+_+R+_+_+_+_+R+_+_+_+_+_+R+_+_,  # noqa
        _+_+R+R+R+R+R+R+R+R+R+R+R+R+R+R+R+R+R+R+_+_,  # noqa
        _+_+R+_+_+_+_+_+R+_+_+_+_+R+_+_+_+_+_+R+_+_,  # noqa
        _+_+R+_+_+_+_+_+R+_+_+_+_+R+_+_+_+_+_+R+_+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,  # noqa
        _+B+B+B+_+_+_+_+R+_+_+_+_+R+_+_+_+_+B+B+B+_,  # noqa
        _+B+B+B+_+_+_+_+R+_+_+_+_+R+_+_+_+_+B+B+B+_,  # noqa
        _+B+B+B+_+_+_+_+R+_+_+_+_+R+_+_+_+_+B+B+B+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+R+R+R+R+R+R+R+R+R+R+R+R+R+R+R+R+R+R+_+_,  # noqa
        _+_+R+_+_+_+_+_+R+_+_+_+_+R+_+_+_+_+_+R+_+_,  # noqa
        _+_+R+_+_+_+_+_+R+_+_+_+_+R+_+_+_+_+_+R+_+_,  # noqa
        _+_+R+_+_+_+_+_+R+_+_+_+_+R+_+_+_+_+_+R+_+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,  # noqa
        _+B+B+B+_+_+_+_+R+_+_+_+_+R+_+_+_+_+B+B+B+_,  # noqa
        _+B+B+B+_+_+_+_+R+_+_+_+_+R+_+_+_+_+B+B+B+_,  # noqa
        _+B+B+B+_+_+_+_+R+_+_+_+_+R+_+_+_+_+B+B+B+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,  # noqa
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
    ], '''
      <style>
        @page { size: 22px 18px; margin: 1px; background: #fff }
        td { border: 1px red solid; width: 4px; height: 3px; }
      </style>
      <table style="table-layout: fixed; margin-left: 1px;
                    border-collapse: collapse">
        <tr><td></td><td></td><td></td></tr>
        <tr><td></td><td></td><td></td></tr>
        <tr><td></td><td></td><td></td></tr>
        <tfoot style="border: blue solid; border-width: 2px 3px;
            "><td></td><td></td><td></td></tfoot>''')


@assert_no_logs
@requires('cairo', (1, 12, 0))
def test_tables_11():
    # Segression test for inline table with collapsed border and alignment
    # rendering borders incorrectly
    # https://github.com/Kozea/WeasyPrint/issues/82
    assert_pixels('inline_text_align', 20, 10, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+R+R+R+R+R+R+R+R+R+R+R+_,  # noqa
        _+_+_+_+_+_+_+_+R+_+_+_+_+R+_+_+_+_+R+_,  # noqa
        _+_+_+_+_+_+_+_+R+_+_+_+_+R+_+_+_+_+R+_,  # noqa
        _+_+_+_+_+_+_+_+R+_+_+_+_+R+_+_+_+_+R+_,  # noqa
        _+_+_+_+_+_+_+_+R+R+R+R+R+R+R+R+R+R+R+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,  # noqa
    ], '''
      <style>
        @page { size: 20px 10px; margin: 1px; background: #fff }
        body { text-align: right; font-size: 0 }
        table { display: inline-table; width: 11px }
        td { border: 1px red solid; width: 4px; height: 3px }
      </style>
      <table style="table-layout: fixed; border-collapse: collapse">
        <tr><td></td><td></td></tr>''')
