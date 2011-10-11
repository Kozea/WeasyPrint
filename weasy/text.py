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


class TextFragment(object):
    """Text renderer using Pango.

    This class is used to render the text from a TextBox.

    """
    def __init__(self, utf8_text, style, context, width=None):
        self.layout = PangoCairo.create_layout(context)
        self.layout.set_wrap(Pango.WrapMode.WORD)
        if width is not None:
            self.layout.set_width(Pango.units_from_double(width))

        color = style.color
        attributes = dict(
            # TODO: somehow handle color.alpha
            color='#%02x%02x%02x' % (color.red, color.green, color.blue),
            # Other than 'face', values are numbers or known keyword and don’t
            # need escaping.
            face=', '.join(style.font_family)
                .replace('&', '&amp;').replace('"', '&quot;'),
            # CSS: small-caps, Pango: smallcaps
            variant=style.font_variant.replace('-', ''),
            style=style.font_style,
            size=Pango.units_from_double(style.font_size),
            weight=int(style.font_weight),
            # Alignments and backgrounds are not handled by Pango.

            # Tell Pango that fonts on the system can be used to provide
            # characters missing from the current font. Otherwise, only
            # characters from the closest matching font can be used.
            fallback='true',
        )
        if style.letter_spacing != 'normal':
            attributes['letter_spacing'] = Pango.units_from_double(
                style.letter_spacing)

        # TODO: use an AttrList when it is available with introspection
        markup = [u'<span']
        for key, value in attributes.iteritems():
            markup.append(u' %s="%s"' % (key, value))
        markup.append(u'>')
        markup.append(utf8_text.decode('utf8')
            .replace('&', '&amp;').replace('<', '&lt;'))
        markup.append(u'</span>')
        # Sets both the text and attributes
        self.layout.set_markup(u''.join(markup), -1)

    # TODO: use get_line instead of get_lines when it is not broken anymore
    def split_first_line(self):
        """Fit as much as possible in the available width for one line of text.

        Return ``(show_line, length, width, height, resume_at)``.

        ``show_line``: a closure that takes a cairo Context and draws the
                       first line.
        ``length``: length in UTF-8 bytes of the first line
        ``width``: width in pixels of the first line
        ``height``: height in pixels of the first line
        ``baseline``: baseline in pixels of the first line
        ``resume_at``: The number of UTF-8 bytes to skip for the next line.
                       May be ``None`` if the whole text fits in one line.
                       This may be greater than ``length`` in case of preserved
                       newline characters.

        """
        lines = self.layout.get_lines_readonly()
        first_line = lines[0]
        length = first_line.length
        _ink_extents, logical_extents = first_line.get_extents()
        width = Pango.units_to_double(logical_extents.width)
        height = Pango.units_to_double(logical_extents.height)
        context = self.layout.get_context()
        descent = context.get_metrics(None, None).get_descent()
        baseline = height - Pango.units_to_double(descent)
        if len(lines) >= 2:
            resume_at = lines[1].start_index
        else:
            resume_at = None

        def show_line(context):
            """Draw the given ``line`` to the Cairo ``context``."""
            PangoCairo.update_layout(context, self.layout)
            PangoCairo.show_layout_line(context, first_line)

        return show_line, length, width, height, baseline, resume_at
