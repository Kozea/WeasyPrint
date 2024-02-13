"""Insert anchors, links, bookmarks and inputs in PDFs."""

import hashlib
import io
import mimetypes
from os.path import basename
from urllib.parse import unquote, urlsplit

import pydyf

from .. import Attachment
from ..logger import LOGGER
from ..text.ffi import ffi, gobject, pango
from ..text.fonts import get_font_description
from ..urls import URLFetchingError


def add_links(links_and_anchors, matrix, pdf, page, names, mark):
    """Include hyperlinks in given PDF page."""
    links, anchors = links_and_anchors

    for link_type, link_target, rectangle, box in links:
        x1, y1 = matrix.transform_point(*rectangle[:2])
        x2, y2 = matrix.transform_point(*rectangle[2:])
        if link_type in ('internal', 'external'):
            box.link_annotation = pydyf.Dictionary({
                'Type': '/Annot',
                'Subtype': '/Link',
                'Rect': pydyf.Array([x1, y1, x2, y2]),
                'BS': pydyf.Dictionary({'W': 0}),
            })
            if mark:
                box.link_annotation['Contents'] = pydyf.String(link_target)
            if link_type == 'internal':
                box.link_annotation['Dest'] = pydyf.String(link_target)
            else:
                box.link_annotation['A'] = pydyf.Dictionary({
                    'Type': '/Action',
                    'S': '/URI',
                    'URI': pydyf.String(link_target),
                })
            pdf.add_object(box.link_annotation)
            if 'Annots' not in page:
                page['Annots'] = pydyf.Array()
            page['Annots'].append(box.link_annotation.reference)

    for anchor in anchors:
        anchor_name, x, y = anchor
        x, y = matrix.transform_point(x, y)
        names.append([
            anchor_name, pydyf.Array([page.reference, '/XYZ', x, y, 0])])


def add_outlines(pdf, bookmarks, parent=None):
    """Include bookmark outlines in PDF."""
    count = len(bookmarks)
    outlines = []
    for title, (page, x, y), children, state in bookmarks:
        destination = pydyf.Array((pdf.page_references[page], '/XYZ', x, y, 0))
        outline = pydyf.Dictionary({
            'Title': pydyf.String(title), 'Dest': destination})
        pdf.add_object(outline)
        children_outlines, children_count = add_outlines(
            pdf, children, parent=outline)
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

    if parent is None and outlines:
        outlines_dictionary = pydyf.Dictionary({
            'Count': count,
            'First': outlines[0].reference,
            'Last': outlines[-1].reference,
        })
        pdf.add_object(outlines_dictionary)
        for outline in outlines:
            outline['Parent'] = outlines_dictionary.reference
        pdf.catalog['Outlines'] = outlines_dictionary.reference

    return outlines, count


