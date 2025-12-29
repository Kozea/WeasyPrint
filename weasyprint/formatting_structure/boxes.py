"""Classes for all types of boxes in the CSS formatting structure / box model.

See https://www.w3.org/TR/CSS21/visuren.html

Names are the same as in CSS 2.1 with the exception of ``TextBox``. In
WeasyPrint, any text is in a ``TextBox``. What CSS calls anonymous inline boxes
are text boxes but not all text boxes are anonymous inline boxes.

See https://www.w3.org/TR/CSS21/visuren.html#anonymous

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
* InlineBox
* InlineBlockBox
* BlockReplacedBox
* InlineReplacedBox
* TextBox
* LineBox
* Various table-related Box subclasses

All concrete box classes whose name contains "Inline" or "Block" have one of
the following "outside" behavior:

* Block-level (inherits from :class:`BlockLevelBox`)
* Inline-level (inherits from :class:`InlineLevelBox`)

and one of the following "inside" behavior:

* Block container (inherits from :class:`BlockContainerBox`)
* Inline content (InlineBox and :class:`TextBox`)
* Replaced content (inherits from :class:`ReplacedBox`)

… with various combinasions of both.

See respective docstrings for details.

"""

import itertools

from ..css import AnonymousStyle


class Box:
    """Abstract base class for all boxes."""
    # Definitions for the rules generating anonymous table boxes
    # https://www.w3.org/TR/CSS21/tables.html#anonymous-boxes
    proper_table_child = False
    internal_table_or_caption = False
    tabular_container = False

    # Keep track of removed collapsing spaces for wrap opportunities.
    leading_collapsible_space = False
    trailing_collapsible_space = False

    # Default, may be overriden on instances.
    is_table_wrapper = False
    is_flex_item = False
    is_grid_item = False
    is_for_root_element = False
    is_column = False
    is_leader = False
    is_outside_marker = False

    # Other properties
    transformation_matrix = None
    bookmark_label = None
    string_set = None
    footnote = None
    cached_counter_values = None
    missing_link = None
    link_annotation = None
    force_fragmentation = False

    # Default, overriden on some subclasses
    def all_children(self):
        return self.children

    def descendants(self, placeholders=False):
        """A flat generator for a box, its children and descendants."""
        yield self
        for child in self.children:
            if placeholders or isinstance(child, Box):
                yield from child.descendants(placeholders)
            else:
                yield child

    def __init__(self, element_tag, style, element):
        self.element_tag = element_tag
        self.element = element
        self.style = style
        self.remove_decoration_sides = set()
        self.children = []
        self.first_letter_style = None
        self.first_line_style = None

    def __repr__(self):
        return f'<{type(self).__name__} {self.element_tag}>'

    @classmethod
    def anonymous_from(cls, parent, *args, **kwargs):
        """Return an anonymous box that inherits from ``parent``."""
        style = AnonymousStyle(parent.style)
        return cls(parent.element_tag, style, parent.element, *args, **kwargs)

    def copy(self):
        """Return shallow copy of the box."""
        cls = type(self)
        # Create a new instance without calling __init__: parameters are
        # different depending on the class.
        new_box = cls.__new__(cls)
        # Copy attributes
        new_box.__dict__.update(self.__dict__)
        return new_box

    def deepcopy(self):
        """Return a copy of the box with recursive copies of its children."""
        return self.copy()

    def translate(self, dx=0, dy=0, ignore_floats=False):
        """Change the box’s position.

        Also update the children’s positions accordingly.

        """
        # Overridden in ParentBox to also translate children, if any.
        if dx == dy == 0:
            return
        self.position_x += dx
        self.position_y += dy
        for child in self.all_children():
            if not (ignore_floats and child.is_floated()):
                child.translate(dx, dy, ignore_floats)

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

    def hit_area(self):
        """Return the (x, y, w, h) rectangle where the box is clickable."""
        # "Border area. That's the area that hit-testing is done on."
        # https://lists.w3.org/Archives/Public/www-style/2012Jun/0318.html
        # TODO: manage the border radii, use outer_border_radii instead
        return (self.border_box_x(), self.border_box_y(),
                self.border_width(), self.border_height())

    def rounded_box(self, bt, br, bb, bl):
        """Position, size and radii of a box inside the outer border box.

        bt, br, bb, and bl are distances from the outer border box,
        defining a rectangle to be rounded.

        """
        tlrx, tlry = self.border_top_left_radius
        trrx, trry = self.border_top_right_radius
        brrx, brry = self.border_bottom_right_radius
        blrx, blry = self.border_bottom_left_radius

        tlrx = max(0, tlrx - bl)
        tlry = max(0, tlry - bt)
        trrx = max(0, trrx - br)
        trry = max(0, trry - bt)
        brrx = max(0, brrx - br)
        brry = max(0, brry - bb)
        blrx = max(0, blrx - bl)
        blry = max(0, blry - bb)

        x = self.border_box_x() + bl
        y = self.border_box_y() + bt
        width = self.border_width() - bl - br
        height = self.border_height() - bt - bb

        # Fix overlapping curves
        # See https://www.w3.org/TR/css-backgrounds-3/#corner-overlap
        ratio = min([1] + [
            extent / sum_radii
            for extent, sum_radii in (
                (width, tlrx + trrx),
                (width, blrx + brrx),
                (height, tlry + blry),
                (height, trry + brry),
            )
            if sum_radii > 0
        ])
        return (
            x, y, width, height,
            (tlrx * ratio, tlry * ratio),
            (trrx * ratio, trry * ratio),
            (brrx * ratio, brry * ratio),
            (blrx * ratio, blry * ratio))

    def rounded_box_ratio(self, ratio):
        return self.rounded_box(
            self.border_top_width * ratio,
            self.border_right_width * ratio,
            self.border_bottom_width * ratio,
            self.border_left_width * ratio)

    def rounded_padding_box(self):
        """Return the position, size and radii of the rounded padding box."""
        return self.rounded_box(
            self.border_top_width,
            self.border_right_width,
            self.border_bottom_width,
            self.border_left_width)

    def rounded_border_box(self):
        """Return the position, size and radii of the rounded border box."""
        return self.rounded_box(0, 0, 0, 0)

    def rounded_content_box(self):
        """Return the position, size and radii of the rounded content box."""
        return self.rounded_box(
            self.border_top_width + self.padding_top,
            self.border_right_width + self.padding_right,
            self.border_bottom_width + self.padding_bottom,
            self.border_left_width + self.padding_left)

    # Positioning schemes

    def is_floated(self):
        """Return whether this box is floated."""
        return self.style['float'] in ('left', 'right')

    def is_footnote(self):
        """Return whether this box is a footnote."""
        return self.style['float'] == 'footnote'

    def is_absolutely_positioned(self):
        """Return whether this box is in the absolute positioning scheme."""
        return self.style['position'] in ('absolute', 'fixed')

    def is_running(self):
        """Return whether this box is a running element."""
        return self.style['position'][0] == 'running()'

    def is_in_normal_flow(self):
        """Return whether this box is in normal flow."""
        return not (
            self.is_floated() or self.is_absolutely_positioned() or
            self.is_running() or self.is_footnote())

    def is_monolithic(self):
        """Return whether this box is monolithic."""
        # https://www.w3.org/TR/css-break-3/#monolithic
        return (
            isinstance(self, AtomicInlineLevelBox) or
            isinstance(self, ReplacedBox) or
            self.style['overflow'] in ('auto', 'scroll') or
            (self.style['overflow'] == 'hidden' and
             self.style['height'] != 'auto'))

    def establishes_formatting_context(self):
        """Return whether this box establishes a block formatting context."""
        # See https://www.w3.org/TR/CSS2/visuren.html#block-formatting
        return (
            self.is_floated() or
            self.is_absolutely_positioned() or
            self.is_column or
            (isinstance(self, BlockContainerBox) and not isinstance(self, BlockBox)) or
            (isinstance(self, BlockBox) and self.style['overflow'] != 'visible') or
            'flow-root' in self.style['display'])

    # Start and end page values for named pages

    def page_values(self):
        """Return start and end page values."""
        return (self.style['page'], self.style['page'])

    # PDF attachments

    def is_attachment(self):
        """Return whether this link should be stored as a PDF attachment."""
        from ..html import element_has_link_type

        if self.element is not None and self.element.tag == 'a':
            return element_has_link_type(self.element, 'attachment')
        return False

    # Forms

    def is_input(self):
        """Return whether this box is a form input."""
        # https://html.spec.whatwg.org/multipage/forms.html#category-submit
        if self.style['appearance'] == 'auto' and self.element is not None:
            if self.element.tag in ('button', 'input', 'select', 'textarea'):
                return not isinstance(self, (LineBox, TextBox))
        return False

    def is_form(self):
        """Return whether this box is a form element."""
        if self.element is None:
            return False
        return self.element.tag == 'form'


