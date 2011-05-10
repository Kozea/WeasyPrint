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
    Some CSS properties inherit from the parent element’s value.
"""

from cssutils.css import PropertyValue


r"""
  Built with:
  
    print '\n'.join(
        lxml.html.parse('http://www.w3.org/TR/CSS21/propidx.html')
        .xpath('//table//td[5][contains(text(), "yes")]/../td[1]/a/span/text()')
    ).replace("'", '')
  
  adding some line breaks and removing shorthand properties.
"""
# Do not list shorthand properties here as we handle them before inheritance:
# font, list-style
INHERITED = set("""
    azimuth
    border-collapse
    border-spacing
    caption-side
    color
    cursor
    direction
    elevation
    empty-cells
    font-family
    font-size
    font-style
    font-variant
    font-weight
    letter-spacing
    line-height
    list-style-image
    list-style-position
    list-style-type
    orphans
    pitch-range
    pitch
    quotes
    richness
    speak-header
    speak-numeral
    speak-punctuation
    speak
    speech-rate
    stress
    text-align
    text-indent
    text-transform
    visibility
    voice-family
    volume
    white-space
    widows
    word-spacing
""".split())


def handle_inheritance(element):
    """
    The specified value is the parent element’s computed value iif one of the
    following is true:
     * The cascade did not result in a value, and the the property is inherited
     * The the value is the keyword 'inherit'.
    """
    style = element.style
    parent = element.getparent()
    if parent is None: # root element
        for name, value in style.iteritems():
            # The PropertyValue object has value attribute
            if value.value == 'inherit':
                # The root element can not inherit from anything:
                # use the initial value.
                style[name] = PropertyValue('initial')
    else:
        # The parent appears before in tree order, so we should already have
        # finished with its computed values.
        for name, value in style.iteritems():
            if value.value == 'inherit':
                style[name] = parent.style[name]
        for name in INHERITED:
            # Do not use is_initial() here: only inherit if the property is
            # actually missing.
            if name not in style:
                style[name] = parent.style[name]

