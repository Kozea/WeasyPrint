"""Stacking contexts management."""

from .formatting_structure import boxes
from .layout.absolute import AbsolutePlaceholder


class StackingContext:
    """Stacking contexts define the paint order of all pieces of a document.

    https://www.w3.org/TR/CSS21/visuren.html#x43
    https://www.w3.org/TR/CSS21/zindex.html

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
        self.negative_z_contexts.sort(key=lambda context: context.z_index)
        self.positive_z_contexts.sort(key=lambda context: context.z_index)
        # sort() is stable, so the lists are now storted
        # by z-index, then tree order.

        self.z_index = box.style['z_index']
        if self.z_index == 'auto':
            self.z_index = 0

    @classmethod
    def from_page(cls, page):
        # Page children (the box for the root element and margin boxes)
        # as well as the page box itself are unconditionally stacking contexts.
        child_contexts = [cls.from_box(child, page) for child in page.children]
        # Children are sub-contexts, remove them from the "normal" tree.
        page = page.copy_with_children([])
        return cls(page, child_contexts, [], [], [], page)

    @classmethod
    def from_box(cls, box, page, child_contexts=None):
        children = []  # What will be passed to this box
        if child_contexts is None:
            child_contexts = children
        # child_contexts: where to put sub-contexts that we find here.
        # May not be the same as children for:
        #   "treat the element as if it created a new stacking context, but any
        #    positioned descendants and descendants which actually create a new
        #    stacking context should be considered part of the parent stacking
        #    context, not this new one."
        blocks = []
        floats = []
        blocks_and_cells = []
        box = _dispatch_children(
            box, page, child_contexts, blocks, floats, blocks_and_cells)
        return cls(box, children, blocks, floats, blocks_and_cells, page)


def _dispatch(box, page, child_contexts, blocks, floats, blocks_and_cells):
    if isinstance(box, AbsolutePlaceholder):
        box = box._box
    style = box.style

    # Remove boxes defining a new stacking context from the children list.
    defines_stacking_context = (
        (style['position'] != 'static' and style['z_index'] != 'auto') or
        (box.is_grid_item and style['z_index'] != 'auto') or
        style['opacity'] < 1 or
        style['transform'] or  # 'transform: none' gives a "falsy" empty list
        style['overflow'] != 'visible')
    if defines_stacking_context:
        child_contexts.append(StackingContext.from_box(box, page))
        return

    if style['position'] != 'static':
        assert style['z_index'] == 'auto'
        # "Fake" context: sub-contexts will go in this `child_contexts` list.
        # Insert at the position before creating the sub-context.
        index = len(child_contexts)
        stacking_context = StackingContext.from_box(box, page, child_contexts)
        child_contexts.insert(index, stacking_context)
    elif box.is_floated():
        floats.append(StackingContext.from_box(box, page, child_contexts))
    elif isinstance(box, (
            boxes.InlineBlockBox, boxes.InlineFlexBox, boxes.InlineGridBox)):
        # Have this fake stacking context be part of the "normal" box tree,
        # because we need its position in the middle of a tree of inline boxes.
        return StackingContext.from_box(box, page, child_contexts)
    else:
        if isinstance(box, boxes.BlockLevelBox):
            blocks_index = len(blocks)
            blocks_and_cells_index = len(blocks_and_cells)
        elif isinstance(box, boxes.TableCellBox):
            blocks_index = None
            blocks_and_cells_index = len(blocks_and_cells)
        else:
            blocks_index = None
            blocks_and_cells_index = None

        box = _dispatch_children(
            box, page, child_contexts, blocks, floats, blocks_and_cells)

        # Insert at the positions before dispatch the children.
        if blocks_index is not None:
            blocks.insert(blocks_index, box)
        if blocks_and_cells_index is not None:
            blocks_and_cells.insert(blocks_and_cells_index, box)

        return box


def _dispatch_children(box, page, child_contexts, blocks, floats,
                       blocks_and_cells):
    if not isinstance(box, boxes.ParentBox):
        return box

    new_children = []
    for child in box.children:
        result = _dispatch(
            child, page, child_contexts, blocks, floats, blocks_and_cells)
        if result is not None:
            new_children.append(result)
    return box.copy_with_children(new_children)
