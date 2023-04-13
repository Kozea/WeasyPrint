"""Fonts integration in PDF."""

from math import ceil

import pydyf

from ..logger import LOGGER


def build_fonts_dictionary(pdf, fonts, compress_pdf, subset, hinting):
    pdf_fonts = pydyf.Dictionary()
    fonts_by_file_hash = {}
    for font in fonts.values():
        fonts_by_file_hash.setdefault(font.hash, []).append(font)
    font_references_by_file_hash = {}
    for file_hash, file_fonts in fonts_by_file_hash.items():
        # TODO: find why we can have multiple fonts for one font file
        font = file_fonts[0]
        if font.bitmap:
            continue

        # Clean font, optimize and handle emojis
        cmap = {}
        if subset and not font.used_in_forms:
            for file_font in file_fonts:
                cmap = {**cmap, **file_font.cmap}
        font.clean(cmap, hinting)

        # Include font
        if font.type == 'otf':
            font_extra = pydyf.Dictionary({'Subtype': '/OpenType'})
        else:
            font_extra = pydyf.Dictionary({'Length1': len(font.file_content)})
        font_stream = pydyf.Stream(
            [font.file_content], font_extra, compress=compress_pdf)
        pdf.add_object(font_stream)
        font_references_by_file_hash[file_hash] = font_stream.reference

    for font in fonts.values():
        if subset and font.ttfont and not font.used_in_forms:
            # Only store widths and map for used glyphs
            font_widths = font.widths
            cmap = font.cmap
        else:
            # Store width and Unicode map for all glyphs
            font_widths, cmap = {}, {}
            for letter, key in font.ttfont.getBestCmap().items():
                glyph = font.ttfont.getGlyphID(key)
                if glyph not in cmap:
                    cmap[glyph] = chr(letter)
                width = font.ttfont.getGlyphSet()[key].width
                font_widths[glyph] = width * 1000 / font.upem

        max_x = max(font_widths.values()) if font_widths else 0
        bbox = (0, font.descent, max_x, font.ascent)

        widths = pydyf.Array()
        for i in sorted(font_widths):
            if i - 1 not in font_widths:
                widths.append(i)
                current_widths = pydyf.Array()
                widths.append(current_widths)
            current_widths.append(font_widths[i])

        font_file = f'FontFile{3 if font.type == "otf" else 2}'
        to_unicode = pydyf.Stream([
            b'/CIDInit /ProcSet findresource begin',
            b'12 dict begin',
            b'begincmap',
            b'/CIDSystemInfo',
            b'<< /Registry (Adobe)',
            b'/Ordering (UCS)',
            b'/Supplement 0',
            b'>> def',
            b'/CMapName /Adobe-Identity-UCS def',
            b'/CMapType 2 def',
            b'1 begincodespacerange',
            b'<0000> <ffff>',
            b'endcodespacerange',
            f'{len(cmap)} beginbfchar'.encode()], compress=compress_pdf)
        for glyph, text in cmap.items():
            unicode_codepoints = ''.join(
                f'{letter.encode("utf-16-be").hex()}' for letter in text)
            to_unicode.stream.append(
                f'<{glyph:04x}> <{unicode_codepoints}>'.encode())
        to_unicode.stream.extend([
            b'endbfchar',
            b'endcmap',
            b'CMapName currentdict /CMap defineresource pop',
            b'end',
            b'end'])
        pdf.add_object(to_unicode)
        font_dictionary = pydyf.Dictionary({
            'Type': '/Font',
            'Subtype': f'/Type{3 if font.bitmap else 0}',
            'BaseFont': font.name,
            'ToUnicode': to_unicode.reference,
        })

        if font.bitmap:
            _build_bitmap_font_dictionary(
                font_dictionary, pdf, font, widths, compress_pdf, subset)
        else:
            font_descriptor = pydyf.Dictionary({
                'Type': '/FontDescriptor',
                'FontName': font.name,
                'FontFamily': pydyf.String(font.family),
                'Flags': font.flags,
                'FontBBox': pydyf.Array(bbox),
                'ItalicAngle': font.italic_angle,
                'Ascent': font.ascent,
                'Descent': font.descent,
                'CapHeight': bbox[3],
                'StemV': font.stemv,
                'StemH': font.stemh,
                font_file: font_references_by_file_hash[font.hash],
            })
            if pdf.version <= b'1.4':
                cids = sorted(font.widths)
                padded_width = int(ceil(cids[-1] / 8))
                bits = ['0'] * padded_width * 8
                for cid in cids:
                    bits[cid] = '1'
                stream = pydyf.Stream(
                    (int(''.join(bits), 2).to_bytes(padded_width, 'big'),),
                    compress=compress_pdf)
                pdf.add_object(stream)
                font_descriptor['CIDSet'] = stream.reference
            if font.type == 'otf':
                font_descriptor['Subtype'] = '/OpenType'
            pdf.add_object(font_descriptor)
            subfont_dictionary = pydyf.Dictionary({
                'Type': '/Font',
                'Subtype': f'/CIDFontType{0 if font.type == "otf" else 2}',
                'BaseFont': font.name,
                'CIDSystemInfo': pydyf.Dictionary({
                    'Registry': pydyf.String('Adobe'),
                    'Ordering': pydyf.String('Identity'),
                    'Supplement': 0,
                }),
                'CIDToGIDMap': '/Identity',
                'W': widths,
                'FontDescriptor': font_descriptor.reference,
            })
            pdf.add_object(subfont_dictionary)
            font_dictionary['Encoding'] = '/Identity-H'
            font_dictionary['DescendantFonts'] = pydyf.Array(
                [subfont_dictionary.reference])
        pdf.add_object(font_dictionary)
        pdf_fonts[font.hash] = font_dictionary.reference

    return pdf_fonts


