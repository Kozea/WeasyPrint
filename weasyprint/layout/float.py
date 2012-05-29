# coding: utf8
"""
    weasyprint.float
    ----------------

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from .absolute import absolute_layout
from .inlines import replaced_box_width, replaced_box_height
from .percentages import resolve_percentages, resolve_position_percentages
from .preferred import shrink_to_fit
from ..formatting_structure import boxes


class FloatPlaceholder(object):
    """Left where an float box was taken out of the flow."""
    def __init__(self, box):
        # Work around the overloaded __setattr__
        object.__setattr__(self, '_box', box)
        object.__setattr__(self, '_layout_done', False)

    def set_laid_out_box(self, new_box):
        object.__setattr__(self, '_box', new_box)
        object.__setattr__(self, '_layout_done', True)

    def translate(self, dx=0, dy=0):
        if self._layout_done:
            self._box.translate(dx, dy)
        else:
            # Descendants do not have a position yet.
            self._box.position_x += dx
            self._box.position_y += dy

    def copy(self):
        new_placeholder = FloatPlaceholder(self._box.copy())
        object.__setattr__(new_placeholder, '_layout_done', self._layout_done)
        return new_placeholder

    # Pretend to be the box itself
    def __getattr__(self, name):
        return getattr(self._box, name)

    def __setattr__(self, name, value):
        setattr(self._box, name, value)


def float_layout(document, placeholder, containing_block, absolute_boxes):
    """Set the width and position of floating ``box``."""
    box = placeholder._box

    cb = containing_block
    cb_x = cb.content_box_x()
    cb_y = cb.content_box_y()
    cb_width = cb.width
    cb_height = cb.height

    resolve_percentages(box, (cb_width, cb_height))
    resolve_position_percentages(box, (cb_width, cb_height))

    if box.margin_left == 'auto':
        box.margin_left = 0
    if box.margin_right == 'auto':
        box.margin_right = 0

    if box.width == 'auto':
        if isinstance(box, boxes.BlockReplacedBox):
            box.width = replaced_box_width(box, None)
            box.height = replaced_box_height(box, None)
        else:
            box.width = shrink_to_fit(box, containing_block.width)

    # avoid a circular import
    from .blocks import block_container_layout
    new_box, _, _, _, _ = block_container_layout(
        document, box, max_position_y=float('inf'),
        skip_stack=None, device_size=None, page_is_empty=False,
        absolute_boxes=absolute_boxes, adjoining_margins=None)

    for child_placeholder in absolute_boxes:
        absolute_layout(document, child_placeholder, new_box)

    if new_box.style.float == 'left':
        new_box.position_x = cb_x
    else:
        assert new_box.style.float == 'right'
        new_box.position_x = cb_x - new_box.margin_width()

    placeholder.set_laid_out_box(new_box)
