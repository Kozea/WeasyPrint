"""
    weasyprint.tests.test_counters
    ------------------------------

    Test CSS counters.

"""

import pytest

from .. import HTML
from .test_boxes import assert_tree, parse_all, render_pages
from .testing_utils import assert_no_logs


@assert_no_logs
def test_counters_1():
    assert_tree(parse_all('''
      <style>
        p { counter-increment: p 2 }
        p:before { content: counter(p); }
        p:nth-child(1) { counter-increment: none; }
        p:nth-child(2) { counter-increment: p; }
      </style>
      <p></p>
      <p></p>
      <p></p>
      <p style="counter-reset: p 117 p"></p>
      <p></p>
      <p></p>
      <p style="counter-reset: p -13"></p>
      <p></p>
      <p></p>
      <p style="counter-reset: p 42"></p>
      <p></p>
      <p></p>'''), [
        ('p', 'Block', [
            ('p', 'Line', [
                ('p::before', 'Inline', [
                    ('p::before', 'Text', counter)])])])
        for counter in '0 1 3  2 4 6  -11 -9 -7  44 46 48'.split()])


@assert_no_logs
def test_counters_2():
    assert_tree(parse_all('''
      <ol style="list-style-position: inside">
        <li></li>
        <li></li>
        <li></li>
        <li><ol>
          <li></li>
          <li style="counter-increment: none"></li>
          <li></li>
        </ol></li>
        <li></li>
      </ol>'''), [
        ('ol', 'Block', [
            ('li', 'Block', [
                ('li', 'Line', [
                    ('li::marker', 'Inline', [
                        ('li::marker', 'Text', '1. ')])])]),
            ('li', 'Block', [
                ('li', 'Line', [
                    ('li::marker', 'Inline', [
                        ('li::marker', 'Text', '2. ')])])]),
            ('li', 'Block', [
                ('li', 'Line', [
                    ('li::marker', 'Inline', [
                        ('li::marker', 'Text', '3. ')])])]),
            ('li', 'Block', [
                ('li', 'Block', [
                    ('li', 'Line', [
                        ('li::marker', 'Inline', [
                            ('li::marker', 'Text', '4. ')])])]),
                ('ol', 'Block', [
                    ('li', 'Block', [
                        ('li', 'Line', [
                            ('li::marker', 'Inline', [
                                ('li::marker', 'Text', '1. ')])])]),
                    ('li', 'Block', [
                        ('li', 'Line', [
                            ('li::marker', 'Inline', [
                                ('li::marker', 'Text', '1. ')])])]),
                    ('li', 'Block', [
                        ('li', 'Line', [
                            ('li::marker', 'Inline', [
                                ('li::marker', 'Text', '2. ')])])])])]),
            ('li', 'Block', [
                ('li', 'Line', [
                    ('li::marker', 'Inline', [
                        ('li::marker', 'Text', '5. ')])])])])])


@assert_no_logs
def test_counters_3():
    assert_tree(parse_all('''
      <style>
        p { display: list-item; list-style: inside decimal }
      </style>
      <div>
        <p></p>
        <p></p>
        <p style="counter-reset: list-item 7 list-item -56"></p>
      </div>
      <p></p>'''), [
        ('div', 'Block', [
            ('p', 'Block', [
                ('p', 'Line', [
                    ('p::marker', 'Inline', [
                        ('p::marker', 'Text', '1. ')])])]),
            ('p', 'Block', [
                ('p', 'Line', [
                    ('p::marker', 'Inline', [
                        ('p::marker', 'Text', '2. ')])])]),
            ('p', 'Block', [
                ('p', 'Line', [
                    ('p::marker', 'Inline', [
                        ('p::marker', 'Text', '-55. ')])])])]),
        ('p', 'Block', [
            ('p', 'Line', [
                ('p::marker', 'Inline', [
                    ('p::marker', 'Text', '1. ')])])])])


