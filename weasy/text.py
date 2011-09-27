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
Various classes to break text lines and draw them.

"""

import cairo
from gi.repository import Pango, PangoCairo  # pylint: disable=E0611

from .css.values import get_single_keyword, get_single_pixel_value


class TextFragment(object):
    """Text renderer using Pango.

    This class is mainPly used to render the text from a TextBox.

    """
    def __init__(self, text='', width=-1, context=None):
        if context is None:
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 400, 400)
            self.context = cairo.Context(surface)
        else:
            self.context = context
        pango_context = PangoCairo.create_context(self.context)
        # TODO: find how to do this with introspection
        #pango_context.set_antialias(cairo.ANTIALIAS_SUBPIXEL)
        self.layout = Pango.Layout(pango_context)
        self.text = text  # Keep it here as Unicode
        self.layout.set_text(text.encode('utf-8'), -1)  # Pango works on bytes
        if width != -1:
            width = Pango.SCALE * width
        self.layout.set_width(int(width))
        # If fallback is True other fonts on the system can be used to provide
        # characters missing from the current font. Otherwise, only characters
        # from the closest matching font can be used.
        self._attributes = {'fallback': 'true'}
        # Other properties
        self.layout.set_wrap(Pango.WrapMode.WORD)

    def show_layout(self):
        """Draw the text to the ``context`` given at construction."""
        PangoCairo.update_layout(self.context, self.layout)
        PangoCairo.show_layout(self.context, self.layout)

    @classmethod
    def from_textbox(cls, textbox, context=None, width=-1):
        """Create a TextFragment from a TextBox."""
        if context is None:
            surface = textbox.document.surface
            context = cairo.Context(surface)

        # Name abuse to make the following look like a normal method.
        self = cls(textbox.text, width, context)

        # TODO: somehow handle color.alpha
        color = textbox.style.color[0]
        self._attributes.update(dict(
            color='#%02x%02x%02x' % (color.red, color.green, color.blue),
            face=', '.join(v.value for v in textbox.style['font-family']),
            variant=get_single_keyword(textbox.style.font_variant),
            style=get_single_keyword(textbox.style.font_style),
            size=int(get_single_pixel_value(textbox.style.font_size)
                     * Pango.SCALE),
            weight=int(textbox.style.font_weight[0].value),
        ))

        letter_spacing = get_single_pixel_value(textbox.style.letter_spacing)
        if letter_spacing is not None:
            self._attributes['letter_spacing'] = int(value * Pango.SCALE)

        self._set_attributes()

        # Alignments and backgrounds are not handled by Pango.

        return self

    def _set_attributes(self):
        """Set the ``key`` attribute to ``value`` in the layout."""
        # TODO: use an AttrList when it is available with introspection
        attributes = ' '.join(
            '%s="%s"' % (key, value)
            for key, value in self._attributes.items())
        text = self.text.replace('&', '&amp;').replace('<', '&lt;')
        markup = ('<span %s>%s</span>' % (attributes, text)).encode('utf-8')
        _, attributes_list, _, _ = Pango.parse_markup(markup, -1, '\x00')
        self.layout.set_attributes(attributes_list)

    def get_size(self):
        """Get the real text area size in pixels."""
        return self.layout.get_pixel_size()

    def set_font_family(self, font):
        """Set the ``font`` used by the layout.

        ``font`` can be a unicode comma-separated list of font names, as in
        CSS.

        >>> set_font_family('Al Mawash Bold, Comic sans MS')

        """
        self._attributes['face'] = font.encode('utf-8')
        self._set_attributes()

    def set_font_size(self, size):
        """Set the layout font size in pixels."""
        self._attributes['size'] = int(size * Pango.SCALE)
        self._set_attributes()


    def set_font_weight(self, weight):
        """Set the layout font weight.

        The value of ``weight`` must be an integer in a range from 100 to 900.

        """
        self._attributes['weight'] = weight
        self._set_attributes()

    # TODO: use get_line instead of get_lines when it is not broken anymore
    def get_remaining_text(self):
        """Get the unicode text that can't be on the line."""
        # Do not use the length of the first line here.
        # Preserved new-line characters are between get_lines()[0].length
        # and get_lines()[1].start_index
        if self.layout.get_line_count() > 1:
            index = self.layout.get_lines()[1].start_index
            text = self.layout.get_text()[index:].decode('utf-8')
            return text

    def get_first_line_text(self):
        """Get all the unicode text can be on the line."""
        length = self.layout.get_lines()[0].length
        return self.layout.get_text()[:length].decode('utf-8')

    def get_logical_extents(self):
        """Get the size of the logical area occupied by the text."""
        return self.layout.get_lines()[0].get_pixel_extents()[0]

    def get_ink_extents(self):
        """Get the size of the ink area occupied by the text."""
        return self.layout.get_lines()[0].get_pixel_extents()[1]

    def get_baseline(self):
        """Get the baseline of the text."""
        # TODO: use introspection to get the descent
        #descent = self.layout.get_context().get_metrics().get_descent()
        _width, height = self.get_size()
        return height   # - descent
