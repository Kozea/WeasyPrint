"""Imports of dynamic libraries used for text layout."""

import os
from contextlib import suppress

import cffi

ffi = cffi.FFI()
ffi.cdef('''
    // HarfBuzz

    typedef ... hb_font_t;
    typedef ... hb_face_t;
    typedef ... hb_blob_t;
    typedef uint32_t hb_codepoint_t;
    hb_face_t * hb_font_get_face (hb_font_t *font);
    hb_blob_t * hb_face_reference_blob (hb_face_t *face);
    unsigned int hb_face_get_index (const hb_face_t *face);
    unsigned int hb_face_get_upem (const hb_face_t *face);
    const char * hb_blob_get_data (hb_blob_t *blob, unsigned int *length);
    bool hb_ot_color_has_png (hb_face_t *face);
    hb_blob_t * hb_ot_color_glyph_reference_png (
        hb_font_t *font, hb_codepoint_t glyph);
    bool hb_ot_color_has_svg (hb_face_t *face);
    hb_blob_t * hb_ot_color_glyph_reference_svg (
        hb_face_t *face, hb_codepoint_t glyph);
    void hb_blob_destroy (hb_blob_t *blob);


    // Pango

    typedef unsigned int guint;
    typedef int gint;
    typedef char gchar;
    typedef gint gboolean;
    typedef void* gpointer;
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
    typedef ... PangoFont;
    typedef guint PangoGlyph;
    typedef gint PangoGlyphUnit;

    const guint PANGO_GLYPH_EMPTY = 0x0FFFFFFF;
    const guint PANGO_GLYPH_UNKNOWN_FLAG = 0x10000000;

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
        PANGO_FONT_MASK_SIZE = 1 << 5,
        PANGO_FONT_MASK_GRAVITY = 1 << 6,
        PANGO_FONT_MASK_VARIATIONS = 1 << 7
    } PangoFontMask;

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

    typedef enum {
        PANGO_ELLIPSIZE_NONE,
        PANGO_ELLIPSIZE_START,
        PANGO_ELLIPSIZE_MIDDLE,
        PANGO_ELLIPSIZE_END
    } PangoEllipsizeMode;

    typedef struct GSList {
       gpointer data;
       struct GSList *next;
    } GSList;

    typedef struct {
        void *shape_engine;
        void *lang_engine;
        PangoFont *font;
        guint level;
        guint gravity;
        guint flags;
        guint script;
        PangoLanguage *language;
        GSList *extra_attrs;
    } PangoAnalysis;

    typedef struct {
        gint offset;
        gint length;
        gint num_chars;
        PangoAnalysis analysis;
    } PangoItem;

    typedef struct {
        PangoGlyphUnit width;
        PangoGlyphUnit x_offset;
        PangoGlyphUnit y_offset;
    } PangoGlyphGeometry;

    typedef struct {
        guint is_cluster_start : 1;
    } PangoGlyphVisAttr;

    typedef struct {
        PangoGlyph         glyph;
        PangoGlyphGeometry geometry;
        PangoGlyphVisAttr  attr;
    } PangoGlyphInfo;

    typedef struct {
        gint num_glyphs;
        PangoGlyphInfo *glyphs;
        gint *log_clusters;
    } PangoGlyphString;

    typedef struct {
        PangoItem        *item;
        PangoGlyphString *glyphs;
    } PangoGlyphItem;

    typedef struct GSListRuns {
       PangoGlyphItem    *data;
       struct GSListRuns *next;
    } GSListRuns;

    typedef struct {
        const PangoAttrClass *klass;
        guint start_index;
        guint end_index;
    } PangoAttribute;

    typedef struct {
        PangoLayout *layout;
        gint         start_index;
        gint         length;
        GSListRuns  *runs;
        guint        is_paragraph_start : 1;
        guint        resolved_dir : 3;
    } PangoLayoutLine;

    typedef struct  {
        int x;
        int y;
        int width;
        int height;
    } PangoRectangle;

    typedef struct {
        guint is_line_break: 1;
        guint is_mandatory_break : 1;
        guint is_char_break : 1;
        guint is_white : 1;
        guint is_cursor_position : 1;
        guint is_word_start : 1;
        guint is_word_end : 1;
        guint is_sentence_boundary : 1;
        guint is_sentence_start : 1;
        guint is_sentence_end : 1;
        guint backspace_deletes_character : 1;
        guint is_expandable_space : 1;
        guint is_word_boundary : 1;
    } PangoLogAttr;

    int pango_version (void);

    double pango_units_to_double (int i);
    int pango_units_from_double (double d);
    void g_object_unref (gpointer object);
    void g_type_init (void);

    PangoLayout * pango_layout_new (PangoContext *context);
    void pango_layout_set_width (PangoLayout *layout, int width);
    PangoAttrList * pango_layout_get_attributes(PangoLayout *layout);
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
    void pango_layout_set_single_paragraph_mode (
        PangoLayout *layout, gboolean setting);
    int pango_layout_get_baseline (PangoLayout *layout);
    PangoLayoutLine * pango_layout_get_line_readonly (
        PangoLayout *layout, int line);

    hb_font_t * pango_font_get_hb_font (PangoFont *font);

    PangoFontDescription * pango_font_description_new (void);
    void pango_font_description_free (PangoFontDescription *desc);
    PangoFontDescription * pango_font_description_copy (
        const PangoFontDescription *desc);

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
    void pango_font_description_set_variations (
        PangoFontDescription* desc, const char* variations);

    PangoStyle pango_font_description_get_style (
        const PangoFontDescription *desc);
    const char* pango_font_description_get_variations (
        const PangoFontDescription* desc);
    PangoWeight pango_font_description_get_weight (
        const PangoFontDescription* desc);
    int pango_font_description_get_size (PangoFontDescription *desc);

    void pango_font_description_unset_fields (
        PangoFontDescription* desc, PangoFontMask to_unset);

    int pango_glyph_string_get_width (PangoGlyphString *glyphs);
    char * pango_font_description_to_string (
        const PangoFontDescription *desc);

    PangoFontDescription * pango_font_describe (PangoFont *font);
    const char * pango_font_description_get_family (
        const PangoFontDescription *desc);
    guint pango_font_description_hash (const PangoFontDescription *desc);

    PangoContext * pango_context_new ();
    PangoContext * pango_font_map_create_context (PangoFontMap *fontmap);

    PangoFont* pango_font_map_load_font (
        PangoFontMap* fontmap, PangoContext* context,
        const PangoFontDescription* desc);

    PangoFontMetrics * pango_context_get_metrics (
        PangoContext *context, const PangoFontDescription *desc,
        PangoLanguage *language);
    PangoFontMetrics * pango_font_get_metrics (
        PangoFont *font, PangoLanguage *language);
    void pango_font_metrics_unref (PangoFontMetrics *metrics);
    int pango_font_metrics_get_ascent (PangoFontMetrics *metrics);
    int pango_font_metrics_get_descent (PangoFontMetrics *metrics);
    int pango_font_metrics_get_underline_thickness (
        PangoFontMetrics *metrics);
    int pango_font_metrics_get_underline_position (
        PangoFontMetrics *metrics);
    int pango_font_metrics_get_strikethrough_thickness (
        PangoFontMetrics *metrics);
    int pango_font_metrics_get_strikethrough_position (
        PangoFontMetrics *metrics);
    void pango_font_get_glyph_extents (
        PangoFont *font, PangoGlyph glyph, PangoRectangle *ink_rect,
        PangoRectangle *logical_rect);

    void pango_context_set_round_glyph_positions (
        PangoContext *context, gboolean round_positions);

    PangoAttrList * pango_attr_list_new (void);
    void pango_attr_list_unref (PangoAttrList *list);
    void pango_attr_list_insert (
        PangoAttrList *list, PangoAttribute *attr);
    void pango_attr_list_change (
        PangoAttrList *list, PangoAttribute *attr);
    PangoAttribute * pango_attr_font_features_new (const gchar *features);
    PangoAttribute * pango_attr_letter_spacing_new (int letter_spacing);
    PangoAttribute * pango_attr_insert_hyphens_new (gboolean insert_hyphens);
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
    void pango_layout_set_ellipsize (
        PangoLayout *layout,
        PangoEllipsizeMode ellipsize);

    void pango_get_log_attrs (
        const char *text, int length, int level, PangoLanguage *language,
        PangoLogAttr *log_attrs, int attrs_len);


    // FontConfig

    typedef int FcBool;
    typedef struct _FcConfig FcConfig;
    typedef struct _FcPattern FcPattern;
    typedef struct _FcStrList FcStrList;
    typedef unsigned char FcChar8;

    typedef enum {
        FcResultMatch, FcResultNoMatch, FcResultTypeMismatch, FcResultNoId,
        FcResultOutOfMemory
    } FcResult;

    typedef enum {
        FcMatchPattern, FcMatchFont, FcMatchScan
    } FcMatchKind;

    typedef struct _FcFontSet {
        int nfont;
        int sfont;
        FcPattern **fonts;
    } FcFontSet;

    typedef enum _FcSetName {
        FcSetSystem = 0,
        FcSetApplication = 1
    } FcSetName;

    FcConfig * FcInitLoadConfigAndFonts (void);
    void FcConfigDestroy (FcConfig *config);
    FcBool FcConfigAppFontAddFile (
        FcConfig *config, const FcChar8 *file);
    FcConfig * FcConfigGetCurrent (void);
    FcBool FcConfigSetCurrent (FcConfig *config);
    FcBool FcConfigParseAndLoad (
        FcConfig *config, const FcChar8 *file, FcBool complain);

    FcFontSet * FcConfigGetFonts(FcConfig *config, FcSetName set);
    FcStrList * FcConfigGetConfigFiles(FcConfig *config);
    FcChar8 * FcStrListNext(FcStrList *list);

    void FcDefaultSubstitute (FcPattern *pattern);
    FcBool FcConfigSubstitute (
        FcConfig *config, FcPattern *p, FcMatchKind kind);

    FcPattern * FcPatternCreate (void);
    FcPattern * FcPatternDestroy (FcPattern *p);
    FcBool FcPatternAddString (
        FcPattern *p, const char *object, const FcChar8 *s);
    FcResult FcPatternGetString (
        FcPattern *p, const char *object, int n, FcChar8 **s);
    FcPattern * FcFontMatch (
        FcConfig *config, FcPattern *p, FcResult *result);


    // PangoFT2

    typedef ... PangoFcFontMap;

    PangoFontMap * pango_ft2_font_map_new (void);
    void pango_fc_font_map_set_config (
        PangoFcFontMap *fcfontmap, FcConfig *fcconfig);
    void pango_fc_font_map_config_changed (PangoFcFontMap *fcfontmap);
''')


