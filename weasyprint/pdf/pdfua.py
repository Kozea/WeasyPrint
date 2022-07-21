"""PDF/UA generation."""

import pydyf

from ..logger import LOGGER
from .metadata import add_metadata


def pdfua(pdf, metadata, pages, page_streams):
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

    elements = []
    content_mapping['Nums'] = pydyf.Array()
    links = []
    for page_number, page_stream in enumerate(page_streams):
        page_elements = []
        for mcid, (key, box) in enumerate(page_stream.marked):
            kids = [mcid]
            if key == 'Link':
                reference = pydyf.Dictionary({
                    'Type': '/OBJR',
                    'Obj': box.link_annotation.reference,
                })
                pdf.add_object(reference)
                kids.append(reference.reference)
            element = pydyf.Dictionary({
                'Type': '/StructElem',
                'S': f'/{key}',
                'P': structure_document.reference,
                'Pg': f'{pdf.pages["Kids"][3 * page_number]} 0 R',
                'K': pydyf.Array(kids)
            })
            pdf.add_object(element)
            page_elements.append(element.reference)
            if key == 'Link':
                links.append((element.reference, box.link_annotation))
        content_mapping['Nums'].append(page_number)
        content_mapping['Nums'].append(pydyf.Array(page_elements))
        elements.extend(page_elements)
    structure_document['K'] = pydyf.Array(elements)
    for i, (link, annotation) in enumerate(links, start=page_number + 1):
        content_mapping['Nums'].append(i)
        content_mapping['Nums'].append(link)
        annotation['StructParent'] = i

    # Common PDF metadata stream
    add_metadata(pdf, metadata, 'ua', version=1, conformance=None)

    # PDF document extra metadata
    # TODO: that’s a dirty way to get the document root’s language
    pdf.catalog['Lang'] = pydyf.String(pages[0]._page_box.style['lang'])
    pdf.catalog['ViewerPreferences'] = pydyf.Dictionary({
        'DisplayDocTitle': 'true',
    })


VARIANTS = {'pdf/ua-1': (pdfua, {'mark': True})}
