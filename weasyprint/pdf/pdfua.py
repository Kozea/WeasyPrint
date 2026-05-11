"""PDF/UA generation."""

from functools import partial


def pdfua(pdf, metadata, document, page_streams, attachments, compress, version):
    """Set metadata for PDF/UA documents."""
    # Common PDF metadata stream
    conformance = f'PDF/UA-{version}' if version >= 2 else None
    metadata.include_in_pdf(
        pdf, 'ua', version, conformance=conformance, compress=compress)


VARIANTS = {
    'pdf/ua-1': (partial(pdfua, version=1), {'version': '1.7', 'pdf_tags': True}),
    'pdf/ua-2': (partial(pdfua, version=2), {'version': '2.0', 'pdf_tags': True}),
}
