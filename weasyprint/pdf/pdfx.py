"""PDF/X generation."""

from functools import partial
from time import localtime

import pydyf


def pdfx(pdf, metadata, document, page_streams, attachments, compress, version,
         variant):
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
    if not metadata.modified:
        metadata.modified = now_iso
        pdf.info['ModDate'] = now_pdf
    if not metadata.created:
        metadata.created = now_iso
        pdf.info['CreationDate'] = now_pdf

    # Add output intents.
    if 'device-cmyk' not in document.color_profiles:
        # Add standard CMYK profile.
        pdf.catalog['OutputIntents'] = pydyf.Array([
            pydyf.Dictionary({
                'Type': '/OutputIntent',
                'S': '/GTS_PDFX',
                'OutputConditionIdentifier': pydyf.String('CGATS TR 001'),
                'RegistryName': pydyf.String('http://www.color.org'),
            }),
        ])

    # Common PDF metadata stream.
    metadata.include_in_pdf(pdf, 'x', version, conformance, compress=compress)


VARIANTS = {
    'pdf/x-1a': (
        partial(pdfx, version=1, variant='a:2003'),
        {'version': '1.4', 'identifier': True},
    ),
    'pdf/x-3': (
        partial(pdfx, version=3, variant=':2003'),
        {'version': '1.4', 'identifier': True},
    ),
    'pdf/x-4': (
        partial(pdfx, version=4, variant=''),
        {'version': '1.6', 'identifier': True},
    ),
    'pdf/x-5g': (
        partial(pdfx, version=5, variant='g'),
        {'version': '1.6', 'identifier': True},
    ),
    # TODO: these variants forbid OutputIntent to include ICC file.
    # 'pdf/x-4p': (
    #     partial(pdfx, version=4, variant='p'),
    #     {'version': '1.6', 'identifier': True},
    # ),
    # 'pdf/x-5pg': (
    #     partial(pdfx, version=5, variant='pg'),
    #     {'version': '1.6', 'identifier': True},
    # ),
    # 'pdf/x-5n': (
    #     partial(pdfx, version=5, variant='n'),
    #     {'version': '1.6', 'identifier': True},
    # ),
}