class ParentBox(Box):
    """A box that has children."""
    def __init__(self, element_tag, style, element, children):
        super().__init__(element_tag, style, element)
        self.children = tuple(children)

    def _reset_spacing(self, side):
        """Set to 0 the margin, padding and border of ``side``."""
        self.remove_decoration_sides.add(side)
        setattr(self, f'margin_{side}', 0)
        setattr(self, f'padding_{side}', 0)
        setattr(self, f'border_{side}_width', 0)

    def remove_decoration(self, start, end):
        if self.style['box_decoration_break'] == 'clone':
            return
        if start:
            self._reset_spacing('top')
        if end:
            self._reset_spacing('bottom')

    def copy_with_children(self, new_children):
        """Create a new equivalent box with given ``new_children``."""
        new_box = self.copy()
        new_box.children = new_children

        # Clear and reset removed decorations as we don't want to keep the
        # previous data, for example when a box is split between two pages.
        self.remove_decoration_sides = set()

        return new_box

    def deepcopy(self):
        result = self.copy()
        result.children = list(child.deepcopy() for child in self.children)
        return result

    def get_wrapped_table(self):
        """Get the table wrapped by the box."""
        assert self.is_table_wrapper
        for child in self.children:
            if isinstance(child, TableBox):
                return child
        else:  # pragma: no cover
            raise ValueError('Table wrapper without a table')

    def page_values(self):
        start_value, end_value = super().page_values()
        # TODO: We should find Class A possible page breaks according to
        # https://drafts.csswg.org/css-page-3/#propdef-page
        # Keep only children in normal flow for now.
        children = [
            child for child in self.children if child.is_in_normal_flow()]
        if children:
            if len(children) == 1:
                page_values = children[0].page_values()
                start_value = page_values[0] or start_value
                end_value = page_values[1] or end_value
            else:
                start_box, end_box = children[0], children[-1]
                start_value = start_box.page_values()[0] or start_value
                end_value = end_box.page_values()[1] or end_value
        return start_value, end_value

    def top_margin_collapses(self):
        return not (
            self.border_top_width or self.padding_top or
            self.is_flex_item or self.is_grid_item or
            self.establishes_formatting_context() or
            self.is_table_wrapper or
            self.is_for_root_element)

    def bottom_margin_collapses(self):
        return not (
            self.border_bottom_width or self.padding_bottom or
            self.is_flex_item or self.is_grid_item or
            self.establishes_formatting_context() or
            self.is_table_wrapper or
            self.is_for_root_element)


