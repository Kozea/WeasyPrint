# coding: utf-8
"""
    weasyprint.text
    ---------------

    Interface with Pango to decide where to do line breaks and to draw text.

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division

import re
import warnings

import cairocffi as cairo
import cffi
import pyphen

from .compat import basestring
from .logger import LOGGER

# XXX No unicode_literals, cffi likes native strings


if cairo.cairo_version() <= 11400:
    warnings.warn('There are known rendering problems with Cairo <= 1.14.0')


PANGO_ATTR_FONT_FEATURES_CACHE = {}


ffi = cffi.FFI()
ffi.cdef('''
    // Cairo

    typedef enum {
        CAIRO_FONT_TYPE_TOY,
        CAIRO_FONT_TYPE_FT,
        CAIRO_FONT_TYPE_WIN32,
        CAIRO_FONT_TYPE_QUARTZ,
        CAIRO_FONT_TYPE_USER
    } cairo_font_type_t;


    // Pango

    typedef unsigned int guint;
    typedef int gint;
    typedef char gchar;
    typedef gint gboolean;
    typedef void* gpointer;
    typedef ... cairo_t;
    typedef ... PangoLayout;
    typedef ... PangoContext;
    typedef ... PangoFontMap;
    typedef ... PangoFontMetrics;
    typedef ... PangoLanguage;
    typedef ... PangoTabArray;
    typedef ... PangoFontDescription;
    typedef ... PangoLayoutIter;
    typedef ... PangoAttrList;
    typedef ... PangoAttrClass;

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

    typedef enum {
        PANGO_TAB_LEFT
    } PangoTabAlign;

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

    typedef struct  {
        int x;
        int y;
        int width;
        int height;
    } PangoRectangle;

    int pango_version (void);

    double pango_units_to_double (int i);
    int pango_units_from_double (double d);
    void g_object_unref (gpointer object);
    void g_type_init (void);

    void pango_layout_set_width (PangoLayout *layout, int width);
    void pango_layout_set_attributes (
        PangoLayout *layout, PangoAttrList *attrs);
    void pango_layout_set_text (
        PangoLayout *layout, const char *text, int length);
    void pango_layout_set_tabs (
        PangoLayout *layout, PangoTabArray *tabs);
    void pango_layout_set_font_description (
        PangoLayout *layout, const PangoFontDescription *desc);
    void pango_layout_set_wrap (
        PangoLayout *layout, PangoWrapMode wrap);

    PangoLayoutIter * pango_layout_get_iter (PangoLayout *layout);
    void pango_layout_iter_free (PangoLayoutIter *iter);
    gboolean pango_layout_iter_next_line (PangoLayoutIter *iter);
    PangoLayoutLine * pango_layout_iter_get_line_readonly (
        PangoLayoutIter *iter);
    int pango_layout_iter_get_baseline (PangoLayoutIter *iter);

    PangoFontDescription * pango_font_description_new (void);
    void pango_font_description_free (PangoFontDescription *desc);
    void pango_font_description_set_family (
        PangoFontDescription *desc, const char *family);
    void pango_font_description_set_style (
        PangoFontDescription *desc, PangoStyle style);
    void pango_font_description_set_stretch (
        PangoFontDescription *desc, PangoStretch stretch);
    void pango_font_description_set_weight (
        PangoFontDescription *desc, PangoWeight weight);
    void pango_font_description_set_absolute_size (
        PangoFontDescription *desc, double size);

    PangoFontMetrics * pango_context_get_metrics (
        PangoContext *context, const PangoFontDescription *desc,
        PangoLanguage *language);
    void pango_font_metrics_unref (PangoFontMetrics *metrics);
    int pango_font_metrics_get_ascent (PangoFontMetrics *metrics);
    int pango_font_metrics_get_descent (PangoFontMetrics *metrics);
    int pango_font_metrics_get_approximate_char_width (
        PangoFontMetrics *metrics);
    int pango_font_metrics_get_approximate_digit_width (
        PangoFontMetrics *metrics);
    int pango_font_metrics_get_underline_thickness (
        PangoFontMetrics *metrics);
    int pango_font_metrics_get_underline_position (
        PangoFontMetrics *metrics);
    int pango_font_metrics_get_strikethrough_thickness (
        PangoFontMetrics *metrics);
    int pango_font_metrics_get_strikethrough_position (
        PangoFontMetrics *metrics);

    PangoAttrList * pango_attr_list_new (void);
    void pango_attr_list_unref (PangoAttrList *list);
    void pango_attr_list_insert (
        PangoAttrList *list, PangoAttribute *attr);
    PangoAttribute * pango_attr_font_features_new (const gchar *features);
    PangoAttribute * pango_attr_letter_spacing_new (int letter_spacing);
    void pango_attribute_destroy (PangoAttribute *attr);

    PangoTabArray * pango_tab_array_new_with_positions (
        gint size, gboolean positions_in_pixels, PangoTabAlign first_alignment,
        gint first_position, ...);
    void pango_tab_array_free (PangoTabArray *tab_array);

    PangoLanguage * pango_language_from_string (const char *language);
    PangoLanguage * pango_language_get_default (void);
    void pango_context_set_language (
        PangoContext *context, PangoLanguage *language);
    void pango_context_set_font_map (
        PangoContext *context, PangoFontMap *font_map);

    void pango_layout_line_get_extents (
        PangoLayoutLine *line,
        PangoRectangle *ink_rect, PangoRectangle *logical_rect);

    PangoContext * pango_layout_get_context (PangoLayout *layout);


    // PangoCairo

    PangoLayout * pango_cairo_create_layout (cairo_t *cr);
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


gobject = dlopen(ffi, 'gobject-2.0', 'libgobject-2.0-0', 'libgobject-2.0.so',
                 'libgobject-2.0.dylib')
pango = dlopen(ffi, 'pango-1.0', 'libpango-1.0-0', 'libpango-1.0.so',
               'libpango-1.0.dylib')
pangocairo = dlopen(ffi, 'pangocairo-1.0', 'libpangocairo-1.0-0',
                    'libpangocairo-1.0.so', 'libpangocairo-1.0.dylib')

gobject.g_type_init()

units_to_double = pango.pango_units_to_double
units_from_double = pango.pango_units_from_double

PYPHEN_DICTIONARY_CACHE = {}


PANGO_STYLE = {
    'normal': pango.PANGO_STYLE_NORMAL,
    'oblique': pango.PANGO_STYLE_OBLIQUE,
    'italic': pango.PANGO_STYLE_ITALIC,
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

# From http://www.microsoft.com/typography/otspec/languagetags.htm
LST_TO_ISO = {
    'aba': 'abq',
    'afk': 'afr',
    'afr': 'aar',
    'agw': 'ahg',
    'als': 'gsw',
    'alt': 'atv',
    'ari': 'aiw',
    'ark': 'mhv',
    'ath': 'apk',
    'avr': 'ava',
    'bad': 'bfq',
    'bad0': 'bad',
    'bag': 'bfy',
    'bal': 'krc',
    'bau': 'bci',
    'bch': 'bcq',
    'bgr': 'bul',
    'bil': 'byn',
    'bkf': 'bla',
    'bli': 'bal',
    'bln': 'bjt',
    'blt': 'bft',
    'bmb': 'bam',
    'bri': 'bra',
    'brm': 'mya',
    'bsh': 'bak',
    'bti': 'btb',
    'chg': 'sgw',
    'chh': 'hne',
    'chi': 'nya',
    'chk': 'ckt',
    'chk0': 'chk',
    'chu': 'chv',
    'chy': 'chy',
    'cmr': 'swb',
    'crr': 'crx',
    'crt': 'crh',
    'csl': 'chu',
    'csy': 'ces',
    'dcr': 'cwd',
    'dgr': 'doi',
    'djr': 'dje',
    'djr0': 'djr',
    'dng': 'ada',
    'dnk': 'din',
    'dri': 'prs',
    'dun': 'dng',
    'dzn': 'dzo',
    'ebi': 'igb',
    'ecr': 'crj',
    'edo': 'bin',
    'erz': 'myv',
    'esp': 'spa',
    'eti': 'est',
    'euq': 'eus',
    'evk': 'evn',
    'evn': 'eve',
    'fan': 'acf',
    'fan0': 'fan',
    'far': 'fas',
    'fji': 'fij',
    'fle': 'vls',
    'fne': 'enf',
    'fos': 'fao',
    'fri': 'fry',
    'frl': 'fur',
    'frp': 'frp',
    'fta': 'fuf',
    'gad': 'gaa',
    'gae': 'gla',
    'gal': 'glg',
    'gaw': 'gbm',
    'gil': 'niv',
    'gil0': 'gil',
    'gmz': 'guk',
    'grn': 'kal',
    'gro': 'grt',
    'gua': 'grn',
    'hai': 'hat',
    'hal': 'flm',
    'har': 'hoj',
    'hbn': 'amf',
    'hma': 'mrj',
    'hnd': 'hno',
    'ho': 'hoc',
    'hri': 'har',
    'hye0': 'hye',
    'ijo': 'ijc',
    'ing': 'inh',
    'inu': 'iku',
    'iri': 'gle',
    'irt': 'gle',
    'ism': 'smn',
    'iwr': 'heb',
    'jan': 'jpn',
    'jii': 'yid',
    'jud': 'lad',
    'jul': 'dyu',
    'kab': 'kbd',
    'kab0': 'kab',
    'kac': 'kfr',
    'kal': 'kln',
    'kar': 'krc',
    'keb': 'ktb',
    'kge': 'kat',
    'kha': 'kjh',
    'khk': 'kca',
    'khs': 'kca',
    'khv': 'kca',
    'kis': 'kqs',
    'kkn': 'kex',
    'klm': 'xal',
    'kmb': 'kam',
    'kmn': 'kfy',
    'kmo': 'kmw',
    'kms': 'kxc',
    'knr': 'kau',
    'kod': 'kfa',
    'koh': 'okm',
    'kon': 'ktu',
    'kon0': 'kon',
    'kop': 'koi',
    'koz': 'kpv',
    'kpl': 'kpe',
    'krk': 'kaa',
    'krm': 'kdr',
    'krn': 'kar',
    'krt': 'kqy',
    'ksh': 'kas',
    'ksh0': 'ksh',
    'ksi': 'kha',
    'ksm': 'sjd',
    'kui': 'kxu',
    'kul': 'kfx',
    'kuu': 'kru',
    'kuy': 'kdt',
    'kyk': 'kpy',
    'lad': 'lld',
    'lah': 'bfu',
    'lak': 'lbe',
    'lam': 'lmn',
    'laz': 'lzz',
    'lcr': 'crm',
    'ldk': 'lbj',
    'lma': 'mhr',
    'lmb': 'lif',
    'lmw': 'ngl',
    'lsb': 'dsb',
    'lsm': 'smj',
    'lth': 'lit',
    'luh': 'luy',
    'lvi': 'lav',
    'maj': 'mpe',
    'mak': 'vmw',
    'man': 'mns',
    'map': 'arn',
    'maw': 'mwr',
    'mbn': 'kmb',
    'mch': 'mnc',
    'mcr': 'crm',
    'mde': 'men',
    'men': 'mym',
    'miz': 'lus',
    'mkr': 'mak',
    'mle': 'mdy',
    'mln': 'mlq',
    'mlr': 'mal',
    'mly': 'msa',
    'mnd': 'mnk',
    'mng': 'mon',
    'mnk': 'man',
    'mnx': 'glv',
    'mok': 'mdf',
    'mon': 'mnw',
    'mth': 'mai',
    'mts': 'mlt',
    'mun': 'unr',
    'nan': 'gld',
    'nas': 'nsk',
    'ncr': 'csw',
    'ndg': 'ndo',
    'nhc': 'csw',
    'nis': 'dap',
    'nkl': 'nyn',
    'nko': 'nqo',
    'nor': 'nob',
    'nsm': 'sme',
    'nta': 'nod',
    'nto': 'epo',
    'nyn': 'nno',
    'ocr': 'ojs',
    'ojb': 'oji',
    'oro': 'orm',
    'paa': 'sam',
    'pal': 'pli',
    'pap': 'plp',
    'pap0': 'pap',
    'pas': 'pus',
    'pgr': 'ell',
    'pil': 'fil',
    'plg': 'pce',
    'plk': 'pol',
    'ptg': 'por',
    'qin': 'bgr',
    'rbu': 'bxr',
    'rcr': 'atj',
    'rms': 'roh',
    'rom': 'ron',
    'roy': 'rom',
    'rsy': 'rue',
    'rua': 'kin',
    'sad': 'sck',
    'say': 'chp',
    'sek': 'xan',
    'sel': 'sel',
    'sgo': 'sag',
    'sgs': 'sgs',
    'sib': 'sjo',
    'sig': 'xst',
    'sks': 'sms',
    'sky': 'slk',
    'sla': 'scs',
    'sml': 'som',
    'sna': 'seh',
    'sna0': 'sna',
    'snh': 'sin',
    'sog': 'gru',
    'srb': 'srp',
    'ssl': 'xsl',
    'ssm': 'sma',
    'sur': 'suq',
    'sve': 'swe',
    'swa': 'aii',
    'swk': 'swa',
    'swz': 'ssw',
    'sxt': 'ngo',
    'taj': 'tgk',
    'tcr': 'cwd',
    'tgn': 'ton',
    'tgr': 'tig',
    'tgy': 'tir',
    'tht': 'tah',
    'tib': 'bod',
    'tkm': 'tuk',
    'tmn': 'tem',
    'tna': 'tsn',
    'tne': 'enh',
    'tng': 'toi',
    'tod': 'xal',
    'tod0': 'tod',
    'trk': 'tur',
    'tsg': 'tso',
    'tua': 'tru',
    'tul': 'tcy',
    'tuv': 'tyv',
    'twi': 'aka',
    'usb': 'hsb',
    'uyg': 'uig',
    'vit': 'vie',
    'vro': 'vro',
    'wa': 'wbm',
    'wag': 'wbr',
    'wcr': 'crk',
    'wel': 'cym',
    'wlf': 'wol',
    'xbd': 'khb',
    'xhs': 'xho',
    'yak': 'sah',
    'yba': 'yor',
    'ycr': 'cre',
    'yim': 'iii',
    'zhh': 'zho',
    'zhp': 'zho',
    'zhs': 'zho',
    'zht': 'zho',
    'znd': 'zne',
}


def utf8_slice(string, slice_):
    return string.encode('utf-8')[slice_].decode('utf-8')


def unicode_to_char_p(string):
    """Return ``(pointer, bytestring)``.

    The byte string must live at least as long as the pointer is used.

    """
    bytestring = string.encode('utf8').replace(b'\x00', b'')
    return ffi.new('char[]', bytestring), bytestring


def get_size(line, style):
    logical_extents = ffi.new('PangoRectangle *')
    pango.pango_layout_line_get_extents(line, ffi.NULL, logical_extents)
    width, height = (units_to_double(logical_extents.width),
                     units_to_double(logical_extents.height))
    if style.letter_spacing != 'normal':
        width += style.letter_spacing
    return width, height


def get_ink_position(line):
    ink_extents = ffi.new('PangoRectangle *')
    pango.pango_layout_line_get_extents(line, ink_extents, ffi.NULL)
    return (units_to_double(ink_extents.x), units_to_double(ink_extents.y))


def first_line_metrics(first_line, text, layout, resume_at, space_collapse,
                       style, hyphenated=False, hyphenation_character=None):
    length = first_line.length
    if hyphenated:
        length -= len(hyphenation_character.encode('utf8'))
    elif resume_at:
        # Set an infinite width as we don't want to break lines when drawing,
        # the lines have already been split and the size may differ.
        pango.pango_layout_set_width(layout.layout, -1)
        # Create layout with final text
        first_line_text = utf8_slice(text, slice(length))
        # Remove trailing spaces if spaces collapse
        if space_collapse:
            first_line_text = first_line_text.rstrip(u' ')
        # Remove soft hyphens
        layout.set_text(first_line_text.replace(u'\u00ad', u''))
        first_line = next(layout.iter_lines(), None)
        length = first_line.length if first_line is not None else 0
        soft_hyphens = 0
        if u'\u00ad' in first_line_text:
            if first_line_text[0] == u'\u00ad':
                length += 2  # len(u'\u00ad'.encode('utf8'))
            for i in range(len(layout.text_bytes.decode('utf8'))):
                while i + soft_hyphens + 1 < len(first_line_text):
                    if first_line_text[i + soft_hyphens + 1] == u'\u00ad':
                        soft_hyphens += 1
                    else:
                        break
        length += soft_hyphens * 2  # len(u'\u00ad'.encode('utf8'))
    width, height = get_size(first_line, style)
    baseline = units_to_double(pango.pango_layout_iter_get_baseline(ffi.gc(
        pango.pango_layout_get_iter(layout.layout),
        pango.pango_layout_iter_free)))
    return layout, length, resume_at, width, height, baseline


class Layout(object):
    """Object holding PangoLayout-related cdata pointers."""
    def __init__(self, context, font_size, style):
        self.context = context
        hinting = context.enable_hinting if context else False
        cairo_dummy_context = (
            cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1))
            if hinting else cairo.Context(cairo.PDFSurface(None, 1, 1)))
        self.layout = ffi.gc(
            pangocairo.pango_cairo_create_layout(ffi.cast(
                'cairo_t *', cairo_dummy_context._pointer)),
            gobject.g_object_unref)
        pango_context = pango.pango_layout_get_context(self.layout)
        if context and context.font_config.font_map:
            pango.pango_context_set_font_map(
                pango_context, context.font_config.font_map)
        self.font = ffi.gc(
            pango.pango_font_description_new(),
            pango.pango_font_description_free)
        if style.font_language_override != 'normal':
            lang_p, lang = unicode_to_char_p(LST_TO_ISO.get(
                style.font_language_override.lower(),
                style.font_language_override))
        elif style.lang:
            lang_p, lang = unicode_to_char_p(style.lang)
        else:
            lang = None
            self.language = pango.pango_language_get_default()
        if lang:
            self.language = pango.pango_language_from_string(lang_p)
            pango.pango_context_set_language(pango_context, self.language)

        assert not isinstance(style.font_family, basestring), (
            'font_family should be a list')
        family_p, family = unicode_to_char_p(','.join(style.font_family))
        pango.pango_font_description_set_family(self.font, family_p)
        pango.pango_font_description_set_style(
            self.font, PANGO_STYLE[style.font_style])
        pango.pango_font_description_set_stretch(
            self.font, PANGO_STRETCH[style.font_stretch])
        pango.pango_font_description_set_weight(self.font, style.font_weight)
        pango.pango_font_description_set_absolute_size(
            self.font, units_from_double(font_size))
        pango.pango_layout_set_font_description(self.layout, self.font)

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
        return FontMetrics(context, self.font, self.language)

    def set_wrap(self, wrap_mode):
        pango.pango_layout_set_wrap(self.layout, wrap_mode)

    def set_tabs(self, style):
        if isinstance(style.tab_size, int):
            layout = Layout(
                context=self.context, font_size=style.font_size,
                style=style)
            layout.set_text(' ' * style.tab_size)
            line, = layout.iter_lines()
            width, _ = get_size(line, style)
            width = int(round(width))
        else:
            width = int(style.tab_size.value)
        # TODO: 0 is not handled correctly by Pango
        array = ffi.gc(
            pango.pango_tab_array_new_with_positions(
                1, True, pango.PANGO_TAB_LEFT, width or 1),
            pango.pango_tab_array_free)
        pango.pango_layout_set_tabs(self.layout, array)


class FontMetrics(object):
    def __init__(self, context, font, language):
        self.metrics = ffi.gc(
            pango.pango_context_get_metrics(context, font, language),
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


def get_font_features(
        font_kerning='normal', font_variant_ligatures='normal',
        font_variant_position='normal', font_variant_caps='normal',
        font_variant_numeric='normal', font_variant_alternates='normal',
        font_variant_east_asian='normal', font_feature_settings='normal'):
    """Get the font features from the different properties in style.

    See https://www.w3.org/TR/css-fonts-3/#feature-precedence

    """
    features = {}
    ligature_keys = {
        'common-ligatures': ['liga', 'clig'],
        'historical-ligatures': ['hlig'],
        'discretionary-ligatures': ['dlig'],
        'contextual': ['calt']}
    caps_keys = {
        'small-caps': ['smcp'],
        'all-small-caps': ['c2sc', 'smcp'],
        'petite-caps': ['pcap'],
        'all-petite-caps': ['c2pc', 'pcap'],
        'unicase': ['unic'],
        'titling-caps': ['titl']}
    numeric_keys = {
        'lining-nums': 'lnum',
        'oldstyle-nums': 'onum',
        'proportional-nums': 'pnum',
        'tabular-nums': 'tnum',
        'diagonal-fractions': 'frac',
        'stacked-fractions': 'afrc',
        'ordinal': 'ordn',
        'slashed-zero': 'zero'}
    east_asian_keys = {
        'jis78': 'jp78',
        'jis83': 'jp83',
        'jis90': 'jp90',
        'jis04': 'jp04',
        'simplified': 'smpl',
        'traditional': 'trad',
        'full-width': 'fwid',
        'proportional-width': 'pwid',
        'ruby': 'ruby'}

    # Step 1: getting the default, we rely on Pango for this
    # Step 2: @font-face font-variant, done in fonts.add_font_face
    # Step 3: @font-face font-feature-settings, done in fonts.add_font_face

    # Step 4: font-variant and OpenType features

    if font_kerning != 'auto':
        features['kern'] = int(font_kerning == 'normal')

    if font_variant_ligatures == 'none':
        for keys in ligature_keys.values():
            for key in keys:
                features[key] = 0
    elif font_variant_ligatures != 'normal':
        for ligature_type in font_variant_ligatures:
            value = 1
            if ligature_type.startswith('no-'):
                value = 0
                ligature_type = ligature_type[3:]
            for key in ligature_keys[ligature_type]:
                features[key] = value

    if font_variant_position == 'sub':
        # TODO: the specification asks for additional checks
        # https://www.w3.org/TR/css-fonts-3/#font-variant-position-prop
        features['subs'] = 1
    elif font_variant_position == 'super':
        features['sups'] = 1

    if font_variant_caps != 'normal':
        # TODO: the specification asks for additional checks
        # https://www.w3.org/TR/css-fonts-3/#font-variant-caps-prop
        for key in caps_keys[font_variant_caps]:
            features[key] = 1

    if font_variant_numeric != 'normal':
        for key in font_variant_numeric:
            features[numeric_keys[key]] = 1

    if font_variant_alternates != 'normal':
        # TODO: support other values
        # See https://www.w3.org/TR/css-fonts-3/#font-variant-caps-prop
        if font_variant_alternates == 'historical-forms':
            features['hist'] = 1

    if font_variant_east_asian != 'normal':
        for key in font_variant_east_asian:
            features[east_asian_keys[key]] = 1

    # Step 5: incompatible non-OpenType features, already handled by Pango

    # Step 6: font-feature-settings

    if font_feature_settings != 'normal':
        features.update(dict(font_feature_settings))

    return features


def create_layout(text, style, context, max_width):
    """Return an opaque Pango layout with default Pango line-breaks.

    :param text: Unicode
    :param style: a :class:`StyleDict` of computed values
    :param hinting: whether to enable text hinting or not
    :param max_width:
        The maximum available width in the same unit as ``style.font_size``,
        or ``None`` for unlimited width.

    """
    text_wrap = style.white_space in ('pre', 'nowrap')
    if text_wrap:
        max_width = None

    layout = Layout(context, style.font_size, style)
    layout.set_text(text)

    # Make sure that max_width * Pango.SCALE == max_width * 1024 fits in a
    # signed integer. Treat bigger values same as None: unconstrained width.
    if max_width is not None and max_width < 2 ** 21:
        pango.pango_layout_set_width(
            layout.layout, units_from_double(max_width))

    text_bytes = layout.text_bytes

    # Word and letter spacings
    word_spacing = style.word_spacing
    letter_spacing = style.letter_spacing
    if letter_spacing == 'normal':
        letter_spacing = 0
    if text and (word_spacing != 0 or letter_spacing != 0):
        letter_spacing = units_from_double(letter_spacing)
        space_spacing = units_from_double(word_spacing) + letter_spacing
        attr_list = pango.pango_attr_list_new()

        def add_attr(start, end, spacing):
            # TODO: attributes should be freed
            attr = pango.pango_attr_letter_spacing_new(spacing)
            attr.start_index, attr.end_index = start, end
            pango.pango_attr_list_insert(attr_list, attr)

        add_attr(0, len(text_bytes) + 1, letter_spacing)
        position = text_bytes.find(b' ')
        while position != -1:
            add_attr(position, position + 1, space_spacing)
            position = text_bytes.find(b' ', position + 1)

        pango.pango_layout_set_attributes(layout.layout, attr_list)
        pango.pango_attr_list_unref(attr_list)

    features = get_font_features(
        style.font_kerning, style.font_variant_ligatures,
        style.font_variant_position, style.font_variant_caps,
        style.font_variant_numeric, style.font_variant_alternates,
        style.font_variant_east_asian, style.font_feature_settings)
    if features:
        features = ','.join(
            ('%s %i' % (key, value)) for key, value in features.items())

        # TODO: attributes should be freed.
        # In the meantime, keep a cache to avoid leaking too many of them.
        attr = PANGO_ATTR_FONT_FEATURES_CACHE.get(features)
        if attr is None:
            try:
                attr = pango.pango_attr_font_features_new(
                    features.encode('ascii'))
            except AttributeError:
                LOGGER.warning(
                    'OpenType features are not available with Pango < 1.38')
            else:
                PANGO_ATTR_FONT_FEATURES_CACHE[features] = attr
        if attr is not None:
            attr_list = pango.pango_attr_list_new()
            pango.pango_attr_list_insert(attr_list, attr)
            pango.pango_layout_set_attributes(layout.layout, attr_list)

    # Tabs width
    if style.tab_size != 8:  # Default Pango value is 8
        layout.set_tabs(style)

    return layout


def split_first_line(text, style, context, max_width, line_width):
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
    text_wrap = style.white_space in ('pre', 'nowrap')
    space_collapse = style.white_space in ('normal', 'nowrap', 'pre-line')

    if text_wrap:
        max_width = None

    # Step #1: Get a draft layout with the first line
    layout = create_layout(text, style, context, max_width)
    lines = layout.iter_lines()
    first_line = next(lines, None)
    second_line = next(lines, None)
    resume_at = None if second_line is None else second_line.start_index

    # Step #2: Don't hyphenize when it's not needed
    if max_width is None:
        # The first line can take all the place needed
        return first_line_metrics(
            first_line, text, layout, resume_at, space_collapse, style)
    first_line_width, _ = get_size(first_line, style)
    if second_line is None and first_line_width <= max_width:
        # The first line fits in the available width
        return first_line_metrics(
            first_line, text, layout, resume_at, space_collapse, style)

    # Step #3: Try to put the first word of the second line on the first line
    # https://mail.gnome.org/archives/gtk-i18n-list/2013-September/msg00006
    # is a good thread related to this problem.
    if first_line_width <= max_width:
        # The first line may have been cut too early by Pango
        second_line_index = second_line.start_index
        first_line_text = utf8_slice(text, slice(second_line_index))
        second_line_text = utf8_slice(text, slice(second_line_index, None))
    else:
        # The first word is longer than the line, try to hyphenize it
        first_line_text = ''
        second_line_text = text

    next_word = second_line_text.split(' ', 1)[0]
    if next_word:
        if space_collapse:
            # next_word might fit without a space afterwards
            # only try when space collapsing is allowed
            new_first_line_text = first_line_text + next_word
            layout.set_text(new_first_line_text)
            lines = layout.iter_lines()
            first_line = next(lines, None)
            second_line = next(lines, None)
            first_line_width, _ = get_size(first_line, style)
            if second_line is None and first_line_text:
                # The next word fits in the first line, keep the layout
                resume_at = len(new_first_line_text.encode('utf-8')) + 1
                if resume_at == len(text.encode('utf-8')):
                    resume_at = None
                return first_line_metrics(
                    first_line, text, layout, resume_at, space_collapse, style)
            elif second_line:
                # Text may have been split elsewhere by Pango earlier
                resume_at = second_line.start_index
            else:
                resume_at = first_line.length + 1
    elif first_line_text:
        # We found something on the first line but we did not find a word on
        # the next line, no need to hyphenate, we can keep the current layout
        return first_line_metrics(
            first_line, text, layout, resume_at, space_collapse, style)

    # Step #4: Try to hyphenize
    hyphens = style.hyphens
    lang = style.lang and pyphen.language_fallback(style.lang)
    total, left, right = style.hyphenate_limit_chars
    hyphenated = False
    soft_hyphen = u'\u00ad'

    # Automatic hyphenation possible and next word is long enough
    if hyphens != 'none' and len(next_word) >= total:
        first_line_width, _ = get_size(first_line, style)
        space = max_width - first_line_width
        if style.hyphenate_limit_zone.unit == '%':
            limit_zone = max_width * style.hyphenate_limit_zone.value / 100.
        else:
            limit_zone = style.hyphenate_limit_zone.value

        if space > limit_zone or space < 0:
            # Manual hyphenation: check that the line ends with a soft hyphen
            # and add the missing hyphen
            if hyphens == 'manual':
                if first_line_text.endswith(soft_hyphen):
                    # The first line has been split on a soft hyphen
                    if u' ' in first_line_text:
                        first_line_text, next_word = (
                            first_line_text.rsplit(u' ', 1))
                        next_word = u' ' + next_word
                        layout.set_text(first_line_text)
                        lines = layout.iter_lines()
                        first_line = next(lines, None)
                        second_line = next(lines, None)
                        resume_at = len(
                            (first_line_text + u' ').encode('utf8'))
                    else:
                        first_line_text, next_word = u'', first_line_text
                soft_hyphen_indexes = [
                    match.start() for match in
                    re.finditer(soft_hyphen, next_word)]
                soft_hyphen_indexes.reverse()
                dictionary_iterations = [
                    next_word[:i + 1] for i in soft_hyphen_indexes]
            elif hyphens == 'auto' and lang:
                # The next word does not fit, try hyphenation
                dictionary_key = (lang, left, right, total)
                dictionary = PYPHEN_DICTIONARY_CACHE.get(dictionary_key)
                if dictionary is None:
                    dictionary = pyphen.Pyphen(
                        lang=lang, left=left, right=right)
                    PYPHEN_DICTIONARY_CACHE[dictionary_key] = dictionary
                dictionary_iterations = [
                    start for start, end in dictionary.iterate(next_word)]
            else:
                dictionary_iterations = []

            if dictionary_iterations:
                for first_word_part in dictionary_iterations:
                    new_first_line_text = first_line_text + first_word_part
                    hyphenated_first_line_text = (
                        new_first_line_text + style.hyphenate_character)
                    new_layout = create_layout(
                        hyphenated_first_line_text, style, context, max_width)
                    new_lines = new_layout.iter_lines()
                    new_first_line = next(new_lines, None)
                    new_second_line = next(new_lines, None)
                    new_first_line_width, _ = get_size(new_first_line, style)
                    new_space = max_width - new_first_line_width
                    if new_second_line is None and (
                            new_space >= 0 or
                            first_word_part == dictionary_iterations[-1]):
                        hyphenated = True
                        layout = new_layout
                        first_line = new_first_line
                        second_line = new_second_line
                        resume_at = len(new_first_line_text.encode('utf8'))
                        if text[len(new_first_line_text)] == soft_hyphen:
                            resume_at += len(soft_hyphen.encode('utf8'))
                        break

                if not hyphenated and not first_line_text:
                    # Recreate the layout with no max_width to be sure that
                    # we don't break inside the hyphenate-character string
                    hyphenated = True
                    layout.set_text(hyphenated_first_line_text)
                    pango.pango_layout_set_width(
                        layout.layout, units_from_double(-1))
                    lines = layout.iter_lines()
                    first_line = next(lines, None)
                    second_line = next(lines, None)
                    resume_at = len(new_first_line_text.encode('utf8'))
                    if text[len(first_line_text)] == soft_hyphen:
                        resume_at += len(soft_hyphen.encode('utf8'))

    if not hyphenated and first_line_text.endswith(soft_hyphen):
        # Recreate the layout with no max_width to be sure that
        # we don't break inside the hyphenate-character string
        hyphenated = True
        hyphenated_first_line_text = (
            first_line_text + style.hyphenate_character)
        layout.set_text(hyphenated_first_line_text)
        pango.pango_layout_set_width(
            layout.layout, units_from_double(-1))
        lines = layout.iter_lines()
        first_line = next(lines, None)
        second_line = next(lines, None)
        resume_at = len(first_line_text.encode('utf8'))

    # Step 5: Try to break word if it's too long for the line
    overflow_wrap = style.overflow_wrap
    first_line_width, _ = get_size(first_line, style)
    space = max_width - first_line_width
    # If we can break words and the first line is too long
    if overflow_wrap == 'break-word' and space < 0:
        # Is it really OK to remove hyphenation for word-break ?
        hyphenated = False
        # TODO: Modify code to preserve W3C condition:
        # "Shaping characters are still shaped as if the word were not broken"
        # The way new lines are processed in this function (one by one with no
        # memory of the last) prevents shaping characters (arabic, for
        # instance) from keeping their shape when wrapped on the next line with
        # pango layout.  Maybe insert Unicode shaping characters in text ?
        layout.set_text(text)
        pango.pango_layout_set_width(
            layout.layout, units_from_double(max_width))
        layout.set_wrap(PANGO_WRAP_MODE['WRAP_CHAR'])
        temp_lines = layout.iter_lines()
        next(temp_lines, None)
        temp_second_line = next(temp_lines, None)
        temp_second_line_index = (
            len(text.encode('utf-8')) if temp_second_line is None
            else temp_second_line.start_index)
        # TODO: WRAP_CHAR is said to "wrap lines at character boundaries", but
        # it doesn't. Looks like it tries to split at word boundaries and then
        # at character boundaries if there's no enough space for a full word,
        # just as WRAP_WORD_CHAR does. That's why we have to split this text
        # twice. Find why. It may be related to the problem described in the
        # link given in step #3.
        first_line_text = utf8_slice(text, slice(temp_second_line_index))
        layout.set_text(first_line_text)
        lines = layout.iter_lines()
        first_line = next(lines, None)
        second_line = next(lines, None)
        resume_at = (
            first_line.length if second_line is None
            else second_line.start_index)

    return first_line_metrics(
        first_line, text, layout, resume_at, space_collapse, style, hyphenated,
        style.hyphenate_character)


def line_widths(text, style, context, width):
    """Return the width for each line."""
    layout = create_layout(text, style, context, width)
    for line in layout.iter_lines():
        width, _height = get_size(line, style)
        yield width


def show_first_line(context, pango_layout, hinting):
    """Draw the given ``line`` to the Cairo ``context``."""
    context = ffi.cast('cairo_t *', context._pointer)
    if hinting:
        pangocairo.pango_cairo_update_layout(context, pango_layout.layout)
    # Set an infinite width as we don't want to break lines when drawing, the
    # lines have already been split and the size may differ for example because
    # of hinting.
    pango.pango_layout_set_width(pango_layout.layout, -1)
    pangocairo.pango_cairo_show_layout_line(
        context, next(pango_layout.iter_lines()))
