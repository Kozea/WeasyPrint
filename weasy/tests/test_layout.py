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

from .testing_utils import (
    TestPNGDocument, resource_filename, FONTS, assert_no_logs, capture_logs)
from .test_boxes import monkeypatch_validation
from ..formatting_structure import boxes
from ..layout.inlines import split_inline_box
from ..layout.percentages import resolve_percentages
from ..layout.preferred import (inline_preferred_width,
                                inline_preferred_minimum_width)


SUITE = Tests()
SUITE.context(assert_no_logs)


def body_children(page):
    """Take a ``page``  and return its <body>’s children."""
    html, = page.children
    assert html.element_tag == 'html'
    body, = html.children
    assert body.element_tag == 'body'
    return body.children


def parse_without_layout(html_content):
    """Parse some HTML, apply stylesheets, transform to boxes."""
    return TestPNGDocument.from_string(html_content)


def validate_absolute_and_float(
        real_non_shorthand, name, values, required=False):
    """Fake validator for ``absolute`` and ``float``."""
    value = values[0].value
    if (name == 'position' and value == 'absolute'
            ) or (name == 'float' and value == 'left'):
        return [(name, value)]
    return real_non_shorthand(name, values, required)


def parse(html_content, return_document=False):
    """Parse some HTML, apply stylesheets, transform to boxes and lay out."""
    # TODO: remove this patching when asbolute and floats are validated
    with monkeypatch_validation(validate_absolute_and_float):
        document = TestPNGDocument.from_string(html_content)
        document.base_url = resource_filename('<inline HTML>')
        if return_document:
            return document
        else:
            return document.pages


