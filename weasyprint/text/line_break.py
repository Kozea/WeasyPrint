"""Decide where to break text lines."""

from collections import namedtuple
import re
from math import inf

import pyphen

from .constants import LST_TO_ISO, PANGO_STRETCH, PANGO_STYLE, PANGO_WRAP_MODE
from .ffi import (
    ffi, gobject, harfbuzz, pango, pangoft2, unicode_to_char_p,
    units_from_double, units_to_double, glist_to_list, PANGO_SCALE)
from .fonts import font_features

ShapingResult = namedtuple(
    'ShapingResult', 'start end item hb_buffer glyph_positions glyph_infos ' \
    'hb_font pango_font')


def pango_attrs_from_style(context, style, start, end):
    """
    Returns an array of Pango attributes corresponding to the provided style.
    """
    assert not isinstance(style['font_family'], str), (
        'font_family should be a list')

    font_desc_key = (
        style['font_family'], style['font_style'], style['font_stretch'],
        style['font_weight'], style['font_size'])

    if context and font_desc_key in context.pango_font_descs:
        font_desc = context.pango_font_descs[font_desc_key]
    else:
        font_desc = ffi.gc(
            pango.pango_font_description_new(),
            pango.pango_font_description_free)
        family_p, _family = unicode_to_char_p(','.join(style['font_family']))
        pango.pango_font_description_set_family(font_desc, family_p)
        pango.pango_font_description_set_style(
            font_desc, PANGO_STYLE[style['font_style']])
        pango.pango_font_description_set_stretch(
            font_desc, PANGO_STRETCH[style['font_stretch']])
        pango.pango_font_description_set_weight(
            font_desc, style['font_weight'])
        pango.pango_font_description_set_absolute_size(
            font_desc, style['font_size'] * PANGO_SCALE)

    # TODO: Freeing the AttrList will free attributes belonging to it, which
    # means we can't later free them. Make sure we never lose track of any
    # attributes we generate here.
    font_desc_attr = pango.pango_attr_font_desc_new(font_desc)

    # TODO: Copy font_features handling from line_break.py here too.

    attrs = [font_desc_attr]
    for attr in attrs:
        attr.start_index = start
        attr.end_index = end

    return attrs


