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
Classes for all types of boxes in the CSS formatting structure / box model.

See http://www.w3.org/TR/CSS21/visuren.html

Names are the same as in CSS 2.1 with the exception of ``TextBox``. In
WeasyPrint, any text is in a ``TextBox``. What CSS calls anonymous inline boxes
are text boxes but not all text boxes are anonymous inline boxes.

See http://www.w3.org/TR/CSS21/visuren.html#anonymous

Abstract classes, should not be instantiated:

 * Box
 * BlockLevelBox
 * InlineLevelBox
 * BlockContainerBox
 * AnonymousBox
 * ReplacedBox
 * ParentBox
 * AtomicInlineLevelBox

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

Apart from :class:`PageBox` and :class:`LineBox`, all concrete box classes have
one of the following "outside" behavior:

 * Block-level (inherits from :class:`BlockLevelBox`)
 * Inline-level (inherits from :class:`InlineLevelBox`)

and one of the following "inside" behavior:

 * Block container (inherits from :class:`BlockContainerBox`)
 * Inline content (InlineBox and :class:`TextBox`)
 * Replaced content (inherits from :class:`ReplacedBox`)

See respective docstrings for details.

"""


from ..css import computed_from_cascaded


# The *Box classes have many attributes and methods, but that's the way it is
# pylint: disable=R0904,R0902

class Box(object):
    """Abstract base class for all boxes."""
    def __init__(self, document, element):
        self.document = document
        # Should never be None
        self.element = element
        self._init_style()

    def _init_style(self):
        """Initialize the style."""
        # Computed values
        # Copying might not be needed, but let’s be careful with mutable
        # objects.
        self.style = self.document.style_for(self.element).copy()

    def __repr__(self):
        return '<%s %s %i>' % (
            type(self).__name__, self.element.tag, self.element.sourceline)

    @property
    def direction(self):
        return self.style.direction

    def _copy(self):
        """Return shallow copy of the box."""
        cls = type(self)
        # Create a new instance without calling __init__: initializing
        # styles may be kinda expensive, no need to do it again.
        new_box = cls.__new__(cls)
        # Copy attributes
        new_box.__dict__.update(self.__dict__)
        new_box.style = self.style.copy()
        return new_box

    def translate(self, x, y):
        """Change the box’s position.

        Also update the children’s positions accordingly.

        """
        # Overridden in ParentBox to also translate children, if any.
        self.position_x += x
        self.position_y += y

    # Heights and widths

    def padding_width(self):
        """Width of the padding box."""
        return self.width + self.padding_left + self.padding_right

    def padding_height(self):
        """Height of the padding box."""
        return self.height + self.padding_top + self.padding_bottom

    def border_width(self):
        """Width of the border box."""
        return self.padding_width() + self.border_left_width + \
            self.border_right_width

    def border_height(self):
        """Height of the border box."""
        return self.padding_height() + self.border_top_width + \
            self.border_bottom_width

    def margin_width(self):
        """Width of the margin box (aka. outer box)."""
        return self.border_width() + self.margin_left + self.margin_right

    def margin_height(self):
        """Height of the margin box (aka. outer box)."""
        return self.border_height() + self.margin_top + self.margin_bottom

    def horizontal_surroundings(self):
        """Sum of all horizontal margins, paddings and borders."""
        return self.margin_left + self.margin_right + \
               self.padding_left + self.padding_right + \
               self.border_left_width + self.border_right_width

    def vertical_surroundings(self):
        """Sum of all vertical margins, paddings and borders."""
        return self.margin_top + self.margin_bottom + \
               self.padding_top + self.padding_bottom + \
               self.border_top_width + self.border_bottom_width

    # Corners positions

    def content_box_x(self):
        """Absolute horizontal position of the content box."""
        return self.position_x + self.margin_left + self.padding_left + \
            self.border_left_width

    def content_box_y(self):
        """Absolute vertical position of the content box."""
        return self.position_y + self.margin_top + self.padding_top + \
            self.border_top_width

    def padding_box_x(self):
        """Absolute horizontal position of the padding box."""
        return self.position_x + self.margin_left + self.border_left_width

    def padding_box_y(self):
        """Absolute vertical position of the padding box."""
        return self.position_y + self.margin_top + self.border_top_width

    def border_box_x(self):
        """Absolute horizontal position of the border box."""
        return self.position_x + self.margin_left

    def border_box_y(self):
        """Absolute vertical position of the border box."""
        return self.position_y + self.margin_top

    def reset_spacing(self, side):
        """Set to 0 the margin, padding and border of ``side``."""
        setattr(self, 'margin_%s' % side, 0)
        setattr(self, 'padding_%s' % side, 0)
        setattr(self, 'border_%s_width' % side, 0)

        self.style['margin_%s' % side] = 0
        self.style['padding_%s' % side] = 0
        self.style['border_%s_width' % side] = 0

    # Positioning schemes

    def is_floated(self):
        """Return whether this box is floated."""
        return self.style.float != 'none'

    def is_absolutely_positioned(self):
        """Return whether this box is in the absolute positioning scheme."""
        return self.style.position in ('absolute', 'fixed')

    def is_in_normal_flow(self):
        """Return whether this box is in normal flow."""
        return not (self.is_floated() or self.is_absolutely_positioned())


class PageBox(Box):
    """Box for a page.

    Initially the whole document will be in a single page box. During layout
    a new page box is created after every page break.

    """
    def __init__(self, document, page_number):
        # starting at 1 for the first page.
        self.page_number = page_number
        # Page boxes are not linked to any element.
        super(PageBox, self).__init__(document, element=None)

    def __repr__(self):
        return '<%s %s>' % (type(self).__name__, self.page_number)

    def _init_style(self):
        """Initialize the style of the page.'"""
        # First page is a right page.
        # TODO: this "should depend on the major writing direction of the
        # document".
        first_is_right = True
        is_right = (self.page_number % 2) == (1 if first_is_right else 0)
        page_type = 'right' if is_right else 'left'
        if self.page_number == 1:
            page_type = 'first_' + page_type
        style = self.document.computed_styles['@page', page_type]
        # Copying might not be needed, but let’s be careful with mutable
        # objects.
        self.style = style.copy()

    @property
    def direction(self):
        return self.root_box.direction


