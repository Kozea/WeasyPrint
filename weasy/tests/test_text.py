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
from gi.repository import Pango  # pylint: disable=E0611

from ..text import TextFragment
from .test_layout import parse, body_children

SUITE = Tests()

FONTS = u"Nimbus Mono L, Liberation Mono, FreeMono, Monospace"


@SUITE.test
def test_line_content():
    """Test the line break for various fixed-width lines."""
    for width, remaining in [(120, u'text for test'),
                             (60, u'is a text for test')]:
        text = 'This is a text for test'
        line = TextFragment(text, width)
        line.set_font_size(12)
        line.set_font_family(FONTS)
        assert line.get_remaining_text() == remaining
        assert u'%s%s' % (line.get_first_line_text(),
                          line.get_remaining_text()) == text


@SUITE.test
def test_line_with_any_width():
    """Test the auto-fit width of lines."""
    line = TextFragment(u'some text')
    width, _height = line.get_size()

    line = TextFragment('some some some text some some some text')
    new_width, _height = line.get_size()

    assert width < new_width


@SUITE.test
def test_line_breaking():
    """Test the line breaking."""
    string = u'This is a text for test'
    width = 120
    line = TextFragment(string, width)
    line.set_font_family(FONTS)

    line.set_font_size(12)
    line.set_font_weight(200)
    assert line.get_remaining_text() == u'text for test'

    line.set_font_weight(800)
    assert line.get_remaining_text() == u'text for test'

    line.set_font_size(14)
    assert line.get_remaining_text() == u'text for test'


@SUITE.test
def test_text_dimension():
    """Test the font size impact on the text dimension."""
    string = u'This is a text for test. This is a test for text.py'
    width = 200
    fragment = TextFragment(string, width)
    fragment.set_font_size(12)

    dimension = list(fragment.get_size())
    fragment.set_font_size(20)
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