@assert_no_logs
def test_counters_4():
    assert_tree(parse_all('''
      <style>
        section:before { counter-reset: h; content: '' }
        h1:before { counter-increment: h; content: counters(h, '.') }
      </style>
      <body>
        <section><h1></h1>
          <h1></h1>
          <section><h1></h1>
            <h1></h1>
          </section>
          <h1></h1>
        </section>
      </body>'''), [
        ('section', 'Block', [
            ('section', 'Block', [
                ('section', 'Line', [
                    ('section::before', 'Inline', [])])]),
            ('h1', 'Block', [
                ('h1', 'Line', [
                    ('h1::before', 'Inline', [
                        ('h1::before', 'Text', '1')])])]),
            ('h1', 'Block', [
                ('h1', 'Line', [
                    ('h1::before', 'Inline', [
                        ('h1::before', 'Text', '2')])])]),
            ('section', 'Block', [
                ('section', 'Block', [
                    ('section', 'Line', [
                        ('section::before', 'Inline', [])])]),
                ('h1', 'Block', [
                    ('h1', 'Line', [
                        ('h1::before', 'Inline', [
                            ('h1::before', 'Text', '2.1')])])]),
                ('h1', 'Block', [
                    ('h1', 'Line', [
                        ('h1::before', 'Inline', [
                            ('h1::before', 'Text', '2.2')])])])]),
            ('h1', 'Block', [
                ('h1', 'Line', [
                    ('h1::before', 'Inline', [
                        ('h1::before', 'Text', '3')])])])])])


@assert_no_logs
def test_counters_5():
    assert_tree(parse_all('''
      <style>
        p:before { content: counter(c) }
      </style>
      <div>
        <span style="counter-reset: c">
          Scope created now, deleted after the div
        </span>
      </div>
      <p></p>'''), [
        ('div', 'Block', [
            ('div', 'Line', [
                ('span', 'Inline', [
                    ('span', 'Text',
                     'Scope created now, deleted after the div ')])])]),
        ('p', 'Block', [
            ('p', 'Line', [
                ('p::before', 'Inline', [
                    ('p::before', 'Text', '0')])])])])


@assert_no_logs
def test_counters_6():
    # counter-increment may interfere with display: list-item
    assert_tree(parse_all('''
      <p style="counter-increment: c;
                display: list-item; list-style: inside decimal">'''), [
        ('p', 'Block', [
            ('p', 'Line', [
                ('p::marker', 'Inline', [
                    ('p::marker', 'Text', '0. ')])])])])


@assert_no_logs
def test_counters_7():
    # Test that counters are case-sensitive
    # See https://github.com/Kozea/WeasyPrint/pull/827
    assert_tree(parse_all('''
      <style>
        p { counter-increment: p 2 }
        p:before { content: counter(p) '.' counter(P); }
      </style>
      <p></p>
      <p style="counter-increment: P 3"></p>
      <p></p>'''), [
        ('p', 'Block', [
            ('p', 'Line', [
                ('p::before', 'Inline', [
                    ('p::before', 'Text', counter)])])])
        for counter in '2.0 2.3 4.3'.split()])


@assert_no_logs
def test_counters_8():
    assert_tree(parse_all('''
      <style>
        p:before { content: 'a'; display: list-item }
      </style>
      <p></p>
      <p></p>'''), 2 * [
        ('p', 'Block', [
          ('p::before', 'Block', [
            ('p::marker', 'Block', [
              ('p::marker', 'Line', [
                ('p::marker', 'Text', '• ')])]),
            ('p::before', 'Block', [
                ('p::before', 'Line', [
                    ('p::before', 'Text', 'a')])])])])])


@assert_no_logs
def test_counter_styles_1():
    assert_tree(parse_all('''
      <style>
        body { --var: 'Counter'; counter-reset: p -12 }
        p { counter-increment: p }
        p:nth-child(1):before { content: '-' counter(p, none) '-'; }
        p:nth-child(2):before { content: counter(p, disc); }
        p:nth-child(3):before { content: counter(p, circle); }
        p:nth-child(4):before { content: counter(p, square); }
        p:nth-child(5):before { content: counter(p); }
        p:nth-child(6):before { content: var(--var) ':' counter(p); }
        p:nth-child(7):before { content: counter(p) ':' var(--var); }
      </style>
      <p></p>
      <p></p>
      <p></p>
      <p></p>
      <p></p>
      <p></p>
      <p></p>
    '''), [
        ('p', 'Block', [
            ('p', 'Line', [
                ('p::before', 'Inline', [
                    ('p::before', 'Text', counter)])])])
        for counter in '--  •  ◦  ▪  -7 Counter:-6 -5:Counter'.split()])


