"""PDF generation management."""

import hashlib
import io
import math
import zlib
from os.path import basename
from urllib.parse import unquote, urlsplit

import pydyf

from .. import Attachment, __version__
from ..html import W3C_DATE_RE
from ..links import make_page_bookmark_tree, resolve_links
from ..logger import LOGGER, PROGRESS_LOGGER
from ..matrix import Matrix
from ..urls import URLFetchingError
from . import pdfa
from .stream import Stream

VARIANTS = {
    name: function for variants in (pdfa.VARIANTS,)
    for (name, function) in variants.items()}


def _w3c_date_to_pdf(string, attr_name):
    """Tranform W3C date to PDF format."""
    if string is None:
        return None
    match = W3C_DATE_RE.match(string)
    if match is None:
        LOGGER.warning(f'Invalid {attr_name} date: {string!r}')
        return None
    groups = match.groupdict()
    pdf_date = ''
    found = groups['hour']
    for key in ('second', 'minute', 'hour', 'day', 'month', 'year'):
        if groups[key]:
            found = True
            pdf_date = groups[key] + pdf_date
        elif found:
            pdf_date = f'{(key in ("day", "month")):02d}{pdf_date}'
    if groups['hour']:
        assert groups['minute']
        if groups['tz_hour']:
            assert groups['tz_hour'].startswith(('+', '-'))
            assert groups['tz_minute']
            tz_hour = int(groups['tz_hour'])
            tz_minute = int(groups['tz_minute'])
            pdf_date += f"{tz_hour:+03d}'{tz_minute:02d}"
        else:
            pdf_date += 'Z'
    return pdf_date


def _write_pdf_attachment(pdf, attachment, url_fetcher):
    """Write an attachment to the PDF stream.

    :return:
        the attachment PDF dictionary.

    """
    # Attachments from document links like <link> or <a> can only be URLs.
    # They're passed in as tuples
    url = ''
    if isinstance(attachment, tuple):
        url, description = attachment
        attachment = Attachment(
            url=url, url_fetcher=url_fetcher, description=description)
    elif not isinstance(attachment, Attachment):
        attachment = Attachment(guess=attachment, url_fetcher=url_fetcher)

    try:
        with attachment.source as (source_type, source, url, _):
            if isinstance(source, bytes):
                source = io.BytesIO(source)
            uncompressed_length = 0
            stream = b''
            md5 = hashlib.md5()
            compress = zlib.compressobj()
            for data in iter(lambda: source.read(4096), b''):
                uncompressed_length += len(data)
                md5.update(data)
                compressed = compress.compress(data)
                stream += compressed
            compressed = compress.flush(zlib.Z_FINISH)
            stream += compressed
            file_extra = pydyf.Dictionary({
                'Type': '/EmbeddedFile',
                'Filter': '/FlateDecode',
                'Params': pydyf.Dictionary({
                    'CheckSum': f'<{md5.hexdigest()}>',
                    'Size': uncompressed_length,
                })
            })
            file_stream = pydyf.Stream([stream], file_extra)
            pdf.add_object(file_stream)

    except URLFetchingError as exception:
        LOGGER.error('Failed to load attachment: %s', exception)
        return

    # TODO: Use the result object from a URL fetch operation to provide more
    # details on the possible filename.
    if url and urlsplit(url).path:
        filename = basename(unquote(urlsplit(url).path))
    else:
        filename = 'attachment.bin'

    attachment = pydyf.Dictionary({
        'Type': '/Filespec',
        'F': pydyf.String(),
        'UF': pydyf.String(filename),
        'EF': pydyf.Dictionary({'F': file_stream.reference}),
        'Desc': pydyf.String(attachment.description or ''),
    })
    pdf.add_object(attachment)
    return attachment


def _reference_resources(pdf, resources, images, fonts):
    if 'Font' in resources:
        assert resources['Font'] is None
        resources['Font'] = fonts
    _use_references(pdf, resources, images)
    pdf.add_object(resources)
    return resources.reference


