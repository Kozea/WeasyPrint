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

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from .absolute import absolute_box_layout
from .pages import make_all_pages, make_margin_boxes
from .backgrounds import layout_backgrounds


def layout_fixed_boxes(context, pages):
    """Lay out and yield the fixed boxes of ``pages``."""
    for page in pages:
        for box in page.fixed_boxes:
            # Use an empty list as last argument because the fixed boxes in the
            # fixed box has already been added to page.fixed_boxes, we don't
            # want to get them again
            yield absolute_box_layout(context, box, page, [])


def layout_document(enable_hinting, style_for, get_image_from_uri, root_box):
    """Lay out the whole document.

    This includes line breaks, page breaks, absolute size and position for all
    boxes.

    :param context: a LayoutContext object.
    :returns: a list of laid out Page objects.

    """
    context = LayoutContext(enable_hinting, style_for, get_image_from_uri)
    pages = list(make_all_pages(context, root_box))
    page_counter = [1]
    counter_values = {'page': page_counter, 'pages': [len(pages)]}
    for i, page in enumerate(pages):
        root_children = []
        root, = page.children
        root_children.extend(layout_fixed_boxes(context, pages[:i]))
        root_children.extend(root.children)
        root_children.extend(layout_fixed_boxes(context, pages[i+1:]))
        root = root.copy_with_children(root_children)
        page.children = (root,) + tuple(
            make_margin_boxes(context, page, counter_values))
        layout_backgrounds(page, get_image_from_uri)
        yield page
        page_counter[0] += 1


class LayoutContext(object):
    def __init__(self, enable_hinting, style_for, get_image_from_uri):
        self.enable_hinting = enable_hinting
        self.style_for = style_for
        self.get_image_from_uri = get_image_from_uri
        self._excluded_shapes_lists = []
        self.excluded_shapes = None  # Not initialized yet

    def create_block_formatting_context(self):
        self.excluded_shapes = []
        self._excluded_shapes_lists.append(self.excluded_shapes)

    def finish_block_formatting_context(self, root_box):
        # See http://www.w3.org/TR/CSS2/visudet.html#root-height
        if root_box.style.height == 'auto':
            box_bottom = root_box.content_box_y() + root_box.height
            for shape in self.excluded_shapes:
                shape_bottom = shape.position_y + shape.margin_height()
                if shape_bottom > box_bottom:
                    root_box.height += shape_bottom - box_bottom
        self._excluded_shapes_lists.pop()
        if self._excluded_shapes_lists:
            self.excluded_shapes = self._excluded_shapes_lists[-1]
        else:
            self.excluded_shapes = None
