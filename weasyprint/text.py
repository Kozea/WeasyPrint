# coding: utf8
"""
    weasyprint.text
    ---------------

    Interface with Pango to decide where to do line breaks and to draw text.

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division
# XXX No unicode_literals, cffi likes native strings

import pyphen
import cffi
import cairocffi as cairo

from .compat import basestring


ffi = cffi.FFI()
ffi.cdef('''
    typedef enum {
        PANGO_STYLE_NORMAL,
        PANGO_STYLE_OBLIQUE,
        PANGO_STYLE_ITALIC
    } PangoStyle;

    typedef enum {
        PANGO_WEIGHT_THIN = 100,
        PANGO_WEIGHT_ULTRALIGHT = 200,
        PANGO_WEIGHT_LIGHT = 300,
        PANGO_WEIGHT_BOOK = 380,
        PANGO_WEIGHT_NORMAL = 400,
        PANGO_WEIGHT_MEDIUM = 500,
        PANGO_WEIGHT_SEMIBOLD = 600,
        PANGO_WEIGHT_BOLD = 700,
        PANGO_WEIGHT_ULTRABOLD = 800,
        PANGO_WEIGHT_HEAVY = 900,
        PANGO_WEIGHT_ULTRAHEAVY = 1000
    } PangoWeight;

    typedef enum {
        PANGO_VARIANT_NORMAL,
        PANGO_VARIANT_SMALL_CAPS
    } PangoVariant;

    typedef enum {
        PANGO_STRETCH_ULTRA_CONDENSED,
        PANGO_STRETCH_EXTRA_CONDENSED,
        PANGO_STRETCH_CONDENSED,
        PANGO_STRETCH_SEMI_CONDENSED,
        PANGO_STRETCH_NORMAL,
        PANGO_STRETCH_SEMI_EXPANDED,
        PANGO_STRETCH_EXPANDED,
        PANGO_STRETCH_EXTRA_EXPANDED,
        PANGO_STRETCH_ULTRA_EXPANDED
    } PangoStretch;

    typedef enum {
        PANGO_WRAP_WORD,
        PANGO_WRAP_CHAR,
        PANGO_WRAP_WORD_CHAR
    } PangoWrapMode;

    typedef unsigned int guint;
    typedef int gint;
    typedef gint gboolean;
    typedef void* gpointer;
    typedef ... cairo_t;
    typedef ... PangoLayout;
    typedef ... PangoContext;
    typedef ... PangoFontMetrics;
    typedef ... PangoLanguage;
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
    void                g_type_init                         (void);


    PangoLayout * pango_cairo_create_layout (cairo_t *cr);
    void pango_layout_set_width (PangoLayout *layout, int width);
    void pango_layout_set_attributes(
        PangoLayout *layout, PangoAttrList *attrs);
    void pango_layout_set_text (
        PangoLayout *layout, const char *text, int length);
    void pango_layout_set_font_description (
        PangoLayout *layout, const PangoFontDescription *desc);
    void pango_layout_set_wrap (
        PangoLayout *layout, PangoWrapMode wrap);


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


    PangoAttrList *     pango_attr_list_new             (void);
    void                pango_attr_list_unref           (PangoAttrList *list);
    void                pango_attr_list_insert          (
        PangoAttrList *list, PangoAttribute *attr);

    PangoAttribute *    pango_attr_letter_spacing_new   (int letter_spacing);
    void                pango_attribute_destroy         (PangoAttribute *attr);


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

    PangoContext *      pango_layout_get_context    (PangoLayout *layout);
    PangoFontMetrics *  pango_context_get_metrics   (
        PangoContext *context, const PangoFontDescription *desc,
        PangoLanguage *language);

    void    pango_font_metrics_unref            (PangoFontMetrics *metrics);
    int     pango_font_metrics_get_ascent       (PangoFontMetrics *metrics);
    int     pango_font_metrics_get_descent      (PangoFontMetrics *metrics);
    int     pango_font_metrics_get_approximate_char_width
                                                (PangoFontMetrics *metrics);
    int     pango_font_metrics_get_approximate_digit_width
                                                (PangoFontMetrics *metrics);
    int     pango_font_metrics_get_underline_thickness
                                                (PangoFontMetrics *metrics);
    int     pango_font_metrics_get_underline_position
                                                (PangoFontMetrics *metrics);
    int     pango_font_metrics_get_strikethrough_thickness
                                                (PangoFontMetrics *metrics);
    int     pango_font_metrics_get_strikethrough_position
                                                (PangoFontMetrics *metrics);

    void pango_cairo_update_layout (cairo_t *cr, PangoLayout *layout);
    void pango_cairo_show_layout_line (cairo_t *cr, PangoLayoutLine *line);

''')


def dlopen(ffi, *names):
    """Try various names for the same library, for different platforms."""
    for name in names:
        try:
            return ffi.dlopen(name)
        except OSError:
            pass
    # Re-raise the exception.
    return ffi.dlopen(names[0])  # pragma: no cover


gobject = dlopen(ffi, 'gobject-2.0', 'libgobject-2.0-0',
                 'libgobject-2.0.dylib')
pango = dlopen(ffi, 'pango-1.0', 'libpango-1.0-0', 'libpango-1.0.dylib')
pangocairo = dlopen(ffi, 'pangocairo-1.0', 'libpangocairo-1.0-0',
                    'libpangocairo-1.0.dylib')

gobject.g_type_init()

units_to_double = pango.pango_units_to_double
units_from_double = pango.pango_units_from_double

PYPHEN_DICTIONARY_CACHE = {}


PANGO_STYLE = {
    'normal': pango.PANGO_STYLE_NORMAL,
    'oblique': pango.PANGO_STYLE_OBLIQUE,
    'italic': pango.PANGO_STYLE_ITALIC,
}

PANGO_VARIANT = {
    'normal': pango.PANGO_VARIANT_NORMAL,
    'small-caps': pango.PANGO_VARIANT_SMALL_CAPS,
}

PANGO_STRETCH = {
    'ultra-condensed': pango.PANGO_STRETCH_ULTRA_CONDENSED,
    'extra-condensed': pango.PANGO_STRETCH_EXTRA_CONDENSED,
    'condensed': pango.PANGO_STRETCH_CONDENSED,
    'semi-condensed': pango.PANGO_STRETCH_SEMI_CONDENSED,
    'normal': pango.PANGO_STRETCH_NORMAL,
    'semi-expanded': pango.PANGO_STRETCH_SEMI_EXPANDED,
    'expanded': pango.PANGO_STRETCH_EXPANDED,
    'extra-expanded': pango.PANGO_STRETCH_EXTRA_EXPANDED,
    'ultra-expanded': pango.PANGO_STRETCH_ULTRA_EXPANDED,
}

PANGO_WRAP_MODE = {
    'WRAP_WORD': pango.PANGO_WRAP_WORD,
    'WRAP_CHAR': pango.PANGO_WRAP_CHAR,
    'WRAP_WORD_CHAR': pango.PANGO_WRAP_WORD_CHAR
}


def utf8_slice(string, slice_):
    return string.encode('utf-8')[slice_].decode('utf-8')


def unicode_to_char_p(string):
    """Return ``(pointer, bytestring)``.

    The byte string must live at least as long as the pointer is used.

    """
    bytestring = string.encode('utf8').replace(b'\x00', b'')
    return ffi.new('char[]', bytestring), bytestring


def get_size(line):
    logical_extents = ffi.new('PangoRectangle *')
    pango.pango_layout_line_get_extents(line, ffi.NULL, logical_extents)
    return (units_to_double(logical_extents.width),
            units_to_double(logical_extents.height))


def get_ink_position(line):
    ink_extents = ffi.new('PangoRectangle *')
    pango.pango_layout_line_get_extents(line, ink_extents, ffi.NULL)
    return (units_to_double(ink_extents.x), units_to_double(ink_extents.y))


def first_line_metrics(first_line, text, layout, resume_at, hyphenated=False):
    length = first_line.length
    if not hyphenated:
        first_line_text = utf8_slice(text, slice(length))
        if first_line_text.endswith(' ') and resume_at:
            # Remove trailing spaces
            layout.set_text(first_line_text.rstrip(' '))
            first_line = next(layout.iter_lines(), None)
            length = first_line.length if first_line is not None else 0
    width, height = get_size(first_line)
    baseline = units_to_double(pango.pango_layout_iter_get_baseline(ffi.gc(
        pango.pango_layout_get_iter(layout.layout),
        pango.pango_layout_iter_free)))
    return layout, length, resume_at, width, height, baseline


class Layout(object):
    """Object holding PangoLayout-related cdata pointers."""
    def __init__(self, hinting, font_size, style):
        self.dummy_context = (
            cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1))
            if hinting else
            cairo.Context(cairo.PDFSurface(None, 1, 1)))
        self.layout = ffi.gc(
            pangocairo.pango_cairo_create_layout(ffi.cast(
                'cairo_t *', self.dummy_context._pointer)),
            gobject.g_object_unref)
        self.font = font = ffi.gc(
            pango.pango_font_description_new(),
            pango.pango_font_description_free)
        assert not isinstance(style.font_family, basestring), (
            'font_family should be a list')
        family_p, family = unicode_to_char_p(','.join(style.font_family))
        pango.pango_font_description_set_family(font, family_p)
        pango.pango_font_description_set_variant(
            font, PANGO_VARIANT[style.font_variant])
        pango.pango_font_description_set_style(
            font, PANGO_STYLE[style.font_style])
        pango.pango_font_description_set_stretch(
            font, PANGO_STRETCH[style.font_stretch])
        pango.pango_font_description_set_weight(font, style.font_weight)
        pango.pango_font_description_set_absolute_size(
            font, units_from_double(font_size))
        pango.pango_layout_set_font_description(self.layout, font)

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

    def get_font_metrics(self):
        context = pango.pango_layout_get_context(self.layout)
        return FontMetrics(context, self.font)

    def set_wrap(self, wrap_mode):
        pango.pango_layout_set_wrap(self.layout, wrap_mode)


class FontMetrics(object):
    def __init__(self, context, font):
        self.metrics = ffi.gc(
            pango.pango_context_get_metrics(context, font, ffi.NULL),
            pango.pango_font_metrics_unref)

    def __dir__(self):
        return ['ascent', 'descent',
                'approximate_char_width', 'approximate_digit_width',
                'underline_thickness', 'underline_position',
                'strikethrough_thickness', 'strikethrough_position']

    def __getattr__(self, key):
        if key in dir(self):
            return units_to_double(
                getattr(pango, 'pango_font_metrics_get_' + key)(self.metrics))


def create_layout(text, style, hinting, max_width):
    """Return an opaque Pango layout with default Pango line-breaks.

    :param text: Unicode
    :param style: a :class:`StyleDict` of computed values
    :param hinting: whether to enable text hinting or not
    :param max_width:
        The maximum available width in the same unit as ``style.font_size``,
        or ``None`` for unlimited width.

    """
    layout = Layout(hinting, style.font_size, style)
    layout.set_text(text)
    # Make sure that max_width * Pango.SCALE == max_width * 1024 fits in a
    # signed integer. Treat bigger values same as None: unconstrained width.
    if max_width is not None and max_width < 2 ** 21:
        pango.pango_layout_set_width(
            layout.layout, units_from_double(max_width))
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

        text_bytes = layout.text_bytes
        add_attr(0, len(text_bytes) + 1, letter_spacing)
        position = text_bytes.find(b' ')
        while position != -1:
            add_attr(position, position + 1, space_spacing)
            position = text_bytes.find(b' ', position + 1)
        pango.pango_layout_set_attributes(layout.layout, attr_list)
        pango.pango_attr_list_unref(attr_list)
    return layout


def split_first_line(text, style, hinting, max_width, line_width):
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
    # In some cases (shrink-to-fit result being the preferred width)
    # this value is coming from Pango itself,
    # but floating point errors have accumulated:
    #   width2 = (width + X) - X   # in some cases, width2 < width
    # Increase the value a bit to compensate and not introduce
    # an unexpected line break.
    if max_width is not None:
        max_width *= 1.0001
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
    resume_at = None if second_line is None else second_line.start_index

    # Step #2: Don't hyphenize when it's not needed
    if max_width is None:
        # The first line can take all the place needed
        return first_line_metrics(first_line, text, layout, resume_at)
    first_line_width, _height = get_size(first_line)
    if second_line is None and first_line_width <= max_width:
        # The first line fits in the available width
        return first_line_metrics(first_line, text, layout, resume_at)

    # Step #3: Try to put the first word of the second line on the first line
    if first_line_width <= max_width:
        # The first line may have been cut too early by Pango
        second_line_index = second_line.start_index
        first_part = utf8_slice(text, slice(second_line_index))
        second_part = utf8_slice(text, slice(second_line_index, None))
    else:
        # The first word is longer than the line, try to hyphenize it
        first_part = ''
        second_part = text
    next_word = second_part.split(' ', 1)[0]

    if not next_word:
        # We did not find a word on the next line
        return first_line_metrics(first_line, text, layout, resume_at)

    # next_word might fit without a space afterwards.
    # Pango previously counted that space’s advance width.
    new_first_line = first_part + next_word
    layout.set_text(new_first_line)
    lines = layout.iter_lines()
    first_line = next(lines, None)
    second_line = next(lines, None)
    first_line_width, _height = get_size(first_line)
    if second_line is None and first_line_width <= max_width:
        # The next word fits in the first line, keep the layout
        resume_at = len(new_first_line.encode('utf-8')) + 1
        return first_line_metrics(first_line, text, layout, resume_at)

    # Step #4: Try to hyphenize
    hyphens = style.hyphens
    lang = style.lang and pyphen.language_fallback(style.lang)
    total, left, right = style.hyphenate_limit_chars

    hyphenated = False

    # Automatic hyphenation possible and next word is long enough
    if hyphens not in ('none', 'manual') and lang and len(next_word) >= total:
        first_line_width, _height = get_size(first_line)
        space = max_width - first_line_width
        if style.hyphenate_limit_zone.unit == '%':
            limit_zone = max_width * style.hyphenate_limit_zone.value / 100.
        else:
            limit_zone = style.hyphenate_limit_zone.value

        if space > limit_zone or space < 0:
            # The next word does not fit, try hyphenation
            dictionary_key = (lang, left, right, total)
            dictionary = PYPHEN_DICTIONARY_CACHE.get(dictionary_key)
            if dictionary is None:
                dictionary = pyphen.Pyphen(lang=lang, left=left, right=right)
                PYPHEN_DICTIONARY_CACHE[dictionary_key] = dictionary
            for first_word_part, _ in dictionary.iterate(next_word):
                new_first_line = (
                    first_part + first_word_part + style.hyphenate_character)
                temp_layout = create_layout(
                    new_first_line, style, hinting, max_width)
                temp_lines = temp_layout.iter_lines()
                temp_first_line = next(temp_lines, None)
                temp_second_line = next(temp_lines, None)

                if (temp_second_line is None and space >= 0) or space < 0:
                    hyphenated = True
                    # TODO: find why there's no need to .encode
                    resume_at = len(first_part + first_word_part)
                    layout = temp_layout
                    first_line = temp_first_line
                    second_line = temp_second_line
                    temp_first_line_width, _height = get_size(temp_first_line)
                    if temp_first_line_width <= max_width:
                        break

    # Step 5: Try to break word if it's too long for the line
    overflow_wrap = style.overflow_wrap
    first_line_width, _height = get_size(first_line)
    space = max_width - first_line_width
    # If we can break words and the first line is too long
    if overflow_wrap == 'break-word' and space < 0:
        if hyphenated:
            # Is it really OK to remove hyphenation for word-break ?
            new_first_line = new_first_line.rstrip(
                new_first_line[-(len(style.hyphenate_character)):])
            if second_line is not None:
                second_line_index = second_line.start_index
                second_part = utf8_slice(text, slice(second_line_index, None))
                new_first_line += second_part
            hyphenated = False

        # TODO: Modify code to preserve W3C condition:
        # "Shaping characters are still shaped as if the word were not broken"
        # The way new lines are processed in this function (one by one with no
        # memory of the last) prevents shaping characters (arabic, for
        # instance) from keeping their shape when wrapped on the next line with
        # pango layout.  Maybe insert Unicode shaping characters in text ?
        temp_layout = create_layout(new_first_line, style, hinting, max_width)
        temp_layout.set_wrap(PANGO_WRAP_MODE['WRAP_WORD_CHAR'])
        temp_lines = temp_layout.iter_lines()
        temp_first_line = next(temp_lines, None)
        temp_second_line = next(temp_lines, None)
        temp_second_line_index = (
            len(new_first_line) if temp_second_line is None
            else temp_second_line.start_index)
        resume_at = temp_second_line_index
        first_part = utf8_slice(text, slice(temp_second_line_index))
        layout = create_layout(first_part, style, hinting, max_width)
        lines = layout.iter_lines()
        first_line = next(lines, None)

    return first_line_metrics(first_line, text, layout, resume_at, hyphenated)


def line_widths(text, style, enable_hinting, width):
    """Return the width for each line."""
    layout = create_layout(text, style, enable_hinting, width)
    for line in layout.iter_lines():
        width, _height = get_size(line)
        yield width


def show_first_line(context, pango_layout, hinting):
    """Draw the given ``line`` to the Cairo ``context``."""
    context = ffi.cast('cairo_t *', context._pointer)
    if hinting:
        pangocairo.pango_cairo_update_layout(context, pango_layout.layout)
    pangocairo.pango_cairo_show_layout_line(
        context, next(pango_layout.iter_lines()))