def shape_string(context, style, shaping_string, pango_attrs = None):
    if context is None:
        font_map = ffi.gc(
            pangoft2.pango_ft2_font_map_new(), gobject.g_object_unref)
    else:
        font_map = context.font_config.font_map

    if context is None or context.pango_context is None:
        pango_context = ffi.gc(
            pango.pango_font_map_create_context(font_map),
            gobject.g_object_unref)
        pango.pango_context_set_round_glyph_positions(pango_context, False)

        if context is not None:
            context.pango_context = pango_context
    else:
        pango_context = context.pango_context

    # TODO: Set language on Pango attr list
    # TODO: Set Pango attributes at all
    attr_list = ffi.gc(
        pango.pango_attr_list_new(), pango.pango_attr_list_unref)

    if not pango_attrs:
        pango_attrs = pango_attrs_from_style(
            context, style, 0, len(shaping_string))

    for pango_attr in pango_attrs:
        pango.pango_attr_list_insert(attr_list, pango_attr)

    # We don't use ffi.unicode_to_char_p because we don't actually want to skip
    # nulls: that makes it hard to track which character is which.
    shaping_utf8 = shaping_string.encode()
    shaping_utf8_length = len(shaping_utf8)
    shaping_utf8_ptr = ffi.new('char[]', shaping_utf8)

    if style['direction'] == 'rtl':
        base_direction = pango.PANGO_DIRECTION_RTL
    else:
        base_direction = pango.PANGO_DIRECTION_LTR

    # We assume we can have Pango itemize all of the content at once. This may
    # lead to long pauses for many-megabyte strings, but this isn't an
    # interactive program anyway: the only concern would be memory usage.
    itemized = pango.pango_itemize_with_base_dir(
        pango_context, base_direction, shaping_utf8_ptr, 0,
        shaping_utf8_length, attr_list, ffi.NULL)
    # TODO: free itemize results

    # TODO: Set Harfbuzz buffer language and possibly(?) script
    hb_shaping_string = ffi.gc(
        harfbuzz.hb_buffer_create(), harfbuzz.hb_buffer_destroy)
    # Unfortunately, hb_buffer_add_utf8 sets the cluster values used inside
    # Harfbuzz to the *byte* position of each codepoint, not its actual
    # codepoint index. This makes it very difficult to index back into a string
    # position, so we add each codepoint manually. This may be moderately
    # inefficient, since we make an FFI call per character. Luckily, we only do
    # it once per character, as this is reused in future shaping.
    harfbuzz.hb_buffer_pre_allocate(hb_shaping_string, len(shaping_string))
    harfbuzz.hb_buffer_set_content_type(
        hb_shaping_string, harfbuzz.HB_BUFFER_CONTENT_TYPE_UNICODE)
    for cp_index, codepoint in enumerate(shaping_string):
        harfbuzz.hb_buffer_add(hb_shaping_string, ord(codepoint), cp_index)

    items = glist_to_list(itemized, 'PangoItem *')
    shaping_results = []

    end_char = 0
    for item in items:
        # Start is inclusive, end is exclusive.
        start_byte = item.offset
        end_byte = start_byte + item.length
        start_char = end_char
        end_char = start_char + item.num_chars
        # Make sure we don't go off the end of the string.
        assert end_byte <= shaping_utf8_length

        # Allocate a buffer for this item's text to pass to Harfbuzz to shape.
        item_buffer = ffi.gc(
            harfbuzz.hb_buffer_create(), harfbuzz.hb_buffer_destroy)
        harfbuzz.hb_buffer_append(
            item_buffer, hb_shaping_string, start_char, end_char)
        harfbuzz.hb_buffer_set_cluster_level(
            item_buffer, harfbuzz.HB_BUFFER_CLUSTER_LEVEL_MONOTONE_CHARACTERS)
        harfbuzz.hb_buffer_set_flags(
            item_buffer, harfbuzz.HB_BUFFER_FLAG_PRODUCE_UNSAFE_TO_CONCAT)

        # Set the buffer's direction from what Pango computed.
        if item.analysis.level % 2 == 0:
            hb_direction = harfbuzz.HB_DIRECTION_LTR
        else:
            hb_direction = harfbuzz.HB_DIRECTION_RTL
        harfbuzz.hb_buffer_set_direction(item_buffer, hb_direction)

        # Get the hb_font_t Pango would use for this item.
        hb_font = pango.pango_font_get_hb_font(item.analysis.font)

        # Ask Harfbuzz to shape the item for us. This may not fit on one line -
        # that's fine, we'll handle it later.
        harfbuzz.hb_shape(hb_font, item_buffer, ffi.NULL, 0)

        # Get the position information for the shaped glyphs.
        num_glyphs = ffi.new('unsigned int *')
        glyph_positions = harfbuzz.hb_buffer_get_glyph_positions(
            item_buffer, num_glyphs)
        num_glyphs = num_glyphs[0]
        glyph_positions = ffi.cast(
            f'hb_glyph_position_t[{num_glyphs}]', glyph_positions)

        # Get the glyph info structures for the shaped glyphs.
        glyph_infos = harfbuzz.hb_buffer_get_glyph_infos(item_buffer, ffi.NULL)
        glyph_infos = ffi.cast(f'hb_glyph_info_t[{num_glyphs}]', glyph_infos)

        shaping_results.append(ShapingResult(
            start_char, end_char, item, item_buffer, glyph_positions,
            glyph_infos, hb_font, item.analysis.font))

    return shaping_utf8_ptr, shaping_utf8_length, items, shaping_results


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
                f'{key} {value}' for key, value in features.items()).encode()
            # TODO: attributes should be freed.
            # In the meantime, keep a cache to avoid leaking too many of them.
            attr = context.font_features.setdefault(
                features, pango.pango_attr_font_features_new(features))
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
            # End-of-line not found, keep the whole text
            pass
        text, bytestring = unicode_to_char_p(text)
        self.text = bytestring.decode()
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
            if not attr_list:
                # TODO: list should be freed
                attr_list = pango.pango_attr_list_new()

            def add_attr(start, end, spacing):
                # TODO: attributes should be freed
                attr = pango.pango_attr_letter_spacing_new(spacing)
                attr.start_index, attr.end_index = start, end
                pango.pango_attr_list_change(attr_list, attr)

            if letter_spacing:
                letter_spacing = units_from_double(letter_spacing)
                add_attr(0, len(bytestring), letter_spacing)

            if word_spacing:
                space_spacing = (
                    units_from_double(word_spacing) + letter_spacing)
                position = bytestring.find(b' ')
                while position != -1:
                    add_attr(position, position + 1, space_spacing)
                    position = bytestring.find(b' ', position + 1)

            if word_breaking:
                # TODO: attributes should be freed
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

    # Step #1: Get a draft layout with the first line
    layout = None
    if max_width is not None and max_width != inf and style['font_size']:
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
    resume_index = index

    # Step #2: Don't split lines when it's not needed
    if max_width is None:
        # The first line can take all the place needed
        return first_line_metrics(
            first_line, text, layout, resume_index, space_collapse, style)
    first_line_width, _ = line_size(first_line, style)
    if index is None and first_line_width <= max_width:
        # The first line fits in the available width
        return first_line_metrics(
            first_line, text, layout, resume_index, space_collapse, style)

    # Step #3: Try to put the first word of the second line on the first line
    # https://mail.gnome.org/archives/gtk-i18n-list/2013-September/msg00006
    # is a good thread related to this problem.
    first_line_text = text.encode()[:index].decode()
    first_line_fits = (
        first_line_width <= max_width or
        ' ' in first_line_text.strip() or
        can_break_text(first_line_text.strip(), style['lang']))
    if first_line_fits:
        # The first line fits but may have been cut too early by Pango
        second_line_text = text.encode()[index:].decode()
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
                resume_index = len(new_first_line_text.encode()) + 1
                return first_line_metrics(
                    first_line, text, layout, resume_index, space_collapse,
                    style)
            elif index:
                # Text may have been split elsewhere by Pango earlier
                resume_index = index
            else:
                # Second line is None
                resume_index = first_line.length + 1
                if resume_index >= len(text.encode()):
                    resume_index = None
    elif first_line_text:
        # We found something on the first line but we did not find a word on
        # the next line, no need to hyphenate, we can keep the current layout
        return first_line_metrics(
            first_line, text, layout, resume_index, space_collapse, style)

    # Step #4: Try to hyphenate
    hyphens = style['hyphens']
    lang = style['lang'] and pyphen.language_fallback(style['lang'])
    total, left, right = style['hyphenate_limit_chars']
    hyphenated = False
    soft_hyphen = '\xad'

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
                        max_width * style['hyphenate_limit_zone'].value / 100)
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
                    resume_index = len((f'{first_line_text} ').encode())
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
                    resume_index = len(new_first_line_text.encode())
                    if text[len(new_first_line_text)] == soft_hyphen:
                        # Recreate the layout with no max_width to be sure that
                        # we don't break before the soft hyphen
                        pango.pango_layout_set_width(
                            layout.layout, units_from_double(-1))
                        resume_index += len(soft_hyphen.encode())
                    break

            if not hyphenated and not first_line_text:
                # Recreate the layout with no max_width to be sure that
                # we don't break before or inside the hyphenate character
                hyphenated = True
                layout.set_text(hyphenated_first_line_text)
                pango.pango_layout_set_width(
                    layout.layout, units_from_double(-1))
                first_line, index = layout.get_first_line()
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
        pango.pango_layout_set_width(
            layout.layout, units_from_double(-1))
        first_line, index = layout.get_first_line()
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
        pango.pango_layout_set_width(
            layout.layout, units_from_double(max_width))
        pango.pango_layout_set_wrap(
            layout.layout, PANGO_WRAP_MODE['WRAP_CHAR'])
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