class ParentBox(Box):
    """A box that has children."""
    def __init__(self, document, element, children):
        super(ParentBox, self).__init__(document, element)
        self.children = tuple(children)

    def enumerate_skip(self, skip_num=0):
        """Yield ``(child, child_index)`` tuples for each child.

        ``skip_num`` children are skipped before iterating over them.

        """
        for index in xrange(skip_num, len(self.children)):
            yield index, self.children[index]

    def copy_with_children(self, children):
        """Create a new equivalent box with given ``children``."""
        new_box = self._copy()
        new_box.children = tuple(children)
        return new_box

    def descendants(self):
        """A flat generator for a box, its children and descendants."""
        yield self
        for child in self.children:
            if hasattr(child, 'descendants'):
                for grand_child in child.descendants():
                    yield grand_child
            else:
                yield child

    def translate(self, x, y):
        """Change the position of the box.

        Also update the children’s positions accordingly.

        """
        super(ParentBox, self).translate(x, y)
        for child in self.children:
            child.translate(x, y)


class BlockLevelBox(Box):
    """A box that participates in an block formatting context.

    An element with a ``display`` value of ``block``, ``list-item`` or
    ``table`` generates a block-level box.

    """


class BlockContainerBox(ParentBox):
    """A box that contains only block-level boxes or only line boxes.

    A box that either contains only block-level boxes or establishes an inline
    formatting context and thus contains only line boxes.

    A non-replaced element with a ``display`` value of ``block``,
    ``list-item``, ``inline-block`` or 'table-cell' generates a block container
    box.

    """


class BlockBox(BlockContainerBox, BlockLevelBox):
    """A block-level box that is also a block container.

    A non-replaced element with a ``display`` value of ``block``, ``list-item``
    generates a block box.

    """


