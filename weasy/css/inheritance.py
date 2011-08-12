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

from .utils import get_single_keyword, make_keyword
from .initial_values import INITIAL_VALUES


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
#
# text-decoration is not a realy inherited property
# See : http://www.w3.org/TR/CSS2/text.html#propdef-text-decoration
INHERITED = set("""
    border-collapse
    border-spacing
    caption-side
    color
    direction
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
    quotes
    text-align
    text-decoration
    text-indent
    text-transform
    visibility
    white-space
    widows
    word-spacing
""".split())

# Disabled since not applicable to the print media:
#    azimuth
#    cursor
#    elevation
#    pitch-range
#    pitch
#    richness
#    speak-header
#    speak-numeral
#    speak-punctuation
#    speak
#    speech-rate
#    stress
#    voice-family
#    volume


def handle_inheritance_and_initial(style, parent_style):
    """
    Handle inheritance and initial values.
    """
    if parent_style is None:
        # Root element, 'inherit' from initial values
        parent_style = INITIAL_VALUES

    for name, initial in INITIAL_VALUES.iteritems():
        values = style.get(name, None)
        if values is None:
            if name in INHERITED:
                keyword = 'inherit'
            else:
                keyword = 'initial'
        else:
            keyword = get_single_keyword(values)

        if keyword == 'initial':
            style[name] = initial
        elif keyword == 'inherit':
            style[name] = parent_style[name]