def add_inputs(inputs, matrix, pdf, page, resources, stream, font_map,
               compress):
    """Include form inputs in PDF."""
    if not inputs:
        return

    if 'Annots' not in page:
        page['Annots'] = pydyf.Array()
    if 'AcroForm' not in pdf.catalog:
        pdf.catalog['AcroForm'] = pydyf.Dictionary({
            'Fields': pydyf.Array(),
            'DR': resources.reference,
            'NeedAppearances': 'true',
        })
    page_reference = page['Contents'].split()[0]
    context = ffi.gc(
        pango.pango_font_map_create_context(font_map),
        gobject.g_object_unref)
    for i, (element, style, rectangle) in enumerate(inputs):
        rectangle = (
            *matrix.transform_point(*rectangle[:2]),
            *matrix.transform_point(*rectangle[2:]))

        input_type = element.attrib.get('type')
        default_name = f'unknown-{page_reference.decode()}-{i}'
        input_name = pydyf.String(element.attrib.get('name', default_name))
        # TODO: where does this 0.75 scale come from?
        font_size = style['font_size'] * 0.75
        field_stream = pydyf.Stream(compress=compress)
        field_stream.set_color_rgb(*style['color'][:3])
        if input_type == 'checkbox':
            # Checkboxes
            width = rectangle[2] - rectangle[0]
            height = rectangle[1] - rectangle[3]
            checked_stream = pydyf.Stream(extra={
                'Resources': resources.reference,
                'Type': '/XObject',
                'Subtype': '/Form',
                'BBox': pydyf.Array((0, 0, width, height)),
            }, compress=compress)
            checked_stream.push_state()
            checked_stream.begin_text()
            checked_stream.set_color_rgb(*style['color'][:3])
            checked_stream.set_font_size('ZaDb', font_size)
            # Center (let’s assume that Dingbat’s check has a 0.8em size)
            x = (width - font_size * 0.8) / 2
            y = (height - font_size * 0.8) / 2
            checked_stream.move_text_to(x, y)
            checked_stream.show_text_string('4')
            checked_stream.end_text()
            checked_stream.pop_state()
            pdf.add_object(checked_stream)

            checked = 'checked' in element.attrib
            field_stream.set_font_size('ZaDb', font_size)
            field = pydyf.Dictionary({
                'Type': '/Annot',
                'Subtype': '/Widget',
                'Rect': pydyf.Array(rectangle),
                'FT': '/Btn',
                'F': 1 << (3 - 1),  # Print flag
                'P': page.reference,
                'T': pydyf.String(input_name),
                'V': '/Yes' if checked else '/Off',
                'AP': pydyf.Dictionary({'N': pydyf.Dictionary({
                    'Yes': checked_stream.reference,
                })}),
                'AS': '/Yes' if checked else '/Off',
                'DA': pydyf.String(b' '.join(field_stream.stream)),
            })
        elif element.tag == 'select':
            # Select fields
            font_description = get_font_description(style)
            font = pango.pango_font_map_load_font(
                font_map, context, font_description)
            font = stream.add_font(font)
            font.used_in_forms = True

            field_stream.set_font_size(font.hash, font_size)
            options = []
            selected_values = []
            for option in element:
                value = pydyf.String(option.attrib.get('value', ''))
                text = pydyf.String(option.text)
                options.append(pydyf.Array([value, text]))
                if 'selected' in option.attrib:
                    selected_values.append(value)

            field = pydyf.Dictionary({
                'DA': pydyf.String(b' '.join(field_stream.stream)),
                'F': 1 << (3 - 1),  # Print flag
                'FT': '/Ch',
                'Opt': pydyf.Array(options),
                'P': page.reference,
                'Rect': pydyf.Array(rectangle),
                'Subtype': '/Widget',
                'T': pydyf.String(input_name),
                'Type': '/Annot',
            })
            if 'multiple' in element.attrib:
                field['Ff'] = 1 << (22 - 1)
                field['V'] = pydyf.Array(selected_values)
            else:
                field['Ff'] = 1 << (18 - 1)
                field['V'] = (
                    selected_values[-1] if selected_values
                    else pydyf.String(''))
        else:
            # Text, password, textarea, files, and unknown
            font_description = get_font_description(style)
            font = pango.pango_font_map_load_font(
                font_map, context, font_description)
            font = stream.add_font(font)
            font.used_in_forms = True

            field_stream.set_font_size(font.hash, font_size)
            value = (
                element.text if element.tag == 'textarea'
                else element.attrib.get('value', ''))
            field = pydyf.Dictionary({
                'Type': '/Annot',
                'Subtype': '/Widget',
                'Rect': pydyf.Array(rectangle),
                'FT': '/Tx',
                'F': 1 << (3 - 1),  # Print flag
                'P': page.reference,
                'T': pydyf.String(input_name),
                'V': pydyf.String(value or ''),
                'DA': pydyf.String(b' '.join(field_stream.stream)),
            })
            if element.tag == 'textarea':
                field['Ff'] = 1 << (13 - 1)
            elif input_type == 'password':
                field['Ff'] = 1 << (14 - 1)
            elif input_type == 'file':
                field['Ff'] = 1 << (21 - 1)

        pdf.add_object(field)
        page['Annots'].append(field.reference)
        pdf.catalog['AcroForm']['Fields'].append(field.reference)


