"""Fonts integration in PDF."""

import io
import re
from hashlib import md5
from logging import WARNING
from math import ceil

import pydyf
from fontTools import subset
from fontTools.ttLib import TTFont, TTLibError, ttFont
from fontTools.varLib.mutator import instantiateVariableFont

from ..logger import LOGGER, capture_logs
from ..text.constants import PANGO_STRETCH_PERCENT
from ..text.ffi import FROM_UNITS, ffi, harfbuzz, harfbuzz_subset, pango
from ..text.fonts import get_hb_object_data, get_pango_font_hb_face


class Font:
    def __init__(self, pango_font, description, font_size):
        self.hb_font = pango.pango_font_get_hb_font(pango_font)
        self.hb_face = get_pango_font_hb_face(pango_font)
        self.file_content = get_hb_object_data(self.hb_face)
        self.index = harfbuzz.hb_face_get_index(self.hb_face)

        self.font_size = font_size
        self.style = pango.pango_font_description_get_style(description)
        self.family = ffi.string(pango.pango_font_description_get_family(description))

        self.variations = {}
        variations = pango.pango_font_description_get_variations(description)
        if variations != ffi.NULL:
            self.variations = {
                part.split('=')[0]: float(part.split('=')[1])
                for part in ffi.string(variations).decode().split(',')}
        if weight := self.variations.get('weight'):
            self.weight = round(weight)
            pango.pango_font_description_set_weight(description, weight)
        else:
            self.weight = pango.pango_font_description_get_weight(description)
        if self.variations.get('ital'):
            pango.pango_font_description_set_style(
                description, pango.PANGO_STYLE_ITALIC)
        elif self.variations.get('slnt'):
            pango.pango_font_description_set_style(
                description, pango.PANGO_STYLE_OBLIQUE)
        if (width := self.variations.get('wdth')) is not None:
            stretch = min(
                PANGO_STRETCH_PERCENT.items(),
                key=lambda item: abs(item[0] - width))[1]
            pango.pango_font_description_set_stretch(description, stretch)
        description_string = ffi.string(
            pango.pango_font_description_to_string(description))

        # Never use the built-in hash function here: it’s not stable.
        self.hash = ''.join(
            chr(65 + letter % 26) for letter
            in md5(description_string, usedforsecurity=False).digest()[:6])

        # Set font name.
        name = re.split(b' [#@]', description_string)[0]
        self.name = b'/' + self.hash.encode() + b'+' + name.replace(b' ', b'-')

        # Set ascent and descent.
        if self.font_size:
            pango_metrics = pango.pango_font_get_metrics(pango_font, ffi.NULL)
            self.ascent = round(
                pango.pango_font_metrics_get_ascent(pango_metrics) * FROM_UNITS /
                self.font_size * 1000)
            self.descent = -round(
                pango.pango_font_metrics_get_descent(pango_metrics) * FROM_UNITS /
                self.font_size * 1000)
        else:
            self.ascent = self.descent = 0

        # Get font tables and set metadata.
        table_count = ffi.new('unsigned int *', 100)
        table_tags = ffi.new('hb_tag_t[100]')
        table_name = ffi.new('char[4]')
        harfbuzz.hb_face_get_table_tags(self.hb_face, 0, table_count, table_tags)
        self.tables = []
        for i in range(table_count[0]):
            harfbuzz.hb_tag_to_string(table_tags[i], table_name)
            self.tables.append(ffi.string(table_name).decode())
        self.bitmap = False
        if 'EBDT' in self.tables and 'EBLC' in self.tables:
            if 'glyf' in self.tables:
                tag = harfbuzz.hb_tag_from_string(b'glyf', -1)
                blob = harfbuzz.hb_face_reference_table(self.hb_face, tag)
                if harfbuzz.hb_blob_get_length(blob) == 0:
                    self.bitmap = True
                harfbuzz.hb_blob_destroy(blob)
            else:
                self.bitmap = True
        self.italic_angle = 0  # TODO: this should be different
        self.upem = harfbuzz.hb_face_get_upem(self.hb_face)
        self.png = harfbuzz.hb_ot_color_has_png(self.hb_face)
        self.svg = harfbuzz.hb_ot_color_has_svg(self.hb_face)
        self.stemv = 80
        self.stemh = 80
        self.widths = {}
        self.cmap = {}
        self.used_in_forms = False

        # Set font flags.
        self.flags = 2 ** (3 - 1)  # Symbolic, custom character set
        if self.style:
            self.flags += 2 ** (7 - 1)  # Italic
        if b'Serif' in name.split(b' '):
            self.flags += 2 ** (2 - 1)  # Serif

    def clean(self, cmap, hinting):
        """Remove useless data from font."""

        # Subset font.
        self.subset(cmap, hinting)

        # Transform variable into static font.
        if 'fvar' in self.tables:
            full_font = io.BytesIO(self.file_content)
            ttfont = TTFont(full_font, fontNumber=self.index)
            if 'wght' not in self.variations:
                self.variations['wght'] = self.weight
            if 'opsz' not in self.variations:
                self.variations['opsz'] = self.font_size
            if 'slnt' not in self.variations:
                slnt = 0
                if self.style == 1:
                    for axe in ttfont['fvar'].axes:
                        if axe.axisTag == 'slnt':
                            if axe.maxValue == 0:
                                slnt = axe.minValue
                            else:
                                slnt = axe.maxValue
                            break
                self.variations['slnt'] = slnt
            if 'ital' not in self.variations:
                self.variations['ital'] = int(self.style == 2)
            partial_font = io.BytesIO()
            try:
                ttfont = instantiateVariableFont(ttfont, self.variations)
                for key, (advance, bearing) in ttfont['hmtx'].metrics.items():
                    if advance < 0:
                        ttfont['hmtx'].metrics[key] = (0, bearing)
                ttfont.save(partial_font)
            except Exception:
                LOGGER.warning('Unable to mutate variable font')
            else:
                self.file_content = partial_font.getvalue()

        # Remove images.
        if self.png or self.svg:
            full_font = io.BytesIO(self.file_content)
            ttfont = TTFont(full_font, fontNumber=self.index)
            try:
                # Add empty glyphs instead of PNG or SVG emojis.
                if 'loca' not in self.tables or 'glyf' not in self.tables:
                    ttfont['loca'] = ttFont.getTableClass('loca')()
                    ttfont['glyf'] = ttFont.getTableClass('glyf')()
                    ttfont['glyf'].glyphOrder = ttfont.getGlyphOrder()
                    ttfont['glyf'].glyphs = {
                        name: ttFont.getTableModule('glyf').Glyph()
                        for name in ttfont['glyf'].glyphOrder}
                else:
                    for glyph in ttfont['glyf'].glyphs:
                        ttfont['glyf'][glyph] = ttFont.getTableModule('glyf').Glyph()
                for table_name in ('CBDT', 'CBLC', 'SVG '):
                    if table_name in ttfont:
                        del ttfont[table_name]
                output_font = io.BytesIO()
                ttfont.save(output_font)
                self.file_content = output_font.getvalue()
            except TTLibError:
                LOGGER.warning('Unable to save emoji font')

    @property
    def type(self):
        return 'otf' if self.file_content[:4] == b'OTTO' else 'ttf'

    def subset(self, cmap, hinting):
        """Remove unused glyphs and tables from font."""
        if not cmap:
            return

        if harfbuzz_subset and harfbuzz.hb_version_atleast(4, 1, 0):
            # 4.1.0 is required for hb_set_add_sorted_array.
            self._harfbuzz_subset(cmap, hinting)
        else:
            self._fonttools_subset(cmap, hinting)

    def _harfbuzz_subset(self, cmap, hinting):
        """Subset font using Harfbuzz."""
        hb_subset = ffi.gc(
            harfbuzz_subset.hb_subset_input_create_or_fail(),
            harfbuzz_subset.hb_subset_input_destroy)

        # Only keep used glyphs.
        gid_set = harfbuzz_subset.hb_subset_input_glyph_set(hb_subset)
        gid_array = ffi.new(f'hb_codepoint_t[{len(cmap)}]', sorted(cmap))
        harfbuzz.hb_set_add_sorted_array(gid_set, gid_array, len(cmap))

        # Set flags.
        flags = (
            harfbuzz_subset.HB_SUBSET_FLAGS_RETAIN_GIDS |
            harfbuzz_subset.HB_SUBSET_FLAGS_PASSTHROUGH_UNRECOGNIZED |
            harfbuzz_subset.HB_SUBSET_FLAGS_DESUBROUTINIZE)
        harfbuzz_subset.hb_subset_input_set_flags(hb_subset, flags)

        # Drop useless tables.
        drop_set = harfbuzz_subset.hb_subset_input_set(
            hb_subset, harfbuzz_subset.HB_SUBSET_SETS_DROP_TABLE_TAG)
        drop_tables = tuple(harfbuzz.hb_tag_from_string(name, -1) for name in (
            b'BASE', b'DSIG', b'EBDT', b'EBLC', b'EBSC', b'GPOS', b'GSUB', b'JSTF',
            b'LTSH', b'PCLT', b'SVG '))
        drop_tables_array = ffi.new(f'hb_codepoint_t[{len(drop_tables)}]', drop_tables)
        harfbuzz.hb_set_add_sorted_array(drop_set, drop_tables_array, len(drop_tables))

        # Subset font.
        hb_face = ffi.gc(
            harfbuzz_subset.hb_subset_or_fail(self.hb_face, hb_subset),
            harfbuzz.hb_face_destroy)

        # Drop empty glyphs after last one used.
        gid_set = harfbuzz_subset.hb_subset_input_glyph_set(hb_subset)
        keep = tuple(range(max(cmap) + 1))
        gid_array = ffi.new(f'hb_codepoint_t[{len(keep)}]', keep)
        harfbuzz.hb_set_add_sorted_array(gid_set, gid_array, len(keep))

        # Set flags.
        flags = (
            harfbuzz_subset.HB_SUBSET_FLAGS_PASSTHROUGH_UNRECOGNIZED |
            harfbuzz_subset.HB_SUBSET_FLAGS_DESUBROUTINIZE)
        if not hinting:
            flags |= harfbuzz_subset.HB_SUBSET_FLAGS_NO_HINTING
        harfbuzz_subset.hb_subset_input_set_flags(hb_subset, flags)

        # Subset font.
        hb_face = ffi.gc(
            harfbuzz_subset.hb_subset_or_fail(hb_face, hb_subset),
            harfbuzz.hb_face_destroy)

        # Store new font.
        if hb_face:
            file_content = get_hb_object_data(hb_face)
            if file_content:
                self.file_content = file_content
                return

        LOGGER.warning('Unable to subset font with Harfbuzz')

    def _fonttools_subset(self, cmap, hinting):
        """Subset font using Fonttools."""
        full_font = io.BytesIO(self.file_content)

        # Set subset options.
        options = subset.Options(
            retain_gids=True, passthrough_tables=True, ignore_missing_glyphs=True,
            hinting=hinting, desubroutinize=True)
        options.drop_tables += ['GSUB', 'GPOS', 'SVG']
        subsetter = subset.Subsetter(options)
        subsetter.populate(gids=cmap)

        # Subset font.
        try:
            ttfont = TTFont(full_font, fontNumber=self.index)
            with capture_logs('fontTools', level=WARNING) as logs:
                subsetter.subset(ttfont)
            for log in logs:
                LOGGER.warning(
                    'fontTools warning when subsetting "%s": %s',
                    self.family.decode(), log)
        except TTLibError:
            LOGGER.warning('Unable to subset font with fontTools')
        else:
            optimized_font = io.BytesIO()
            ttfont.save(optimized_font)
            self.file_content = optimized_font.getvalue()


