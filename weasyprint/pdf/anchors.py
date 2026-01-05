"""Insert anchors, links, bookmarks and inputs in PDFs."""

import collections
import mimetypes
from hashlib import md5
from os.path import basename
from urllib.parse import unquote, urlsplit

import pydyf

from .. import Attachment
from ..logger import LOGGER
from ..text.ffi import ffi, gobject, pango
from ..text.fonts import get_font_description
from ..urls import URLFetchingError


def add_links(links_and_anchors, matrix, pdf, page, names, tags):
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
            if tags is not None:
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


def add_forms(forms, matrix, pdf, page, resources, stream, font_map):
    """Include form inputs in PDF."""
    if not forms or not any(forms.values()):
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
    inputs_with_forms = [
        (form, element, style, rectangle)
        for form, inputs in forms.items()
        for element, style, rectangle in inputs
    ]
    radio_groups = collections.defaultdict(dict)
    forms = collections.defaultdict(dict)
    for i, (form, element, style, rectangle) in enumerate(inputs_with_forms):
        rectangle = (
            *matrix.transform_point(*rectangle[:2]),
            *matrix.transform_point(*rectangle[2:]))

        input_type = element.attrib.get('type')
        input_value = element.attrib.get('value', 'Yes')
        default_name = f'unknown-{page_reference.decode()}-{i}'
        input_name = element.attrib.get('name', default_name)
        # TODO: where does this 0.75 scale come from?
        font_size = style['font_size'] * 0.75
        field_stream = stream.clone()
        field_stream.set_color(style['color'])
        field = pydyf.Dictionary({
            'Type': '/Annot',
            'Subtype': '/Widget',
            'Rect': pydyf.Array(rectangle),
            'P': page.reference,
            'F': 1 << (3 - 1),  # Print flag
            'T': pydyf.String(input_name),
        })
        if input_type in ('radio', 'checkbox'):
            if input_type == 'radio':
                if input_name not in radio_groups[form]:
                    radio_groups[form][input_name] = group = pydyf.Dictionary({
                        'FT': '/Btn',
                        'Ff': (1 << (15 - 1)) + (1 << (16 - 1)),  # NoToggle & Radio
                        'T': pydyf.String(input_name),
                        'V': '/Off',
                        'Kids': pydyf.Array(),
                        'Opt': pydyf.Array(),
                    })
                    pdf.add_object(group)
                    pdf.catalog['AcroForm']['Fields'].append(group.reference)
                group = radio_groups[form][input_name]
                font_size = style['font_size'] * 0.5
                character = 'l'  # Disc character in Dingbats
            else:
                character = '4'  # Check character in Dingbats

            # Create stream when input is checked.
            width = rectangle[2] - rectangle[0]
            height = rectangle[1] - rectangle[3]
            checked_stream = stream.clone(extra={
                'Resources': resources.reference,
                'Type': '/XObject',
                'Subtype': '/Form',
                'BBox': pydyf.Array((0, 0, width, height)),
            })
            checked_stream.push_state()
            checked_stream.begin_text()
            checked_stream.set_color(style['color'])
            checked_stream.set_font_size('ZaDb', font_size)
            # Center (assuming that Dingbat’s characters have a 0.75em size).
            x = (width - font_size * 0.75) / 2
            y = (height - font_size * 0.75) / 2
            checked_stream.move_text_to(x, y)
            checked_stream.show_text_string(character)
            checked_stream.end_text()
            checked_stream.pop_state()
            pdf.add_object(checked_stream)

            field_stream.set_font_size('ZaDb', font_size)

            checked = 'checked' in element.attrib
            key = len(group['Kids']) if input_type == 'radio' else 'on'
            appearance = pydyf.Dictionary({key: checked_stream.reference})
            field['FT'] = '/Btn'
            field['DA'] = pydyf.String(b' '.join(field_stream.stream))
            field['AS'] = f'/{key}' if checked else '/Off'
            field['AP'] = pydyf.Dictionary({'N': appearance})
            field['MK'] = pydyf.Dictionary({'CA': pydyf.String(character)})
            pdf.add_object(field)
            if input_type == 'radio':
                field['Parent'] = group.reference
                if checked:
                    group['V'] = f'/{key}'
                group['Kids'].append(field.reference)
                group['Opt'].append(pydyf.String(input_value))
            else:
                field['T'] = pydyf.String(input_name)
                field['V'] = field['AS']

        elif element.tag == 'select':
            font_description = get_font_description(style)
            font = pango.pango_font_map_load_font(
                font_map, context, font_description)
            font, _ = stream.add_font(font)
            font.used_in_forms = True

            field_stream.set_font_size(font.hash, font_size)
            options = []
            selected_values = []
            for option in element:
                value = pydyf.String(option.attrib.get('value', ''))
                text = pydyf.String(option.text or '')
                options.append(pydyf.Array([value, text]))
                if 'selected' in option.attrib:
                    selected_values.append(value)

            field['FT'] = '/Ch'
            field['DA'] = pydyf.String(b' '.join(field_stream.stream))
            field['Opt'] = pydyf.Array(options)
            if 'multiple' in element.attrib:
                field['Ff'] = 1 << (22 - 1)
                field['V'] = pydyf.Array(selected_values)
            else:
                field['Ff'] = 1 << (18 - 1)
                field['V'] = (
                    selected_values[-1] if selected_values
                    else pydyf.String(''))
            pdf.add_object(field)

        elif input_type == 'submit' or element.tag == 'button':
            flags = 1 << (3 - 1)  # HTML form format
            if form.attrib.get('method', '').lower() != 'post':
                flags += 1 << (4 - 1)  # GET method
            fields = pydyf.Array(field.reference for field in forms[form].values())
            field['FT'] = '/Btn'
            field['DA'] = pydyf.String(b' '.join(field_stream.stream))
            field['V'] = pydyf.String(form.attrib.get('value', ''))
            field['Ff'] = 1 << (17 - 1)  # Push-button
            field['A'] = pydyf.Dictionary({
                'Type': '/Action',
                'S': '/SubmitForm',
                'F': pydyf.String(form.attrib.get('action')),
                'Fields': fields,
                'Flags': flags,
            })
            pdf.add_object(field)

        else:
            # Text, password, textarea, files, and other unknown fields.
            font_description = get_font_description(style)
            font = pango.pango_font_map_load_font(
                font_map, context, font_description)
            font, _ = stream.add_font(font)
            font.used_in_forms = True

            field_stream.set_font_size(font.hash, font_size)
            field['FT'] = '/Tx'
            field['DA'] = pydyf.String(b' '.join(field_stream.stream))
            field['V'] = pydyf.String(element.attrib.get('value', ''))
            if element.tag == 'textarea':
                field['Ff'] = 1 << (13 - 1)
                field['V'] = pydyf.String(element.text or '')
            elif input_type == 'password':
                field['Ff'] = 1 << (14 - 1)
            elif input_type == 'file':
                field['Ff'] = 1 << (21 - 1)
            if (max_length := element.get('maxlength', '')).isdigit():
                field['MaxLen'] = max_length
            pdf.add_object(field)

        page['Annots'].append(field.reference)
        pdf.catalog['AcroForm']['Fields'].append(field.reference)
        if input_name not in forms:
            forms[form][input_name] = field


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
            attachment = Attachment(
                url=annot_target, url_fetcher=document.url_fetcher)
            annot_files[annot_target] = write_pdf_attachment(
                pdf, attachment, compress)
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
    url = mime_type = None
    try:
        with attachment.source as (file_obj, url, _, mime_type):
            stream = file_obj.read()
            if isinstance(stream, str):
                stream = stream.encode()
    except URLFetchingError as exception:
        LOGGER.error('Failed to load attachment: %s', exception)
        LOGGER.debug('Error while loading attachment:', exc_info=exception)
        return
    attachment.md5 = md5(stream, usedforsecurity=False).hexdigest()

    # TODO: Use the result object from a URL fetch operation to provide more
    # details on the possible filename and MIME type.
    if attachment.name:
        filename = attachment.name
    elif url and urlsplit(url).path:
        filename = basename(unquote(urlsplit(url).path))
    else:
        filename = 'attachment.bin'
    mime_type = (
        mime_type or
        mimetypes.guess_type(filename, strict=False)[0] or
        'application/octet-stream')

    creation = pydyf.String(attachment.created.strftime('D:%Y%m%d%H%M%SZ'))
    mod = pydyf.String(attachment.modified.strftime('D:%Y%m%d%H%M%SZ'))
    file_extra = pydyf.Dictionary({
        'Type': '/EmbeddedFile',
        'Subtype': f'/{mime_type.replace("/", "#2f")}',
        'Params': pydyf.Dictionary({
            'CheckSum': f'<{attachment.md5}>',
            'Size': len(stream),
            'CreationDate': creation,
            'ModDate': mod,
        })
    })
    file_stream = pydyf.Stream([stream], file_extra, compress=compress)
    pdf.add_object(file_stream)

    pdf_attachment = pydyf.Dictionary({
        'Type': '/Filespec',
        'F': pydyf.String(filename.encode(errors='ignore')),
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
        for anchor_name, (point_x, point_y, _, _) in page.anchors.items():
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