def add_annotations(links, matrix, document, pdf, page, annot_files, compress):
    """Include annotations in PDF."""
    # TODO: splitting a link into multiple independent rectangular
    # annotations works well for pure links, but rather mediocre for
    # other annotations and fails completely for transformed (CSS) or
    # complex link shapes (area). It would be better to use /AP for all
    # links and coalesce link shapes that originate from the same HTML
    # link. This would give a feeling similiar to what browsers do with
    # links that span multiple lines.
    for link_type, annot_target, rectangle, _ in links:
        if link_type != 'attachment':
            continue
        if annot_target not in annot_files:
            # A single link can be split in multiple regions. We don't want
            # to embed a file multiple times of course, so keep a reference
            # to every embedded URL and reuse the object number.
            # TODO: Use the title attribute as description. The comment
            # above about multiple regions won't always be correct, because
            # two links might have the same href, but different titles.
            annot_files[annot_target] = write_pdf_attachment(
                pdf, Attachment(annot_target), compress)
        annot_file = annot_files[annot_target]
        if annot_file is None:
            continue
        rectangle = (
            *matrix.transform_point(*rectangle[:2]),
            *matrix.transform_point(*rectangle[2:]))
        stream = pydyf.Stream([], {
            'Type': '/XObject',
            'Subtype': '/Form',
            'BBox': pydyf.Array(rectangle),
        }, compress)
        pdf.add_object(stream)
        annot = pydyf.Dictionary({
            'Type': '/Annot',
            'Rect': pydyf.Array(rectangle),
            'Subtype': '/FileAttachment',
            'T': pydyf.String(),
            'FS': annot_file.reference,
            'AP': pydyf.Dictionary({'N': stream.reference}),
            'AS': '/N',
        })
        pdf.add_object(annot)
        if 'Annots' not in page:
            page['Annots'] = pydyf.Array()
        page['Annots'].append(annot.reference)


def write_pdf_attachment(pdf, attachment, compress):
    """Write an attachment to the PDF stream."""
    # Attachments from document links like <link> or <a> can only be URLs.
    # They're passed in as tuples
    url = None
    uncompressed_length = 0
    stream = b''
    try:
        with attachment.source as (_, source, url, _):
            if isinstance(source, str):
                source = source.encode()
            if isinstance(source, bytes):
                source = io.BytesIO(source)
            for data in iter(lambda: source.read(4096), b''):
                uncompressed_length += len(data)
                stream += data
    except URLFetchingError as exception:
        LOGGER.error('Failed to load attachment: %s', exception)
        return
    attachment.md5 = hashlib.md5(stream).hexdigest()

    # TODO: Use the result object from a URL fetch operation to provide more
    # details on the possible filename and MIME type.
    if url and urlsplit(url).path:
        filename = basename(unquote(urlsplit(url).path))
    else:
        filename = 'attachment.bin'
    mime_type = mimetypes.guess_type(filename, strict=False)[0]
    if not mime_type:
        mime_type = 'application/octet-stream'

    creation = pydyf.String(attachment.created.strftime('D:%Y%m%d%H%M%SZ'))
    mod = pydyf.String(attachment.modified.strftime('D:%Y%m%d%H%M%SZ'))
    file_extra = pydyf.Dictionary({
        'Type': '/EmbeddedFile',
        'Subtype': f'/{mime_type.replace("/", "#2f")}',
        'Params': pydyf.Dictionary({
            'CheckSum': f'<{attachment.md5}>',
            'Size': uncompressed_length,
            'CreationDate': creation,
            'ModDate': mod,
        })
    })
    file_stream = pydyf.Stream([stream], file_extra, compress=compress)
    pdf.add_object(file_stream)

    pdf_attachment = pydyf.Dictionary({
        'Type': '/Filespec',
        'F': pydyf.String(),
        'UF': pydyf.String(filename),
        'EF': pydyf.Dictionary({'F': file_stream.reference}),
        'Desc': pydyf.String(attachment.description or ''),
    })
    pdf.add_object(pdf_attachment)
    return pdf_attachment


def resolve_links(pages):
    """Resolve internal hyperlinks.

    Links to a missing anchor are removed with a warning.

    If multiple anchors have the same name, the first one is used.

    :returns:
        A generator yielding lists (one per page) like :attr:`Page.links`,
        except that ``target`` for internal hyperlinks is
        ``(page_number, x, y)`` instead of an anchor name.
        The page number is a 0-based index into the :attr:`pages` list,
        and ``x, y`` are in CSS pixels from the top-left of the page.

    """
    anchors = set()
    paged_anchors = []
    for i, page in enumerate(pages):
        paged_anchors.append([])
        for anchor_name, (point_x, point_y) in page.anchors.items():
            if anchor_name not in anchors:
                paged_anchors[-1].append((anchor_name, point_x, point_y))
                anchors.add(anchor_name)
    for page in pages:
        page_links = []
        for link in page.links:
            link_type, anchor_name, _, _ = link
            if link_type == 'internal':
                if anchor_name not in anchors:
                    LOGGER.error(
                        'No anchor #%s for internal URI reference',
                        anchor_name)
                else:
                    page_links.append(link)
            else:
                # External link
                page_links.append(link)
        yield page_links, paged_anchors.pop(0)
