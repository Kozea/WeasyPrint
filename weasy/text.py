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


PANGO_VARIANT = {
    'normal': Pango.Variant.NORMAL,
    'small-caps': Pango.Variant.SMALL_CAPS,
}

PANGO_STYLE = {
    'normal': Pango.Style.NORMAL,
    'italic': Pango.Style.ITALIC,
    'oblique': Pango.Style.OBLIQUE,
}

class TextFragment(object):
    """Text renderer using Pango.

    This class is used to render the text from a TextBox.

    """
    def __init__(self, utf8_text, style, context, width=None):
        self.layout = PangoCairo.create_layout(context)
        font = Pango.FontDescription()
        font.set_family(', '.join(style.font_family))
        font.set_variant(PANGO_VARIANT[style.font_variant])
        font.set_style(PANGO_STYLE[style.font_style])
        font.set_absolute_size(Pango.units_from_double(style.font_size))
        font.set_weight(style.font_weight)
        self.layout.set_font_description(font)
        self.layout.set_text(utf8_text.decode('utf8'), -1)
        self.layout.set_wrap(Pango.WrapMode.WORD)
        if width is not None:
            self.layout.set_width(Pango.units_from_double(width))

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
        baseline = Pango.units_to_double(self.layout.get_baseline())
        if len(lines) >= 2:
            resume_at = lines[1].start_index
        else:
            resume_at = None

        def show_line(context):
            """Draw the given ``line`` to the Cairo ``context``."""
            PangoCairo.update_layout(context, self.layout)
            PangoCairo.show_layout_line(context, first_line)

        return show_line, length, width, height, baseline, resume_at