@assert_no_logs
def test_counter_styles_2():
    assert_tree(parse_all('''
      <style>
        p { counter-increment: p }
        p::before { content: counter(p, decimal-leading-zero); }
      </style>
      <p style="counter-reset: p -1987"></p>
      <p></p>
      <p style="counter-reset: p -12"></p>
      <p></p>
      <p></p>
      <p></p>
      <p style="counter-reset: p -2"></p>
      <p></p>
      <p></p>
      <p></p>
      <p style="counter-reset: p 8"></p>
      <p></p>
      <p></p>
      <p style="counter-reset: p 98"></p>
      <p></p>
      <p></p>
      <p style="counter-reset: p 4134"></p>
      <p></p>
    '''), [
        ('p', 'Block', [
            ('p', 'Line', [
                ('p::before', 'Inline', [
                    ('p::before', 'Text', counter)])])])
        for counter in '''-1986 -1985  -11 -10 -9 -8  -1 00 01 02  09 10 11
                            99 100 101  4135 4136'''.split()])


@assert_no_logs
def test_counter_styles_3():
    render = HTML(string='')._ua_counter_style()[0].render_value
    assert [render(value, 'decimal-leading-zero') for value in [
        -1986, -1985,
        -11, -10, -9, -8,
        -1, 0, 1, 2,
        9, 10, 11,
        99, 100, 101,
        4135, 4136
    ]] == '''
        -1986 -1985  -11 -10 -9 -8  -1 00 01 02  09 10 11
        99 100 101  4135 4136
    '''.split()


@assert_no_logs
def test_counter_styles_4():
    render = HTML(string='')._ua_counter_style()[0].render_value
    assert [render(value, 'lower-roman') for value in [
        -1986, -1985,
        -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
        49, 50,
        389, 390,
        3489, 3490, 3491,
        4999, 5000, 5001
     ]] == '''
        -1986 -1985  -1 0 i ii iii iv v vi vii viii ix x xi xii
        xlix l  ccclxxxix cccxc  mmmcdlxxxix mmmcdxc mmmcdxci
        4999 5000 5001
    '''.split()


@assert_no_logs
def test_counter_styles_5():
    render = HTML(string='')._ua_counter_style()[0].render_value
    assert [render(value, 'upper-roman') for value in [
         -1986, -1985,
         -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
         49, 50,
         389, 390,
         3489, 3490, 3491,
         4999, 5000, 5001
    ]] == '''
        -1986 -1985  -1 0 I II III IV V VI VII VIII IX X XI XII
        XLIX L  CCCLXXXIX CCCXC  MMMCDLXXXIX MMMCDXC MMMCDXCI
        4999 5000 5001
    '''.split()


@assert_no_logs
def test_counter_styles_6():
    render = HTML(string='')._ua_counter_style()[0].render_value
    assert [render(value, 'lower-alpha') for value in [
        -1986, -1985,
        -1, 0, 1, 2, 3, 4,
        25, 26, 27, 28, 29,
        2002, 2003
    ]] == '''
        -1986 -1985  -1 0 a b c d  y z aa ab ac bxz bya
    '''.split()


@assert_no_logs
def test_counter_styles_7():
    render = HTML(string='')._ua_counter_style()[0].render_value
    assert [render(value, 'upper-alpha') for value in [
        -1986, -1985,
        -1, 0, 1, 2, 3, 4,
        25, 26, 27, 28, 29,
        2002, 2003
    ]] == '''
        -1986 -1985  -1 0 A B C D  Y Z AA AB AC BXZ BYA
    '''.split()


