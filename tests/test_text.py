"""Test the text layout."""

import pytest
from weasyprint.css.properties import INITIAL_VALUES
from weasyprint.formatting_structure.build import capitalize
from weasyprint.text.line_break import split_first_line

from .testing_utils import MONO_FONTS, SANS_FONTS, assert_no_logs, render_pages


def make_text(text, width=None, **style):
    """Wrapper for split_first_line() creating a style dict."""
    new_style = INITIAL_VALUES.copy()
    new_style['font_family'] = MONO_FONTS.split(',')
    new_style.update(style)
    return split_first_line(
        text, new_style, context=None, max_width=width,
        justification_spacing=0)


@assert_no_logs
def test_line_content():
    for width, remaining in [(100, 'text for test'),
                             (45, 'is a text for test')]:
        text = 'This is a text for test'
        _, length, resume_index, _, _, _ = make_text(
            text, width, font_family=SANS_FONTS.split(','), font_size=19)
        assert text[resume_index:] == remaining
        assert length + 1 == resume_index  # +1 for the removed trailing space


@assert_no_logs
def test_line_with_any_width():
    _, _, _, width_1, _, _ = make_text('some text')
    _, _, _, width_2, _, _ = make_text('some text some text')
    assert width_1 < width_2


@assert_no_logs
def test_line_breaking():
    string = 'Thïs is a text for test'

    # These two tests do not really rely on installed fonts
    _, _, resume_index, _, _, _ = make_text(string, 90, font_size=1)
    assert resume_index is None

    _, _, resume_index, _, _, _ = make_text(string, 90, font_size=100)
    assert string.encode()[resume_index:].decode() == 'is a text for test'

    _, _, resume_index, _, _, _ = make_text(
        string, 100, font_family=SANS_FONTS.split(','), font_size=19)
    assert string.encode()[resume_index:].decode() == 'text for test'


@assert_no_logs
def test_line_breaking_rtl():
    string = 'لوريم ايبسوم دولا'

    # These two tests do not really rely on installed fonts
    _, _, resume_index, _, _, _ = make_text(string, 90, font_size=1)
    assert resume_index is None

    _, _, resume_index, _, _, _ = make_text(string, 90, font_size=100)
    assert string.encode()[resume_index:].decode() == 'ايبسوم دولا'


@assert_no_logs
def test_line_breaking_nbsp():
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/1561
    page, = render_pages('''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        body { font-family: weasyprint; width: 7.5em }
      </style>
      <body>a <span>b</span> c d&nbsp;<span>ef
    ''')
    html, = page.children
    body, = html.children
    line_1, line_2 = body.children
    assert line_1.children[0].text == 'a '
    assert line_1.children[1].children[0].text == 'b'
    assert line_1.children[2].text == ' c'
    assert line_2.children[0].text == 'd\xa0'
    assert line_2.children[1].children[0].text == 'ef'


@assert_no_logs
def test_text_dimension():
    string = 'This is a text for test. This is a test for text.py'
    _, _, _, width_1, height_1, _ = make_text(string, 200, font_size=12)

    _, _, _, width_2, height_2, _ = make_text(string, 200, font_size=20)
    assert width_1 * height_1 < width_2 * height_2


@assert_no_logs
def test_text_font_size_zero():
    page, = render_pages('''
      <style>
        p { font-size: 0; }
      </style>
      <p>test font size zero</p>
    ''')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    line, = paragraph.children
    # zero-sized text boxes are removed
    assert not line.children
    assert line.height == 0
    assert paragraph.height == 0


@assert_no_logs
def test_text_font_size_very_small():
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/1499
    page, = render_pages('''
      <style>
        p { font-size: 0.00000001px }
      </style>
      <p>test font size zero</p>
    ''')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    line, = paragraph.children
    assert line.height < 0.001
    assert paragraph.height < 0.001


@assert_no_logs
def test_text_spaced_inlines():
    page, = render_pages('''
      <p>start <i><b>bi1</b> <b>bi2</b></i> <b>b1</b> end</p>
    ''')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    line, = paragraph.children
    start, i, space, b, end = line.children
    assert start.text == 'start '
    assert space.text == ' '
    assert space.width > 0
    assert end.text == ' end'

    bi1, space, bi2 = i.children
    bi1, = bi1.children
    bi2, = bi2.children
    assert bi1.text == 'bi1'
    assert space.text == ' '
    assert space.width > 0
    assert bi2.text == 'bi2'

    b1, = b.children
    assert b1.text == 'b1'


@assert_no_logs
def test_text_align_left():
    # <-------------------->  page, body
    #     +-----+
    # +---+     |
    # |   |     |
    # +---+-----+

    # ^   ^     ^          ^
    # x=0 x=40  x=100      x=200
    page, = render_pages('''
      <style>
        @page { size: 200px }
      </style>
      <body>
        <img src="pattern.png" style="width: 40px"
        ><img src="pattern.png" style="width: 60px">''')
    html, = page.children
    body, = html.children
    line, = body.children
    img_1, img_2 = line.children
    # initial value for text-align: left (in ltr text)
    assert img_1.position_x == 0
    assert img_2.position_x == 40


