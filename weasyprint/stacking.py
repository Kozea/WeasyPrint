# coding: utf8
"""
    weasyprint.stacking
    -------------------

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from .formatting_structure import boxes


def establishes_stacking_context(box):
    return (
        box.style.position != 'static' and box.style.z_index != 'auto'
    ) or (
        box.style.opacity < 1
    ) or (
        box.style.transform  # empty list for 'transform: none'
    )


class StackingContext(object):
    def __init__(self, box):
        self.negative_z_contexts = []  # 3: Child contexts, z-index < 0
        self.block_boxes = []  # 4, 7: In flow, non positioned
        self.float_boxes = []  # 5: Non positioned
        self.zero_z_contexts = []  # 8: Child contexts, z-index = 0
        self.positive_z_contexts = []  # 9: Child contexts, z-index > 0

        self.box = self._dispatch_children(box)
        self.z_index = box.style.z_index
        if self.z_index == 'auto':
            self.z_index = 0

    def _dispatch_children(self, box):
        if not isinstance(box, boxes.ParentBox):
            return box

        children = []
        for child in box.children:
            if establishes_stacking_context(child):
                context = StackingContext(child)
                if context.z_index < 0:
                    self.negative_z_contexts.append(context)
                elif context.z_index == 0:
                    self.zero_z_contexts.append(context)
                elif context.z_index > 0:
                    self.positive_z_contexts.append(context)
                # Remove from children
            else:
                child = self._dispatch_children(child)
                if child.style.position != 'static':
                    assert child.style.z_index == 'auto'
                    # sub-contexts are already removed
                    context = StackingContext(child)
                    self.zero_z_contexts.append(context)
                elif child.is_floated():
                    self.float_boxes.append(child)
                elif isinstance(child, boxes.BlockBox):
                    self.block_boxes.append(child)

                children.append(child)
        return box.copy_with_children(children)
                