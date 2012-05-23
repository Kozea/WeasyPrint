# coding: utf8
"""
    weasyprint.layout
    -----------------

    Transform a "before layout" box tree into an "after layout" tree.
    (Surprising, hu?)

    Break boxes across lines and pages; determine the size and dimension
    of each box fragement.

    Boxes in the new tree have *used values* in their ``position_x``,
    ``position_y``, ``width`` and ``height`` attributes, amongst others.

    See http://www.w3.org/TR/CSS21/cascade.html#used-value

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from .absolute import absolute_layout
from .pages import make_all_pages, make_margin_boxes


def layout_document(document, root_box):
    """Lay out the whole document.

    This includes line breaks, page breaks, absolute size and position for all
    boxes.

    :param document: a Document object.
    :returns: a list of laid out Page objects.

    """
    pages = list(make_all_pages(document, root_box))
    page_counter = [1]
    counter_values = {'page': page_counter, 'pages': [len(pages)]}
    for page in pages:
        root, = page.children
        root_children = list(root.children)
        for fixed_box in document.fixed_boxes:
            fixed_box_for_page = fixed_box.copy()
            absolute_layout(document, fixed_box_for_page, page)
            root_children.append(fixed_box_for_page)

        root = root.copy_with_children(root_children)
        page.children = (root,) + tuple(
            make_margin_boxes(document, page, counter_values))
        yield page
        page_counter[0] += 1
