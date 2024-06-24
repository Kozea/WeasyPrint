
import pydyf

def add_debug(debug, matrix, pdf, page, names, mark):
    """Include anchors for each element with an ID in a given PDF page."""
    if not debug:
        return

    if 'Annots' not in page:
        page['Annots'] = pydyf.Array()

    ids = {}

    for i, (element, style, rectangle, box) in enumerate(debug): # style is usused for now?
        id = element.get("id")
        if id.startswith("auto-id"):
            id = "-".join(id.split("-")[:4])
            if id in ids:
                ids[id] += 1
            else:
                ids[id] = 0
            final_id = id + "-" + str(ids[id])
            element.set("id", final_id)
            id = final_id
            # print("add_debug", element.get("id"))
        x1, y1 = matrix.transform_point(*rectangle[:2])
        x2, y2 = matrix.transform_point(*rectangle[2:])
        box.annotation = pydyf.Dictionary({
            'Type': '/Annot',
            'Subtype': '/Link',
            # 'Subtype': '/Square',
            'Rect': pydyf.Array([x1, y1, x2, y2]),
            'P': page.reference,
            # 'BS': pydyf.Dictionary({'W': 1}), # border style
            'T': pydyf.String(id), # the title element gets added as metadata
        })

        # Internal links are deactivated when in local
        # See: https://github.com/mozilla/pdf.js/issues/12415
        # box.annotation['A'] = pydyf.Dictionary({
        #     'Type': '/Action',
        #     'S': '/URI',
        #     'URI': pydyf.String("#" + id)
        # })

        # Internal links - works better with a local version PDFjs... But why?
        box.annotation['Dest'] = pydyf.String(id)

        # In order to preserve page references
        names.append([id, pydyf.Array([page.reference, '/XYZ', x1, y1, 0])])

        # Actually adding the PDF object
        pdf.add_object(box.annotation)
        page['Annots'].append(box.annotation.reference)

def resolve_debug(pages):
    '''Resolve the added debug IDs. Inspired from resolve_links.
    '''
    debug = list()
    paged_debug = []
    for i, page in enumerate(pages):
        paged_debug.append([])
        # for (element, style, rectangle, box) in page.debug:
        #     debug.append(element.get('id'))
    for page in pages:
        page_debug = []
        for m in page.debug:
            page_debug.append(m)
        yield page_debug, paged_debug.pop(0)
