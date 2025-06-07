"""PDF/UA generation."""

from .metadata import add_metadata


def pdfua(pdf, metadata, document, page_streams, attachments, compress):
    """Set metadata for PDF/UA documents."""
    # Common PDF metadata stream
    add_metadata(pdf, metadata, 'ua', 1, conformance=None, compress=compress)


VARIANTS = {
    'pdf/ua-1': (pdfua, {'version': '1.7', 'pdf_tags': True}),
    'pdf/ua-2': (pdfua, {'version': '2.0', 'pdf_tags': True}),
}
