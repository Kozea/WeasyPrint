# coding: utf8
"""
    weasyprint.text
    ---------------

    Interface with Pango to decide where to do line breaks and to draw text.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division
# XXX No unicode_literals, cffi likes native strings

from cgi import escape

import cffi
import cairocffi as cairo

from .compat import xrange, basestring


ffi = cffi.FFI()
ffi.cdef('''
    typedef enum {
        NORMAL,
        OBLIQUE,
        ITALIC
    } PangoStyle;

    typedef enum {
        THIN = 100,
        ULTRALIGHT = 200,
        LIGHT = 300,
        BOOK = 380,
        NORMAL = 400,
        MEDIUM = 500,
        SEMIBOLD = 600,
        BOLD = 700,
        ULTRABOLD = 800,
        HEAVY = 900,
        ULTRAHEAVY = 1000
    } PangoWeight;

    typedef enum {
        NORMAL,
        SMALL_CAPS
    } PangoVariant;

    typedef enum {
        ULTRA_CONDENSED,
        EXTRA_CONDENSED,
        CONDENSED,
        SEMI_CONDENSED,
        NORMAL,
        SEMI_EXPANDED,
        EXPANDED,
        EXTRA_EXPANDED,
        ULTRA_EXPANDED
    } PangoStretch;

      typedef enum {
        WRAP_WORD,
        WRAP_CHAR,
        WRAP_WORD_CHAR
    } PangoWrapMode;

    typedef unsigned int guint;
    typedef int gint;
    typedef gint gboolean;
    typedef void* gpointer;
    typedef ... cairo_t;
    typedef ... PangoLayout;
    typedef ... PangoFontDescription;
    typedef ... PangoLayoutIter;
    typedef ... PangoAttrList;
    typedef ... PangoAttrClass;
    typedef struct {
        const PangoAttrClass *klass;
        guint start_index;
        guint end_index;
    } PangoAttribute;
    typedef struct {
        PangoLayout *layout;
        gint         start_index;
        gint         length;
        /* ... */
    } PangoLayoutLine;

    double              pango_units_to_double               (int i);
    int                 pango_units_from_double             (double d);
    void                g_object_unref                      (gpointer object);


    PangoLayout * pango_cairo_create_layout (cairo_t *cr);
    void pango_layout_set_wrap (PangoLayout *layout, PangoWrapMode wrap);
    void pango_layout_set_width (PangoLayout *layout, int width);
    void pango_layout_set_attributes(PangoLayout *layout, PangoAttrList *attrs);
    void pango_layout_set_text (
        PangoLayout *layout, const char *text, int length);
    void pango_layout_set_font_description (
        PangoLayout *layout, const PangoFontDescription *desc);


    PangoFontDescription * pango_font_description_new (void);

    void pango_font_description_free (PangoFontDescription *desc);

    void pango_font_description_set_family (
        PangoFontDescription *desc, const char *family);

    void pango_font_description_set_variant (
        PangoFontDescription *desc, PangoVariant variant);

    void pango_font_description_set_style (
        PangoFontDescription *desc, PangoStyle style);

    void pango_font_description_set_stretch (
        PangoFontDescription *desc, PangoStretch stretch);

    void pango_font_description_set_weight (
        PangoFontDescription *desc, PangoWeight weight);

    void pango_font_description_set_absolute_size (
        PangoFontDescription *desc, double size);


    PangoAttrList *     pango_attr_list_new              (void);
    void                pango_attr_list_unref            (PangoAttrList *list);
    void                pango_attr_list_insert           (
        PangoAttrList *list, PangoAttribute *attr);

    PangoAttribute *    pango_attr_letter_spacing_new    (int letter_spacing);
    void                pango_attribute_destroy          (PangoAttribute *attr);


    PangoLayoutIter * pango_layout_get_iter (PangoLayout *layout);
    void pango_layout_iter_free (PangoLayoutIter *iter);

    gboolean pango_layout_iter_next_line (PangoLayoutIter *iter);

    PangoLayoutLine * pango_layout_iter_get_line_readonly (
        PangoLayoutIter *iter);

    int pango_layout_iter_get_baseline (PangoLayoutIter *iter);


    typedef struct  {
        int x;
        int y;
        int width;
        int height;
    } PangoRectangle;

    void pango_layout_line_get_extents (
        PangoLayoutLine *line,
        PangoRectangle *ink_rect, PangoRectangle *logical_rect);

    void pango_cairo_update_layout (cairo_t *cr, PangoLayout *layout);
    void pango_cairo_show_layout_line (cairo_t *cr, PangoLayoutLine *line);

''')
gobject = ffi.dlopen('gobject-2.0')
pango = ffi.dlopen('pango-1.0')
pangocairo = ffi.dlopen('pangocairo-1.0')

units_to_double = pango.pango_units_to_double
units_from_double = pango.pango_units_from_double


def to_enum(string):
    return str(string.replace('-', '_').upper())


def unicode_to_char_p(string):
    bytestring = string.encode('utf8').replace(b'\x00', b'')
    return ffi.new('char[]', bytestring), bytestring


def get_size(line):
    logical_extents = ffi.new('PangoRectangle *')
    pango.pango_layout_line_get_extents(line, ffi.NULL, logical_extents)
    return (units_to_double(logical_extents.width),
            units_to_double(logical_extents.height))


class Layout(object):
    """Object holding PangoLayout-related cdata pointers."""
    def iter_lines(self):
        layout_iter = ffi.gc(
            pango.pango_layout_get_iter(self.layout),
            pango.pango_layout_iter_free)
        while 1:
            yield pango.pango_layout_iter_get_line_readonly(layout_iter)
            if not pango.pango_layout_iter_next_line(layout_iter):
                return

    def set_text(self, text):
        text, bytestring = unicode_to_char_p(text)
        self.text = text
        self.text_bytes = bytestring
        pango.pango_layout_set_text(self.layout, text, -1)


def create_layout(text, style, hinting, max_width):
    """Return an opaque Pango layout with default Pango line-breaks.

    :param text: Unicode
    :param style: a :class:`StyleDict` of computed values
    :param hinting: whether to enable text hinting or not
    :param max_width:
        The maximum available width in the same unit as ``style.font_size``,
        or ``None`` for unlimited width.

    """
    layout_obj = Layout()
    dummy_context = layout_obj.dummy_context = (
        cairo.Context(cairo.ImageSurface('ARGB32', 1, 1))
        if hinting else
        cairo.Context(cairo.PDFSurface(None, 1, 1)))
    layout = layout_obj.layout = ffi.gc(
        pangocairo.pango_cairo_create_layout(ffi.cast(
            'cairo_t *', dummy_context._pointer)),
        gobject.g_object_unref)
    font = layout_obj.font = ffi.gc(
        pango.pango_font_description_new(),
        pango.pango_font_description_free)
    assert not isinstance(style.font_family, basestring), (
        'font_family should be a list')
    font_family = layout_obj.font_family = unicode_to_char_p(
        ','.join(style.font_family))[0]
    pango.pango_font_description_set_family(font, font_family)
    pango.pango_font_description_set_variant(font, to_enum(style.font_variant))
    pango.pango_font_description_set_style(font, to_enum(style.font_style))
    pango.pango_font_description_set_stretch(font, to_enum(style.font_stretch))
    pango.pango_font_description_set_weight(font, style.font_weight)
    pango.pango_font_description_set_absolute_size(
        font, units_from_double(style.font_size))
    pango.pango_layout_set_font_description(layout, font)
    pango.pango_layout_set_wrap(layout, 'WRAP_WORD')
    layout_obj.set_text(text)
    # Make sure that max_width * Pango.SCALE == max_width * 1024 fits in a
    # signed integer. Treat bigger values same as None: unconstrained width.
    if max_width is not None and max_width < 2 ** 21:
        pango.pango_layout_set_width(layout, units_from_double(max_width))
    word_spacing = style.word_spacing
    letter_spacing = style.letter_spacing
    if letter_spacing == 'normal':
        letter_spacing = 0
    if text and (word_spacing != 0 or letter_spacing != 0):
        letter_spacing = units_from_double(letter_spacing)
        space_spacing = units_from_double(word_spacing) + letter_spacing
        attr_list = pango.pango_attr_list_new()

        def add_attr(start, end, spacing):
            attr = pango.pango_attr_letter_spacing_new(spacing)
            attr.start_index = start
            attr.end_index = end
            pango.pango_attr_list_insert(attr_list, attr)

        text_bytes = layout_obj.text_bytes
        add_attr(0, len(text_bytes) + 1, letter_spacing)
        position = text_bytes.find(b' ')
        while position != -1:
            add_attr(position, position + 1, space_spacing)
            position = text_bytes.find(b' ', position + 1)
        pango.pango_layout_set_attributes(layout, attr_list)
        pango.pango_attr_list_unref(attr_list)
    return layout_obj


def split_first_line(text, style, hinting, max_width):
    """Fit as much as possible in the available width for one line of text.

    Return ``(layout, length, resume_at, width, height, baseline)``.

    ``layout``: a pango Layout with the first line
    ``length``: length in UTF-8 bytes of the first line
    ``resume_at``: The number of UTF-8 bytes to skip for the next line.
                   May be ``None`` if the whole text fits in one line.
                   This may be greater than ``length`` in case of preserved
                   newline characters.
    ``width``: width in pixels of the first line
    ``height``: height in pixels of the first line
    ``baseline``: baseline in pixels of the first line

    """
    # Step #1: Get a draft layout with the first line
    layout = None
    if max_width:
        expected_length = int(max_width / style.font_size * 2.5)
        if expected_length < len(text):
            # Try to use a small amount of text instead of the whole text
            layout = create_layout(
                text[:expected_length], style, hinting, max_width)
            lines = layout.iter_lines()
            first_line = next(lines, None)
            second_line = next(lines, None)
            if second_line is None:
                # The small amount of text fits in one line, give up and use
                # the whole text
                layout = None
    if layout is None:
        layout = create_layout(text, style, hinting, max_width)
        lines = layout.iter_lines()
        first_line = next(lines, None)
        second_line = next(lines, None)

    if second_line is not None:
        resume_at = second_line.start_index
    else:
        resume_at = None

    # Step #2: Build the final layout
    if max_width and second_line is not None:
        # The first line may have been cut too early by pango
        second_line_index = second_line.start_index
        first_part = text.encode('utf-8')[:second_line_index].decode('utf-8')
        second_part = text.encode('utf-8')[second_line_index:].decode('utf-8')
        next_word = second_part.split(' ', 1)[0]
        if next_word:
            new_first_line = first_part + next_word
            layout.set_text(new_first_line)
            lines = layout.iter_lines()
            first_line = next(lines, None)
            second_line = next(lines, None)
            if second_line is None:  # XXX never reached?
                resume_at = len(new_first_line.encode('utf-8')) + 1

    # Step #3: We have the right layout, find metrics
    length = first_line.length

    first_line_text = text.encode('utf-8')[:length].decode('utf-8')
    if first_line_text.endswith(' ') and resume_at:
        # Remove trailing spaces
        layout.set_text(first_line_text.rstrip(' '))
        first_line = next(layout.iter_lines(), None)
        length = first_line.length if first_line is not None else 0

    width, height = get_size(first_line)

    baseline = units_to_double(pango.pango_layout_iter_get_baseline(ffi.gc(
            pango.pango_layout_get_iter(layout.layout),
            pango.pango_layout_iter_free)))

    # Step #4: Return the layout and the metrics
    return layout, length, resume_at, width, height, baseline


def line_widths(box, enable_hinting, width, skip=None):
    """Return the width for each line."""
    # TODO: without the lstrip, we get an extra empty line at the beginning. Is
    # there a better solution to avoid that?
    layout = create_layout(
        box.text[(skip or 0):].lstrip(), box.style, enable_hinting, width)
    for line in layout.iter_lines():
        width, _height = get_size(line)
        yield width


def show_first_line(cairo_context, pango_layout, hinting):
    """Draw the given ``line`` to the Cairo ``context``."""
    cairo_context = ffi.cast('cairo_t *', cairo_context._pointer)
    if hinting:
        pangocairo.pango_cairo_update_layout(cairo_context, pango_layout.layout)
    pangocairo.pango_cairo_show_layout_line(
        cairo_context, next(pango_layout.iter_lines()))
