# coding: utf8
"""
    weasyprint.text
    ---------------

    Interface with Pango to decide where to do line breaks and to draw text.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import os
from io import BytesIO
from cgi import escape

import cairo

from .compat import xrange, basestring
from .logger import LOGGER


USING_INTROSPECTION = bool(os.environ.get('WEASYPRINT_USE_INTROSPECTION'))
if not USING_INTROSPECTION:
    try:
        import pygtk
        pygtk.require('2.0')
        import pango as Pango
    except ImportError:
        USING_INTROSPECTION = True

if USING_INTROSPECTION:
    from gi.repository import Pango, PangoCairo
    from gi.repository.PangoCairo import create_layout as create_pango_layout

    if Pango.version() < 12903:
        LOGGER.warn('Using Pango-introspection %s. Versions before '
                    '1.29.3 are known to be buggy.', Pango.version_string())

    PANGO_VARIANT = {
        'normal': Pango.Variant.NORMAL,
        'small-caps': Pango.Variant.SMALL_CAPS,
    }
    PANGO_STYLE = {
        'normal': Pango.Style.NORMAL,
        'italic': Pango.Style.ITALIC,
        'oblique': Pango.Style.OBLIQUE,
    }
    PANGO_STRETCH = {
        'ultra-condensed': Pango.Stretch.ULTRA_CONDENSED,
        'extra-condensed': Pango.Stretch.EXTRA_CONDENSED,
        'condensed': Pango.Stretch.CONDENSED,
        'semi-condensed': Pango.Stretch.SEMI_CONDENSED,
        'normal': Pango.Stretch.NORMAL,
        'semi-expanded': Pango.Stretch.SEMI_EXPANDED,
        'expanded': Pango.Stretch.EXPANDED,
        'extra-expanded': Pango.Stretch.EXTRA_EXPANDED,
        'ultra-expanded': Pango.Stretch.ULTRA_EXPANDED,
    }
    PANGO_WRAP_WORD = Pango.WrapMode.WORD

    def set_text(layout, text):
        layout.set_text(text, -1)

    def parse_markup(markup):
        _, attributes_list, _, _ = Pango.parse_markup(markup, -1, '\x00')
        return attributes_list

    def get_size(line):
        _ink_extents, logical_extents = line.get_extents()
        return (units_to_double(logical_extents.width),
                units_to_double(logical_extents.height))

    def show_first_line(cairo_context, pango_layout, hinting):
        """Draw the given ``line`` to the Cairo ``context``."""
        if hinting:
            PangoCairo.update_layout(cairo_context, pango_layout)
        lines = pango_layout.get_lines_readonly()
        PangoCairo.show_layout_line(cairo_context, lines[0])

else:
    import pango as Pango
    import pangocairo

    PANGO_VARIANT = {
        'normal': Pango.VARIANT_NORMAL,
        'small-caps': Pango.VARIANT_SMALL_CAPS,
    }
    PANGO_STYLE = {
        'normal': Pango.STYLE_NORMAL,
        'italic': Pango.STYLE_ITALIC,
        'oblique': Pango.STYLE_OBLIQUE,
    }
    PANGO_STRETCH = {
        'ultra-condensed': Pango.STRETCH_ULTRA_CONDENSED,
        'extra-condensed': Pango.STRETCH_EXTRA_CONDENSED,
        'condensed': Pango.STRETCH_CONDENSED,
        'semi-condensed': Pango.STRETCH_SEMI_CONDENSED,
        'normal': Pango.STRETCH_NORMAL,
        'semi-expanded': Pango.STRETCH_SEMI_EXPANDED,
        'expanded': Pango.STRETCH_EXPANDED,
        'extra-expanded': Pango.STRETCH_EXTRA_EXPANDED,
        'ultra-expanded': Pango.STRETCH_ULTRA_EXPANDED,
    }
    PANGO_WRAP_WORD = Pango.WRAP_WORD
    set_text = Pango.Layout.set_text

    def create_pango_layout(context):
        return pangocairo.CairoContext(context).create_layout()

    def parse_markup(markup):
        attributes_list, _, _ = Pango.parse_markup(markup, '\x00')
        return attributes_list

    def get_size(line):
        _ink_extents, logical_extents = line.get_extents()
        _x, _y, width, height = logical_extents
        return units_to_double(width), units_to_double(height)

    def show_first_line(cairo_context, pango_layout, hinting):
        """Draw the given ``line`` to the Cairo ``context``."""
        context = pangocairo.CairoContext(cairo_context)
        if hinting:
            context.update_layout(pango_layout)
        context.show_layout_line(pango_layout.get_line(0))


# None as a the target for PDFSurface is new in pycairo 1.8.8.
# This helps with compat with earlier versions:
_DUMMY_FILE = BytesIO()
NON_HINTED_DUMMY_CONTEXT = cairo.Context(cairo.PDFSurface(_DUMMY_FILE, 1, 1))
HINTED_DUMMY_CONTEXT = cairo.Context(cairo.ImageSurface(
    cairo.FORMAT_ARGB32, 1, 1))


def units_from_double(value):
    return int(value * Pango.SCALE)


def units_to_double(value):
    # True division, with the __future__ import
    return value / Pango.SCALE


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
    layout = create_pango_layout(
        HINTED_DUMMY_CONTEXT if hinting else NON_HINTED_DUMMY_CONTEXT)
    font = Pango.FontDescription()
    assert not isinstance(style.font_family, basestring), (
        'font_family should be a list')
    font.set_family(','.join(style.font_family))
    font.set_variant(PANGO_VARIANT[style.font_variant])
    font.set_style(PANGO_STYLE[style.font_style])
    font.set_stretch(PANGO_STRETCH[style.font_stretch])
    font.set_absolute_size(units_from_double(style.font_size))
    font.set_weight(style.font_weight)
    layout.set_font_description(font)
    layout.set_wrap(PANGO_WRAP_WORD)
    set_text(layout, text)
    # Make sure that max_width * Pango.SCALE == max_width * 1024 fits in a
    # signed integer. Treat bigger values same as None: unconstrained width.
    if max_width is not None and max_width < 2**21:
        layout.set_width(units_from_double(max_width))
    word_spacing = style.word_spacing
    letter_spacing = style.letter_spacing
    if letter_spacing == 'normal':
        letter_spacing = 0
    if text and (word_spacing != 0 or letter_spacing != 0):
        word_spacing = units_from_double(word_spacing)
        letter_spacing = units_from_double(letter_spacing)
        markup = escape(text).replace(
            ' ', '<span letter_spacing="%i"> </span>' % (
                word_spacing + letter_spacing,))
        markup = '<span letter_spacing="%i">%s</span>' % (
            letter_spacing, markup)
        layout.set_attributes(parse_markup(markup))
    return layout


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
    first_line = layout.get_line(0)
    length = first_line.length
    width, height = get_size(first_line)
    baseline = units_to_double(layout.get_iter().get_baseline())
    if layout.get_line_count() >= 2:
        resume_at = layout.get_line(1).start_index
    else:
        resume_at = None
    return layout, length, resume_at, width, height, baseline


def line_widths(box, enable_hinting, width, skip=None):
    """Return the width for each line."""
    # TODO: without the lstrip, we get an extra empty line at the beginning. Is
    # there a better solution to avoid that?
    layout = create_layout(
        box.text[(skip or 0):].lstrip(), box.style, enable_hinting, width)
    for i in xrange(layout.get_line_count()):
        width, _height = get_size(layout.get_line(i))
        yield width
