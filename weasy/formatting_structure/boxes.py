# coding: utf8

#  WeasyPrint converts web documents (HTML, CSS, ...) to PDF.
#  Copyright (C) 2011  Simon Sapin
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

This module defines the classes for all types of boxes in the CSS formatting
structure / box model.

http://www.w3.org/TR/CSS21/visuren.html

Names are the same as in CSS 2.1 with the exception of TextBox. In WeasyPrint,
any text is in a TextBox. What CSS calls anonymous inline boxes are text boxes
but not all text boxes are anonymous inline boxes.

http://www.w3.org/TR/CSS21/visuren.html#anonymous

Abstract classes, should not be instanciated:

 * Box
 * BlockLevelBox
 * InlineLevelBox
 * BlockContainerBox
 * AnonymousBox
 * ReplacedBox

Concrete classes:

 * PageBox
 * BlockBox
 * AnonymousBlockBox
 * InlineBox
 * InlineBlockBox
 * BlockLevelReplacedBox
 * InlineLevelReplacedBox
 * TextBox
 * LineBox

Apart from PageBox and LineBox, all concrete box classes have one of the
following "outside" behavior:

 * Block-level (inherits from BlockLevelBox)
 * Inline-level (inherits from InlineLevelBox)

and one of the following "inside" behavior:

 * Block container (inherits from BlockContainerBox)
 * Inline content (is or inherits from InlineBox)
 * Replaced content (inherits from ReplacedBox)

See respective docstrings for details.

"""


from .. import css


class Box(object):
    """
    Abstract base class for all boxes.
    """
    def __init__(self, element):
        # Should never be None
        self.element = element
        # No parent yet. Will be set when this box is added to another box’s
        # children. Only the root box should stay without a parent.
        self.parent = None
        self.children = []
        self._init_style()
        # When the size is not calculated yet, use None as default value
        self.width = None
        self.height = None

    def _init_style(self):
        # Computed values
        # Copying might not be needed, but let’s be careful with mutable
        # objects.
        self.style = self.element.style.copy()

    def add_child(self, child, index=None):
        """
        Add the new child to this box’s children list and set this box as the
        child’s parent.
        """
        child.parent = self
        if index == None:
            self.children.append(child)
        else:
            self.children.insert(index, child)

    def descendants(self):
        """A flat generator for a box, its children and descendants."""
        yield self
        for child in self.children or []:
            for grand_child in child.descendants():
                yield grand_child

    def ancestors(self):
        """Yield parent and recursively yield parent's parents."""
        parent = self
        while parent.parent:
            parent = parent.parent
            yield parent

    @property
    def index(self):
        """Index of the box in its parent's children."""
        if self.parent:
            return self.parent.children.index(self)

    def containing_block_size(self):
        """``(width, height)`` size of the box's containing block."""
        if isinstance(self.parent, PageBox):
            return self.parent.width, self.parent.height
        elif self.style.position in ('relative', 'static'):
            return self.parent.width, self.parent.height
        elif self.style.position == 'fixed':
            for ancestor in self.ancestors():
                if isinstance(ancestor, PageBox):
                    return ancestor.width, ancestor.height
            assert False, 'Page not found'
        elif self.style.position == 'absolute':
            for ancestor in self.ancestors():
                if ancestor.style.position in ('absolute', 'relative', 'fixed'):
                    if ancestor.style.display == 'inline':
                        # TODO: fix this bad behaviour, see CSS 10.1
                        return ancestor.width, ancestor.height
                    else:
                        return ancestor.width, ancestor.height
        assert False, 'Containing block not found'


class BlockLevelBox(Box):
    """
    A box that participates in an block formatting context.

    An element with a 'display' value of 'block', 'liste-item' or 'table'
    generates a block-level box.
    """


class BlockContainerBox(Box):
    """
    A box that either contains only block-level boxes or establishes an inline
    formatting context and thus contains only line boxes.

    A non-replaced element with a 'display' value of 'block', 'list-item',
    'inline-block' or 'table-cell' generates a block container box.
    """


