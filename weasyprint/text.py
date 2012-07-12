# coding: utf8
"""
    weasyprint.text
    ---------------

    Interface with Pango to decide where to do line breaks and to draw text.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import cairo

from cgi import escape
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

NON_HINTED_DUMMY_CONTEXT = cairo.Context(cairo.PDFSurface(None, 1, 1))
HINTED_DUMMY_CONTEXT = cairo.Context(cairo.ImageSurface(
    cairo.FORMAT_ARGB32, 1, 1))


def create_layout(text, style, hinting, max_width):
    """Return an opaque Pango object to be passed to other functions
    in this module.

    :param text: Unicode
    :param style: a :class:`StyleDict` of computed values
    :param hinting: whether to enable text hinting or not
    :param max_width:
        The maximum available width in the same unit as ``style.font_size``,
        or ``None`` for unlimited width.

    """
    layout = PangoCairo.create_layout(
        HINTED_DUMMY_CONTEXT if hinting else NON_HINTED_DUMMY_CONTEXT)
    font = Pango.FontDescription()
    font.set_family(','.join(style.font_family))
    font.set_variant(PANGO_VARIANT[style.font_variant])
    font.set_style(PANGO_STYLE[style.font_style])
    font.set_absolute_size(Pango.units_from_double(style.font_size))
    font.set_weight(style.font_weight)
    layout.set_font_description(font)
    layout.set_text(text, -1)
    layout.set_wrap(Pango.WrapMode.WORD)
    if max_width is not None:
        layout.set_width(Pango.units_from_double(max_width))
    word_spacing = style.word_spacing
    letter_spacing = style.letter_spacing
    if letter_spacing == 'normal':
        letter_spacing = 0
    if text and (word_spacing != 0 or letter_spacing != 0):
        word_spacing = Pango.units_from_double(word_spacing)
        letter_spacing = Pango.units_from_double(letter_spacing)
        markup = escape(text).replace(
            ' ', '<span letter_spacing="%i"> </span>' % (
                word_spacing + letter_spacing,))
        markup = '<span letter_spacing="%i">%s</span>' % (
            letter_spacing, markup)
        attributes_list = Pango.parse_markup(markup, -1, '\x00')[1]
        layout.set_attributes(attributes_list)
    return layout


# TODO: use get_line instead of get_lines when it is not broken anymore
def split_first_line(*args, **kwargs):
    """Fit as much as possible in the available width for one line of text.

    Return ``(length, width, height, resume_at)``.

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
    layout = create_layout(*args, **kwargs)
    lines = layout.get_lines_readonly()
    first_line = lines[0]
    length = first_line.length
    _ink_extents, logical_extents = first_line.get_extents()
    width = Pango.units_to_double(logical_extents.width)
    height = Pango.units_to_double(logical_extents.height)
    baseline = Pango.units_to_double(layout.get_baseline())
    resume_at = lines[1].start_index if len(lines) >= 2 else None
    return layout, length, resume_at, width, height, baseline


def show_first_line(cairo_context, pango_layout, hinting):
    """Draw the given ``line`` to the Cairo ``context``."""
    if hinting:
        PangoCairo.update_layout(cairo_context, pango_layout)
    lines = pango_layout.get_lines_readonly()
    PangoCairo.show_layout_line(cairo_context, lines[0])


def line_widths(box, enable_hinting, width, skip=None):
    """Return the width for each line."""
    # TODO: without the lstrip, we get an extra empty line at the beginning. Is
    # there a better solution to avoid that?
    layout = create_layout(
        box.text[(skip or 0):].lstrip(), box.style, enable_hinting, width)
    for line in layout.get_lines_readonly():
        _ink_extents, logical_extents = line.get_extents()
        yield Pango.units_to_double(logical_extents.width)