@assert_no_logs
def test_text_align_right():
    # <-------------------->  page, body
    #                +-----+
    #            +---+     |
    #            |   |     |
    #            +---+-----+

    # ^          ^   ^     ^
    # x=0        x=100     x=200
    #                x=140
    page, = render_pages('''
      <style>
        @page { size: 200px }
        body { text-align: right }
      </style>
      <body>
        <img src="pattern.png" style="width: 40px"
        ><img src="pattern.png" style="width: 60px">''')
    html, = page.children
    body, = html.children
    line, = body.children
    img_1, img_2 = line.children
    assert img_1.position_x == 100  # 200 - 60 - 40
    assert img_2.position_x == 140  # 200 - 60


@assert_no_logs
def test_text_align_center():
    # <-------------------->  page, body
    #           +-----+
    #       +---+     |
    #       |   |     |
    #       +---+-----+

    # ^     ^   ^     ^
    # x=    x=50     x=150
    #           x=90
    page, = render_pages('''
      <style>
        @page { size: 200px }
        body { text-align: center }
      </style>
      <body>
        <img src="pattern.png" style="width: 40px"
        ><img src="pattern.png" style="width: 60px">''')
    html, = page.children
    body, = html.children
    line, = body.children
    img_1, img_2 = line.children
    assert img_1.position_x == 50
    assert img_2.position_x == 90


@assert_no_logs
def test_text_align_justify():
    page, = render_pages('''
      <style>
        @page { size: 300px 1000px }
        body { text-align: justify }
      </style>
      <p><img src="pattern.png" style="width: 40px">
        <strong>
          <img src="pattern.png" style="width: 60px">
          <img src="pattern.png" style="width: 10px">
          <img src="pattern.png" style="width: 100px"
        ></strong><img src="pattern.png" style="width: 290px"
        ><!-- Last image will be on its own line. -->''')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    line_1, line_2 = paragraph.children
    image_1, space_1, strong = line_1.children
    image_2, space_2, image_3, space_3, image_4 = strong.children
    image_5, = line_2.children
    assert space_1.text == ' '
    assert space_2.text == ' '
    assert space_3.text == ' '

    assert image_1.position_x == 0
    assert space_1.position_x == 40
    assert strong.position_x == 70
    assert image_2.position_x == 70
    assert space_2.position_x == 130
    assert image_3.position_x == 160
    assert space_3.position_x == 170
    assert image_4.position_x == 200
    assert strong.width == 230

    assert image_5.position_x == 0


@assert_no_logs
def test_text_align_justify_all():
    page, = render_pages('''
      <style>
        @page { size: 300px 1000px }
        body { text-align: justify-all }
      </style>
      <p><img src="pattern.png" style="width: 40px">
        <strong>
          <img src="pattern.png" style="width: 60px">
          <img src="pattern.png" style="width: 10px">
          <img src="pattern.png" style="width: 100px"
        ></strong><img src="pattern.png" style="width: 200px">
        <img src="pattern.png" style="width: 10px">''')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    line_1, line_2 = paragraph.children
    image_1, space_1, strong = line_1.children
    image_2, space_2, image_3, space_3, image_4 = strong.children
    image_5, space_4, image_6 = line_2.children
    assert space_1.text == ' '
    assert space_2.text == ' '
    assert space_3.text == ' '
    assert space_4.text == ' '

    assert image_1.position_x == 0
    assert space_1.position_x == 40
    assert strong.position_x == 70
    assert image_2.position_x == 70
    assert space_2.position_x == 130
    assert image_3.position_x == 160
    assert space_3.position_x == 170
    assert image_4.position_x == 200
    assert strong.width == 230

    assert image_5.position_x == 0
    assert space_4.position_x == 200
    assert image_6.position_x == 290


@assert_no_logs
def test_text_align_all_last():
    page, = render_pages('''
      <style>
        @page { size: 300px 1000px }
        body { text-align-all: justify; text-align-last: right }
      </style>
      <p><img src="pattern.png" style="width: 40px">
        <strong>
          <img src="pattern.png" style="width: 60px">
          <img src="pattern.png" style="width: 10px">
          <img src="pattern.png" style="width: 100px"
        ></strong><img src="pattern.png" style="width: 200px"
        ><img src="pattern.png" style="width: 10px">''')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    line_1, line_2 = paragraph.children
    image_1, space_1, strong = line_1.children
    image_2, space_2, image_3, space_3, image_4 = strong.children
    image_5, image_6 = line_2.children
    assert space_1.text == ' '
    assert space_2.text == ' '
    assert space_3.text == ' '

    assert image_1.position_x == 0
    assert space_1.position_x == 40
    assert strong.position_x == 70
    assert image_2.position_x == 70
    assert space_2.position_x == 130
    assert image_3.position_x == 160
    assert space_3.position_x == 170
    assert image_4.position_x == 200
    assert strong.width == 230

    assert image_5.position_x == 90
    assert image_6.position_x == 290


@assert_no_logs
def test_text_align_not_enough_space():
    page, = render_pages('''
      <style>
        p { text-align: center; width: 0 }
        span { display: inline-block }
      </style>
      <p><span>aaaaaaaaaaaaaaaaaaaaaaaaaa</span></p>''')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    span, = paragraph.children
    assert span.position_x == 0


