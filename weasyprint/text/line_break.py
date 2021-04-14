"""
    weasyprint.text.line_break
    --------------------------

    Decide where to break text lines.

"""

import re

import pyphen

from ..logger import LOGGER
from .constants import LST_TO_ISO, PANGO_STRETCH, PANGO_STYLE, PANGO_WRAP_MODE
from .ffi import (
    ffi, gobject, pango, pangoft2, unicode_to_char_p, units_from_double,
    units_to_double)
from .fonts import font_features


def line_size(line, style):
    """Get logical width and height of the given ``line``.

    ``style`` is used to add letter spacing (if needed).

    """
    logical_extents = ffi.new('PangoRectangle *')
    pango.pango_layout_line_get_extents(line, ffi.NULL, logical_extents)
    width = units_to_double(logical_extents.width)
    height = units_to_double(logical_extents.height)
    ffi.release(logical_extents)
    if style['letter_spacing'] != 'normal':
        width += style['letter_spacing']
    return width, height


def first_line_metrics(first_line, text, layout, resume_at, space_collapse,
                       style, hyphenated=False, hyphenation_character=None):
    length = first_line.length
    if hyphenated:
        length -= len(hyphenation_character.encode('utf8'))
    elif resume_at:
        # Set an infinite width as we don't want to break lines when drawing,
        # the lines have already been split and the size may differ. Rendering
        # is also much faster when no width is set.
        pango.pango_layout_set_width(layout.layout, -1)

        # Create layout with final text
        first_line_text = text.encode('utf-8')[:length].decode('utf-8')

        # Remove trailing spaces if spaces collapse
        if space_collapse:
            first_line_text = first_line_text.rstrip(' ')

        # Remove soft hyphens
        layout.set_text(first_line_text.replace('\u00ad', ''))

        first_line, _ = layout.get_first_line()
        length = first_line.length if first_line is not None else 0

        if '\u00ad' in first_line_text:
            soft_hyphens = 0
            if first_line_text[0] == '\u00ad':
                length += 2  # len('\u00ad'.encode('utf8'))
            for i in range(len(layout.text)):
                while i + soft_hyphens + 1 < len(first_line_text):
                    if first_line_text[i + soft_hyphens + 1] == '\u00ad':
                        soft_hyphens += 1
                    else:
                        break
            length += soft_hyphens * 2  # len('\u00ad'.encode('utf8'))

    width, height = line_size(first_line, style)
    baseline = units_to_double(pango.pango_layout_get_baseline(layout.layout))
    layout.deactivate()
    return layout, length, resume_at, width, height, baseline


