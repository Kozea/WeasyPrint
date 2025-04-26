"""PDF/UA generation."""

import pydyf

from .metadata import add_metadata


def pdfua(pdf, metadata, document, page_streams, attachments, compress):
    """Set metadata for PDF/UA documents."""
    # Structure for PDF tagging
    content_mapping = pydyf.Dictionary({})
    pdf.add_object(content_mapping)
    structure_root = pydyf.Dictionary({
        'Type': '/StructTreeRoot',
        'ParentTree': content_mapping.reference,
    })
    pdf.add_object(structure_root)
    structure_document = pydyf.Dictionary({
        'Type': '/StructElem',
        'S': '/Document',
        'K': pydyf.Array(),
        'P': structure_root.reference,
    })
    pdf.add_object(structure_document)
    structure_root['K'] = pydyf.Array([structure_document.reference])
    pdf.catalog['StructTreeRoot'] = structure_root.reference

    content_mapping['Nums'] = pydyf.Array()
    links = []
    for page_number, page in enumerate(document.pages):
        elements = []
        content_mapping['Nums'].append(page_number)
        content_mapping['Nums'].append(pydyf.Array())
        for mcid, marked in enumerate(page._page_box.marked):
            parent = structure_document if mcid == 0 else elements[marked['parent']]
            tag, box = marked['tag'], marked['box']
            element = pydyf.Dictionary({
                'Type': '/StructElem',
                'S': f'/{tag}',
                'K': pydyf.Array([mcid]),
                'Pg': pdf.page_references[page_number],
                'P': parent.reference,
            })
            pdf.add_object(element)
            if tag == 'LI':
                if box.element.tag == 'dt':
                    sub_key = 'Lbl'
                else:
                    sub_key = 'LBody'
                real_element = pydyf.Dictionary({
                    'Type': '/StructElem',
                    'S': f'/{sub_key}',
                    'K': pydyf.Array([mcid]),
                    'Pg': pdf.page_references[page_number],
                    'P': element.reference,
                })
                pdf.add_object(real_element)
                element['K'] = pydyf.Array([real_element.reference])
            elif tag == 'Figure':
                if box.element.tag == 'img' and 'alt' in box.element.attrib:
                    element['Alt'] = pydyf.String(box.element.attrib['alt'])
            elements.append(element)
            content_mapping['Nums'][-1].append(element.reference)
            if marked['tag'] == 'Link':
                annotation = box.link_annotation
                object_reference = pydyf.Dictionary({
                    'Type': '/OBJR',
                    'Obj': annotation.reference,
                    'Pg': pdf.page_references[page_number],
                })
                pdf.add_object(object_reference)
                links.append((object_reference.reference, annotation))
        structure_document['K'].append(elements[0].reference)
    for i, (link, annotation) in enumerate(links, start=len(document.pages)):
        content_mapping['Nums'].append(i)
        content_mapping['Nums'].append(link)
        annotation['StructParent'] = i
        annotation['F'] = 2 ** (2 - 1)

    # Common PDF metadata stream
    add_metadata(pdf, metadata, 'ua', 1, conformance=None, compress=compress)

    # PDF document extra metadata
    if 'Lang' not in pdf.catalog:
        pdf.catalog['Lang'] = pydyf.String()
    pdf.catalog['ViewerPreferences'] = pydyf.Dictionary({
        'DisplayDocTitle': 'true',
    })
    pdf.catalog['MarkInfo'] = pydyf.Dictionary({'Marked': 'true'})


VARIANTS = {'pdf/ua-1': (pdfua, {'mark': True})}
