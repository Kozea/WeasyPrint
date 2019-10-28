WF_CLASSES = [
    'wf-text',
]

def augment_markup(html):
    wf_fields = {
        wf_class: html.findall(".//*[@class='{}']".format(wf_class))
        for wf_class in WF_CLASSES
    }

    return html