@assert_no_logs
def test_counter_styles_8():
    render = HTML(string='')._ua_counter_style()[0].render_value
    assert [render(value, 'lower-latin') for value in [
        -1986, -1985,
        -1, 0, 1, 2, 3, 4,
        25, 26, 27, 28, 29,
        2002, 2003
    ]] == '''
        -1986 -1985  -1 0 a b c d  y z aa ab ac bxz bya
    '''.split()


@assert_no_logs
def test_counter_styles_9():
    render = HTML(string='')._ua_counter_style()[0].render_value
    assert [render(value, 'upper-latin') for value in [
        -1986, -1985,
        -1, 0, 1, 2, 3, 4,
        25, 26, 27, 28, 29,
        2002, 2003
    ]] == '''
        -1986 -1985  -1 0 A B C D  Y Z AA AB AC BXZ BYA
    '''.split()


@assert_no_logs
def test_counter_styles_10():
    render = HTML(string='')._ua_counter_style()[0].render_value
    assert [render(value, 'georgian') for value in [
        -1986, -1985,
        -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
        20, 30, 40, 50, 60, 70, 80, 90, 100,
        200, 300, 400, 500, 600, 700, 800, 900, 1000,
        2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000,
        19999, 20000, 20001
    ]] == '''
        -1986 -1985  -1 0 ა
        ბ გ დ ე ვ ზ ჱ თ ი ია იბ
        კ ლ მ ნ ჲ ო პ ჟ რ
        ს ტ ჳ ფ ქ ღ ყ შ ჩ
        ც ძ წ ჭ ხ ჴ ჯ ჰ ჵ
        ჵჰშჟთ 20000 20001
    '''.split()


@assert_no_logs
def test_counter_styles_11():
    render = HTML(string='')._ua_counter_style()[0].render_value
    assert [render(value, 'armenian') for value in [
        -1986, -1985,
        -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
        20, 30, 40, 50, 60, 70, 80, 90, 100,
        200, 300, 400, 500, 600, 700, 800, 900, 1000,
        2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000,
        9999, 10000, 10001
    ]] == '''
        -1986 -1985  -1 0 Ա
        Բ Գ Դ Ե Զ Է Ը Թ Ժ ԺԱ ԺԲ
        Ի Լ Խ Ծ Կ Հ Ձ Ղ Ճ
        Մ Յ Ն Շ Ո Չ Պ Ջ Ռ
        Ս Վ Տ Ր Ց Ւ Փ Ք
        ՔՋՂԹ 10000 10001
    '''.split()


@assert_no_logs
@pytest.mark.parametrize('arguments, values', (
    ('cyclic "a" "b" "c"', ('a ', 'b ', 'c ', 'a ')),
    ('symbolic "a" "b"', ('a ', 'b ', 'aa ', 'bb ')),
    ('"a" "b"', ('a ', 'b ', 'aa ', 'bb ')),
    ('alphabetic "a" "b"', ('a ', 'b ', 'aa ', 'ab ')),
    ('fixed "a" "b"', ('a ', 'b ', '3 ', '4 ')),
    ('numeric "0" "1" "2"', ('1 ', '2 ', '10 ', '11 ')),
))
def test_counter_symbols(arguments, values):
    page, = render_pages('''
      <style>
        ol { list-style-type: symbols(%s) }
      </style>
      <ol>
        <li>abc</li>
        <li>abc</li>
        <li>abc</li>
        <li>abc</li>
      </ol>
    ''' % arguments)
    html, = page.children
    body, = html.children
    ol, = body.children
    li_1, li_2, li_3, li_4 = ol.children
    assert li_1.children[0].children[0].children[0].text == values[0]
    assert li_2.children[0].children[0].children[0].text == values[1]
    assert li_3.children[0].children[0].children[0].text == values[2]
    assert li_4.children[0].children[0].children[0].text == values[3]