class AnonymousBox(Box):
    """A box that is not directly generated by an element.

    Inherits style instead of copying them.

    """
    def _init_style(self):
        parent_style = self.document.style_for(self.element)
        self.style = computed_from_cascaded(self.element, {}, parent_style)

    # These properties are not inherited so they always have their initial
    # value, zero. The used value is zero too.
    margin_top = 0
    margin_bottom = 0
    margin_left = 0
    margin_right = 0

    padding_top = 0
    padding_bottom = 0
    padding_left = 0
    padding_right = 0

    border_top_width = 0
    border_bottom_width = 0
    border_left_width = 0
    border_right_width = 0


class AnonymousBlockBox(AnonymousBox, BlockBox):
    """A box that wraps inline-level boxes where block-level boxes are needed.

    Block containers (eventually) contain either only block-level boxes or only
    inline-level boxes. When they initially contain both, consecutive
    inline-level boxes are wrapped in an anonymous block box by
    :meth:`boxes.inline_in_block`.

    """


class LineBox(AnonymousBox, ParentBox):
    """A box that represents a line in an inline formatting context.

    Can only contain inline-level boxes.

    In early stages of building the box tree a single line box contains many
    consecutive inline boxes. Later, during layout phase, each line boxes will
    be split into multiple line boxes, one for each actual line.

    """


class InlineLevelBox(Box):
    """A box that participates in an inline formatting context.

    An inline-level box that is not an inline box is said to be "atomic". Such
    boxes are inline blocks, replaced elements and inline tables.

    An element with a ``display`` value of ``inline``, ``inline-table``, or
    ``inline-block`` generates an inline-level box.

    """


class InlineBox(InlineLevelBox, ParentBox):
    """An inline box with inline children.

    A box that participates in an inline formatting context and whose content
    also participates in that inline formatting context.

    A non-replaced element with a ``display`` value of ``inline`` generates an
    inline box.

    """


class TextBox(AnonymousBox, InlineLevelBox):
    """A box that contains only text and has no box children.

    Any text in the document ends up in a text box. What CSS calls "anonymous
    inline boxes" are also text boxes.

    """
    def __init__(self, document, element, text):
        assert text
        super(TextBox, self).__init__(document, element)
        self.utf8_text = text.encode('utf8')

    def copy_with_text(self, utf8_text):
        assert utf8_text
        new_box = self._copy()
        new_box.utf8_text = utf8_text
        return new_box


class AtomicInlineLevelBox(InlineLevelBox):
    """An atomic box in an inline formatting context.

    This inline-level box cannot be split for line breaks.

    """


class InlineBlockBox(AtomicInlineLevelBox, BlockContainerBox):
    """A box that is both inline-level and a block container.

    It behaves as inline on the outside and as a block on the inside.

    A non-replaced element with a 'display' value of 'inline-block' generates
    an inline-block box.

    """


class ReplacedBox(Box):
    """A box whose content is replaced.

    For example, ``<img>`` are replaced: their content is rendered externally
    and is opaque from CSS’s point of view.

    """
    def __init__(self, document, element, replacement):
        super(ReplacedBox, self).__init__(document, element)
        self.replacement = replacement


class BlockLevelReplacedBox(ReplacedBox, BlockLevelBox):
    """A box that is both replaced and block-level.

    A replaced element with a ``display`` value of ``block``, ``liste-item`` or
    ``table`` generates a block-level replaced box.

    """


class InlineLevelReplacedBox(ReplacedBox, AtomicInlineLevelBox):
    """A box that is both replaced and inline-level.

    A replaced element with a ``display`` value of ``inline``,
    ``inline-table``, or ``inline-block`` generates an inline-level replaced
    box.

    """


class ImageMarkerBox(InlineLevelReplacedBox, AnonymousBox):
    """A box for an image list marker.

    An element with ``display: list-item`` and a valid image for
    ``list-style-image`` generates an image list maker box.  This box is
    anonymous, inline-level, and replaced.

    """
