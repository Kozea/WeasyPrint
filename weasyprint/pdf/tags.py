"""PDF tagging."""

from collections import defaultdict

import pydyf

from ..formatting_structure import boxes
from ..layout.absolute import AbsolutePlaceholder
from ..logger import LOGGER


def add_tags(pdf, document, page_streams):
    """Add tag tree to the document."""

    # Add root structure.
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


    # Content mapping
    content_mapping['Nums'] = pydyf.Array()
    links = []
    part_container = {'part': None}

    for page_number, (page, stream) in enumerate(zip(document.pages, page_streams)):
        tags = stream._tags
        page_box = page._page_box

        # Prepare array for this page’s MCID-to-StructElem mapping
        content_mapping['Nums'].append(page_number)
        content_mapping['Nums'].append(pydyf.Array())
        page_nums = {}

        # Descend directly into real children (skip PageBox itself)
        for child in page_box.children:
            children = child.children if isinstance(child, boxes.LineBox) else [child]
            for real_child in children:
                element = _build_box_tree(
                    real_child, structure_document, pdf, page_number,
                    page_nums, links, tags, part_container
                )
                if element is not None:
                    structure_document['K'].append(element.reference)

        # Flatten page-local nums into global mapping
        sorted_refs = [ref for _, ref in sorted(page_nums.items())]
        content_mapping['Nums'][-1].extend(sorted_refs)

    # Add annotations for links
    for i, (link_objref, annotation) in enumerate(links, start=len(document.pages)):
        content_mapping['Nums'].append(i)
        content_mapping['Nums'].append(link_objref)
        annotation['StructParent'] = i
        annotation['F'] = 2 ** (2 - 1)

    # Add required metadata
    pdf.catalog['ViewerPreferences'] = pydyf.Dictionary({'DisplayDocTitle': 'true'})
    pdf.catalog['MarkInfo'] = pydyf.Dictionary({'Marked': 'true'})
    if 'Lang' not in pdf.catalog:
        LOGGER.error('Missing required "lang" attribute at the root of the document')
        pdf.catalog['Lang'] = pydyf.String()


def _get_pdf_tag(box):
    """Get PDF tag corresponding to box."""
    if box.element is None:
        return 'NonStruct'

    tag = box.element_tag
    if tag == 'div':
        return 'Div'
    elif tag.split(':')[0] == 'a':
        # Links and link pseudo elements create link annotations.
        return 'Link'
    elif tag == 'body':
        return 'Body'
    elif tag == 'html':
        return 'Html'
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


