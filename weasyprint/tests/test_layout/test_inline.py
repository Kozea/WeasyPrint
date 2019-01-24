"""
    weasyprint.tests.layout.inline
    ------------------------------

    Tests for inline layout.

    :copyright: Copyright 2011-2018 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import pytest

from ...formatting_structure import boxes
from ..test_boxes import render_pages as parse
from ..testing_utils import SANS_FONTS, assert_no_logs


@assert_no_logs
def test_empty_linebox():
    page, = parse('<p> </p>')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    assert len(paragraph.children) == 0
    assert paragraph.height == 0


@pytest.mark.xfail
@assert_no_logs
def test_empty_linebox_removed_space():
    # Whitespace removed at the beginning of the line => empty line => no line
    page, = parse('''
      <style>
        p { width: 1px }
      </style>
      <p><br>  </p>
    ''')
    page, = parse('<p> </p>')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    # TODO: The second line should be removed
    assert len(paragraph.children) == 1


@assert_no_logs
def test_breaking_linebox():
    page, = parse('''
      <style>
      p { font-size: 13px;
          width: 300px;
          font-family: %(fonts)s;
          background-color: #393939;
          color: #FFFFFF;
          line-height: 1;
          text-decoration: underline overline line-through;}
      </style>
      <p><em>Lorem<strong> Ipsum <span>is very</span>simply</strong><em>
      dummy</em>text of the printing and. naaaa </em> naaaa naaaa naaaa
      naaaa naaaa naaaa naaaa naaaa</p>
    ''' % {'fonts': SANS_FONTS})
    html, = page.children
    body, = html.children
    paragraph, = body.children
    assert len(list(paragraph.children)) == 3

    lines = paragraph.children
    for line in lines:
        assert line.style['font_size'] == 13
        assert line.element_tag == 'p'
        for child in line.children:
            assert child.element_tag in ('em', 'p')
            assert child.style['font_size'] == 13
            if isinstance(child, boxes.ParentBox):
                for child_child in child.children:
                    assert child.element_tag in ('em', 'strong', 'span')
                    assert child.style['font_size'] == 13


@assert_no_logs
def test_position_x_ltr():
    page, = parse('''
      <style>
        span {
          padding: 0 10px 0 15px;
          margin: 0 2px 0 3px;
          border: 1px solid;
         }
      </style>
      <body><span>a<br>b<br>c</span>''')
    html, = page.children
    body, = html.children
    line1, line2, line3 = body.children
    span1, = line1.children
    assert span1.position_x == 0
    text1, br1 = span1.children
    assert text1.position_x == 15 + 3 + 1
    span2, = line2.children
    assert span2.position_x == 0
    text2, br2 = span2.children
    assert text2.position_x == 0
    span3, = line3.children
    assert span3.position_x == 0
    text3, = span3.children
    assert text3.position_x == 0


@assert_no_logs
def test_position_x_rtl():
    page, = parse('''
      <style>
        body {
          direction: rtl;
          width: 100px;
        }
        span {
          padding: 0 10px 0 15px;
          margin: 0 2px 0 3px;
          border: 1px solid;
         }
      </style>
      <body><span>a<br>b<br>c</span>''')
    html, = page.children
    body, = html.children
    line1, line2, line3 = body.children
    span1, = line1.children
    text1, br1 = span1.children
    assert span1.position_x == 100 - text1.width - (10 + 2 + 1)
    assert text1.position_x == 100 - text1.width - (10 + 2 + 1)
    span2, = line2.children
    text2, br2 = span2.children
    assert span2.position_x == 100 - text2.width
    assert text2.position_x == 100 - text2.width
    span3, = line3.children
    text3, = span3.children
    assert span3.position_x == 100 - text3.width - (15 + 3 + 1)
    assert text3.position_x == 100 - text3.width


@assert_no_logs
def test_breaking_linebox_regression_1():
    # See http://unicode.org/reports/tr14/
    page, = parse('<pre>a\nb\rc\r\nd\u2029e</pre>')
    html, = page.children
    body, = html.children
    pre, = body.children
    lines = pre.children
    texts = []
    for line in lines:
        text_box, = line.children
        texts.append(text_box.text)
    assert texts == ['a', 'b', 'c', 'd', 'e']


@assert_no_logs
def test_breaking_linebox_regression_2():
    html_sample = '''
      <style>
        @font-face { src: url(AHEM____.TTF); font-family: ahem }
      </style>
      <p style="width: %i.5em; font-family: ahem">ab
      <span style="padding-right: 1em; margin-right: 1em">c def</span>g
      hi</p>'''
    for i in range(16):
        page, = parse(html_sample % i)
        html, = page.children
        body, = html.children
        p, = body.children
        lines = p.children

        if i in (0, 1, 2, 3):
            line_1, line_2, line_3, line_4 = lines

            textbox_1, = line_1.children
            assert textbox_1.text == 'ab'

            span_1, = line_2.children
            textbox_1, = span_1.children
            assert textbox_1.text == 'c'

            span_1, textbox_2 = line_3.children
            textbox_1, = span_1.children
            assert textbox_1.text == 'def'
            assert textbox_2.text == 'g'

            textbox_1, = line_4.children
            assert textbox_1.text == 'hi'
        elif i in (4, 5, 6, 7, 8):
            line_1, line_2, line_3 = lines

            textbox_1, span_1 = line_1.children
            assert textbox_1.text == 'ab '
            textbox_2, = span_1.children
            assert textbox_2.text == 'c'

            span_1, textbox_2 = line_2.children
            textbox_1, = span_1.children
            assert textbox_1.text == 'def'
            assert textbox_2.text == 'g'

            textbox_1, = line_3.children
            assert textbox_1.text == 'hi'
        elif i in (9, 10):
            line_1, line_2 = lines

            textbox_1, span_1 = line_1.children
            assert textbox_1.text == 'ab '
            textbox_2, = span_1.children
            assert textbox_2.text == 'c'

            span_1, textbox_2 = line_2.children
            textbox_1, = span_1.children
            assert textbox_1.text == 'def'
            assert textbox_2.text == 'g hi'
        elif i in (11, 12, 13):
            line_1, line_2 = lines

            textbox_1, span_1, textbox_3 = line_1.children
            assert textbox_1.text == 'ab '
            textbox_2, = span_1.children
            assert textbox_2.text == 'c def'
            assert textbox_3.text == 'g'

            textbox_1, = line_2.children
            assert textbox_1.text == 'hi'
        else:
            line_1, = lines

            textbox_1, span_1, textbox_3 = line_1.children
            assert textbox_1.text == 'ab '
            textbox_2, = span_1.children
            assert textbox_2.text == 'c def'
            assert textbox_3.text == 'g hi'


@assert_no_logs
def test_breaking_linebox_regression_3():
    # Regression test #1 for https://github.com/Kozea/WeasyPrint/issues/560
    page, = parse(
      '<style>@font-face { src: url(AHEM____.TTF); font-family: ahem }</style>'
      '<div style="width: 5.5em; font-family: ahem">'
      'aaaa aaaa a [<span>aaa</span>]')
    html, = page.children
    body, = html.children
    div, = body.children
    line1, line2, line3, line4 = div.children
    assert line1.children[0].text == line2.children[0].text == 'aaaa'
    assert line3.children[0].text == 'a'
    text1, span, text2 = line4.children
    assert text1.text == '['
    assert text2.text == ']'
    assert span.children[0].text == 'aaa'


@assert_no_logs
def test_breaking_linebox_regression_4():
    # Regression test #2 for https://github.com/Kozea/WeasyPrint/issues/560
    page, = parse(
      '<style>@font-face { src: url(AHEM____.TTF); font-family: ahem }</style>'
      '<div style="width: 5.5em; font-family: ahem">'
      'aaaa a <span>b c</span>d')
    html, = page.children
    body, = html.children
    div, = body.children
    line1, line2, line3 = div.children
    assert line1.children[0].text == 'aaaa'
    assert line2.children[0].text == 'a '
    assert line2.children[1].children[0].text == 'b'
    assert line3.children[0].children[0].text == 'c'
    assert line3.children[1].text == 'd'


@assert_no_logs
def test_breaking_linebox_regression_5():
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/580
    page, = parse(
      '<style>@font-face { src: url(AHEM____.TTF); font-family: ahem }</style>'
      '<div style="width: 5.5em; font-family: ahem">'
      '<span>aaaa aaaa a a a</span><span>bc</span>')
    html, = page.children
    body, = html.children
    div, = body.children
    line1, line2, line3, line4 = div.children
    assert line1.children[0].children[0].text == 'aaaa'
    assert line2.children[0].children[0].text == 'aaaa'
    assert line3.children[0].children[0].text == 'a a'
    assert line4.children[0].children[0].text == 'a'
    assert line4.children[1].children[0].text == 'bc'


@assert_no_logs
def test_breaking_linebox_regression_6():
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/586
    page, = parse(
      '<style>@font-face { src: url(AHEM____.TTF); font-family: ahem }</style>'
      '<div style="width: 5.5em; font-family: ahem">'
      'a a <span style="white-space: nowrap">/ccc</span>')
    html, = page.children
    body, = html.children
    div, = body.children
    line1, line2 = div.children
    assert line1.children[0].text == 'a a'
    assert line2.children[0].children[0].text == '/ccc'


@assert_no_logs
def test_breaking_linebox_regression_7():
    # Regression test for https://github.com/Kozea/WeasyPrint/issues/660
    page, = parse(
      '<style>@font-face { src: url(AHEM____.TTF); font-family: ahem }</style>'
      '<div style="width: 3.5em; font-family: ahem">'
      '<span><span>abc d e</span></span><span>f')
    html, = page.children
    body, = html.children
    div, = body.children
    line1, line2, line3 = div.children
    assert line1.children[0].children[0].children[0].text == 'abc'
    assert line2.children[0].children[0].children[0].text == 'd'
    assert line3.children[0].children[0].children[0].text == 'e'
    assert line3.children[1].children[0].text == 'f'


@assert_no_logs
def test_linebox_text():
    page, = parse('''
      <style>
        p { width: 165px; font-family:%(fonts)s;}
      </style>
      <p><em>Lorem Ipsum</em>is very <strong>coool</strong></p>
    ''' % {'fonts': SANS_FONTS})
    html, = page.children
    body, = html.children
    paragraph, = body.children
    lines = list(paragraph.children)
    assert len(lines) == 2

    text = ' '.join(
        (''.join(box.text for box in line.descendants()
                 if isinstance(box, boxes.TextBox)))
        for line in lines)
    assert text == 'Lorem Ipsumis very coool'


@assert_no_logs
def test_linebox_positions():
    for width, expected_lines in [(165, 2), (1, 5), (0, 5)]:
        page = '''
          <style>
            p { width:%(width)spx; font-family:%(fonts)s;
                line-height: 20px }
          </style>
          <p>this is test for <strong>Weasyprint</strong></p>'''
        page, = parse(page % {'fonts': SANS_FONTS, 'width': width})
        html, = page.children
        body, = html.children
        paragraph, = body.children
        lines = list(paragraph.children)
        assert len(lines) == expected_lines

        ref_position_y = lines[0].position_y
        ref_position_x = lines[0].position_x
        for line in lines:
            assert ref_position_y == line.position_y
            assert ref_position_x == line.position_x
            for box in line.children:
                assert ref_position_x == box.position_x
                ref_position_x += box.width
                assert ref_position_y == box.position_y
            assert ref_position_x - line.position_x <= line.width
            ref_position_x = line.position_x
            ref_position_y += line.height


@assert_no_logs
def test_forced_line_breaks_pre():
    # These lines should be small enough to fit on the default A4 page
    # with the default 12pt font-size.
    page, = parse('''
      <style> pre { line-height: 42px }</style>
      <pre>Lorem ipsum dolor sit amet,
          consectetur adipiscing elit.


          Sed sollicitudin nibh

          et turpis molestie tristique.</pre>
    ''')
    html, = page.children
    body, = html.children
    pre, = body.children
    assert pre.element_tag == 'pre'
    lines = pre.children
    assert all(isinstance(line, boxes.LineBox) for line in lines)
    assert len(lines) == 7
    assert [line.height for line in lines] == [42] * 7


@assert_no_logs
def test_forced_line_breaks_paragraph():
    page, = parse('''
      <style> p { line-height: 42px }</style>
      <p>Lorem ipsum dolor sit amet,<br>
        consectetur adipiscing elit.<br><br><br>
        Sed sollicitudin nibh<br>
        <br>

        et turpis molestie tristique.</p>
    ''')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    assert paragraph.element_tag == 'p'
    lines = paragraph.children
    assert all(isinstance(line, boxes.LineBox) for line in lines)
    assert len(lines) == 7
    assert [line.height for line in lines] == [42] * 7


@assert_no_logs
def test_inlinebox_splitting():
    # The text is strange to test some corner cases
    # See https://github.com/Kozea/WeasyPrint/issues/389
    for width in [10000, 100, 10, 0]:
        page, = parse('''
          <style>p { font-family:%(fonts)s; width: %(width)spx; }</style>
          <p><strong>WeasyPrint is a frée softwäre ./ visual rendèring enginè
                     for HTML !!! and CSS.</strong></p>
        ''' % {'fonts': SANS_FONTS, 'width': width})
        html, = page.children
        body, = html.children
        paragraph, = body.children
        lines = paragraph.children
        if width == 10000:
            assert len(lines) == 1
        else:
            assert len(lines) > 1
        text_parts = []
        for line in lines:
            strong, = line.children
            text, = strong.children
            text_parts.append(text.text)
        assert ' '.join(text_parts) == (
            'WeasyPrint is a frée softwäre ./ visual '
            'rendèring enginè for HTML !!! and CSS.')


@assert_no_logs
def test_whitespace_processing():
    for source in ['a', '  a  ', ' \n  \ta', ' a\t ']:
        page, = parse('<p><em>%s</em></p>' % source)
        html, = page.children
        body, = html.children
        p, = body.children
        line, = p.children
        em, = line.children
        text, = em.children
        assert text.text == 'a', 'source was %r' % (source,)

        page, = parse(
            '<p style="white-space: pre-line">\n\n<em>%s</em></pre>' %
            source.replace('\n', ' '))
        html, = page.children
        body, = html.children
        p, = body.children
        _line1, _line2, line3 = p.children
        em, = line3.children
        text, = em.children
        assert text.text == 'a', 'source was %r' % (source,)


@assert_no_logs
def test_inline_replaced_auto_margins():
    page, = parse('''
      <style>
        @page { size: 200px }
        img { display: inline; margin: auto; width: 50px }
      </style>
      <body><img src="pattern.png" />''')
    html, = page.children
    body, = html.children
    line, = body.children
    img, = line.children
    assert img.margin_top == 0
    assert img.margin_right == 0
    assert img.margin_bottom == 0
    assert img.margin_left == 0


@assert_no_logs
def test_empty_inline_auto_margins():
    page, = parse('''
      <style>
        @page { size: 200px }
        span { margin: auto }
      </style>
      <body><span></span>''')
    html, = page.children
    body, = html.children
    block, = body.children
    span, = block.children
    assert span.margin_top != 0
    assert span.margin_right == 0
    assert span.margin_bottom != 0
    assert span.margin_left == 0


@assert_no_logs
def test_font_stretch():
    page, = parse('''
      <style>
        p { float: left; font-family: %s }
      </style>
      <p>Hello, world!</p>
      <p style="font-stretch: condensed">Hello, world!</p>
    ''' % SANS_FONTS)
    html, = page.children
    body, = html.children
    p_1, p_2 = body.children
    normal = p_1.width
    condensed = p_2.width
    assert condensed < normal


@assert_no_logs
@pytest.mark.parametrize('source, lines_count', (
    ('<body>hyphénation', 1),  # Default: no hyphenation
    ('<body lang=fr>hyphénation', 1),  # lang only: no hyphenation
    ('<body style="hyphens: auto">hyphénation', 1),  # hyphens only: no hyph.
    ('<body style="hyphens: auto" lang=fr>hyphénation', 2),  # both: hyph.
    ('<body>hyp&shy;hénation', 2),  # Hyphenation with soft hyphens
    ('<body style="hyphens: none">hyp&shy;hénation', 1),  # … unless disabled
))
def line_count(source, lines_count):
    page, = parse(
        '<html style="width: 5em; font-family: ahem">' +
        '<style>@font-face {src:url(AHEM____.TTF); font-family:ahem}</style>' +
        source)
    html, = page.children
    body, = html.children
    lines = body.children
    assert len(lines) == lines_count


@assert_no_logs
def test_vertical_align_1():
    #            +-------+      <- position_y = 0
    #      +-----+       |
    # 40px |     |       | 60px
    #      |     |       |
    #      +-----+-------+      <- baseline
    page, = parse('''
      <span>
        <img src="pattern.png" style="width: 40px"
        ><img src="pattern.png" style="width: 60px"
      ></span>''')
    html, = page.children
    body, = html.children
    line, = body.children
    span, = line.children
    img_1, img_2 = span.children
    assert img_1.height == 40
    assert img_2.height == 60
    assert img_1.position_y == 20
    assert img_2.position_y == 0
    # 60px + the descent of the font below the baseline
    assert 60 < line.height < 70
    assert body.height == line.height


@assert_no_logs
def test_vertical_align_2():
    #            +-------+      <- position_y = 0
    #       35px |       |
    #      +-----+       | 60px
    # 40px |     |       |
    #      |     +-------+      <- baseline
    #      +-----+  15px
    page, = parse('''
      <span>
        <img src="pattern.png" style="width: 40px; vertical-align: -15px"
        ><img src="pattern.png" style="width: 60px"></span>''')
    html, = page.children
    body, = html.children
    line, = body.children
    span, = line.children
    img_1, img_2 = span.children
    assert img_1.height == 40
    assert img_2.height == 60
    assert img_1.position_y == 35
    assert img_2.position_y == 0
    assert line.height == 75
    assert body.height == line.height


@assert_no_logs
def test_vertical_align_3():
    # Same as previously, but with percentages
    page, = parse('''
      <span style="line-height: 10px">
        <img src="pattern.png" style="width: 40px; vertical-align: -150%"
        ><img src="pattern.png" style="width: 60px"></span>''')
    html, = page.children
    body, = html.children
    line, = body.children
    span, = line.children
    img_1, img_2 = span.children
    assert img_1.height == 40
    assert img_2.height == 60
    assert img_1.position_y == 35
    assert img_2.position_y == 0
    assert line.height == 75
    assert body.height == line.height


@assert_no_logs
def test_vertical_align_4():
    # Same again, but have the vertical-align on an inline box.
    page, = parse('''
      <span style="line-height: 10px">
        <span style="line-height: 10px; vertical-align: -15px">
          <img src="pattern.png" style="width: 40px"></span>
        <img src="pattern.png" style="width: 60px"></span>''')
    html, = page.children
    body, = html.children
    line, = body.children
    span_1, = line.children
    span_2, _whitespace, img_2 = span_1.children
    img_1, = span_2.children
    assert img_1.height == 40
    assert img_2.height == 60
    assert img_1.position_y == 35
    assert img_2.position_y == 0
    assert line.height == 75
    assert body.height == line.height


@assert_no_logs
def test_vertical_align_5():
    # Same as previously, but with percentages
    page, = parse(
        '<style>@font-face {src: url(AHEM____.TTF); font-family: ahem}</style>'
        '<span style="line-height: 12px; font-size: 12px; font-family: ahem">'
        '<img src="pattern.png" style="width: 40px; vertical-align: middle">'
        '<img src="pattern.png" style="width: 60px"></span>''')
    html, = page.children
    body, = html.children
    line, = body.children
    span, = line.children
    img_1, img_2 = span.children
    assert img_1.height == 40
    assert img_2.height == 60
    # middle of the image (position_y + 20) is at half the ex-height above
    # the baseline of the parent. The ex-height of Ahem is something like 0.8em
    # TODO: ex unit doesn't work with @font-face fonts, see computed_values.py
    # assert img_1.position_y == 35.2  # 60 - 0.5 * 0.8 * font-size - 40/2
    assert img_2.position_y == 0
    # assert line.height == 75.2
    assert body.height == line.height


@assert_no_logs
def test_vertical_align_6():
    # sup and sub currently mean +/- 0.5 em
    # With the initial 16px font-size, that’s 8px.
    page, = parse('''
      <span style="line-height: 10px">
        <img src="pattern.png" style="width: 60px"
        ><img src="pattern.png" style="width: 40px; vertical-align: super"
        ><img src="pattern.png" style="width: 40px; vertical-align: sub"
      ></span>''')
    html, = page.children
    body, = html.children
    line, = body.children
    span, = line.children
    img_1, img_2, img_3 = span.children
    assert img_1.height == 60
    assert img_2.height == 40
    assert img_3.height == 40
    assert img_1.position_y == 0
    assert img_2.position_y == 12  # 20 - 16 * 0.5
    assert img_3.position_y == 28  # 20 + 16 * 0.5
    assert line.height == 68
    assert body.height == line.height


@assert_no_logs
def test_vertical_align_7():
    page, = parse('''
      <body style="line-height: 10px">
        <span>
          <img src="pattern.png" style="vertical-align: text-top"
          ><img src="pattern.png" style="vertical-align: text-bottom"
        ></span>''')
    html, = page.children
    body, = html.children
    line, = body.children
    span, = line.children
    img_1, img_2 = span.children
    assert img_1.height == 4
    assert img_2.height == 4
    assert img_1.position_y == 0
    assert img_2.position_y == 12  # 16 - 4
    assert line.height == 16
    assert body.height == line.height


@assert_no_logs
def test_vertical_align_8():
    # This case used to cause an exception:
    # The second span has no children but should count for line heights
    # since it has padding.
    page, = parse('''<span style="line-height: 1.5">
      <span style="padding: 1px"></span></span>''')
    html, = page.children
    body, = html.children
    line, = body.children
    span_1, = line.children
    span_2, = span_1.children
    assert span_1.height == 16
    assert span_2.height == 16
    # The line’s strut does not has 'line-height: normal' but the result should
    # be smaller than 1.5.
    assert span_1.margin_height() == 24
    assert span_2.margin_height() == 24
    assert line.height == 24


@assert_no_logs
def test_vertical_align_9():
    page, = parse('''
      <span>
        <img src="pattern.png" style="width: 40px; vertical-align: -15px"
        ><img src="pattern.png" style="width: 60px"
      ></span><div style="display: inline-block; vertical-align: 3px">
        <div>
          <div style="height: 100px">foo</div>
          <div>
            <img src="pattern.png" style="
                 width: 40px; vertical-align: -15px"
            ><img src="pattern.png" style="width: 60px"
          ></div>
        </div>
      </div>''')
    html, = page.children
    body, = html.children
    line, = body.children
    span, div_1 = line.children
    assert line.height == 178
    assert body.height == line.height

    # Same as earlier
    img_1, img_2 = span.children
    assert img_1.height == 40
    assert img_2.height == 60
    assert img_1.position_y == 138
    assert img_2.position_y == 103

    div_2, = div_1.children
    div_3, div_4 = div_2.children
    div_line, = div_4.children
    div_img_1, div_img_2 = div_line.children
    assert div_1.position_y == 0
    assert div_1.height == 175
    assert div_3.height == 100
    assert div_line.height == 75
    assert div_img_1.height == 40
    assert div_img_2.height == 60
    assert div_img_1.position_y == 135
    assert div_img_2.position_y == 100


@assert_no_logs
def test_vertical_align_10():
    # The first two images bring the top of the line box 30px above
    # the baseline and 10px below.
    # Each of the inner span
    page, = parse('''
      <span style="font-size: 0">
        <img src="pattern.png" style="vertical-align: 26px">
        <img src="pattern.png" style="vertical-align: -10px">
        <span style="vertical-align: top">
          <img src="pattern.png" style="vertical-align: -10px">
          <span style="vertical-align: -10px">
            <img src="pattern.png" style="vertical-align: bottom">
          </span>
        </span>
        <span style="vertical-align: bottom">
          <img src="pattern.png" style="vertical-align: 6px">
        </span>
      </span>''')
    html, = page.children
    body, = html.children
    line, = body.children
    span_1, = line.children
    img_1, img_2, span_2, span_4 = span_1.children
    img_3, span_3 = span_2.children
    img_4, = span_3.children
    img_5, = span_4.children
    assert body.height == line.height
    assert line.height == 40
    assert img_1.position_y == 0
    assert img_2.position_y == 36
    assert img_3.position_y == 6
    assert img_4.position_y == 36
    assert img_5.position_y == 30


@assert_no_logs
def test_vertical_align_11():
    page, = parse('''
      <span style="font-size: 0">
        <img src="pattern.png" style="vertical-align: bottom">
        <img src="pattern.png" style="vertical-align: top; height: 100px">
      </span>
    ''')
    html, = page.children
    body, = html.children
    line, = body.children
    span, = line.children
    img_1, img_2 = span.children
    assert img_1.position_y == 96
    assert img_2.position_y == 0


@assert_no_logs
def test_vertical_align_12():
    # Reference for the next test
    page, = parse('''
      <span style="font-size: 0; vertical-align: top">
        <img src="pattern.png">
      </span>
    ''')
    html, = page.children
    body, = html.children
    line, = body.children
    span, = line.children
    img_1, = span.children
    assert img_1.position_y == 0


@assert_no_logs
def test_vertical_align_13():
    # Should be the same as above
    page, = parse('''
      <span style="font-size: 0; vertical-align: top; display: inline-block">
        <img src="pattern.png">
      </span>''')
    html, = page.children
    body, = html.children
    line_1, = body.children
    span, = line_1.children
    line_2, = span.children
    img_1, = line_2.children
    assert img_1.element_tag == 'img'
    assert img_1.position_y == 0
