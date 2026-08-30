"""Draw text."""

from io import BytesIO
from xml.etree import ElementTree

from PIL import Image

from ..images import RasterImage, SVGImage
from ..logger import LOGGER
from ..matrix import Matrix
from ..text.ffi import FROM_UNITS, TO_UNITS, ffi, pango
from ..text.fonts import get_hb_object_data
from ..text.line_break import Layout, get_last_word_end
from .border import draw_line
from .color import get_color


def draw_text(stream, textbox, offset_x, text_overflow, block_ellipsis):
    """Draw a textbox to a pydyf stream."""
    from ..layout.percent import percentage

    # Pango crashes with font-size: 0.
    assert textbox.style['font_size']

    # Don’t draw invisible textboxes.
    if textbox.style['visibility'] != 'visible':
        return

    # Draw underline and overline.
    text_decoration_values = textbox.style['text_decoration_line']
    text_decoration_color = get_color(textbox.style, 'text_decoration_color')
    if 'underline' in text_decoration_values or 'overline' in text_decoration_values:
        if textbox.style['text_decoration_thickness'] in ('auto', 'from-font'):
            thickness = textbox.pango_layout.underline_thickness
        else:
            thickness = percentage(
                textbox.style['text_decoration_thickness'], textbox.style,
                textbox.style['font_size'])
    if 'overline' in text_decoration_values:
        offset_y = (
            textbox.baseline - textbox.pango_layout.ascent + thickness / 2)
        draw_text_decoration(
            stream, textbox, offset_x, offset_y, thickness,
            text_decoration_color)
    if 'underline' in text_decoration_values:
        if textbox.style['text_underline_offset'] == 'auto':
            underline_offset = - textbox.pango_layout.underline_position
        else:
            underline_offset = percentage(
                textbox.style['text_underline_offset'], textbox.style,
                textbox.style['font_size'])
        offset_y = textbox.baseline + underline_offset + thickness / 2
        draw_text_decoration(
            stream, textbox, offset_x, offset_y, thickness,
            text_decoration_color)

    # Draw emphasis marks.
    x, y = textbox.position_x, textbox.position_y + textbox.baseline
    textbox.pango_layout.reactivate(textbox.style)
    draw_text_emphasis(stream, textbox, x, y)

    # Draw text.
    stream.set_color(textbox.style['color'])
    stream.begin_text()
    emojis = draw_first_line(
        stream, textbox, text_overflow, block_ellipsis, Matrix(d=-1, e=x, f=y))
    stream.end_text()

    # Draw emojis.
    draw_emojis(stream, textbox.style, x, y, emojis)

    # Draw line through.
    if 'line-through' in text_decoration_values:
        thickness = textbox.pango_layout.strikethrough_thickness
        offset_y = textbox.baseline - textbox.pango_layout.strikethrough_position
        draw_text_decoration(
            stream, textbox, offset_x, offset_y, thickness, text_decoration_color)
    textbox.pango_layout.deactivate()


def draw_emojis(stream, style, x, y, emojis):
    """Draw list of emojis."""
    font_size = style['font_size']
    for image, font, a, d, e, f in emojis:
        with stream.stacked():
            stream.transform(a=a, d=d, e=x + e * font_size, f=y + f)
            image.draw(stream, font_size, font_size, style)


