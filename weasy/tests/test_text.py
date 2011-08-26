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

from ..text import TextFragment, TextLineFragment, ALIGN_PROPERTIES
from ..document import PNGDocument
from .test_layout import parse, body_children

SUITE = Tests()

FONTS = u"Nimbus Mono L, Liberation Mono, FreeMono, Monospace"


@SUITE.test
def test_line_content():
    """Test the line break for various fixed-width lines."""
    string = u"This is a text for test"
    width = 120
    line = TextLineFragment(string, width)
    line.set_font_size(12)
    line.set_font_family(FONTS)
    assert line.get_remaining_text() == u'text for test'
    line.set_width(60)
    assert line.get_remaining_text() == u'is a text for test'
    assert u"%s%s" % (line.get_text(), line.get_remaining_text())  == string


@SUITE.test
def test_line_with_any_width():
    """Test the auto-fit width of lines."""
    line = TextLineFragment(u'some text')
    line.set_font_family(FONTS)
    width = line.get_size()[0]
    line.set_text('some some some text some some some text')
    new_width = line.get_size()[0]

    assert width < new_width


@SUITE.test
def test_line_breaking():
    """Test the line breaking."""
    string = u'This is a text for test'
    width = 120
    line = TextLineFragment(string, width)
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
    """Test the font size and spacing size impact on the text dimension."""
    string = u'This is a text for test. This is a test for text.py'
    width = 200
    fragment = TextFragment(string, width)
    fragment.set_font_size(12)

    dimension = list(fragment.get_size())
    fragment.set_font_size(20)
    new_dimension = list(fragment.get_size())
    assert dimension[0] * dimension[1] < new_dimension[0] * new_dimension[1]

    dimension = list(fragment.get_size())
    fragment.set_spacing(20)
    new_dimension = list(fragment.get_size())
    assert dimension[0] * dimension[1] < new_dimension[0] * new_dimension[1]


@SUITE.test
def test_text_other():
    """Test various text properties."""
    fragment = TextFragment(u'', 40)
    fragment.set_text(u'some text')

    # The default value of alignement property is ``left`` for western script
    assert fragment.layout.get_alignment() == ALIGN_PROPERTIES['left']
    assert not fragment.layout.get_justify()

    for key, value in ALIGN_PROPERTIES.iteritems():
        fragment.set_alignment(key)
        assert fragment.layout.get_alignment() == value

    fragment.set_alignment('justify')
    assert fragment.layout.get_justify()

    fragment.justify = True
    assert fragment.justify != False


@SUITE.test
def test_text_font_size_zero():
    page, = parse('''
        <style>
            p { font-size: 0; }
        </style>
        <p>test font size zero</p>
    ''')
    textbox = body_children(page)[0].children[0].children[0]
    assert textbox.height == 0
    assert textbox.width == 0

