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
 * ReplacedBox
 * ParentBox
 * AtomicInlineLevelBox

Concrete classes:

 * PageBox
 * BlockBox
 * AnonymousBlockBox
 * InlineBox
 * InlineBlockBox
 * BlockReplacedBox
 * InlineReplacedBox
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


# The *Box classes have many attributes and methods, but that's the way it is
# pylint: disable=R0904,R0902

class Box(object):
    """Abstract base class for all boxes."""
    # Definitions for the rules generating anonymous table boxes
    # http://www.w3.org/TR/CSS21/tables.html#anonymous-boxes
    proper_table_child = False
    internal_table_or_caption = False
    tabular_container = False

    # Default, may be overriden on instances.
    is_table_wrapper = False


    def __init__(self, element_tag, sourceline, style):
        self.element_tag = element_tag
        self.sourceline = sourceline  # for debugging only
        # Copying might not be needed, but let’s be careful with mutable
        # objects.
        self.style = style.copy()

    def __repr__(self):
        return '<%s %s %s>' % (
            type(self).__name__, self.element_tag, self.sourceline)

    @classmethod
    def anonymous_from(cls, parent, *args, **kwargs):
        """Return an anonymous box that inherits from ``parent``."""
        return cls(parent.element_tag, parent.sourceline,
                   parent.style.inherit_from(),
                   *args, **kwargs)

    def copy(self):
        """Return shallow copy of the box."""
        cls = type(self)
        # Create a new instance without calling __init__: initializing
        # styles may be kinda expensive, no need to do it again.
        new_box = cls.__new__(cls)
        # Copy attributes
        new_box.__dict__.update(self.__dict__)
        new_box.style = self.style.copy()
        return new_box

    def translate(self, dx=0, dy=0):
        """Change the box’s position.

        Also update the children’s positions accordingly.

        """
        # Overridden in ParentBox to also translate children, if any.
        self.position_x += dx
        self.position_y += dy

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


class ParentBox(Box):
    """A box that has children."""
    def __init__(self, element_tag, sourceline, style, children):
        super(ParentBox, self).__init__(element_tag, sourceline, style)
        self.children = tuple(children)

    def enumerate_skip(self, skip_num=0):
        """Yield ``(child, child_index)`` tuples for each child.

        ``skip_num`` children are skipped before iterating over them.

        """
        for index in xrange(skip_num, len(self.children)):
            yield index, self.children[index]

    def copy_with_children(self, children):
        """Create a new equivalent box with given ``children``."""
        new_box = self.copy()
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

    def translate(self, dx=0, dy=0):
        """Change the position of the box.

        Also update the children’s positions accordingly.

        """
        super(ParentBox, self).translate(dx, dy)
        for child in self.children:
            child.translate(dx, dy)


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


class LineBox(ParentBox):
    """A box that represents a line in an inline formatting context.

    Can only contain inline-level boxes.

    In early stages of building the box tree a single line box contains many
    consecutive inline boxes. Later, during layout phase, each line boxes will
    be split into multiple line boxes, one for each actual line.

    """
    def __init__(self, element_tag, sourceline, style, children):
        assert style.anonymous
        super(LineBox, self).__init__(element_tag, sourceline, style, children)


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


class TextBox(InlineLevelBox):
    """A box that contains only text and has no box children.

    Any text in the document ends up in a text box. What CSS calls "anonymous
    inline boxes" are also text boxes.

    """
    def __init__(self, element_tag, sourceline, style, text):
        assert style.anonymous
        assert text
        super(TextBox, self).__init__(element_tag, sourceline, style)
        text_transform = style.text_transform
        if text_transform != 'none':
            text = {
                'uppercase': lambda t: t.upper(),
                'lowercase': lambda t: t.lower(),
                # Python’s unicode.captitalize is not the same.
                'capitalize': lambda t: t.title(),
            }[text_transform](text)
        self.text = text

    def copy_with_text(self, text):
        """Return a new TextBox identical to this one except for the text."""
        assert text
        new_box = self.copy()
        new_box.text = text
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
    def __init__(self, element_tag, sourceline, style, replacement):
        super(ReplacedBox, self).__init__(element_tag, sourceline, style)
        self.replacement = replacement


