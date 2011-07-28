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


from attest import Tests, assert_hook

from ..document import PNGDocument
from ..formatting_structure import boxes
from ..layout import inline_formatting_contex


suite = Tests()


def parse(html_content):
    """
    Parse some HTML, apply stylesheets, transform to boxes and do layout.
    """
    document = PNGDocument.from_string(html_content)
    document.do_layout()
    return document.pages


@suite.test
def test_page():
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
        <style>@page { size: 200px 300px; margin: 10px 10% 20% 1in }</style>
        <p style="margin: 0">
    ''')
    assert page.outer_width == 200
    assert page.outer_height == 300
    assert page.position_x == 0
    assert page.position_y == 0
    assert page.width == 84 # 200px - 10% - 1 inch
    assert page.height == 230 # 300px - 10px - 20%

    html = page.root_box
    assert html.element.tag == 'html'
    assert html.position_x == 96 # 1in
    assert html.position_y == 10
    assert html.width == 84

    body = html.children[0]
    assert body.element.tag == 'body'
    assert body.position_x == 96 # 1in
    assert body.position_y == 10
    # body has margins in the UA stylesheet
    assert body.margin_left == 8
    assert body.margin_right == 8
    assert body.margin_top == 8
    assert body.margin_bottom == 8
    assert body.width == 68

    paragraph = body.children[0]
    assert paragraph.element.tag == 'p'
    assert paragraph.position_x == 104 # 1in + 8px
    assert paragraph.position_y == 18 # 10px + 8px
    assert paragraph.width == 68

    page, = parse('''
        <style>
            @page { size: 100px; margin: 1px 2px; padding: 4px 8px;
                    border-width: 16px 32px; border-style: solid }
        </style>
        <body>
    ''')
    assert page.width == 16 # 100 - 2 * 42
    assert page.height == 58 # 100 - 2 * 21
    html = page.root_box
    assert html.element.tag == 'html'
    assert html.position_x == 42 # 2 + 8 + 32
    assert html.position_y == 21 # 1 + 4 + 16


@suite.test
def test_block_widths():
    pages = parse('''
        <style>
            @page { margin: 0; size: 120px }
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
    html = pages[0].root_box
    assert html.element.tag == 'html'
    body = html.children[0]
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
                # TODO remove this when we have proper whitespace handling
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
#    assert paragraphs[0].position_x == 0

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


@suite.test
def test_block_heights():
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
    html = page.root_box
    assert html.element.tag == 'html'
    body = html.children[0]
    assert body.element.tag == 'body'
    divs = body.children

    assert divs[0].height == 90
    assert divs[1].height == 90 * 3


@suite.test
def test_breaking_empty_linebox():
    def get_paragraph_linebox(width, font_size):
        page = u'''
            <style>
            p { font-size:%(font_size)spx; width:%(width)spx; }
            </style>
            <p> </p>'''
        page, = parse(page % locals())
        html = page.root_box
        body = html.children[0]
        p = body.children[0]
        return p

    font_size = 12
    width = 500
    p = get_paragraph_linebox(width, font_size)
    assert len(p.children) == 0


@suite.test
def test_breaking_linebox():
    def get_paragraph_linebox(width, font_size):
        page = u'''
            <style>
            p { font-size:%(font_size)spx;
                width:%(width)spx;
                background-color:#393939;
                color:#FFFFFF;
                font-family: Arial, Helvetica, sans-serif;
                text-align:center;
                line-height:1;
                text-decoration : underline overline line-through;
            }
            </style>
            <p><em>Lorem<strong> Ipsum <span>is very</span>simply</strong><em>
            dummy</em>text of the printing and. naaaa </em> naaaa naaaa naaaa
            naaaa naaaa naaaa naaaa naaaa</p>'''
        page, = parse(page % locals())
        html = page.root_box
        body = html.children[0]
        paragraph = body.children[0]
        return paragraph
    font_size = 12
    width = 150
    paragraph = get_paragraph_linebox(width, font_size)
    assert len(list(paragraph.children)) == 3

    lines = paragraph.children
    for line in lines:
#        assert line.width <= width
        assert line.style.font_size == font_size
        assert line.element.tag == 'p'
#        assert sum(linebox_children_width(line)) <= line.width
        for child in line.children:
             assert child.element.tag in ('em', 'p')
             assert child.style.font_size == font_size
             if isinstance(child, boxes.ParentBox):
                 for child_child in child.children:
                    assert child.element.tag in ('em', 'strong', 'span')
                    assert child.style.font_size == font_size

    paragraph = get_paragraph_linebox(width=300,  font_size=font_size)
    assert len(list(paragraph.children)) == 2

#import pdb

#@suite.test
#def test_linebox_positions():
#    def get_paragraph_linebox():
#        page = u'''
#            <style>
#                p { width:200px; }
#            </style>
#            <p>Lorem ipsum dolor sit amet</p>'''
#        page, = parse(page)
#        html = page.root_box
#        body = html.children[0]
#        paragraph = body.children[0]
#        return paragraph

#    paragraph = get_paragraph_linebox()
#    assert len(list(paragraph.children)) == 2

#    def get_text(lines):
#        text = ""
#        for line in lines:
#            for box in line.descendants:
#                if isinstance(box, boxes.TextBox):
#                    text = "%s%s" % box.text
#    assert
#    pdb.set_trace()

