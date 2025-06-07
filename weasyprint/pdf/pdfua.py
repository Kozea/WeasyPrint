"""PDF/UA generation."""

import pydyf

from ..logger import LOGGER
from .metadata import add_metadata


def pdfua(pdf, metadata, document, page_streams, attachments, compress):
    """Set metadata for PDF/UA documents."""
    # Common PDF metadata stream
    add_metadata(pdf, metadata, 'ua', 1, conformance=None, compress=compress)

    # PDF document extra metadata
    if 'Lang' not in pdf.catalog:
        LOGGER.error('Missing required "lang" attribute at the root of the document')
        pdf.catalog['Lang'] = pydyf.String()


VARIANTS = {'pdf/ua-1': (pdfua, {'pdf_tags': True})}
