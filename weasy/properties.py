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

A few values have a sepcial meaning here:
 * ``-weasy-DIRECTION-ORIGIN`` (for text-align): 'left' if `direction` is
   'ltr', 'right' if `direction` is 'rtl' 
 * ``-weasy-SAME-AS-COLOR`` (for border-color): use the value of the `color`
   property
"""

from cssutils.css import Property, CSSStyleDeclaration


def four_sides_lengths(property):
    """
    Expand properties that set a dimension for each of the four sides of a box.
    """
    values = list(property.propertyValue)
    # Make sure we have 4 values
    if len(values) == 1:
        values *= 4
    elif len(values) == 2:
        values *= 2 # (bottom, left) defaults to (top, right) 
    elif len(values) == 3:
        values.append(values[1]) # left defaults to right
    elif len(values) != 4:
        raise ValueError('Invalid number of value components for %s: %s'
            % (property.name, property.value))
    for suffix, value in zip(('-top', '-right', '-bottom', '-left'), values):
        yield Property(name=property.name + suffix, value=value.cssText,
                       priority=property.priority)

SHORTHANDS = {
    'margin': four_sides_lengths,
    'padding': four_sides_lengths,
    'border-width': four_sides_lengths,
}

# Should be in the weasy.css module but that would cause a circular import
def expand_shorthands_in_declaration(style):
    """
    Expand shorthand properties in a CSSStyleDeclaration and return a new
    CSSStyleDeclaration.
    """
    # Build a new CSSStyleDeclaration to preserve ordering.
    new_style = CSSStyleDeclaration()
    for prop in style:
        if prop.name in SHORTHANDS:
            expander = SHORTHANDS[prop.name]
            for new_prop in expander(prop):
                new_style.setProperty(new_prop)
        else:
            new_style.setProperty(prop)
    return new_style


r"""
  Built with:
  
    print '\n'.join(
        lxml.html.parse('http://www.w3.org/TR/CSS21/propidx.html')
        .xpath('//table//td[5][contains(text(), "yes")]/../td[1]/a/span/text()')
    ).replace("'", '')
  
  and adding some line breaks.
"""
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
    font
    letter-spacing
    line-height
    list-style-image
    list-style-position
    list-style-type
    list-style
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
    for prop in expand_shorthands_in_declaration(CSSStyleDeclaration("""
        azimuth: center;
        background-attachment: scroll;
        background-color: transparent;
        background-image: none;
        background-position: 0% 0%;
        background-repeat: repeat;
        border-collapse: separate;
        border-color: -weasy-SAME-AS-COLOR;  /* the value of the 'color'
                                                property */
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
        text-align: -weasy-DIRECTION-ORIGIN; /* acts as 'left' if 'direction'
                                                is 'ltr', 'right' if
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

