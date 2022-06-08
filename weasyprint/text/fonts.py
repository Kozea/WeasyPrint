"""Interface with external libraries managing fonts installed on the system."""

from hashlib import sha1
from io import BytesIO
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from warnings import warn

from fontTools.ttLib import TTFont, woff2

from ..logger import LOGGER
from ..urls import FILESYSTEM_ENCODING, fetch
from .constants import (
    CAPS_KEYS, EAST_ASIAN_KEYS, FONTCONFIG_STRETCH, FONTCONFIG_STYLE,
    FONTCONFIG_WEIGHT, LIGATURE_KEYS, NUMERIC_KEYS)
from .ffi import ffi, fontconfig, gobject, pangoft2


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
    # fallback stragegy seems to work since fontconfig >= 2.13
    fonts = fontconfig.FcConfigGetFonts(font_config, fontconfig.FcSetSystem)
    # Of course, with nfont == 1 the user wont be happy, too…
    if fonts.nfont > 0:
        return

    # Find the reason why we have no fonts
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
    """A FreeType font configuration.

    Keep a list of fonts, including fonts installed on the system, fonts
    installed for the current user, and fonts referenced by cascading
    stylesheets.

    When created, an instance of this class gathers available fonts. It can
    then be given to :class:`weasyprint.HTML` methods or to
    :class:`weasyprint.CSS` to find fonts in ``@font-face`` rules.

    """

    def __init__(self):
        """Create a FreeType font configuration.

        See Behdad's blog:
        https://mces.blogspot.fr/2015/05/
                how-to-use-custom-application-fonts.html

        """
        # Load the master config file and the fonts.
        self._fontconfig_config = ffi.gc(
            fontconfig.FcInitLoadConfigAndFonts(),
            fontconfig.FcConfigDestroy)
        self.font_map = ffi.gc(
            pangoft2.pango_ft2_font_map_new(), gobject.g_object_unref)
        pangoft2.pango_fc_font_map_set_config(
            ffi.cast('PangoFcFontMap *', self.font_map),
            self._fontconfig_config)
        # pango_fc_font_map_set_config keeps a reference to config
        fontconfig.FcConfigDestroy(self._fontconfig_config)

        # Temporary folder storing fonts and Fontconfig config files
        self._folder = Path(mkdtemp(prefix='weasyprint-'))

    def add_font_face(self, rule_descriptors, url_fetcher):
        features = {
            rules[0][0].replace('-', '_'): rules[0][1] for rules in
            rule_descriptors.get('font_variant', [])}
        key = 'font_feature_settings'
        if key in rule_descriptors:
            features[key] = rule_descriptors[key]
        features_string = ''.join(
            f'<string>{key} {value}</string>'
            for key, value in font_features(**features).items())
        fontconfig_style = FONTCONFIG_STYLE[
            rule_descriptors.get('font_style', 'normal')]
        fontconfig_weight = FONTCONFIG_WEIGHT[
            rule_descriptors.get('font_weight', 'normal')]
        fontconfig_stretch = FONTCONFIG_STRETCH[
            rule_descriptors.get('font_stretch', 'normal')]
        config_key = sha1((
            f'{rule_descriptors["font_family"]}-{fontconfig_style}-'
            f'{fontconfig_weight}-{features_string}').encode()).hexdigest()
        font_path = self._folder / config_key
        if font_path.exists():
            return

        for font_type, url in rule_descriptors['src']:
            if url is None:
                continue
            if font_type in ('external', 'local'):
                config = self._fontconfig_config
                if font_type == 'local':
                    font_name = url.encode()
                    pattern = ffi.gc(
                        fontconfig.FcPatternCreate(),
                        fontconfig.FcPatternDestroy)
                    fontconfig.FcConfigSubstitute(
                        config, pattern, fontconfig.FcMatchFont)
                    fontconfig.FcDefaultSubstitute(pattern)
                    fontconfig.FcPatternAddString(
                        pattern, b'fullname', font_name)
                    fontconfig.FcPatternAddString(
                        pattern, b'postscriptname', font_name)
                    family = ffi.new('FcChar8 **')
                    postscript = ffi.new('FcChar8 **')
                    result = ffi.new('FcResult *')
                    matching_pattern = fontconfig.FcFontMatch(
                        config, pattern, result)
                    # prevent RuntimeError, see issue #677
                    if matching_pattern == ffi.NULL:
                        LOGGER.debug(
                            'Failed to get matching local font for %r',
                            font_name.decode())
                        continue

                    # TODO: do many fonts have multiple family values?
                    fontconfig.FcPatternGetString(
                        matching_pattern, b'fullname', 0, family)
                    fontconfig.FcPatternGetString(
                        matching_pattern, b'postscriptname', 0, postscript)
                    family = ffi.string(family[0])
                    postscript = ffi.string(postscript[0])
                    if font_name.lower() in (
                            family.lower(), postscript.lower()):
                        filename = ffi.new('FcChar8 **')
                        fontconfig.FcPatternGetString(
                            matching_pattern, b'file', 0, filename)
                        path = ffi.string(filename[0]).decode(
                            FILESYSTEM_ENCODING)
                        url = Path(path).as_uri()
                    else:
                        LOGGER.debug(
                            'Failed to load local font %r', font_name.decode())
                        continue

                # Get font content
                try:
                    with fetch(url_fetcher, url) as result:
                        if 'string' in result:
                            font = result['string']
                        else:
                            font = result['file_obj'].read()
                except Exception as exc:
                    LOGGER.debug('Failed to load font at %r (%s)', url, exc)
                    continue

                # Store font content
                try:
                    # Decode woff and woff2 fonts
                    if font[:3] == b'wOF':
                        out = BytesIO()
                        woff_version_byte = font[3:4]
                        if woff_version_byte == b'F':
                            # woff font
                            ttfont = TTFont(BytesIO(font))
                            ttfont.flavor = ttfont.flavorData = None
                            ttfont.save(out)
                        elif woff_version_byte == b'2':
                            # woff2 font
                            woff2.decompress(BytesIO(font), out)
                        font = out.getvalue()
                except Exception as exc:
                    LOGGER.debug(
                        'Failed to handle woff font at %r (%s)', url, exc)
                    continue
                font_path.write_bytes(font)

                xml_path = self._folder / f'{config_key}.xml'
                xml_path.write_text(f'''<?xml version="1.0"?>
                <!DOCTYPE fontconfig SYSTEM "fonts.dtd">
                <fontconfig>
                  <match target="scan">
                    <test name="file" compare="eq">
                      <string>{font_path}</string>
                    </test>
                    <edit name="family" mode="assign_replace">
                      <string>{rule_descriptors['font_family']}</string>
                    </edit>
                    <edit name="slant" mode="assign_replace">
                      <const>{fontconfig_style}</const>
                    </edit>
                    <edit name="weight" mode="assign_replace">
                      <int>{fontconfig_weight}</int>
                    </edit>
                    <edit name="width" mode="assign_replace">
                      <const>{fontconfig_stretch}</const>
                    </edit>
                  </match>
                  <match target="font">
                    <test name="file" compare="eq">
                      <string>{font_path}</string>
                    </test>
                    <edit name="fontfeatures"
                          mode="assign_replace">{features_string}</edit>
                  </match>
                </fontconfig>''')

                # TODO: We should mask local fonts with the same name
                # too as explained in Behdad's blog entry.
                fontconfig.FcConfigParseAndLoad(
                    config, str(xml_path).encode(FILESYSTEM_ENCODING),
                    True)
                font_added = fontconfig.FcConfigAppFontAddFile(
                    config, str(font_path).encode(FILESYSTEM_ENCODING))
                if font_added:
                    return pangoft2.pango_fc_font_map_config_changed(
                        ffi.cast('PangoFcFontMap *', self.font_map))
                LOGGER.debug('Failed to load font at %r', url)
        LOGGER.warning(
            'Font-face %r cannot be loaded', rule_descriptors['font_family'])

    def __del__(self):
        """Clean a font configuration for a document."""
        rmtree(self._folder, ignore_errors=True)


def font_features(font_kerning='normal', font_variant_ligatures='normal',
                  font_variant_position='normal', font_variant_caps='normal',
                  font_variant_numeric='normal',
                  font_variant_alternates='normal',
                  font_variant_east_asian='normal',
                  font_feature_settings='normal'):
    """Get the font features from the different properties in style.

    See https://www.w3.org/TR/css-fonts-3/#feature-precedence

    """
    features = {}

    # Step 1: getting the default, we rely on Pango for this
    # Step 2: @font-face font-variant, done in fonts.add_font_face
    # Step 3: @font-face font-feature-settings, done in fonts.add_font_face

    # Step 4: font-variant and OpenType features

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
        # See https://www.w3.org/TR/css-fonts-3/#font-variant-caps-prop
        if font_variant_alternates == 'historical-forms':
            features['hist'] = 1

    if font_variant_east_asian != 'normal':
        for key in font_variant_east_asian:
            features[EAST_ASIAN_KEYS[key]] = 1

    # Step 5: incompatible non-OpenType features, already handled by Pango

    # Step 6: font-feature-settings

    if font_feature_settings != 'normal':
        features.update(dict(font_feature_settings))

    return features
