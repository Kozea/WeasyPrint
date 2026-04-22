"""Draw text."""

from math import cos, inf, radians, sin
from unicodedata import category

from ..matrix import Matrix
from .bounding_box import extend_bounding_box
from .utils import normalize, size


class TextBox:
    """Dummy text box used to draw text."""
    def __init__(self, pango_layout, style):
        self.pango_layout = pango_layout
        self.style = style

    @property
    def text(self):
        return self.pango_layout.text


class Style(dict):
    """Dummy class to store dict."""


def is_positioned(positions):
    """Return whether a list of positions includes per-character values."""
    return any(len(position) > 1 for position in positions)


def apply_unicode_bidi(text, direction, unicode_bidi):
    """Add Unicode bidi controls matching CSS unicode-bidi."""
    if not text:
        return text
    direction = 'rtl' if direction == 'rtl' else 'ltr'
    unicode_bidi = (unicode_bidi or 'normal').strip()
    if unicode_bidi == 'normal':
        return text

    controls = {
        ('embed', 'ltr'): ('\u202a', '\u202c'),
        ('embed', 'rtl'): ('\u202b', '\u202c'),
        ('isolate', 'ltr'): ('\u2066', '\u2069'),
        ('isolate', 'rtl'): ('\u2067', '\u2069'),
        ('bidi-override', 'ltr'): ('\u202d', '\u202c'),
        ('bidi-override', 'rtl'): ('\u202e', '\u202c'),
        ('isolate-override', 'ltr'): ('\u2068\u202d', '\u202c\u2069'),
        ('isolate-override', 'rtl'): ('\u2068\u202e', '\u202c\u2069'),
        ('plaintext', 'ltr'): ('\u2068', '\u2069'),
        ('plaintext', 'rtl'): ('\u2068', '\u2069'),
    }
    start, end = controls.get((unicode_bidi, direction), ('', ''))
    return f'{start}{text}{end}'


def _is_hangul_leading_jamo(character):
    return '\u1100' <= character <= '\u115f' or '\ua960' <= character <= '\ua97c'


def _is_hangul_vowel_jamo(character):
    return '\u1160' <= character <= '\u11a7' or '\ud7b0' <= character <= '\ud7c6'


def _is_hangul_trailing_jamo(character):
    return '\u11a8' <= character <= '\u11ff' or '\ud7cb' <= character <= '\ud7fb'


def _is_virama(character):
    return character in {
        '\u094d',  # Devanagari
        '\u09cd',  # Bengali
        '\u0a4d',  # Gurmukhi
        '\u0acd',  # Gujarati
        '\u0b4d',  # Oriya
        '\u0bcd',  # Tamil
        '\u0c4d',  # Telugu
        '\u0ccd',  # Kannada
        '\u0d4d',  # Malayalam
        '\u0dca',  # Sinhala
        '\u1039',  # Myanmar
    }


def _byte_offsets(text):
    """Return UTF-8 byte offsets for every character boundary."""
    offsets, offset = [], 0
    for character in text:
        offsets.append(offset)
        offset += len(character.encode())
    offsets.append(offset)
    return offsets


def _is_bidi_control(character):
    """Return whether ``character`` is discarded by bidi layout."""
    return character in (
        '\u061c',  # ARABIC LETTER MARK
        '\u200e',  # LEFT-TO-RIGHT MARK
        '\u200f',  # RIGHT-TO-LEFT MARK
        '\u202a',  # LEFT-TO-RIGHT EMBEDDING
        '\u202b',  # RIGHT-TO-LEFT EMBEDDING
        '\u202c',  # POP DIRECTIONAL FORMATTING
        '\u202d',  # LEFT-TO-RIGHT OVERRIDE
        '\u202e',  # RIGHT-TO-LEFT OVERRIDE
        '\u2066',  # LEFT-TO-RIGHT ISOLATE
        '\u2067',  # RIGHT-TO-LEFT ISOLATE
        '\u2068',  # FIRST STRONG ISOLATE
        '\u2069',  # POP DIRECTIONAL ISOLATE
    )


def _addressable_indexes(text):
    """Return SVG text-position indexes for every character boundary."""
    indexes, index = [], 0
    for character in text:
        indexes.append(index)
        if not _is_bidi_control(character):
            index += 2 if ord(character) > 0xffff else 1
    indexes.append(index)
    return indexes


