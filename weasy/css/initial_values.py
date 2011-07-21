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
    Values that CSS properties take when there is no other value, including
    inherited.
"""

from cssutils.css import PropertyValue, CSSStyleDeclaration

from .shorthands import expand_shorthand


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
    expanded_prop
    # XXX: Special cases that can not be expressed as CSS:
    #   border-color, text-align
    for prop in CSSStyleDeclaration(u"""
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

        /* CSS3 Paged Media: http://www.w3.org/TR/css3-page/#page-size */
        size: auto;
    """)
    for expanded_prop in expand_shorthand(prop)
)



def is_initial(style, name):
    """
    Return whether the property `name` is missing in the given `style` dict
    or if its value is the 'initial' keyword.
    """
    # Explicit 'initial' values are new in CSS3
    # http://www.w3.org/TR/css3-values/#computed0
    return name not in style or style[name].value == 'initial'


def handle_initial_values(style):
    """
    Properties that do not have a value after inheritance or whose value is the
    'initial' keyword (CSS3) get their initial value.
    """
    for name, initial in INITIAL_VALUES.iteritems():
        if is_initial(style, name):
            style[name] = initial

    # Special cases for initial values that can not be expressed as CSS

    # border-color: same as color
    for name in ('border-top-color', 'border-right-color',
                 'border-bottom-color', 'border-left-color'):
        if is_initial(style, name):
            style[name] = style['color']

    # text-align: left in left-to-right text, right in right-to-left
    if is_initial(style, 'text-align'):
        if style.direction == 'rtl':
            style['text-align'] = PropertyValue('right')
        else:
            style['text-align'] = PropertyValue('left')
