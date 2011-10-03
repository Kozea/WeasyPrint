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

from __future__ import division

from gi.repository import Pango, PangoCairo  # pylint: disable=E0611

from .css.values import get_single_keyword, get_single_pixel_value


class TextFragment(object):
    """Text renderer using Pango.

    This class is used to render the text from a TextBox.

    """
    def __init__(self, utf8_text, style, context, width=-1):
        self.layout = PangoCairo.create_layout(context)
        # Pango works on bytes
        self.layout.set_text(utf8_text, -1)
        self.layout.set_wrap(Pango.WrapMode.WORD)
        if width is not None:
            self.layout.set_width(int(Pango.SCALE * width))

        color = style.color[0]
        attributes = dict(
            # TODO: somehow handle color.alpha
            color='#%02x%02x%02x' % (color.red, color.green, color.blue),
            face=', '.join(v.value for v in style.font_family),
            variant=get_single_keyword(style.font_variant),
            style=get_single_keyword(style.font_style),
            size=int(get_single_pixel_value(style.font_size) * Pango.SCALE),
            weight=int(style.font_weight[0].value),
            # Alignments and backgrounds are not handled by Pango.
            letter_spacing = int(
                (get_single_pixel_value(style.letter_spacing) or 0)
                * Pango.SCALE
            ),
            # Tell Pango that fonts on the system can be used to provide
            # characters missing from the current font. Otherwise, only
            # characters from the closest matching font can be used.
            fallback='true',
        )

        # TODO: use an AttrList when it is available with introspection
        attributes = ' '.join(
            u'%s="%s"' % (key, value)
            for key, value in attributes.iteritems()).encode('utf8')
        text = utf8_text.replace('&', '&amp;').replace('<', '&lt;')
        markup = ('<span %s>%s</span>' % (attributes, text))
        _, attributes_list, _, _ = Pango.parse_markup(markup, -1, '\x00')
        self.layout.set_attributes(attributes_list)

    def show_layout(self, context):
        """Draw the text to the Cairo ``context``."""
        PangoCairo.update_layout(context, self.layout)
        PangoCairo.show_layout(context, self.layout)

    def get_size(self):
        """Get the real text area size in pixels."""
        return self.layout.get_pixel_size()

    # TODO: use get_line instead of get_lines when it is not broken anymore
    def split_first_line(self):
        """Return ``(first_line, remaining_text)``.

        ``remaining_text`` may be None if the whole text fits on
        the first line.

        """
        lines = self.layout.get_lines()
        if len(lines) >= 2:
            # Preserved new-line characters are between these two indexes.
            # We don’t want them in either of the returned strings.
            return lines[0].length, lines[1].start_index

    def get_extents(self):
        """Return ``(logical_extents, ink_extents)``.

        The size of the logical and ink areas occupied by the text.

        """
        return self.layout.get_lines()[0].get_pixel_extents()

    def get_baseline(self):
        """Get the baseline of the text."""
        # TODO: use introspection to get the descent
        descent = self.layout.get_context().get_metrics(None, None).get_descent()
        _width, height = self.get_size()
        return height - descent / Pango.SCALE