def _grapheme_spans(text):
    """Return simple grapheme-like spans as UTF-8 byte offsets."""
    offsets = _byte_offsets(text)
    if not text:
        return []

    spans, start = [], 0
    for index, character in enumerate(text[1:], 1):
        previous = text[index - 1]
        attach = (
            category(character).startswith('M') or
            character in ('\u200c', '\u200d') or
            previous in ('\u200c', '\u200d') or
            _is_virama(character) or
            _is_virama(previous) or
            (
                _is_hangul_vowel_jamo(character) and
                (_is_hangul_leading_jamo(previous) or
                 _is_hangul_vowel_jamo(previous))) or
            (
                _is_hangul_trailing_jamo(character) and
                (_is_hangul_vowel_jamo(previous) or
                 _is_hangul_trailing_jamo(previous))))
        if not attach:
            spans.append((offsets[start], offsets[index]))
            start = index
    spans.append((offsets[start], offsets[-1]))
    return spans


def _expand_to_graphemes(start, end, grapheme_spans):
    """Expand a UTF-8 span to the grapheme spans it intersects."""
    spans = [
        (span_start, span_end) for span_start, span_end in grapheme_spans
        if span_start < end and start < span_end]
    if spans:
        return min(span[0] for span in spans), max(span[1] for span in spans)
    return start, end


def _positioned_clusters(layout, text):
    """Return Pango clusters in visual order."""
    from ..text.ffi import FROM_UNITS, ffi, pango

    encoded = text.encode()
    offsets = _byte_offsets(text)
    char_indexes = {offset: index for index, offset in enumerate(offsets)}
    addressable_indexes = _addressable_indexes(text)
    grapheme_spans = _grapheme_spans(text)
    clusters = []

    first_line, _ = layout.get_first_line()
    run = first_line.runs[0]
    while run != ffi.NULL:
        glyph_item = run.data
        run = run.next
        glyph_string = glyph_item.glyphs
        glyphs_info = glyph_string.glyphs
        number_of_glyphs = glyph_string.num_glyphs
        offset = glyph_item.item.offset
        run_end = offset + glyph_item.item.length

        utf8_positions = [
            offset + glyph_string.log_clusters[i]
            for i in range(number_of_glyphs)]
        if glyph_item.item.analysis.level % 2:
            utf8_positions.insert(0, run_end)
        else:
            utf8_positions.append(run_end)

        start_index = 0
        for index in range(1, number_of_glyphs + 1):
            if (index == number_of_glyphs or
                    glyphs_info[index].attr.is_cluster_start):
                glyph_indexes = range(start_index, index)
                visible = any(
                    glyphs_info[i].glyph != pango.PANGO_GLYPH_EMPTY
                    for i in glyph_indexes)
                boundaries = [
                    sorted(utf8_positions[i:i + 2])
                    for i in glyph_indexes]
                start = min(boundary[0] for boundary in boundaries)
                end = max(boundary[1] for boundary in boundaries)
                start, end = _expand_to_graphemes(
                    start, end, grapheme_spans)
                if start != end:
                    start_char_index = char_indexes[start]
                    end_char_index = char_indexes[end]
                    cluster_text = encoded[start:end].decode()
                    width = sum(
                        glyphs_info[i].geometry.width * FROM_UNITS
                        for i in glyph_indexes)
                    glyph_ranges = ((glyph_item, start_index, index),)
                    cluster = (
                        start, end, start_char_index, end_char_index,
                        addressable_indexes[start_char_index],
                        addressable_indexes[end_char_index],
                        visible, cluster_text, glyph_ranges, width)
                    if (clusters and clusters[-1][0] == start and
                            clusters[-1][1] == end):
                        previous = clusters[-1]
                        clusters[-1] = (
                            *previous[:6], previous[6] or visible,
                            previous[7], (*previous[8], *glyph_ranges),
                            previous[9] + width)
                    else:
                        clusters.append(cluster)
                start_index = index

    return clusters


def _positions_sum(positions, start, end):
    """Return sum of positions between start and end indexes."""
    return sum(positions[index] for index in range(start, min(end, len(positions))))


