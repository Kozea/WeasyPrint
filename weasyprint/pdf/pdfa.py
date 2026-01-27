"""PDF/A generation."""

from functools import partial

import pydyf


def pdfa(pdf, document, page_streams, attachments, compress, version, variant):
    """Set metadata for PDF/A documents."""

    # Handle attachments.
    if version == 1:
        # Remove embedded files dictionary.
        if 'Names' in pdf.catalog and 'EmbeddedFiles' in pdf.catalog['Names']:
            del pdf.catalog['Names']['EmbeddedFiles']
    if version <= 2:
        # Remove attachments.
        for pdf_object in pdf.objects:
            if not isinstance(pdf_object, dict):
                continue
            if pdf_object.get('Type') != '/Filespec':
                continue
            reference = int(pdf_object['EF']['F'].split()[0])
            stream = pdf.objects[reference]
            # Remove all attachments for version 1.
            # Remove non-PDF attachments for version 2.
            # TODO: check that PDFs are actually PDF/A-2+ files.
            if version == 1 or stream.extra['Subtype'] != '/application#2fpdf':
                del pdf_object['EF']
    if version >= 3:
        # Add AF for attachments.
        relationships = {
            f'<{attachment.md5}>': attachment.relationship
            for attachment in attachments if attachment.md5}
        pdf_attachments = []
        if 'Names' in pdf.catalog and 'EmbeddedFiles' in pdf.catalog['Names']:
            reference = int(pdf.catalog['Names']['EmbeddedFiles'].split()[0])
            names = pdf.objects[reference]
            for name in names['Names'][1::2]:
                pdf_attachments.append(name)
        for pdf_object in pdf.objects:
            if not isinstance(pdf_object, dict):
                continue
            if pdf_object.get('Type') != '/Filespec':
                continue
            reference = int(pdf_object['EF']['F'].split()[0])
            checksum = pdf.objects[reference].extra['Params']['CheckSum']
            relationship = relationships.get(checksum, 'Unspecified')
            pdf_object['AFRelationship'] = f'/{relationship}'
            pdf_attachments.append(pdf_object.reference)
        if pdf_attachments:
            if 'AF' not in pdf.catalog:
                pdf.catalog['AF'] = pydyf.Array()
            pdf.catalog['AF'].extend(pdf_attachments)

    # Print annotations.
    for pdf_object in pdf.objects:
        if isinstance(pdf_object, dict) and pdf_object.get('Type') == '/Annot':
            pdf_object['F'] = 2 ** (3 - 1)

    # Common PDF metadata stream.
    if version == 1:
        # Metadata compression is forbidden for version 1.
        compress = False
    document.metadata.include_in_pdf(pdf, 'a', version, variant, compress)

    # Remove document information.
    if version >= 4:
        pdf.info.clear()


def _values(version, pdf_tags=None):
    values = {'pdf_version': version, 'pdf_identifier': True, 'output_intent': 'sRGB'}
    if pdf_tags is not None:
        values['pdf_tags'] = pdf_tags
    return values


VARIANTS = {
    'pdf/a-1b': (partial(pdfa, version=1, variant='B'), _values('1.4')),
    'pdf/a-2b': (partial(pdfa, version=2, variant='B'), _values('1.7')),
    'pdf/a-3b': (partial(pdfa, version=3, variant='B'), _values('1.7')),
    'pdf/a-2u': (partial(pdfa, version=2, variant='U'), _values('1.7')),
    'pdf/a-3u': (partial(pdfa, version=3, variant='U'), _values('1.7')),
    'pdf/a-4u': (partial(pdfa, version=4, variant='U'), _values('2.0')),
    'pdf/a-1a': (partial(pdfa, version=1, variant='A'), _values('1.4', pdf_tags=True)),
    'pdf/a-2a': (partial(pdfa, version=2, variant='A'), _values('1.7', pdf_tags=True)),
    'pdf/a-3a': (partial(pdfa, version=3, variant='A'), _values('1.7', pdf_tags=True)),
    'pdf/a-4e': (partial(pdfa, version=4, variant='E'), _values('2.0')),
    'pdf/a-4f': (partial(pdfa, version=4, variant='F'), _values('2.0')),
}
