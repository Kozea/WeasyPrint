"""PDF/X generation."""

from functools import partial

import pydyf

from .metadata import add_metadata


def pdfx(pdf, metadata, document, page_streams, attachments, compress, version,
         variant):
    """Set metadata for PDF/X documents."""
    conformance = f'PDF/X-{version}{variant}'
    pdf.info['GTS_PDFXVersion'] = pydyf.String(conformance)
    pdf.info['GTS_PDFXConformance'] = pydyf.String(conformance)
    # Common PDF metadata stream
    add_metadata(pdf, metadata, 'x', version, conformance, compress=compress)


VARIANTS = {
    'pdf/x-3:2003': (partial(pdfx, version=3, variant=':2003'), {'version': '1.4'}),
}