def _lines(text, style, context, max_width):
    """Yield wrapped Pango layouts for ``text``."""
    from ..text.line_break import split_first_line

    while text:
        layout, _, resume_index, width, height, baseline = split_first_line(
            text, style, context, max_width, 0)
        yield layout, width, height, baseline
        if resume_index is None:
            break
        next_text = text.encode()[resume_index:].decode()
        if next_text == text:
            break
        text = next_text


def text(svg, node, font_size):
    """Draw text node."""
    from ..css.properties import INITIAL_VALUES
    from ..draw.text import draw_emojis, draw_first_line, draw_first_line_glyphs
    from ..text.line_break import split_first_line

    # TODO: use real computed values
    style = Style()
    style.update(INITIAL_VALUES)
    style.font_config = svg.font_config
    style['font_family'] = [
        font.strip('"\'') for font in
        node.get('font-family', 'sans-serif').split(',')]
    style['font_style'] = node.get('font-style', 'normal')
    style['font_weight'] = node.get('font-weight', 400)
    style['font_size'] = font_size
    if node.get('direction') in ('ltr', 'rtl'):
        style['direction'] = node.get('direction')
    if style['font_weight'] == 'normal':
        style['font_weight'] = 400
    elif style['font_weight'] == 'bold':
        style['font_weight'] = 700
    else:
        try:
            style['font_weight'] = int(style['font_weight'])
        except ValueError:
            style['font_weight'] = 400

    # Get rotations and translations
    x, y, dx, dy, rotate = [], [], [], [], [0]
    if 'x' in node.attrib:
        x = [size(i, font_size, svg.inner_width)
             for i in normalize(node.attrib['x']).strip().split(' ')]
    if 'y' in node.attrib:
        y = [size(i, font_size, svg.inner_height)
             for i in normalize(node.attrib['y']).strip().split(' ')]
    if 'dx' in node.attrib:
        dx = [size(i, font_size, svg.inner_width)
              for i in normalize(node.attrib['dx']).strip().split(' ')]
    if 'dy' in node.attrib:
        dy = [size(i, font_size, svg.inner_height)
              for i in normalize(node.attrib['dy']).strip().split(' ')]
    if 'rotate' in node.attrib:
        rotate = [radians(float(i)) if i else 0
                  for i in normalize(node.attrib['rotate']).strip().split(' ')]
    last_r = rotate[-1]

    # Return early when there’s no text
    if not node.text:
        x = x[0] if x else svg.cursor_position[0]
        y = y[0] if y else svg.cursor_position[1]
        dx = dx[0] if dx else 0
        dy = dy[0] if dy else 0
        svg.cursor_position = (x + dx, y + dy)
        return

    letter_spacing = svg.length(node.get('letter-spacing'), font_size)
    text_length = svg.length(node.get('textLength'), font_size)
    writing_mode = node.get('writing-mode')
    vertical = writing_mode in ('vertical-rl', 'vertical-lr')
    inline_size = node.get('inline-size')
    inline_size = (
        size(inline_size, font_size, svg.inner_width)
        if inline_size and inline_size != 'auto' else None)
    use_unicode_bidi = not (
        vertical or is_positioned((x, y, dx, dy, rotate)) or
        letter_spacing or text_length)
    text = (
        apply_unicode_bidi(node.text, style['direction'], node.get('unicode-bidi'))
        if use_unicode_bidi else node.text)
    layout, _, _, width, height, baseline = split_first_line(
        text, style, svg.context, inf, 0)

    scale_x = 1
    if text_length and node.text:
        # calculate the number of spaces to be considered for the text
        spaces_count = len(node.text) - 1
        if normalize(node.attrib.get('lengthAdjust')) == 'spacingAndGlyphs':
            # scale letter_spacing up/down to textLength
            width_with_spacing = width + spaces_count * letter_spacing
            letter_spacing *= text_length / width_with_spacing
            # calculate the glyphs scaling factor by:
            # - deducting the scaled letter_spacing from textLength
            # - dividing the calculated value by the original width
            spaceless_text_length = text_length - spaces_count * letter_spacing
            scale_x = spaceless_text_length / width
        elif spaces_count:
            # adjust letter spacing to fit textLength
            letter_spacing = (text_length - width) / spaces_count
        width = text_length

    # TODO: use real values
    ascent, descent = font_size * .8, font_size * .2

    # Align text box vertically
    # TODO: This is a hack. Other baseline alignment tags are not supported.
    # See https://www.w3.org/TR/SVG2/text.html#TextPropertiesSVG
    y_align = 0
    display_anchor = node.get('display-anchor')
    alignment_baseline = node.get(
        'dominant-baseline', node.get('alignment-baseline'))
    if display_anchor == 'middle':
        y_align = -height / 2
    elif display_anchor == 'top':
        pass
    elif display_anchor == 'bottom':
        y_align = -height
    elif alignment_baseline in ('central', 'middle'):
        # TODO: This is wrong, we use font top-to-bottom
        y_align = (ascent + descent) / 2 - descent
    elif alignment_baseline in (
            'text-before-edge', 'before_edge', 'top', 'hanging', 'text-top'):
        y_align = ascent
    elif alignment_baseline in (
            'text-after-edge', 'after_edge', 'bottom', 'text-bottom'):
        y_align = -descent

    svg.stream.push_state()
    svg.set_graphical_state(node, font_size, text=True)
    svg.stream.begin_text()
    emoji_lines = []

    def draw_text(
            layout, width, height, baseline, position, spacing=False,
            layout_style=style, glyph_ranges=None):
        x, y, dx, dy, r = position
        if x is not None:
            svg.cursor_d_position[0] = 0
        if y is not None:
            svg.cursor_d_position[1] = 0
        svg.cursor_d_position[0] += dx or 0
        svg.cursor_d_position[1] += dy or 0
        x = svg.cursor_position[0] if x is None else x
        y = svg.cursor_position[1] if y is None else y
        width *= scale_x
        if spacing:
            x += letter_spacing
        svg.cursor_position = x + width, y

        x_position = x + svg.cursor_d_position[0]
        y_position = y + svg.cursor_d_position[1] + y_align
        angle = last_r if r is None else r
        points = (
            (x_position, y_position - baseline),
            (x_position + width, y_position - baseline + height))
        # TODO: Use ink extents instead of logical from line_break.line_size().
        node.text_bounding_box = extend_bounding_box(
            node.text_bounding_box, points)

        svg.fill_stroke(node, font_size, text=True)
        matrix = Matrix(a=scale_x, d=-1, e=x_position, f=y_position)
        if angle:
            a, c = cos(angle), sin(angle)
            matrix = Matrix(a, -c, c, a) @ matrix
        if glyph_ranges is None:
            layout.reactivate(layout_style)
            emojis = draw_first_line(
                svg.stream, TextBox(layout, style), 'none', 'none', matrix)
        else:
            emojis = draw_first_line_glyphs(
                svg.stream, TextBox(layout, style), glyph_ranges, matrix)
        emoji_lines.append((x, y, emojis))

    def draw_wrapped_text(position):
        x, y, dx, dy, r = position
        first_x, first_y = x, y
        if x is not None:
            svg.cursor_d_position[0] = 0
        if y is not None:
            svg.cursor_d_position[1] = 0
        svg.cursor_d_position[0] += dx or 0
        svg.cursor_d_position[1] += dy or 0
        x = svg.cursor_position[0] if x is None else x
        y = svg.cursor_position[1] if y is None else y

        right_to_left = (
            style['direction'] == 'rtl' and
            node.get('text-anchor') in (None, 'start'))
        line_y = y
        max_y = y
        for line_layout, line_width, line_height, line_baseline in _lines(
                text, style, svg.context, inline_size):
            line_x = x
            if right_to_left:
                line_x += inline_size - line_width
            draw_text(
                line_layout, line_width, line_height, line_baseline,
                (line_x, line_y, dx if line_y == y else 0, 0, r))
            max_y = max(max_y, line_y - line_baseline + line_height)
            line_y += line_height

        if right_to_left:
            x_position = x + svg.cursor_d_position[0]
            y_position = y + svg.cursor_d_position[1] + y_align
            node.text_bounding_box = extend_bounding_box(
                node.text_bounding_box,
                ((x_position, y_position), (x_position + inline_size, max_y)))
        svg.cursor_position = (
            first_x if first_x is not None else x,
            first_y if first_y is not None else line_y)

    def draw_vertical_text(position):
        x, y, dx, dy, r = position
        if x is not None:
            svg.cursor_d_position[0] = 0
        if y is not None:
            svg.cursor_d_position[1] = 0
        svg.cursor_d_position[0] += dx or 0
        svg.cursor_d_position[1] += dy or 0
        x = svg.cursor_position[0] if x is None else x
        y = svg.cursor_position[1] if y is None else y

        x_position = x + svg.cursor_d_position[0]
        y_position = y + svg.cursor_d_position[1]
        angle = last_r if r is None else r
        vertical_inline_size = inline_size if inline_size is not None else inf
        column_step = font_size
        column_x = x_position
        current_y = y_position
        column_height = 0
        min_x, max_x = x_position, x_position + column_step
        max_y = y_position

        layout.reactivate(style)
        clusters = _positioned_clusters(layout, text)
        svg.fill_stroke(node, font_size, text=True)
        for cluster in clusters:
            (
                _, _, _, _, _, _, visible, _, glyph_ranges,
                cluster_advance) = cluster
            if not visible:
                continue
            if (vertical_inline_size != inf and column_height and
                    column_height + cluster_advance > vertical_inline_size):
                column_x += (
                    -column_step if writing_mode == 'vertical-rl'
                    else column_step)
                current_y = y_position
                column_height = 0

            matrix = Matrix(d=-1, e=column_x, f=current_y + baseline)
            if angle:
                a, c = cos(angle), sin(angle)
                matrix = Matrix(a, -c, c, a) @ matrix
            emojis = draw_first_line_glyphs(
                svg.stream, TextBox(layout, style), glyph_ranges, matrix)
            emoji_lines.append((column_x, current_y + baseline, emojis))

            min_x = min(min_x, column_x)
            max_x = max(max_x, column_x + column_step)
            max_y = max(max_y, current_y + cluster_advance)
            current_y += cluster_advance
            column_height += cluster_advance

        layout.deactivate()
        node.text_bounding_box = extend_bounding_box(
            node.text_bounding_box, ((min_x, y_position), (max_x, max_y)))
        svg.cursor_position = column_x, current_y

    if vertical:
        position = [
            positions[0] if positions else None
            for positions in (x, y, dx, dy, rotate)]
        draw_vertical_text(position)
    elif inline_size and not (
            is_positioned((x, y, dx, dy, rotate)) or
            letter_spacing or text_length):
        position = [
            positions[0] if positions else None
            for positions in (x, y, dx, dy, rotate)]
        draw_wrapped_text(position)
    elif not (is_positioned((x, y, dx, dy, rotate)) or letter_spacing or text_length):
        position = [
            positions[0] if positions else None
            for positions in (x, y, dx, dy, rotate)]
        draw_text(layout, width, height, baseline, position)
    else:
        layout.reactivate(style)
        clusters = _positioned_clusters(layout, text)

        # Draw visible typographic clusters in visual order. Pango has already
        # shaped the layout through HarfBuzz, so these clusters match the glyph
        # runs used for PDF text drawing.
        pending_dx = pending_dy = 0
        visible_index = 0
        for cluster in clusters:
            (
                _, _, _, _, position_index, end_position_index, visible, _,
                glyph_ranges, cluster_width) = cluster
            if not visible:
                pending_dx += _positions_sum(
                    dx, position_index, end_position_index)
                pending_dy += _positions_sum(
                    dy, position_index, end_position_index)
                continue

            position = []
            for positions in (x, y):
                if len(positions) == 1:
                    position.append(positions[0] if visible_index == 0 else None)
                else:
                    position.append(
                        positions[position_index]
                        if position_index < len(positions) else None)
            for positions, pending in ((dx, pending_dx), (dy, pending_dy)):
                if len(positions) == 1:
                    position.append(positions[0] if visible_index == 0 else None)
                else:
                    value = (
                        positions[position_index]
                        if position_index < len(positions) else 0)
                    position.append(value + pending)
            if len(rotate) == 1:
                position.append(rotate[0] if visible_index == 0 else None)
            else:
                position.append(
                    rotate[position_index]
                    if position_index < len(rotate) else None)

            pending_dx = _positions_sum(
                dx, position_index + 1, end_position_index)
            pending_dy = _positions_sum(
                dy, position_index + 1, end_position_index)
            draw_text(
                layout, cluster_width, height, baseline, position,
                spacing=bool(visible_index), glyph_ranges=glyph_ranges)
            visible_index += 1
        layout.deactivate()

    svg.stream.end_text()
    svg.stream.pop_state()

    for x, y, emojis in emoji_lines:
        draw_emojis(svg.stream, style, x, y, emojis)