@assert_no_logs
def test_text_align_justify_no_space():
    # single-word line (zero spaces)
    page, = render_pages('''
      <style>
        body { text-align: justify; width: 50px }
      </style>
      <p>Supercalifragilisticexpialidocious bar</p>
    ''')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    line_1, line_2 = paragraph.children
    text, = line_1.children
    assert text.position_x == 0


@assert_no_logs
def test_text_align_justify_text_indent():
    # text-indent
    page, = render_pages('''
      <style>
        @page { size: 300px 1000px }
        body { text-align: justify }
        p { text-indent: 3px }
      </style>
      <p><img src="pattern.png" style="width: 40px">
        <strong>
          <img src="pattern.png" style="width: 60px">
          <img src="pattern.png" style="width: 10px">
          <img src="pattern.png" style="width: 100px"
        ></strong><img src="pattern.png" style="width: 290px"
        ><!-- Last image will be on its own line. -->''')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    line_1, line_2 = paragraph.children
    image_1, space_1, strong = line_1.children
    image_2, space_2, image_3, space_3, image_4 = strong.children
    image_5, = line_2.children
    assert space_1.text == ' '
    assert space_2.text == ' '
    assert space_3.text == ' '

    assert image_1.position_x == 3
    assert space_1.position_x == 43
    assert strong.position_x == 72
    assert image_2.position_x == 72
    assert space_2.position_x == 132
    assert image_3.position_x == 161
    assert space_3.position_x == 171
    assert image_4.position_x == 200
    assert strong.width == 228

    assert image_5.position_x == 0


@assert_no_logs
def test_text_align_justify_no_break_between_children():
    # Test justification when line break happens between two inline children
    # that must stay together.
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/637
    page, = render_pages('''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        p { text-align: justify; font-family: weasyprint; width: 7em }
      </style>
      <p>
        <span>a</span>
        <span>b</span>
        <span>bla</span><span>,</span>
        <span>b</span>
      </p>
    ''')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    line_1, line_2 = paragraph.children

    span_1, space_1, span_2, space_2 = line_1.children
    assert span_1.position_x == 0
    assert span_2.position_x == 6 * 16  # 1 character + 5 spaces
    assert line_1.width == 7 * 16  # 7em

    span_1, span_2, space_1, span_3, space_2 = line_2.children
    assert span_1.position_x == 0
    assert span_2.position_x == 3 * 16  # 3 characters
    assert span_3.position_x == 5 * 16  # (3 + 1) characters + 1 space


@pytest.mark.parametrize('text', (
    'Lorem ipsum dolor<em>sit amet</em>',
    'Lorem ipsum <em>dolorsit</em> amet',
    'Lorem ipsum <em></em>dolorsit amet',
    'Lorem ipsum<em> </em>dolorsit amet',
    'Lorem ipsum<em> dolorsit</em> amet',
    'Lorem ipsum <em>dolorsit </em>amet',
))
@assert_no_logs
def test_word_spacing(text):
    # keep the empty <style> as a regression test: element.text is None
    # (Not a string.)
    page, = render_pages('''
      <style></style>
      <body><strong>Lorem ipsum dolor<em>sit amet</em></strong>''')
    html, = page.children
    body, = html.children
    line, = body.children
    strong_1, = line.children

    page, = render_pages('''
      <style>strong { word-spacing: 11px }</style>
      <body><strong>%s</strong>''' % text)
    html, = page.children
    body, = html.children
    line, = body.children
    strong_2, = line.children

    assert strong_2.width - strong_1.width == 33


@assert_no_logs
def test_letter_spacing_1():
    page, = render_pages('''
        <body><strong>Supercalifragilisticexpialidocious</strong>''')
    html, = page.children
    body, = html.children
    line, = body.children
    strong_1, = line.children

    page, = render_pages('''
        <style>strong { letter-spacing: 11px }</style>
        <body><strong>Supercalifragilisticexpialidocious</strong>''')
    html, = page.children
    body, = html.children
    line, = body.children
    strong_2, = line.children
    assert strong_2.width - strong_1.width == 34 * 11

    # an embedded tag should not affect the single-line letter spacing
    page, = render_pages(
        '<style>strong { letter-spacing: 11px }</style>'
        '<body><strong>Supercali<span>fragilistic</span>expialidocious'
        '</strong>')
    html, = page.children
    body, = html.children
    line, = body.children
    strong_3, = line.children
    assert strong_3.width == strong_2.width

    # duplicate wrapped lines should also have same overall width
    # Note work-around for word-wrap bug (issue #163) by marking word
    # as an inline-block
    page, = render_pages(
        '<style>'
        '  strong {'
        '    letter-spacing: 11px;'
        f'    max-width: {strong_3.width * 1.5}px'
        '}'
        '  span { display: inline-block }'
        '</style>'
        '<body><strong>'
        '  <span>Supercali<i>fragilistic</i>expialidocious</span> '
        '  <span>Supercali<i>fragilistic</i>expialidocious</span>'
        '</strong>')
    html, = page.children
    body, = html.children
    line1, line2 = body.children
    assert line1.children[0].width == line2.children[0].width
    assert line1.children[0].width == strong_2.width


@pytest.mark.parametrize('spacing', ('word-spacing', 'letter-spacing'))
@assert_no_logs
def test_spacing_ex(spacing):
    # Test regression on ex units in spacing properties
    render_pages(f'<div style="{spacing}: 2ex">abc def')


