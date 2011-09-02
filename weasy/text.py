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

    This class is mainly used to render the text from a TextBox.

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
        self.set_text(text)
        self.set_width(width)
        self._attributes = {}
        # If fallback is True other fonts on the system can be used to provide
        # characters missing from the current font. Otherwise, only characters
        # from the closest matching font can be used.
        self._set_attribute('fallback', 'true')
        # Other properties
        self.layout.set_wrap(Pango.WrapMode.WORD)

    def set_textbox(self, textbox):
        """Set the textbox properties in the layout."""
        self.set_text(textbox.text)
        font = ', '.join(v.value for v in textbox.style['font-family'])
        self.set_font_family(font)
        self.set_font_size(get_single_pixel_value(textbox.style.font_size))
        self.set_alignment(get_single_keyword(textbox.style.text_align))
        self.set_font_variant(get_single_keyword(textbox.style.font_variant))
        self.set_font_weight(int(textbox.style.font_weight[0].value))
        self.set_font_style(get_single_keyword(textbox.style.font_style))
        letter_spacing = get_single_pixel_value(textbox.style.letter_spacing)
        if letter_spacing is not None:
            self.set_letter_spacing(letter_spacing)
        self.set_foreground(textbox.style.color[0])
        # Have the draw package draw backgrounds like for blocks, do not
        # set the background with Pango.

    def show_layout(self):
        """Draw the text to the ``context`` given at construction."""
        PangoCairo.update_layout(self.context, self.layout)
        PangoCairo.show_layout(self.context, self.layout)

    @classmethod
    def from_textbox(cls, textbox, context=None):
        """Create a TextFragment from a TextBox."""
        if context is None:
            surface = textbox.document.surface
            context = cairo.Context(surface)
        object_cls = cls('', -1, context)
        object_cls.set_textbox(textbox)
        return object_cls

    def _set_attribute(self, key, value):
        """Set the ``key`` attribute to ``value`` in the layout."""
        # TODO: use an AttrList when it is available with introspection
        self._attributes[key] = value
        string = '<span %s>' % ' '.join(
            '%s="%s" ' % (key, value)
            for key, value in self._attributes.items())
        string += self.get_text().replace('&', '&amp;').replace('<', '&lt;')
        string += '</span>'
        attributes_list = Pango.parse_markup(string, -1, '\x00')[1]
        self.layout.set_attributes(attributes_list)

    def get_text(self):
        """Get the unicode text of the layout."""
        return self.layout.get_text().decode('utf-8')

    def set_text(self, text):
        """Set the layout unicode ``text``."""
        self.layout.set_text(text.encode('utf-8'), -1)

    def get_size(self):
        """Get the real text area size in pixels."""
        return self.layout.get_pixel_size()

    def set_width(self, width):
        """Set the layout ``width``.

        The ``width`` value can be ``-1`` to indicate that no wrapping should
        be performed.

        """
        if width != -1:
            width = Pango.SCALE * width
        self.layout.set_width(int(width))

    def set_spacing(self, value):
        """Set the spacing ``value`` between the lines of the layout."""
        self.layout.set_spacing(Pango.SCALE * value)

    def set_alignment(self, alignment):
        """Set the default alignment of text in layout.

        The value of alignment must be ``'left'``, ``'center'``, ``'right'`` or
        ``'justify'``.

        """
        if alignment == 'justify':
            alignment = 'left'
            self.layout.set_justify(True)
        self.layout.set_alignment(getattr(Pango.Alignment, alignment.upper()))

    def set_font_family(self, font):
        """Set the ``font`` used by the layout.

        ``font`` can be a unicode comma-separated list of font names, as in
        CSS.

        >>> set_font_family('Al Mawash Bold, Comic sans MS')

        """
        self._set_attribute('face', font.encode('utf-8'))

    def set_font_style(self, style):
        """Set the font style of the layout text.

        The value must be ``'normal'``, ``'italic'`` or ``'oblique'``, as in
        CSS.

        """
        self._set_attribute('style', style.encode('utf-8'))

    def set_font_size(self, size):
        """Set the layout font size in pixels."""
        self._set_attribute('size', int(size) * Pango.SCALE)

    def set_font_variant(self, variant):
        """Set the layout font variant.

        The value of ``variant`` must be ``'normal'`` or ``'small-caps'``.

        """
        self._set_attribute('variant', variant.encode('utf-8'))

    def set_font_weight(self, weight):
        """Set the layout font weight.

        The value of ``weight`` must be an integer in a range from 100 to 900.

        """
        self._set_attribute('weight', weight)

    def set_foreground(self, color):
        """Set the foreground ``color``."""
        # TODO: somehow handle color.alpha
        self._set_attribute(
            'color', '#%02x%02x%02x' % (color.red, color.green, color.blue))

    def set_letter_spacing(self, value):
        """Set the letter spacing ``value``."""
        self._set_attribute(
            'letter_spacing', int(value * Pango.SCALE))

    def set_rise(self, value):
        """Set the text displacement ``value`` from the baseline."""
        self._set_attribute('raise', value * Pango.SCALE)


class TextLineFragment(TextFragment):
    """Text renderer splitting lines."""
    def get_remaining_text(self):
        """Get the unicode text that can't be on the line."""
        # Do not use the length of the first line here.
        # Preserved new-line characters are between get_line(0).length
        # and get_line(1).start_index
        second_line = self.layout.get_line(1)
        if second_line is not None:
            text = self.layout.get_text()[second_line.start_index:]
            return text.decode('utf-8')
        else:
            return None

    def get_text(self):
        """Get all the unicode text can be on the line."""
        first_line = self.layout.get_line(0)
        return self.layout.get_text()[:first_line.length].decode('utf-8')

    def get_size(self):
        """Get the real text area dimensions for this line in pixels."""
        layout = self.layout.copy()
        layout.set_text(self.get_text(), -1)
        return layout.get_pixel_size()

    def get_logical_extents(self):
        """Get the size of the logical area occupied by the text."""
        return self.layout.get_line(0).get_pixel_extents()[0]

    def get_ink_extents(self):
        """Get the size of the ink area occupied by the text."""
        return self.layout.get_line(0).get_pixel_extents()[1]

    def get_baseline(self):
        """Get the baseline of the text."""
        # TODO: use introspection to get the descent
        #descent = self.layout.get_context().get_metrics().get_descent()
        height = self.get_size()[1]
        return height   # - descent
