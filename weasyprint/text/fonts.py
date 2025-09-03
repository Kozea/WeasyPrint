"""Interface with external libraries managing fonts installed on the system."""

from hashlib import md5
from io import BytesIO
from locale import getpreferredencoding
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from warnings import warn
from xml.etree.ElementTree import Element, SubElement, tostring

from fontTools.ttLib import TTFont, woff2

from ..logger import LOGGER
from ..urls import fetch

from .constants import (  # isort:skip
    CAPS_KEYS, EAST_ASIAN_KEYS, FONTCONFIG_STRETCH, FONTCONFIG_STYLE, FONTCONFIG_WEIGHT,
    LIGATURE_KEYS, NUMERIC_KEYS, PANGO_STRETCH, PANGO_STYLE, PANGO_VARIANT)
from .ffi import (  # isort:skip
    FROM_UNITS, TO_UNITS, ffi, fontconfig, gobject, harfbuzz, pango, pangoft2,
    unicode_to_char_p)

PREFERRED_ENCODING = getpreferredencoding(False)


def _check_font_configuration(font_config):  # pragma: no cover
    """Check whether the given font_config has fonts.

    The default fontconfig configuration file may be missing (particularly
    on Windows or macOS, where installation of fontconfig isn't as
    standardized as on Linux), resulting in "Fontconfig error: Cannot load
    default config file".

    Fontconfig tries to retrieve the system fonts as fallback, which may or
    may not work, especially on macOS, where fonts can be installed at
    various loactions. On Windows (at least since fontconfig 2.13) the
    fallback seems to work.

    If there’s no default configuration and the system fonts fallback
    fails, or if the configuration file exists but doesn’t provide fonts,
    output will be ugly.

    If you happen to have no fonts and an HTML document without a valid
    @font-face, all letters turn into rectangles.

    If you happen to have an HTML document with at least one valid
    @font-face, all text is styled with that font.

    On Windows and macOS we can cause Pango to use native font rendering
    instead of rendering fonts with FreeType. But then we must do without
    @font-face. Expect other missing features and ugly output.

    """
    # Having fonts means: fontconfig's config file returns fonts or
    # fontconfig managed to retrieve system fallback-fonts. On Windows the
    # fallback stragegy seems to work since fontconfig >= 2.13.
    fonts = fontconfig.FcConfigGetFonts(font_config, fontconfig.FcSetSystem)
    # Of course, with nfont == 1 the user wont be happy, too…
    if fonts.nfont > 0:
        return

    # Find the reason why we have no fonts.
    config_files = fontconfig.FcConfigGetConfigFiles(font_config)
    config_file = fontconfig.FcStrListNext(config_files)
    if config_file == ffi.NULL:
        warn('FontConfig cannot load default config file. Expect ugly output.')
    else:
        # Useless config file, or indeed no fonts.
        warn('No fonts configured in FontConfig. Expect ugly output.')


_check_font_configuration(ffi.gc(
    fontconfig.FcInitLoadConfigAndFonts(), fontconfig.FcConfigDestroy))


