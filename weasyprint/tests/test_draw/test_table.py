"""
    weasyprint.tests.test_draw.test_tables
    --------------------------------------

    Test how tables are drawn.

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from ...html import HTML_HANDLERS
from ..testing_utils import assert_no_logs, requires
from . import as_pixel, assert_pixels, parse_pixels

PIX_BY_CHAR_OVERRIDES = {
    # rgba(255, 0, 0, 0.5) above #fff
    'r': as_pixel(b'\xff\x7f\x7f\xff'),
    # rgba(0, 255, 0, 0.5) above #fff
    'g': as_pixel(b'\x7f\xff\x7f\xff'),
    # r above B above #fff.
    'b': as_pixel(b'\x80\x00\x7f\xff'),
}


def to_pix(pixels_str):
    return parse_pixels(pixels_str, PIX_BY_CHAR_OVERRIDES)


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
    assert_pixels('table_borders', 28, 28, to_pix('''
        ____________________________
        _BBBBBBBBBBBBBBBBBBBBBBBBBB_
        _B________________________B_
        _B________________________B_
        _B__rrrrrr_rrrrrr_rrrrrr__B_
        _B__r____r_r____r_r____r__B_
        _B__r____r_r____r_r____r__B_
        _B__r____r_r____r_r____r__B_
        _B__r____r_r____r_r____r__B_
        _B__rrrrrr_r____r_rrrrrr__B_
        _B_________r____r_________B_
        _B__rrrrrrrSrrrrS_rrrrrr__B_
        _B__r______r____S_r____r__B_
        _B__r______r____S_r____r__B_
        _B__r______r____S_r____r__B_
        _B__r______r____S_r____r__B_
        _B__rrrrrrrSSSSSS_rrrrrr__B_
        _B________________________B_
        _B__rrrrrr_rrrrrr_________B_
        _B__r____r_r____r_________B_
        _B__r____r_r____r_________B_
        _B__r____r_r____r_________B_
        _B__r____r_r____r_________B_
        _B__rrrrrr_rrrrrr_________B_
        _B________________________B_
        _B________________________B_
        _BBBBBBBBBBBBBBBBBBBBBBBBBB_
        ____________________________
    '''), tables_source % {'extra_css': '''
      x-table { border-color: #00f; table-layout: fixed }
      x-td { border-color: rgba(255, 0, 0, 0.5) }
    '''})


@assert_no_logs
@requires('cairo', (1, 12, 0))
def test_tables_2():
    assert_pixels('table_collapsed_borders', 28, 28, to_pix('''
        ____________________________
        _BBBBBBBBBBBBBBBBBB_________
        _BBBBBBBBBBBBBBBBBB_________
        _BB____r____r____BB_________
        _BB____r____r____BB_________
        _BB____r____r____BB_________
        _BB____r____r____BB_________
        _BBrrrrr____rrrrrBB_________
        _BB_________r____BB_________
        _BB_________r____BB_________
        _BB_________r____BB_________
        _BB_________r____BB_________
        _BBrrrrrrrrrrrrrrBB_________
        _BB____r____r____BB_________
        _BB____r____r____BB_________
        _BB____r____r____BB_________
        _BB____r____r____BB_________
        _BBBBBBBBBBBBBBBBBB_________
        _BBBBBBBBBBBBBBBBBB_________
        ____________________________
        ____________________________
        ____________________________
        ____________________________
        ____________________________
        ____________________________
        ____________________________
        ____________________________
        ____________________________
    '''), tables_source % {'extra_css': '''
      x-table { border: 2px solid #00f; table-layout: fixed;
                border-collapse: collapse }
      x-td { border-color: #ff7f7f }
    '''})


@assert_no_logs
@requires('cairo', (1, 12, 0))
def test_tables_3():
    assert_pixels('table_collapsed_borders_paged', 28, 52, to_pix('''
        ____________________________
        _gggggggggggggggggggggggggg_
        _g________________________g_
        _g_BBBBBBBBBBBBBBBBBB_____g_
        _g_BBBBBBBBBBBBBBBBBB_____g_
        _g_BBBBBBBBBBBBBBBBBB_____g_
        _g_BBBBBBBBBBBBBBBBBB_____g_
        _g_BBBBBBBBBBBBBBBBBB_____g_
        _g_BBBBBBBBBBBBBBBBBB_____g_
        _g_BBBBBBBBBBBBBBBBBB_____g_
        _g_BBBBBBBBBBBBBBBBBB_____g_
        _g_BB____r____r____BB_____g_
        _g_BB____r____r____BB_____g_
        _g_BB____r____r____BB_____g_
        _g_BB____r____r____BB_____g_
        _g_BBrrrrr____rrrrrBB_____g_
        _g_BB_________r____BB_____g_
        _g_BB_________r____BB_____g_
        _g_BB_________r____BB_____g_
        _g_BB_________r____BB_____g_
        _g_BBrrrrrrrrrrrrrrBB_____g_
        _g________________________g_
        _g________________________g_
        _g________________________g_
        _gggggggggggggggggggggggggg_
        ____________________________
        ____________________________
        _gggggggggggggggggggggggggg_
        _g_BBrrrrrrrrrrrrrrBB_____g_
        _g_BB____r____r____BB_____g_
        _g_BB____r____r____BB_____g_
        _g_BB____r____r____BB_____g_
        _g_BB____r____r____BB_____g_
        _g_BBBBBBBBBBBBBBBBBB_____g_
        _g_BBBBBBBBBBBBBBBBBB_____g_
        _g_BBBBBBBBBBBBBBBBBB_____g_
        _g_BBBBBBBBBBBBBBBBBB_____g_
        _g_BBBBBBBBBBBBBBBBBB_____g_
        _g_BBBBBBBBBBBBBBBBBB_____g_
        _g_BBBBBBBBBBBBBBBBBB_____g_
        _g_BBBBBBBBBBBBBBBBBB_____g_
        _g________________________g_
        _g________________________g_
        _g________________________g_
        _g________________________g_
        _g________________________g_
        _g________________________g_
        _g________________________g_
        _g________________________g_
        _g________________________g_
        _gggggggggggggggggggggggggg_
        ____________________________
    '''), tables_source % {'extra_css': '''
      x-table { border: solid #00f; border-width: 8px 2px;
                table-layout: fixed; border-collapse: collapse }
      x-td { border-color: #ff7f7f }
      @page { size: 28px 26px; margin: 1px;
              border: 1px solid rgba(0, 255, 0, 0.5); }
    '''})


@assert_no_logs
@requires('cairo', (1, 12, 0))
def test_tables_4():
    assert_pixels('table_td_backgrounds', 28, 28, to_pix('''
        ____________________________
        _BBBBBBBBBBBBBBBBBBBBBBBBBB_
        _B________________________B_
        _B________________________B_
        _B__rrrrrr_rrrrrr_rrrrrr__B_
        _B__rrrrrr_rrrrrr_rrrrrr__B_
        _B__rrrrrr_rrrrrr_rrrrrr__B_
        _B__rrrrrr_rrrrrr_rrrrrr__B_
        _B__rrrrrr_rrrrrr_rrrrrr__B_
        _B__rrrrrr_rrrrrr_rrrrrr__B_
        _B_________rrrrrr_________B_
        _B__rrrrrrrSSSSSS_rrrrrr__B_
        _B__rrrrrrrSSSSSS_rrrrrr__B_
        _B__rrrrrrrSSSSSS_rrrrrr__B_
        _B__rrrrrrrSSSSSS_rrrrrr__B_
        _B__rrrrrrrSSSSSS_rrrrrr__B_
        _B__rrrrrrrSSSSSS_rrrrrr__B_
        _B________________________B_
        _B__rrrrrr_rrrrrr_________B_
        _B__rrrrrr_rrrrrr_________B_
        _B__rrrrrr_rrrrrr_________B_
        _B__rrrrrr_rrrrrr_________B_
        _B__rrrrrr_rrrrrr_________B_
        _B__rrrrrr_rrrrrr_________B_
        _B________________________B_
        _B________________________B_
        _BBBBBBBBBBBBBBBBBBBBBBBBBB_
        ____________________________
    '''), tables_source % {'extra_css': '''
      x-table { border-color: #00f; table-layout: fixed }
      x-td { background: rgba(255, 0, 0, 0.5) }
    '''})


@assert_no_logs
@requires('cairo', (1, 12, 0))
def test_tables_5():
    assert_pixels('table_row_backgrounds', 28, 28, to_pix('''
        ____________________________
        _BBBBBBBBBBBBBBBBBBBBBBBBBB_
        _B________________________B_
        _B________________________B_
        _B__bbbbbb_bbbbbb_bbbbbb__B_
        _B__bbbbbb_bbbbbb_bbbbbb__B_
        _B__bbbbbb_bbbbbb_bbbbbb__B_
        _B__bbbbbb_bbbbbb_bbbbbb__B_
        _B__bbbbbb_bbbbbb_bbbbbb__B_
        _B__bbbbbb_bbbbbb_bbbbbb__B_
        _B_________bbbbbb_________B_
        _B__bbbbbbbpppppp_bbbbbb__B_
        _B__bbbbbbbpppppp_bbbbbb__B_
        _B__bbbbbbbpppppp_bbbbbb__B_
        _B__bbbbbbbpppppp_bbbbbb__B_
        _B__bbbbbbbpppppp_bbbbbb__B_
        _B__bbbbbbbpppppp_bbbbbb__B_
        _B________________________B_
        _B__rrrrrr_rrrrrr_________B_
        _B__rrrrrr_rrrrrr_________B_
        _B__rrrrrr_rrrrrr_________B_
        _B__rrrrrr_rrrrrr_________B_
        _B__rrrrrr_rrrrrr_________B_
        _B__rrrrrr_rrrrrr_________B_
        _B________________________B_
        _B________________________B_
        _BBBBBBBBBBBBBBBBBBBBBBBBBB_
        ____________________________
    '''), tables_source % {'extra_css': '''
      x-table { border-color: #00f; table-layout: fixed }
      x-tbody { background: rgba(0, 0, 255, 1) }
      x-tr { background: rgba(255, 0, 0, 0.5) }
    '''})


@assert_no_logs
@requires('cairo', (1, 12, 0))
def test_tables_6():
    assert_pixels('table_column_backgrounds', 28, 28, to_pix('''
        ____________________________
        _BBBBBBBBBBBBBBBBBBBBBBBBBB_
        _B________________________B_
        _B________________________B_
        _B__bbbbbb_bbbbbb_rrrrrr__B_
        _B__bbbbbb_bbbbbb_rrrrrr__B_
        _B__bbbbbb_bbbbbb_rrrrrr__B_
        _B__bbbbbb_bbbbbb_rrrrrr__B_
        _B__bbbbbb_bbbbbb_rrrrrr__B_
        _B__bbbbbb_bbbbbb_rrrrrr__B_
        _B_________bbbbbb_________B_
        _B__bbbbbbbpppppp_rrrrrr__B_
        _B__bbbbbbbpppppp_rrrrrr__B_
        _B__bbbbbbbpppppp_rrrrrr__B_
        _B__bbbbbbbpppppp_rrrrrr__B_
        _B__bbbbbbbpppppp_rrrrrr__B_
        _B__bbbbbbbpppppp_rrrrrr__B_
        _B________________________B_
        _B__bbbbbb_bbbbbb_________B_
        _B__bbbbbb_bbbbbb_________B_
        _B__bbbbbb_bbbbbb_________B_
        _B__bbbbbb_bbbbbb_________B_
        _B__bbbbbb_bbbbbb_________B_
        _B__bbbbbb_bbbbbb_________B_
        _B________________________B_
        _B________________________B_
        _BBBBBBBBBBBBBBBBBBBBBBBBBB_
        ____________________________
    '''), tables_source % {'extra_css': '''
      x-table { border-color: #00f; table-layout: fixed }
      x-colgroup { background: rgba(0, 0, 255, 1) }
      x-col { background: rgba(255, 0, 0, 0.5) }
    '''})


@assert_no_logs
@requires('cairo', (1, 12, 0))
def test_tables_7():
    assert_pixels('table_borders_and_row_backgrounds', 28, 28, to_pix('''
        ____________________________
        _BBBBBBBBBBBBBBBBBBBBBBBBBB_
        _B________________________B_
        _B________________________B_
        _B__bbbbbb_bbbbbb_bbbbbb__B_
        _B__bBBBBb_bBBBBb_bBBBBb__B_
        _B__bBBBBb_bBBBBb_bBBBBb__B_
        _B__bBBBBb_bBBBBb_bBBBBb__B_
        _B__bBBBBb_bBBBBb_bBBBBb__B_
        _B__bbbbbb_bBBBBb_bbbbbb__B_
        _B_________bBBBBb_________B_
        _B__rrrrrrrpbbbbp_rrrrrr__B_
        _B__r______bBBBBp_r____r__B_
        _B__r______bBBBBp_r____r__B_
        _B__r______bBBBBp_r____r__B_
        _B__r______bBBBBp_r____r__B_
        _B__rrrrrrrpppppp_rrrrrr__B_
        _B________________________B_
        _B__rrrrrr_rrrrrr_________B_
        _B__r____r_r____r_________B_
        _B__r____r_r____r_________B_
        _B__r____r_r____r_________B_
        _B__r____r_r____r_________B_
        _B__rrrrrr_rrrrrr_________B_
        _B________________________B_
        _B________________________B_
        _BBBBBBBBBBBBBBBBBBBBBBBBBB_
        ____________________________
    '''), tables_source % {'extra_css': '''
      x-table { border-color: #00f; table-layout: fixed }
      x-tr:first-child { background: blue }
      x-td { border-color: rgba(255, 0, 0, 0.5) }
    '''})


@assert_no_logs
@requires('cairo', (1, 12, 0))
def test_tables_8():
    assert_pixels('table_borders_and_column_backgrounds', 28, 28, to_pix('''
        ____________________________
        _BBBBBBBBBBBBBBBBBBBBBBBBBB_
        _B________________________B_
        _B________________________B_
        _B__bbbbbb_rrrrrr_rrrrrr__B_
        _B__bBBBBb_r____r_r____r__B_
        _B__bBBBBb_r____r_r____r__B_
        _B__bBBBBb_r____r_r____r__B_
        _B__bBBBBb_r____r_r____r__B_
        _B__bbbbbb_r____r_rrrrrr__B_
        _B_________r____r_________B_
        _B__bbbbbbbpbbbbp_rrrrrr__B_
        _B__bBBBBBBbBBBBp_r____r__B_
        _B__bBBBBBBbBBBBp_r____r__B_
        _B__bBBBBBBbBBBBp_r____r__B_
        _B__bBBBBBBbBBBBp_r____r__B_
        _B__bbbbbbbpppppp_rrrrrr__B_
        _B________________________B_
        _B__bbbbbb_rrrrrr_________B_
        _B__bBBBBb_r____r_________B_
        _B__bBBBBb_r____r_________B_
        _B__bBBBBb_r____r_________B_
        _B__bBBBBb_r____r_________B_
        _B__bbbbbb_rrrrrr_________B_
        _B________________________B_
        _B________________________B_
        _BBBBBBBBBBBBBBBBBBBBBBBBBB_
        ____________________________
    '''), tables_source % {'extra_css': '''
      x-table { border-color: #00f; table-layout: fixed }
      x-col:first-child { background: blue }
      x-td { border-color: rgba(255, 0, 0, 0.5) }
    '''})


@assert_no_logs
@requires('cairo', (1, 12, 0))
def test_tables_9():
    assert_pixels('collapsed_border_thead', 22, 36, '''
        ______________________
        _BBBBBBBBBBBBBBBBBBBB_
        _BBBBBBBBBBBBBBBBBBBB_
        _BBB____R____R____BBB_
        _BBB____R____R____BBB_
        _BBB____R____R____BBB_
        _BBBBBBBBBBBBBBBBBBBB_
        _BBBBBBBBBBBBBBBBBBBB_
        __R_____R____R_____R__
        __R_____R____R_____R__
        __R_____R____R_____R__
        __RRRRRRRRRRRRRRRRRR__
        __R_____R____R_____R__
        __R_____R____R_____R__
        __R_____R____R_____R__
        __RRRRRRRRRRRRRRRRRR__
        ______________________
        ______________________
        _BBBBBBBBBBBBBBBBBBBB_
        _BBBBBBBBBBBBBBBBBBBB_
        _BBB____R____R____BBB_
        _BBB____R____R____BBB_
        _BBB____R____R____BBB_
        _BBBBBBBBBBBBBBBBBBBB_
        _BBBBBBBBBBBBBBBBBBBB_
        __R_____R____R_____R__
        __R_____R____R_____R__
        __R_____R____R_____R__
        __RRRRRRRRRRRRRRRRRR__
        ______________________
        ______________________
        ______________________
        ______________________
        ______________________
        ______________________
        ______________________
    ''', '''
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
    assert_pixels('collapsed_border_tfoot', 22, 36, '''
        ______________________
        __RRRRRRRRRRRRRRRRRR__
        __R_____R____R_____R__
        __R_____R____R_____R__
        __R_____R____R_____R__
        __RRRRRRRRRRRRRRRRRR__
        __R_____R____R_____R__
        __R_____R____R_____R__
        _BBBBBBBBBBBBBBBBBBBB_
        _BBBBBBBBBBBBBBBBBBBB_
        _BBB____R____R____BBB_
        _BBB____R____R____BBB_
        _BBB____R____R____BBB_
        _BBBBBBBBBBBBBBBBBBBB_
        _BBBBBBBBBBBBBBBBBBBB_
        ______________________
        ______________________
        ______________________
        ______________________
        __RRRRRRRRRRRRRRRRRR__
        __R_____R____R_____R__
        __R_____R____R_____R__
        __R_____R____R_____R__
        _BBBBBBBBBBBBBBBBBBBB_
        _BBBBBBBBBBBBBBBBBBBB_
        _BBB____R____R____BBB_
        _BBB____R____R____BBB_
        _BBB____R____R____BBB_
        _BBBBBBBBBBBBBBBBBBBB_
        _BBBBBBBBBBBBBBBBBBBB_
        ______________________
        ______________________
        ______________________
        ______________________
        ______________________
        ______________________
    ''', '''
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
    assert_pixels('inline_text_align', 20, 10, '''
      ____________________
      ________RRRRRRRRRRR_
      ________R____R____R_
      ________R____R____R_
      ________R____R____R_
      ________RRRRRRRRRRR_
      ____________________
      ____________________
      ____________________
      ____________________
    ''', '''
      <style>
        @page { size: 20px 10px; margin: 1px; background: #fff }
        body { text-align: right; font-size: 0 }
        table { display: inline-table; width: 11px }
        td { border: 1px red solid; width: 4px; height: 3px }
      </style>
      <table style="table-layout: fixed; border-collapse: collapse">
        <tr><td></td><td></td></tr>''')
