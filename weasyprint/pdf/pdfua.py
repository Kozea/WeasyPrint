"""PDF/UA generation."""

from functools import partial


def pdfua(pdf, document, page_streams, attachments, compress, version):
    """Set metadata for PDF/UA documents."""
    # Common PDF metadata stream
    document.metadata.include_in_pdf(
        pdf, 'ua', version, conformance=None, compress=compress)


VARIANTS = {
    'pdf/ua-1': (partial(pdfua, version=1), {'pdf_version': '1.7', 'pdf_tags': True}),
    'pdf/ua-2': (partial(pdfua, version=2), {'pdf_version': '2.0', 'pdf_tags': True}),
}
