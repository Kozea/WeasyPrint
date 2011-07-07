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

import os.path
from attest import Tests, assert_hook
import attest

from .. import text


suite = Tests()


@suite.test
def test_line_content():
    string = u"This is a text for test"
    width = 120
    line = text.LineTextFragment(string, width)
    assert line.remaining_text == u'test'
    assert u"%s%s" % (line.text, line.remaining_text)  == string
    line.width = 80
    assert line.remaining_text == u'text for test'
    assert u"%s%s" % (line.text, line.remaining_text)  == string


@suite.test
def test_line_breaking():
    string = u"This is a text for test"
    width = 120
    line = text.LineTextFragment(string, width)
    
    line.font_size = 12
    line.font_weight = 200
    assert line.remaining_text == u"test"
    
    line.font_weight = 800
    assert line.remaining_text == u"for test"
    
    line.font_size = 14
    assert line.remaining_text == u"for test"

@suite.test
def test_text_dimension():
    string = u"This is a text for test. This is a test for text.py"
    width = 200
    fragment = text.TextFragment(string, width)
    fragment.font_size = 12
    
    dimension = list(fragment.size)
    print dimension
    fragment.font_size = 20
    new_dimension = list(fragment.size)
    print new_dimension
    assert dimension[0]*dimension[1] < new_dimension[0]*new_dimension[1]
    
    dimension = list(fragment.size)
    fragment.spacing = 20
    new_dimension = list(fragment.size)
    assert dimension[0]*dimension[1] < new_dimension[0]*new_dimension[1]


@suite.test
def test_text_font():
    string = u"This is a text for test. This is a test for text.py"
    width = 200
    fragment = text.TextFragment(string, width)
    fragment.font_family = u"Comic Sans MS"
    assert fragment.font_family == u"Comic Sans MS"
    assert fragment.size == (187, 44)
    
    fragment.font_family = u"inexistante font, Comic Sans MS"
    dimension = list(fragment.size)
    fragment.font_family = u"Comic Sans MS"
    new_dimension = list(fragment.size)
    assert new_dimension == dimension
    
    fragment.font_size = 12
    assert fragment.font_size == 12
    
    for value in text.STYLE_PROPERTIES.keys():
        fragment.font_style = value
        assert fragment.font_style == value
    
    with attest.raises(ValueError):
        fragment.font_style = "inexistante property"

    for value in text.VARIANT_PROPERTIES.keys():
        fragment.font_variant = value
        assert fragment.font_variant == value


@suite.test
def test_text_other():
    """ Test other properties """
    width = 200
    fragment = text.TextFragment(u"", 40)
    fragment.text = u"some text"
    
    #The default value of alignement property is ``left`` for western script
    assert fragment.alignment == u"left"
    for value in text.ALIGN_PROPERTIES.keys():
        fragment.alignment = value
        assert fragment.alignment == value
    
    
    fragment.justify = True
    assert fragment.justify != False