@pytest.mark.parametrize('indent', ('12px', '6%'))
@assert_no_logs
def test_text_indent(indent):
    page, = render_pages('''
        <style>
            @page { size: 220px }
            body { margin: 10px; text-indent: %(indent)s }
        </style>
        <p>Some text that is long enough that it take at least three line,
           but maybe more.
    ''' % {'indent': indent})
    html, = page.children
    body, = html.children
    paragraph, = body.children
    lines = paragraph.children
    text_1, = lines[0].children
    text_2, = lines[1].children
    text_3, = lines[2].children
    assert text_1.position_x == 22  # 10px margin-left + 12px indent
    assert text_2.position_x == 10  # No indent
    assert text_3.position_x == 10  # No indent


@assert_no_logs
def test_text_indent_inline():
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/1000
    page, = render_pages('''
        <style>
            @font-face { src: url(weasyprint.otf); font-family: weasyprint }
            p { display: inline-block; text-indent: 1em;
                font-family: weasyprint }
        </style>
        <p><span>text
    ''')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    line, = paragraph.children
    assert line.width == (4 + 1) * 16


@pytest.mark.parametrize('indent', ('12px', '6%'))
@assert_no_logs
def test_text_indent_multipage(indent):
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/706
    pages = render_pages('''
        <style>
            @page { size: 220px 1.5em; margin: 0 }
            body { margin: 10px; text-indent: %(indent)s }
        </style>
        <p>Some text that is long enough that it take at least three line,
           but maybe more.
    ''' % {'indent': indent})
    page = pages.pop(0)
    html, = page.children
    body, = html.children
    paragraph, = body.children
    line, = paragraph.children
    text, = line.children
    assert text.position_x == 22  # 10px margin-left + 12px indent

    page = pages.pop(0)
    html, = page.children
    body, = html.children
    paragraph, = body.children
    line, = paragraph.children
    text, = line.children
    assert text.position_x == 10  # No indent


@assert_no_logs
def test_hyphenate_character_1():
    page, = render_pages(
        '<html style="width: 5em; font-family: weasyprint">'
        '<style>'
        '  @font-face {src: url(weasyprint.otf); font-family: weasyprint}'
        '</style>'
        '<body style="hyphens: auto;'
        'hyphenate-character: \'!\'" lang=fr>'
        'hyphénation')
    html, = page.children
    body, = html.children
    lines = body.children
    assert len(lines) > 1
    assert lines[0].children[0].text.endswith('!')
    full_text = ''.join(line.children[0].text for line in lines)
    assert full_text.replace('!', '') == 'hyphénation'


@assert_no_logs
def test_hyphenate_character_2():
    page, = render_pages(
        '<html style="width: 5em; font-family: weasyprint">'
        '<style>'
        '  @font-face {src: url(weasyprint.otf); font-family: weasyprint}'
        '</style>'
        '<body style="hyphens: auto;'
        'hyphenate-character: \'à\'" lang=fr>'
        'hyphénation')
    html, = page.children
    body, = html.children
    lines = body.children
    assert len(lines) > 1
    assert lines[0].children[0].text.endswith('à')
    full_text = ''.join(line.children[0].text for line in lines)
    assert full_text.replace('à', '') == 'hyphénation'


@assert_no_logs
def test_hyphenate_character_3():
    page, = render_pages(
        '<html style="width: 5em; font-family: weasyprint">'
        '<style>'
        '  @font-face {src: url(weasyprint.otf); font-family: weasyprint}'
        '</style>'
        '<body style="hyphens: auto;'
        'hyphenate-character: \'ù ù\'" lang=fr>'
        'hyphénation')
    html, = page.children
    body, = html.children
    lines = body.children
    assert len(lines) > 1
    assert lines[0].children[0].text.endswith('ù ù')
    full_text = ''.join(line.children[0].text for line in lines)
    assert full_text.replace(' ', '').replace('ù', '') == 'hyphénation'


@assert_no_logs
def test_hyphenate_character_4():
    page, = render_pages(
        '<html style="width: 5em; font-family: weasyprint">'
        '<style>'
        '  @font-face {src: url(weasyprint.otf); font-family: weasyprint}'
        '</style>'
        '<body style="hyphens: auto;'
        'hyphenate-character: \'\'" lang=fr>'
        'hyphénation')
    html, = page.children
    body, = html.children
    lines = body.children
    assert len(lines) > 1
    full_text = ''.join(line.children[0].text for line in lines)
    assert full_text == 'hyphénation'


@assert_no_logs
def test_hyphenate_character_5():
    page, = render_pages(
        '<html style="width: 5em; font-family: weasyprint">'
        '<style>'
        '  @font-face {src: url(weasyprint.otf); font-family: weasyprint}'
        '</style>'
        '<body style="hyphens: auto;'
        'hyphenate-character: \'———\'" lang=fr>'
        'hyphénation')
    html, = page.children
    body, = html.children
    lines = body.children
    assert len(lines) > 1
    assert lines[0].children[0].text.endswith('———')
    full_text = ''.join(line.children[0].text for line in lines)
    assert full_text.replace('—', '') == 'hyphénation'


