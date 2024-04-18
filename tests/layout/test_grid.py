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
    assert article.width == html.width
    assert div_a.width == div_b.width == div_c.width == html.width


@assert_no_logs
def test_grid_template_fr():
    page, = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
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
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
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
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
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
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
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
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
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
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
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
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
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
def test_grid_template_areas_extra_span():
    page, = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
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
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
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
    assert article.width == 9


@assert_no_logs
def test_grid_template_repeat_fr():
    page, = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
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
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
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
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
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
def test_grid_shorthand_auto_flow_columns_none_dense():
    page, = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
        article {
          display: grid;
          font-family: weasyprint;
          font-size: 2px;
          grid: none / auto-flow 1fr dense;
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
    assert div_a.width == div_b.width == div_c.width == 10
    assert {div.height for div in article.children} == {2}
    assert article.width == 10


@assert_no_logs
def test_grid_template_fr_undefined_free_space():
    page, = render_pages('''
      <style>
        @font-face { src: url(weasyprint.otf); font-family: weasyprint }
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
