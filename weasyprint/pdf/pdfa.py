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

from ..logger import LOGGER
from .metadata import add_metadata


def pdfa(pdf, metadata, document, page_streams, version):
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

    # Print annotations
    for pdf_object in pdf.objects:
        if isinstance(pdf_object, dict) and pdf_object.get('Type') == '/Annot':
            pdf_object['F'] = 2 ** (3 - 1)

    # Common PDF metadata stream
    add_metadata(pdf, metadata, 'a', version, 'B')


VARIANTS = {
    f'pdf/a-{i}b': (partial(pdfa, version=i), {'version': pdf_version})
    for i, pdf_version in enumerate(('1.4', '1.7', '1.7', '2.0'), start=1)}