@assert_no_logs
@pytest.mark.parametrize('i', (range(1, len('hyphénation'))))
def test_hyphenate_manual_1(i):
    for hyphenate_character in ('!', 'ù ù'):
        word = f'{"hyphénation"[:i]}\xad{"hyphénation"[i:]}'
        page, = render_pages(
            '<html style="width: 5em; font-family: weasyprint">'
            '<style>@font-face {'
            '  src: url(weasyprint.otf); font-family: weasyprint}</style>'
            '<body style="hyphens: manual;'
            f'  hyphenate-character: \'{hyphenate_character}\'"'
            f'  lang=fr>{word}')
        html, = page.children
        body, = html.children
        lines = body.children
        assert len(lines) == 2
        assert lines[0].children[0].text.endswith(hyphenate_character)
        full_text = ''.join(
            child.text for line in lines for child in line.children)
        assert full_text.replace(hyphenate_character, '') == word


@assert_no_logs
@pytest.mark.parametrize('i', (range(1, len('hy phénation'))))
def test_hyphenate_manual_2(i):
    for hyphenate_character in ('!', 'ù ù'):
        word = f'{"hy phénation"[:i]}\xad{"hy phénation"[i:]}'
        page, = render_pages(
            '<html style="width: 5em; font-family: weasyprint">'
            '<style>@font-face {'
            '  src: url(weasyprint.otf); font-family: weasyprint}</style>'
            '<body style="hyphens: manual;'
            f'  hyphenate-character: \'{hyphenate_character}\'"'
            f'  lang=fr>{word}')
        html, = page.children
        body, = html.children
        lines = body.children
        assert len(lines) in (2, 3)
        full_text = ''.join(
            child.text for line in lines for child in line.children)
        full_text = full_text.replace(hyphenate_character, '')
        if lines[0].children[0].text.endswith(hyphenate_character):
            assert full_text == word
        else:
            assert lines[0].children[0].text.rstrip('\xad').endswith('y')
            if len(lines) == 3:
                assert lines[1].children[0].text.rstrip('\xad').endswith(
                    hyphenate_character)


@assert_no_logs
def test_hyphenate_manual_3():
    # Automatic hyphenation opportunities within a word must be ignored if the
    # word contains a conditional hyphen, in favor of the conditional
    # hyphen(s).
    page, = render_pages(
        '<html style="width: 0.1em" lang="en">'
        '<body style="hyphens: auto">in&shy;lighten&shy;lighten&shy;in')
    html, = page.children
    body, = html.children
    line_1, line_2, line_3, line_4 = body.children
    assert line_1.children[0].text == 'in\xad‐'
    assert line_2.children[0].text == 'lighten\xad‐'
    assert line_3.children[0].text == 'lighten\xad‐'
    assert line_4.children[0].text == 'in'


@assert_no_logs
def test_hyphenate_manual_4():
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/1878
    page, = render_pages(
        '<html style="width: 0.1em" lang="en">'
        '<body style="hyphens: auto">test&shy;')
    html, = page.children
    body, = html.children
    line_1, = body.children
    # TODO: should not end with an hyphen
    # assert line_1.children[0].text == 'test\xad'


@assert_no_logs
def test_hyphenate_limit_zone_1():
    page, = render_pages(
        '<html style="width: 12em; font-family: weasyprint">'
        '<style>'
        '  @font-face {src: url(weasyprint.otf); font-family: weasyprint}'
        '</style>'
        '<body style="hyphens: auto;'
        'hyphenate-limit-zone: 0" lang=fr>'
        'mmmmm hyphénation')
    html, = page.children
    body, = html.children
    lines = body.children
    assert len(lines) == 2
    assert lines[0].children[0].text.endswith('‐')
    full_text = ''.join(line.children[0].text for line in lines)
    assert full_text.replace('‐', '') == 'mmmmm hyphénation'


@assert_no_logs
def test_hyphenate_limit_zone_2():
    page, = render_pages(
        '<html style="width: 12em; font-family: weasyprint">'
        '<style>'
        '  @font-face {src: url(weasyprint.otf); font-family: weasyprint}'
        '</style>'
        '<body style="hyphens: auto;'
        'hyphenate-limit-zone: 9em" lang=fr>'
        'mmmmm hyphénation')
    html, = page.children
    body, = html.children
    lines = body.children
    assert len(lines) > 1
    assert lines[0].children[0].text.endswith('mm')
    full_text = ''.join(line.children[0].text for line in lines)
    assert full_text == 'mmmmmhyphénation'


@assert_no_logs
def test_hyphenate_limit_zone_3():
    page, = render_pages(
        '<html style="width: 12em; font-family: weasyprint">'
        '<style>'
        '  @font-face {src: url(weasyprint.otf); font-family: weasyprint}'
        '</style>'
        '<body style="hyphens: auto;'
        'hyphenate-limit-zone: 5%" lang=fr>'
        'mmmmm hyphénation')
    html, = page.children
    body, = html.children
    lines = body.children
    assert len(lines) == 2
    assert lines[0].children[0].text.endswith('‐')
    full_text = ''.join(line.children[0].text for line in lines)
    assert full_text.replace('‐', '') == 'mmmmm hyphénation'