class FontConfiguration:
    """A Fontconfig font configuration.

    Keep a list of fonts, including fonts installed on the system, fonts
    installed for the current user, and fonts referenced by cascading
    stylesheets.

    When created, an instance of this class gathers available fonts. It can
    then be given to :class:`weasyprint.HTML` methods or to
    :class:`weasyprint.CSS` to find fonts in ``@font-face`` rules.

    """
    _folder = None  # required by __del__ when code stops before __init__ finishes

    def __init__(self):
        """Create a Fontconfig font configuration.

        See Behdad's blog:
        https://mces.blogspot.fr/2015/05/how-to-use-custom-application-fonts.html

        """
        # Load the main config file and the fonts.
        self._config = ffi.gc(
            fontconfig.FcInitLoadConfigAndFonts(), fontconfig.FcConfigDestroy)
        self.font_map = ffi.gc(
            pangoft2.pango_ft2_font_map_new(), gobject.g_object_unref)
        pangoft2.pango_fc_font_map_set_config(
            ffi.cast('PangoFcFontMap *', self.font_map), self._config)
        # pango_fc_font_map_set_config keeps a reference to config.
        fontconfig.FcConfigDestroy(self._config)

        # Temporary folder storing fonts.
        self._folder = None

        # Cache.
        self.strut_layouts = {}
        self.font_features = {}

    def add_font_face(self, rule_descriptors, url_fetcher):
        """Add a font face to the Fontconfig configuration."""

        # Define path where to save font, depending on the rule descriptors.
        config_key = str(rule_descriptors)
        config_digest = md5(config_key.encode(), usedforsecurity=False).hexdigest()
        if self._folder is None:
            self._folder = Path(mkdtemp(prefix='weasyprint-'))
        font_path = self._folder / config_digest
        if font_path.exists():
            # Font already exists, we have nothing more to do.
            return

        # Try values in "src" descriptor until one works.
        string = ffi.new('FcChar8 **')
        for font_type, url in rule_descriptors['src']:
            # Abort if font URL is broken.
            if url is None or font_type == 'internal':
                continue

            # Try to find a font installed on the system that matches descriptors.
            if font_type == 'local':
                # Create a pattern that matches font name.
                font_name = url.encode()
                pattern = ffi.gc(
                    fontconfig.FcPatternCreate(), fontconfig.FcPatternDestroy)
                fontconfig.FcConfigSubstitute(
                    self._config, pattern, fontconfig.FcMatchFont)
                fontconfig.FcDefaultSubstitute(pattern)
                fontconfig.FcPatternAddString(pattern, b'fullname', font_name)
                fontconfig.FcPatternAddString(pattern, b'postscriptname', font_name)
                result = ffi.new('FcResult *')
                matching_pattern = fontconfig.FcFontMatch(self._config, pattern, result)
                if matching_pattern == ffi.NULL:
                    # No font has been found, abort.
                    LOGGER.debug('Failed to get matching local font for %r', url)
                    continue

                # Check that the font name in descriptor matches name in font.
                for tag in b'fullname', b'postscriptname':
                    fontconfig.FcPatternGetString(matching_pattern, tag, 0, string)
                    name = ffi.string(string[0])
                    if font_name.lower() == name.lower():
                        fontconfig.FcPatternGetString(
                            matching_pattern, b'file', 0, string)
                        path = ffi.string(string[0]).decode(PREFERRED_ENCODING)
                        url = Path(path).as_uri()
                        break
                else:
                    # Names don’t match, abort.
                    LOGGER.debug('Failed to load local font %r', font_name.decode())
                    continue

            # Get font content.
            try:
                with fetch(url_fetcher, url) as result:
                    string = 'string' in result
                    font = result['string'] if string else result['file_obj'].read()
            except Exception as exception:
                LOGGER.debug('Failed to load font at %r (%s)', url, exception)
                continue

            # Store font content.
            try:
                # Decode woff and woff2 fonts.
                if font[:3] == b'wOF':
                    out = BytesIO()
                    woff_version_byte = font[3:4]
                    if woff_version_byte == b'F':  # woff font
                        ttfont = TTFont(BytesIO(font))
                        ttfont.flavor = ttfont.flavorData = None
                        ttfont.save(out)
                    elif woff_version_byte == b'2':  # woff2 font
                        woff2.decompress(BytesIO(font), out)
                    font = out.getvalue()
            except Exception as exc:
                LOGGER.debug('Failed to handle woff font at %r (%s)', url, exc)
                continue
            font_path.write_bytes(font)

            # Create Fontconfig XML config file.
            mode = 'assign_replace'
            root = Element('fontconfig')
            match = SubElement(root, 'match', target='scan')
            test = SubElement(match, 'test', name='file', compare='eq')
            SubElement(test, 'string').text = str(font_path)
            # Prepend, as replacing the font family breaks Pango, see #2510.
            edit = SubElement(match, 'edit', name='family', mode='prepend')
            SubElement(edit, 'string').text = rule_descriptors['font_family']
            if 'font_style' in rule_descriptors:
                edit = SubElement(match, 'edit', name='slant', mode=mode)
                text = FONTCONFIG_STYLE[rule_descriptors['font_style']]
                SubElement(edit, 'const').text = text
            if 'font_weight' in rule_descriptors:
                edit = SubElement(match, 'edit', name='weight', mode=mode)
                integer = FONTCONFIG_WEIGHT[rule_descriptors['font_weight']]
                SubElement(edit, 'int').text = str(integer)
            if 'font_stretch' in rule_descriptors:
                edit = SubElement(match, 'edit', name='width', mode=mode)
                text = FONTCONFIG_STRETCH[rule_descriptors['font_stretch']]
                SubElement(edit, 'const').text = text
            match = SubElement(root, 'match', target='font')
            test = SubElement(match, 'test', name='file', compare='eq')
            SubElement(test, 'string').text = str(font_path)
            descriptors = {
                rules[0][0].replace('-', '_'): rules[0][1] for rules in
                rule_descriptors.get('font_variant', [])}
            settings = rule_descriptors.get('font_feature_settings', 'normal')
            features = font_features(font_feature_settings=settings, **descriptors)
            if features:
                edit = SubElement(match, 'edit', name='fontfeatures', mode=mode)
                for key, value in features.items():
                    SubElement(edit, 'string').text = f'{key} {value}'
            if unicode_ranges := rule_descriptors.get('unicode_range'):
                edit = SubElement(match, 'edit', name='charset', mode=mode)
                plus = SubElement(edit, 'plus')
                for unicode_range in unicode_ranges:
                    charset = SubElement(plus, 'charset')
                    range_ = SubElement(charset, 'range')
                    for value in (unicode_range.start, unicode_range.end):
                        SubElement(range_, 'int').text = f'0x{value:x}'
            header = (
                b'<?xml version="1.0"?>',
                b'<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">')
            xml = b'\n'.join((*header, tostring(root, encoding='utf-8')))

            # Register font and configuration in Fontconfig.
            # TODO: We should mask local fonts with the same name
            # too as explained in Behdad's blog entry.
            fontconfig.FcConfigParseAndLoadFromMemory(self._config, xml, True)
            font_added = fontconfig.FcConfigAppFontAddFile(
                self._config, str(font_path).encode(PREFERRED_ENCODING))
            if font_added:
                return pangoft2.pango_fc_font_map_config_changed(
                    ffi.cast('PangoFcFontMap *', self.font_map))
            LOGGER.debug('Failed to load font at %r', url)
        LOGGER.warning('Font-face %r cannot be loaded', rule_descriptors['font_family'])

    def __del__(self):
        """Clean a font configuration for a document."""
        if self._folder:
            rmtree(self._folder, ignore_errors=True)


