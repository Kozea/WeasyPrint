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
from .layout.absolute import AbsolutePlaceholder


_Z_INDEX_GETTER = operator.attrgetter('z_index')


class StackingContext(object):
    """Stacking contexts define the paint order of all pieces of a document.

    http://www.w3.org/TR/CSS21/visuren.html#x43
    http://www.w3.org/TR/CSS21/zindex.html

    """
    def __init__(self, box, child_contexts, blocks, floats, blocks_and_cells,
                 page):
        self.box = box
        self.page = page
        self.block_level_boxes = blocks  # 4: In flow, non positioned
        self.float_contexts = floats  # 5: Non positioned
        self.negative_z_contexts = []  # 3: Child contexts, z-index < 0
        self.zero_z_contexts = []  # 8: Child contexts, z-index = 0
        self.positive_z_contexts = []  # 9: Child contexts, z-index > 0
        self.blocks_and_cells = blocks_and_cells  # 7: Non positioned

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
        child_contexts = [cls.from_box(child, page) for child in page.children]
        return cls(page, child_contexts, [], [], [], page)

    @classmethod
    def from_box(cls, box, page, child_contexts=None):
        children = []  # What will be passed to this box
        if child_contexts is None:
            child_contexts = children
        # child_contexts: where to put sub-contexts that we find here.
        # May not be the same as children for:
        #   "treat the element as if it created a new stacking context,
        #    but any positioned descendants and descendants which actually
        #    create a new stacking context should be considered part of the
        #    parent stacking context, not this new one."
        blocks = []
        floats = []
        blocks_and_cells = []

        def dispatch_children(box):
            if isinstance(box, AbsolutePlaceholder):
                box = box._box

            if not isinstance(box, boxes.ParentBox):
                return box

            children = []
            for child in box.children:
                if ((child.style.position != 'static' and
                            child.style.z_index != 'auto')
                        or child.style.opacity < 1
                        # 'transform: none' gives a "falsy" empty list here
                        or child.style.transform
                        or child.style.clip
                        or child.style.overflow != 'visible'
                    ):
                    # This child defines a new stacking context, remove it
                    # from the "normal" children list.
                    child_contexts.append(
                        StackingContext.from_box(child, page))
                else:
                    if child.style.position != 'static':
                        assert child.style.z_index == 'auto'
                        # "Fake" context: sub-contexts are already removed
                        child_contexts.append(StackingContext.from_box(
                            child, page, child_contexts))
                        continue
                    elif child.is_floated():
                        floats.append(StackingContext.from_box(
                            child, page, child_contexts))
                        continue
                    elif isinstance(child, boxes.BlockLevelBox):
                        blocks.append(child)
                        blocks_and_cells.append(child)
                    elif isinstance(child, boxes.TableCellBox):
                        blocks_and_cells.append(child)

                    children.append(dispatch_children(child))
            return box.copy_with_children(children)

        box = dispatch_children(box)

        return cls(box, children, blocks, floats, blocks_and_cells, page)