class Layout:
    """Object holding PangoLayout-related cdata pointers."""
    def __init__(self, context, font_size, style, justification_spacing=0,
                 max_width=None):
        self.justification_spacing = justification_spacing
        self.setup(context, font_size, style)
        self.max_width = max_width

    def setup(self, context, font_size, style):
        self.context = context
        self.style = style
        self.first_line_direction = 0

        if context is None:
            font_map = ffi.gc(
                pangoft2.pango_ft2_font_map_new(), gobject.g_object_unref)
        else:
            font_map = context.font_config.font_map
        pango_context = ffi.gc(
            pango.pango_font_map_create_context(font_map),
            gobject.g_object_unref)
        pango.pango_context_set_round_glyph_positions(pango_context, False)
        self.layout = ffi.gc(
            pango.pango_layout_new(pango_context),
            gobject.g_object_unref)

        if style['font_language_override'] != 'normal':
            lang_p, lang = unicode_to_char_p(LST_TO_ISO.get(
                style['font_language_override'].lower(),
                style['font_language_override']))
        elif style['lang']:
            lang_p, lang = unicode_to_char_p(style['lang'])
        else:
            lang = None
            self.language = pango.pango_language_get_default()
        if lang:
            self.language = pango.pango_language_from_string(lang_p)
            pango.pango_context_set_language(pango_context, self.language)

        assert not isinstance(style['font_family'], str), (
            'font_family should be a list')
        self.font = ffi.gc(
            pango.pango_font_description_new(),
            pango.pango_font_description_free)
        family_p, family = unicode_to_char_p(','.join(style['font_family']))
        pango.pango_font_description_set_family(self.font, family_p)
        pango.pango_font_description_set_style(
            self.font, PANGO_STYLE[style['font_style']])
        pango.pango_font_description_set_stretch(
            self.font, PANGO_STRETCH[style['font_stretch']])
        pango.pango_font_description_set_weight(
            self.font, style['font_weight'])
        pango.pango_font_description_set_absolute_size(
            self.font, units_from_double(font_size))
        pango.pango_layout_set_font_description(self.layout, self.font)

        text_decoration = style['text_decoration_line']
        if text_decoration != 'none':
            metrics = ffi.gc(
                pango.pango_context_get_metrics(
                    pango_context, self.font, self.language),
                pango.pango_font_metrics_unref)
            self.ascent = units_to_double(
                pango.pango_font_metrics_get_ascent(metrics))
            self.underline_position = units_to_double(
                pango.pango_font_metrics_get_underline_position(metrics))
            self.strikethrough_position = units_to_double(
                pango.pango_font_metrics_get_strikethrough_position(metrics))
            self.underline_thickness = units_to_double(
                pango.pango_font_metrics_get_underline_thickness(metrics))
            self.strikethrough_thickness = units_to_double(
                pango.pango_font_metrics_get_strikethrough_thickness(metrics))
        else:
            self.ascent = None
            self.underline_position = None
            self.strikethrough_position = None

        features = font_features(
            style['font_kerning'], style['font_variant_ligatures'],
            style['font_variant_position'], style['font_variant_caps'],
            style['font_variant_numeric'], style['font_variant_alternates'],
            style['font_variant_east_asian'], style['font_feature_settings'])
        if features and context:
            features = ','.join(
                f'{key} {value}' for key, value in features.items())

            # TODO: attributes should be freed.
            # In the meantime, keep a cache to avoid leaking too many of them.
            attr = context.font_features.get(features)
            if attr is None:
                try:
                    attr = pango.pango_attr_font_features_new(
                        features.encode('ascii'))
                except AttributeError:
                    LOGGER.error(
                        'OpenType features are not available '
                        'with Pango < 1.38')
                else:
                    context.font_features[features] = attr
            if attr is not None:
                attr_list = pango.pango_attr_list_new()
                pango.pango_attr_list_insert(attr_list, attr)
                pango.pango_layout_set_attributes(self.layout, attr_list)

    def get_first_line(self):
        first_line = pango.pango_layout_get_line_readonly(self.layout, 0)
        second_line = pango.pango_layout_get_line_readonly(self.layout, 1)
        if second_line != ffi.NULL:
            index = second_line.start_index
        else:
            index = None
        self.first_line_direction = first_line.resolved_dir
        return first_line, index

    def set_text(self, text, justify=False):
        try:
            # Keep only the first line plus one character, we don't need more
            text = text[:text.index('\n') + 2]
        except ValueError:
            # End-of-line not found, keept the whole text
            pass
        text, bytestring = unicode_to_char_p(text)
        self.text = bytestring.decode('utf-8')
        pango.pango_layout_set_text(self.layout, text, -1)

        # Word spacing may not be set if we're trying to get word-spacing
        # computed value using a layout, for example if its unit is ex.
        word_spacing = self.style.get('word_spacing', 0)
        if justify:
            # Justification is needed when drawing text but is useless during
            # layout. Ignore it before layout is reactivated before the drawing
            # step.
            word_spacing += self.justification_spacing

        # Letter spacing may not be set if we're trying to get letter-spacing
        # computed value using a layout, for example if its unit is ex.
        letter_spacing = self.style.get('letter_spacing', 'normal')
        if letter_spacing == 'normal':
            letter_spacing = 0

        if text and (word_spacing != 0 or letter_spacing != 0):
            letter_spacing = units_from_double(letter_spacing)
            space_spacing = units_from_double(word_spacing) + letter_spacing
            attr_list = pango.pango_layout_get_attributes(self.layout)
            if not attr_list:
                # TODO: list should be freed
                attr_list = pango.pango_attr_list_new()

            def add_attr(start, end, spacing):
                # TODO: attributes should be freed
                attr = pango.pango_attr_letter_spacing_new(spacing)
                attr.start_index, attr.end_index = start, end
                pango.pango_attr_list_change(attr_list, attr)

            add_attr(0, len(bytestring), letter_spacing)
            position = bytestring.find(b' ')
            while position != -1:
                add_attr(position, position + 1, space_spacing)
                position = bytestring.find(b' ', position + 1)

            pango.pango_layout_set_attributes(self.layout, attr_list)

        # Tabs width
        if b'\t' in bytestring:
            self.set_tabs()

    def set_tabs(self):
        if isinstance(self.style['tab_size'], int):
            layout = Layout(
                self.context, self.style['font_size'], self.style,
                self.justification_spacing)
            layout.set_text(' ' * self.style['tab_size'])
            line, _ = layout.get_first_line()
            width, _ = line_size(line, self.style)
            width = int(round(width))
        else:
            width = int(self.style['tab_size'].value)
        # 0 is not handled correctly by Pango
        array = ffi.gc(
            pango.pango_tab_array_new_with_positions(
                1, True, pango.PANGO_TAB_LEFT, width or 1),
            pango.pango_tab_array_free)
        pango.pango_layout_set_tabs(self.layout, array)

    def deactivate(self):
        del self.layout, self.font, self.language, self.style

    def reactivate(self, style):
        self.setup(self.context, style['font_size'], style)
        self.set_text(self.text, justify=True)


