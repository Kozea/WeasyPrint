"""PDF tagging."""

from collections import defaultdict

import pydyf

from ..formatting_structure import boxes
from ..layout.absolute import AbsolutePlaceholder


def add_tags(pdf, document):
    content_mapping = pydyf.Dictionary({})
    pdf.add_object(content_mapping)
    structure_root = pydyf.Dictionary({
        'Type': '/StructTreeRoot',
        'ParentTree': content_mapping.reference,
    })
    pdf.add_object(structure_root)
    structure_document = pydyf.Dictionary({
        'Type': '/StructElem',
        'S': '/Document',
        'K': pydyf.Array(),
        'P': structure_root.reference,
    })
    pdf.add_object(structure_document)
    structure_root['K'] = pydyf.Array([structure_document.reference])
    pdf.catalog['StructTreeRoot'] = structure_root.reference

    content_mapping['Nums'] = pydyf.Array()
    links = []
    for page_number, page in enumerate(document.pages):
        content_mapping['Nums'].append(page_number)
        content_mapping['Nums'].append(pydyf.Array())
        nums = {}
        marked = {kid['box']: kid for kid in page._page_box.marked}
        element = _build_box_tree(
            page._page_box, structure_document, pdf, page_number, nums, links, marked)
        structure_document['K'].append(element.reference)
        assert not marked
        nums = [reference for mcid, reference in sorted(nums.items())]
        content_mapping['Nums'][-1].extend(nums)

    for i, (link, annotation) in enumerate(links, start=len(document.pages)):
        content_mapping['Nums'].append(i)
        content_mapping['Nums'].append(link)
        annotation['StructParent'] = i
        annotation['F'] = 2 ** (2 - 1)


def _get_marked_content_tag(box):
    if box.element is None:
        return 'NonStruct'
    tag = box.element_tag
    if tag == 'div':
        return 'Div'
    elif tag.split(':')[0] == 'a':
        # Links and link pseudo elements create link annotations.
        return 'Link'
    elif tag == 'span':
        return 'Span'
    elif tag == 'main':
        return 'Part'
    elif tag == 'article':
        return 'Art'
    elif tag == 'section':
        return 'Sect'
    elif tag == 'blockquote':
        return 'BlockQuote'
    elif tag == 'p':
        return 'P'
    elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
        return tag.upper()
    elif tag in ('dl', 'ul', 'ol'):
        return 'L'
    elif tag in ('li', 'dt', 'dd'):
        # TODO: dt should be different.
        return 'LI'
    elif tag == 'li::marker':
        return 'Lbl'
    elif tag == 'table':
        return 'Table'
    elif tag in ('tr', 'th', 'td'):
        return tag.upper()
    elif tag in ('thead', 'tbody', 'tfoot'):
        return tag[:2].upper() + tag[2:]
    elif tag == 'img':
        return 'Figure'
    elif tag in ('caption', 'figcaption'):
        return 'Caption'
    else:
        return 'NonStruct'


def _build_box_tree(box, parent, pdf, page_number, nums, links, marked):
    if isinstance(box, AbsolutePlaceholder):
        box = box._box

    # Create box element.
    tag = _get_marked_content_tag(box)
    if tag == 'LI':
        if parent['S'] == '/LI':
            # Anonymous list element, store as list item body.
            tag = 'LBody'
        elif box.element_tag in ('dt', 'dd'):
            # Definition list item, wrap in list item body.
            parent = pydyf.Dictionary({
                'Type': '/StructElem',
                'S': '/LI',
                'K': pydyf.Array([]),
                'Pg': pdf.page_references[page_number],
                'P': parent.reference,
            })
            pdf.add_object(parent)
            child = _build_box_tree(box, parent, pdf, page_number, nums, links, marked)
            parent['K'].append(child.reference)
            return parent
    element = pydyf.Dictionary({
        'Type': '/StructElem',
        'S': f'/{tag}',
        'K': pydyf.Array([]),
        'Pg': pdf.page_references[page_number],
        'P': parent.reference,
    })
    pdf.add_object(element)

    # Handle special cases.
    if tag == 'Figure':
        x1, y1 = box.content_box_x(), box.content_box_y()
        x2, y2 = x1 + box.width, y1 + box.height
        element['A'] = pydyf.Dictionary({
            'O': '/Layout',
            'BBox': pydyf.Array((x1, y1, x2, y2)),
        })
        if 'alt' in box.element.attrib:
            element['Alt'] = pydyf.String(box.element.attrib['alt'])
    elif tag == 'Link':
        annotation = box.link_annotation
        object_reference = pydyf.Dictionary({
            'Type': '/OBJR',
            'Obj': annotation.reference,
            'Pg': pdf.page_references[page_number],
        })
        pdf.add_object(object_reference)
        links.append((object_reference.reference, annotation))
    elif tag == 'Table':
        # TODO: handle tables correctly.
        box, = box.children
    elif tag == 'TH':
        element['ID'] = pydyf.String(id(box))
    elif tag == 'TD':
        # TODO: don’t use the box to store this.
        box.mark = element

    def _add_children(children):
        for child in children:
            if isinstance(child, boxes.TextBox):
                kid = marked.pop(child)
                kid_element = pydyf.Dictionary({
                    'Type': '/StructElem',
                    'S': f'/{kid["tag"]}',
                    'K': pydyf.Array([kid['mcid']]),
                    'Pg': pdf.page_references[page_number],
                    'P': element.reference,
                })
                pdf.add_object(kid_element)
                element['K'].append(kid_element.reference)
                assert kid['mcid'] not in nums
                nums[kid['mcid']] = kid_element.reference
            else:
                if child.element_tag in ('ul', 'ol') and element['S'] == '/LI':
                    child_parent = parent
                else:
                    child_parent = element
                child_element = _build_box_tree(
                    child, child_parent, pdf, page_number, nums, links, marked)
                child_parent['K'].append(child_element.reference)

    if isinstance(box, boxes.ParentBox):
        # Build tree for box children.
        for child in box.children:
            children = child.children if isinstance(child, boxes.LineBox) else [child]
            _add_children(children)
    else:
        # Add replaced box.
        assert isinstance(box, boxes.ReplacedBox)
        kid = marked.pop(box)
        element['K'].append(kid['mcid'])
        assert kid['mcid'] not in nums
        nums[kid['mcid']] = element.reference

    if tag == 'Table':
        def _get_rows(table_box):
            for child in table_box.children:
                if child.element_tag == 'tr':
                    yield child
                else:
                    yield from _get_rows(child)

        # Get headers.
        column_headers = defaultdict(list)
        line_headers = defaultdict(list)
        rows = tuple(_get_rows(box))
        for i, row in enumerate(rows):
            # TODO: handle rowspan and colspan values.
            for j, cell in enumerate(row.children):
                if cell.element is None:
                    continue
                if cell.element_tag == 'th':
                    # TODO: handle rowgroup and colgroup values.
                    if cell.element.attrib.get('scope') == 'row':
                        line_headers[i].append(pydyf.String(id(cell)))
                    else:
                        column_headers[j].append(pydyf.String(id(cell)))
        for i, row in enumerate(rows):
            for j, cell in enumerate(row.children):
                if cell.element is None:
                    continue
                if cell.element_tag == 'td':
                    headers = []
                    headers.extend(line_headers[i])
                    headers.extend(column_headers[j])
                    cell.mark['A'] = pydyf.Dictionary({
                        'O': '/Table',
                        'Headers': pydyf.Array(headers),
                    })

    return element