def build_fonts_dictionary(pdf, fonts, compress, subset, options):
    """Build PDF dictionary for fonts."""
    pdf_fonts = pydyf.Dictionary()
    fonts_by_file_hash = {}
    for font in fonts.values():
        fonts_by_file_hash.setdefault(font.hash, []).append(font)
    font_references_by_file_hash = {}
    for file_hash, file_fonts in fonts_by_file_hash.items():
        # TODO: Find why we can have multiple fonts for one font file.
        font = file_fonts[0]
        if font.bitmap:
            continue

        # Clean font, optimize and handle emojis.
        cmap = {}
        if subset and not font.used_in_forms:
            for file_font in file_fonts:
                cmap = {**cmap, **file_font.cmap}
        font.clean(cmap, options['hinting'])

        # Include font.
        if font.type == 'otf':
            font_extra = pydyf.Dictionary({'Subtype': '/OpenType'})
        else:
            font_extra = pydyf.Dictionary({'Length1': len(font.file_content)})
        font_stream = pydyf.Stream([font.file_content], font_extra, compress=compress)
        pdf.add_object(font_stream)
        font_references_by_file_hash[file_hash] = font_stream.reference

    for font in fonts.values():
        if subset and not font.used_in_forms:
            # Only store widths and map for used glyphs
            font_widths = font.widths
            cmap = font.cmap
        else:
            # Store width and Unicode map for all glyphs
            full_font = io.BytesIO(font.file_content)
            ttfont = TTFont(full_font, fontNumber=font.index)
            font_widths, cmap = {}, {}
            for i, glyph in enumerate(ttfont.getGlyphSet().values()):
                font_widths[i] = glyph.width * 1000 / font.upem
            for letter, key in ttfont.getBestCmap().items():
                glyph = ttfont.getGlyphID(key)
                if glyph not in cmap:
                    cmap[glyph] = chr(letter)

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
            b'endcodespacerange'], compress=compress)
        cmap_length = len(cmap)
        cmap_items = tuple(cmap.items())
        for i in range(ceil(cmap_length / 100)):
            batch_length = min(100, cmap_length - i * 100)
            to_unicode.stream.append(f'{batch_length} beginbfchar'.encode())
            for glyph, text in cmap_items[i*100:(i+1)*100]:
                unicode_codepoints = ''.join(
                    f'{letter.encode("utf-16-be").hex()}' for letter in text)
                to_unicode.stream.append(
                    f'<{glyph:04x}> <{unicode_codepoints}>'.encode())
            to_unicode.stream.append(b'endbfchar')
        to_unicode.stream.extend([
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
                font_dictionary, pdf, font, font_widths, compress, subset)
        else:
            _build_vector_font_dictionary(
                font_dictionary, pdf, font, font_widths, compress,
                font_references_by_file_hash[font.hash], options['pdf_version'])
        pdf.add_object(font_dictionary)
        pdf_fonts[font.hash] = font_dictionary.reference

    return pdf_fonts


def _build_bitmap_font_dictionary(font_dictionary, pdf, font, widths, compress, subset):
    # https://docs.microsoft.com/typography/opentype/spec/ebdt
    font_dictionary['FontBBox'] = pydyf.Array([0, 0, 1, 1])
    font_dictionary['FontMatrix'] = pydyf.Array([1, 0, 0, 1, 0, 0])
    if subset:
        chars = tuple(sorted(font.cmap))
    else:
        chars = tuple(range(256))
    first, last = chars[0], chars[-1]
    differences = []
    for glyph in sorted(widths):
        if glyph - 1 not in widths:
            differences.append(glyph)
        differences.append(f'/{glyph}')
    font_dictionary['FirstChar'] = first
    font_dictionary['LastChar'] = last
    font_dictionary['Encoding'] = pydyf.Dictionary({
        'Type': '/Encoding',
        'Differences': pydyf.Array(differences),
    })
    char_procs = pydyf.Dictionary({})
    full_font = io.BytesIO(font.file_content)
    ttfont = TTFont(full_font, fontNumber=font.index)
    font_glyphs = ttfont['EBDT'].strikeData[0]
    widths = [0] * (last - first + 1)
    glyphs_info = {}
    for key, glyph in font_glyphs.items():
        glyph_format = glyph.getFormat()
        glyph_id = ttfont.getGlyphID(key)

        # Get and store glyph metrics.
        if glyph_format == 5:
            data = glyph.data
            subtables = ttfont['EBLC'].strikes[0].indexSubTables
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

        # Decode bitmaps.
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
            glyph_info['bitmap'] = int(bitmap_bits, 2).to_bytes(height * stride, 'big')
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
        # Don’t store glyph not in cmap.
        if glyph_id not in chars:
            continue

        # Draw glyph.
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
                    # TODO: Support subglyph in subglyph.
                    LOGGER.warning(f'Unsupported subglyph in subglyph: {sub_id}')
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
        ], compress=compress)
        pdf.add_object(bitmap_stream)
        char_procs[glyph_id] = bitmap_stream.reference

    pdf.add_object(char_procs)
    font_dictionary['Widths'] = pydyf.Array(widths)
    font_dictionary['CharProcs'] = char_procs.reference


