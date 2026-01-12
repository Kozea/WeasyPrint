"""PDF metadata stream generation."""

from uuid import uuid4
from xml.etree.ElementTree import Element, SubElement, register_namespace, tostring

import pydyf

from .. import __version__

# XML namespaces used for metadata
NS = {
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'dc': 'http://purl.org/dc/elements/1.1/',
    '': '',
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


class DocumentMetadata:
    """Meta-information belonging to a whole :class:`Document`.

    New attributes may be added in future versions of WeasyPrint.
    """
    def __init__(self, title=None, authors=None, description=None, keywords=None,
                 generator=None, created=None, modified=None, attachments=None,
                 lang=None, custom=None, xmp_metadata=None):
        #: The title of the document, as a string or :obj:`None`.
        #: Extracted from the ``<title>`` element in HTML
        #: and written to the ``/Title`` info field in PDF.
        self.title = title
        #: The authors of the document, as a list of strings.
        #: (Defaults to the empty list.)
        #: Extracted from the ``<meta name=author>`` elements in HTML
        #: and written to the ``/Author`` info field in PDF.
        self.authors = authors or []
        #: The description of the document, as a string or :obj:`None`.
        #: Extracted from the ``<meta name=description>`` element in HTML
        #: and written to the ``/Subject`` info field in PDF.
        self.description = description
        #: Keywords associated with the document, as a list of strings.
        #: (Defaults to the empty list.)
        #: Extracted from ``<meta name=keywords>`` elements in HTML
        #: and written to the ``/Keywords`` info field in PDF.
        self.keywords = keywords or []
        #: The name of one of the software packages
        #: used to generate the document, as a string or :obj:`None`.
        #: Extracted from the ``<meta name=generator>`` element in HTML
        #: and written to the ``/Creator`` info field in PDF.
        self.generator = generator
        #: The creation date of the document, as a string or :obj:`None`.
        #: Dates are in one of the six formats specified in
        #: `W3C’s profile of ISO 8601 <https://www.w3.org/TR/NOTE-datetime>`_.
        #: Extracted from the ``<meta name=dcterms.created>`` element in HTML
        #: and written to the ``/CreationDate`` info field in PDF.
        self.created = created
        #: The modification date of the document, as a string or :obj:`None`.
        #: Dates are in one of the six formats specified in
        #: `W3C’s profile of ISO 8601 <https://www.w3.org/TR/NOTE-datetime>`_.
        #: Extracted from the ``<meta name=dcterms.modified>`` element in HTML
        #: and written to the ``/ModDate`` info field in PDF.
        self.modified = modified
        #: A list of :class:`attachments <weasyprint.Attachment>`, empty by default.
        #: Extracted from the ``<link rel=attachment>`` elements in HTML
        #: and written to the ``/EmbeddedFiles`` dictionary in PDF.
        self.attachments = attachments or []
        #: Document language as BCP 47 language tags.
        #: Extracted from ``<html lang=lang>`` in HTML.
        self.lang = lang
        #: Custom metadata, as a dict whose keys are the metadata names and
        #: values are the metadata values.
        self.custom = custom or {}
        #: A list of XML bytestrings to add into the XMP metadata.
        self.xmp_metadata = xmp_metadata or []


    def include_in_pdf(self, pdf, variant, version, conformance, compress):
        """Add PDF stream of metadata.

        Described in ISO-32000-1:2008, 14.3.2.

        """
        header = b'<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
        header += b'<x:xmpmeta xmlns:x="adobe:ns:meta/">'
        footer = b'</x:xmpmeta>\n<?xpacket end="r"?>'
        xml_data = self.generate_rdf_metadata(variant, version, conformance)
        stream_content = b'\n'.join((header, xml_data, *self.xmp_metadata, footer))
        extra = {'Type': '/Metadata', 'Subtype': '/XML'}
        metadata = pydyf.Stream([stream_content], extra, compress)
        pdf.add_object(metadata)
        pdf.catalog['Metadata'] = metadata.reference


    def generate_rdf_metadata(self, variant, version, conformance):
        """Generate RDF metadata as a bytestring."""
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
                    assert self.modified
                    subelement = SubElement(element, f'{{{NS["xmp"]}}}MetadataDate')
                    subelement.text = self.modified
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

        if self.title:
            element = SubElement(rdf, f'{{{NS["rdf"]}}}Description')
            element.attrib[f'{{{NS["rdf"]}}}about'] = ''
            element = SubElement(element, f'{{{NS["dc"]}}}title')
            element = SubElement(element, f'{{{NS["rdf"]}}}Alt')
            element = SubElement(element, f'{{{NS["rdf"]}}}li')
            element.attrib['xml:lang'] = 'x-default'
            element.text = self.title
        if self.authors:
            element = SubElement(rdf, f'{{{NS["rdf"]}}}Description')
            element.attrib[f'{{{NS["rdf"]}}}about'] = ''
            element = SubElement(element, f'{{{NS["dc"]}}}creator')
            element = SubElement(element, f'{{{NS["rdf"]}}}Seq')
            for author in self.authors:
                author_element = SubElement(element, f'{{{NS["rdf"]}}}li')
                author_element.text = author
        if self.description:
            element = SubElement(rdf, f'{{{NS["rdf"]}}}Description')
            element.attrib[f'{{{NS["rdf"]}}}about'] = ''
            element = SubElement(element, f'{{{NS["dc"]}}}subject')
            element = SubElement(element, f'{{{NS["rdf"]}}}Bag')
            element = SubElement(element, f'{{{NS["rdf"]}}}li')
            element.attrib['xml:lang'] = 'x-default'
            element.text = self.description
        if self.keywords:
            element = SubElement(rdf, f'{{{NS["rdf"]}}}Description')
            element.attrib[f'{{{NS["rdf"]}}}about'] = ''
            element = SubElement(element, f'{{{NS["pdf"]}}}Keywords')
            element.text = ', '.join(self.keywords)
        if self.generator:
            element = SubElement(rdf, f'{{{NS["rdf"]}}}Description')
            element.attrib[f'{{{NS["rdf"]}}}about'] = ''
            element = SubElement(element, f'{{{NS["xmp"]}}}CreatorTool')
            element.text = self.generator
        if self.created:
            element = SubElement(rdf, f'{{{NS["rdf"]}}}Description')
            element.attrib[f'{{{NS["rdf"]}}}about'] = ''
            element = SubElement(element, f'{{{NS["xmp"]}}}CreateDate')
            element.text = self.created
        if self.modified:
            element = SubElement(rdf, f'{{{NS["rdf"]}}}Description')
            element.attrib[f'{{{NS["rdf"]}}}about'] = ''
            element = SubElement(element, f'{{{NS["xmp"]}}}ModifyDate')
            element.text = self.modified
        return tostring(rdf, encoding='utf-8')
