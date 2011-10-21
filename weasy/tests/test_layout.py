# coding: utf8

#  WeasyPrint converts web documents (HTML, CSS, ...) to PDF.
#  Copyright (C) 2011  Simon Sapin
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""
Test the layout.

"""

from attest import Tests, assert_hook  # pylint: disable=W0611

from . import TestPNGDocument, resource_filename
from ..formatting_structure import boxes
from .test_boxes import monkeypatch_validation
from . import FONTS
from ..layout.blocks import block_level_width
from ..layout.inlines import split_inline_box
from ..layout.percentages import resolve_percentages

SUITE = Tests()


def body_children(page):
    """Take a ``page``  and return its <body>’s children."""
    html = page.root_box
    assert html.element.tag == 'html'
    body, = html.children
    assert body.element.tag == 'body'
    return body.children


def parse_without_layout(html_content):
    """Parse some HTML, apply stylesheets, transform to boxes."""
    return TestPNGDocument.from_string(html_content).formatting_structure


def validate_absolute_and_float(
        real_non_shorthand, name, values, required=False):
    """Fake validator for ``absolute`` and ``float``."""
    value = values[0].value
    if (name == 'position' and value == 'absolute'
            ) or (name == 'float' and value == 'left'):
        return [(name, value)]
    return real_non_shorthand(name, values, required)


def parse(html_content):
    """Parse some HTML, apply stylesheets, transform to boxes and lay out."""
    # TODO: remove this patching when asbolute and floats are validated
    with monkeypatch_validation(validate_absolute_and_float):
        document = TestPNGDocument.from_string(html_content)
        document.base_url = resource_filename('<inline HTML>')
        return document.pages


@SUITE.test
def test_page():
    """Test the layout for ``@page`` properties."""
    pages = parse('<p>')
    page = pages[0]
    assert isinstance(page, boxes.PageBox)
    assert int(page.outer_width) == 793  # A4: 210 mm in pixels
    assert int(page.outer_height) == 1122  # A4: 297 mm in pixels

    page, = parse('''<style>@page { size: 2in 10in; }</style>''')
    assert page.outer_width == 192
    assert page.outer_height == 960

    page, = parse('''<style>@page { size: 242px; }</style>''')
    assert page.outer_width == 242
    assert page.outer_height == 242

    page, = parse('''<style>@page { size: letter; }</style>''')
    assert page.outer_width == 816  # 8.5in
    assert page.outer_height == 1056  # 11in

    page, = parse('''<style>@page { size: letter portrait; }</style>''')
    assert page.outer_width == 816  # 8.5in
    assert page.outer_height == 1056  # 11in

    page, = parse('''<style>@page { size: letter landscape; }</style>''')
    assert page.outer_width == 1056  # 11in
    assert page.outer_height == 816  # 8.5in

    page, = parse('''<style>@page { size: portrait; }</style>''')
    assert int(page.outer_width) == 793  # A4: 210 mm
    assert int(page.outer_height) == 1122  # A4: 297 mm

    page, = parse('''<style>@page { size: landscape; }</style>''')
    assert int(page.outer_width) == 1122  # A4: 297 mm
    assert int(page.outer_height) == 793  # A4: 210 mm

    page, = parse('''
        <style>@page { size: 200px 300px; margin: 10px 10% 20% 1in }
               body { margin: 8px }
        </style>
        <p style="margin: 0">
    ''')
    assert page.outer_width == 200
    assert page.outer_height == 300
    assert page.position_x == 0
    assert page.position_y == 0
    assert page.width == 84  # 200px - 10% - 1 inch
    assert page.height == 230  # 300px - 10px - 20%

    html = page.root_box
    assert html.element.tag == 'html'
    assert html.position_x == 96  # 1in
    assert html.position_y == 10
    assert html.width == 84

    body, = html.children
    assert body.element.tag == 'body'
    assert body.position_x == 96  # 1in
    assert body.position_y == 10
    # body has margins in the UA stylesheet
    assert body.margin_left == 8
    assert body.margin_right == 8
    assert body.margin_top == 8
    assert body.margin_bottom == 8
    assert body.width == 68

    paragraph, = body.children
    assert paragraph.element.tag == 'p'
    assert paragraph.position_x == 104  # 1in + 8px
    assert paragraph.position_y == 18  # 10px + 8px
    assert paragraph.width == 68

    page, = parse('''
        <style>
            @page { size: 100px; margin: 1px 2px; padding: 4px 8px;
                    border-width: 16px 32px; border-style: solid }
        </style>
        <body>
    ''')
    assert page.width == 16  # 100 - 2 * 42
    assert page.height == 58  # 100 - 2 * 21
    html = page.root_box
    assert html.element.tag == 'html'
    assert html.position_x == 42  # 2 + 8 + 32
    assert html.position_y == 21  # 1 + 4 + 16


@SUITE.test
def test_block_widths():
    """Test the blocks widths."""
    page, = parse('''
        <style>
            @page { margin: 0; size: 120px 2000px }
            body { margin: 0 }
            div { margin: 10px }
            p { padding: 2px; border-width: 1px; border-style: solid }
        </style>
        <div>
          <p></p>
          <p style="width: 50px"></p>
        </div>
        <div style="direction: rtl">
          <p style="width: 50px; direction: rtl"></p>
        </div>
        <div>
          <p style="margin: 0 10px 0 20px"></p>
          <p style="width: 50px; margin-left: 20px; margin-right: auto"></p>
          <p style="width: 50px; margin-left: auto; margin-right: 20px"></p>
          <p style="width: 50px; margin: auto"></p>

          <p style="margin-left: 20px; margin-right: auto"></p>
          <p style="margin-left: auto; margin-right: 20px"></p>
          <p style="margin: auto"></p>

          <p style="width: 200px; margin: auto"></p>
        </div>
    ''')
    html = page.root_box
    assert html.element.tag == 'html'
    body, = html.children
    assert body.element.tag == 'body'
    assert body.width == 120

    divs = body.children
    # TODO: remove this when we have proper whitespace handling that
    # does not create anonymous block boxes for the whitespace between divs.
    divs = [box for box in divs if not isinstance(box, boxes.AnonymousBox)]

    paragraphs = []
    for div in divs:
        assert isinstance(div, boxes.BlockBox)
        assert div.element.tag == 'div'
        assert div.width == 100
        for paragraph in div.children:
            if isinstance(paragraph, boxes.AnonymousBox):
                # TODO: remove this when we have proper whitespace handling
                continue
            assert isinstance(paragraph, boxes.BlockBox)
            assert paragraph.element.tag == 'p'
            assert paragraph.padding_left == 2
            assert paragraph.padding_right == 2
            assert paragraph.border_left_width == 1
            assert paragraph.border_right_width == 1
            paragraphs.append(paragraph)

    assert len(paragraphs) == 11

    # width is 'auto'
    assert paragraphs[0].width == 94
    assert paragraphs[0].margin_left == 0
    assert paragraphs[0].margin_right == 0

    # No 'auto', over-constrained equation with ltr, the initial
    # 'margin-right: 0' was ignored.
    assert paragraphs[1].width == 50
    assert paragraphs[1].margin_left == 0
    assert paragraphs[1].margin_right == 44

    # No 'auto', over-constrained equation with ltr, the initial
    # 'margin-right: 0' was ignored.
    assert paragraphs[2].width == 50
    assert paragraphs[2].margin_left == 44
    assert paragraphs[2].margin_right == 0

    # width is 'auto'
    assert paragraphs[3].width == 64
    assert paragraphs[3].margin_left == 20
    assert paragraphs[3].margin_right == 10

    # margin-right is 'auto'
    assert paragraphs[4].width == 50
    assert paragraphs[4].margin_left == 20
    assert paragraphs[4].margin_right == 24

    # margin-left is 'auto'
    assert paragraphs[5].width == 50
    assert paragraphs[5].margin_left == 24
    assert paragraphs[5].margin_right == 20

    # Both margins are 'auto', remaining space is split in half
    assert paragraphs[6].width == 50
    assert paragraphs[6].margin_left == 22
    assert paragraphs[6].margin_right == 22

    # width is 'auto', other 'auto' are set to 0
    assert paragraphs[7].width == 74
    assert paragraphs[7].margin_left == 20
    assert paragraphs[7].margin_right == 0

    # width is 'auto', other 'auto' are set to 0
    assert paragraphs[8].width == 74
    assert paragraphs[8].margin_left == 0
    assert paragraphs[8].margin_right == 20

    # width is 'auto', other 'auto' are set to 0
    assert paragraphs[9].width == 94
    assert paragraphs[9].margin_left == 0
    assert paragraphs[9].margin_right == 0

    # sum of non-auto initially is too wide, set auto values to 0
    assert paragraphs[10].width == 200
    assert paragraphs[10].margin_left == 0
    assert paragraphs[10].margin_right == -106


@SUITE.test
def test_block_heights():
    """Test the blocks heights."""
    page, = parse('''
        <style>
            @page { margin: 0; size: 100px 2000px }
            html, body { margin: 0 }
            div { margin: 4px; border-width: 2px; border-style: solid;
                  padding: 4px }
            p { margin: 8px; border-width: 4px; border-style: solid;
                padding: 8px; height: 50px }
        </style>
        <div>
          <p></p>
          <!-- These two are not in normal flow: the do not contribute to
            the parent’s height. -->
          <p style="position: absolute"></p>
          <p style="float: left"></p>
        </div><div>
          <p></p>
          <p></p>
          <p></p>
        </div>
    ''')
    divs = body_children(page)

    assert divs[0].height == 90
    assert divs[1].height == 90 * 3


@SUITE.test
def test_block_percentage_heights():
    """Test the blocks heights set in percents."""
    page, = parse('''
        <style>
            html, body { margin: 0 }
            body { height: 50% }
        </style>
        <body>
    ''')
    html = page.root_box
    assert html.element.tag == 'html'
    body, = html.children
    assert body.element.tag == 'body'

    # Since html’s height depend on body’s, body’s 50% means 'auto'
    assert body.height == 0

    page, = parse('''
        <style>
            html, body { margin: 0 }
            html { height: 300px }
            body { height: 50% }
        </style>
        <body>
    ''')
    html = page.root_box
    assert html.element.tag == 'html'
    body, = html.children
    assert body.element.tag == 'body'

    # This time the percentage makes sense
    assert body.height == 150


@SUITE.test
def test_lists():
    """Test the lists."""
    page, = parse('''
        <style>
            body { margin: 0 }
            ul { margin-left: 50px; list-style: inside circle }
        </style>
        <ul>
          <li>abc</li>
        </ul>
    ''')
    unordered_list, = body_children(page)
    list_element, = [child for child in unordered_list.children
           if not isinstance(child, boxes.AnonymousBox)]
    line, = list_element.children
    marker, spacer, content = line.children
    assert marker.utf8_text.decode('utf8') == u'◦'
    assert spacer.utf8_text.decode('utf8') == u'\u00a0'  # NO-BREAK SPACE
    assert content.utf8_text.decode('utf8') == u'abc'

    page, = parse('''
        <style>
            body { margin: 0 }
            ul { margin-left: 50px; }
        </style>
        <ul>
          <li>abc</li>
        </ul>
    ''')
    unordered_list, = body_children(page)
    list_element, = [child for child in unordered_list.children
           if not isinstance(child, boxes.AnonymousBox)]
    marker = list_element.outside_list_marker
    font_size = marker.style.font_size
    assert marker.margin_right == 0.5 * font_size  # 0.5em
    assert marker.position_x == (
        list_element.padding_box_x() - marker.width - marker.margin_right)
    assert marker.position_y == list_element.position_y
    assert marker.utf8_text.decode('utf8') == u'•'
    line, = list_element.children
    content, = line.children
    assert content.utf8_text == b'abc'


@SUITE.test
def test_empty_linebox():
    """Test lineboxes with no content other than space-like characters."""
    page, = parse('''
        <style>
        p { font-size: 12px; width: 500px;
            font-family:%(fonts)s;}
        </style>
        <p> </p>
    ''' % {'fonts': FONTS})
    paragraph, = body_children(page)
    line, = paragraph.children
    assert line.height == 0
    assert paragraph.height == 0


@SUITE.test
def test_breaking_linebox():
    """Test lineboxes breaks with a lot of text and deep nesting."""
    page, = parse(u'''
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
    ''' % {'fonts': FONTS})
    html = page.root_box
    body, = html.children
    paragraph, = body.children
    assert len(list(paragraph.children)) == 3

    lines = paragraph.children
    for line in lines:
        assert line.style.font_size == 13
        assert line.element.tag == 'p'
        for child in line.children:
            assert child.element.tag in ('em', 'p')
            assert child.style.font_size == 13
            if isinstance(child, boxes.ParentBox):
                for child_child in child.children:
                    assert child.element.tag in ('em', 'strong', 'span')
                    assert child.style.font_size == 13


@SUITE.test
def test_linebox_text():
    """Test the creation of line boxes."""
    page, = parse('''
        <style>
            p { width: 165px; font-family:%(fonts)s;}
        </style>
        <p><em>Lorem Ipsum</em>is very <strong>coool</strong></p>
    ''' % {'fonts': FONTS})
    paragraph, = body_children(page)
    lines = list(paragraph.children)
    assert len(lines) == 2

    text = b' '.join(
        (b''.join(box.utf8_text for box in line.descendants()
                 if isinstance(box, boxes.TextBox)))
        for line in lines)
    assert text == b'Lorem Ipsumis very coool'


@SUITE.test
def test_linebox_positions():
    """Test the position of line boxes."""
    page = u'''
        <style>
            p { width:%(width)spx; font-family:%(fonts)s;}
        </style>
        <p>this is test for <strong>Weasyprint</strong></p>'''
    page, = parse(page % {'fonts': FONTS, 'width': 165})
    paragraph, = body_children(page)
    lines = list(paragraph.children)
    assert len(lines) == 2

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


@SUITE.test
def test_forced_line_breaks():
    """Test <pre> and <br>."""
    # These lines should be small enough to fit on the default A4 page
    # with the default 12pt font-size.
    page, = parse('''
        <style> pre { line-height: 42px }</style>
        <pre>Lorem ipsum dolor sit amet,
            consectetur adipiscing elit.


            Sed sollicitudin nibh

            et turpis molestie tristique.</pre>
    ''')
    pre, = body_children(page)
    assert pre.element.tag == 'pre'
    lines = pre.children
    assert all(isinstance(line, boxes.LineBox) for line in lines)
    assert len(lines) == 7
    assert [line.height for line in lines] == [42] * 7

    page, = parse('''
        <style> p { line-height: 42px }</style>
        <p>Lorem ipsum dolor sit amet,<br>
            consectetur adipiscing elit.<br><br><br>
            Sed sollicitudin nibh<br>
            <br>

            et turpis molestie tristique.</p>
    ''')
    pre, = body_children(page)
    assert pre.element.tag == 'p'
    lines = pre.children
    assert all(isinstance(line, boxes.LineBox) for line in lines)
    assert len(lines) == 7
    assert [line.height for line in lines] == [42] * 7


#@SUITE.test
def test_page_breaks():
    """Test the page breaks."""
    pages = parse('''
        <style>
            @page { size: 100px; margin: 10px }
            body { margin: 0 }
            div { height: 30px }
        </style>
        <div/><div/><div/><div/><div/>
    ''')
    page_divs = []
    for page in pages:
        divs = body_children(page)
        assert all([div.element.tag == 'div' for div in divs])
        assert all([div.position_x == 10 for div in divs])
        page_divs.append(divs)

    positions_y = [[div.position_y for div in divs] for divs in page_divs]
    assert positions_y == [[10, 40], [10, 40], [10]]


@SUITE.test
def test_inlinebox_spliting():
    """Test the inline boxes spliting."""
    def get_inlinebox(content):
        """Helper returning a inlinebox with customizable style."""
        page = u'<style>p { font-family:%(fonts)s;}</style>'
        page = '%s <p>%s</p>' % (page, content)
        html = parse_without_layout(page % {'fonts': FONTS})
        body, = html.children
        paragraph, = body.children
        line, = paragraph.children
        inline, = line.children
        paragraph.width = 200
        paragraph.height = 'auto'
        return inline, paragraph

    def get_parts(inlinebox, width, parent):
        """Yield the parts of the splitted ``inlinebox`` of given ``width``."""
        skip = None
        while 1:
            box, skip, _ = split_inline_box(
                inlinebox, 0, width, skip, parent, None)
            yield box
            if skip is None:
                break

    def get_joined_text(parts):
        """Get the joined text from ``parts``."""
        return b''.join(part.children[0].utf8_text for part in parts)

    def test_inlinebox_spacing(inlinebox, value, side):
        """Test the margin, padding and border-width of ``inlinebox``."""
        if side in ['left', 'right']:
            # Vertical margins on inlines are irrelevant.
            assert getattr(inlinebox, 'margin_%s' % side) == value
        assert getattr(inlinebox, 'padding_%s' % side) == value
        assert getattr(inlinebox, 'border_%s_width' % side) == value

    content = '''<strong>WeasyPrint is a free software visual rendering engine
              for HTML and CSS</strong>'''

    inlinebox, parent = get_inlinebox(content)
    resolve_percentages(inlinebox, parent)
    original_text = inlinebox.children[0].utf8_text

    # test with width = 1000
    parts = list(get_parts(inlinebox, 1000, parent))
    assert len(parts) == 1
    assert original_text == get_joined_text(parts)

    inlinebox, parent = get_inlinebox(content)
    resolve_percentages(inlinebox, parent)
    original_text = inlinebox.children[0].utf8_text

    # test with width = 100
    parts = list(get_parts(inlinebox, 100, parent))
    assert len(parts) > 1
    assert original_text == get_joined_text(parts)

    inlinebox, parent = get_inlinebox(content)
    resolve_percentages(inlinebox, parent)
    original_text = inlinebox.children[0].utf8_text

    # test with width = 10
    parts = list(get_parts(inlinebox, 10, parent))
    assert len(parts) > 1
    assert original_text == get_joined_text(parts)

    # with margin-border-padding
    content = '''<strong style="border:10px solid; margin:10px; padding:10px">
              WeasyPrint is a free software visual rendering engine
              for HTML and CSS</strong>'''

    inlinebox, parent = get_inlinebox(content)
    resolve_percentages(inlinebox, parent)
    original_text = inlinebox.children[0].utf8_text
    # test with width = 1000
    parts = list(get_parts(inlinebox, 1000, parent))
    assert len(parts) == 1
    assert original_text == get_joined_text(parts)
    for side in ('left', 'top', 'bottom', 'right'):
        test_inlinebox_spacing(parts[0], 10, side)


    inlinebox, parent = get_inlinebox(content)
    resolve_percentages(inlinebox, parent)
    original_text = inlinebox.children[0].utf8_text

    # test with width = 1000
    parts = list(get_parts(inlinebox, 100, parent))
    assert len(parts) != 1
    assert original_text == get_joined_text(parts)
    first_inline_box = parts.pop(0)
    test_inlinebox_spacing(first_inline_box, 10, 'left')
    test_inlinebox_spacing(first_inline_box, 0, 'right')
    last_inline_box = parts.pop()
    test_inlinebox_spacing(last_inline_box, 10, 'right')
    test_inlinebox_spacing(last_inline_box, 0, 'left')
    for part in parts:
        test_inlinebox_spacing(part, 0, 'right')
        test_inlinebox_spacing(part, 0, 'left')


@SUITE.test
def test_inlinebox_text_after_spliting():
    """Test the inlinebox text after spliting."""
    html = parse_without_layout('''
        <style>p { width: 200px; font-family:%(fonts)s;}</style>
        <p><strong><em><em><em>
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13
        </em></em></em></strong></p>
    ''' % {'fonts': FONTS})
    body, = html.children
    paragraph, = body.children
    line, = paragraph.children
    inlinebox, = line.children
    paragraph.width = 200
    paragraph.height = 'auto'
    resolve_percentages(inlinebox, paragraph)

    original_text = b''.join(
        part.utf8_text for part in inlinebox.descendants()
        if isinstance(part, boxes.TextBox))

    # test with width = 10
    parts = []
    skip = None
    while 1:
        box, skip, _ = split_inline_box(
            inlinebox, 0, 100, skip, paragraph, None)
        parts.append(box)
        if skip is None:
            break
    assert len(parts) > 2
    assert b''.join(
        child.utf8_text
        for part in parts
        for child in part.descendants()
        if isinstance(child, boxes.TextBox)
    ) == original_text


@SUITE.test
def test_page_and_linebox_breaking():
    """Test the linebox text after spliting linebox and page."""
    # The empty <span/> tests a corner case
    # in skip_first_whitespace()
    pages = parse('''
        <style>
            div { font-family:%(fonts)s; font-size:22px}
            @page { size: 100px; margin:2px; border:1px solid }
            body { margin: 0 }
        </style>
        <div><span/>1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15</div>
    ''' % {'fonts': FONTS})

    texts = []
    for page in pages:
        html = page.root_box
        body, = html.children
        div, = body.children
        lines = div.children
        for line in lines:
            line_texts = []
            for child in line.descendants():
                if isinstance(child, boxes.TextBox):
                    line_texts.append(child.utf8_text)
            texts.append(b''.join(line_texts))

    assert len(pages) == 2
    assert b' '.join(texts) == \
        '1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15'


@SUITE.test
def test_whitespace_processing():
    for source in ['a', '  a  ', ' \n  \ta', ' a\t ']:
        page, = parse('<p><em>%s</em></p>' % source)
        html = page.root_box
        body, = html.children
        p, = body.children
        line, = p.children
        em, = line.children
        text, = em.children
        assert text.utf8_text == b'a', 'source was %r' % (source,)

        page, = parse('<p style="white-space: pre-line">\n\n<em>%s</em></pre>'
            % source.replace('\n', ' '))
        html = page.root_box
        body, = html.children
        p, = body.children
        _line1, _line2, line3 = p.children
        em, = line3.children
        text, = em.children
        assert text.utf8_text == b'a', 'source was %r' % (source,)


@SUITE.test
def test_with_images():
    # pattern.png is 4x4 px. Layout rules try to preserve the ratio, so
    # the height should be 40px too:
    page, = parse('<img src="pattern.png" style="width: 40px">')
    html = page.root_box
    body, = html.children
    line, = body.children
    img, = line.children
    assert body.height == 40
    assert img.position_y == 0

    page, = parse('''
        <img src="pattern.png" style="width: 40px">
        <img src="pattern.png" style="width: 60px">
    ''')
    html = page.root_box
    body, = html.children
    line, = body.children
    img_1, img_2 = line.children
    assert body.height == 60
    assert img_1.height == 40
    assert img_2.height == 60
    assert img_1.position_y == 20
    assert img_2.position_y == 0

    """
               +-------+      <- position_y = 0
         +-----+       |
    40px |     |       | 60px
         |     |       |
         +-----+-------+      <- baseline
    """
    page, = parse('''
        <span>
            <img src="pattern.png" style="width: 40px">
            <img src="pattern.png" style="width: 60px">
        </span>
    ''')
    html = page.root_box
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


    """
               +-------+      <- position_y = 0
          35px |       |
         +-----+       | 60px
    40px |     |       |
         |     +-------+      <- baseline
         +-----+  15px

    """
    page, = parse('''
        <span>
            <img src="pattern.png" style="width: 40px; vertical-align: -15px">
            <img src="pattern.png" style="width: 60px">
        </span>
    ''')
    html = page.root_box
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

    # Same as previously, but with percentages
    page, = parse('''
        <span style="line-height: 10px">
            <img src="pattern.png" style="width: 40px; vertical-align: -150%">
            <img src="pattern.png" style="width: 60px">
        </span>
    ''')
    html = page.root_box
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


@SUITE.test
def test_text_align_left():
    """
        <-------------------->  page, body
            +-----+
        +---+     |
        |   |     |
        +---+-----+

        ^   ^     ^          ^
        x=0 x=40  x=100      x=200
    """
    page, = parse('''
        <style>
            @page { size: 200px }
        </style>
        <body>
            <img src="pattern.png" style="width: 40px">
            <img src="pattern.png" style="width: 60px">
    ''')
    html = page.root_box
    body, = html.children
    line, = body.children
    img_1, img_2 = line.children
    # initial value for text-align: left (in ltr text)
    assert img_1.position_x == 0
    assert img_2.position_x == 40


@SUITE.test
def test_text_align_right():
    """
        <-------------------->  page, body
                       +-----+
                   +---+     |
                   |   |     |
                   +---+-----+

        ^          ^   ^     ^
        x=0        x=100     x=200
                       x=140
    """
    page, = parse('''
        <style>
            @page { size: 200px }
            body { text-align: right }
        </style>
        <body>
            <img src="pattern.png" style="width: 40px">
            <img src="pattern.png" style="width: 60px">
    ''')
    html = page.root_box
    body, = html.children
    line, = body.children
    img_1, img_2 = line.children
    assert img_1.position_x == 100  # 200 - 60 - 40
    assert img_2.position_x == 140  # 200 - 60


@SUITE.test
def test_text_align_center():
    """
        <-------------------->  page, body
                  +-----+
              +---+     |
              |   |     |
              +---+-----+

        ^     ^   ^     ^
        x=    x=50     x=150
                  x=90
    """
    page, = parse('''
        <style>
            @page { size: 200px }
            body { text-align: center }
        </style>
        <body>
            <img src="pattern.png" style="width: 40px">
            <img src="pattern.png" style="width: 60px">
    ''')
    html = page.root_box
    body, = html.children
    line, = body.children
    img_1, img_2 = line.children
    assert img_1.position_x == 50
    assert img_2.position_x == 90


@SUITE.test
def test_text_indent():
    for indent in ['12px', '6%']:  # 6% of 200px is 12px
        page, = parse('''
            <style>
                @page { size: 220px }
                body { margin: 10px; text-indent: %(indent)s }
            </style>
            <p>Some text that is long enough that it take at least three line,
               but maybe more.
        ''' % {'indent': indent})
        html = page.root_box
        body, = html.children
        paragraph, = body.children
        lines = paragraph.children
        text_1, = lines[0].children
        text_2, = lines[1].children
        text_3, = lines[2].children
        assert text_1.position_x == 22  # 10px margin-left + 12px indent
        assert text_2.position_x == 10  # No indent
        assert text_3.position_x == 10  # No indent
