"""
    weasyprint.tests.test_presentational_hints
    ------------------------------------------

    Test the HTML presentational hints.

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from .. import CSS, HTML
from .testing_utils import BASE_URL, assert_no_logs

PH_TESTING_CSS = CSS(string='''
@page {margin: 0; size: 1000px 1000px}
body {margin: 0}
''')


@assert_no_logs
def test_no_ph():
    # Test both CSS and non-CSS rules
    document = HTML(string='''
      <hr size=100 />
      <table align=right width=100><td>0</td></table>
    ''').render(stylesheets=[PH_TESTING_CSS])
    page, = document.pages
    html, = page._page_box.children
    body, = html.children
    hr, table = body.children
    assert hr.border_height() != 100
    assert table.position_x == 0


@assert_no_logs
def test_ph_page():
    document = HTML(string='''
      <body marginheight=2 topmargin=3 leftmargin=5
            bgcolor=red text=blue />
    ''').render(stylesheets=[PH_TESTING_CSS], presentational_hints=True)
    page, = document.pages
    html, = page._page_box.children
    body, = html.children
    assert body.margin_top == 2
    assert body.margin_bottom == 2
    assert body.margin_left == 5
    assert body.margin_right == 0
    assert body.style['background_color'] == (1, 0, 0, 1)
    assert body.style['color'] == (0, 0, 1, 1)


@assert_no_logs
def test_ph_flow():
    document = HTML(string='''
      <pre wrap></pre>
      <center></center>
      <div align=center></div>
      <div align=middle></div>
      <div align=left></div>
      <div align=right></div>
      <div align=justify></div>
    ''').render(stylesheets=[PH_TESTING_CSS], presentational_hints=True)
    page, = document.pages
    html, = page._page_box.children
    body, = html.children
    pre, center, div1, div2, div3, div4, div5 = body.children
    assert pre.style['white_space'] == 'pre-wrap'
    assert center.style['text_align'] == 'center'
    assert div1.style['text_align'] == 'center'
    assert div2.style['text_align'] == 'center'
    assert div3.style['text_align'] == 'left'
    assert div4.style['text_align'] == 'right'
    assert div5.style['text_align'] == 'justify'


@assert_no_logs
def test_ph_phrasing():
    document = HTML(string='''
      <style>@font-face { src: url(AHEM____.TTF); font-family: ahem }</style>
      <br clear=left>
      <br clear=right />
      <br clear=both />
      <br clear=all />
      <font color=red face=ahem size=7></font>
      <Font size=4></Font>
      <font size=+5 ></font>
      <font size=-5 ></font>
    ''', base_url=BASE_URL).render(
        stylesheets=[PH_TESTING_CSS], presentational_hints=True)
    page, = document.pages
    html, = page._page_box.children
    body, = html.children
    line1, line2, line3, line4, line5 = body.children
    br1, = line1.children
    br2, = line2.children
    br3, = line3.children
    br4, = line4.children
    font1, font2, font3, font4 = line5.children
    assert br1.style['clear'] == 'left'
    assert br2.style['clear'] == 'right'
    assert br3.style['clear'] == 'both'
    assert br4.style['clear'] == 'both'
    assert font1.style['color'] == (1, 0, 0, 1)
    assert font1.style['font_family'] == ('ahem',)
    assert font1.style['font_size'] == 1.5 * 2 * 16
    assert font2.style['font_size'] == 6 / 5 * 16
    assert font3.style['font_size'] == 1.5 * 2 * 16
    assert font4.style['font_size'] == 8 / 9 * 16


@assert_no_logs
def test_ph_lists():
    document = HTML(string='''
      <ol>
        <li type=A></li>
        <li type=1></li>
        <li type=a></li>
        <li type=i></li>
        <li type=I></li>
      </ol>
      <ul>
        <li type=circle></li>
        <li type=disc></li>
        <li type=square></li>
      </ul>
    ''').render(stylesheets=[PH_TESTING_CSS], presentational_hints=True)
    page, = document.pages
    html, = page._page_box.children
    body, = html.children
    ol, ul = body.children
    oli1, oli2, oli3, oli4, oli5 = ol.children
    uli1, uli2, uli3 = ul.children
    assert oli1.style['list_style_type'] == 'upper-alpha'
    assert oli2.style['list_style_type'] == 'decimal'
    assert oli3.style['list_style_type'] == 'lower-alpha'
    assert oli4.style['list_style_type'] == 'lower-roman'
    assert oli5.style['list_style_type'] == 'upper-roman'
    assert uli1.style['list_style_type'] == 'circle'
    assert uli2.style['list_style_type'] == 'disc'
    assert uli3.style['list_style_type'] == 'square'


@assert_no_logs
def test_ph_lists_types():
    document = HTML(string='''
      <ol type=A></ol>
      <ol type=1></ol>
      <ol type=a></ol>
      <ol type=i></ol>
      <ol type=I></ol>
      <ul type=circle></ul>
      <ul type=disc></ul>
      <ul type=square></ul>
    ''').render(stylesheets=[PH_TESTING_CSS], presentational_hints=True)
    page, = document.pages
    html, = page._page_box.children
    body, = html.children
    ol1, ol2, ol3, ol4, ol5, ul1, ul2, ul3 = body.children
    assert ol1.style['list_style_type'] == 'upper-alpha'
    assert ol2.style['list_style_type'] == 'decimal'
    assert ol3.style['list_style_type'] == 'lower-alpha'
    assert ol4.style['list_style_type'] == 'lower-roman'
    assert ol5.style['list_style_type'] == 'upper-roman'
    assert ul1.style['list_style_type'] == 'circle'
    assert ul2.style['list_style_type'] == 'disc'
    assert ul3.style['list_style_type'] == 'square'


@assert_no_logs
def test_ph_tables():
    document = HTML(string='''
      <table align=left rules=none></table>
      <table align=right rules=groups></table>
      <table align=center rules=rows></table>
      <table border=10 cellspacing=3 bordercolor=green>
        <thead>
          <tr>
            <th valign=top></th>
          </tr>
        </thead>
        <tr>
          <td nowrap><h1 align=right></h1><p align=center></p></td>
        </tr>
        <tr>
        </tr>
        <tfoot align=justify>
          <tr>
            <td></td>
          </tr>
        </tfoot>
      </table>
    ''').render(stylesheets=[PH_TESTING_CSS], presentational_hints=True)
    page, = document.pages
    html, = page._page_box.children
    body, = html.children
    wrapper1, wrapper2, wrapper3, wrapper4, = body.children
    assert wrapper1.style['float'] == 'left'
    assert wrapper2.style['float'] == 'right'
    assert wrapper3.style['margin_left'] == 'auto'
    assert wrapper3.style['margin_right'] == 'auto'
    assert wrapper1.children[0].style['border_left_style'] == 'hidden'
    assert wrapper1.style['border_collapse'] == 'collapse'
    assert wrapper2.children[0].style['border_left_style'] == 'hidden'
    assert wrapper2.style['border_collapse'] == 'collapse'
    assert wrapper3.children[0].style['border_left_style'] == 'hidden'
    assert wrapper3.style['border_collapse'] == 'collapse'

    table4, = wrapper4.children
    assert table4.style['border_top_style'] == 'outset'
    assert table4.style['border_top_width'] == 10
    assert table4.style['border_spacing'] == (3, 3)
    r, g, b, a = table4.style['border_left_color']
    assert g > r and g > b
    head_group, rows_group, foot_group = table4.children
    head, = head_group.children
    th, = head.children
    assert th.style['vertical_align'] == 'top'
    line1, line2 = rows_group.children
    td, = line1.children
    assert td.style['white_space'] == 'nowrap'
    assert td.style['border_top_width'] == 1
    assert td.style['border_top_style'] == 'inset'
    h1, p = td.children
    assert h1.style['text_align'] == 'right'
    assert p.style['text_align'] == 'center'
    foot, = foot_group.children
    tr, = foot.children
    assert tr.style['text_align'] == 'justify'


@assert_no_logs
def test_ph_hr():
    document = HTML(string='''
      <hr align=left>
      <hr align=right />
      <hr align=both color=red />
      <hr align=center noshade size=10 />
      <hr align=all size=8 width=100 />
    ''').render(stylesheets=[PH_TESTING_CSS], presentational_hints=True)
    page, = document.pages
    html, = page._page_box.children
    body, = html.children
    hr1, hr2, hr3, hr4, hr5 = body.children
    assert hr1.margin_left == 0
    assert hr1.style['margin_right'] == 'auto'
    assert hr2.style['margin_left'] == 'auto'
    assert hr2.margin_right == 0
    assert hr3.style['margin_left'] == 'auto'
    assert hr3.style['margin_right'] == 'auto'
    assert hr3.style['color'] == (1, 0, 0, 1)
    assert hr4.style['margin_left'] == 'auto'
    assert hr4.style['margin_right'] == 'auto'
    assert hr4.border_height() == 10
    assert hr4.style['border_top_width'] == 5
    assert hr5.border_height() == 8
    assert hr5.height == 6
    assert hr5.width == 100
    assert hr5.style['border_top_width'] == 1


@assert_no_logs
def test_ph_embedded():
    document = HTML(string='''
      <object data="data:image/svg+xml,<svg></svg>"
              align=top hspace=10 vspace=20></object>
      <img src="data:image/svg+xml,<svg></svg>" alt=text
              align=right width=10 height=20 />
      <embed src="data:image/svg+xml,<svg></svg>" align=texttop />
    ''').render(stylesheets=[PH_TESTING_CSS], presentational_hints=True)
    page, = document.pages
    html, = page._page_box.children
    body, = html.children
    line, = body.children
    object_, text1, img, embed, text2 = line.children
    assert embed.style['vertical_align'] == 'text-top'
    assert object_.style['vertical_align'] == 'top'
    assert object_.margin_top == 20
    assert object_.margin_left == 10
    assert img.style['float'] == 'right'
    assert img.width == 10
    assert img.height == 20
