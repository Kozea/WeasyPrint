"""PDF/A generation."""

from importlib.resources import read_binary

import pydyf

from ..logger import LOGGER
from .metadata import add_metadata


def pdfa(pdf, metadata, version):
    """Set metadata for PDF/A documents."""
    LOGGER.warning(
        'PDF/A support is experimental, '
        'generated PDF files are not guaranteed to be valid. '
        'Please open an issue if you have problems generating PDF/A files.')

    # Add ICC profile
    profile = pydyf.Stream(
        [read_binary(__package__, 'sRGB2014.icc')],
        pydyf.Dictionary({'N': 3, 'Alternate': '/DeviceRGB'}),
        compress=True)
    pdf.add_object(profile)
    pdf.catalog['OutputIntents'] = pydyf.Array([
        pydyf.Dictionary({
            'Type': '/OutputIntent',
            'S': '/GTS_PDFA1',
            'OutputConditionIdentifier': pydyf.String('sRGB IEC61966-2.1'),
            'DestOutputProfile': profile.reference,
        }),
    ])

    # Set PDF version
    if version == 1:
        pdf.version = b'1.4'
    elif version in (2, 3):
        pdf.version = b'1.7'
    else:
        pdf.version = b'2.0'

    add_metadata(pdf, metadata, 'a', version, 'B')


VARIANTS = {
    'pdf/a-1b': lambda pdf, pages, metadata: pdfa(pdf, metadata, 1),
    'pdf/a-2b': lambda pdf, pages, metadata: pdfa(pdf, metadata, 2),
    'pdf/a-3b': lambda pdf, pages, metadata: pdfa(pdf, metadata, 3),
    'pdf/a-4b': lambda pdf, pages, metadata: pdfa(pdf, metadata, 4),
}
