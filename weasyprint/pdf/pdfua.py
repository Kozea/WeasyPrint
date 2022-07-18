"""PDF/UA generation."""

import pydyf

from ..logger import LOGGER
from .metadata import add_metadata


def pdfua(pdf, pages, metadata, version):
    """Set metadata for PDF/UA documents."""
    LOGGER.warning(
        'PDF/UA support is experimental, '
        'generated PDF files are not guaranteed to be valid. '
        'Please open an issue if you have problems generating PDF/UA files.')

    # TODO: that’s a dirty way to get the document root’s language
    pdf.catalog['Lang'] = pydyf.String(pages[0]._page_box.style['lang'])
    pdf.catalog['ViewerPreferences'] = pydyf.Dictionary({
        'DisplayDocTitle': 'true',
    })

    add_metadata(pdf, metadata, 'ua', version, conformance=None)


VARIANTS = {
    'pdf/ua-1': lambda pdf, pages, metadata: pdfua(pdf, pages, metadata, 1),
}