def _dlopen(ffi, *names):
    """Try various names for the same library, for different platforms."""
    for name in names:
        with suppress(OSError):
            return ffi.dlopen(name)
    # Re-raise the exception.
    print(
        '\n-----\n\n'
        'WeasyPrint could not import some external libraries. Please '
        'carefully follow the installation steps before reporting an issue:\n'
        'https://doc.courtbouillon.org/weasyprint/stable/'
        'first_steps.html#installation\n'
        'https://doc.courtbouillon.org/weasyprint/stable/'
        'first_steps.html#troubleshooting',
        '\n\n-----\n')  # pragma: no cover
    return ffi.dlopen(names[0])  # pragma: no cover


if hasattr(os, 'add_dll_directory'):  # pragma: no cover
    dll_directories = os.getenv(
        'WEASYPRINT_DLL_DIRECTORIES',
        'C:\\Program Files\\GTK3-Runtime Win64\\bin').split(';')
    for dll_directory in dll_directories:
        with suppress((OSError, FileNotFoundError)):
            os.add_dll_directory(dll_directory)

gobject = _dlopen(
    ffi, 'gobject-2.0-0', 'gobject-2.0', 'libgobject-2.0-0',
    'libgobject-2.0.so.0', 'libgobject-2.0.dylib',  'libgobject-2.0-0.dll')