class PageBox(BlockContainerBox):
    """
    Initially the whole document will be in a single page box. During layout
    a new page box is created after every page break.
    """
    def __init__(self, document, page_number):
        self.document = document
        # starting at 1 for the first page.
        self.page_number = page_number
        # Page boxes are not linked to any element.
        super(PageBox, self).__init__(element=None)

    def _init_style(self):
        # First page is a right page. TODO: this "should depend on the major
        # writing direction of the document".
        first_is_right = True
        is_right = (self.page_number % 2) == (1 if first_is_right else 0)
        page_type = 'right' if is_right else 'left'
        if self.page_number == 1:
            page_type = 'first_' + page_type
        style = self.document.page_pseudo_elements[page_type].style
        # Copying might not be needed, but let’s be careful with mutable
        # objects.
        self.style = style.copy()

    def containing_block_size(self):
        return self.outer_width, self.outer_height


class BlockBox(BlockContainerBox, BlockLevelBox):
    """
    A block-level box that is also a block container.

    A non-replaced element with a 'display' value of 'block', 'list-item'
    generates a block box.
    """


class AnonymousBox(Box):
    """
    A box that is not directly generated by an element. Inherits style instead
    of copying them.
    """
    def _init_style(self):
        pseudo = css.PseudoElement(self.element, 'anonymous_box')
        # New PseudoElement has an empty .applicable_properties list:
        # no cascaded value, only inherited and initial values.
        # TODO: Maybe pre-compute initial values and remove the compute_values
        # step here.
        css.assign_properties(pseudo)
        self.style = pseudo.style


class AnonymousBlockBox(AnonymousBox, BlockBox):
    """
    Wraps inline-level boxes where block-level boxes are needed.

    Block containers (eventually) contain either only block-level boxes or only
    inline-level boxes. When they initially contain both, consecutive
    inline-level boxes are wrapped in an anonymous block box by
    ``boxes.inline_in_block()``.
    """


class LineBox(AnonymousBox):
    """
    Eventually a line in an inline formatting context. Can only contain
    inline-level boxes.

    In early stages of building the box tree a single line box contains many
    consecutive inline boxes. Later, during layout phase, each line boxes will
    be split into multiple line boxes, one for each actual line.
    """


class InlineLevelBox(Box):
    """
    A box that participates in an inline formatting context.

    An inline-level box that is not an inline box (see below) is said to be
    "atomic". Such boxes are inline-blocks, replaced elements and inline tables.

    An element with a 'display' value of 'inline', 'inline-table', or
    'inline-block' generates an inline-level box.
    """


class InlineBox(InlineLevelBox):
    """
    A box who participates in an inline formatting context and whose content
    also participates in that inline formatting context.

    A non-replaced element with a 'display' value of 'inline' generates an
    inline box.
    """


class TextBox(AnonymousBox, InlineBox):
    """
    A box that contains only text and has no box children.

    Any text in the document ends up in a text box. What CSS calls "anonymous
    inline boxes" are also text boxes.
    """
    def __init__(self, element, text):
        super(TextBox, self).__init__(element)
        self.children = None
        self.text = text


class InlineBlockBox(InlineLevelBox, BlockContainerBox):
    """
    A box that is both inline-level and a block container: it behaves as
    inline on the outside and as a block on the inside.

    A non-replaced element with a 'display' value of 'inline-block' generates an
    inline-block box.
    """


class ReplacedBox(Box):
    """
    A box that is replaced, ie. its content is rendered externally and is opaque
    from CSS’s point of view. Example: <img> elements are replaced.
    """
    def __init__(self, element, replacement):
        super(ReplacedBox, self).__init__(element)
        self.replacement = replacement


class BlockLevelReplacedBox(ReplacedBox, BlockLevelBox):
    """
    A box that is both replaced and block-level.

    A replaced element with a 'display' value of 'block', 'liste-item' or
    'table' generates a block-level replaced box.
    """


class InlineLevelReplacedBox(ReplacedBox, InlineLevelBox):
    """
    A box that is both replaced and inline-level.

    A replaced element with a 'display' value of 'inline', 'inline-table', or
    'inline-block' generates an inline-level replaced box.
    """