@SUITE.test
def test_page():
    """Test the layout for ``@page`` properties."""
    pages = parse('<p>')
    page = pages[0]
    assert isinstance(page, boxes.PageBox)
    assert int(page.outer_width) == 793  # A4: 210 mm in pixels
    assert int(page.outer_height) == 1122  # A4: 297 mm in pixels

    page, = parse('''<style>@page { -weasy-size: 2in 10in; }</style>''')
    assert page.outer_width == 192
    assert page.outer_height == 960

    page, = parse('''<style>@page { -weasy-size: 242px; }</style>''')
    assert page.outer_width == 242
    assert page.outer_height == 242

    page, = parse('''<style>@page { -weasy-size: letter; }</style>''')
    assert page.outer_width == 816  # 8.5in
    assert page.outer_height == 1056  # 11in

    page, = parse('''<style>@page { -weasy-size: letter portrait; }</style>''')
    assert page.outer_width == 816  # 8.5in
    assert page.outer_height == 1056  # 11in

    page, = parse('''<style>@page { -weasy-size: letter landscape; }</style>''')
    assert page.outer_width == 1056  # 11in
    assert page.outer_height == 816  # 8.5in

    page, = parse('''<style>@page { -weasy-size: portrait; }</style>''')
    assert int(page.outer_width) == 793  # A4: 210 mm
    assert int(page.outer_height) == 1122  # A4: 297 mm

    page, = parse('''<style>@page { -weasy-size: landscape; }</style>''')
    assert int(page.outer_width) == 1122  # A4: 297 mm
    assert int(page.outer_height) == 793  # A4: 210 mm

    page, = parse('''
        <style>@page { -weasy-size: 200px 300px; margin: 10px 10% 20% 1in }
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

    html, = page.children
    assert html.element_tag == 'html'
    assert html.position_x == 96  # 1in
    assert html.position_y == 10
    assert html.width == 84

    body, = html.children
    assert body.element_tag == 'body'
    assert body.position_x == 96  # 1in
    assert body.position_y == 10
    # body has margins in the UA stylesheet
    assert body.margin_left == 8
    assert body.margin_right == 8
    assert body.margin_top == 8
    assert body.margin_bottom == 8
    assert body.width == 68

    paragraph, = body.children
    assert paragraph.element_tag == 'p'
    assert paragraph.position_x == 104  # 1in + 8px
    assert paragraph.position_y == 18  # 10px + 8px
    assert paragraph.width == 68

    page, = parse('''
        <style>
            @page { -weasy-size: 100px; margin: 1px 2px; padding: 4px 8px;
                    border-width: 16px 32px; border-style: solid }
        </style>
        <body>
    ''')
    assert page.width == 16  # 100 - 2 * 42
    assert page.height == 58  # 100 - 2 * 21
    html, = page.children
    assert html.element_tag == 'html'
    assert html.position_x == 42  # 2 + 8 + 32
    assert html.position_y == 21  # 1 + 4 + 16


@SUITE.test
def test_block_widths():
    """Test the blocks widths."""
    page, = parse('''
        <style>
            @page { margin: 0; -weasy-size: 120px 2000px }
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
    html, = page.children
    assert html.element_tag == 'html'
    body, = html.children
    assert body.element_tag == 'body'
    assert body.width == 120

    divs = body.children

    paragraphs = []
    for div in divs:
        assert isinstance(div, boxes.BlockBox)
        assert div.element_tag == 'div'
        assert div.width == 100
        for paragraph in div.children:
            assert isinstance(paragraph, boxes.BlockBox)
            assert paragraph.element_tag == 'p'
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
            @page { margin: 0; -weasy-size: 100px 2000px }
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
    html, = page.children
    assert html.element_tag == 'html'
    body, = html.children
    assert body.element_tag == 'body'

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
    html, = page.children
    assert html.element_tag == 'html'
    body, = html.children
    assert body.element_tag == 'body'

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
    list_item, = unordered_list.children
    line, = list_item.children
    marker, content = line.children
    assert marker.text == u'◦'
    assert marker.margin_left == 0
    assert marker.margin_right == 8
    assert content.text == u'abc'

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
    list_item, = unordered_list.children
    marker = list_item.outside_list_marker
    font_size = marker.style.font_size
    assert marker.margin_right == 0.5 * font_size  # 0.5em
    assert marker.position_x == (
        list_item.padding_box_x() - marker.width - marker.margin_right)
    assert marker.position_y == list_item.position_y
    assert marker.text == u'•'
    line, = list_item.children
    content, = line.children
    assert content.text == u'abc'


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
    assert len(paragraph.children) == 0
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
    html, = page.children
    body, = html.children
    paragraph, = body.children
    assert len(list(paragraph.children)) == 3

    lines = paragraph.children
    for line in lines:
        assert line.style.font_size == 13
        assert line.element_tag == 'p'
        for child in line.children:
            assert child.element_tag in ('em', 'p')
            assert child.style.font_size == 13
            if isinstance(child, boxes.ParentBox):
                for child_child in child.children:
                    assert child.element_tag in ('em', 'strong', 'span')
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

    text = ' '.join(
        (''.join(box.text for box in line.descendants()
                 if isinstance(box, boxes.TextBox)))
        for line in lines)
    assert text == 'Lorem Ipsumis very coool'


@SUITE.test
def test_linebox_positions():
    """Test the position of line boxes."""
    for width, expected_lines in [(165, 2), (1, 5), (0, 5)]:
        page = u'''
            <style>
                p { width:%(width)spx; font-family:%(fonts)s;
                    line-height: 20px }
            </style>
            <p>this is test for <strong>Weasyprint</strong></p>'''
        page, = parse(page % {'fonts': FONTS, 'width': width})
        paragraph, = body_children(page)
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
    assert pre.element_tag == 'pre'
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
    assert pre.element_tag == 'p'
    lines = pre.children
    assert all(isinstance(line, boxes.LineBox) for line in lines)
    assert len(lines) == 7
    assert [line.height for line in lines] == [42] * 7


@SUITE.test
def test_page_breaks():
    """Test the page breaks."""
    pages = parse('''
        <style>
            @page { -weasy-size: 100px; margin: 10px }
            body { margin: 0 }
            div { height: 30px; font-size: 20px; }
        </style>
        <div>1</div>
        <div>2</div>
        <div>3</div>
        <div>4</div>
        <div>5</div>
    ''')
    page_divs = []
    for page in pages:
        divs = body_children(page)
        assert all([div.element_tag == 'div' for div in divs])
        assert all([div.position_x == 10 for div in divs])
        page_divs.append(divs)

    positions_y = [[div.position_y for div in divs] for divs in page_divs]
    assert positions_y == [[10, 40], [10, 40], [10]]

    # Same as above, but no content inside each <div>.
    # TODO: This currently gives no page break. Should it?
#    pages = parse('''
#        <style>
#            @page { -weasy-size: 100px; margin: 10px }
#            body { margin: 0 }
#            div { height: 30px }
#        </style>
#        <div/><div/><div/><div/><div/>
#    ''')
#    page_divs = []
#    for page in pages:
#        divs = body_children(page)
#        assert all([div.element_tag == 'div' for div in divs])
#        assert all([div.position_x == 10 for div in divs])
#        page_divs.append(divs)

#    positions_y = [[div.position_y for div in divs] for divs in page_divs]
#    assert positions_y == [[10, 40], [10, 40], [10]]

    page_1, page_2, page_3, page_4 = parse('''
        <style>
            @page { margin: 10px }
            @page :left { margin-left: 50px }
            @page :right { margin-right: 50px }

            html { page-break-before: left }
            div { page-break-after: left }
            ul { page-break-before: always }
        </style>
        <div>1</div>
        <p>2</p>
        <p>3</p>
        <ul><li>4</li></ul>
    ''')

    # The first page is a right page on rtl, but not here because of
    # page-break-before on the root element.
    assert page_1.margin_left == 50  # left page
    assert page_1.margin_right == 10
    html, = page_1.children
    body, = html.children
    div, = body.children
    line, = div.children
    text, = line.children
    assert div.element_tag == 'div'
    assert text.text == '1'

    assert page_2.margin_left == 10
    assert page_2.margin_right == 50  # right page
    assert not page_2.children  # empty page to get to a left page

    assert page_3.margin_left == 50  # left page
    assert page_3.margin_right == 10
    html, = page_3.children
    body, = html.children
    p_1, p_2 = body.children
    assert p_1.element_tag == 'p'
    assert p_2.element_tag == 'p'

    assert page_4.margin_left == 10
    assert page_4.margin_right == 50  # right page
    html, = page_4.children
    body, = html.children
    ulist, = body.children
    assert ulist.element_tag == 'ul'


@SUITE.test
def test_inlinebox_spliting():
    """Test the inline boxes spliting."""
    def get_inlinebox(content):
        """Helper returning a inlinebox with customizable style."""
        page = u'<style>p { font-family:%(fonts)s;}</style>'
        page = '%s <p>%s</p>' % (page, content)
        document = parse_without_layout(page % {'fonts': FONTS})
        html = document.formatting_structure
        body, = html.children
        paragraph, = body.children
        line, = paragraph.children
        inline, = line.children
        paragraph.width = 200
        paragraph.height = 'auto'
        return document, inline, paragraph

    def get_parts(document, inlinebox, width, parent):
        """Yield the parts of the splitted ``inlinebox`` of given ``width``."""
        skip = None
        while 1:
            box, skip, _ = split_inline_box(
                document, inlinebox, 0, width, skip, parent, None)
            yield box
            if skip is None:
                break

    def get_joined_text(parts):
        """Get the joined text from ``parts``."""
        return ''.join(part.children[0].text for part in parts)

    def test_inlinebox_spacing(inlinebox, value, side):
        """Test the margin, padding and border-width of ``inlinebox``."""
        if side in ['left', 'right']:
            # Vertical margins on inlines are irrelevant.
            assert getattr(inlinebox, 'margin_%s' % side) == value
        assert getattr(inlinebox, 'padding_%s' % side) == value
        assert getattr(inlinebox, 'border_%s_width' % side) == value

    content = '''<strong>WeasyPrint is a free software visual rendering engine
              for HTML and CSS</strong>'''

    document, inlinebox, parent = get_inlinebox(content)
    resolve_percentages(inlinebox, parent)
    original_text = inlinebox.children[0].text

    # test with width = 1000
    parts = list(get_parts(document, inlinebox, 1000, parent))
    assert len(parts) == 1
    assert original_text == get_joined_text(parts)

    document, inlinebox, parent = get_inlinebox(content)
    resolve_percentages(inlinebox, parent)
    original_text = inlinebox.children[0].text

    # test with width = 100
    parts = list(get_parts(document, inlinebox, 100, parent))
    assert len(parts) > 1
    assert original_text == get_joined_text(parts)

    document, inlinebox, parent = get_inlinebox(content)
    resolve_percentages(inlinebox, parent)
    original_text = inlinebox.children[0].text

    # test with width = 10
    parts = list(get_parts(document, inlinebox, 10, parent))
    assert len(parts) > 1
    assert original_text == get_joined_text(parts)

    # test with width = 0
    parts = list(get_parts(document, inlinebox, 0, parent))
    assert len(parts) > 1
    assert original_text == get_joined_text(parts)

    # with margin-border-padding
    content = '''<strong style="border:10px solid; margin:10px; padding:10px">
              WeasyPrint is a free software visual rendering engine
              for HTML and CSS</strong>'''

    document, inlinebox, parent = get_inlinebox(content)
    resolve_percentages(inlinebox, parent)
    original_text = inlinebox.children[0].text
    # test with width = 1000
    parts = list(get_parts(document, inlinebox, 1000, parent))
    assert len(parts) == 1
    assert original_text == get_joined_text(parts)
    for side in ('left', 'top', 'bottom', 'right'):
        test_inlinebox_spacing(parts[0], 10, side)

    document, inlinebox, parent = get_inlinebox(content)
    resolve_percentages(inlinebox, parent)
    original_text = inlinebox.children[0].text

    # test with width = 1000
    parts = list(get_parts(document, inlinebox, 100, parent))
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
    document = parse_without_layout('''
        <style>p { width: 200px; font-family:%(fonts)s;}</style>
        <p><strong><em><em><em>
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13
        </em></em></em></strong></p>
    ''' % {'fonts': FONTS})
    html = document.formatting_structure
    body, = html.children
    paragraph, = body.children
    line, = paragraph.children
    inlinebox, = line.children
    paragraph.width = 200
    paragraph.height = 'auto'
    resolve_percentages(inlinebox, paragraph)

    original_text = ''.join(
        part.text for part in inlinebox.descendants()
        if isinstance(part, boxes.TextBox))

    # test with width = 10
    parts = []
    skip = None
    while 1:
        box, skip, _ = split_inline_box(
            document, inlinebox, 0, 100, skip, paragraph, None)
        parts.append(box)
        if skip is None:
            break
    assert len(parts) > 2
    assert ''.join(
        child.text
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
            @page { -weasy-size: 100px; margin:2px; border:1px solid }
            body { margin: 0 }
        </style>
        <div><span/>1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15</div>
    ''' % {'fonts': FONTS})

    texts = []
    for page in pages:
        html, = page.children
        body, = html.children
        div, = body.children
        lines = div.children
        for line in lines:
            line_texts = []
            for child in line.descendants():
                if isinstance(child, boxes.TextBox):
                    line_texts.append(child.text)
            texts.append(''.join(line_texts))

    assert len(pages) == 2
    assert ' '.join(texts) == \
        '1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15'


@SUITE.test
def test_whitespace_processing():
    """Test various spaces and tabulations processing."""
    for source in ['a', '  a  ', ' \n  \ta', ' a\t ']:
        page, = parse('<p><em>%s</em></p>' % source)
        html, = page.children
        body, = html.children
        p, = body.children
        line, = p.children
        em, = line.children
        text, = em.children
        assert text.text == 'a', 'source was %r' % (source,)

        page, = parse('<p style="white-space: pre-line">\n\n<em>%s</em></pre>'
            % source.replace('\n', ' '))
        html, = page.children
        body, = html.children
        p, = body.children
        _line1, _line2, line3 = p.children
        em, = line3.children
        text, = em.children
        assert text.text == 'a', 'source was %r' % (source,)


@SUITE.test
def test_with_images():
    """Test that width, height and ratio of images are respected."""
    # Try a few image formats
    for url in ['pattern.png', 'pattern.gif', 'pattern.jpg', 'pattern.svg',
                "data:image/svg+xml,<svg width='4' height='4'></svg>",
                "data:image/svg+xml,<svg width='4px' height='4px'></svg>",
                ]:
        page, = parse('<img src="%s">' % url)
        html, = page.children
        body, = html.children
        line, = body.children
        img, = line.children
        assert img.width == 4
        assert img.height == 4

    # With physical units
    url = "data:image/svg+xml,<svg width='2.54cm' height='0.5in'></svg>"
    page, = parse('<img src="%s">' % url)
    html, = page.children
    body, = html.children
    line, = body.children
    img, = line.children
    assert img.width == 96
    assert img.height == 48

    # Invalid images
    for url in [
        'inexistant.png',
        'unknownprotocol://weasyprint.org/foo.png',
        'data:image/unknowntype,Not an image',
        # zero-byte images
        'data:image/png,',
        'data:image/jpeg,',
        'data:image/svg+xml,',
        # Incorrect format
        'data:image/png,Not a PNG',
        'data:image/jpeg,Not a JPEG',
        'data:image/svg+xml,<svg>invalid xml',
        # Unsupported units (yet) in CairoSVG
        'data:image/svg+xml,<svg width="100%" height="100%"></svg>',
        'data:image/svg+xml,<svg width="20em" height="10em"></svg>',
        'data:image/svg+xml,<svg width="20ex" height="10ex"></svg>',
    ]:
        with capture_logs() as logs:
            page, = parse("<p><img src='%s' alt='invalid image'>" % url)
        assert len(logs) == 1
        if url.startswith('data:'):
            assert 'WARNING: Error while parsing an image' in logs[0]
        else:
            assert 'WARNING: Error while fetching an image' in logs[0]
        html, = page.children
        body, = html.children
        paragraph, = body.children
        line, = paragraph.children
        img, = line.children
        text, = img.children
        assert text.text == 'invalid image', url

    # Layout rules try to preserve the ratio, so the height should be 40px too:
    page, = parse('<img src="pattern.png" style="width: 40px">')
    html, = page.children
    body, = html.children
    line, = body.children
    img, = line.children
    assert body.height == 40
    assert img.position_y == 0
    assert img.width == 40
    assert img.height == 40

    page, = parse('''
        <img src="pattern.png" style="width: 40px">
        <img src="pattern.png" style="width: 60px">
    ''')
    html, = page.children
    body, = html.children
    line, = body.children
    img_1, img_2 = line.children
    assert body.height == 60
    assert img_1.width == 40
    assert img_1.height == 40
    assert img_2.width == 60
    assert img_2.height == 60
    assert img_1.position_y == 20
    assert img_2.position_y == 0


@SUITE.test
def test_vertical_align():
    """Test various values of vertical-align."""
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

    # Same as previously, but with percentages
    page, = parse('''
        <span style="line-height: 10px">
            <img src="pattern.png" style="width: 40px; vertical-align: -150%">
            <img src="pattern.png" style="width: 60px">
        </span>
    ''')
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

    # Same again, but have the vertical-align on an inline box.
    page, = parse('''
        <span style="line-height: 10px">
            <span style="line-height: 10px; vertical-align: -15px">
                <img src="pattern.png" style="width: 40px">
            </span>
            <img src="pattern.png" style="width: 60px">
        </span>
    ''')
    html, = page.children
    body, = html.children
    line, = body.children
    span_1, = line.children
    span_2, _whitespace, img_1 = span_1.children
    img_1, = span_2.children
    assert img_1.height == 40
    assert img_2.height == 60
    assert img_1.position_y == 35
    assert img_2.position_y == 0
    assert line.height == 75
    assert body.height == line.height

    # Same as previously, but with percentages
    page, = parse('''
        <span style="line-height: 12px; font-size: 12px">
            <img src="pattern.png" style="width: 40px; vertical-align: middle">
            <img src="pattern.png" style="width: 60px">
        </span>
    ''')
    html, = page.children
    body, = html.children
    line, = body.children
    span, = line.children
    img_1, img_2 = span.children
    assert img_1.height == 40
    assert img_2.height == 60
    # middle of the image (position_y + 20) is at half the ex-height above
    # the baseline of the parent. Currently the ex-height is 0.5em
    # TODO: update this when we actually get ex form the font metrics
    assert img_1.position_y == 37  # 60 - 0.5 * 0.5 * font-size - 40/2
    assert img_2.position_y == 0
    assert line.height == 77
    assert body.height == line.height

    # sup and sub currently mean +/- 0.5 em
    # With the initial 16px font-size, that’s 8px.
    page, = parse('''
        <span style="line-height: 10px">
            <img src="pattern.png" style="width: 60px">
            <img src="pattern.png" style="width: 40px; vertical-align: super">
            <img src="pattern.png" style="width: 40px; vertical-align: sub">
        </span>
    ''')
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

    # Pango gives a height of 19px for font-size of 16px
    page, = parse('''
        <span style="line-height: 10px">
            <img src="pattern.png" style="vertical-align: text-top">
            <img src="pattern.png" style="vertical-align: text-bottom">
        </span>
    ''')
    html, = page.children
    body, = html.children
    line, = body.children
    span, = line.children
    img_1, img_2 = span.children
    assert img_1.height == 4
    assert img_2.height == 4
    assert img_1.position_y == 0
    assert img_2.position_y == 15  # 19 - 4
    assert line.height == 19
    assert body.height == line.height

    # This case used to cause an exception:
    # The second span has no children but should count for line heights
    # since it has padding.
    page, = parse('<span><span style="padding: 1px"></span></span>')
    html, = page.children
    body, = html.children
    line, = body.children
    span_1, = line.children
    span_2, = span_1.children
    assert span_1.height == 19
    assert span_2.height == 19


@SUITE.test
def test_text_align_left():
    """Test the left text alignment."""

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
            @page { -weasy-size: 200px }
        </style>
        <body>
            <img src="pattern.png" style="width: 40px">
            <img src="pattern.png" style="width: 60px">
    ''')
    html, = page.children
    body, = html.children
    line, = body.children
    img_1, img_2 = line.children
    # initial value for text-align: left (in ltr text)
    assert img_1.position_x == 0
    assert img_2.position_x == 40


@SUITE.test
def test_text_align_right():
    """Test the right text alignment."""

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
            @page { -weasy-size: 200px }
            body { text-align: right }
        </style>
        <body>
            <img src="pattern.png" style="width: 40px">
            <img src="pattern.png" style="width: 60px">
    ''')
    html, = page.children
    body, = html.children
    line, = body.children
    img_1, img_2 = line.children
    assert img_1.position_x == 100  # 200 - 60 - 40
    assert img_2.position_x == 140  # 200 - 60


@SUITE.test
def test_text_align_center():
    """Test the center text alignment."""

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
            @page { -weasy-size: 200px }
            body { text-align: center }
        </style>
        <body>
            <img src="pattern.png" style="width: 40px">
            <img src="pattern.png" style="width: 60px">
    ''')
    html, = page.children
    body, = html.children
    line, = body.children
    img_1, img_2 = line.children
    assert img_1.position_x == 50
    assert img_2.position_x == 90