pango = _dlopen(
    ffi, 'pango-1.0-0', 'pango-1.0', 'libpango-1.0-0', 'libpango-1.0.so.0',
    'libpango-1.0.dylib', 'libpango-1.0-0.dll')
harfbuzz = _dlopen(
    ffi, 'harfbuzz', 'harfbuzz-0.0', 'libharfbuzz-0',
    'libharfbuzz.so.0', 'libharfbuzz.so.0', 'libharfbuzz.0.dylib',
    'libharfbuzz-0.dll')
fontconfig = _dlopen(
    ffi, 'libfontconfig-1.dll', 'fontconfig-1', 'fontconfig', 'libfontconfig',
    'libfontconfig.so.1', 'libfontconfig.1.dylib')
pangoft2 = _dlopen(
    ffi, 'pangoft2-1.0-0', 'pangoft2-1.0', 'libpangoft2-1.0-0',
    'libpangoft2-1.0.so.0', 'libpangoft2-1.0.dylib', 'libpangoft2-1.0-0.dll')

gobject.g_type_init()

units_to_double = pango.pango_units_to_double
units_from_double = pango.pango_units_from_double


def unicode_to_char_p(string):
    """Return ``(pointer, bytestring)``.

    The byte string must live at least as long as the pointer is used.

    """
    bytestring = string.encode().replace(b'\x00', b'')
    return ffi.new('char[]', bytestring), bytestring
