# coding: utf8
"""
    weasyprint.stacking
    -------------------

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import operator

from .formatting_structure import boxes


_Z_INDEX_GETTER = operator.attrgetter('z_index')


class StackingContext(object):
    """Stacking contexts define the paint order of all pieces of a document.

    http://www.w3.org/TR/CSS21/visuren.html#x43
    http://www.w3.org/TR/CSS21/zindex.html

    """
    def __init__(self, box, child_contexts, blocks, floats):
        self.block_boxes = blocks  # 4, 7: In flow, non positioned
        self.float_boxes = floats  # 5: Non positioned
        self.negative_z_contexts = []  # 3: Child contexts, z-index < 0
        self.zero_z_contexts = []  # 8: Child contexts, z-index = 0
        self.positive_z_contexts = []  # 9: Child contexts, z-index > 0

        for context in child_contexts:
            if context.z_index < 0:
                self.negative_z_contexts.append(context)
            elif context.z_index == 0:
                self.zero_z_contexts.append(context)
            else:  # context.z_index > 0
                self.positive_z_contexts.append(context)
        self.negative_z_contexts.sort(key=_Z_INDEX_GETTER)
        self.positive_z_contexts.sort(key=_Z_INDEX_GETTER)
        # sort() is stable, so the lists are now storted
        # by z-index, then tree order.

        self.z_index = box.style.z_index
        if self.z_index == 'auto':
            self.z_index = 0

    @classmethod
    def from_page(cls, page):
        # Page children (the box for the root element and margin boxes)
        # as well as the page box itself are unconditionally stacking contexts.
        cls(page, [cls.from_box(child) for child in page.children], [], [])

    @classmethod
    def from_box(cls, box):
        child_contexts = []
        blocks = []
        floats = []

        def dispatch_children(box):
            if not isinstance(box, boxes.ParentBox):
                return box

            children = []
            for child in box.children:
                if ((child.style.position != 'static' and
                            child.style.z_index != 'auto')
                        or child.style.opacity < 1
                        # 'transform: none' gives a "falsy" empty list here
                        or child.style.transform
                    ):
                    # This child defines a new stacking context, remove it
                    # from the "normal" children list.
                    child_contexts.append(StackingContext.from_box(child))
                else:
                    child = dispatch_children(child)
                    children.append(child)
                    if child.style.position != 'static':
                        assert child.style.z_index == 'auto'
                        # "Fake" context: sub-contexts are already removed
                        child_contexts.append(StackingContext.from_box(child))
                    elif child.is_floated():
                        floats.append(child)
                    elif isinstance(child, boxes.BlockBox):
                        blocks.append(child)
            return box.copy_with_children(children)

        dispatch_children(box)

        return cls(box, child_contexts, blocks, floats)
