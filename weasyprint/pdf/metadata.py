"""PDF metadata stream generation."""

from uuid import uuid4
from xml.etree.ElementTree import Element, SubElement, register_namespace, tostring

import pydyf

from .. import __version__

# XML namespaces used for metadata
NS = {
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'xmp': 'http://ns.adobe.com/xap/1.0/',
    'xmpMM': 'http://ns.adobe.com/xap/1.0/mm/',
    'pdf': 'http://ns.adobe.com/pdf/1.3/',
    'pdfaid': 'http://www.aiim.org/pdfa/ns/id/',
    'pdfuaid': 'http://www.aiim.org/pdfua/ns/id/',
    'pdfxid': 'http://www.npes.org/pdfx/ns/id/',
    'pdfx': 'http://ns.adobe.com/pdfx/1.3/',
}
for key, value in NS.items():
    register_namespace(key, value)


def add_metadata(pdf, metadata, variant, version, conformance, compress):
    """Add PDF stream of metadata.

    Described in ISO-32000-1:2008, 14.3.2.

    """
    header = b'<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>'
    footer = b'<?xpacket end="r"?>'
    xml_data = metadata.generate_rdf_metadata(metadata, variant, version, conformance)
    stream_content = b'\n'.join((header, xml_data, footer))
    extra = {'Type': '/Metadata', 'Subtype': '/XML'}
    metadata = pydyf.Stream([stream_content], extra, compress)
    pdf.add_object(metadata)
    pdf.catalog['Metadata'] = metadata.reference


def generate_rdf_metadata(metadata, variant, version, conformance):
    """Generate RDF metadata as a bytestring.

    Might be replaced by DocumentMetadata.rdf_metadata_generator().

    """
    namespace = f'pdf{variant}id'
    rdf = Element(f'{{{NS["rdf"]}}}RDF')

    if version:
        element = SubElement(rdf, f'{{{NS["rdf"]}}}Description')
        element.attrib[f'{{{NS["rdf"]}}}about'] = ''
        element.attrib[f'{{{NS[namespace]}}}part'] = str(version)
    if conformance:
        assert version
        if variant == 'x':
            for key in (
                f'{{{NS["pdfxid"]}}}GTS_PDFXVersion',
                f'{{{NS["pdfx"]}}}GTS_PDFXVersion',
                f'{{{NS["pdfx"]}}}GTS_PDFXConformance',
            ):
                subelement = SubElement(element, key)
                subelement.text = conformance
            subelement = SubElement(element, f'{{{NS["pdf"]}}}Trapped')
            subelement.text = 'False'
            if version >= 4:
                # TODO: these values could be useful instead of using random values.
                assert metadata.modified
                subelement = SubElement(element, f'{{{NS["xmp"]}}}MetadataDate')
                subelement.text = metadata.modified
                subelement = SubElement(element, f'{{{NS["xmpMM"]}}}DocumentID')
                subelement.text = f'xmp.did:{uuid4()}'
                subelement = SubElement(element, f'{{{NS["xmpMM"]}}}RenditionClass')
                subelement.text = 'proof:pdf'
                subelement = SubElement(element, f'{{{NS["xmpMM"]}}}VersionID')
                subelement.text = '1'
        else:
            element.attrib[f'{{{NS[namespace]}}}conformance'] = conformance
            if variant == 'a' and version == 4:
                subelement = SubElement(element, f'{{{NS["pdfaid"]}}}rev')
                subelement.text = '2020'

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
        element.attrib['xml:lang'] = 'x-default'
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