def font_features(font_kerning='normal', font_variant_ligatures='normal',
                  font_variant_position='normal', font_variant_caps='normal',
                  font_variant_numeric='normal', font_variant_alternates='normal',
                  font_variant_east_asian='normal', font_feature_settings='normal'):
    """Get the font features from the different properties in style.

    See https://www.w3.org/TR/css-fonts-3/#feature-precedence

    """
    features = {}

    # Step 1: getting the default, we rely on Pango for this.
    # Step 2: @font-face font-variant, done in fonts.add_font_face.
    # Step 3: @font-face font-feature-settings, done in fonts.add_font_face.

    # Step 4: font-variant and OpenType features.

    if font_kerning != 'auto':
        features['kern'] = int(font_kerning == 'normal')

    if font_variant_ligatures == 'none':
        for keys in LIGATURE_KEYS.values():
            for key in keys:
                features[key] = 0
    elif font_variant_ligatures != 'normal':
        for ligature_type in font_variant_ligatures:
            value = 1
            if ligature_type.startswith('no-'):
                value = 0
                ligature_type = ligature_type[3:]
            for key in LIGATURE_KEYS[ligature_type]:
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
        for key in CAPS_KEYS[font_variant_caps]:
            features[key] = 1

    if font_variant_numeric != 'normal':
        for key in font_variant_numeric:
            features[NUMERIC_KEYS[key]] = 1

    if font_variant_alternates != 'normal':
        # TODO: support other values
        # See https://drafts.csswg.org/css-fonts/#font-variant-alternates-prop
        if font_variant_alternates == 'historical-forms':
            features['hist'] = 1

    if font_variant_east_asian != 'normal':
        for key in font_variant_east_asian:
            features[EAST_ASIAN_KEYS[key]] = 1

    # Step 5: incompatible non-OpenType features, already handled by Pango.

    # Step 6: font-feature-settings.

    if font_feature_settings != 'normal':
        features.update(dict(font_feature_settings))

    return features


