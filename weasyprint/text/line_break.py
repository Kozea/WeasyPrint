"""Decide where to break text lines."""

import re
from math import inf

import pyphen

from .constants import LST_TO_ISO, PANGO_DIRECTION, PANGO_WRAP_MODE
from .ffi import FROM_UNITS, TO_UNITS, ffi, gobject, pango, pangoft2, unicode_to_char_p
from .fonts import font_features, get_font_description


def line_size(line, style):
    """Get logical width and height of the given ``line``.

    ``style`` is used to add letter spacing (if needed).

    """
    logical_extents = ffi.new('PangoRectangle *')
    pango.pango_layout_line_get_extents(line, ffi.NULL, logical_extents)
    width = logical_extents.width * FROM_UNITS
    height = logical_extents.height * FROM_UNITS
    ffi.release(logical_extents)
    if style['letter_spacing'] != 'normal':
        width += style['letter_spacing']
    return width, height


def first_line_metrics(first_line, text, layout, resume_at, space_collapse,
                       style, hyphenated=False, hyphenation_character=None):
    length = first_line.length
    if hyphenated:
        length -= len(hyphenation_character.encode())
    elif resume_at:
        # Set an infinite width as we don't want to break lines when drawing,
        # the lines have already been split and the size may differ. Rendering
        # is also much faster when no width is set.
        pango.pango_layout_set_width(layout.layout, -1)

        # Create layout with final text
        first_line_text = text.encode()[:length].decode()

        # Remove trailing spaces if spaces collapse
        if space_collapse:
            first_line_text = first_line_text.rstrip(' ')

        layout.set_text(first_line_text)
        first_line, _ = layout.get_first_line()
        length = first_line.length if first_line is not None else 0

    width, height = line_size(first_line, style)
    baseline = pango.pango_layout_get_baseline(layout.layout) * FROM_UNITS
    layout.deactivate()
    return layout, length, resume_at, width, height, baseline


class Layout:
    """Object holding PangoLayout-related cdata pointers."""
    def __init__(self, context, style, justification_spacing=0,
                 max_width=None):
        self.justification_spacing = justification_spacing
        self.setup(context, style)
        self.max_width = max_width

    def setup(self, context, style):
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
        pango.pango_context_set_base_dir(
            pango_context, PANGO_DIRECTION[style['direction']])

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
        font_description = get_font_description(style)
        self.layout = ffi.gc(
            pango.pango_layout_new(pango_context),
            gobject.g_object_unref)
        pango.pango_layout_set_auto_dir(self.layout, False)
        pango.pango_layout_set_font_description(self.layout, font_description)

        text_decoration = style['text_decoration_line']
        if text_decoration != 'none':
            metrics = ffi.gc(
                pango.pango_context_get_metrics(
                    pango_context, font_description, self.language),
                pango.pango_font_metrics_unref)
            self.ascent = FROM_UNITS * (
                pango.pango_font_metrics_get_ascent(metrics))
            self.underline_position = FROM_UNITS * (
                pango.pango_font_metrics_get_underline_position(metrics))
            self.strikethrough_position = FROM_UNITS * (
                pango.pango_font_metrics_get_strikethrough_position(metrics))
            self.underline_thickness = FROM_UNITS * (
                pango.pango_font_metrics_get_underline_thickness(metrics))
            self.strikethrough_thickness = FROM_UNITS * (
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
                f'{key} {value}' for key, value in features.items()).encode()
            # In the meantime, keep a cache to avoid leaking too many of them.
            attr = context.font_features.setdefault(
                features, pango.pango_attr_font_features_new(features))
            attr_list = pango.pango_attr_list_new()
            pango.pango_attr_list_insert(attr_list, attr)
            pango.pango_layout_set_attributes(self.layout, attr_list)

    def get_first_line(self):
        first_line = pango.pango_layout_get_line_readonly(self.layout, 0)
        second_line = pango.pango_layout_get_line_readonly(self.layout, 1)
        index = None if second_line == ffi.NULL else second_line.start_index
        self.first_line_direction = first_line.resolved_dir
        return first_line, index

    def set_text(self, text, justify=False):
        index = text.find('\n')
        if index != -1:
            # Keep only the first line plus one character, we don't need more
            text = text[:index+2]
        self.text = text
        text, bytestring = unicode_to_char_p(text)
        pango.pango_layout_set_text(self.layout, text, -1)

        word_spacing = self.style['word_spacing']
        if justify:
            # Justification is needed when drawing text but is useless during
            # layout, when it can be ignored.
            word_spacing += self.justification_spacing

        letter_spacing = self.style['letter_spacing']
        if letter_spacing == 'normal':
            letter_spacing = 0

        word_breaking = (
            self.style['overflow_wrap'] in ('anywhere', 'break-word'))

        if self.text and (word_spacing or letter_spacing or word_breaking):
            attr_list = pango.pango_layout_get_attributes(self.layout)
            if attr_list == ffi.NULL:
                attr_list = ffi.gc(
                    pango.pango_attr_list_new(),
                    pango.pango_attr_list_unref)

            def add_attr(start, end, spacing):
                attr = pango.pango_attr_letter_spacing_new(spacing)
                attr.start_index, attr.end_index = start, end
                pango.pango_attr_list_change(attr_list, attr)

            if letter_spacing:
                letter_spacing = int(letter_spacing * TO_UNITS)
                add_attr(0, len(bytestring), letter_spacing)

            if word_spacing:
                if bytestring == b' ':
                    # We need more than one space to set word spacing
                    self.text = ' \u200b'  # Space + zero-width space
                    text, bytestring = unicode_to_char_p(self.text)
                    pango.pango_layout_set_text(self.layout, text, -1)

                space_spacing = int(word_spacing * TO_UNITS + letter_spacing)
                # Pango gives only half of word-spacing on boundaries
                boundary_positions = (0, len(bytestring) - 1)
                for match in re.finditer(' |\u00a0'.encode(), bytestring):
                    factor = 1 + (match.start() in boundary_positions)
                    add_attr(match.start(), match.end(), factor * space_spacing)

            if word_breaking:
                attr = pango.pango_attr_insert_hyphens_new(False)
                attr.start_index, attr.end_index = 0, len(bytestring)
                pango.pango_attr_list_change(attr_list, attr)

            pango.pango_layout_set_attributes(self.layout, attr_list)

        # Tabs width
        if b'\t' in bytestring:
            self.set_tabs()

    def set_tabs(self):
        if isinstance(self.style['tab_size'], int):
            layout = Layout(
                self.context, self.style, self.justification_spacing)
            layout.set_text(' ' * self.style['tab_size'])
            line, _ = layout.get_first_line()
            width, _ = line_size(line, self.style)
            width = round(width)
        else:
            width = int(self.style['tab_size'].value)
        # 0 is not handled correctly by Pango
        array = ffi.gc(
            pango.pango_tab_array_new_with_positions(
                1, True, pango.PANGO_TAB_LEFT, width or 1),
            pango.pango_tab_array_free)
        pango.pango_layout_set_tabs(self.layout, array)

    def deactivate(self):
        del self.layout, self.language, self.style

    def reactivate(self, style):
        self.setup(self.context, style)
        self.set_text(self.text, justify=True)


