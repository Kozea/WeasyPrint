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
    line = text.WeasyInlineText(string, width)
    assert line.remaining_text == u'test'
    assert u"%s%s" % (line.text, line.remaining_text)  == string
    line.width = 80
    assert line.remaining_text == u'text for test'
    assert u"%s%s" % (line.text, line.remaining_text)  == string


@suite.test
def test_line_dimension():
    string = u"This is a text for test"
    width = 120
    line = text.WeasyInlineText(string, width)
    
    line.font_size = 12
    line.font_weight = 200
    assert line.size == (114, 38)
    assert line.remaining_text == u"test"
    
    line.font_weight = 800
    assert line.size == (98, 38)
    assert line.remaining_text == u"for test"
    
    line.font_size = 14
    assert line.size == (109, 44)
    assert line.remaining_text == u"for test"

@suite.test
def test_text_dimension():
    string = u"This is a text for test. This is a test for text.py"
    width = 200
    weasytext = text.WeasyText(string, width)
    weasytext.font_size = 12
    assert weasytext.size == (183, 38)
    
    weasytext.font_size = 14
    assert weasytext.size == (198, 44)
    
    weasytext.spacing = 20
    assert weasytext.size == (198, 64)
    
    assert weasytext.text == string


@suite.test
def test_text_font():
    string = u"This is a text for test. This is a test for text.py"
    width = 200
    weasytext = text.WeasyText(string, width)
    weasytext.font_family = u"Comic Sans MS"
    assert weasytext.font_family == u"Comic Sans MS"
    assert weasytext.size == (187, 44)
    
    weasytext.font_family = u"Courier 10 Pitch"
    assert weasytext.font_family == u"Courier 10 Pitch"
    assert weasytext.size == (180, 54)
    
    weasytext.font_family = u"Nimbus Roman No9 L"
    assert weasytext.font_family == u"Nimbus Roman No9 L"
    assert weasytext.size == (182, 38)
    
#    weasytext.font_family = u"inexistante font"
#    assert weasytext.font_family != u"inexistante font"
    weasytext.font_family = u"Nimbus Roman No9 L"
    
    weasytext.font_size = 12
    assert weasytext.font_size == 12
    
    for value in text.STYLE_PROPERTIES.keys():
        weasytext.font_style = value
        assert weasytext.font_style == value
    
    with attest.raises(ValueError):
        weasytext.font_style = "inexistante property"

    for value in text.VARIANT_PROPERTIES.keys():
        weasytext.font_variant = value
        assert weasytext.font_variant == value

#    weasytext.font_variant
#    assert 
#    weasytext.font_weight
#    assert 


@suite.test
def test_text_other():
    """ Test all properties """
    width = 200
    weasytext = text.WeasyText(u"", 40)
    weasytext.text = u"some text"
    assert weasytext.text == u"some text"
    weasytext.width = 20
    assert weasytext.width == 20
    weasytext.spacing = 20
    assert weasytext.spacing == 20
    
    #The default value of alignement property is ``left`` for western script
    assert weasytext.alignment == u"left"
    for value in text.ALIGN_PROPERTIES.keys():
        weasytext.alignment = value
        assert weasytext.alignment == value
    
    
    weasytext.justify = True
    assert weasytext.justify != False

