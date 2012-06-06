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


def layout_fixed_boxes(document, pages):
    """Lay out and yield the fixed boxes of ``pages``."""
    for page in pages:
        for fixed_box in page.fixed_boxes:
            fixed_box_for_page = fixed_box.copy()
            # Use an empty list as last argument because the fixed boxes in the
            # fixed box has already been added to page.fixed_boxes, we don't
            # want to get them again
            absolute_layout(document, fixed_box_for_page, page, [])
            yield fixed_box_for_page


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
    for i, page in enumerate(pages):
        root_children = []
        root, = page.children
        root_children.extend(layout_fixed_boxes(document, pages[:i]))
        root_children.extend(root.children)
        root_children.extend(layout_fixed_boxes(document, pages[i+1:]))
        root = root.copy_with_children(root_children)
        page.children = (root,) + tuple(
            make_margin_boxes(document, page, counter_values))
        yield page
        page_counter[0] += 1