def _use_references(pdf, resources, images):
    # XObjects
    for key, x_object in resources.get('XObject', {}).items():
        # Images
        if x_object is None:
            x_object = images[key]
            if x_object.number is not None:
                # Image already added to PDF
                resources['XObject'][key] = x_object.reference
                continue

        pdf.add_object(x_object)
        resources['XObject'][key] = x_object.reference

        # Masks
        if 'SMask' in x_object.extra:
            pdf.add_object(x_object.extra['SMask'])
            x_object.extra['SMask'] = x_object.extra['SMask'].reference

        # Resources
        if 'Resources' in x_object.extra:
            x_object.extra['Resources'] = _reference_resources(
                pdf, x_object.extra['Resources'], images,
                resources['Font'])

    # Patterns
    for key, pattern in resources.get('Pattern', {}).items():
        pdf.add_object(pattern)
        resources['Pattern'][key] = pattern.reference
        if 'Resources' in pattern.extra:
            pattern.extra['Resources'] = _reference_resources(
                pdf, pattern.extra['Resources'], images, resources['Font'])

    # Shadings
    for key, shading in resources.get('Shading', {}).items():
        pdf.add_object(shading)
        resources['Shading'][key] = shading.reference

    # Alpha states
    for key, alpha in resources.get('ExtGState', {}).items():
        if 'SMask' in alpha and 'G' in alpha['SMask']:
            alpha['SMask']['G'] = alpha['SMask']['G'].reference


def _add_links(links, anchors, matrix, pdf, page, names):
    """Include hyperlinks in given PDF page."""
    for link in links:
        link_type, link_target, rectangle, _ = link
        x1, y1 = matrix.transform_point(*rectangle[:2])
        x2, y2 = matrix.transform_point(*rectangle[2:])
        if link_type in ('internal', 'external'):
            annot = pydyf.Dictionary({
                'Type': '/Annot',
                'Subtype': '/Link',
                'Rect': pydyf.Array([x1, y1, x2, y2]),
                'BS': pydyf.Dictionary({'W': 0}),
            })
            if link_type == 'internal':
                annot['Dest'] = pydyf.String(link_target)
            else:
                annot['A'] = pydyf.Dictionary({
                    'Type': '/Action',
                    'S': '/URI',
                    'URI': pydyf.String(link_target),
                })
            pdf.add_object(annot)
            if 'Annots' not in page:
                page['Annots'] = pydyf.Array()
            page['Annots'].append(annot.reference)

    for anchor in anchors:
        anchor_name, x, y = anchor
        x, y = matrix.transform_point(x, y)
        names.append([
            anchor_name, pydyf.Array([page.reference, '/XYZ', x, y, 0])])


def _create_bookmarks(bookmarks, pdf, parent=None):
    count = len(bookmarks)
    outlines = []
    for title, (page, x, y), children, state in bookmarks:
        destination = pydyf.Array((
            pdf.objects[pdf.pages['Kids'][page * 3]].reference,
            '/XYZ', x, y, 0))
        outline = pydyf.Dictionary({
            'Title': pydyf.String(title), 'Dest': destination})
        pdf.add_object(outline)
        children_outlines, children_count = _create_bookmarks(
            children, pdf, parent=outline)
        outline['Count'] = children_count
        if state == 'closed':
            outline['Count'] *= -1
        else:
            count += children_count
        if outlines:
            outline['Prev'] = outlines[-1].reference
            outlines[-1]['Next'] = outline.reference
        if children_outlines:
            outline['First'] = children_outlines[0].reference
            outline['Last'] = children_outlines[-1].reference
        if parent is not None:
            outline['Parent'] = parent.reference
        outlines.append(outline)
    return outlines, count