def draw_first_line(stream, textbox, text_overflow, block_ellipsis, matrix):
    """Draw the given ``textbox`` line to the document ``stream``."""
    # Don’t draw lines with only invisible characters.
    if not textbox.text.strip():
        return []

    if textbox.style['font_size'] < 1e-6:  # default float precision used by pydyf
        return []

    pango.pango_layout_set_single_paragraph_mode(textbox.pango_layout.layout, True)

    if text_overflow == 'ellipsis' or block_ellipsis != 'none':
        assert textbox.pango_layout.max_width is not None
        max_width = textbox.pango_layout.max_width
        pango.pango_layout_set_width(
            textbox.pango_layout.layout, int(max_width * TO_UNITS))
        if text_overflow == 'ellipsis':
            pango.pango_layout_set_ellipsize(
                textbox.pango_layout.layout, pango.PANGO_ELLIPSIZE_END)
        else:
            if block_ellipsis == 'auto':
                ellipsis = '…'
            else:
                assert block_ellipsis[0] == 'string'
                ellipsis = block_ellipsis[1]

            # Remove last word if hyphenated.
            new_text = textbox.pango_layout.text
            if new_text.endswith(textbox.style['hyphenate_character']):
                last_word_end = get_last_word_end(
                    new_text[:-len(textbox.style['hyphenate_character'])],
                    textbox.style['lang'])
                if last_word_end:
                    new_text = new_text[:last_word_end]

            textbox.pango_layout.set_text(new_text + ellipsis)

    first_line, index = textbox.pango_layout.get_first_line()

    if block_ellipsis != 'none':
        while index:
            last_word_end = get_last_word_end(
                textbox.pango_layout.text[:-len(ellipsis)],
                textbox.style['lang'])
            if last_word_end is None:
                break
            new_text = textbox.pango_layout.text[:last_word_end]
            textbox.pango_layout.set_text(new_text + ellipsis)
            first_line, index = textbox.pango_layout.get_first_line()

    stream.set_text_matrix(*matrix.values)
    previous_pango_font = None
    string = ''
    x_advance = 0
    emojis = []
    run = first_line.runs[0]
    while run != ffi.NULL:
        # Get Pango objects.
        glyph_item = run.data
        run = run.next
        glyph_string = glyph_item.glyphs
        glyphs_info = glyph_string.glyphs
        num_glyphs = glyph_string.num_glyphs
        clusters = glyph_string.log_clusters
        utf8_text = None

        pango_font = glyph_item.item.analysis.font
        if pango_font != previous_pango_font:
            # Add font file content and get font size.
            previous_pango_font = pango_font
            font, font_size = stream.add_font(pango_font)

            # Workaround for https://gitlab.gnome.org/GNOME/pango/-/issues/530.
            # This is also needed by raster emoji fonts, see #2800.
            if pango.pango_version() < 14802 or font.png:
                font_size = textbox.style['font_size']

            # Go through the run glyphs.
            if string:
                stream.show_text(string)
            string = ''
            stream.set_font_size(font.hash, 1 if font.bitmap else font_size)
        string += '<'
        for i, glyph_info in enumerate(glyphs_info[0:num_glyphs]):
            glyph_id = glyph_info.glyph
            width = glyph_info.geometry.width

            # Display zero-width empty glyph.
            if glyph_id == pango.PANGO_GLYPH_EMPTY:
                string += f'>{-width / font_size}<'
                continue

            # Display .notdef and log warning for missing glyphs.
            if glyph_id & pango.PANGO_GLYPH_UNKNOWN_FLAG:
                codepoint = glyph_id - pango.PANGO_GLYPH_UNKNOWN_FLAG
                LOGGER.warning(
                    '.notdef glyph rendered for Unicode string unsupported by fonts: '
                    '"%s" (U+%04X)', chr(codepoint), codepoint)
                glyph_id = font.get_unused_glyph_id(codepoint)
                font.widths[glyph_id] = round(width * 1000 * FROM_UNITS / font_size)
                if 0 not in font.widths:
                    # "width" is actually Pango’s get_approximate_char_width. Force
                    # .notdef’s to use this width, even if it’s not the right, as we
                    # want to keep Pango’s layout for next glyphs.
                    font.widths[0] = font.widths[glyph_id]

            # Create mapping between glyphs and Unicode codepoints.
            if glyph_id not in font.to_unicode:
                # Get positions of the glyph in the UTF-8 string.
                offset = glyph_item.item.offset
                t1 = clusters[i]
                if glyph_item.item.analysis.level % 2:  # rtl
                    t2 = glyph_item.item.length if i == 0 else clusters[i-1]
                else:
                    t2 = glyph_item.item.length if i == num_glyphs-1 else clusters[i+1]
                utf8_text = utf8_text or textbox.pango_layout.text.encode()
                font.to_unicode[glyph_id] = utf8_text[offset+t1:offset+t2].decode()

            # Set horizontal and vertical offsets.
            offset = glyph_info.geometry.x_offset / font_size
            rise = glyph_info.geometry.y_offset / 1000
            if rise:
                if string[-1] == '<':
                    string = string[:-1]
                else:
                    string += '>'
                if string:
                    stream.show_text(string)
                stream.set_text_rise(-rise)
                string = ''
                if offset:
                    string = f'{-offset}'
                string += f'<{glyph_id:02x}>' if font.bitmap else f'<{glyph_id:04x}>'
                stream.show_text(string)
                stream.set_text_rise(0)
                string = '<'
            else:
                if offset:
                    string += f'>{-offset}<'
                string += f'{glyph_id:02x}' if font.bitmap else f'{glyph_id:04x}'

            # Get glyph logical widths.
            if glyph_id in font.widths:
                logical_width = font.widths[glyph_id]
            else:
                pango.pango_font_get_glyph_extents(
                    pango_font, glyph_id, stream.ink_rect, stream.logical_rect)
                logical_width = font.widths[glyph_id] = round(
                    stream.logical_rect.width * 1000 * FROM_UNITS / font_size)

            # Set kerning, word spacing, letter spacing.
            kerning = logical_width + offset - width * 1000 * FROM_UNITS / font_size
            if kerning:
                string += f'>{int(kerning)}<'

            # Create list of emojis.
            if font.svg:
                svg_data = get_hb_object_data(font.hb_face, 'svg', glyph_id)
                if svg_data:
                    # Do as explained in specification
                    # https://learn.microsoft.com/typography/opentype/spec/svg
                    tree = ElementTree.fromstring(svg_data)
                    if tree.get('id') != f'glyph{glyph_id}':
                        defs = ElementTree.Element('defs')
                        for child in list(tree):
                            defs.append(child)
                            tree.remove(child)
                        tree.append(defs)
                        ElementTree.SubElement(
                            tree, 'use', attrib={'href': f'#glyph{glyph_id}'})
                    if 'viewBox' not in tree.attrib:
                        tree.attrib['viewBox'] = f'0 0 {font.upem} {font.upem}'
                    image = SVGImage(tree, None, None, None)
                    a = d = 1
                    emojis.append([image, font, a, d, x_advance, 0])
            elif font.png:
                png_data = get_hb_object_data(font.hb_font, 'png', glyph_id)
                if png_data:
                    pillow_image = Image.open(BytesIO(png_data))
                    image_id = f'{font.hash}{glyph_id}'
                    image = RasterImage(pillow_image, image_id, png_data)
                    d = logical_width / 1000
                    a = pillow_image.width / pillow_image.height * d
                    pango.pango_font_get_glyph_extents(
                        pango_font, glyph_id, stream.ink_rect,
                        stream.logical_rect)
                    f = -stream.logical_rect.y
                    f = f * FROM_UNITS / font_size - font_size
                    emojis.append([image, font, a, d, x_advance, f])
            elif font.colr:
                svg_data = get_hb_object_data(font.hb_font, 'colr', glyph_id)
                if svg_data:
                    tree = ElementTree.fromstring(svg_data)
                    image = SVGImage(tree, None, None, None)
                    a = d = 1
                    e = x_advance - kerning
                    emojis.append([image, font, a, d, e, -textbox.baseline])

            x_advance += (logical_width + offset - kerning) / 1000

        # Close the last glyphs list, remove if empty.
        if string[-1] == '<':
            string = string[:-1]
        else:
            string += '>'

    # Draw text.
    stream.show_text(string)

    return emojis