class BlockLevelBox(Box):
    """A box that participates in an block formatting context.

    An element with a ``display`` value of ``block``, ``list-item`` or
    ``table`` generates a block-level box.

    """
    clearance = None


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
    text_overflow = 'clip'
    block_ellipsis = 'none'

    @classmethod
    def anonymous_from(cls, parent, *args, **kwargs):
        box = super().anonymous_from(parent, *args, **kwargs)
        if parent.style['overflow'] != 'visible':
            box.text_overflow = parent.style['text_overflow']
        return box


class InlineLevelBox(Box):
    """A box that participates in an inline formatting context.

    An inline-level box that is not an inline box is said to be "atomic". Such
    boxes are inline blocks, replaced elements and inline tables.

    An element with a ``display`` value of ``inline``, ``inline-table``, or
    ``inline-block`` generates an inline-level box.

    """
    def remove_decoration(self, start, end):
        if self.style['box_decoration_break'] == 'clone':
            return
        ltr = self.style['direction'] == 'ltr'
        if start:
            self._reset_spacing('left' if ltr else 'right')
        if end:
            self._reset_spacing('right' if ltr else 'left')


class InlineBox(InlineLevelBox, ParentBox):
    """An inline box with inline children.

    A box that participates in an inline formatting context and whose content
    also participates in that inline formatting context.

    A non-replaced element with a ``display`` value of ``inline`` generates an
    inline box.

    """
    def hit_area(self):
        """Return the (x, y, w, h) rectangle where the box is clickable."""
        # Use line-height (margin_height) rather than border_height
        return (self.border_box_x(), self.position_y,
                self.border_width(), self.margin_height())


class TextBox(InlineLevelBox):
    """A box that contains only text and has no box children.

    Any text in the document ends up in a text box. What CSS calls "anonymous
    inline boxes" are also text boxes.

    """
    justification_spacing = 0

    def __init__(self, element_tag, style, element, text):
        assert text
        super().__init__(element_tag, style, element)
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
    def __init__(self, element_tag, style, element, replacement):
        super().__init__(element_tag, style, element)
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
    # https://www.w3.org/TR/CSS21/tables.html#anonymous-boxes
    tabular_container = True

    def all_children(self):
        return itertools.chain(self.children, self.column_groups)

    def translate(self, dx=0, dy=0, ignore_floats=False):
        self.column_positions = [
            position + dx for position in self.column_positions]
        return super().translate(dx, dy, ignore_floats)

    def page_values(self):
        return (self.style['page'], self.style['page'])


class InlineTableBox(TableBox):
    """Box for elements with ``display: inline-table``"""