def generate_pdf(pages, url_fetcher, metadata, fonts, target, zoom,
                 attachments, finisher, optimize_size, identifier, variant,
                 version, custom_metadata):
    # 0.75 = 72 PDF point per inch / 96 CSS pixel per inch
    scale = zoom * 0.75

    PROGRESS_LOGGER.info('Step 6 - Creating PDF')

    pdf = pydyf.PDF()
    pdf.version = str(version or '1.7').encode()
    states = pydyf.Dictionary()
    x_objects = pydyf.Dictionary()
    patterns = pydyf.Dictionary()
    shadings = pydyf.Dictionary()
    images = {}
    resources = pydyf.Dictionary({
        'ExtGState': states,
        'XObject': x_objects,
        'Pattern': patterns,
        'Shading': shadings,
    })
    pdf.add_object(resources)
    pdf_names = []

    # Variants
    if variant:
        VARIANTS[variant](pdf, metadata)

    # Links and anchors
    page_links_and_anchors = list(resolve_links(pages))
    attachment_links = [
        [link for link in page_links if link[0] == 'attachment']
        for page_links, page_anchors in page_links_and_anchors]

    # Annotations
    annot_files = {}
    # A single link can be split in multiple regions. We don't want to embed a
    # file multiple times of course, so keep a reference to every embedded URL
    # and reuse the object number.
    for page_links in attachment_links:
        for link_type, annot_target, rectangle, _ in page_links:
            if link_type == 'attachment' and target not in annot_files:
                # TODO: Use the title attribute as description. The comment
                # above about multiple regions won't always be correct, because
                # two links might have the same href, but different titles.
                annot_files[annot_target] = _write_pdf_attachment(
                    pdf, (annot_target, None), url_fetcher)

    # Bookmarks
    root = []
    # At one point in the document, for each "output" depth, how much to add to
    # get the source level (CSS values of bookmark-level).
    # E.g. with <h1> then <h3>, level_shifts == [0, 1]
    # 1 means that <h3> has depth 3 - 1 = 2 in the output.
    skipped_levels = []
    last_by_depth = [root]
    previous_level = 0

    for page_number, (page, links_and_anchors, page_links) in enumerate(
            zip(pages, page_links_and_anchors, attachment_links)):
        # Draw from the top-left corner
        matrix = Matrix(scale, 0, 0, -scale, 0, page.height * scale)

        # Links and anchors
        links, anchors = links_and_anchors

        page_width = scale * (
            page.width + page.bleed['left'] + page.bleed['right'])
        page_height = scale * (
            page.height + page.bleed['top'] + page.bleed['bottom'])
        left = -scale * page.bleed['left']
        top = -scale * page.bleed['top']
        right = left + page_width
        bottom = top + page_height

        page_rectangle = (
            left / scale, top / scale,
            (right - left) / scale, (bottom - top) / scale)
        stream = Stream(
            fonts, page_rectangle, states, x_objects, patterns, shadings,
            images)
        stream.transform(d=-1, f=(page.height * scale))
        page.paint(stream, scale=scale)
        pdf.add_object(stream)

        pdf_page = pydyf.Dictionary({
            'Type': '/Page',
            'Parent': pdf.pages.reference,
            'MediaBox': pydyf.Array([left, top, right, bottom]),
            'Contents': stream.reference,
            'Resources': resources.reference,
        })
        pdf.add_page(pdf_page)

        _add_links(links, anchors, matrix, pdf, pdf_page, pdf_names)

        # Bleed
        bleed = {key: value * 0.75 for key, value in page.bleed.items()}

        trim_left = left + bleed['left']
        trim_top = top + bleed['top']
        trim_right = right - bleed['right']
        trim_bottom = bottom - bleed['bottom']

        # Arbitrarly set PDF BleedBox between CSS bleed box (MediaBox) and
        # CSS page box (TrimBox) at most 10 points from the TrimBox.
        bleed_left = trim_left - min(10, bleed['left'])
        bleed_top = trim_top - min(10, bleed['top'])
        bleed_right = trim_right + min(10, bleed['right'])
        bleed_bottom = trim_bottom + min(10, bleed['bottom'])

        pdf_page['TrimBox'] = pydyf.Array([
            trim_left, trim_top, trim_right, trim_bottom])
        pdf_page['BleedBox'] = pydyf.Array([
            bleed_left, bleed_top, bleed_right, bleed_bottom])

        # Annotations
        # TODO: splitting a link into multiple independent rectangular
        # annotations works well for pure links, but rather mediocre for
        # other annotations and fails completely for transformed (CSS) or
        # complex link shapes (area). It would be better to use /AP for all
        # links and coalesce link shapes that originate from the same HTML
        # link. This would give a feeling similiar to what browsers do with
        # links that span multiple lines.
        for link_type, annot_target, rectangle, _ in page_links:
            annot_file = annot_files[annot_target]
            if link_type == 'attachment' and annot_file is not None:
                rectangle = (
                    *matrix.transform_point(*rectangle[:2]),
                    *matrix.transform_point(*rectangle[2:]))
                annot = pydyf.Dictionary({
                    'Type': '/Annot',
                    'Rect': pydyf.Array(rectangle),
                    'Subtype': '/FileAttachment',
                    'T': pydyf.String(),
                    'FS': annot_file.reference,
                    'AP': pydyf.Dictionary({'N': pydyf.Stream([], {
                        'Type': '/XObject',
                        'Subtype': '/Form',
                        'BBox': pydyf.Array(rectangle),
                        'Length': 0,
                    })})
                })
                pdf.add_object(annot)
                if 'Annots' not in pdf_page:
                    pdf_page['Annots'] = pydyf.Array()
                pdf_page['Annots'].append(annot.reference)

        # Bookmarks
        previous_level = make_page_bookmark_tree(
            page, skipped_levels, last_by_depth, previous_level, page_number,
            matrix)

    # Outlines
    outlines, count = _create_bookmarks(root, pdf)
    if outlines:
        outlines_dictionary = pydyf.Dictionary({
            'Count': count,
            'First': outlines[0].reference,
            'Last': outlines[-1].reference,
        })
        pdf.add_object(outlines_dictionary)
        for outline in outlines:
            outline['Parent'] = outlines_dictionary.reference
        pdf.catalog['Outlines'] = outlines_dictionary.reference

    PROGRESS_LOGGER.info('Step 7 - Adding PDF metadata')

    # PDF information
    pdf.info['Producer'] = pydyf.String(f'WeasyPrint {__version__}')
    if metadata.title:
        pdf.info['Title'] = pydyf.String(metadata.title)
    if metadata.authors:
        pdf.info['Author'] = pydyf.String(', '.join(metadata.authors))
    if metadata.description:
        pdf.info['Subject'] = pydyf.String(metadata.description)
    if metadata.keywords:
        pdf.info['Keywords'] = pydyf.String(
            ', '.join(metadata.keywords))
    if metadata.generator:
        pdf.info['Creator'] = pydyf.String(metadata.generator)
    if metadata.created:
        pdf.info['CreationDate'] = pydyf.String(
            _w3c_date_to_pdf(metadata.created, 'created'))
    if metadata.modified:
        pdf.info['ModDate'] = pydyf.String(
            _w3c_date_to_pdf(metadata.modified, 'modified'))
    if custom_metadata:
        for key, value in metadata.custom.items():
            key = ''.join(char for char in key if char.isalnum())
            key = key.encode('ascii', errors='ignore').decode()
            if key:
                pdf.info[key] = pydyf.String(value)

    # Embedded files
    attachments = metadata.attachments + (attachments or [])
    pdf_attachments = []
    for attachment in attachments:
        pdf_attachment = _write_pdf_attachment(pdf, attachment, url_fetcher)
        if pdf_attachment is not None:
            pdf_attachments.append(pdf_attachment)
    if pdf_attachments:
        content = pydyf.Dictionary({'Names': pydyf.Array()})
        for i, pdf_attachment in enumerate(pdf_attachments):
            content['Names'].append(pydyf.String(f'attachment{i}'))
            content['Names'].append(pdf_attachment.reference)
        pdf.add_object(content)
        if 'Names' not in pdf.catalog:
            pdf.catalog['Names'] = pydyf.Dictionary()
        pdf.catalog['Names']['EmbeddedFiles'] = content.reference

    # Embeded fonts
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
        if 'fonts' in optimize_size:
            for file_font in file_fonts:
                cmap = {**cmap, **file_font.cmap}
        font.clean(cmap)

        # Include font
        if font.type == 'otf':
            font_extra = pydyf.Dictionary({'Subtype': '/OpenType'})
        else:
            font_extra = pydyf.Dictionary(
                {'Length1': len(font.file_content)})
        font_stream = pydyf.Stream(
            [font.file_content], font_extra, compress=True)
        pdf.add_object(font_stream)
        font_references_by_file_hash[file_hash] = font_stream.reference

    for font in fonts.values():
        widths = pydyf.Array()
        for i in sorted(font.widths):
            if i - 1 not in font.widths:
                widths.append(i)
                current_widths = pydyf.Array()
                widths.append(current_widths)
            current_widths.append(font.widths[i])
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
            f'{len(font.cmap)} beginbfchar'.encode()])
        for glyph, text in font.cmap.items():
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
            # https://docs.microsoft.com/typography/opentype/spec/ebdt
            font_dictionary['FontBBox'] = pydyf.Array([0, 0, 1, 1])
            font_dictionary['FontMatrix'] = pydyf.Array([1, 0, 0, 1, 0, 0])
            if 'fonts' in optimize_size:
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
                # Get and store glyph metrics
                height, width = glyph.data[0:2]
                bearing_x = int.from_bytes(
                    glyph.data[2:3], 'big', signed=True)
                bearing_y = int.from_bytes(
                    glyph.data[3:4], 'big', signed=True)
                advance = glyph.data[4]
                position_y = bearing_y - height
                glyph_id = font.ttfont.getGlyphID(key)
                if glyph_id in chars:
                    widths[glyph_id - first] = advance
                stride = math.ceil(width / 8)
                glyph_info = glyphs_info[glyph_id] = {
                    'width': width,
                    'height': height,
                    'x': bearing_x,
                    'y': position_y,
                    'stride': stride,
                    'bitmap': None,
                    'subglyphs': None,
                }

                # Apply glyph format tweaks
                glyph_format = glyph.getFormat()
                data_start = 5 if glyph_format in (1, 2, 8) else 8
                data = glyph.data[data_start:]
                if glyph_format in (1, 6):
                    glyph_info['bitmap'] = data
                elif glyph_format in (2, 7):
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
                    number_of_components = int.from_bytes(
                        data[i:i+2], 'big')
                    for j in range(number_of_components):
                        index = (i + 2) + (j * 4)
                        subglyph_id = int.from_bytes(
                            data[index:index+2], 'big')
                        x = int.from_bytes(
                            data[index+2:index+3], 'big', signed=True)
                        y = int.from_bytes(
                            data[index+3:index+4], 'big', signed=True)
                        subglyphs.append(
                            {'id': subglyph_id, 'x': x, 'y': y})
                else:  # pragma: no cover
                    LOGGER.warning(
                        f'Unsupported bitmap glyph format: {glyph_format}')
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
                                'Unsupported subglyph in subglyph: '
                                f'{sub_id}')
                            continue
                        for row_y in range(subglyph['height']):
                            row_slice = slice(
                                row_y * subglyph['stride'],
                                (row_y + 1) * subglyph['stride'])
                            row = subglyph['bitmap'][row_slice]
                            row_int = int.from_bytes(row, 'big')
                            shift = (
                                stride * 8 * (height - sub_y - row_y - 1))
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
                ])
                pdf.add_object(bitmap_stream)
                char_procs[glyph_id] = bitmap_stream.reference

            pdf.add_object(char_procs)
            font_dictionary['Widths'] = pydyf.Array(widths)
            font_dictionary['CharProcs'] = char_procs.reference

        else:
            font_descriptor = pydyf.Dictionary({
                'Type': '/FontDescriptor',
                'FontName': font.name,
                'FontFamily': pydyf.String(font.family),
                'Flags': font.flags,
                'FontBBox': pydyf.Array(font.bbox),
                'ItalicAngle': font.italic_angle,
                'Ascent': font.ascent,
                'Descent': font.descent,
                'CapHeight': font.bbox[3],
                'StemV': font.stemv,
                'StemH': font.stemh,
                font_file: font_references_by_file_hash[font.hash],
            })
            if pdf.version <= b'1.4':
                cids = sorted(font.widths)
                padded_width = int(math.ceil(cids[-1] / 8))
                bits = ['0'] * padded_width * 8
                for cid in cids:
                    bits[cid] = '1'
                stream = pydyf.Stream(
                    (int(''.join(bits), 2).to_bytes(padded_width, 'big'),))
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

    pdf.add_object(pdf_fonts)
    resources['Font'] = pdf_fonts.reference
    _use_references(pdf, resources, images)

    # Anchors
    if pdf_names:
        # Anchors are name trees that have to be sorted
        name_array = pydyf.Array()
        for anchor in sorted(pdf_names):
            name_array.append(pydyf.String(anchor[0]))
            name_array.append(anchor[1])
        dests = pydyf.Dictionary({'Names': name_array})
        pdf.catalog['Names'] = pydyf.Dictionary({'Dests': dests})

    return pdf
