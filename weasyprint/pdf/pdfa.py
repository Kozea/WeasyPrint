"""PDF/A generation."""

from importlib.resources import read_binary
from xml.etree.ElementTree import (
    Element, SubElement, register_namespace, tostring)

import pydyf

from .. import __version__
from ..logger import LOGGER

# XML namespaces used for metadata
NS = {
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'xmp': 'http://ns.adobe.com/xap/1.0/',
    'pdf': 'http://ns.adobe.com/pdf/1.3/',
    'pdfaid': 'http://www.aiim.org/pdfa/ns/id/',
}
for key, value in NS.items():
    register_namespace(key, value)


def pdfa(pdf, metadata, version):
    """Set metadata for PDF/A documents."""
    LOGGER.warning(
        'PDF/A support is experimental, '
        'generated PDF files are not guaranteed to be valid. '
        'Please open an issue if you have problems generating PDF/A files.')

    # Set PDF version
    if version == 1:
        pdf.version = b'1.4'
    elif version in (2, 3):
        pdf.version = b'1.7'
    else:
        pdf.version = b'2.0'

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

    # Add metadata
    rdf = Element(f'{{{NS["rdf"]}}}RDF')

    element = SubElement(rdf, f'{{{NS["rdf"]}}}Description')
    element.attrib[f'{{{NS["rdf"]}}}about'] = ''
    element.attrib[f'{{{NS["pdfaid"]}}}part'] = str(version)
    element.attrib[f'{{{NS["pdfaid"]}}}conformance'] = 'B'

    element = SubElement(rdf, f'{{{NS["rdf"]}}}Description')
    element.attrib[f'{{{NS["rdf"]}}}about'] = ''
    element.attrib[f'{{{NS["pdf"]}}}Producer'] = f'WeasyPrint {__version__}'

    if metadata.title:
        element = SubElement(rdf, f'{{{NS["rdf"]}}}Description')
        element.attrib[f'{{{NS["rdf"]}}}about'] = ''
        element = SubElement(element, f'{{{NS["dc"]}}}title')
        element = SubElement(element, f'{{{NS["rdf"]}}}Alt')
        element = SubElement(element, f'{{{NS["rdf"]}}}li')
        element.attrib['xml:lang'] = 'x-default'
        element.text = metadata.title
    if metadata.authors:
        element = SubElement(rdf, f'{{{NS["rdf"]}}}Description')
        element.attrib[f'{{{NS["rdf"]}}}about'] = ''
        element = SubElement(element, f'{{{NS["dc"]}}}creator')
        element = SubElement(element, f'{{{NS["rdf"]}}}Seq')
        for author in metadata.authors:
            author_element = SubElement(element, f'{{{NS["rdf"]}}}li')
            author_element.text = author
    if metadata.description:
        element = SubElement(rdf, f'{{{NS["rdf"]}}}Description')
        element.attrib[f'{{{NS["rdf"]}}}about'] = ''
        element = SubElement(element, f'{{{NS["dc"]}}}subject')
        element = SubElement(element, f'{{{NS["rdf"]}}}Bag')
        element = SubElement(element, f'{{{NS["rdf"]}}}li')
        element.text = metadata.description
    if metadata.keywords:
        element = SubElement(rdf, f'{{{NS["rdf"]}}}Description')
        element.attrib[f'{{{NS["rdf"]}}}about'] = ''
        element = SubElement(element, f'{{{NS["pdf"]}}}Keywords')
        element.text = ', '.join(metadata.keywords)
    if metadata.generator:
        element = SubElement(rdf, f'{{{NS["rdf"]}}}Description')
        element.attrib[f'{{{NS["rdf"]}}}about'] = ''
        element = SubElement(element, f'{{{NS["xmp"]}}}CreatorTool')
        element.text = metadata.generator
    if metadata.created:
        element = SubElement(rdf, f'{{{NS["rdf"]}}}Description')
        element.attrib[f'{{{NS["rdf"]}}}about'] = ''
        element = SubElement(element, f'{{{NS["xmp"]}}}CreateDate')
        element.text = metadata.created
    if metadata.modified:
        element = SubElement(rdf, f'{{{NS["rdf"]}}}Description')
        element.attrib[f'{{{NS["rdf"]}}}about'] = ''
        element = SubElement(element, f'{{{NS["xmp"]}}}ModifyDate')
        element.text = metadata.modified
    xml = tostring(rdf, encoding='utf-8')
    header = b'<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>'
    footer = b'<?xpacket end="r"?>'
    stream_content = b'\n'.join((header, xml, footer))
    extra = {'Type': '/Metadata', 'Subtype': '/XML'}
    metadata = pydyf.Stream([stream_content], extra=extra)
    pdf.add_object(metadata)
    pdf.catalog['Metadata'] = metadata.reference


VARIANTS = {
    'pdf/a-1b': lambda pdf, metadata: pdfa(pdf, metadata, 1),
    'pdf/a-2b': lambda pdf, metadata: pdfa(pdf, metadata, 2),
    'pdf/a-3b': lambda pdf, metadata: pdfa(pdf, metadata, 3),
    'pdf/a-4b': lambda pdf, metadata: pdfa(pdf, metadata, 4),
}
