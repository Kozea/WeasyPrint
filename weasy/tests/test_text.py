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
Test the text management.

"""

from attest import Tests, assert_hook  # pylint: disable=W0611

from ..text import TextFragment
from ..document import PNGDocument
from .test_layout import parse, body_children

SUITE = Tests()


def make_text(text, width=-1, style=''):
    """
    Make and return a TextFragment built from a TextBox in an HTML document.
    """
    document = PNGDocument.from_string('''
        <style>
        p {
            font-family: Nimbus Mono L, Liberation Mono, FreeMono, Monospace;
            %s
        }
        </style>
        <p>%s</p>
    ''' % (style, text))
    html = document.formatting_structure
    body, = html.children
    p, = body.children
    line, = p.children
    text, = line.children
    return TextFragment(text, width=width)


@SUITE.test
def test_line_content():
    """Test the line break for various fixed-width lines."""
    for width, remaining in [(120, 'text for test'),
                             (60, 'is a text for test')]:
        text = 'This is a text for test'
        # TODO: find a way to not depend on a specific font
        line = make_text(text, width, 'font-family: "Arial"; font-size: 19px')
        text1, text2 = line.split_first_line()
        assert text2 == remaining
        assert text1 + text2 == text


@SUITE.test
def test_line_with_any_width():
    """Test the auto-fit width of lines."""
    line = make_text(u'some text')
    width, _height = line.get_size()

    line = make_text('some some some text some some some text')
    new_width, _height = line.get_size()

    assert width < new_width


@SUITE.test
def test_line_breaking():
    """Test the line breaking."""
    string = u'This is a text for test'

    # These two tests do not really rely on installed fonts
    line = make_text(string, 120, 'font-size: 1px')
    text1, text2 = line.split_first_line()
    assert text2 == None

    line = make_text(string, 120, 'font-size: 100px')
    text1, text2 = line.split_first_line()
    assert text2 == u'is a text for test'

    # TODO: find a way to not depend on a specific font
    line = make_text(string, 120, 'font-family: "Arial"; font-size: 19px')
    text1, text2 = line.split_first_line()
    assert text2 == u'text for test'


@SUITE.test
def test_text_dimension():
    """Test the font size impact on the text dimension."""
    string = u'This is a text for test. This is a test for text.py'
    fragment = make_text(string, 200, 'font-size: 12px')
    dimension = list(fragment.get_size())

    fragment = make_text(string, 200, 'font-size: 20px')
    new_dimension = list(fragment.get_size())
    assert dimension[0] * dimension[1] < new_dimension[0] * new_dimension[1]


@SUITE.test
def test_text_font_size_zero():
    """Test a text with a font size set to 0."""
    page, = parse('''
        <style>
            p { font-size: 0; }
        </style>
        <p>test font size zero</p>
    ''')
    textbox = body_children(page)[0].children[0].children[0]
    assert textbox.height == 0
    assert textbox.width == 0
