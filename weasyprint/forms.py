import collections
import re
from xml.etree import ElementTree as ET
#
# from .pdf import PDFFile
#
#
WF_CLASSES = [
    'wf-text',
]

WFID_REGEX = re.compile(
    rb"\(WF-"
    rb"(?P<class>(?:\w|-)+)-"
    rb"(?P<wfid>\w+)-"
    rb"(?P<corner>topleft|bottomright)\) \["
    rb"(?P<page>\d+) \d+ R \/XYZ "
    rb"(?P<x>\d+) "
    rb"(?P<y>\d+) \d+\]"
)

ACROFORM_TX = """
{id} 0 obj
<<
    /BS <<
        /S /S
        /W 1
    >>
    /FT /Tx
    /Rect [{rect}]
    /Subtype /Widget
    /Type /Annot
    /V ()
>>
endobj
"""


class WFid:
    __slots__ = ['name', 'topleft', 'bottomright', 'html_class', 'page']

    def __init__(self, *, name=None, topleft=None, bottomright=None, html_class=None, page=None):
        self.name = name
        self.topleft = topleft
        self.bottomright = bottomright
        self.html_class = html_class
        self.page = page

    def __repr__(self):
        return (
            "WFid("
            "{name}, "
            "<{html_class} />, "
            "({topleft}, {bottomright}), "
            "page object: {page}"
            ")"
        ).format(
            **{key: getattr(self, key) for key in self.__slots__}
        )


def augment_markup(html: ET.Element) -> None:
    wf_fields = {
        wf_class: html.findall(".//*[@class='{}']".format(wf_class))
        for wf_class in WF_CLASSES
    }

    for wf_class, fields in wf_fields.items():
        for field in fields:
            augment_tag(field)

    pass


def augment_tag(tag):
    wfid = tag.attrib['wfid']
    top_left = tag.makeelement(
        'div',
        {
            'class': 'wf-top-left',
            'id': 'WF-{}-{}-topleft'.format(tag.attrib['class'], wfid)
        }
    )
    tag.append(top_left)
    bottom_right = tag.makeelement(
        'div',
        {
            'class': 'wf-bottom-right',
            'id': 'WF-{}-{}-bottomright'.format(tag.attrib['class'], wfid)
        }
    )
    tag.append(bottom_right)


def write_pdf_form_fields(fileobj):
    pos = fileobj.tell()

    # Collect wfids
    fileobj.seek(0)
    content = fileobj.read()
    collect_wfids(content)

    # pdf = PDFFile(fileobj)

    # for field in fields:
    #     pdf.write_new_object(field)
    # pdf.write_new_object(form)
    # pdf.extend_dict(dictionary, new_content) # add acroform

    fileobj.seek(pos)

    # return pdf


def collect_wfids(pdf: bytes) -> bytes:
    wfids = {}
    for match in WFID_REGEX.finditer(pdf):
        name = match.group('wfid')
        corner = str(match.group('corner'), 'ascii')
        x = int(match.group('x'))
        y = int(match.group('y'))
        page = int(str(match.group('page'), 'ascii'))
        html_class = str(match.group('class'), 'ascii')

        wfid = wfids.setdefault(name, WFid(name=name, html_class=html_class, page=page))
        setattr(wfid, corner, (x, y))

    return wfids
