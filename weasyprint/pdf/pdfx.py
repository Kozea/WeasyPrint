"""PDF/X generation."""

from functools import partial
from time import localtime

import pydyf


def pdfx(pdf, document, page_streams, attachments, compress, version, variant):
    """Set metadata for PDF/X documents."""

    # Add conformance metadata.
    conformance = f'PDF/X-{version}{variant}'
    if version < 4:
        pdf.info['GTS_PDFXVersion'] = pydyf.String(conformance)
        pdf.info['GTS_PDFXConformance'] = pydyf.String(conformance)
    pdf.info['Trapped'] = '/False'
    now = localtime()
    year, month, day, hour, minute, second = now[:6]
    tz_hour, tz_minute = divmod(now.tm_gmtoff, 3600)
    now_iso = (
        f'{year:04}-{month:02}-{day:02}T{hour:02}:{minute:02}:{second:02}'
        f'{tz_hour:+03}:{tz_minute:02}')
    now_pdf = (
        f'(D:{year:04}{month:02}{day:02}{hour:02}{minute:02}{second:02}'
        f"{tz_hour:+03}'{tz_minute:02}')")
    if not document.metadata.modified:
        document.metadata.modified = now_iso
        pdf.info['ModDate'] = now_pdf
    if not document.metadata.created:
        document.metadata.created = now_iso
        pdf.info['CreationDate'] = now_pdf

    # Common PDF metadata stream.
    document.metadata.include_in_pdf(pdf, 'x', version, conformance, compress=compress)

    # Add output intents.
    intents = pydyf.Dictionary({
        'Type': '/OutputIntent',
        'S': '/GTS_PDFX',
        'OutputConditionIdentifier': pydyf.String('CGATS TR 001'),
    }),
    pdf.catalog['OutputIntents'] = pydyf.Array([intents])
    allow_inclusion = not ('p' in variant or 'n' in variant)
    if allow_inclusion and document.output_intent in document.color_profiles:
        color_profile = document.color_profile[document.output_intent]
        intents['OutputConditionIdentifier'] = pydyf.String(color_profile.name)
        intents['Info'] = pydyf.String(color_profile.name)
        intents['DestOutputProfile'] = color_profile.pdf_reference
    elif document.output_intent:
        intents['OutputConditionIdentifier'] = pydyf.String(document.output_intent)


def _values(version):
    output = 'CGATS TR 001'
    return {'pdf_version': version, 'pdf_identifier': True, 'output_intent': output}


VARIANTS = {
    'pdf/x-1a': (partial(pdfx, version=1, variant='a:2003'), _values('1.4')),
    'pdf/x-3': (partial(pdfx, version=3, variant=':2003'), _values('1.4')),
    'pdf/x-4': (partial(pdfx, version=4, variant=''), _values('1.6')),
    'pdf/x-4p': (partial(pdfx, version=4, variant='p'), _values('1.6')),
    'pdf/x-5g': (partial(pdfx, version=5, variant='g'), _values('1.6')),
    'pdf/x-5pg': (partial(pdfx, version=5, variant='pg'), _values('1.6')),
    'pdf/x-5n': (partial(pdfx, version=5, variant='n'), _values('1.6')),
}