@assert_no_logs
def test_hyphenate_limit_zone_4():
    page, = render_pages(
        '<html style="width: 12em; font-family: weasyprint">'
        '<style>'
        '  @font-face {src: url(weasyprint.otf); font-family: weasyprint}'
        '</style>'
        '<body style="hyphens: auto;'
        'hyphenate-limit-zone: 95%" lang=fr>'
        'mmmmm hyphénation')
    html, = page.children
    body, = html.children
    lines = body.children
    assert len(lines) > 1
    assert lines[0].children[0].text.endswith('mm')
    full_text = ''.join(line.children[0].text for line in lines)
    assert full_text == 'mmmmmhyphénation'


@assert_no_logs
@pytest.mark.parametrize('css, result', (
    ('auto', 2),
    ('auto auto 0', 2),
    ('0 0 0', 2),
    ('4 4 auto', 1),
    ('6 2 4', 2),
    ('auto 1 auto', 2),
    ('7 auto auto', 1),
    ('6 auto auto', 2),
    ('5 2', 2),
    ('3', 2),
    ('2 4 6', 1),
    ('auto 4', 1),
    ('auto 2', 2),
))
def test_hyphenate_limit_chars(css, result):
    page, = render_pages(
        '<html style="width: 1em; font-family: weasyprint">'
        '<style>'
        '  @font-face {src: url(weasyprint.otf); font-family: weasyprint}'
        '</style>'
        '<body style="hyphens: auto;'
        f'hyphenate-limit-chars: {css}" lang=en>'
        'hyphen')
    html, = page.children
    body, = html.children
    lines = body.children
    assert len(lines) == result


@assert_no_logs
@pytest.mark.parametrize('css', (
    # light·en
    '3 3 3',  # 'en' is shorter than 3
    '3 6 2',  # 'light' is shorter than 6
    '8',  # 'lighten' is shorter than 8
))
def test_hyphenate_limit_chars_punctuation(css):
    # See https://github.com/Kozea/WeasyPrint/issues/109
    page, = render_pages(
        '<html style="width: 1em; font-family: weasyprint">'
        '<style>'
        '  @font-face {src: url(weasyprint.otf); font-family: weasyprint}'
        '</style>'
        '<body style="hyphens: auto;'
        f'hyphenate-limit-chars: {css}" lang=en>'
        '..lighten..')
    html, = page.children
    body, = html.children
    lines = body.children
    assert len(lines) == 1


@assert_no_logs
@pytest.mark.parametrize('wrap, text, test, full_text', (
    ('anywhere', 'aaaaaaaa', lambda a: a > 1, 'aaaaaaaa'),
    ('break-word', 'aaaaaaaa', lambda a: a > 1, 'aaaaaaaa'),
    ('normal', 'aaaaaaaa', lambda a: a == 1, 'aaaaaaaa'),
    ('break-word', 'hyphenations', lambda a: a > 3,
     'hy\u2010phen\u2010ations'),
    ('break-word', "A splitted word.  An hyphenated word.",
     lambda a: a > 8, "Asplittedword.Anhy\u2010phen\u2010atedword."),
))
def test_overflow_wrap(wrap, text, test, full_text):
    page, = render_pages('''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        body {width: 80px; overflow: hidden; font-family: weasyprint}
        span {overflow-wrap: %s}
      </style>
      <body style="hyphens: auto;" lang="en">
        <span>%s
    ''' % (wrap, text))
    html, = page.children
    body, = html.children
    lines = []
    for line in body.children:
        box, = line.children
        textBox, = box.children
        lines.append(textBox.text)
    lines_full_text = ''.join(line for line in lines)
    assert test(len(lines))
    assert full_text == lines_full_text


@assert_no_logs
@pytest.mark.parametrize('span_css, expected_lines', (
    # overflow-wrap: anywhere and break-word are only allowed to break a word
    # "if there are no otherwise-acceptable break points in the line", which
    # means they should not split a word if it fits cleanly into the next line.
    # This can be done accidentally if it is in its own inline element.
    ('overflow-wrap: anywhere', ['aaa', 'bbb']),
    ('overflow-wrap: break-word', ['aaa', 'bbb']),

    # On the other hand, word-break: break-all mandates a break anywhere at the
    # end of a line, even if the word could fit cleanly onto the next line.
    ('word-break: break-all', ['aaa b', 'bb']),
))
def test_wrap_overflow_word_break(span_css, expected_lines):
    page, = render_pages('''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        body {width: 80px; overflow: hidden; font-family: weasyprint}
        span {%s}
      </style>
      <body>
        <span>aaa </span><span>bbb
    ''' % span_css)
    html, = page.children
    body, = html.children
    lines = body.children
    lines = []
    for line in body.children:
        line_text = ''
        for span_box in line.children:
            line_text += span_box.children[0].text
        lines.append(line_text)
    assert lines == expected_lines


@assert_no_logs
@pytest.mark.parametrize('wrap, text, body_width, expected_width', (
    ('anywhere', 'aaaaaa', 10, 20),
    ('anywhere', 'aaaaaa', 40, 40),
    ('break-word', 'aaaaaa', 40, 120),
    ('normal', 'aaaaaa', 40, 120),
))
def test_overflow_wrap_2(wrap, text, body_width, expected_width):
    page, = render_pages('''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        body {width: %dpx; font-family: weasyprint; font-size: 20px}
        table {overflow-wrap: %s}
      </style>
      <table><tr><td>%s''' % (body_width, wrap, text))
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    tr, = row_group.children
    td, = tr.children
    assert td.width == expected_width