def create_layout(text, style, context, max_width, justification_spacing):
    """Return an opaque Pango layout with default Pango line-breaks.

    :param text: Unicode
    :param style: a style dict of computed values
    :param max_width:
        The maximum available width in the same unit as ``style['font_size']``,
        or ``None`` for unlimited width.

    """
    layout = Layout(
        context, style['font_size'], style, justification_spacing, max_width)

    # Make sure that max_width * Pango.SCALE == max_width * 1024 fits in a
    # signed integer. Treat bigger values same as None: unconstrained width.
    text_wrap = style['white_space'] in ('normal', 'pre-wrap', 'pre-line')
    if max_width is not None and text_wrap and max_width < 2 ** 21:
        pango.pango_layout_set_width(
            layout.layout, units_from_double(max(0, max_width)))

    layout.set_text(text)
    return layout


def split_first_line(text, style, context, max_width, justification_spacing,
                     minimum=False):
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
    # See https://www.w3.org/TR/css-text-3/#white-space-property
    text_wrap = style['white_space'] in ('normal', 'pre-wrap', 'pre-line')
    space_collapse = style['white_space'] in ('normal', 'nowrap', 'pre-line')

    original_max_width = max_width
    if not text_wrap:
        max_width = None

    # Step #1: Get a draft layout with the first line
    layout = None
    if (max_width is not None and max_width != float('inf') and
            style['font_size']):
        if max_width == 0:
            # Trying to find minimum size, let's naively split on spaces and
            # keep one word + one letter
            space_index = text.find(' ')
            if space_index == -1:
                expected_length = len(text)
            else:
                expected_length = space_index + 2  # index + space + one letter
        else:
            expected_length = int(max_width / style['font_size'] * 2.5)
        if expected_length < len(text):
            # Try to use a small amount of text instead of the whole text
            layout = create_layout(
                text[:expected_length], style, context, max_width,
                justification_spacing)
            first_line, index = layout.get_first_line()
            if index is None:
                # The small amount of text fits in one line, give up and use
                # the whole text
                layout = None
    if layout is None:
        layout = create_layout(
            text, style, context, original_max_width, justification_spacing)
        first_line, index = layout.get_first_line()
    resume_at = index

    # Step #2: Don't split lines when it's not needed
    if max_width is None:
        # The first line can take all the place needed
        return first_line_metrics(
            first_line, text, layout, resume_at, space_collapse, style)
    first_line_width, _ = line_size(first_line, style)
    if index is None and first_line_width <= max_width:
        # The first line fits in the available width
        return first_line_metrics(
            first_line, text, layout, resume_at, space_collapse, style)

    # Step #3: Try to put the first word of the second line on the first line
    # https://mail.gnome.org/archives/gtk-i18n-list/2013-September/msg00006
    # is a good thread related to this problem.
    first_line_text = text.encode('utf-8')[:index].decode('utf-8')
    # We can’t rely on first_line_width, see
    # https://github.com/Kozea/WeasyPrint/issues/1051
    first_line_fits = (
        first_line_width <= max_width or
        ' ' in first_line_text.strip() or
        can_break_text(first_line_text.strip(), style['lang']))
    if first_line_fits:
        # The first line fits but may have been cut too early by Pango
        second_line_text = text.encode('utf-8')[index:].decode('utf-8')
    else:
        # The line can't be split earlier, try to hyphenate the first word.
        first_line_text = ''
        second_line_text = text

    next_word = second_line_text.split(' ', 1)[0]
    if next_word:
        if space_collapse:
            # next_word might fit without a space afterwards
            # only try when space collapsing is allowed
            new_first_line_text = first_line_text + next_word
            layout.set_text(new_first_line_text)
            first_line, index = layout.get_first_line()
            first_line_width, _ = line_size(first_line, style)
            if index is None and first_line_text:
                # The next word fits in the first line, keep the layout
                resume_at = len(new_first_line_text.encode('utf-8')) + 1
                return first_line_metrics(
                    first_line, text, layout, resume_at, space_collapse, style)
            elif index:
                # Text may have been split elsewhere by Pango earlier
                resume_at = index
            else:
                # Second line is none
                resume_at = first_line.length + 1
                if resume_at >= len(text.encode('utf-8')):
                    resume_at = None
    elif first_line_text:
        # We found something on the first line but we did not find a word on
        # the next line, no need to hyphenate, we can keep the current layout
        return first_line_metrics(
            first_line, text, layout, resume_at, space_collapse, style)

    # Step #4: Try to hyphenate
    hyphens = style['hyphens']
    lang = style['lang'] and pyphen.language_fallback(style['lang'])
    total, left, right = style['hyphenate_limit_chars']
    hyphenated = False
    soft_hyphen = '\u00ad'

    try_hyphenate = False
    if hyphens != 'none':
        next_word_boundaries = get_next_word_boundaries(second_line_text, lang)
        if next_word_boundaries:
            # We have a word to hyphenate
            start_word, stop_word = next_word_boundaries
            next_word = second_line_text[start_word:stop_word]
            if stop_word - start_word >= total:
                # This word is long enough
                first_line_width, _ = line_size(first_line, style)
                space = max_width - first_line_width
                if style['hyphenate_limit_zone'].unit == '%':
                    limit_zone = (
                        max_width * style['hyphenate_limit_zone'].value / 100.)
                else:
                    limit_zone = style['hyphenate_limit_zone'].value
                if space > limit_zone or space < 0:
                    # Available space is worth the try, or the line is even too
                    # long to fit: try to hyphenate
                    try_hyphenate = True

    if try_hyphenate:
        # Automatic hyphenation possible and next word is long enough
        auto_hyphenation = hyphens == 'auto' and lang
        manual_hyphenation = False
        if auto_hyphenation:
            if soft_hyphen in first_line_text or soft_hyphen in next_word:
                # Automatic hyphenation opportunities within a word must be
                # ignored if the word contains a conditional hyphen, in favor
                # of the conditional hyphen(s).
                # See https://drafts.csswg.org/css-text-3/#valdef-hyphens-auto
                manual_hyphenation = True
        else:
            manual_hyphenation = hyphens == 'manual'

        if manual_hyphenation:
            # Manual hyphenation: check that the line ends with a soft
            # hyphen and add the missing hyphen
            if first_line_text.endswith(soft_hyphen):
                # The first line has been split on a soft hyphen
                if ' ' in first_line_text:
                    first_line_text, next_word = (
                        first_line_text.rsplit(' ', 1))
                    next_word = f' {next_word}'
                    layout.set_text(first_line_text)
                    first_line, index = layout.get_first_line()
                    resume_at = len((first_line_text + ' ').encode('utf8'))
                else:
                    first_line_text, next_word = '', first_line_text
            soft_hyphen_indexes = [
                match.start() for match in re.finditer(soft_hyphen, next_word)]
            soft_hyphen_indexes.reverse()
            dictionary_iterations = [
                next_word[:i + 1] for i in soft_hyphen_indexes]
        elif auto_hyphenation:
            dictionary_key = (lang, left, right, total)
            dictionary = context.dictionaries.get(dictionary_key)
            if dictionary is None:
                dictionary = pyphen.Pyphen(lang=lang, left=left, right=right)
                context.dictionaries[dictionary_key] = dictionary
            dictionary_iterations = [
                start for start, end in dictionary.iterate(next_word)]
        else:
            dictionary_iterations = []

        if dictionary_iterations:
            for first_word_part in dictionary_iterations:
                new_first_line_text = (
                    first_line_text +
                    second_line_text[:start_word] +
                    first_word_part)
                hyphenated_first_line_text = (
                    new_first_line_text + style['hyphenate_character'])
                new_layout = create_layout(
                    hyphenated_first_line_text, style, context, max_width,
                    justification_spacing)
                new_first_line, new_index = new_layout.get_first_line()
                new_first_line_width, _ = line_size(new_first_line, style)
                new_space = max_width - new_first_line_width
                if new_index is None and (
                        new_space >= 0 or
                        first_word_part == dictionary_iterations[-1]):
                    hyphenated = True
                    layout = new_layout
                    first_line = new_first_line
                    index = new_index
                    resume_at = len(new_first_line_text.encode('utf8'))
                    if text[len(new_first_line_text)] == soft_hyphen:
                        # Recreate the layout with no max_width to be sure that
                        # we don't break before the soft hyphen
                        pango.pango_layout_set_width(
                            layout.layout, units_from_double(-1))
                        resume_at += len(soft_hyphen.encode('utf8'))
                    break

            if not hyphenated and not first_line_text:
                # Recreate the layout with no max_width to be sure that
                # we don't break before or inside the hyphenate character
                hyphenated = True
                layout.set_text(hyphenated_first_line_text)
                pango.pango_layout_set_width(
                    layout.layout, units_from_double(-1))
                first_line, index = layout.get_first_line()
                resume_at = len(new_first_line_text.encode('utf8'))
                if text[len(first_line_text)] == soft_hyphen:
                    resume_at += len(soft_hyphen.encode('utf8'))

    if not hyphenated and first_line_text.endswith(soft_hyphen):
        # Recreate the layout with no max_width to be sure that
        # we don't break inside the hyphenate-character string
        hyphenated = True
        hyphenated_first_line_text = (
            first_line_text + style['hyphenate_character'])
        layout.set_text(hyphenated_first_line_text)
        pango.pango_layout_set_width(
            layout.layout, units_from_double(-1))
        first_line, index = layout.get_first_line()
        resume_at = len(first_line_text.encode('utf8'))

    # Step 5: Try to break word if it's too long for the line
    overflow_wrap = style['overflow_wrap']
    first_line_width, _ = line_size(first_line, style)
    space = max_width - first_line_width
    # If we can break words and the first line is too long
    if not minimum and overflow_wrap == 'break-word' and space < 0:
        # Is it really OK to remove hyphenation for word-break ?
        hyphenated = False
        # TODO: Modify code to preserve W3C condition:
        # "Shaping characters are still shaped as if the word were not broken"
        # The way new lines are processed in this function (one by one with no
        # memory of the last) prevents shaping characters (arabic, for
        # instance) from keeping their shape when wrapped on the next line with
        # pango layout. Maybe insert Unicode shaping characters in text?
        layout.set_text(text)
        pango.pango_layout_set_width(
            layout.layout, units_from_double(max_width))
        pango.pango_layout_set_wrap(
            layout.layout, PANGO_WRAP_MODE['WRAP_CHAR'])
        first_line, index = layout.get_first_line()
        resume_at = index or first_line.length
        if resume_at >= len(text.encode('utf-8')):
            resume_at = None

    return first_line_metrics(
        first_line, text, layout, resume_at, space_collapse, style, hyphenated,
        style['hyphenate_character'])


