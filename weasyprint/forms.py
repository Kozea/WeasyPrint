"""
    weasyprint.forms
    ----------------

    Post-process the PDF files created by cairo and add forms.

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import re

WFID_REGEX = re.compile(
    rb"\(WF-"
    rb"(?P<class>(?:\w|-)+)-"
    rb"(?P<wfid>\w+)-"
    rb"(?P<corner>topleft|bottomright)\) \["
    rb"(?P<page>\d+) \d+ R \/XYZ "
    rb"(?P<x>\d+) "
    rb"(?P<y>\d+) \d+\]"
)

ACROFORM = """
<<
    /DA (/Times 10 Tf 0 g)
    /DR <<
      /Font <<
        /Times <<
          /BaseFont /Times-Roman
          /Subtype /Type1
          /Type /Font
        >>
      >>
    >>
    /Fields [{fields}]
>>
"""

WF_CLASSES = {
    'wf-text': """
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
""",
    'wf-textarea': """
<<
    /BS <<
        /S /S
        /W 1
    >>
    /Ff 4096
    /FT /Tx
    /Rect [{rect}]
    /Subtype /Widget
    /Type /Annot
    /V ()
>>
"""
}


class WField:
    def __init__(self, name, html_class, page):
        self.name = name
        self.topleft = None
        self.bottomright = None
        self.html_class = html_class
        self.page = page
        self.pdf_obj_id = None

    def __repr__(self):
        return (
            "WFid({name}, <{html_class} />, ({topleft}, {bottomright}), "
            "page object: {page})"
        ).format(
            name=self.name, html_class=self.html_class, topleft=self.topleft,
            bottomright=self.bottomright, page=self.page)

    def to_pdf_obj(self):
        template = WF_CLASSES[self.html_class]
        result = template.format(
            rect="{} {} {} {}".format(*self.topleft, *self.bottomright))
        return result.encode('ascii')


def augment_markup(html):
    wf_fields = {
        wf_class: html.findall(".//*[@class='{}']".format(wf_class))
        for wf_class in WF_CLASSES}

    for wf_class, fields in wf_fields.items():
        for field in fields:
            augment_tag(field)


def augment_tag(tag):
    wfid = tag.attrib['wfid']
    top_left = tag.makeelement('div', {
        'class': 'wf-top-left',
        'id': 'WF-{}-{}-topleft'.format(tag.attrib['class'], wfid)})
    tag.append(top_left)
    bottom_right = tag.makeelement('div', {
        'class': 'wf-bottom-right',
        'id': 'WF-{}-{}-bottomright'.format(tag.attrib['class'], wfid)})
    tag.append(bottom_right)


def collect_wfields(pdf):
    wfields = {}
    for match in WFID_REGEX.finditer(pdf):
        name = match.group('wfid')
        corner = str(match.group('corner'), 'ascii')
        x = int(match.group('x'))
        y = int(match.group('y'))
        page = int(str(match.group('page'), 'ascii'))
        html_class = str(match.group('class'), 'ascii')

        wfield = wfields.setdefault(
            name, WField(name=name, html_class=html_class, page=page))
        setattr(wfield, corner, (x, y))

    return wfields


def make_acroform(field_ids):
    return ACROFORM.format(
        fields=' '.join('{} 0 R'.format(x) for x in field_ids)).encode('ascii')
