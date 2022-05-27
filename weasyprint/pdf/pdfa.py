"""PDF/A generation."""

from xml.etree import ElementTree

import pydyf

from .. import __version__

# XML namespaces used for metadata
NS = {
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'xmp': 'http://ns.adobe.com/xap/1.0/',
    'pdf': 'http://ns.adobe.com/pdf/1.3/',
    'pdfaid': 'http://www.aiim.org/pdfa/ns/id/',
}
for key, value in NS.items():
    ElementTree.register_namespace(key, value)


def pdf_2b(pdf, metadata):
    # Add ICC profile
    profile = pydyf.Stream(
        [open('/tmp/icc', 'rb').read()],
        pydyf.Dictionary({'N': 3, 'Alternate': '/DeviceRGB'}),
        compress=True,
    )
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
    rdf = ElementTree.Element(f'{{{NS["rdf"]}}}RDF')

    element = ElementTree.SubElement(rdf, f'{{{NS["rdf"]}}}Description')
    element.attrib[f'{{{NS["pdfaid"]}}}part'] = '2'
    element.attrib[f'{{{NS["pdfaid"]}}}conformance'] = 'B'

    element = ElementTree.SubElement(rdf, f'{{{NS["rdf"]}}}Description')
    element.attrib[f'{{{NS["pdf"]}}}Producer'] = f'WeasyPrint {__version__}'

    if metadata.title:
        element = ElementTree.SubElement(
            rdf, f'{{{NS["rdf"]}}}Description')
        element = ElementTree.SubElement(element, f'{{{NS["dc"]}}}title')
        element = ElementTree.SubElement(element, f'{{{NS["rdf"]}}}Alt')
        element = ElementTree.SubElement(element, f'{{{NS["rdf"]}}}li')
        element.attrib['xml:lang'] = 'x-default'
        element.text = metadata.title
    if metadata.authors:
        element = ElementTree.SubElement(rdf, f'{{{NS["rdf"]}}}Description')
        element = ElementTree.SubElement(element, f'{{{NS["dc"]}}}creator')
        element = ElementTree.SubElement(element, f'{{{NS["rdf"]}}}Seq')
        for author in metadata.authors:
            author_element = ElementTree.SubElement(
                element, f'{{{NS["rdf"]}}}li')
            author_element.text = author
    if metadata.description:
        element = ElementTree.SubElement(
            rdf, f'{{{NS["rdf"]}}}Description')
        element = ElementTree.SubElement(element, f'{{{NS["dc"]}}}subject')
        element = ElementTree.SubElement(element, f'{{{NS["rdf"]}}}Bag')
        element = ElementTree.SubElement(element, f'{{{NS["rdf"]}}}li')
        element.text = metadata.description
    if metadata.keywords:
        element = ElementTree.SubElement(rdf, f'{{{NS["rdf"]}}}Description')
        element = ElementTree.SubElement(element, f'{{{NS["pdf"]}}}Keywords')
        element.text = ', '.join(metadata.keywords)
    if metadata.generator:
        element = ElementTree.SubElement(rdf, f'{{{NS["rdf"]}}}Description')
        element = ElementTree.SubElement(
            element, f'{{{NS["xmp"]}}}CreatorTool')
        element.text = metadata.generator
    if metadata.created:
        element = ElementTree.SubElement(rdf, f'{{{NS["rdf"]}}}Description')
        element = ElementTree.SubElement(element, f'{{{NS["xmp"]}}}CreateDate')
        element.text = metadata.created
    if metadata.modified:
        element = ElementTree.SubElement(rdf, f'{{{NS["rdf"]}}}Description')
        element = ElementTree.SubElement(element, f'{{{NS["xmp"]}}}ModifyDate')
        element.text = metadata.modified
    xml = ElementTree.tostring(rdf, encoding='utf-8')
    metadata = pydyf.Stream(
        [xml], extra={'Type': '/Metadata', 'Subtype': '/XML'})
    pdf.add_object(metadata)
    pdf.catalog['Metadata'] = metadata.reference