def get_log_attrs(text, lang):
    if lang:
        lang_p, lang = unicode_to_char_p(lang)
    else:
        lang = None
        language = pango.pango_language_get_default()
    if lang:
        language = pango.pango_language_from_string(lang_p)
    # TODO: this should be removed when bidi is supported
    for char in ('\u202a', '\u202b', '\u202c', '\u202d', '\u202e'):
        text = text.replace(char, '\u200b')
    text_p, bytestring = unicode_to_char_p(text)
    length = len(text) + 1
    log_attrs = ffi.new('PangoLogAttr[]', length)
    pango.pango_get_log_attrs(
        text_p, len(bytestring), -1, language, log_attrs, length)
    return bytestring, log_attrs


def can_break_text(text, lang):
    if not text or len(text) < 2:
        return None
    bytestring, log_attrs = get_log_attrs(text, lang)
    length = len(text) + 1
    return any(attr.is_line_break for attr in log_attrs[1:length - 1])


def get_next_word_boundaries(text, lang):
    if not text or len(text) < 2:
        return None
    bytestring, log_attrs = get_log_attrs(text, lang)
    for i, attr in enumerate(log_attrs):
        if attr.is_word_end:
            word_end = i
            break
        if attr.is_word_boundary:
            word_start = i
    else:
        return None
    return word_start, word_end


def get_last_word_end(text, lang):
    if not text or len(text) < 2:
        return None
    bytestring, log_attrs = get_log_attrs(text, lang)
    for i, attr in enumerate(list(log_attrs)[::-1]):
        if i and attr.is_word_end:
            return len(text) - i