@SUITE.test
def test_text_align_justify():
    """Test justified text."""
    page, = parse('''
        <style>
            @page { -weasy-size: 300px 1000px }
            body { text-align: justify }
        </style>
        <p><img src="pattern.png" style="width: 40px"> &#20;
           <strong>
                <img src="pattern.png" style="width: 60px"> &#20;
                <img src="pattern.png" style="width: 10px"> &#20;
                <img src="pattern.png" style="width: 100px">
           </strong><img src="pattern.png" style="width: 290px">
            <!-- Last image will be on its own line. -->
    ''')
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


@SUITE.test
def test_word_spacing():
    """Test word-spacing."""
    # keep the empty <style> as a regression test: element.text is None
    # (Not a string.)
    page, = parse('''
        <style></style>
        <body><strong>Lorem ipsum dolor<em>sit amet</em></strong>
    ''')
    html, = page.children
    body, = html.children
    line, = body.children
    strong_1, = line.children
    assert 200 <= strong_1.width <= 250

    # TODO: Pango gives only half of word-spacing to a space at the end
    # of a TextBox. Is this what we want?
    page, = parse('''
        <style>strong { word-spacing: 11px }</style>
        <body><strong>Lorem ipsum dolor<em>sit amet</em></strong>
    ''')
    html, = page.children
    body, = html.children
    line, = body.children
    strong_2, = line.children
    assert strong_2.width - strong_1.width == 33