class BlockReplacedBox(ReplacedBox, BlockLevelBox):
    """A box that is both replaced and block-level.

    A replaced element with a ``display`` value of ``block``, ``liste-item`` or
    ``table`` generates a block-level replaced box.

    """


class InlineReplacedBox(ReplacedBox, AtomicInlineLevelBox):
    """A box that is both replaced and inline-level.

    A replaced element with a ``display`` value of ``inline``,
    ``inline-table``, or ``inline-block`` generates an inline-level replaced
    box.

    """


class TableBox(BlockLevelBox, ParentBox):
    """Box for elements with ``display: table``"""
    # Definitions for the rules generating anonymous table boxes
    # http://www.w3.org/TR/CSS21/tables.html#anonymous-boxes
    tabular_container = True


class InlineTableBox(TableBox):
    """Box for elements with ``display: inline-table``"""


class TableRowGroupBox(ParentBox):
    """Box for elements with ``display: table-row-group``"""
    proper_table_child = True
    internal_table_or_caption = True
    tabular_container = True
    proper_parents = (TableBox, InlineTableBox)

    # Default values. May be overriden on instances.
    header_group = False
    footer_group = False


class TableRowBox(ParentBox):
    """Box for elements with ``display: table-row``"""
    proper_table_child = True
    internal_table_or_caption = True
    tabular_container = True
    proper_parents = (TableBox, InlineTableBox, TableRowGroupBox)


class TableColumnGroupBox(ParentBox):
    """Box for elements with ``display: table-column-group``"""
    proper_table_child = True
    internal_table_or_caption = True
    proper_parents = (TableBox, InlineTableBox)

    # Default value. May be overriden on instances.
    span = 1

    # Columns groups never have margins or paddings
    margin_top = 0
    margin_bottom = 0
    margin_left = 0
    margin_right = 0

    padding_top = 0
    padding_bottom = 0
    padding_left = 0
    padding_right = 0


# Not really a parent box, but pretending to be removes some special cases.
class TableColumnBox(ParentBox):
    """Box for elements with ``display: table-column``"""
    proper_table_child = True
    internal_table_or_caption = True
    proper_parents = (TableBox, InlineTableBox, TableColumnGroupBox)

    # Default value. May be overriden on instances.
    span = 1

    # Columns never have margins or paddings
    margin_top = 0
    margin_bottom = 0
    margin_left = 0
    margin_right = 0

    padding_top = 0
    padding_bottom = 0
    padding_left = 0
    padding_right = 0


class TableCellBox(BlockContainerBox):
    """Box for elements with ``display: table-cell``"""
    internal_table_or_caption = True

    # Default values. May be overriden on instances.
    colspan = 1
    rowspan = 1


class TableCaptionBox(BlockBox):
    """Box for elements with ``display: table-caption``"""
    proper_table_child = True
    internal_table_or_caption = True
    proper_parents = (TableBox, InlineTableBox)


class PageBox(ParentBox):
    """Box for a page.

    Initially the whole document will be in the box for the root element.
    During layout a new page box is created after every page break.

    """
    def __init__(self, page_type, style):
        self.page_type = page_type
        # Page boxes are not linked to any element.
        super(PageBox, self).__init__(
            element_tag=None, sourceline=None, style=style, children=[])

    def __repr__(self):
        return '<%s %s>' % (type(self).__name__, self.page_type)


class MarginBox(BlockContainerBox):
    """Box in page margins, as defined in CSS3 Paged Media"""
    def __init__(self, at_keyword, style, children=[]):
        self.at_keyword = at_keyword
        # Margin boxes are not linked to any element.
        super(MarginBox, self).__init__(
            element_tag=None, sourceline=None, style=style, children=children)

    def __repr__(self):
        return '<%s %s>' % (type(self).__name__, self.at_keyword)
