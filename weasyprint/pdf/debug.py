"""PDF generation with debug information."""

import pydyf

from ..matrix import Matrix


def debug(pdf, metadata, document, page_streams, attachments, compress):
    """Set debug PDF metadata."""

    # Add links on ids.
    pages = zip(pdf.pages['Kids'][::3], document.pages, page_streams)
    for pdf_page_number, document_page, stream in pages:
        if not document_page.anchors:
            continue

        page = pdf.objects[pdf_page_number]
        if 'Annots' not in page:
            page['Annots'] = pydyf.Array()

        for id, (x1, y1, x2, y2) in document_page.anchors.items():
            # TODO: handle zoom correctly.
            matrix = Matrix(0.75, 0, 0, 0.75) @ stream.ctm
            x1, y1 = matrix.transform_point(x1, y1)
            x2, y2 = matrix.transform_point(x2, y2)
            annotation = pydyf.Dictionary({
                'Type': '/Annot',
                'Subtype': '/Link',
                'Rect': pydyf.Array([x1, y1, x2, y2]),
                'BS': pydyf.Dictionary({'W': 0}),
                'P': page.reference,
                'T': pydyf.String(id),  # id added as metadata
            })

            # The next line makes all of this relevent to use
            # with PDFjs
            annotation['Dest'] = pydyf.String(id)

            pdf.add_object(annotation)
            page['Annots'].append(annotation.reference)


VARIANTS = {'debug': (debug, {})}
