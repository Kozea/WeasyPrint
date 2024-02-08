"""PDF/A generation."""

try:
    # Available in Python 3.9+
    from importlib.resources import files
except ImportError:
    # Deprecated in Python 3.11+
    from importlib.resources import read_binary
else:
    def read_binary(package, resource):
        return (files(package) / resource).read_bytes()

from functools import partial

import pydyf

from .metadata import add_metadata


def pdfa(pdf, metadata, document, page_streams, attachments, compress,
         version):
    """Set metadata for PDF/A documents."""
    # Add ICC profile.
    profile = pydyf.Stream(
        [read_binary(__package__, 'sRGB2014.icc')],
        pydyf.Dictionary({'N': 3, 'Alternate': '/DeviceRGB'}),
        compress=compress)
    pdf.add_object(profile)
    pdf.catalog['OutputIntents'] = pydyf.Array([
        pydyf.Dictionary({
            'Type': '/OutputIntent',
            'S': '/GTS_PDFA1',
            'OutputConditionIdentifier': pydyf.String('sRGB IEC61966-2.1'),
            'DestOutputProfile': profile.reference,
        }),
    ])

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
    add_metadata(pdf, metadata, 'a', version, 'B', compress)


VARIANTS = {
    f'pdf/a-{i}b': (partial(pdfa, version=i), {'version': pdf_version})
    for i, pdf_version in enumerate(('1.4', '1.7', '1.7', '2.0'), start=1)}