def draw_text_decoration(stream, textbox, offset_x, offset_y, thickness, color):
    """Draw text-decoration of ``textbox`` to a ``pdf.stream.Stream``."""
    draw_line(
        stream, textbox.position_x, textbox.position_y + offset_y,
        textbox.position_x + textbox.width, textbox.position_y + offset_y,
        thickness, textbox.style['text_decoration_style'], color, offset_x)


# Maps (fill, shape) keyword pairs to Unicode codepoints, as defined in
# https://drafts.csswg.org/css-text-decor-4/#text-emphasis-style
EMPHASIS_MARKS = {
    ('filled', 'dot'): '•',
    ('open', 'dot'): '◦',
    ('filled', 'circle'): '●',
    ('open', 'circle'): '○',
    ('filled', 'double-circle'): '◉',
    ('open', 'double-circle'): '◎',
    ('filled', 'triangle'): '▲',
    ('open', 'triangle'): '△',
    ('filled', 'sesame'): '﹅',
    ('open', 'sesame'): '﹆',
}


def draw_text_emphasis(stream, textbox, x, y):
    """Draw emphasis marks of ``textbox`` to a ``pdf.stream.Stream``.

    Each mark is drawn above (or below) the center of the corresponding
    typographic character unit, at half the font size.

    """
    style = textbox.style
    emphasis_style = style['text_emphasis_style']
    if emphasis_style is None or emphasis_style == 'none':
        return
    if emphasis_style[0] == 'custom':
        mark = emphasis_style[1]
        if len(mark) > 1:
            LOGGER.warning(
                'Only one character can be used as custom text emphasis '
                'mark: "%s" is ignored, first character is used', mark)
            mark = mark[0]
    else:
        fill, shape = emphasis_style
        mark = EMPHASIS_MARKS[(fill, shape)]

    vertical, horizontal = style['text_emphasis_position'].split()
    if horizontal != 'right':
        LOGGER.warning(
            'Only "right" text-emphasis-position horizontal keyword is '
            'supported, "%s" is ignored', horizontal)

    # Ruby position: above the ascent or below the descent, half font size.
    font_size = style['font_size']
    mark_size = font_size / 2
    ascent = textbox.pango_layout.ascent
    if vertical == 'over':
        offset_y = -ascent - mark_size / 2
    else:
        # Descent from the bottom of the textbox content area.
        offset_y = textbox.height - ascent + mark_size / 2

    color = get_color(style, 'text_emphasis_color')

    # Layout for the mark, so that Pango can select a font that has a glyph
    # for it (the text font may not have one, e.g. for sesames).
    mark_layout = Layout(style)
    mark_layout.set_text(mark)
    mark_line, _ = mark_layout.get_first_line()
    mark_run = mark_line.runs[0]
    if mark_run == ffi.NULL:
        LOGGER.warning(
            'No glyph found for text emphasis mark "%s"', mark)
        return
    mark_glyph_item = mark_run.data
    mark_pango_font = mark_glyph_item.item.analysis.font
    mark_font, _ = stream.add_font(mark_pango_font)
    mark_glyph = mark_glyph_item.glyphs.glyphs[0].glyph

    # Iterate over runs to draw a mark above each grapheme cluster.
    first_line, _ = textbox.pango_layout.get_first_line()
    run = first_line.runs[0]
    while run != ffi.NULL:
        glyph_item = run.data
        run = run.next
        glyph_string = glyph_item.glyphs
        num_glyphs = glyph_string.num_glyphs
        clusters = glyph_string.log_clusters

        # Draw one mark per cluster, using the first cluster that maps to it.
        item_offset = glyph_item.item.offset
        item_length = glyph_item.item.length
        utf8_text = textbox.pango_layout.text.encode()
        for i in range(num_glyphs):
            glyph_info = glyph_string.glyphs[i]
            glyph_id = glyph_info.glyph

            # Advance by the width of every glyph, cluster-start or not.
            cluster_width = glyph_info.geometry.width * FROM_UNITS

            cluster_start = not i or clusters[i] != clusters[i - 1]
            if not cluster_start:
                x += cluster_width
                continue

            if glyph_id == pango.PANGO_GLYPH_EMPTY:
                x += cluster_width
                continue

            # Skip whitespace clusters, they don't get emphasis marks.
            byte_start = item_offset + clusters[i]
            byte_end = (
                item_offset + clusters[i + 1]
                if i + 1 < num_glyphs else item_offset + item_length)
            cluster_text = utf8_text[byte_start:byte_end]
            if not cluster_text.strip():
                x += cluster_width
                continue

            # Draw the mark at half the font size, centered on the cluster.
            if mark_glyph not in mark_font.widths:
                pango.pango_font_get_glyph_extents(
                    mark_pango_font, mark_glyph, stream.ink_rect,
                    stream.logical_rect)
                mark_font.widths[mark_glyph] = round(
                    stream.logical_rect.width * 1000 * FROM_UNITS /
                    mark_font.font_size)
            if mark_glyph not in mark_font.to_unicode:
                mark_font.to_unicode[mark_glyph] = mark

            with stream.stacked():
                stream.set_color(color)
                stream.transform(
                    d=-mark_size, e=x + cluster_width / 2,
                    f=y + offset_y)
                stream.begin_text()
                stream.set_font_size(mark_font.hash, 1)
                stream.show_text(f'<{mark_glyph:04x}>')
                stream.end_text()
            x += cluster_width
