"""PDF/UA generation."""

import pydyf

from ..logger import LOGGER
from .metadata import add_metadata


def pdfua(pdf, metadata, document, page_streams):
    """Set metadata for PDF/UA documents."""
    LOGGER.warning(
        'PDF/UA support is experimental, '
        'generated PDF files are not guaranteed to be valid. '
        'Please open an issue if you have problems generating PDF/UA files.')

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
        'P': structure_root.reference,
    })
    pdf.add_object(structure_document)
    structure_root['K'] = pydyf.Array([structure_document.reference])
    pdf.catalog['StructTreeRoot'] = structure_root.reference

    document_children = []
    content_mapping['Nums'] = pydyf.Array()
    links = []
    for page_number, page_stream in enumerate(page_streams):
        structure = {}
        document.build_element_structure(structure)
        parents = [None] * len(page_stream.marked)
        for mcid, (key, box) in enumerate(page_stream.marked):
            # Build structure elements
            kids = [mcid]
            if key == 'Link':
                object_reference = pydyf.Dictionary({
                    'Type': '/OBJR',
                    'Obj': box.link_annotation.reference,
                    'Pg': pdf.page_references[page_number],
                })
                pdf.add_object(object_reference)
                links.append((object_reference.reference, box.link_annotation))
            etree_element = box.element
            child_structure_data_element = None
            while True:
                if etree_element is None:
                    structure_data = structure.setdefault(
                        box, {'parent': None})
                else:
                    structure_data = structure[etree_element]
                new_element = 'element' not in structure_data
                if new_element:
                    child = structure_data['element'] = pydyf.Dictionary({
                        'Type': '/StructElem',
                        'S': f'/{key}',
                        'K': pydyf.Array(kids),
                        'Pg': pdf.page_references[page_number],
                    })
                    pdf.add_object(child)
                    if key == 'LI':
                        if etree_element.tag == 'dt':
                            sub_key = 'Lbl'
                        else:
                            sub_key = 'LBody'
                        real_child = pydyf.Dictionary({
                            'Type': '/StructElem',
                            'S': f'/{sub_key}',
                            'K': pydyf.Array(kids),
                            'Pg': pdf.page_references[page_number],
                            'P': child.reference,
                        })
                        pdf.add_object(real_child)
                        for kid in kids:
                            if isinstance(kid, int):
                                parents[kid] = real_child.reference
                        child['K'] = pydyf.Array([real_child.reference])
                        structure_data['element'] = real_child
                    else:
                        for kid in kids:
                            if isinstance(kid, int):
                                parents[kid] = child.reference
                else:
                    child = structure_data['element']
                    child['K'].extend(kids)
                    for kid in kids:
                        if isinstance(kid, int):
                            parents[kid] = child.reference
                kid = child.reference
                if child_structure_data_element is not None:
                    child_structure_data_element['P'] = kid
                if not new_element:
                    break
                kids = [kid]
                child_structure_data_element = child
                if structure_data['parent'] is None:
                    child['P'] = structure_document.reference
                    document_children.append(child.reference)
                    break
                else:
                    etree_element = structure_data['parent']
                key = page_stream.get_marked_content_tag(etree_element.tag)
        content_mapping['Nums'].append(page_number)
        content_mapping['Nums'].append(pydyf.Array(parents))
    structure_document['K'] = pydyf.Array(document_children)
    for i, (link, annotation) in enumerate(links, start=page_number + 1):
        content_mapping['Nums'].append(i)
        content_mapping['Nums'].append(link)
        annotation['StructParent'] = i
        annotation['F'] = 2 ** (2 - 1)

    # Common PDF metadata stream
    add_metadata(pdf, metadata, 'ua', version=1, conformance=None)

    # PDF document extra metadata
    if 'Lang' not in pdf.catalog:
        pdf.catalog['Lang'] = pydyf.String()
    pdf.catalog['ViewerPreferences'] = pydyf.Dictionary({
        'DisplayDocTitle': 'true',
    })
    pdf.catalog['MarkInfo'] = pydyf.Dictionary({'Marked': 'true'})


VARIANTS = {'pdf/ua-1': (pdfua, {'mark': True})}
