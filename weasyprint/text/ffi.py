"""Imports of dynamic libraries used for text layout."""

import os

import cffi

ffi = cffi.FFI()
ffi.cdef('''
    // HarfBuzz

    typedef ... hb_blob_t;
    typedef int hb_bool_t;
    typedef ... hb_buffer_t;
    typedef uint32_t hb_codepoint_t;
    typedef ... hb_face_t;
    typedef ... hb_font_t;
    typedef uint32_t hb_mask_t;
    typedef int32_t hb_position_t;
    typedef uint32_t hb_tag_t;

    typedef union _hb_var_int_t {
        uint32_t u32;
        int32_t i32;
        uint16_t u16[2];
        int16_t i16[2];
        uint8_t u8[4];
        int8_t i8[4];
    } hb_var_int_t;

    typedef enum {
        HB_BUFFER_CLUSTER_LEVEL_MONOTONE_GRAPHEMES  = 0,
        HB_BUFFER_CLUSTER_LEVEL_MONOTONE_CHARACTERS = 1,
        HB_BUFFER_CLUSTER_LEVEL_CHARACTERS          = 2,
        HB_BUFFER_CLUSTER_LEVEL_DEFAULT = HB_BUFFER_CLUSTER_LEVEL_MONOTONE_GRAPHEMES
    } hb_buffer_cluster_level_t;

    typedef enum {
        HB_BUFFER_CONTENT_TYPE_INVALID = 0,
        HB_BUFFER_CONTENT_TYPE_UNICODE,
        HB_BUFFER_CONTENT_TYPE_GLYPHS
    } hb_buffer_content_type_t;

    typedef enum { /*< flags >*/
        HB_BUFFER_FLAG_DEFAULT                      = 0x00000000u,
        HB_BUFFER_FLAG_BOT                          = 0x00000001u,
        HB_BUFFER_FLAG_EOT                          = 0x00000002u,
        HB_BUFFER_FLAG_PRESERVE_DEFAULT_IGNORABLES  = 0x00000004u,
        HB_BUFFER_FLAG_REMOVE_DEFAULT_IGNORABLES    = 0x00000008u,
        HB_BUFFER_FLAG_DO_NOT_INSERT_DOTTED_CIRCLE  = 0x00000010u,
        HB_BUFFER_FLAG_VERIFY                       = 0x00000020u,
        HB_BUFFER_FLAG_PRODUCE_UNSAFE_TO_CONCAT     = 0x00000040u,
        HB_BUFFER_FLAG_DEFINED                      = 0x0000007Fu
    } hb_buffer_flags_t;

    typedef enum {
        HB_BUFFER_SERIALIZE_FORMAT_TEXT,
        HB_BUFFER_SERIALIZE_FORMAT_JSON,
        HB_BUFFER_SERIALIZE_FORMAT_INVALID
    } hb_buffer_serialize_format_t;

    typedef enum {
        HB_BUFFER_SERIALIZE_FLAG_DEFAULT        = 0x00000000u,
        HB_BUFFER_SERIALIZE_FLAG_NO_CLUSTERS    = 0x00000001u,
        HB_BUFFER_SERIALIZE_FLAG_NO_POSITIONS   = 0x00000002u,
        HB_BUFFER_SERIALIZE_FLAG_NO_GLYPH_NAMES = 0x00000004u,
        HB_BUFFER_SERIALIZE_FLAG_GLYPH_EXTENTS  = 0x00000008u,
        HB_BUFFER_SERIALIZE_FLAG_GLYPH_FLAGS    = 0x00000010u,
        HB_BUFFER_SERIALIZE_FLAG_NO_ADVANCES    = 0x00000020u,
        HB_BUFFER_SERIALIZE_FLAG_DEFINED        = 0x0000003Fu
    } hb_buffer_serialize_flags_t;

    typedef enum {
        HB_DIRECTION_INVALID = 0,
        HB_DIRECTION_LTR = 4,
        HB_DIRECTION_RTL,
        HB_DIRECTION_TTB,
        HB_DIRECTION_BTT
    } hb_direction_t;

    typedef enum {
        HB_OT_LAYOUT_BASELINE_TAG_ROMAN                     = 0x726f6d6eu,
        HB_OT_LAYOUT_BASELINE_TAG_HANGING                   = 0x68616e67u,
        HB_OT_LAYOUT_BASELINE_TAG_IDEO_FACE_BOTTOM_OR_LEFT  = 0x69636662u,
        HB_OT_LAYOUT_BASELINE_TAG_IDEO_FACE_TOP_OR_RIGHT    = 0x69636674u,
        HB_OT_LAYOUT_BASELINE_TAG_IDEO_FACE_CENTRAL         = 0x49636663u,
        HB_OT_LAYOUT_BASELINE_TAG_IDEO_EMBOX_BOTTOM_OR_LEFT = 0x6964656fu,
        HB_OT_LAYOUT_BASELINE_TAG_IDEO_EMBOX_TOP_OR_RIGHT   = 0x69647470u,
        HB_OT_LAYOUT_BASELINE_TAG_IDEO_EMBOX_CENTRAL        = 0x49646365u,
        HB_OT_LAYOUT_BASELINE_TAG_MATH                      = 0x6d617468u
    } hb_ot_layout_baseline_tag_t;

    typedef struct {
        hb_tag_t      tag;
        uint32_t      value;
        unsigned int  start;
        unsigned int  end;
    } hb_feature_t;

    typedef struct {
        hb_position_t ascender;
        hb_position_t descender;
        hb_position_t line_gap;
        /*< private >*/
        hb_position_t reserved9;
        hb_position_t reserved8;
        hb_position_t reserved7;
        hb_position_t reserved6;
        hb_position_t reserved5;
        hb_position_t reserved4;
        hb_position_t reserved3;
        hb_position_t reserved2;
        hb_position_t reserved1;
    } hb_font_extents_t;

    typedef struct {
        hb_position_t x_bearing;
        hb_position_t y_bearing;
        hb_position_t width;
        hb_position_t height;
    } hb_glyph_extents_t;

    typedef enum {
        HB_GLYPH_FLAG_UNSAFE_TO_BREAK   = 0x00000001,
        HB_GLYPH_FLAG_UNSAFE_TO_CONCAT  = 0x00000002,
        HB_GLYPH_FLAG_DEFINED           = 0x00000003
    } hb_glyph_flags_t;

    typedef struct hb_glyph_info_t {
        hb_codepoint_t codepoint;
        /*< private >*/
        hb_mask_t      mask;
        /*< public >*/
        uint32_t       cluster;

        /*< private >*/
        hb_var_int_t   var1;
        hb_var_int_t   var2;
    } hb_glyph_info_t;

    typedef struct {
        hb_position_t  x_advance;
        hb_position_t  y_advance;
        hb_position_t  x_offset;
        hb_position_t  y_offset;
        /*< private >*/
        hb_var_int_t   var;
    } hb_glyph_position_t;

    hb_buffer_t * hb_buffer_create (void);
    void hb_buffer_destroy (hb_buffer_t *buffer);
    void hb_buffer_add (
        hb_buffer_t *buffer, hb_codepoint_t codepoint, unsigned int cluster);
    void hb_buffer_append (
        hb_buffer_t *buffer, const hb_buffer_t *source, unsigned int start,
        unsigned int end);
    hb_glyph_info_t * hb_buffer_get_glyph_infos (
        hb_buffer_t *buffer, unsigned int *length);
    hb_glyph_position_t * hb_buffer_get_glyph_positions (
        hb_buffer_t *buffer, unsigned int *length);
    unsigned int hb_buffer_get_length (const hb_buffer_t *buffer);
    hb_bool_t hb_buffer_pre_allocate (
        hb_buffer_t *buffer, unsigned int size);
    unsigned int hb_buffer_serialize (
        hb_buffer_t *buffer, unsigned int start, unsigned int end, char *buf,
        unsigned int buf_size, unsigned int *buf_consumed, hb_font_t *font,
        hb_buffer_serialize_format_t format,
        hb_buffer_serialize_flags_t flags);
    hb_buffer_serialize_format_t hb_buffer_serialize_format_from_string(
        const char *str, int len);
    void hb_buffer_set_cluster_level (
        hb_buffer_t *buffer, hb_buffer_cluster_level_t cluster_level);
    void hb_buffer_set_content_type (
        hb_buffer_t *buffer, hb_buffer_content_type_t content_type);
    void hb_buffer_set_direction (
        hb_buffer_t *buffer, hb_direction_t direction);
    void hb_buffer_set_flags (
        hb_buffer_t *buffer, hb_buffer_flags_t flags);

    void hb_shape (
        hb_font_t *font, hb_buffer_t *buffer, const hb_feature_t *features,
        unsigned int num_features);

    void hb_font_get_extents_for_direction (
        hb_font_t *font, hb_direction_t direction, hb_font_extents_t *extents);
    hb_face_t * hb_font_get_face (hb_font_t *font);
    hb_bool_t hb_font_get_glyph_extents (
        hb_font_t *font, hb_codepoint_t glyph, hb_glyph_extents_t *extents);
    void hb_font_get_ppem (
        hb_font_t *font, unsigned int *x_ppem, unsigned int *y_ppem);
    float hb_font_get_ptem (hb_font_t *font);
    void hb_font_get_scale (hb_font_t *font, int *x_scale, int *y_scale);

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
    typedef ... PangoAttrIterator;
    typedef ... PangoAttrList;
    typedef ... PangoAttrClass;
    typedef ... PangoFont;
    typedef guint PangoGlyph;
    typedef gint PangoGlyphUnit;

    const guint PANGO_GLYPH_EMPTY = 0x0FFFFFFF;
    const guint PANGO_GLYPH_UNKNOWN_FLAG = 0x10000000;

    typedef enum {
        PANGO_DIRECTION_LTR,
        PANGO_DIRECTION_RTL,
        PANGO_DIRECTION_TTB_LTR, // Deprecated, use _RTL
        PANGO_DIRECTION_TTB_RTL, // Deprecated, use _LTR
        PANGO_DIRECTION_WEAK_LTR,
        PANGO_DIRECTION_WEAK_RTL,
        PANGO_DIRECTION_NEUTRAL
    } PangoDirection;

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

    typedef enum {
        PANGO_ELLIPSIZE_NONE,
        PANGO_ELLIPSIZE_START,
        PANGO_ELLIPSIZE_MIDDLE,
        PANGO_ELLIPSIZE_END
    } PangoEllipsizeMode;

    typedef struct GList {
        gpointer data;
        struct GList* next;
        struct GList* prev;
    } GList;

    typedef struct GSList {
       gpointer data;
       struct GSList *next;
    } GSList;

    typedef struct {
        const PangoAttrClass *klass;
        guint start_index;
        guint end_index;
    } PangoAttribute;

    typedef struct {
        PangoLayout *layout;
        gint         start_index;
        gint         length;
        GSList      *runs;
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
    PangoStyle pango_font_description_get_style (
        const PangoFontDescription *desc);
    void pango_font_description_set_stretch (
        PangoFontDescription *desc, PangoStretch stretch);
    void pango_font_description_set_weight (
        PangoFontDescription *desc, PangoWeight weight);
    void pango_font_description_set_absolute_size (
        PangoFontDescription *desc, double size);
    int pango_font_description_get_size (PangoFontDescription *desc);

    int pango_glyph_string_get_width (PangoGlyphString *glyphs);
    char * pango_font_description_to_string (
        const PangoFontDescription *desc);

    PangoFontDescription * pango_font_describe (PangoFont *font);
    const char * pango_font_description_get_family (
        const PangoFontDescription *desc);
    int pango_font_description_hash (const PangoFontDescription *desc);

    PangoContext * pango_context_new ();
    PangoContext * pango_font_map_create_context (PangoFontMap *fontmap);

    PangoFontMetrics * pango_context_get_metrics (
        PangoContext *context, const PangoFontDescription *desc,
        PangoLanguage *language);
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

    void pango_context_set_round_glyph_positions (
        PangoContext *context, gboolean round_positions);

    PangoFontMetrics * pango_font_get_metrics (
        PangoFont *font, PangoLanguage *language);

    void pango_font_get_glyph_extents (
        PangoFont *font, PangoGlyph glyph, PangoRectangle *ink_rect,
        PangoRectangle *logical_rect);

    PangoAttrList * pango_attr_list_new (void);
    void pango_attr_list_unref (PangoAttrList *list);
    void pango_attr_list_insert (
        PangoAttrList *list, PangoAttribute *attr);
    void pango_attr_list_change (
        PangoAttrList *list, PangoAttribute *attr);
    PangoAttribute * pango_attr_font_desc_new (
        const PangoFontDescription *desc);
    PangoAttribute * pango_attr_font_features_new (const gchar *features);
    PangoAttribute * pango_attr_letter_spacing_new (int letter_spacing);
    PangoAttribute * pango_attr_insert_hyphens_new (gboolean insert_hyphens);
    void pango_attribute_destroy (PangoAttribute *attr);

    PangoGlyphString * pango_glyph_string_new ();
    void pango_glyph_string_free (PangoGlyphString * string);
    void pango_glyph_string_extents_range (
        PangoGlyphString * glyphs, int start, int end, PangoFont* font,
        PangoRectangle * ink_rect, PangoRectangle * logical_rect);
    void pango_glyph_string_get_logical_widths (
        PangoGlyphString * glyphs, const char * text, int length,
        int embedding_level, int * logical_widths);

    GList * pango_itemize_with_base_dir (
        PangoContext *context, PangoDirection base_dir,
        const char *text, int start_index, int length,
        PangoAttrList *attrs, PangoAttrIterator *cached_iter);

    void pango_shape_full (
        const char * item_text, int item_length,
        const char * paragraph_text, int paragraph_length,
        const PangoAnalysis * analysis, PangoGlyphString * glyphs);

    void pango_default_break (
        const char * text, int length, PangoAnalysis * analysis,
        PangoLogAttr * attrs, int attrs_len);

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
        try:
            return ffi.dlopen(name)
        except OSError:
            pass
    # Re-raise the exception.
    return ffi.dlopen(names[0])  # pragma: no cover


if hasattr(os, 'add_dll_directory'):  # pragma: no cover
    dll_directories = os.getenv(
        'WEASYPRINT_DLL_DIRECTORIES',
        'C:\\Program Files\\GTK3-Runtime Win64\\bin').split(';')
    for dll_directory in dll_directories:
        try:
            os.add_dll_directory(dll_directory)
        except (OSError, FileNotFoundError):
            pass

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
    ffi, 'fontconfig-1', 'fontconfig', 'libfontconfig', 'libfontconfig.so.1',
    'libfontconfig-1.dylib', 'libfontconfig-1.dll')
pangoft2 = _dlopen(
    ffi, 'pangoft2-1.0-0', 'pangoft2-1.0', 'libpangoft2-1.0-0',
    'libpangoft2-1.0.so.0', 'libpangoft2-1.0.dylib', 'libpangoft2-1.0-0.dll')

gobject.g_type_init()

units_to_double = pango.pango_units_to_double
units_from_double = pango.pango_units_from_double
PANGO_SCALE = pango.pango_units_from_double(1.0)


def unicode_to_char_p(string):
    """Return ``(pointer, bytestring)``.

    The byte string must live at least as long as the pointer is used.

    """
    bytestring = string.encode().replace(b'\x00', b'')
    return ffi.new('char[]', bytestring), bytestring


def glist_to_list(glist, obj_type):
    """Return a Python list from ``glist`` casted to ``type``."""
    # Get to the head of the list if we're not there yet.
    while glist.prev != ffi.NULL:
        glist = glist.prev

    obj_list = [ffi.cast(obj_type, glist.data)]
    while glist.next != ffi.NULL:
        glist = glist.next
        obj_list.append(ffi.cast(obj_type, glist.data))

    return obj_list
