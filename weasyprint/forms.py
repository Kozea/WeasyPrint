from xml.etree import ElementTree as ET


WF_CLASSES = [
    'wf-text',
]


def augment_markup(html: ET.Element) -> None:
    wf_fields = {
        wf_class: html.findall(".//*[@class='{}']".format(wf_class))
        for wf_class in WF_CLASSES
    }

    for wf_class, fields in wf_fields.items():
        for field in fields:
            augment_tag(field)


def augment_tag(tag):
    wfid = tag.attrib['wfid']
    top_left = tag.makeelement(
        'div',
        {
            'class': 'wf-top-left',
            'id': 'WF-{}-topleft'.format(wfid)
        }
    )
    tag.append(top_left)
    bottom_right = tag.makeelement(
        'div',
        {
            'class': 'wf-bottom-right',
            'id': 'WF-{}-bottomright'.format(wfid)
        }
    )
    tag.append(bottom_right)