@assert_no_logs
@pytest.mark.parametrize('wrap, text, body_width, expected_width', (
    ('anywhere', 'aaaaaa', 10, 20),
    ('anywhere', 'aaaaaa', 40, 40),
    ('break-word', 'aaaaaa', 40, 120),
    ('normal', 'abcdef', 40, 120),
))
def test_overflow_wrap_trailing_space(wrap, text, body_width, expected_width):
    page, = render_pages('''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        body {width: %dpx; font-family: weasyprint; font-size: 20px}
        table {overflow-wrap: %s}
      </style>
      <table><tr><td>%s ''' % (body_width, wrap, text))
    html, = page.children
    body, = html.children
    table_wrapper, = body.children
    table, = table_wrapper.children
    row_group, = table.children
    tr, = row_group.children
    td, = tr.children
    assert td.width == expected_width


def test_line_break_before_trailing_space():
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/1852
    page, = render_pages('''
        <p style="display: inline-block">test\u2028 </p>a
        <p style="display: inline-block">test\u2028</p>a
    ''')
    html, = page.children
    body, = html.children
    line, = body.children
    p1, space1, p2, space2 = line.children
    assert p1.width == p2.width


def white_space_lines(width, space):
    page, = render_pages('''
      <style>
        body { font-size: 100px; width: %dpx }
        span { white-space: %s }
      </style>
      <body><span>This +    \n    is text''' % (width, space))
    html, = page.children
    body, = html.children
    return body.children


@assert_no_logs
def test_white_space_1():
    line1, line2, line3, line4 = white_space_lines(1, 'normal')
    box1, = line1.children
    text1, = box1.children
    assert text1.text == 'This'
    box2, = line2.children
    text2, = box2.children
    assert text2.text == '+'
    box3, = line3.children
    text3, = box3.children
    assert text3.text == 'is'
    box4, = line4.children
    text4, = box4.children
    assert text4.text == 'text'


@assert_no_logs
def test_white_space_2():
    line1, line2 = white_space_lines(1, 'pre')
    box1, = line1.children
    text1, = box1.children
    assert text1.text == 'This +    '
    box2, = line2.children
    text2, = box2.children
    assert text2.text == '    is text'


@assert_no_logs
def test_white_space_3():
    line1, = white_space_lines(1, 'nowrap')
    box1, = line1.children
    text1, = box1.children
    assert text1.text == 'This + is text'


@assert_no_logs
def test_white_space_4():
    line1, line2, line3, line4, line5 = white_space_lines(1, 'pre-wrap')
    box1, = line1.children
    text1, = box1.children
    assert text1.text == 'This '
    box2, = line2.children
    text2, = box2.children
    assert text2.text == '+    '
    box3, = line3.children
    text3, = box3.children
    assert text3.text == '    '
    box4, = line4.children
    text4, = box4.children
    assert text4.text == 'is '
    box5, = line5.children
    text5, = box5.children
    assert text5.text == 'text'


@assert_no_logs
def test_white_space_5():
    line1, line2, line3, line4 = white_space_lines(1, 'pre-line')
    box1, = line1.children
    text1, = box1.children
    assert text1.text == 'This'
    box2, = line2.children
    text2, = box2.children
    assert text2.text == '+'
    box3, = line3.children
    text3, = box3.children
    assert text3.text == 'is'
    box4, = line4.children
    text4, = box4.children
    assert text4.text == 'text'


@assert_no_logs
def test_white_space_6():
    line1, = white_space_lines(1000000, 'normal')
    box1, = line1.children
    text1, = box1.children
    assert text1.text == 'This + is text'


@assert_no_logs
def test_white_space_7():
    line1, line2 = white_space_lines(1000000, 'pre')
    box1, = line1.children
    text1, = box1.children
    assert text1.text == 'This +    '
    box2, = line2.children
    text2, = box2.children
    assert text2.text == '    is text'


@assert_no_logs
def test_white_space_8():
    line1, = white_space_lines(1000000, 'nowrap')
    box1, = line1.children
    text1, = box1.children
    assert text1.text == 'This + is text'


@assert_no_logs
def test_white_space_9():
    line1, line2 = white_space_lines(1000000, 'pre-wrap')
    box1, = line1.children
    text1, = box1.children
    assert text1.text == 'This +    '
    box2, = line2.children
    text2, = box2.children
    assert text2.text == '    is text'


@assert_no_logs
def test_white_space_10():
    line1, line2 = white_space_lines(1000000, 'pre-line')
    box1, = line1.children
    text1, = box1.children
    assert text1.text == 'This +'
    box2, = line2.children
    text2, = box2.children
    assert text2.text == 'is text'


@assert_no_logs
def test_white_space_11():
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/813
    page, = render_pages('''
      <style>
        pre { width: 0 }
      </style>
      <body><pre>This<br/>is text''')
    html, = page.children
    body, = html.children
    pre, = body.children
    line1, line2 = pre.children
    text1, box = line1.children
    assert text1.text == 'This'
    assert box.element_tag == 'br'
    text2, = line2.children
    assert text2.text == 'is text'


@assert_no_logs
def test_white_space_12():
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/813
    page, = render_pages('''
      <style>
        pre { width: 0 }
      </style>
      <body><pre>This is <span>lol</span> text''')
    html, = page.children
    body, = html.children
    pre, = body.children
    line1, = pre.children
    text1, span, text2 = line1.children
    assert text1.text == 'This is '
    assert span.element_tag == 'span'
    assert text2.text == ' text'


