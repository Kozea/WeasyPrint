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

    structure = {}
    document.build_element_structure(structure)

    elements = []
    content_mapping['Nums'] = pydyf.Array()
    for page_number, page_stream in enumerate(page_streams):
        page_elements = []
        for mcid, (key, box) in enumerate(page_stream.marked):
            # Build structure elements
            kid = mcid
            etree_element = box.element
            child_structure_data_element = None
            while True:
                if etree_element is None:
                    structure_data = structure.setdefault(
                        box, {'parent': None, 'children': ()})
                else:
                    structure_data = structure[etree_element]
                new_element = 'element' not in structure_data
                if new_element:
                    structure_data['element'] = pydyf.Dictionary({
                        'Type': '/StructElem',
                        'S': f'/{key}',
                        'K': pydyf.Array([kid])
                    })
                    pdf.add_object(structure_data['element'])
                else:
                    structure_data['element']['K'].append(kid)
                kid = structure_data['element'].reference
                if child_structure_data_element is not None:
                    child_structure_data_element['P'] = kid
                if not new_element:
                    break
                page_elements.append(kid)
                child_structure_data_element = structure_data['element']
                if structure_data['parent'] is None:
                    structure_data['element']['P'] = (
                        structure_document.reference)
                    break
                else:
                    etree_element = structure_data['parent']
        content_mapping['Nums'].append(page_number)
        content_mapping['Nums'].append(pydyf.Array(page_elements))
        elements.extend(page_elements)
    structure_document['K'] = pydyf.Array(elements)

    # Common PDF metadata stream
    add_metadata(pdf, metadata, 'ua', version=1, conformance=None)

    # PDF document extra metadata
    # TODO: that’s a dirty way to get the document root’s language
    pdf.catalog['Lang'] = pydyf.String(
        document.pages[0]._page_box.style['lang'])
    pdf.catalog['ViewerPreferences'] = pydyf.Dictionary({
        'DisplayDocTitle': 'true',
    })


VARIANTS = {'pdf/ua-1': (pdfua, {'mark': True})}