def get_font_description(style):
    """Get font description string out of given style."""
    font_description = ffi.gc(
        pango.pango_font_description_new(), pango.pango_font_description_free)
    family_p, family = unicode_to_char_p(','.join(style['font_family']))
    pango.pango_font_description_set_family(font_description, family_p)
    font_style = PANGO_STYLE[style['font_style']]
    pango.pango_font_description_set_style(font_description, font_style)
    font_stretch = PANGO_STRETCH[style['font_stretch']]
    pango.pango_font_description_set_stretch(font_description, font_stretch)
    font_weight = style['font_weight']
    pango.pango_font_description_set_weight(font_description, font_weight)
    font_size = int(style['font_size'] * TO_UNITS)
    pango.pango_font_description_set_absolute_size(font_description, font_size)
    font_variant = PANGO_VARIANT[style['font_variant_caps']]
    pango.pango_font_description_set_variant(font_description, font_variant)
    if style['font_variation_settings'] != 'normal':
        string = ','.join(
            f'{key}={value}' for key, value in
            style['font_variation_settings']).encode()
        pango.pango_font_description_set_variations(font_description, string)
    return font_description


def get_pango_font_hb_face(pango_font):
    """Get Harfbuzz face out of given Pango font."""
    fc_font = ffi.cast('PangoFcFont *', pango_font)
    fontmap = ffi.cast('PangoFcFontMap *', pango.pango_font_get_font_map(pango_font))
    return pangoft2.pango_fc_font_map_get_hb_face(fontmap, fc_font)


def get_hb_object_data(hb_object, ot_color=None, glyph=None):
    """Get binary data out of given Harfbuzz font or face.

    If ``ot_color`` is 'svg', return the SVG color glyph reference. If it’s 'png',
    return the PNG color glyph reference. Otherwise, return the whole face blob.

    """
    if ot_color == 'png':
        hb_blob = harfbuzz.hb_ot_color_glyph_reference_png(hb_object, glyph)
    elif ot_color == 'svg':
        hb_blob = harfbuzz.hb_ot_color_glyph_reference_svg(hb_object, glyph)
    else:
        hb_blob = harfbuzz.hb_face_reference_blob(hb_object)
    with ffi.new('unsigned int *') as length:
        hb_data = harfbuzz.hb_blob_get_data(hb_blob, length)
        data = None if hb_data == ffi.NULL else ffi.unpack(hb_data, int(length[0]))
        harfbuzz.hb_blob_destroy(hb_blob)
        return data


def get_pango_font_key(pango_font):
    """Get key corresponding to given Pango font."""
    # TODO: This value is stable for a given Pango font in a given Pango map, but can’t
    # be cached with just the Pango font as a key because two Pango fonts could point to
    # the same address for two different Pango maps. We should cache it in the
    # FontConfiguration object. See issue #2144.
    description = ffi.gc(
        pango.pango_font_describe(pango_font), pango.pango_font_description_free)
    font_size = pango.pango_font_description_get_size(description) * FROM_UNITS
    mask = pango.PANGO_FONT_MASK_SIZE + pango.PANGO_FONT_MASK_GRAVITY
    pango.pango_font_description_unset_fields(description, mask)
    return pango.pango_font_description_hash(description), description, font_size