def _build_box_tree(box, parent, pdf, page_number, nums, links, tags, part_container):
    """Recursively build tag tree for given box."""

    # Special case for absolute elements.
    if isinstance(box, AbsolutePlaceholder):
        box = box._box

    # Create box element.
    tag = _get_pdf_tag(box)

    # Avoid generate Html and Body as a semantic node. Children required
    # to be processed.
    if tag == 'Html' or tag == 'Body':
        if isinstance(box, boxes.ParentBox):
            for child in box.children:
                children = child.children if isinstance(child, boxes.LineBox) else [child]
                for child in children:
                    if isinstance(child, boxes.MarginBox):
                        _build_box_tree(child, parent, pdf, page_number, nums, links, tags, part_container)
                    elif isinstance(child, boxes.TextBox):
                        kid = tags.pop(child)
                        kid_element = pydyf.Dictionary({
                            'Type': '/StructElem',
                            'S': f'/{kid["tag"]}',
                            'K': pydyf.Array([kid['mcid']]),
                            'Pg': pdf.page_references[page_number],
                            'P': parent.reference,
                        })
                        pdf.add_object(kid_element)
                        parent['K'].append(kid_element.reference)
                        nums[kid['mcid']] = kid_element.reference
                    else:
                        child_element = _build_box_tree(
                            child, parent, pdf, page_number, nums, links, tags, part_container)
                        if child_element is not None:
                            parent['K'].append(child_element.reference)
        return None

    if tag == 'Part':
        if part_container['part'] is None:
            element = pydyf.Dictionary({
                'Type': '/StructElem',
                'S': '/Part',
                'K': pydyf.Array(),
                'Pg': pdf.page_references[page_number],
                'P': parent.reference,
            })
            pdf.add_object(element)
            part_container['part'] = element
            parent['K'].append(element.reference)
        else:
            element = part_container['part']

        # Procesar los hijos dentro del único Part
        for child in box.children:
            children = child.children if isinstance(child, boxes.LineBox) else [child]
            for grandchild in children:
                child_element = _build_box_tree(
                    grandchild, element, pdf, page_number, nums, links, tags, part_container
                )
                if child_element is not None:
                    element['K'].append(child_element.reference)

        return None


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
            child = _build_box_tree(box, parent, pdf, page_number, nums, links, tags, part_container)
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
        # Add extra data for images.
        x1, y1 = box.content_box_x(), box.content_box_y()
        x2, y2 = x1 + box.width, y1 + box.height
        element['A'] = pydyf.Dictionary({
            'O': '/Layout',
            'BBox': pydyf.Array((x1, y1, x2, y2)),
        })
        if alt := box.element.attrib.get('alt'):
            element['Alt'] = pydyf.String(alt)
        else:
            source = box.element.attrib.get('src', 'unknown')
            LOGGER.error(f'Image "{source}" has no required alt description')
    elif tag == 'Table':
        # Ignore table wrapper, map actual table.
        box, = box.children
    elif tag == 'TH':
        # Set identifier for table headers to reference them in cells.
        element['ID'] = pydyf.String(id(box))
    elif tag == 'TD':
        # Store table cell element to map it to headers later.
        # TODO: don’t use the box to store this.
        box.mark = element

    # Include link annotations.
    if box.link_annotation:
        annotation = box.link_annotation
        object_reference = pydyf.Dictionary({
            'Type': '/OBJR',
            'Obj': annotation.reference,
            'Pg': pdf.page_references[page_number],
        })
        pdf.add_object(object_reference)
        links.append((object_reference.reference, annotation))

    if isinstance(box, boxes.ParentBox):
        # Build tree for box children.
        for child in box.children:
            children = child.children if isinstance(child, boxes.LineBox) else [child]
            for child in children:
                if isinstance(child, boxes.MarginBox):
                    # Build tree but don’t link it to main tree. It ensures that marked
                    # content is mapped in document and removed from list. It could be
                    # included in tree as Artifact, but that’s only allowed in PDF 2.0.
                    _build_box_tree(child, element, pdf, page_number, nums, links, tags, part_container)
                elif isinstance(child, boxes.TextBox):
                    # Add marked element from the stream.
                    kid = tags.pop(child)
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
                    # Recursively build tree for child.
                    if child.element_tag in ('ul', 'ol') and element['S'] == '/LI':
                        # In PDFs, nested lists are linked to the parent list, but in
                        # HTML, nested lists are linked to a parent’s list item.
                        child_parent = parent
                    else:
                        child_parent = element
                    child_element = _build_box_tree(
                        child, child_parent, pdf, page_number, nums, links, tags, part_container)

                    # Check if it is already been referenced before
                    if child_element is not None:
                        child_parent['K'].append(child_element.reference)

    else:
        # Add replaced box.
        assert isinstance(box, boxes.ReplacedBox)
        kid = tags.pop(box)
        element['K'].append(kid['mcid'])
        assert kid['mcid'] not in nums
        nums[kid['mcid']] = element.reference

    # Link table cells to related headers.
    if tag == 'Table':
        def _get_rows(table_box):
            for child in table_box.children:
                if child.element_tag == 'tr':
                    yield child
                else:
                    yield from _get_rows(child)

        # Get headers and rows.
        column_headers = defaultdict(list)
        row_headers = defaultdict(list)
        rows = tuple(_get_rows(box))

        # Find column and row headers.
        # TODO: handle rowspan and colspan values.
        for i, row in enumerate(rows):
            for j, cell in enumerate(row.children):
                if cell.element is None:
                    continue
                if cell.element_tag == 'th':
                    # TODO: handle rowgroup and colgroup values.
                    if cell.element.attrib.get('scope') == 'row':
                        row_headers[i].append(pydyf.String(id(cell)))
                    else:
                        column_headers[j].append(pydyf.String(id(cell)))

        # Map headers to cells.
        for i, row in enumerate(rows):
            for j, cell in enumerate(row.children):
                if cell.element is None:
                    continue
                if cell.element_tag == 'td':
                    cell.mark['A'] = pydyf.Dictionary({
                        'O': '/Table',
                        'Headers': pydyf.Array(row_headers[i] + column_headers[j]),
                    })

    return element
