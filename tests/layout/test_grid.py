"""Tests for grid layout."""

from ..testing_utils import assert_no_logs, render_pages


@assert_no_logs
def test_grid_empty():
    page, = render_pages('''
      <article style="display: grid">
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    assert article.position_x == 0
    assert article.position_y == 0
    assert article.width == html.width
    assert article.height == 0


@assert_no_logs
def test_grid_single_item():
    page, = render_pages('''
      <article style="display: grid">
        <div>a</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div, = article.children
    assert article.position_x == div.position_x == 0
    assert article.position_y == div.position_y == 0
    assert article.width == div.width == html.width


@assert_no_logs
def test_grid_rows():
    page, = render_pages('''
      <article style="display: grid">
        <div>a</div>
        <div>b</div>
        <div>c</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_a, div_b, div_c = article.children
    assert div_a.position_x == div_b.position_x == div_c.position_x == 0
    assert div_a.position_y < div_b.position_y < div_c.position_y
    assert div_a.height == div_b.height == div_c.height
    assert div_a.width == div_b.width == div_c.width == html.width == article.width


@assert_no_logs
def test_grid_template_fr():
    page, = render_pages('''
      <style>
        article {
          display: grid;
          font-family: weasyprint;
          font-size: 2px;
          grid-template-rows: auto 1fr;
          grid-template-columns: auto 1fr;
          line-height: 1;
          width: 10px;
        }
      </style>
      <article>
        <div>a</div> <div>b</div>
        <div>c</div> <div>d</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_a, div_b, div_c, div_d = article.children
    assert div_a.position_x == div_c.position_x == 0
    assert div_b.position_x == div_d.position_x == 2
    assert div_a.height == div_b.height == div_c.height == div_d.height == 2
    assert div_a.width == div_c.width == 2
    assert div_b.width == div_d.width == 8
    assert article.width == 10


@assert_no_logs
def test_grid_template_areas():
    page, = render_pages('''
      <style>
        article {
          display: grid;
          font-family: weasyprint;
          font-size: 2px;
          grid-template-areas: 'a b' 'c d';
          line-height: 1;
          width: 10px;
        }
      </style>
      <article>
        <div>a</div> <div>b</div>
        <div>c</div> <div>d</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_a, div_b, div_c, div_d = article.children
    assert div_a.position_x == div_c.position_x == 0
    assert div_b.position_x == div_d.position_x == 5
    assert div_a.position_y == div_b.position_y == 0
    assert div_c.position_y == div_d.position_y == 2
    assert div_a.height == div_b.height == div_c.height == div_d.height == 2
    assert div_a.width == div_b.width == div_c.width == div_d.width == 5
    assert article.width == 10


@assert_no_logs
def test_grid_template_areas_grid_area():
    page, = render_pages('''
      <style>
        article {
          display: grid;
          font-family: weasyprint;
          font-size: 2px;
          grid-template-areas: 'b a' 'd c';
          line-height: 1;
          width: 10px;
        }
      </style>
      <article>
        <div style="grid-area: a">a</div> <div style="grid-area: b">b</div>
        <div style="grid-area: c">c</div> <div style="grid-area: d">d</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_a, div_b, div_c, div_d = article.children
    assert div_b.position_x == div_d.position_x == 0
    assert div_a.position_x == div_c.position_x == 5
    assert div_a.position_y == div_b.position_y == 0
    assert div_c.position_y == div_d.position_y == 2
    assert div_a.height == div_b.height == div_c.height == div_d.height == 2
    assert div_a.width == div_b.width == div_c.width == div_d.width == 5
    assert article.width == 10


@assert_no_logs
def test_grid_template_areas_empty_row():
    page, = render_pages('''
      <style>
        article {
          display: grid;
          font-family: weasyprint;
          font-size: 2px;
          grid-template-areas: 'b a' 'd a' 'd c';
          line-height: 1;
          width: 10px;
        }
      </style>
      <article>
        <div style="grid-area: a">a</div> <div style="grid-area: b">b</div>
        <div style="grid-area: c">c</div> <div style="grid-area: d">d</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_a, div_b, div_c, div_d = article.children
    assert div_b.position_x == div_d.position_x == 0
    assert div_a.position_x == div_c.position_x == 5
    assert div_a.position_y == div_b.position_y == 0
    assert div_c.position_y == div_d.position_y == 2
    assert div_a.height == div_b.height == div_c.height == div_d.height == 2
    assert div_a.width == div_b.width == div_c.width == div_d.width == 5
    assert article.width == 10


@assert_no_logs
def test_grid_template_areas_multiple_rows():
    page, = render_pages('''
      <style>
        article {
          display: grid;
          font-family: weasyprint;
          font-size: 2px;
          grid-template-areas: 'b a' 'd a' '. c';
          line-height: 1;
          width: 10px;
        }
      </style>
      <article>
        <div style="grid-area: a">a</div> <div style="grid-area: b">b</div>
        <div style="grid-area: c">c</div> <div style="grid-area: d">d</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_a, div_b, div_c, div_d = article.children
    assert div_b.position_x == div_d.position_x == 0
    assert div_a.position_x == div_c.position_x == 5
    assert div_a.position_y == div_b.position_y == 0
    assert div_c.position_y == 4
    assert div_d.position_y == 2
    assert div_a.height == 4
    assert div_b.height == div_c.height == div_d.height == 2
    assert div_a.width == div_b.width == div_c.width == div_d.width == 5
    assert article.width == 10


@assert_no_logs
def test_grid_template_areas_multiple_columns():
    page, = render_pages('''
      <style>
        article {
          display: grid;
          font-family: weasyprint;
          font-size: 2px;
          grid-template-areas: 'b b' 'c a';
          line-height: 1;
          width: 10px;
        }
      </style>
      <article>
        <div style="grid-area: a">a</div>
        <div style="grid-area: b">b</div>
        <div style="grid-area: c">c</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_a, div_b, div_c = article.children
    assert div_b.position_x == div_c.position_x == 0
    assert div_a.position_x == 5
    assert div_a.position_y == div_c.position_y == 2
    assert div_b.position_y == 0
    assert div_a.height == div_b.height == div_c.height == 2
    assert div_a.width == div_c.width == 5
    assert div_b.width == 10
    assert article.width == 10


@assert_no_logs
def test_grid_template_areas_overlap():
    page, = render_pages('''
      <style>
        article {
          display: grid;
          font-family: weasyprint;
          font-size: 2px;
          grid-template-areas: 'a b' 'c d';
          line-height: 1;
          width: 10px;
        }
      </style>
      <article>
        <div style="grid-area: a">a</div>
        <div style="grid-area: a">a</div>
        <div style="grid-area: a">a</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_a1, div_a2, div_a3 = article.children
    assert div_a1.position_x == div_a2.position_x == div_a3.position_x == 0
    assert div_a1.position_y == div_a2.position_y == div_a3.position_y == 0
    assert div_a1.width == div_a2.width == div_a3.width == 6  # 2 + (10-2) / 2
    assert div_a1.height == div_a2.height == div_a3.height == 2
    assert article.width == 10


@assert_no_logs
def test_grid_template_big_span():
    page, = render_pages('''
      <style>
        article {
          display: grid;
          font-family: weasyprint;
          font-size: 2px;
          grid-template-columns: 50% 50%;
          line-height: 1;
          width: 6px;
        }
      </style>
      <article>
        <div>a</div>
        <div style="grid-row: span 2">b b b b</div>
        <div>a</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_1, div_2, div_3 = article.children
    assert div_1.position_x == div_3.position_x == 0
    assert div_2.position_x == 3
    assert div_1.position_y == div_2.position_y == 0
    assert div_3.position_y == 4
    assert div_1.width == div_2.width == div_3.width == 3
    assert div_1.height == div_3.height == 4
    assert div_2.height == article.height == 8
    assert article.width == 6


@assert_no_logs
def test_grid_template_multiple_big_span():
    page, = render_pages('''
      <style>
        article {
          display: grid;
          font-family: weasyprint;
          font-size: 2px;
          grid-template-columns: 50% 50%;
          line-height: 1;
          width: 6px;
        }
      </style>
      <article>
        <div>a</div>
        <div style="grid-row: span 3">b b b b b b</div>
        <div>a</div>
        <div>a</div>
        <div style="grid-row: span 2">c</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_1, div_2, div_3, div_4, div_5 = article.children
    assert div_1.position_x == div_3.position_x == div_4.position_x == 0
    assert div_5.position_x == 0
    assert div_2.position_x == 3
    assert div_1.position_y == div_2.position_y == 0
    assert div_3.position_y == 4
    assert div_4.position_y == 8
    assert div_5.position_y == 12
    assert div_1.width == div_2.width == div_3.width == div_5.width == 3
    assert div_4.width == 3
    assert div_1.height == div_3.height == div_4.height == 4
    assert div_2.height == 12
    assert div_5.height == 2
    assert article.height == 14
    assert article.width == 6


@assert_no_logs
def test_grid_template_areas_span_overflow():
    page, = render_pages('''
      <style>
        article {
          display: grid;
          font-family: weasyprint;
          font-size: 2px;
          grid-template-columns: 50% 50%;
          line-height: 1;
          width: 10px;
        }
      </style>
      <article>
        <div style="">a</div>
        <div style="grid-column: span 2">a</div>
        <div style="">a</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_a1, div_a2, div_a3 = article.children
    assert div_a1.position_x == div_a2.position_x == div_a3.position_x == 0
    assert div_a1.position_y == 0
    assert div_a2.position_y == 2
    assert div_a3.position_y == 4
    assert div_a1.width == div_a3.width == 5
    assert div_a2.width == 10
    assert div_a1.height == div_a2.height == div_a3.height == 2
    assert article.width == 10


@assert_no_logs
def test_grid_template_areas_extra_span():
    page, = render_pages('''
      <style>
        article {
          display: grid;
          font-family: weasyprint;
          font-size: 2px;
          grid-template-areas: 'a . b' 'c d d';
          line-height: 1;
          width: 10px;
        }
      </style>
      <article>
        <div style="grid-area: a">a</div>
        <div style="grid-area: b">b</div>
        <div style="grid-area: c">c</div>
        <div style="grid-area: d">d</div>
        <div style="grid-row: span 2; grid-column: span 2">e</div>
        <div>f</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_a, div_b, div_c, div_d, div_e, div_f = article.children
    assert div_a.position_x == div_c.position_x == div_e.position_x == 0
    assert div_d.position_x == 4  # 2 + (10 - 2×3) / 2
    assert div_b.position_x == div_f.position_x == 6
    assert div_a.position_y == div_b.position_y == 0
    assert div_c.position_y == div_d.position_y == 2
    assert div_e.position_y == div_f.position_y == 4
    assert div_a.width == div_b.width == div_c.width == div_f.width == 4
    assert div_d.width == div_e.width == 6
    assert {div.height for div in article.children} == {2}
    assert article.width == 10


@assert_no_logs
def test_grid_template_areas_extra_span_dense():
    page, = render_pages('''
      <style>
        article {
          display: grid;
          font-family: weasyprint;
          font-size: 2px;
          grid-auto-flow: dense;
          grid-template-areas: 'a . b' 'c d d';
          line-height: 1;
          width: 9px;
        }
      </style>
      <article>
        <div style="grid-area: a">a</div>
        <div style="grid-area: b">b</div>
        <div style="grid-area: c">c</div>
        <div style="grid-area: d">d</div>
        <div style="grid-row: span 2; grid-column: span 2">e</div>
        <div>f</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_a, div_b, div_c, div_d, div_e, div_f = article.children
    assert div_a.position_x == div_c.position_x == div_e.position_x == 0
    assert div_d.position_x == div_f.position_x == 3
    assert div_b.position_x == 6
    assert div_a.position_y == div_b.position_y == div_f.position_y == 0
    assert div_c.position_y == div_d.position_y == 2
    assert div_e.position_y == 4
    assert div_a.width == div_b.width == div_c.width == div_f.width == 3
    assert div_d.width == div_e.width == 6
    assert {div.height for div in article.children} == {2}
    assert article.height == 6
    assert article.width == 9


@assert_no_logs
def test_grid_area_multiple_values():
    page, = render_pages('''
      <style>
        article {
          display: grid;
          font-family: weasyprint;
          font-size: 2px;
          grid-template-columns: 5px 5px;
          grid-template-rows: 2px 2px;
          line-height: 1;
          width: 10px;
        }
      </style>
      <article>
        <div style="grid-area: 2 / 1 / 3 / 2">a</div>
        <div style="grid-area: 1 / 1 / 2 / 3">b</div>
        <div style="grid-area: 2 / 2 / 3 / 3">c</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_a, div_b, div_c = article.children
    assert div_a.position_x == div_b.position_x == 0
    assert div_c.position_x == 5
    assert div_b.position_y == 0
    assert div_a.position_y == div_c.position_y == 2
    assert div_a.height == div_b.height == div_c.height == 2
    assert div_a.width == div_c.width == 5
    assert div_b.width == 10
    assert article.width == 10


@assert_no_logs
def test_grid_template_repeat_fr():
    page, = render_pages('''
      <style>
        article {
          display: grid;
          font-family: weasyprint;
          font-size: 2px;
          grid-template-columns: repeat(2, 1fr 2fr);
          line-height: 1;
          width: 12px;
        }
      </style>
      <article>
        <div>a</div>
        <div>b</div>
        <div>c</div>
        <div>d</div>
        <div>e</div>
        <div>f</div>
        <div>g</div>
        <div>h</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_a, div_b, div_c, div_d, div_e, div_f, div_g, div_h = article.children
    assert div_a.position_x == div_e.position_x == 0
    assert div_b.position_x == div_f.position_x == 2
    assert div_c.position_x == div_g.position_x == 6
    assert div_d.position_x == div_h.position_x == 8
    assert div_a.position_y == div_b.position_y == 0
    assert div_c.position_y == div_d.position_y == 0
    assert div_e.position_y == div_f.position_y == 2
    assert div_g.position_y == div_h.position_y == 2
    assert div_a.width == div_c.width == div_e.width == div_g.width == 2
    assert div_b.width == div_d.width == div_f.width == div_h.width == 4
    assert {div.height for div in article.children} == {2}
    assert article.width == 12


@assert_no_logs
def test_grid_template_shorthand_fr():
    page, = render_pages('''
      <style>
        article {
          display: grid;
          font-family: weasyprint;
          font-size: 2px;
          grid-template: auto 1fr / auto 1fr auto;
          line-height: 1;
          width: 10px;
        }
      </style>
      <article>
        <div>a</div>
        <div>b</div>
        <div>c</div>
        <div>d</div>
        <div>e</div>
        <div>f</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_a, div_b, div_c, div_d, div_e, div_f = article.children
    assert div_a.position_x == div_d.position_x == 0
    assert div_b.position_x == div_e.position_x == 2
    assert div_c.position_x == div_f.position_x == 8
    assert div_a.position_y == div_b.position_y == div_c.position_y == 0
    assert div_d.position_y == div_e.position_y == div_f.position_y == 2
    assert div_a.width == div_c.width == div_d.width == div_f.width == 2
    assert div_b.width == div_e.width == 6
    assert {div.height for div in article.children} == {2}
    assert article.width == 10


@assert_no_logs
def test_grid_shorthand_auto_flow_rows_fr_size():
    page, = render_pages('''
      <style>
        article {
          display: grid;
          font-family: weasyprint;
          font-size: 2px;
          grid: auto-flow 1fr / 6px;
          line-height: 1;
          width: 10px;
        }
      </style>
      <article>
        <div>a</div>
        <div>b</div>
        <div>c</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_a, div_b, div_c = article.children
    assert div_a.position_x == div_b.position_x == div_c.position_x == 0
    assert div_a.position_y == 0
    assert div_b.position_y == 2
    assert div_c.position_y == 4
    assert div_a.width == div_b.width == div_c.width == 6
    assert {div.height for div in article.children} == {2}
    assert article.width == 10


@assert_no_logs
def test_grid_template_fr_too_large():
    page, = render_pages('''
      <style>
        article {
          display: grid;
          font-family: weasyprint;
          font-size: 2px;
          grid-template-columns: 1fr 1fr;
          line-height: 1;
          width: 10px;
        }
      </style>
      <article>
        <div>a</div><div>bbb</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_a, div_b = article.children
    assert div_a.position_x == 0
    assert div_b.position_x == 4
    assert div_a.position_y == div_b.position_y == 0
    assert div_a.height == div_b.height == 2
    assert div_a.width == 4
    assert div_b.width == 6
    assert article.width == 10


def test_grid_shorthand_auto_flow_columns_none_dense():
    page, = render_pages('''
      <style>
        article {
          display: grid;
          font-family: weasyprint;
          font-size: 2px;
          grid: none / auto-flow dense 1fr;
          line-height: 1;
          width: 12px;
        }
      </style>
      <article>
        <div>a</div>
        <div>b</div>
        <div>c</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_a, div_b, div_c = article.children
    assert div_a.position_x == 0
    assert div_b.position_x == 4
    assert div_c.position_x == 8
    assert div_a.position_y == div_b.position_y == div_c.position_y == 0
    assert div_a.height == div_b.height == div_c.height == 2
    assert {div.width for div in article.children} == {4}
    assert article.width == 12


@assert_no_logs
def test_grid_template_fr_undefined_free_space():
    page, = render_pages('''
      <style>
        article {
          display: grid;
          font-family: weasyprint;
          font-size: 2px;
          grid-template-rows: 1fr 1fr;
          grid-template-columns: 1fr 1fr;
          line-height: 1;
          width: 10px;
        }
      </style>
      <article>
        <div>a</div> <div>b<br>b<br>b<br>b</div>
        <div>c</div> <div>d</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_a, div_b, div_c, div_d = article.children
    assert div_a.position_x == div_c.position_x == 0
    assert div_b.position_x == div_d.position_x == 5
    assert div_a.height == div_b.height == div_c.height == div_d.height == 8
    assert div_a.width == div_c.width == 5
    assert div_b.width == div_d.width == 5
    assert article.width == 10
    assert article.height == 16


@assert_no_logs
def test_grid_column_start():
    page, = render_pages('''
      <style>
        dl {
          display: grid;
          font-family: weasyprint;
          font-size: 2px;
          grid-template-columns: max-content auto;
          line-height: 1;
          width: 10px;
        }
        dt {
          display: block;
          grid-column-start: 1;
        }
        dd {
          display: block;
          grid-column-start: 2;
        }
      </style>
      <dl>
        <dt>A</dt>
        <dd>A1</dd>
        <dd>A2</dd>
        <dt>B</dt>
        <dd>B1</dd>
        <dd>B2</dd>
      </dl>
    ''')
    html, = page.children
    body, = html.children
    dl, = body.children
    dt_a, dd_a1, dd_a2, dt_b, dd_b1, dd_b2 = dl.children
    assert dt_a.position_y == dd_a1.position_y == 0
    assert dd_a2.position_y == 2
    assert dt_b.position_y == dd_b1.position_y == 4
    assert dd_b2.position_y == 6
    assert dt_a.position_x == dt_b.position_x == 0
    assert dd_a1.position_x == dd_a2.position_x == 2
    assert dd_b1.position_x == dd_b2.position_x == 2


@assert_no_logs
def test_grid_column_start_blockified():
    page, = render_pages('''
      <style>
        dl {
          display: grid;
          font-family: weasyprint;
          font-size: 2px;
          grid-template-columns: max-content auto;
          line-height: 1;
          width: 10px;
        }
        dt {
          display: inline;
          grid-column-start: 1;
        }
        dd {
          display: inline;
          grid-column-start: 2;
        }
      </style>
      <dl>
        <dt>A</dt>
        <dd>A1</dd>
        <dd>A2</dd>
        <dt>B</dt>
        <dd>B1</dd>
        <dd>B2</dd>
      </dl>
    ''')
    html, = page.children
    body, = html.children
    dl, = body.children
    dt_a, dd_a1, dd_a2, dt_b, dd_b1, dd_b2 = dl.children
    assert dt_a.position_y == dd_a1.position_y == 0
    assert dd_a2.position_y == 2
    assert dt_b.position_y == dd_b1.position_y == 4
    assert dd_b2.position_y == 6
    assert dt_a.position_x == dt_b.position_x == 0
    assert dd_a1.position_x == dd_a2.position_x == 2
    assert dd_b1.position_x == dd_b2.position_x == 2


@assert_no_logs
def test_grid_undefined_free_space():
    page, = render_pages('''
      <style>
        body {
          font-family: weasyprint;
          font-size: 2px;
          line-height: 1;
        }
        .columns {
          display: grid;
          grid-template-columns: 1fr 1fr;
          width: 8px;
        }
        .rows {
          display: grid;
          grid-template-rows: 1fr 1fr;
        }
      </style>
      <div class="columns">
        <div class="rows">
          <div>aa</div>
          <div>b</div>
        </div>
        <div class="rows">
          <div>c<br>c</div>
          <div>d</div>
        </div>
      </div>
    ''')
    html, = page.children
    body, = html.children
    div_c, = body.children
    div_c1, div_c2 = div_c.children
    div_r11, div_r12 = div_c1.children
    div_r21, div_r22 = div_c2.children
    assert div_r11.position_x == div_r12.position_x == 0
    assert div_r21.position_x == div_r22.position_x == 4
    assert div_r11.position_y == div_r21.position_y == 0
    assert div_r12.position_y == div_r22.position_y == 4
    assert div_r11.height == div_r12.height == div_r21.height == div_r22.height == 4
    assert div_r11.width == div_r12.width == div_r21.width == div_r22.width == 4
    assert div_c.width == 8


@assert_no_logs
def test_grid_padding():
    page, = render_pages('''
      <style>
        article {
          display: grid;
          font-family: weasyprint;
          font-size: 2px;
          grid-template-rows: auto 1fr;
          grid-template-columns: auto 1fr;
          line-height: 1;
          width: 14px;
        }
      </style>
      <article>
        <div style="padding: 1px">a</div> <div>b</div>
        <div>c</div> <div style="padding: 2px">d</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_a, div_b, div_c, div_d = article.children
    assert div_a.position_x == div_c.position_x == div_c.content_box_x() == 0
    assert div_a.content_box_x() == 1
    assert div_b.position_x == div_b.content_box_x() == div_d.position_x == 4
    assert div_d.content_box_x() == 6
    assert div_a.width == 2
    assert div_b.width == 10
    assert div_c.width == 4
    assert div_d.width == 6
    assert article.width == 14
    assert div_a.position_y == div_b.position_y == div_b.content_box_y() == 0
    assert div_a.content_box_y() == 1
    assert div_c.position_y == div_c.content_box_y() == div_d.position_y == 4
    assert div_d.content_box_y() == 6
    assert div_a.height == div_d.height == 2
    assert div_b.height == 4
    assert div_c.height == 6
    assert article.height == 10


@assert_no_logs
def test_grid_border():
    page, = render_pages('''
      <style>
        article {
          display: grid;
          font-family: weasyprint;
          font-size: 2px;
          grid-template-rows: auto 1fr;
          grid-template-columns: auto 1fr;
          line-height: 1;
          width: 14px;
        }
      </style>
      <article>
        <div style="border: 1px solid">a</div> <div>b</div>
        <div>c</div> <div style="border: 2px solid">d</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_a, div_b, div_c, div_d = article.children
    assert div_a.position_x == div_c.position_x == div_c.padding_box_x() == 0
    assert div_a.padding_box_x() == 1
    assert div_b.position_x == div_b.padding_box_x() == div_d.position_x == 4
    assert div_d.padding_box_x() == 6
    assert div_a.width == 2
    assert div_b.width == 10
    assert div_c.width == 4
    assert div_d.width == 6
    assert article.width == 14
    assert div_a.position_y == div_b.position_y == div_b.padding_box_y() == 0
    assert div_a.padding_box_y() == 1
    assert div_c.position_y == div_c.padding_box_y() == div_d.position_y == 4
    assert div_d.padding_box_y() == 6
    assert div_a.height == div_d.height == 2
    assert div_b.height == 4
    assert div_c.height == 6
    assert article.height == 10


@assert_no_logs
def test_grid_margin():
    page, = render_pages('''
      <style>
        article {
          display: grid;
          font-family: weasyprint;
          font-size: 2px;
          grid-template-rows: auto 1fr;
          grid-template-columns: auto 1fr;
          line-height: 1;
          width: 14px;
        }
      </style>
      <article>
        <div style="margin: 1px">a</div> <div>b</div>
        <div>c</div> <div style="margin: 2px">d</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_a, div_b, div_c, div_d = article.children
    assert div_a.position_x == div_c.position_x == div_c.border_box_x() == 0
    assert div_a.border_box_x() == 1
    assert div_b.position_x == div_b.border_box_x() == div_d.position_x == 4
    assert div_d.border_box_x() == 6
    assert div_a.width == 2
    assert div_b.width == 10
    assert div_c.width == 4
    assert div_d.width == 6
    assert article.width == 14
    assert div_a.position_y == div_b.position_y == div_b.border_box_y() == 0
    assert div_a.border_box_y() == 1
    assert div_c.position_y == div_c.border_box_y() == div_d.position_y == 4
    assert div_d.border_box_y() == 6
    assert div_a.height == div_d.height == 2
    assert div_b.height == 4
    assert div_c.height == 6
    assert article.height == 10


@assert_no_logs
def test_grid_item_margin():
    # Regression test for #2154.
    page, = render_pages('''
      <style>
        article { display: grid }
        div { margin: auto }
      </style>
      <article>
        <div>a</div>
        <div>b</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_a, div_b = article.children
    # TODO: Test auto margin values.


@assert_no_logs
def test_grid_auto_flow_column():
    page, = render_pages('''
      <article style="display: grid; grid-auto-flow: column">
        <div>a</div>
        <div>a</div>
        <div>a</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_a, div_b, div_c = article.children
    assert div_a.position_x < div_b.position_x < div_c.position_x
    assert div_a.position_y == div_b.position_y == div_c.position_y == 0
    assert div_a.width == div_b.width == div_c.width
    assert div_a.height == div_b.height == div_c.height == html.height == article.height


@assert_no_logs
def test_grid_template_areas_extra_span_column_dense():
    page, = render_pages('''
      <style>
        article {
          display: grid;
          font-family: weasyprint;
          font-size: 2px;
          grid-auto-flow: column dense;
          grid-template-areas: 'a . b' 'c d d';
          line-height: 1;
          width: 12px;
        }
      </style>
      <article>
        <div style="grid-area: a">a</div>
        <div style="grid-area: b">b</div>
        <div style="grid-area: c">c</div>
        <div style="grid-area: d">d</div>
        <div style="grid-row: span 2">e</div>
        <div>f</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_a, div_b, div_c, div_d, div_e, div_f = article.children
    assert div_a.position_x == div_c.position_x == 0
    assert div_d.position_x == div_f.position_x == 3
    assert div_b.position_x == 6
    assert div_e.position_x == 9
    assert (
        div_a.position_y == div_b.position_y ==
        div_e.position_y == div_f.position_y == 0)
    assert div_c.position_y == div_d.position_y == 2
    assert (
        div_a.width == div_b.width == div_c.width ==
        div_e.width == div_f.width == 3)
    assert div_d.width == 6
    assert (
        div_a.height == div_b.height == div_c.height ==
        div_d.height == div_f.height == 2)
    assert div_e.height == 4
    assert article.height == 4
    assert article.width == 12


@assert_no_logs
def test_grid_gap_explicit_grid_column():
    # Regression test for #2187.
    page, = render_pages('''
      <style>
        article {
          display: grid;
          font-family: weasyprint;
          font-size: 2px;
          gap: 2px;
          grid-template-columns: 1fr;
          line-height: 1;
          width: 12px;
        }
      </style>
      <article>
        <div>a</div>
        <div style="grid-column: 1">b</div>
      </article>
    ''')
    html, = page.children
    body, = html.children
    article, = body.children
    div_a, div_b = article.children
    assert div_a.position_x == div_b.position_x == 0
    assert div_a.position_y == 0
    assert div_b.position_y == 4
    assert article.height == 6
    assert article.width == 12


@assert_no_logs
def test_grid_break():
    page1, page2 = render_pages('''
      <style>
        @page { size: 10px 11px }
        body { font: 2px / 1 weasyprint }
        section { display: grid; grid-template-columns: 1fr 1fr }
      </style>
      <section>
        <div>1</div>
        <div>2</div>
        <div>3</div>
        <div>4</div>
        <div>5</div>
        <div>6</div>
        <div>7a<br>7b<br>7c</div>
        <div>8</div>
        <div>9</div>
        <div>10</div>
      </section>
    ''')
    html, = page1.children
    body, = html.children
    section, = body.children
    assert section.height == 11
    div1, div2, div3, div4, div5, div6, div7, div8 = section.children
    assert div1.position_x == div3.position_x == div5.position_x == div7.position_x == 0
    assert div2.position_x == div4.position_x == div6.position_x == div8.position_x == 5
    assert div1.position_y == div2.position_y == 0
    assert div1.height == div2.height == 2
    assert div3.position_y == div4.position_y == 2
    assert div3.height == div4.height == 2
    assert div5.position_y == div6.position_y == 4
    assert div5.height == div6.height == 2
    assert div7.position_y == div8.position_y == 6
    assert div7.height == div8.height == 5
    line1, line2 = div7.children
    text, br = line1.children
    assert text.text == '7a'
    text, br = line2.children
    assert text.text == '7b'
    line, = div8.children
    text, = line.children
    assert text.text == '8'

    html, = page2.children
    body, = html.children
    section, = body.children
    assert section.height == 4
    div7, div8, div9, div10 = section.children
    assert div7.position_x == div9.position_x == 0
    assert div8.position_x == div10.position_x == 5
    assert div7.position_y == div8.position_y == 0
    assert div9.position_y == div10.position_y == 2
    assert div7.height == div8.height == div9.height == div10.height == 2
    line, = div7.children
    text, = line.children
    assert text.text == '7c'
    assert not div8.children


@assert_no_logs
def test_grid_break_order_negative():
    page1, page2 = render_pages('''
      <style>
        @page { size: 10px 11px }
        body { font: 2px / 1 weasyprint }
        section { display: grid; grid-template-columns: 1fr 1fr }
      </style>
      <section>
        <div>3</div>
        <div>4</div>
        <div>5</div>
        <div>6</div>
        <div>7a<br>7b<br>7c</div>
        <div>8</div>
        <div>9</div>
        <div>10</div>
        <div style="order: -2">1</div>
        <div style="order: -1">2</div>
      </section>
    ''')
    html, = page1.children
    body, = html.children
    section, = body.children
    assert section.height == 11
    div1, div2, div3, div4, div5, div6, div7, div8 = section.children
    assert div1.position_x == div3.position_x == div5.position_x == div7.position_x == 0
    assert div2.position_x == div4.position_x == div6.position_x == div8.position_x == 5
    assert div1.position_y == div2.position_y == 0
    assert div1.height == div2.height == 2
    assert div3.position_y == div4.position_y == 2
    assert div3.height == div4.height == 2
    assert div5.position_y == div6.position_y == 4
    assert div5.height == div6.height == 2
    assert div7.position_y == div8.position_y == 6
    assert div7.height == div8.height == 5
    line1, line2 = div7.children
    text, br = line1.children
    assert text.text == '7a'
    text, br = line2.children
    assert text.text == '7b'
    line, = div8.children
    text, = line.children
    assert text.text == '8'

    html, = page2.children
    body, = html.children
    section, = body.children
    assert section.height == 4
    div7, div8, div9, div10 = section.children
    assert div7.position_x == div9.position_x == 0
    assert div8.position_x == div10.position_x == 5
    assert div7.position_y == div8.position_y == 0
    assert div9.position_y == div10.position_y == 2
    assert div7.height == div8.height == div9.height == div10.height == 2
    line, = div7.children
    text, = line.children
    assert text.text == '7c'
    assert not div8.children


@assert_no_logs
def test_grid_break_order_positive():
    page1, page2 = render_pages('''
      <style>
        @page { size: 10px 11px }
        body { font: 2px / 1 weasyprint }
        section { display: grid; grid-template-columns: 1fr 1fr }
      </style>
      <section>
        <div>1</div>
        <div>2</div>
        <div style="order: 9">9</div>
        <div style="order: 10">10</div>
        <div>3</div>
        <div>4</div>
        <div>5</div>
        <div>6</div>
        <div>7a<br>7b<br>7c</div>
        <div>8</div>
      </section>
    ''')
    html, = page1.children
    body, = html.children
    section, = body.children
    assert section.height == 11
    div1, div2, div3, div4, div5, div6, div7, div8 = section.children
    assert div1.position_x == div3.position_x == div5.position_x == div7.position_x == 0
    assert div2.position_x == div4.position_x == div6.position_x == div8.position_x == 5
    assert div1.position_y == div2.position_y == 0
    assert div1.height == div2.height == 2
    assert div3.position_y == div4.position_y == 2
    assert div3.height == div4.height == 2
    assert div5.position_y == div6.position_y == 4
    assert div5.height == div6.height == 2
    assert div7.position_y == div8.position_y == 6
    assert div7.height == div8.height == 5
    line1, line2 = div7.children
    text, br = line1.children
    assert text.text == '7a'
    text, br = line2.children
    assert text.text == '7b'
    line, = div8.children
    text, = line.children
    assert text.text == '8'

    html, = page2.children
    body, = html.children
    section, = body.children
    assert section.height == 4
    div7, div8, div9, div10 = section.children
    assert div7.position_x == div9.position_x == 0
    assert div8.position_x == div10.position_x == 5
    assert div7.position_y == div8.position_y == 0
    assert div9.position_y == div10.position_y == 2
    assert div7.height == div8.height == div9.height == div10.height == 2
    line, = div7.children
    text, = line.children
    assert text.text == '7c'
    assert not div8.children
    line, = div9.children
    text, = line.children
    assert text.text == '9'
    line, = div10.children
    text, = line.children
    assert text.text == '10'


@assert_no_logs
def test_grid_break_border():
    page1, page2 = render_pages('''
      <style>
        @page { size: 12px 18px }
        body { font: 2px / 1 weasyprint }
        section { display: grid; grid-template-columns: 1fr 1fr }
        div { border: 1px solid }
      </style>
      <section>
        <div>1</div>
        <div>2</div>
        <div>3</div>
        <div>4</div>
        <div>5</div>
        <div>6</div>
        <div>7a<br>7b<br>7c</div>
        <div>8</div>
        <div>9</div>
        <div>10</div>
      </section>
    ''')
    html, = page1.children
    body, = html.children
    section, = body.children
    assert section.height == 18
    div1, div2, div3, div4, div5, div6, div7, div8 = section.children
    for div in section.children:
        assert div.border_top_width == 1
        assert div.border_left_width == 1
        assert div.border_right_width == 1
    for div in div1, div2, div3, div4, div5, div6:
        assert div.border_bottom_width == 1
    for div in div7, div8:
        assert div.border_bottom_width == 0
    assert div1.position_x == div3.position_x == div5.position_x == div7.position_x == 0
    assert div2.position_x == div4.position_x == div6.position_x == div8.position_x == 6
    assert div1.position_y == div2.position_y == 0
    assert div1.height == div2.height == 2
    assert div1.width == div2.width == 4
    assert div3.position_y == div4.position_y == 4
    assert div3.height == div4.height == 2
    assert div5.position_y == div6.position_y == 8
    assert div5.height == div6.height == 2
    assert div7.position_y == div8.position_y == 12
    assert div7.height == div8.height == 5
    line1, line2 = div7.children
    text, br = line1.children
    assert text.text == '7a'
    text, br = line2.children
    assert text.text == '7b'
    line, = div8.children
    text, = line.children
    assert text.text == '8'

    html, = page2.children
    body, = html.children
    section, = body.children
    # assert section.height == 7
    div7, div8, div9, div10 = section.children
    for div in section.children:
        assert div.border_bottom_width == 1
        assert div.border_left_width == 1
        assert div.border_right_width == 1
    for div in div7, div8:
        assert div.border_top_width == 0
    for div in div9, div10:
        assert div.border_top_width == 1
    assert div7.position_x == div9.position_x == 0
    assert div8.position_x == div10.position_x == 6
    assert div7.position_y == div8.position_y == 0
    assert div9.position_y == div10.position_y == 3
    assert div7.height == div8.height == div9.height == div10.height == 2
    assert div7.width == div8.width == div9.width == div10.width == 4
    line, = div7.children
    text, = line.children
    assert text.text == '7c'
    assert not div8.children


@assert_no_logs
def test_grid_break_multiple():
    page1, page2, page3 = render_pages('''
      <style>
        @page { size: 10px 11px }
        body { font: 2px / 1 weasyprint }
        section { display: grid; grid-template-columns: 1fr 1fr }
      </style>
      <section>
        <div>1</div>
        <div>2</div>
        <div>3</div>
        <div>4</div>
        <div>5</div>
        <div>6</div>
        <div>7a<br>7b<br>7c<br>7d<br>7e<br>7f<br>7g<br>7h</div>
        <div>8</div>
        <div>9</div>
        <div>10</div>
      </section>
    ''')
    html, = page1.children
    body, = html.children
    section, = body.children
    assert section.height == 11
    div1, div2, div3, div4, div5, div6, div7, div8 = section.children
    assert div1.position_x == div3.position_x == div5.position_x == div7.position_x == 0
    assert div2.position_x == div4.position_x == div6.position_x == div8.position_x == 5
    assert div1.position_y == div2.position_y == 0
    assert div1.height == div2.height == 2
    assert div3.position_y == div4.position_y == 2
    assert div3.height == div4.height == 2
    assert div5.position_y == div6.position_y == 4
    assert div5.height == div6.height == 2
    assert div7.position_y == div8.position_y == 6
    assert div7.height == div8.height == 5
    line1, line2 = div7.children
    text, br = line1.children
    assert text.text == '7a'
    text, br = line2.children
    assert text.text == '7b'
    line, = div8.children
    text, = line.children
    assert text.text == '8'

    html, = page2.children
    body, = html.children
    section, = body.children
    assert section.height == 11
    div7, div8 = section.children
    assert div7.position_x == 0
    assert div8.position_x == 5
    assert div7.height == div8.height == 11
    line1, line2, line3, line4, line5 = div7.children
    text, _ = line1.children
    assert text.text == '7c'
    text, _ = line2.children
    assert text.text == '7d'
    text, _ = line3.children
    assert text.text == '7e'
    text, _ = line4.children
    assert text.text == '7f'
    text, _ = line5.children
    assert text.text == '7g'
    assert not div8.children

    html, = page3.children
    body, = html.children
    section, = body.children
    assert section.height == 4
    div7, div8, div9, div10 = section.children
    assert div7.position_x == div9.position_x == 0
    assert div8.position_x == div10.position_x == 5
    assert div7.position_y == div8.position_y == 0
    assert div9.position_y == div10.position_y == 2
    assert div7.height == div8.height == div9.height == div10.height == 2
    line, = div7.children
    text, = line.children
    assert text.text == '7h'
    assert not div8.children


@assert_no_logs
def test_grid_break_span():
    page1, page2 = render_pages('''
      <style>
        @page { size: 10px 11px }
        body { font: 2px / 1 weasyprint }
        section { display: grid; grid-template-columns: 1fr 1fr }
      </style>
      <section>
        <div>1</div>
        <div>2</div>
        <div>3</div>
        <div>4</div>
        <div>5</div>
        <div>6</div>
        <div style="grid-row: span 3">7a<br>7b<br>7c<br>7d</div>
        <div>8</div>
        <div>9</div>
        <div>10</div>
        <div>11</div>
        <div>12</div>
      </section>
    ''')
    html, = page1.children
    body, = html.children
    section, = body.children
    assert section.height == 11
    div1, div2, div3, div4, div5, div6, div7, div8, div9 = section.children
    assert div1.position_x == div3.position_x == div5.position_x == div7.position_x == 0
    assert div2.position_x == div4.position_x == div6.position_x == div8.position_x == 5
    assert div1.position_y == div2.position_y == 0
    assert div1.height == div2.height == 2
    assert div3.position_y == div4.position_y == 2
    assert div3.height == div4.height == 2
    assert div5.position_y == div6.position_y == 4
    assert div5.height == div6.height == 2
    assert div7.position_y == div8.position_y == 6
    assert div7.height == 5
    assert 2.6 < div8.height < 2.7
    assert 2.3 < div9.height < 2.4
    line1, line2 = div7.children
    text, br = line1.children
    assert text.text == '7a'
    text, br = line2.children
    assert text.text == '7b'
    line, = div8.children
    text, = line.children
    assert text.text == '8'
    line, = div9.children
    text, = line.children
    assert text.text == '9'

    # TODO: div7 height could be only 4, but algorithm is not specified.
    html, = page2.children
    body, = html.children
    section, = body.children
    assert 6.6 < section.height < 6.7
    div7, div9, div10, div11, div12 = section.children
    assert div7.position_x == 0
    assert div8.position_x == 5
    assert 4.6 < div7.height < 4.7
    line1, line2 = div7.children
    text, br = line1.children
    assert text.text == '7c'
    text, = line2.children
    assert text.text == '7d'
    assert not div9.children
    assert div10.position_x == 5
    assert 1.3 < div10.position_y < 1.4
    line, = div10.children
    text, = line.children
    assert text.text == '10'
    assert div11.position_x == 0
    assert div12.position_x == 5
    assert 4.6 < div11.position_y < 4.7
    assert 4.6 < div12.position_y < 4.7
    line, = div11.children
    text, = line.children
    assert text.text == '11'
    line, = div12.children
    text, = line.children
    assert text.text == '12'


@assert_no_logs
def test_grid_break_item_avoid():
    page1, page2 = render_pages('''
      <style>
        @page { size: 10px 11px }
        body { font: 2px / 1 weasyprint }
        section { display: grid; grid-template-columns: 1fr 1fr }
      </style>
      <section>
        <div>1</div>
        <div>2</div>
        <div>3</div>
        <div>4</div>
        <div>5</div>
        <div>6</div>
        <div>7a<br>7b<br>7c</div>
        <div style="break-inside: avoid">8</div>
        <div>9</div>
        <div>10</div>
      </section>
    ''')
    html, = page1.children
    body, = html.children
    section, = body.children
    assert section.height == 11
    div1, div2, div3, div4, div5, div6 = section.children
    assert div1.position_x == div3.position_x == div5.position_x == 0
    assert div2.position_x == div4.position_x == div6.position_x == 5
    assert div1.position_y == div2.position_y == 0
    assert div1.height == div2.height == 2
    assert div3.position_y == div4.position_y == 2
    assert div3.height == div4.height == 2
    assert div5.position_y == div6.position_y == 4
    assert div5.height == div6.height == 2

    html, = page2.children
    body, = html.children
    section, = body.children
    assert section.height == 8
    div7, div8, div9, div10 = section.children
    assert div7.position_x == div9.position_x == 0
    assert div8.position_x == div10.position_x == 5
    assert div7.position_y == div8.position_y == 0
    assert div9.position_y == div10.position_y == 6
    assert div7.height == div8.height == 6
    assert div9.height == div10.height == 2
    assert len(div7.children) == 3
    assert len(div8.children) == 1


@assert_no_logs
def test_grid_break_item_avoid_auto():
    page1, page2 = render_pages('''
      <style>
        @page { size: 10px 11px }
        body { font: 2px / 1 weasyprint }
        section { display: grid; grid-template-columns: 1fr 1fr }
      </style>
      <section>
        <div>1</div>
        <div>2</div>
        <div>3</div>
        <div>4</div>
        <div>5</div>
        <div>6</div>
        <div style="break-inside: avoid">7a<br>7b<br>7c</div>
        <div style="break-inside: auto">8</div>
        <div>9</div>
        <div>10</div>
      </section>
    ''')
    html, = page1.children
    body, = html.children
    section, = body.children
    assert section.height == 11
    div1, div2, div3, div4, div5, div6 = section.children
    assert div1.position_x == div3.position_x == div5.position_x == 0
    assert div2.position_x == div4.position_x == div6.position_x == 5
    assert div1.position_y == div2.position_y == 0
    assert div1.height == div2.height == 2
    assert div3.position_y == div4.position_y == 2
    assert div3.height == div4.height == 2
    assert div5.position_y == div6.position_y == 4
    assert div5.height == div6.height == 2

    html, = page2.children
    body, = html.children
    section, = body.children
    assert section.height == 8
    div7, div8, div9, div10 = section.children
    assert div7.position_x == div9.position_x == 0
    assert div8.position_x == div10.position_x == 5
    assert div7.position_y == div8.position_y == 0
    assert div9.position_y == div10.position_y == 6
    assert div7.height == div8.height == 6
    assert div9.height == div10.height == 2
    assert len(div7.children) == 3
    assert len(div8.children) == 1


@assert_no_logs
def test_grid_break_container():
    page1, page2 = render_pages('''
      <style>
        @page { size: 10px 11px }
        body { font: 2px / 1 weasyprint }
        section { display: grid; grid-template-columns: 1fr 1fr }
      </style>
      <p>1<br>2<br>3<br>4</p>
      <section style="break-inside: avoid">
        <div>5</div>
        <div>6</div>
        <div>7</div>
        <div>8</div>
        <div>9</div>
        <div>10</div>
      </section>
    ''')
    html, = page1.children
    body, = html.children
    p, = body.children
    assert len(p.children) == 4
    html, = page2.children
    body, = html.children
    section, = body.children
    assert len(section.children) == 6
