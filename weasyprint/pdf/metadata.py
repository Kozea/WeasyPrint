"""
PDF metadata stream generation.
"""

from typing import TYPE_CHECKING
from xml.etree.ElementTree import Element, SubElement, register_namespace, tostring

import pydyf

from weasyprint import __version__

if TYPE_CHECKING:
    from weasyprint.document import DocumentMetadata


# XML namespaces used for metadata
NS: dict[str, str] = {
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'xmp': 'http://ns.adobe.com/xap/1.0/',
    'pdf': 'http://ns.adobe.com/pdf/1.3/',
    'pdfaid': 'http://www.aiim.org/pdfa/ns/id/',
    'pdfuaid': 'http://www.aiim.org/pdfua/ns/id/',
}
for key, value in NS.items():
    register_namespace(key, value)


def add_metadata(
    pdf: pydyf.PDF,
    metadata: 'DocumentMetadata',
    variant: str,
    version: str,
    conformance: str,
    compress: bool,
) -> None:
    """Add PDF stream of metadata.

    Described in ISO-32000-1:2008, 14.3.2.

    """
    # Add metadata. If `DocumentMetadata` has a generator, we will use it,
    # otherwise we will use the default generator.
    if metadata.rdf_metadata_generator is None:
        xml_data = generate_rdf_metadata(metadata, variant, version, conformance)
    else:
        xml_data = metadata.rdf_metadata_generator(
            metadata=metadata,
            variant=variant,
            version=version,
            conformance=conformance,
        )

    header = b'<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>'
    footer = b'<?xpacket end="r"?>'
    stream_content = b'\n'.join((header, xml_data, footer))
    extra = {'Type': '/Metadata', 'Subtype': '/XML'}
    metadata = pydyf.Stream([stream_content], extra, compress)
    pdf.add_object(metadata)
    pdf.catalog['Metadata'] = metadata.reference


def generate_rdf_metadata(
    metadata: 'DocumentMetadata',
    variant: str,
    version: str,
    conformance: str,
) -> bytes:
    """Generates RDF metadata. Might be replaced by
    DocumentMetadata.rdf_matadata_generator().

    """
    namespace = f'pdf{variant}id'
    rdf = Element(f'{{{NS["rdf"]}}}RDF')

    element = SubElement(rdf, f'{{{NS["rdf"]}}}Description')
    element.attrib[f'{{{NS["rdf"]}}}about'] = ''
    element.attrib[f'{{{NS[namespace]}}}part'] = str(version)
    if conformance:
        element.attrib[f'{{{NS[namespace]}}}conformance'] = conformance

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
    return tostring(rdf, encoding='utf-8')