def create_layout(text, style, context, max_width, justification_spacing):
    """Return an opaque Pango layout with default Pango line-breaks."""
    layout = Layout(context, style, justification_spacing, max_width)

    # Make sure that max_width * Pango.SCALE == max_width * 1024 fits in a
    # signed integer. Treat bigger values same as None: unconstrained width.
    text_wrap = style['white_space'] in ('normal', 'pre-wrap', 'pre-line')
    if max_width is not None and text_wrap and max_width < 2 ** 21:
        pango.pango_layout_set_width(layout.layout, int(max(0, max_width) * TO_UNITS))

    layout.set_text(text)
    return layout


def split_first_line(text, style, context, max_width, justification_spacing,
                     is_line_start=True, minimum=False):
    """Fit as much as possible in the available width for one line of text.

    Return ``(layout, length, resume_index, width, height, baseline)``.

    ``layout``: a pango Layout with the first line
    ``length``: length in UTF-8 bytes of the first line
    ``resume_index``: The number of UTF-8 bytes to skip for the next line.
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

    # Step #1: Get a draft layout with the first line.
    ratio = 4  # number that almost always respects char_height / char_width > ratio
    short_text = text
    if max_width is not None and max_width != inf and style['font_size']:
        # Try to use a small amount of text to avoid the whole layout. We need
        # at least one line, and one possible line break point on the second line.
        if style['font_size'] * ratio > max_width:
            # Trying to find minimum or very small size, let's naively split on
            # spaces and keep one word + one letter.
            space_index = text.find(' ')
            if space_index != -1:
                short_text = text[:space_index+2]  # index + space + one letter
        else:
            # Use the magic ration and hope that we’ll get the right amount of text.
            short_text = text[:int(max_width / style['font_size'] * ratio)]
        layout = create_layout(
            short_text, style, context, max_width, justification_spacing)
        first_line, resume_index = layout.get_first_line()
        if resume_index is None and short_text != text:
            # The small amount of text fits in one line, give up and use the
            # whole text.
            short_text = text
            layout.set_text(text)
            first_line, resume_index = layout.get_first_line()
        else:
            # If the second line of the short text can break, we have the next
            # line break point required for step #3 in it, drop the end of the text.
            first_line_text = short_text.encode()[:resume_index].decode()
            if first_line_text != short_text:
                start, end = len(first_line_text) + 1, len(short_text)
                text_end_log_attrs = pango.pango_layout_get_log_attrs_readonly(
                    layout.layout, ffi.NULL)[start:end]
                if get_next_break_point(text_end_log_attrs) is not None:
                    text = short_text
    else:
        layout = create_layout(
            text, style, context, original_max_width, justification_spacing)
        first_line, resume_index = layout.get_first_line()

    # Step #2: Don't split lines when it's not needed.
    if max_width is None:
        # The first line can take all the place needed.
        return first_line_metrics(
            first_line, text, layout, resume_index, space_collapse, style)
    first_line_width, _ = line_size(first_line, style)
    if resume_index is None and first_line_width <= max_width:
        # The first line fits in the available width.
        return first_line_metrics(
            first_line, text, layout, resume_index, space_collapse, style)

    # Step #3: Try to put the first word of the second line on the first line
    # https://mail.gnome.org/archives/gtk-i18n-list/2013-September/msg00006
    # is a good thread related to this problem.
    if first_line_width <= max_width:
        # The first line fits but may have been cut too early by Pango.
        encoded_text = text.encode()
        first_line_text = encoded_text[:resume_index].decode()
        second_line_text = encoded_text[resume_index:].decode()
    else:
        # The line can't be split earlier, try to hyphenate the first word.
        first_line_text = ''
        second_line_text = text
    if first_line_text == short_text:
        # There’s no second line, don’t try to find a next word.
        break_point = None
    else:
        # Find then second line’s first break point.
        log_attrs = pango.pango_layout_get_log_attrs_readonly(layout.layout, ffi.NULL)
        start, end = len(first_line_text) + 1, len(short_text)
        second_line_log_attrs = log_attrs[start:end]
        break_point = get_next_break_point(second_line_log_attrs)
        if break_point is not None:
            break_point -= len(first_line_text) + 1
    next_word = second_line_text[:break_point].rstrip(' ')
    if next_word:
        if space_collapse and second_line_text[break_point or -1] == ' ':
            # Next word might fit without a space afterwards only try when
            # space collapsing is allowed.
            new_first_line_text = first_line_text + next_word
            layout.set_text(new_first_line_text)
            first_line, resume_index = layout.get_first_line()
            if resume_index is None:
                if first_line_text:
                    # The next word fits in the first line, keep the layout.
                    resume_index = len(new_first_line_text.encode()) + 1
                    return first_line_metrics(
                        first_line, text, layout, resume_index, space_collapse, style)
                else:
                    # Second line is None.
                    resume_index = first_line.length + 1
                    if resume_index >= len(text.encode()):
                        resume_index = None
    elif first_line_text:
        # We found something on the first line but we did not find a word on
        # the next line, no need to hyphenate, we can keep the current layout.
        return first_line_metrics(
            first_line, text, layout, resume_index, space_collapse, style)

    # Step #4: Try to hyphenate
    hyphens = style['hyphens']
    lang = style['lang'] and pyphen.language_fallback(style['lang'])
    total, left, right = style['hyphenate_limit_chars']
    hyphenated = False
    soft_hyphen = '\xad'

    auto_hyphenation = manual_hyphenation = False

    if hyphens != 'none':
        manual_hyphenation = soft_hyphen in first_line_text + second_line_text

    if hyphens == 'auto' and lang:
        # Get text until next line break opportunity.
        next_text = second_line_text
        if (next_break_point := get_next_break_point_from_text(second_line_text, lang)):
            next_text = next_text[:next_break_point]

        # Try all words included in this text.
        next_text_index = 0
        while next_text:
            next_word_boundaries = get_next_word_boundaries(next_text, lang)
            if next_word_boundaries:
                # We have a word to hyphenate.
                start_word, stop_word = next_word_boundaries
                next_word = next_text[start_word:stop_word]
                if stop_word - start_word >= total:
                    # This word is long enough.
                    first_line_width, _ = line_size(first_line, style)
                    space = max_width - first_line_width
                    if style['hyphenate_limit_zone'].unit == '%':
                        limit_zone = (
                            max_width * style['hyphenate_limit_zone'].value / 100)
                    else:
                        limit_zone = style['hyphenate_limit_zone'].value
                    if space > limit_zone or space < 0:
                        # Available space is worth the try, or the line is even too long
                        # to fit: try to hyphenate.
                        auto_hyphenation = True
                        next_text_index += start_word
                        break

                # This word doesn’t work, try next one.
                next_text = next_text[stop_word:]
                next_text_index += stop_word
            else:
                break

    # Automatic hyphenation opportunities within a word must be ignored if the
    # word contains a conditional hyphen, in favor of the conditional
    # hyphen(s).
    # See https://drafts.csswg.org/css-text-3/#valdef-hyphens-auto
    if manual_hyphenation:
        # Manual hyphenation: check that the line ends with a soft
        # hyphen and add the missing hyphen
        if first_line_text.endswith(soft_hyphen):
            # The first line has been split on a soft hyphen
            first_line_text, second_line_text = '', first_line_text
        soft_hyphen_indexes = [
            match.start() for match in re.finditer(soft_hyphen, second_line_text)]
        soft_hyphen_indexes.reverse()
        dictionary_iterations = [second_line_text[:i+1] for i in soft_hyphen_indexes]
    elif auto_hyphenation:
        dictionary_key = (lang, left, right, total)
        dictionary = context.dictionaries.get(dictionary_key)
        if dictionary is None:
            dictionary = pyphen.Pyphen(lang=lang, left=left, right=right)
            context.dictionaries[dictionary_key] = dictionary
        previous_words = second_line_text[:next_text_index]
        dictionary_iterations = [
            previous_words + start for start, end in dictionary.iterate(next_word)]
    else:
        dictionary_iterations = []

    if dictionary_iterations:
        for first_word_part in dictionary_iterations:
            new_first_line_text = first_line_text + first_word_part
            hyphenated_first_line_text = (
                new_first_line_text + style['hyphenate_character'])
            new_layout = create_layout(
                hyphenated_first_line_text, style, context, max_width,
                justification_spacing)
            new_first_line, index = new_layout.get_first_line()
            new_first_line_width, _ = line_size(new_first_line, style)
            new_space = max_width - new_first_line_width
            hyphenated = index is None and (
                new_space >= 0 or first_word_part == dictionary_iterations[-1])
            if hyphenated:
                layout = new_layout
                first_line = new_first_line
                resume_index = len(new_first_line_text.encode())
                break

        if not hyphenated and not first_line_text:
            # Recreate the layout with no max_width to be sure that
            # we don't break before or inside the hyphenate character
            hyphenated = True
            layout.set_text(hyphenated_first_line_text)
            pango.pango_layout_set_width(layout.layout, -1)
            first_line, _ = layout.get_first_line()
            resume_index = len(new_first_line_text.encode())
            if text[len(first_line_text)] == soft_hyphen:
                resume_index += len(soft_hyphen.encode())

    if not hyphenated and first_line_text.endswith(soft_hyphen):
        # Recreate the layout with no max_width to be sure that
        # we don't break inside the hyphenate-character string
        hyphenated = True
        hyphenated_first_line_text = (
            first_line_text + style['hyphenate_character'])
        layout.set_text(hyphenated_first_line_text)
        pango.pango_layout_set_width(layout.layout, -1)
        first_line, _ = layout.get_first_line()
        resume_index = len(first_line_text.encode())

    # Step 5: Try to break word if it's too long for the line
    overflow_wrap = style['overflow_wrap']
    first_line_width, _ = line_size(first_line, style)
    space = max_width - first_line_width
    # If we can break words and the first line is too long
    can_break = (
        style['word_break'] == 'break-all' or (
            is_line_start and (
                overflow_wrap == 'anywhere' or
                (overflow_wrap == 'break-word' and not minimum))))
    if space < 0 and can_break:
        # Is it really OK to remove hyphenation for word-break ?
        hyphenated = False
        # TODO: Modify code to preserve W3C condition:
        # "Shaping characters are still shaped as if the word were not broken"
        # The way new lines are processed in this function (one by one with no
        # memory of the last) prevents shaping characters (arabic, for
        # instance) from keeping their shape when wrapped on the next line with
        # pango layout. Maybe insert Unicode shaping characters in text?
        layout.set_text(text)
        pango.pango_layout_set_width(layout.layout, int(max_width * TO_UNITS))
        pango.pango_layout_set_wrap(layout.layout, PANGO_WRAP_MODE['WRAP_CHAR'])
        first_line, index = layout.get_first_line()
        resume_index = index or first_line.length
        if resume_index >= len(text.encode()):
            resume_index = None

    return first_line_metrics(
        first_line, text, layout, resume_index, space_collapse, style,
        hyphenated, style['hyphenate_character'])


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
    return log_attrs


def get_next_break_point(log_attrs):
    for i, attr in enumerate(log_attrs):
        if attr.is_line_break:
            return i


def get_next_break_point_from_text(text, lang):
    if not text or len(text) < 2:
        return None
    log_attrs = get_log_attrs(text, lang)
    length = len(text) + 1
    return get_next_break_point(log_attrs[1:length-1])


def can_break_text(text, lang):
    return get_next_break_point_from_text(text, lang) is not None


def get_next_word_boundaries(text, lang):
    if not text or len(text) < 2:
        return None
    log_attrs = get_log_attrs(text, lang)
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
    log_attrs = get_log_attrs(text, lang)
    for i, attr in enumerate(list(log_attrs)[::-1]):
        if i and attr.is_word_end:
            return len(text) - i