@assert_no_logs
@pytest.mark.parametrize('value, width', (
    (8, 144),  # (2 + (8 - 1)) * 16
    (4, 80),  # (2 + (4 - 1)) * 16
    ('3em', 64),  # (2 + (3 - 1)) * 16
    ('25px', 41),  # 2 * 16 + 25 - 1 * 16
    # (0, 32),  # See Layout.set_tabs
))
def test_tab_size(value, width):
    page, = render_pages('''
      <style>
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        pre { tab-size: %s; font-family: weasyprint }
      </style>
      <pre>a&#9;a</pre>
    ''' % value)
    html, = page.children
    body, = html.children
    paragraph, = body.children
    line, = paragraph.children
    assert line.width == width


@assert_no_logs
def test_text_transform():
    page, = render_pages('''
      <style>
        p { text-transform: capitalize }
        p+p { text-transform: uppercase }
        p+p+p { text-transform: lowercase }
        p+p+p+p { text-transform: full-width }
        p+p+p+p+p { text-transform: none }
      </style>
<p>hé lO1</p><p>hé lO1</p><p>hé lO1</p><p>hé lO1</p><p>hé lO1</p>
    ''')
    html, = page.children
    body, = html.children
    p1, p2, p3, p4, p5 = body.children
    line1, = p1.children
    text1, = line1.children
    assert text1.text == 'Hé LO1'
    line2, = p2.children
    text2, = line2.children
    assert text2.text == 'HÉ LO1'
    line3, = p3.children
    text3, = line3.children
    assert text3.text == 'hé lo1'
    line4, = p4.children
    text4, = line4.children
    assert text4.text == '\uff48é\u3000\uff4c\uff2f\uff11'
    line5, = p5.children
    text5, = line5.children
    assert text5.text == 'hé lO1'


@assert_no_logs
@pytest.mark.parametrize(
    'original, transformed', (
        ('abc def ghi', 'Abc Def Ghi'),
        ('AbC def ghi', 'AbC Def Ghi'),
        ('I’m SO cool', 'I’m SO Cool'),
        ('Wow.wow!wow', 'Wow.wow!wow'),
        ('!now not tomorrow', '!Now Not Tomorrow'),
        ('SUPER cool', 'SUPER Cool'),
        ('i 😻 non‑breaking characters', 'I 😻 Non‑breaking Characters'),
        ('3lite 3lite', '3lite 3lite'),
        ('one/two/three', 'One/two/three'),
        ('supernatural,super', 'Supernatural,super'),
        ('éternel αιώνια', 'Éternel Αιώνια'),
    )
)
def test_text_transform_capitalize(original, transformed):
    # Results are different for different browsers, we almost get the same
    # results as Firefox, that’s good enough!
    assert capitalize(original) == transformed


@assert_no_logs
def test_text_floating_pre_line():
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/610
    page, = render_pages('''
      <div style="float: left; white-space: pre-line">This is
      oh this end </div>
    ''')


@assert_no_logs
@pytest.mark.parametrize(
    'leader, content', (
        ('dotted', '.'),
        ('solid', '_'),
        ('space', ' '),
        ('" .-"', ' .-'),
    )
)
def test_leader_content(leader, content):
    page, = render_pages('''
      <style>div::after { content: leader(%s) }</style>
      <div></div>
    ''' % leader)
    html, = page.children
    body, = html.children
    div, = body.children
    line, = div.children
    after, = line.children
    inline, = after.children
    assert inline.children[0].text == content


@pytest.mark.xfail
@assert_no_logs
def test_max_lines():
    page, = render_pages('''
      <style>
        @page {size: 10px 10px;}
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        p {
          font-family: weasyprint;
          font-size: 2px;
          max-lines: 2;
        }
      </style>
      <p>
        abcd efgh ijkl
      </p>
    ''')
    html, = page.children
    body, = html.children
    p1, p2 = body.children
    line1, line2 = p1.children
    line3, = p2.children
    text1, = line1.children
    text2, = line2.children
    text3, = line3.children
    assert text1.text == 'abcd'
    assert text2.text == 'efgh'
    assert text3.text == 'ijkl'


@assert_no_logs
def test_continue():
    page, = render_pages('''
      <style>
        @page {size: 10px 4px;}
        @font-face {src: url(weasyprint.otf); font-family: weasyprint}
        div {
          continue: discard;
          font-family: weasyprint;
          font-size: 2px;
        }
      </style>
      <div>
        abcd efgh ijkl
      </div>
    ''')
    html, = page.children
    body, = html.children
    p, = body.children
    line1, line2 = p.children
    text1, = line1.children
    text2, = line2.children
    assert text1.text == 'abcd'
    assert text2.text == 'efgh'


def test_first_letter_text_transform():
    # Test regression: https://github.com/Kozea/WeasyPrint/issues/1906
    page, = render_pages('''
      <style>
        p:first-letter { text-transform: uppercase }
      </style>
      <p>abc
    ''')
    html, = page.children
    body, = html.children
    paragraph, = body.children
    line, = paragraph.children
    first_letter, _ = line.children
    first_letter_text, = first_letter.children
    assert first_letter_text.text == 'A'