@assert_no_logs
@pytest.mark.parametrize('style_type, values', (
    ('decimal', ('1. ', '2. ', '3. ', '4. ')),
    ('"/"', ('/', '/', '/', '/')),
))
def test_list_style_types(style_type, values):
    page, = render_pages('''
      <style>
        ol { list-style-type: %s }
      </style>
      <ol>
        <li>abc</li>
        <li>abc</li>
        <li>abc</li>
        <li>abc</li>
      </ol>
    ''' % style_type)
    html, = page.children
    body, = html.children
    ol, = body.children
    li_1, li_2, li_3, li_4 = ol.children
    assert li_1.children[0].children[0].children[0].text == values[0]
    assert li_2.children[0].children[0].children[0].text == values[1]
    assert li_3.children[0].children[0].children[0].text == values[2]
    assert li_4.children[0].children[0].children[0].text == values[3]


def test_counter_set():
    page, = render_pages('''
      <style>
        body { counter-reset: h2 0 h3 4; font-size: 1px }
        article { counter-reset: h2 2 }
        h1 { counter-increment: h1 }
        h1::before { content: counter(h1) }
        h2 { counter-increment: h2; counter-set: h3 3 }
        h2::before { content: counter(h2) }
        h3 { counter-increment: h3 }
        h3::before { content: counter(h3) }
      </style>
      <article>
        <h1></h1>
      </article>
      <article>
        <h2></h2>
        <h3></h3>
      </article>
      <article>
        <h3></h3>
      </article>
      <article>
        <h2></h2>
      </article>
      <article>
        <h3></h3>
        <h3></h3>
      </article>
      <article>
        <h1></h1>
        <h2></h2>
        <h3></h3>
      </article>
    ''')
    html, = page.children
    body, = html.children
    art_1, art_2, art_3, art_4, art_5, art_6 = body.children

    h1, = art_1.children
    assert h1.children[0].children[0].children[0].text == '1'

    h2, h3, = art_2.children
    assert h2.children[0].children[0].children[0].text == '3'
    assert h3.children[0].children[0].children[0].text == '4'

    h3, = art_3.children
    assert h3.children[0].children[0].children[0].text == '5'

    h2, = art_4.children
    assert h2.children[0].children[0].children[0].text == '3'

    h3_1, h3_2 = art_5.children
    assert h3_1.children[0].children[0].children[0].text == '4'
    assert h3_2.children[0].children[0].children[0].text == '5'

    h1, h2, h3 = art_6.children
    assert h1.children[0].children[0].children[0].text == '1'
    assert h2.children[0].children[0].children[0].text == '3'
    assert h3.children[0].children[0].children[0].text == '4'


def test_counter_multiple_extends():
    # Inspired by W3C failing test system-extends-invalid
    page, = render_pages('''
      <style>
        @counter-style a {
          system: extends b;
          prefix: a;
        }
        @counter-style b {
          system: extends c;
          suffix: b;
        }
        @counter-style c {
          system: extends b;
          pad: 2 c;
        }
        @counter-style d {
          system: extends d;
          prefix: d;
        }
        @counter-style e {
          system: extends unknown;
          prefix: e;
        }
        @counter-style f {
          system: extends decimal;
          symbols: a;
        }
        @counter-style g {
          system: extends decimal;
          additive-symbols: 1 a;
        }
      </style>
      <ol>
        <li style="list-style-type: a"></li>
        <li style="list-style-type: b"></li>
        <li style="list-style-type: c"></li>
        <li style="list-style-type: d"></li>
        <li style="list-style-type: e"></li>
        <li style="list-style-type: f"></li>
        <li style="list-style-type: g"></li>
        <li style="list-style-type: h"></li>
      </ol>
    ''')
    html, = page.children
    body, = html.children
    ol, = body.children
    li_1, li_2, li_3, li_4, li_5, li_6, li_7, li_8 = ol.children
    assert li_1.children[0].children[0].children[0].text == 'a1b'
    assert li_2.children[0].children[0].children[0].text == '2b'
    assert li_3.children[0].children[0].children[0].text == 'c3. '
    assert li_4.children[0].children[0].children[0].text == 'd4. '
    assert li_5.children[0].children[0].children[0].text == 'e5. '
    assert li_6.children[0].children[0].children[0].text == '6. '
    assert li_7.children[0].children[0].children[0].text == '7. '
    assert li_8.children[0].children[0].children[0].text == '8. '