def _build_bitmap_font_dictionary(font_dictionary, pdf, font, widths,
                                  compress_pdf, subset):
    # https://docs.microsoft.com/typography/opentype/spec/ebdt
    font_dictionary['FontBBox'] = pydyf.Array([0, 0, 1, 1])
    font_dictionary['FontMatrix'] = pydyf.Array([1, 0, 0, 1, 0, 0])
    if subset:
        chars = tuple(sorted(font.cmap))
    else:
        chars = tuple(range(256))
    first, last = chars[0], chars[-1]
    font_dictionary['FirstChar'] = first
    font_dictionary['LastChar'] = last
    differences = []
    for index, index_widths in zip(widths[::2], widths[1::2]):
        differences.append(index)
        for i in range(len(index_widths)):
            if i + index in chars:
                differences.append(f'/{i + index}')
    font_dictionary['Encoding'] = pydyf.Dictionary({
        'Type': '/Encoding',
        'Differences': pydyf.Array(differences),
    })
    char_procs = pydyf.Dictionary({})
    font_glyphs = font.ttfont['EBDT'].strikeData[0]
    widths = [0] * (last - first + 1)
    glyphs_info = {}
    for key, glyph in font_glyphs.items():
        glyph_format = glyph.getFormat()
        glyph_id = font.ttfont.getGlyphID(key)

        # Get and store glyph metrics
        if glyph_format == 5:
            data = glyph.data
            subtables = font.ttfont['EBLC'].strikes[0].indexSubTables
            for subtable in subtables:
                first_index = subtable.firstGlyphIndex
                last_index = subtable.lastGlyphIndex
                if first_index <= glyph_id <= last_index:
                    height = subtable.metrics.height
                    advance = width = subtable.metrics.width
                    bearing_x = subtable.metrics.horiBearingX
                    bearing_y = subtable.metrics.horiBearingY
                    break
            else:
                LOGGER.warning(f'Unknown bitmap metrics for glyph: {glyph_id}')
                continue
        else:
            data_start = 5 if glyph_format in (1, 2, 8) else 8
            data = glyph.data[data_start:]
            height, width = glyph.data[0:2]
            bearing_x = int.from_bytes(glyph.data[2:3], 'big', signed=True)
            bearing_y = int.from_bytes(glyph.data[3:4], 'big', signed=True)
            advance = glyph.data[4]
        position_y = bearing_y - height
        if glyph_id in chars:
            widths[glyph_id - first] = advance
        stride = ceil(width / 8)
        glyph_info = glyphs_info[glyph_id] = {
            'width': width,
            'height': height,
            'x': bearing_x,
            'y': position_y,
            'stride': stride,
            'bitmap': None,
            'subglyphs': None,
        }

        # Decode bitmaps
        if 0 in (width, height) or not data:
            glyph_info['bitmap'] = b''
        elif glyph_format in (1, 6):
            glyph_info['bitmap'] = data
        elif glyph_format in (2, 5, 7):
            padding = (8 - (width % 8)) % 8
            bits = bin(int(data.hex(), 16))[2:]
            bits = bits.zfill(8 * len(data))
            bitmap_bits = ''.join(
                bits[i * width:(i + 1) * width] + padding * '0'
                for i in range(height))
            glyph_info['bitmap'] = int(bitmap_bits, 2).to_bytes(
                height * stride, 'big')
        elif glyph_format in (8, 9):
            subglyphs = glyph_info['subglyphs'] = []
            i = 0 if glyph_format == 9 else 1
            number_of_components = int.from_bytes(data[i:i+2], 'big')
            for j in range(number_of_components):
                index = (i + 2) + (j * 4)
                subglyph_id = int.from_bytes(data[index:index+2], 'big')
                x = int.from_bytes(data[index+2:index+3], 'big', signed=True)
                y = int.from_bytes(data[index+3:index+4], 'big', signed=True)
                subglyphs.append({'id': subglyph_id, 'x': x, 'y': y})
        else:  # pragma: no cover
            LOGGER.warning(f'Unsupported bitmap glyph format: {glyph_format}')
            glyph_info['bitmap'] = bytes(height * stride)

    for glyph_id, glyph_info in glyphs_info.items():
        # Don’t store glyph not in cmap
        if glyph_id not in chars:
            continue

        # Draw glyph
        stride = glyph_info['stride']
        width = glyph_info['width']
        height = glyph_info['height']
        x = glyph_info['x']
        y = glyph_info['y']
        if glyph_info['bitmap'] is None:
            length = height * stride
            bitmap_int = int.from_bytes(bytes(length), 'big')
            for subglyph in glyph_info['subglyphs']:
                sub_x = subglyph['x']
                sub_y = subglyph['y']
                sub_id = subglyph['id']
                if sub_id not in glyphs_info:
                    LOGGER.warning(f'Unknown subglyph: {sub_id}')
                    continue
                subglyph = glyphs_info[sub_id]
                if subglyph['bitmap'] is None:
                    # TODO: support subglyph in subglyph
                    LOGGER.warning(
                        f'Unsupported subglyph in subglyph: {sub_id}')
                    continue
                for row_y in range(subglyph['height']):
                    row_slice = slice(
                        row_y * subglyph['stride'],
                        (row_y + 1) * subglyph['stride'])
                    row = subglyph['bitmap'][row_slice]
                    row_int = int.from_bytes(row, 'big')
                    shift = stride * 8 * (height - sub_y - row_y - 1)
                    stride_difference = stride - subglyph['stride']
                    if stride_difference > 0:
                        row_int <<= stride_difference * 8
                    elif stride_difference < 0:
                        row_int >>= -stride_difference * 8
                    if sub_x > 0:
                        row_int >>= sub_x
                    elif sub_x < 0:
                        row_int <<= -sub_x
                    row_int %= 1 << stride * 8
                    row_int <<= shift
                    bitmap_int |= row_int
            bitmap = bitmap_int.to_bytes(length, 'big')
        else:
            bitmap = glyph_info['bitmap']
        bitmap_stream = pydyf.Stream([
            b'0 0 d0',
            f'{width} 0 0 {height} {x} {y} cm'.encode(),
            b'BI',
            b'/IM true',
            b'/W', width,
            b'/H', height,
            b'/BPC 1',
            b'/D [1 0]',
            b'ID', bitmap, b'EI'
        ], compress=compress_pdf)
        pdf.add_object(bitmap_stream)
        char_procs[glyph_id] = bitmap_stream.reference

    pdf.add_object(char_procs)
    font_dictionary['Widths'] = pydyf.Array(widths)
    font_dictionary['CharProcs'] = char_procs.reference
