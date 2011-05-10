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
``SHORTHANDS`` is a dict of prop_name: expander_function pairs for all known
shorthand properties. For example, `margin` is a shorthand for all of
margin-top, margin-right, margin-bottom and margin-left.

Expander functions take a Property and yield expanded Property objects.


``INITIAL_VALUES`` is a CSSStyleDeclaration with the initial values of CSS 2.1
properties. The initial value is the specified value when no other values was
found in the stylesheets for an element.

"""

import collections
from cssutils.css import CSSStyleDeclaration, ColorValue

from .shorthands import expand_shorthands_in_declaration


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


r"""
    Built with:
    
    print '\n'.join(
        '    %s: %s;' % (
            prop.strip("'"), 
            tr.xpath('td[3]/text()')[0].strip()
        )
        for tr in lxml.html.parse('http://www.w3.org/TR/CSS21/propidx.html')
            .iter('tr')
        for prop in tr.xpath('td[1]/a/span/text()')
    )

    and some manual post-processing.
"""
INITIAL_VALUES = dict(
    (prop.name, prop.propertyValue)
    # XXX: Special cases that can not be expressed as CSS:
    #   border-color, text-align
    for prop in expand_shorthands_in_declaration(CSSStyleDeclaration(u"""
        azimuth: center;
        background-attachment: scroll;
        background-color: transparent;
        background-image: none;
        background-position: 0% 0%;
        background-repeat: repeat;
        border-collapse: separate;
    /*  border-color: the value of the 'color' property */
        border-spacing: 0;
        border-style: none;
        border-width: medium;
        bottom: auto;
        caption-side: top;
        clear: none;
        clip: auto;
        color: #000;     /* depends on user agent */
        content: normal;
        counter-increment: none;
        counter-reset: none;
        cue-after: none;
        cue-before: none;
        cursor: auto;
        direction: ltr;
        display: inline;
        elevation: level;
        empty-cells: show;
        float: none;
        font-family: serif; /* depends on user agent */
        font-size: medium;
        font-style: normal;
        font-variant: normal;
        font-weight: normal;
        height: auto;
        left: auto;
        letter-spacing: normal;
        line-height: normal;
        list-style-image: none;
        list-style-position: outside;
        list-style-type: disc;
        margin: 0;
        max-height: none;
        max-width: none;
        min-height: 0;
        min-width: 0;
        orphans: 2;
        outline-color: invert;
        outline-style: none;
        outline-width: medium;
        overflow: visible;
        padding: 0;
        page-break-after: auto;
        page-break-before: auto;
        page-break-inside: auto;
        pause-after: 0;
        pause-before: 0;
        pitch-range: 50;
        pitch: medium;
        play-during: auto;
        quotes: "“" "”" "‘" "’";  /* depends on user agent */
        position: static;
        richness: 50;
        right: auto;
        speak-header: once;
        speak-numeral: continuous;
        speak-punctuation: none;
        speak: normal;
        speech-rate: medium;
        stress: 50;
        table-layout: auto;
    /*  text-align: acts as 'left' if 'direction' is 'ltr', 'right' if
                    'direction' is 'rtl'  */
        text-decoration: none;
        text-indent: 0;
        text-transform: none;
        top: auto;
        unicode-bidi: normal;
        vertical-align: baseline;
        visibility: visible;
        voice-family: child;     /* depends on user agent */
        volume: medium;
        white-space: normal;
        widows: 2;
        width: auto;
        word-spacing: normal;
        z-index: auto;
    """))
)


# How many CSS pixels is one <unit> ?
# http://www.w3.org/TR/CSS21/syndata.html#length-units
LENGTHS_TO_PIXELS = {
    'px': 1,
    'pt': 1. / 0.75,
    'pc': 16., # LENGTHS_TO_PIXELS['pt'] * 12
    'in': 96., # LENGTHS_TO_PIXELS['pt'] * 72
    'cm': 96. / 2.54, # LENGTHS_TO_PIXELS['in'] / 2.54
    'mm': 96. / 25.4, # LENGTHS_TO_PIXELS['in'] / 25.4
}


# Value in pixels of font-size for <absolute-size> keywords: 12pt (16px) for
# medium, and scaling factors given in CSS3 for others:
# http://www.w3.org/TR/css3-fonts/#font-size-prop
# This dict has to be ordered to implement 'smaller' and 'larger'
FONT_SIZE_MEDIUM = 16.
FONT_SIZE_KEYWORDS = collections.OrderedDict([
    ('xx-small', FONT_SIZE_MEDIUM * 3/5),
    ('x-small', FONT_SIZE_MEDIUM * 3/4),
    ('small', FONT_SIZE_MEDIUM * 8/9),
    ('medium', FONT_SIZE_MEDIUM),
    ('large', FONT_SIZE_MEDIUM * 6/5),
    ('x-large', FONT_SIZE_MEDIUM * 3/2),
    ('xx-large', FONT_SIZE_MEDIUM * 2),
])
del FONT_SIZE_MEDIUM


# These are unspecified, other than 'thin' <='medium' <= 'thick'.
# Values are in pixels.
BORDER_WIDTH_KEYWORDS = {
    'thin': 1,
    'medium': 3,
    'thick': 5,
}


# http://www.w3.org/TR/CSS21/fonts.html#propdef-font-weight
FONT_WEIGHT_RELATIVE = dict(
    bolder={
        100: 400,
        200: 400,
        300: 400,
        400: 700,
        500: 700,
        600: 900,
        700: 900,
        800: 900,
        900: 900,
    },
    lighter={
        100: 100,
        200: 100,
        300: 100,
        400: 100,
        500: 100,
        600: 400,
        700: 400,
        800: 700,
        900: 700,
    },
)
