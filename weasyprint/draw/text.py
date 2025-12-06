"""Draw text."""

from io import BytesIO
from xml.etree import ElementTree

from PIL import Image

from ..images import RasterImage, SVGImage
from ..logger import LOGGER
from ..matrix import Matrix
from ..text.ffi import FROM_UNITS, TO_UNITS, ffi, pango
from ..text.fonts import get_hb_object_data
from ..text.line_break import get_last_word_end
from .border import draw_line
from .color import get_color


def draw_text(stream, textbox, offset_x, text_overflow, block_ellipsis):
    """Draw a textbox to a pydyf stream."""
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
        elif textbox.style['text_decoration_thickness'].unit == '%':
            ratio = textbox.style['text_decoration_thickness'].value / 100
            thickness = textbox.style['font_size'] * ratio
        else:
            thickness = textbox.style['text_decoration_thickness'].value
    if 'overline' in text_decoration_values:
        offset_y = (
            textbox.baseline - textbox.pango_layout.ascent + thickness / 2)
        draw_text_decoration(
            stream, textbox, offset_x, offset_y, thickness,
            text_decoration_color)
    if 'underline' in text_decoration_values:
        if textbox.style['text_underline_offset'] == 'auto':
            underline_offset = - textbox.pango_layout.underline_position
        elif textbox.style['text_underline_offset'].unit == '%':
            ratio = textbox.style['text_underline_offset'].value / 100
            underline_offset = textbox.style['font_size'] * ratio
        else:
            underline_offset = textbox.style['text_underline_offset'].value
        offset_y = textbox.baseline + underline_offset + thickness / 2
        draw_text_decoration(
            stream, textbox, offset_x, offset_y, thickness,
            text_decoration_color)

    # Draw text.
    x, y = textbox.position_x, textbox.position_y + textbox.baseline
    stream.set_color(textbox.style['color'])
    textbox.pango_layout.reactivate(textbox.style)
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

    utf8_text = textbox.pango_layout.text.encode()
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
        number_of_glyphs = glyph_string.num_glyphs
        offset = glyph_item.item.offset
        clusters = glyph_string.log_clusters

        # Get positions of the glyphs in the UTF-8 string.
        utf8_positions = [offset + clusters[i] for i in range(number_of_glyphs)]
        if glyph_item.item.analysis.level % 2:
            utf8_positions.insert(0, offset + glyph_item.item.length)  # rtl
        else:
            utf8_positions.append(offset + glyph_item.item.length)  # ltr

        pango_font = glyph_item.item.analysis.font
        if pango_font != previous_pango_font:
            # Add font file content and get font size.
            previous_pango_font = pango_font
            font, font_size = stream.add_font(pango_font)

            # Workaround for https://gitlab.gnome.org/GNOME/pango/-/issues/530.
            if pango.pango_version() < 14802:
                font_size = textbox.style['font_size']

            # Go through the run glyphs.
            if string:
                stream.show_text(string)
            string = ''
            stream.set_font_size(font.hash, 1 if font.bitmap else font_size)
        string += '<'
        for i in range(number_of_glyphs):
            glyph_info = glyphs_info[i]
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
                    f'"{chr(codepoint)}" (U+{codepoint:04X})')
                glyph_id = font.get_unused_glyph_id(codepoint)
                font.widths[glyph_id] = round(width * 1000 * FROM_UNITS / font_size)
                if 0 not in font.widths:
                    # "width" is actually Pango’s get_approximate_char_width. Force
                    # .notdef’s to use this width, even if it’s not the right, as we
                    # want to keep Pango’s layout for next glyphs.
                    font.widths[0] = font.widths[glyph_id]

            # Create mapping between glyphs and Unicode codepoints.
            if glyph_id not in font.to_unicode:
                utf8_slice = slice(*sorted(utf8_positions[i:i+2]))
                font.to_unicode[glyph_id] = utf8_text[utf8_slice].decode()

            # Set horizontal and vertical offsets.
            offset = glyph_info.geometry.x_offset / font_size
            rise = glyph_info.geometry.y_offset / 1000
            if rise:
                if string[-1] == '<':
                    string = string[:-1]
                else:
                    string += '>'
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