def _build_vector_font_dictionary(font_dictionary, pdf, font, widths, compress,
                                  reference, pdf_version):
    font_file = f'FontFile{3 if font.type == "otf" else 2}'
    max_x = max(widths.values()) if widths else 0
    bbox = (0, font.descent, max_x, font.ascent)
    flags = font.flags
    if len(widths) > 1 and len(set(font.widths.values())) == 1:
        flags += 2 ** (1 - 1)  # FixedPitch
    font_descriptor = pydyf.Dictionary({
        'Type': '/FontDescriptor',
        'FontName': font.name,
        'FontFamily': pydyf.String(font.family),
        'Flags': flags,
        'FontBBox': pydyf.Array(bbox),
        'ItalicAngle': font.italic_angle,
        'Ascent': font.ascent,
        'Descent': font.descent,
        'CapHeight': bbox[3],
        'StemV': font.stemv,
        'StemH': font.stemh,
        font_file: reference,
    })
    if str(pdf_version) <= '1.4':  # Cast for bytes and None
        cids = sorted(font.widths)
        padded_width = ceil((cids[-1] + 1) / 8)
        bits = ['0'] * padded_width * 8
        for cid in cids:
            bits[cid] = '1'
        stream = pydyf.Stream(
            (int(''.join(bits), 2).to_bytes(padded_width, 'big'),),
            compress=compress)
        pdf.add_object(stream)
        font_descriptor['CIDSet'] = stream.reference
    if font.type == 'otf':
        font_descriptor['Subtype'] = '/OpenType'
    pdf.add_object(font_descriptor)

    pdf_widths = pydyf.Array()
    for i in sorted(widths):
        if i - 1 not in widths:
            pdf_widths.append(i)
            current_widths = pydyf.Array()
            pdf_widths.append(current_widths)
        current_widths.append(widths[i])

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
        'W': pdf_widths,
        'FontDescriptor': font_descriptor.reference,
    })
    pdf.add_object(subfont_dictionary)
    font_dictionary['Encoding'] = '/Identity-H'
    font_dictionary['DescendantFonts'] = pydyf.Array([subfont_dictionary.reference])