class TableRowGroupBox(ParentBox):
    """Box for elements with ``display: table-row-group``"""
    proper_table_child = True
    internal_table_or_caption = True
    tabular_container = True
    proper_parents = (TableBox, InlineTableBox)

    # Default values. May be overriden on instances.
    is_header = False
    is_footer = False


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

    # Columns groups never have margins or paddings
    margin_top = 0
    margin_bottom = 0
    margin_left = 0
    margin_right = 0

    padding_top = 0
    padding_bottom = 0
    padding_left = 0
    padding_right = 0

    def get_cells(self):
        """Return cells that originate in the group's columns."""
        return [
            cell for column in self.children for cell in column.get_cells()]

    @property
    def span(self):
        if self.children:
            return len(self.children)
        else:
            try:
                return max(int(self.element.get('span', '').strip()), 1)
            except ValueError:
                return 1


# Not really a parent box, but pretending to be removes some corner cases.
class TableColumnBox(ParentBox):
    """Box for elements with ``display: table-column``"""
    proper_table_child = True
    internal_table_or_caption = True
    proper_parents = (TableBox, InlineTableBox, TableColumnGroupBox)

    # Columns never have margins or paddings
    margin_top = 0
    margin_bottom = 0
    margin_left = 0
    margin_right = 0

    padding_top = 0
    padding_bottom = 0
    padding_left = 0
    padding_right = 0

    def get_cells(self):
        """Return cells that originate in the column.

        Is set on instances.

        """
        raise NotImplementedError

    @property
    def span(self):
        try:
            return max(int(self.element.get('span', '').strip()), 1)
        except ValueError:
            return 1


class TableCellBox(BlockContainerBox):
    """Box for elements with ``display: table-cell``"""
    internal_table_or_caption = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # HTML 4.01 gives special meaning to colspan=0
        # https://www.w3.org/TR/html401/struct/tables.html#adef-rowspan
        # but HTML 5 removed it
        # https://html.spec.whatwg.org/multipage/tables.html#attr-tdth-colspan
        # rowspan=0 is still there though.
        try:
            self.colspan = max(int(self.element.get('colspan', '').strip()), 1)
        except (AttributeError, ValueError):
            self.colspan = 1
        try:
            self.rowspan = max(int(self.element.get('rowspan', '').strip()), 0)
        except (AttributeError, ValueError):
            self.rowspan = 1


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
        super().__init__(
            element_tag=None, style=style, element=None, children=[])

    def __repr__(self):
        return f'<{type(self).__name__} {self.page_type}>'

    @property
    def bleed(self):
        return {
            side: self.style[f'bleed_{side}'].value
            for side in ('top', 'right', 'bottom', 'left')}

    @property
    def bleed_area(self):
        return (
            -self.bleed['left'], -self.bleed['top'],
            self.margin_width() + self.bleed['left'] + self.bleed['right'],
            self.margin_height() + self.bleed['top'] + self.bleed['bottom'])


class MarginBox(BlockContainerBox):
    """Box in page margins, as defined in CSS3 Paged Media"""
    def __init__(self, at_keyword, style):
        self.at_keyword = at_keyword
        # Margin boxes are not linked to any element.
        super().__init__(
            element_tag=None, style=style, element=None, children=[])

    def __repr__(self):
        return f'<{type(self).__name__} {self.at_keyword}>'


class FootnoteAreaBox(BlockBox):
    """Box displaying footnotes, as defined in GCPM."""
    def __init__(self, page, style):
        self.page = page
        # Footnote area boxes are not linked to any element.
        super().__init__(
            element_tag=None, style=style, element=None, children=[])

    def __repr__(self):
        return f'<{type(self).__name__} @footnote>'


class FlexContainerBox(ParentBox):
    """A box that contains only flex-items."""


class FlexBox(FlexContainerBox, BlockLevelBox):
    """A box that is both block-level and a flex container.

    It behaves as block on the outside and as a flex container on the inside.

    """


class InlineFlexBox(FlexContainerBox, InlineLevelBox):
    """A box that is both inline-level and a flex container.

    It behaves as inline on the outside and as a flex container on the inside.

    """


class GridContainerBox(ParentBox):
    """A box that contains only grid-items."""
    def __init__(self, element_tag, style, element, children):
        super().__init__(element_tag, style, element, children)
        # TODO: we shouldn’t store this in the box but in the rendering context instead.
        self.advancements = {}


class GridBox(GridContainerBox, BlockLevelBox):
    """A box that is both block-level and a grid container.

    It behaves as block on the outside and as a grid container on the inside.

    """


class InlineGridBox(GridContainerBox, InlineLevelBox):
    """A box that is both inline-level and a grid container.

    It behaves as inline on the outside and as a grid container on the inside.

    """