@SUITE.test
def test_letter_spacing():
    """Test letter-spacing."""
    page, = parse('''
        <body><strong>Supercalifragilisticexpialidocious></strong>
    ''')
    html, = page.children
    body, = html.children
    line, = body.children
    strong_1, = line.children
    assert 280 <= strong_1.width <= 310

    page, = parse('''
        <style>strong { letter-spacing: 11px }</style>
        <body><strong>Supercalifragilisticexpialidocious></strong>
    ''')
    html, = page.children
    body, = html.children
    line, = body.children
    strong_2, = line.children
    assert strong_2.width - strong_1.width == 34 * 11


@SUITE.test
def test_text_indent():
    """Test the text-indent property."""
    for indent in ['12px', '6%']:  # 6% of 200px is 12px
        page, = parse('''
            <style>
                @page { -weasy-size: 220px }
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


@SUITE.test
def test_inline_replaced_auto_margins():
    """Test that auto margins are ignored for inline replaced boxes."""
    page, = parse('''
        <style>
            @page { -weasy-size: 200px }
            img { display: inline; margin: auto; width: 50px }
        </style>
        <body>
          <img src="pattern.png" />
    ''')
    html, = page.children
    body, = html.children
    line, = body.children
    img, = line.children
    assert img.margin_top == 0
    assert img.margin_right == 0
    assert img.margin_bottom == 0
    assert img.margin_left == 0


@SUITE.test
def test_empty_inline_auto_margins():
    """Test that horizontal auto margins are ignored for empty inline boxes."""
    page, = parse('''
        <style>
            @page { -weasy-size: 200px }
            span { margin: auto }
        </style>
        <body><span></span>
    ''')
    html, = page.children
    body, = html.children
    block, = body.children
    span, = block.children
    assert span.margin_top != 0
    assert span.margin_right == 0
    assert span.margin_bottom != 0
    assert span.margin_left == 0


@SUITE.test
def test_box_sizing():
    """Test the box-sizing property.

    http://www.w3.org/TR/css3-ui/#box-sizing

    """
    page, = parse('''
        <style>
            @page { -weasy-size: 100000px }
            body { width: 10000px; margin: 0 }
            div { width: 10%; height: 1000px;
                  margin: 100px; padding: 10px; border: 1px solid }
            div+div { box-sizing: border-box }
        </style>
        <div></div><div></div>
    ''')
    html, = page.children
    body, = html.children
    div_1, div_2 = body.children
    assert div_1.width == 1000
    assert div_1.height == 1000
    assert div_1.border_width() == 1022
    assert div_1.border_height() == 1022
    assert div_1.margin_height() == 1222
    # Do not test margin_width as it depends on the containing block

    assert div_2.width == 978  # 1000 - 22
    assert div_2.height == 978
    assert div_2.border_width() == 1000
    assert div_2.border_height() == 1000
    assert div_2.margin_height() == 1200


@SUITE.test
def test_table_column_width():
    source = '''
        <style>
            body { width: 20000px; margin: 0 }
            table { width: 10000px; margin: 0 auto; border-spacing: 100px 0 }
            td { border: 10px solid; padding: 1px }
        </style>
        <table>
            <col style="width: 10%">
            <tr>
                <td style="width: 30%" colspan=3>
                <td>
            </tr>
            <tr>
                <td>
                <td>
                <td>
                <td>
            </tr>
            <tr>
                <td>
                <td colspan=12>This cell will be truncated to grid width
                <td>This cell will be removed as it is beyond the grid width
            </tr>
        </table>
    '''
    with capture_logs() as logs:
        page, = parse(source)
    assert len(logs) == 1
    assert logs[0] == ('WARNING: This table row has more columns than '
                       'the table, ignored 1 cells: (<TableCellBox td 22>,)')
    html, = page.children
    body, = html.children
    wrapper, = body.children
    table, = wrapper.children
    row_group, = table.children
    first_row, second_row, third_row = row_group.children
    cells = [first_row.children, second_row.children, third_row.children]
    assert len(first_row.children) == 2
    assert len(second_row.children) == 4
    # Third cell here is completly removed
    assert len(third_row.children) == 2

    assert body.position_x == 0
    assert wrapper.position_x == 0
    assert wrapper.margin_left == 5000
    assert wrapper.content_box_x() == 5000  # auto margin-left
    assert wrapper.width == 10000
    assert table.position_x == 5000
    assert table.width  == 10000
    assert row_group.position_x == 5100  # 5000 + border_spacing
    assert row_group.width == 9800  # 10000 - 2*border-spacing
    assert first_row.position_x == row_group.position_x
    assert first_row.width == row_group.width

    # This cell has colspan=3
    assert cells[0][0].position_x == 5100  # 5000 + border-spacing
    # `width` on a cell sets the content width
    assert cells[0][0].width == 3000  # 30% of 10000px
    assert cells[0][0].border_width() == 3022  # 3000 + borders + padding

    # Second cell of the first line, but on the fourth and last column
    assert cells[0][1].position_x == 8222  # 5100 + 3022 + border-spacing
    assert cells[0][1].border_width() == 6678  # 10000 - 3022 - 3*100
    assert cells[0][1].width == 6656  # 6678 - borders - padding

    assert cells[1][0].position_x == 5100  # 5000 + border-spacing
    # `width` on a column sets the border width of cells
    assert cells[1][0].border_width() == 1000  # 10% of 10000px
    assert cells[1][0].width == 978  # 1000 - borders - padding

    assert cells[1][1].position_x == 6200  # 5100 + 1000 + border-spacing
    assert cells[1][1].border_width() == 911  # (3022 - 1000 - 2*100) / 2
    assert cells[1][1].width == 889  # 911 - borders - padding

    assert cells[1][2].position_x == 7211  # 6200 + 911 + border-spacing
    assert cells[1][2].border_width() == 911  # (3022 - 1000 - 2*100) / 2
    assert cells[1][2].width == 889  # 911 - borders - padding

    # Same as cells[0][1]
    assert cells[1][3].position_x == 8222  # Also 7211 + 911 + border-spacing
    assert cells[1][3].border_width() == 6678
    assert cells[1][3].width == 6656

    # Same as cells[1][0]
    assert cells[2][0].position_x == 5100
    assert cells[2][0].border_width() == 1000
    assert cells[2][0].width == 978

    assert cells[2][1].position_x == 6200  # Same as cells[1][1]
    assert cells[2][1].border_width() == 8700  # 1000 - 1000 - 3*border-spacing
    assert cells[2][1].width == 8678  # 8700 - borders - padding
    assert cells[2][1].colspan == 3  # truncated to grid width

    page, = parse('''
        <style>
            table { width: 1000px; border-spacing: 100px }
        </style>
        <table>
            <tr>
                <td style="width: 50%">
                <td style="width: 60%">
                <td>
            </tr>
        </table>
    ''')
    html, = page.children
    body, = html.children
    wrapper, = body.children
    table, = wrapper.children
    row_group, = table.children
    row, = row_group.children
    assert row.children[0].width == 500
    assert row.children[1].width == 600
    assert row.children[2].width == 0
    assert table.width == 1500 # 500 + 600 + 4 * border-spacing


    # Sum of columns width larger that the table width:
    # increase the table width
    for body_width, table_width in [('auto', '1000px'), ('1000px', 'auto')]:
        page, = parse('''
            <style>
                body { width: %(body_width)s }
                table { width: %(table_width)s; border-spacing: 100px }
                td { width: %(td_width)s }
            </style>
            <table>
                <tr>
                    <td>
                    <td>
                </tr>
            </table>
        ''' % {'body_width': body_width, 'table_width': table_width,
               'td_width': '60%'})
        html, = page.children
        body, = html.children
        wrapper, = body.children
        table, = wrapper.children
        row_group, = table.children
        row, = row_group.children
        cell_1, cell_2 = row.children
        assert cell_1.width == 600  # 60% of 1000px
        assert cell_2.width == 600
        assert table.width == 1500  # 600 + 600 + 3*border-spacing
        assert wrapper.width == table.width


@SUITE.test
def test_table_row_height():
    page, = parse('''
        <table style="width: 1000px; border-spacing: 0 100px;
                      font: 20px/1em serif; margin: 3px">
            <tr>
                <td rowspan=0 style="height: 420px; vertical-align: top">
                <td>X<br>X<br>X
                <td><div style="margin-top: 20px">X</div>
                <td style="vertical-align: top">X
                <td style="vertical-align: middle">X
                <td style="vertical-align: bottom">X
            </tr>
            <tr>
                <!-- cells with no text (no line boxes) is a corner case
                     in cell baselines -->
                <td style="padding: 15px"></td>
                <td><div style="height: 10px"></div></td>
            </tr>
            <tr></tr>
            <tr>
                <td style="vertical-align: bottom">
            </tr>
        </table>
    ''')
    html, = page.children
    body, = html.children
    wrapper, = body.children
    table, = wrapper.children
    row_group, = table.children

    assert wrapper.position_y == 0
    assert table.position_y == 3  # 0 + margin-top
    assert table.height == 620  # sum of row heigths + 5*border-spacing
    assert wrapper.height == table.height
    assert row_group.position_y == 103  # 3 + border-spacing
    assert row_group.height == 420  # 620 - 2*border-spacing
    assert [row.height for row in row_group.children] == [
        80, 30, 0, 10]
    assert [row.position_y for row in row_group.children] == [
        # cumulative sum of previous row heights and border-spacings
        103, 283, 413, 513]
    assert [[cell.height for cell in row.children]
            for row in row_group.children] == [
        [420, 60, 40, 20, 20, 20],
        [0, 10],
        [],
        [0]
    ]
    assert [[cell.border_height() for cell in row.children]
            for row in row_group.children] == [
        [420, 80, 80, 80, 80, 80],
        [30, 30],
        [],
        [10]
    ]
    # The baseline of the first row is at 40px because of the third column.
    # The second column thus gets a top padding of 20px pushes the bottom
    # to 80px.The middle is at 40px.
    assert [[cell.padding_top for cell in row.children]
            for row in row_group.children] == [
        [0, 20, 0, 0, 30, 60],
        [15, 5],
        [],
        [10]
    ]
    assert [[cell.padding_bottom for cell in row.children]
            for row in row_group.children] == [
        [0, 0, 40, 60, 30, 0],
        [15, 15],
        [],
        [0]
    ]
    assert [[cell.position_y for cell in row.children]
            for row in row_group.children] == [
        [103, 103, 103, 103, 103, 103],
        [283, 283],
        [],
        [513]
    ]


@SUITE.test
def test_table_wrapper():
    page, = parse('''
        <style>
            @page { -weasy-size: 1000px }
            table { /* width: auto; */ height: 500px;
                    padding: 1px; border: 10px solid; margin: 100px; }
        </style>
        <table></table>
    ''')
    html, = page.children
    body, = html.children
    wrapper, = body.children
    table, = wrapper.children
    assert body.width == 1000
    assert wrapper.margin_width() == 1000
    assert wrapper.width == 800  # 1000 - 2*100, no borders or padding
    assert table.margin_width() == 800
    assert table.width == 778  # 800 - 2*10 - 2*1, no margin
    # box-sizing in the UA stylesheet  makes `height: 500px` set this
    assert table.border_height() == 500
    assert table.height == 478  # 500 - 2*10 - 2*1
    assert table.margin_height() == 500  # no margin
    assert wrapper.height == 500
    assert wrapper.margin_height() == 700  # 500 + 2*100

    # Non-regression test: this used to cause an exception
    page, = parse('<html style="display: table">')


@SUITE.test
def test_margin_boxes_fixed_dimension():
    # Corner boxes
    page, = parse('''
        <style>
            @page {
                @top-left-corner {
                    content: 'top_left';
                    padding: 10px;
                }
                @top-right-corner {
                    content: 'top_right';
                    padding: 10px;
                }
                @bottom-left-corner {
                    content: 'bottom_left';
                    padding: 10px;
                }
                @bottom-right-corner {
                    content: 'bottom_right';
                    padding: 10px;
                }

                -weasy-size: 1000px;
                margin-top: 10%;
                margin-bottom: 40%;
                margin-left: 20%;
                margin-right: 30%;
            }
        </style>
    ''')
    html, top_left, top_right, bottom_left, bottom_right = page.children
    for margin_box, text in zip(
            [top_left, top_right, bottom_left, bottom_right],
            ['top_left', 'top_right', 'bottom_left', 'bottom_right']):

        line, = margin_box.children
        text, = line.children
        assert text == text

    # Check positioning and Rule 1 for fixed dimensions
    assert top_left.position_x == 0
    assert top_left.position_y == 0
    assert top_left.margin_width() == 200  # margin-left
    assert top_left.margin_height() == 100  # margin-top

    assert top_right.position_x == 700  # size-x - margin-right
    assert top_right.position_y == 0
    assert top_right.margin_width() == 300  # margin-right
    assert top_right.margin_height() == 100  # margin-top

    assert bottom_left.position_x == 0
    assert bottom_left.position_y == 600  # size-y - margin-bottom
    assert bottom_left.margin_width() == 200  # margin-left
    assert bottom_left.margin_height() == 400  # margin-bottom

    assert bottom_right.position_x == 700  # size-x - margin-right
    assert bottom_right.position_y == 600  # size-y - margin-bottom
    assert bottom_right.margin_width() == 300  # margin-right
    assert bottom_right.margin_height() == 400  # margin-bottom

    # Test rules 2 and 3
    page, = parse('''
        <style>
            @page {
                margin: 100px 200px;
                @bottom-left-corner {
                    content: "";
                    margin: 60px
                }
            }
        </style>
    ''')
    html, margin_box = page.children
    assert margin_box.margin_width() == 200
    assert margin_box.margin_left == 60
    assert margin_box.margin_right == 60
    assert margin_box.width == 80 # 200 - 60 - 60

    assert margin_box.margin_height() == 100
    # total was too big, the outside margin was ignored:
    assert margin_box.margin_top == 60
    assert margin_box.margin_bottom == 40  # Not 60
    assert margin_box.height == 0  # But not negative

    # Test rule 3 with a non-auto inner dimension
    page, = parse('''
        <style>
            @page {
                margin: 100px;
                @left-middle {
                    content: "";
                    margin: 10px;
                    width: 130px;
                }
            }
        </style>
    ''')
    html, margin_box = page.children
    assert margin_box.margin_width() == 100
    assert margin_box.margin_left == -40  # Not 10px
    assert margin_box.margin_right == 10
    assert margin_box.width == 130  # As specified

    # Test rule 4
    page, = parse('''
        <style>
            @page {
                margin: 100px;
                @left-bottom {
                    content: "";
                    margin-left: 10px;
                    margin-right: auto;
                    width: 70px;
                }
            }
        </style>
    ''')
    html, margin_box = page.children
    assert margin_box.margin_width() == 100
    assert margin_box.margin_left == 10  # 10px this time, no over-constrain
    assert margin_box.margin_right == 20
    assert margin_box.width == 70  # As specified

    # Test rules 2, 3 and 4
    page, = parse('''
        <style>
            @page {
                margin: 100px;
                @right-top {
                    content: "";
                    margin-right: 10px;
                    margin-left: auto;
                    width: 130px;
                }
            }
        </style>
    ''')
    html, margin_box = page.children
    assert margin_box.margin_width() == 100
    assert margin_box.margin_left == 0  # rule 2
    assert margin_box.margin_right == -30  # rule 3, after rule 2
    assert margin_box.width == 130  # As specified

    # Test rule 5
    page, = parse('''
        <style>
            @page {
                margin: 100px;
                @top-left {
                    content: "";
                    margin-top: 10px;
                    margin-bottom: auto;
                }
            }
        </style>
    ''')
    html, margin_box = page.children
    assert margin_box.margin_height() == 100
    assert margin_box.margin_top == 10
    assert margin_box.margin_bottom == 0
    assert margin_box.height == 90

    # Test rule 5
    page, = parse('''
        <style>
            @page {
                margin: 100px;
                @top-center {
                    content: "";
                    margin: auto 0;
                }
            }
        </style>
    ''')
    html, margin_box = page.children
    assert margin_box.margin_height() == 100
    assert margin_box.margin_top == 0
    assert margin_box.margin_bottom == 0
    assert margin_box.height == 100

    # Test rule 6
    page, = parse('''
        <style>
            @page {
                margin: 100px;
                @bottom-right {
                    content: "";
                    margin: auto;
                    height: 70px;
                }
            }
        </style>
    ''')
    html, margin_box = page.children
    assert margin_box.margin_height() == 100
    assert margin_box.margin_top == 15
    assert margin_box.margin_bottom == 15
    assert margin_box.height == 70

    # Rule 2 inhibits rule 6
    page, = parse('''
        <style>
            @page {
                margin: 100px;
                @bottom-center {
                    content: "";
                    margin: auto 0;
                    height: 150px;
                }
            }
        </style>
    ''')
    html, margin_box = page.children
    assert margin_box.margin_height() == 100
    assert margin_box.margin_top == 0
    assert margin_box.margin_bottom == -50  # outside
    assert margin_box.height == 150


@SUITE.test
def test_preferred_widths():
    """Unit tests for preferred widths."""
    document = parse(u'''
        <p style="white-space: pre-line">
            Lorem ipsum dolor sit amet,
              consectetur elit
        </p>
                   <!--  ^  No-break space here  -->
    ''', return_document=True)
    # Non-laid-out boxes:
    body, = document.formatting_structure.children
    paragraph, = body.children
    line, = paragraph.children
    text, = line.children
    assert text.text == u'\nLorem ipsum dolor sit amet,\nconsectetur elit\n'

    minimum = inline_preferred_minimum_width(line)
    preferred = inline_preferred_width(line)
    # Not exact, depends on the installed fonts
    assert 120 < minimum < 140
    assert 220 < preferred < 240


@SUITE.test
def test_margin_boxes_variable_dimension():
    page, = parse('''
        <style>
            @page {
                -weasy-size: 800px;
                margin: 100px;
                padding: 42px;
                border: 7px solid;

                @top-left {
                    content: "";
                }
                @top-center {
                    content: "";
                }
                @top-right {
                    content: "";
                }
            }
        </style>
    ''')
    html, top_left, top_right, top_center = page.children
    assert top_left.at_keyword == '@top-left'
    assert top_center.at_keyword == '@top-center'
    assert top_right.at_keyword == '@top-right'

    assert top_left.margin_width() == 200
    assert top_center.margin_width() == 200
    assert top_right.margin_width() == 200

    page, = parse('''
        <style>
            @page {
                -weasy-size: 800px;
                margin: 100px;
                padding: 42px;
                border: 7px solid;

                @top-left {
                    content: "HeyHey";
                }
                @top-center {
                    content: "Hey";
                }
                @top-right {
                    content: "";
                }
            }
        </style>
    ''')
    html, top_left, top_right, top_center = page.children
    assert top_left.at_keyword == '@top-left'
    assert top_center.at_keyword == '@top-center'
    assert top_right.at_keyword == '@top-right'

    assert top_left.margin_width() == 240
    assert top_center.margin_width() == 120
    assert top_right.margin_width() == 240

    page, = parse('''
        <style>
            @page {
                -weasy-size: 800px;
                margin: 100px;
                padding: 42px;
                border: 7px solid;

                @top-left {
                    content: "Lorem";
                }
                @top-right {
                    content: "Lorem";
                }
            }
        </style>
    ''')
    html, top_left, top_right = page.children
    assert top_left.at_keyword == '@top-left'
    assert top_right.at_keyword == '@top-right'

    assert top_left.margin_width() == 300
    assert top_right.margin_width() == 300

    page, = parse('''
        <style>
            @page {
                -weasy-size: 800px;
                margin: 100px;
                padding: 42px;
                border: 7px solid;

                @top-left {
                    content: "HelloHello";
                }
                @top-right {
                    content: "Hello";
                }
            }
        </style>
    ''')
    html, top_left, top_right = page.children
    assert top_left.margin_width() == 400
    assert top_right.margin_width() == 200

    page, = parse('''
        <style>
            @page {
                -weasy-size: 800px;
                margin: 100px;
                padding: 42px;
                border: 7px solid;

                @top-left {
                    content: url('data:image/svg+xml, \
                                    <svg width="10" height="10"></svg>');
                }
                @top-right {
                    content: url('data:image/svg+xml, \
                                    <svg width="30" height="10"></svg>');
                }
            }
        </style>
    ''')
    html, top_left, top_right = page.children
    assert top_left.margin_width() == 150
    assert top_right.margin_width() == 450

    page, = parse('''
        <style>
            @page {
                -weasy-size: 800px;
                margin: 100px;

                @top-left {
                    width: 150px;
                }
                @top-right {
                    width: 250px;
                }
            }
        </style>
    ''')
    html, top_left, top_right = page.children
    assert top_left.margin_width() == 150
    assert top_right.margin_width() == 250

    page, = parse('''
        <style>
            @page {
                -weasy-size: 800px;
                margin: 100px;

                @top-left {
                    margin: auto;
                    width: 100px;
                }
                @top-center {
                    margin-left: auto;
                }
                @top-right {
                    width: 200px;
                }
            }
        </style>
    ''')
    html, top_left, top_right = page.children
    # 300 pixels evenly distributed over the 3 margins
    assert top_left.margin_left == 100
    assert top_left.margin_right == 100
    assert top_left.width == 100
    assert top_right.margin_left == 0
    assert top_right.margin_right == 0
    assert top_right.width == 200

    page, = parse('''
        <style>
            @page {
                -weasy-size: 800px;
                margin: 100px;

                @top-left {
                    margin: auto;
                    width: 500px;
                }
                @top-center {
                    margin-left: auto;
                }
                @top-right {
                    width: 400px;
                }
            }
        </style>
    ''')
    html, top_left, top_right = page.children
    # -300 pixels evenly distributed over the 3 margins
    assert top_left.margin_left == -100
    assert top_left.margin_right == -100
    assert top_left.width == 500
    assert top_right.margin_left == 0
    assert top_right.margin_right == 0
    assert top_right.width == 400

    page, = parse('''
        <style>
            @page {
                -weasy-size: 800px;
                margin: 100px;
                padding: 42px;
                border: 7px solid;

                @top-left {
                    content: url('data:image/svg+xml, \
                                    <svg width="450" height="10"></svg>');
                }
                @top-right {
                    content: url('data:image/svg+xml, \
                                    <svg width="350" height="10"></svg>');
                }
            }
        </style>
    ''')
    html, top_left, top_right = page.children
    # -200 pixels evenly distributed over the 2 added margins
    assert top_left.margin_left == 0
    assert top_left.margin_right == -100
    assert top_left.width == 450
    assert top_right.margin_left == -100
    assert top_right.margin_right == 0
    assert top_right.width == 350

    page, = parse('''
        <style>
            @page {
                -weasy-size: 800px;
                margin: 100px;
                padding: 42px;
                border: 7px solid;

                @top-left {
                    content: url('data:image/svg+xml, \
                                    <svg width="100" height="10"></svg>');
                    border-right: 50px solid;
                    margin: auto;
                }
                @top-right {
                    content: url('data:image/svg+xml, \
                                    <svg width="200" height="10"></svg>');
                    margin-left: 30px;
                }
            }
        </style>
    ''')
    html, top_left, top_right = page.children
    assert top_left.margin_left == 110
    assert top_left.margin_right == 110
    assert top_left.width == 100
    assert top_left.margin_width() == 370
    assert top_right.margin_left == 30
    assert top_right.margin_right == 0
    assert top_right.width == 200
    assert top_right.margin_width() == 230


@SUITE.test
def test_margin_boxes_vertical_align():
    """
         3 px ->    +-----+
                    |  1  |
                    +-----+

                43 px ->   +-----+
                53 px ->   |  2  |
                           +-----+

                       83 px ->   +-----+
                                  |  3  |
                       103px ->   +-----+
    """
    page, = parse('''
        <style>
            @page {
                -weasy-size: 800px;
                margin: 106px;  /* margin boxes’ content height is 100px */

                @top-left {
                    content: "foo"; line-height: 20px; border: 3px solid;
                    vertical-align: top;
                }
                @top-center {
                    content: "foo"; line-height: 20px; border: 3px solid;
                    vertical-align: middle;
                }
                @top-right {
                    content: "foo"; line-height: 20px; border: 3px solid;
                    vertical-align: bottom;
                }
            }
        </style>
    ''')
    html, top_left, top_right, top_center = page.children
    line_1, = top_left.children
    line_2, = top_center.children
    line_3, = top_right.children
    assert line_1.position_y == 3
    assert line_2.position_y == 43
    assert line_3.position_y == 83
