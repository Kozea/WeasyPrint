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
Building helpers.

Functions building a correct formatting structure from a DOM document,
including handling of anonymous boxes and whitespace processing.

"""

import re
from . import boxes, counters
from .. import html
from ..css import properties


# Maps values of the ``display`` CSS property to box types.
BOX_TYPE_FROM_DISPLAY = {
    'block': boxes.BlockBox,
    'list-item': boxes.BlockBox,
    'inline': boxes.InlineBox,
    'inline-block': boxes.InlineBlockBox,
    'table': boxes.TableBox,
    'inline-table': boxes.InlineTableBox,
    'table-row': boxes.TableRowBox,
    'table-row-group': boxes.TableRowGroupBox,
    'table-header-group': boxes.TableRowGroupBox,
    'table-footer-group': boxes.TableRowGroupBox,
    'table-column': boxes.TableColumnBox,
    'table-column-group': boxes.TableColumnGroupBox,
    'table-cell': boxes.TableCellBox,
    'table-caption': boxes.TableCaptionBox,
}


def build_formatting_structure(document):
    """Build a formatting structure (box tree) from a ``document``."""
    box, = dom_to_box(document, document.dom)
    # If this is changed, maybe update weasy.layout.pages.make_margin_boxes()
    box = process_whitespace(box)
    box = anonymous_table_boxes(box)
    box = inline_in_block(box)
    box = block_in_inline(box)
    box = set_canvas_background(box)
    box = set_viewport_overflow(box)
    return box


def dom_to_box(document, element, state=None):
    """Convert a DOM element and its children into a box with children.

    Return a list of boxes. Most of the time the list will have one item but
    may have zero or more than one.

    Eg.::

        <p>Some <em>emphasised</em> text.<p>

    gives (not actual syntax)::

        BlockBox[
            TextBox['Some '],
            InlineBox[
                TextBox['emphasised'],
            ],
            TextBox[' text.'],
        ]

    ``TextBox``es are anonymous inline boxes:
    See http://www.w3.org/TR/CSS21/visuren.html#anonymous

    """
    if not isinstance(element.tag, basestring):
        # lxml.html already converts HTML entities to text.
        # Here we ignore comments and XML processing instructions.
        return []

    style = document.style_for(element)

    # TODO: should be the used value. When does the used value for `display`
    # differ from the computer value?
    display = style.display
    if display == 'none':
        return []

    box = BOX_TYPE_FROM_DISPLAY[display](
        element.tag, element.sourceline, style, [])

    if state is None:
        # use a list to have a shared mutable object
        state = (
            # Shared mutable objects:
            [0],  # quote_depth: single integer
            {},  # counter_values: name -> stacked/scoped values
            [set()]  # counter_scopes: DOM tree depths -> counter names
        )
    _quote_depth, counter_values, counter_scopes = state

    update_counters(state, style)

    children = []
    if display == 'list-item':
        children.extend(add_box_marker(document, counter_values, box))

    # If this element’s direct children create new scopes, the counter
    # names will be in this new list
    counter_scopes.append(set())

    children.extend(pseudo_to_box(document, state, element, 'before'))
    text = element.text
    if text:
        children.append(boxes.TextBox.anonymous_from(box, text))
    for child_element in element:
        children.extend(dom_to_box(document, child_element, state))
        text = child_element.tail
        if text:
            children.append(boxes.TextBox.anonymous_from(box, text))
    children.extend(pseudo_to_box(document, state, element, 'after'))

    # Scopes created by this element’s children stop here.
    for name in counter_scopes.pop():
        counter_values[name].pop()

    box = box.copy_with_children(children)

    # Specific handling for the element. (eg. replaced element)
    return html.handle_element(document, element, box)


def pseudo_to_box(document, state, element, pseudo_type):
    """Yield the box for a :before or :after pseudo-element if there is one."""
    style = document.style_for(element, pseudo_type)
    if pseudo_type and style is None:
        # Pseudo-elements with no style at all do not get a StyleDict
        # Their initial content property computes to 'none'.
        return

    # TODO: should be the used value. When does the used value for `display`
    # differ from the computer value?
    display = style.display
    content = style.content
    if 'none' in (display, content) or content == 'normal':
        return

    box = BOX_TYPE_FROM_DISPLAY[display](
        '%s:%s' % (element.tag, pseudo_type), element.sourceline, style, [])

    quote_depth, counter_values, _counter_scopes = state
    update_counters(state, style)
    children = []
    if display == 'list-item':
        children.extend(add_box_marker(document, counter_values, box))
    children.extend(content_to_boxes(
        document, style, box, quote_depth, counter_values))

    yield box.copy_with_children(children)


def content_to_boxes(document, style, parent_box, quote_depth, counter_values):
    """Takes the value of a ``content`` property and yield boxes."""
    texts = []
    for type_, value in style.content:
        if type_ == 'STRING':
            texts.append(value)
        elif type_ == 'URI':
            image = document.get_image_from_uri(value)
            if image is not None:
                text = u''.join(texts)
                if text:
                    yield boxes.TextBox.anonymous_from(parent_box, text)
                texts = []
                yield boxes.InlineReplacedBox.anonymous_from(parent_box, image)
        elif type_ == 'counter':
            counter_name, counter_style = value
            counter_value = counter_values.get(counter_name, [0])[-1]
            texts.append(counters.format(counter_value, counter_style))
        elif type_ == 'counters':
            counter_name, separator, counter_style = value
            texts.append(separator.join(
                counters.format(counter_value, counter_style)
                for counter_value in counter_values.get(counter_name, [0])
            ))
        else:
            assert type_ == 'QUOTE'
            is_open, insert = value
            if not is_open:
                quote_depth[0] = max(0, quote_depth[0] - 1)
            if insert:
                open_quotes, close_quotes = style.quotes
                quotes = open_quotes if is_open else close_quotes
                texts.append(quotes[min(quote_depth[0], len(quotes) - 1)])
            if is_open:
                quote_depth[0] += 1
    text = u''.join(texts)
    if text:
        yield boxes.TextBox.anonymous_from(parent_box, text)


def update_counters(state, style):
    """Handle the ``counter-*`` properties."""
    _quote_depth, counter_values, counter_scopes = state
    sibling_scopes = counter_scopes[-1]

    for name, value in style.counter_reset:
        if name in sibling_scopes:
            counter_values[name].pop()
        else:
            sibling_scopes.add(name)
        counter_values.setdefault(name, []).append(value)

    # Disabled for now, only exists in Lists3’s editor’s draft.
    for name, value in []: # XXX style.counter_set:
        values = counter_values.setdefault(name, [])
        if not values:
            if name in sibling_scopes:
                counter_values[name].pop()
            else:
                sibling_scopes.add(name)
            values.append(0)
        values[-1] = value

    counter_increment = style.counter_increment
    if counter_increment == 'auto':
        # 'auto' is the initial value but is not valid in stylesheet:
        # there was no counter-increment declaration for this element.
        # (Or the winning value was 'initial'.)
        # http://dev.w3.org/csswg/css3-lists/#declaring-a-list-item
        if style.display == 'list-item':
            counter_increment = [('list-item', 1)]
        else:
            counter_increment = []
    for name, value in counter_increment:
        values = counter_values.setdefault(name, [])
        if not values:
            if name in sibling_scopes:
                counter_values[name].pop()
            else:
                sibling_scopes.add(name)
            values.append(0)
        values[-1] += value


def add_box_marker(document, counter_values, box):
    """Add a list marker to boxes for elements with ``display: list-item``,
    and yield children to add a the start of the box.

    See http://www.w3.org/TR/CSS21/generate.html#lists

    """
    style = box.style
    image = style.list_style_image
    if image != 'none':
        # surface may be None here too, in case the image is not available.
        image = document.get_image_from_uri(image)
    else:
        image = None

    if image is None:
        type_ = style.list_style_type
        if type_ == 'none':
            return
        counter_value = counter_values['list-item'][-1]
        marker_text = counters.format_list_marker(counter_value, type_)
        marker_box = boxes.TextBox.anonymous_from(box, marker_text)
    else:
        marker_box = boxes.InlineReplacedBox.anonymous_from(box, image)
        marker_box.is_list_marker = True
    marker_box.element_tag += '::marker'

    position = style.list_style_position
    if position == 'inside':
        side = 'right' if style.direction == 'ltr' else 'left'
        marker_box.style['margin_' + side] = style.font_size * 0.5
        yield marker_box
    elif position == 'outside':
        box.outside_list_marker = marker_box


def is_whitespace(box, _has_non_whitespace=re.compile('\S').search):
    """Return True if ``box`` is a TextBox with only whitespace."""
    return (
        isinstance(box, boxes.TextBox)
        and not _has_non_whitespace(box.text)
    )


def wrap_improper(box, children, wrapper_type, test=None):
    """
    Wrap consecutive children that do not pass ``test`` in a box of type
    ``wrapper_type``.

    ``test`` defaults to children being of the same type as ``wrapper_type``.

    """
    if test is None:
        test = lambda child: isinstance(child, wrapper_type)
    improper = []
    for child in children:
        if test(child):
            if improper:
                wrapper = wrapper_type.anonymous_from(box, children=[])
                # Apply the rules again on the new wrapper
                yield table_boxes_children(wrapper, improper)
                improper = []
            yield child
        else:
            # Whitespace either fail the test or were removed earlier,
            # so there is no need to take special care with the definition
            # of "consecutive".
            improper.append(child)
    if improper:
        wrapper = wrapper_type.anonymous_from(box, children=[])
        # Apply the rules again on the new wrapper
        yield table_boxes_children(wrapper, improper)


def anonymous_table_boxes(box):
    """Remove and add boxes according to the table model.

    Take and return a ``Box`` object.

    See http://www.w3.org/TR/CSS21/tables.html#anonymous-boxes

    """
    if not isinstance(box, boxes.ParentBox):
        return box

    # Do recursion.
    children = map(anonymous_table_boxes, box.children)
    return table_boxes_children(box, children)


def table_boxes_children(box, children):
    """Internal implementation of anonymous_table_boxes()."""
    if isinstance(box, boxes.TableColumnBox):  # rule 1.1
        # Remove all children.
        children = []
    elif isinstance(box, boxes.TableColumnGroupBox):  # rule 1.2
        # Remove children other than table-column.
        children = [
            child for child in children
            if isinstance(child, boxes.TableColumnBox)
        ]
        # Rule XXX (not in the spec): column groups have at least
        # one column child.
        if not children:
            children = [boxes.TableColumnBox.anonymous_from(box, [])
                        for _i in xrange(box.span)]

    # rule 1.3
    if box.tabular_container and len(children) >= 2:
        # TODO: Maybe only remove text if internal is also
        #       a proper table descendant of box.
        # This is what the spec says, but maybe not what browsers do:
        # http://lists.w3.org/Archives/Public/www-style/2011Oct/0567

        # Last child
        internal, text = children[-2:]
        if (internal.internal_table_or_caption and is_whitespace(text)):
            children.pop()

        # First child
        if len(children) >= 2:
            text, internal = children[:2]
            if (internal.internal_table_or_caption and is_whitespace(text)):
                children.pop(0)

        # Children other than first and last that would be removed by
        # rule 1.3 are also removed by rule 1.4 below.

    children = [
        child
        for prev_child, child, next_child in zip(
            [None] + children[:-1],
            children,
            children[1:] + [None]
        )
        if not (
            # Ignore some whitespace: rule 1.4
            prev_child and prev_child.internal_table_or_caption and
            next_child and next_child.internal_table_or_caption and
            is_whitespace(child)
        )
    ]

    if isinstance(box, boxes.TableBox) or \
            isinstance(box, boxes.InlineTableBox):
        # Rule 2.1
        children = wrap_improper(box, children, boxes.TableRowBox,
            lambda child: child.proper_table_child)
    elif isinstance(box, boxes.TableRowGroupBox):
        # Rule 2.2
        children = wrap_improper(box, children, boxes.TableRowBox)

    if isinstance(box, boxes.TableRowBox):
        # Rule 2.3
        children = wrap_improper(box, children, boxes.TableCellBox)
    else:
        # Rule 3.1
        children = wrap_improper(box, children, boxes.TableRowBox,
            lambda child: not isinstance(child, boxes.TableCellBox))

    # Rule 3.2
    if isinstance(box, boxes.InlineBox):
        children = wrap_improper(box, children, boxes.InlineTableBox,
            lambda child: not child.proper_table_child)
    else:
        parent_type = type(box)
        children = wrap_improper(box, children, boxes.TableBox,
            lambda child:
                not child.proper_table_child or
                parent_type in child.proper_parents)


    if isinstance(box, boxes.TableBox):
        return wrap_table(box, children)
    else:
        return box.copy_with_children(children)


def wrap_table(box, children):
    """Take a table box and return it in its table wrapper box.

    Also re-order children and assign grid positions to each column an cell.

    http://www.w3.org/TR/CSS21/tables.html#model
    http://www.w3.org/TR/CSS21/tables.html#table-layout

    """
    # Group table children by type
    columns = []
    rows = []
    all_captions = []
    by_type = {
        boxes.TableColumnBox: columns,
        boxes.TableColumnGroupBox: columns,
        boxes.TableRowBox: rows,
        boxes.TableRowGroupBox: rows,
        boxes.TableCaptionBox: all_captions,
    }
    for child in children:
        by_type[type(child)].append(child)

    # Split top and bottom captions
    captions = {'top': [], 'bottom': []}
    for caption in all_captions:
        captions[caption.style.caption_side].append(caption)

    # Assign X positions on the grid to column boxes
    column_groups = list(wrap_improper(
        box, columns, boxes.TableColumnGroupBox))
    grid_x = 0
    for group in column_groups:
        group.grid_x = grid_x
        if group.children:
            for column in group.children:
                column.grid_x = grid_x
                grid_x += 1
            group.span = len(group.children)
        else:
            grid_x += group.span

    # Extract the optional header and footer groups.
    body_row_groups = []
    header = None
    footer = None
    for group in wrap_improper(box, rows, boxes.TableRowGroupBox):
        display = group.style.display
        if display == 'table-header-group' and header is None:
            group.header_group = True
            header = group
        elif display == 'table-footer-group' and footer is None:
            group.footer_group = True
            footer = group
        else:
            body_row_groups.append(group)

    row_groups = (
        ([header] if header is not None else []) +
        body_row_groups +
        ([footer] if footer is not None else []))

    # Assign a (x,y) position in the grid to each cell.
    # rowspan can not extend beyond a row group, so each row group
    # is independent.
    # http://www.w3.org/TR/CSS21/tables.html#table-layout
    # Column 0 is on the left if direction is ltr, right if rtl.
    # This algorithm does not change.
    for group in row_groups:
        # Indexes: row number in the group.
        # Values: set of cells already occupied by row-spanning cells.
        occupied_cells_by_row = [set() for row in group.children]
        for row in group.children:
            occupied_cells_in_this_row = occupied_cells_by_row.pop(0)
            # The list is now about rows after this one.
            grid_x = 0
            for cell in row.children:
                # Make sure that the first grid cell is free.
                while grid_x in occupied_cells_in_this_row:
                    grid_x += 1
                cell.grid_x = grid_x
                new_grid_x = grid_x + cell.colspan
                # http://www.w3.org/TR/html401/struct/tables.html#adef-rowspan
                if cell.rowspan != 1:
                    if cell.rowspan == 0:
                        # All rows until the end of the group
                        spanned_rows = occupied_cells_by_row
                        cell.rowspan = len(occupied_cells_by_row) + 1
                    else:
                        spanned_rows = occupied_cells_by_row[:cell.rowspan - 1]
                    spanned_columns = range(grid_x, new_grid_x)
                    for occupied_cells in spanned_rows:
                        occupied_cells.update(spanned_columns)
                grid_x = new_grid_x

    table = box.copy_with_children(row_groups)
    table.column_groups = tuple(column_groups)

#    table.body_row_groups = tuple(body_row_groups)
#    table.row_groups = tuple(row_groups)
#    table.header = header
#    table.footer = footer

    # TODO: re-enable this once we support inline-block layout.
    if False: # isinstance(box, boxes.InlineTableBox):
        # XXX disabled
        wrapper_type = boxes.InlineBlockBox
    else:
        wrapper_type = boxes.BlockBox

    wrapper = wrapper_type.anonymous_from(
        box, captions['top'] + [table] + captions['bottom'])
    wrapper.is_table_wrapper = True
    if not table.style.anonymous:
        # Non-inherited properties of the table element apply to one
        # of the wrapper and the table. The other get the initial value.
        for name in properties.TABLE_WRAPPER_BOX_PROPERTIES:
            wrapper.style[name] = table.style[name]
            table.style[name] = properties.INITIAL_VALUES[name]
    # else: non-inherited properties already have their initial values

    return wrapper


def process_whitespace(box):
    """First part of "The 'white-space' processing model".

    See http://www.w3.org/TR/CSS21/text.html#white-space-model

    """
    following_collapsible_space = False
    for child in box.descendants():
        if not isinstance(child, boxes.TextBox):
            if isinstance(child, boxes.AtomicInlineLevelBox):
                following_collapsible_space = False
            continue

        text = child.text
        if not text:
            continue

        # Normalize line feeds
        text = re.sub(u'\r\n?', u'\n', text)

        handling = child.style.white_space

        if handling in ('normal', 'nowrap', 'pre-line'):
            # \r characters were removed/converted earlier
            text = re.sub('[\t ]*\n[\t ]*', '\n', text)
        if handling in ('pre', 'pre-wrap'):
            # \xA0 is the non-breaking space
            text = text.replace(' ', u'\xA0')
            if handling == 'pre-wrap':
                # "a line break opportunity at the end of the sequence"
                # \u200B is the zero-width space, marks a line break
                # opportunity.
                text = re.sub(u'\xA0([^\xA0]|$)', u'\xA0\u200B\\1', text)
        elif handling in ('normal', 'nowrap'):
            # TODO: this should be language-specific
            # Could also replace with a zero width space character (U+200B),
            # or no character
            # CSS3: http://www.w3.org/TR/css3-text/#line-break-transform
            text = text.replace('\n', ' ')

        if handling in ('normal', 'nowrap', 'pre-line'):
            text = text.replace('\t', ' ')
            text = re.sub(' +', ' ', text)
            if following_collapsible_space and text.startswith(' '):
                text = text[1:]
            following_collapsible_space = text.endswith(' ')
        else:
            following_collapsible_space = False

        child.text = text
    return box


def inline_in_block(box):
    """Build the structure of lines inside blocks and return a new box tree.

    Consecutive inline-level boxes in a block container box are wrapped into a
    line box, itself wrapped into an anonymous block box.

    This line box will be broken into multiple lines later.

    This is the first case in
    http://www.w3.org/TR/CSS21/visuren.html#anonymous-block-level

    Eg.::

        BlockBox[
            TextBox['Some '],
            InlineBox[TextBox['text']],
            BlockBox[
                TextBox['More text'],
            ]
        ]

    is turned into::

        BlockBox[
            AnonymousBlockBox[
                LineBox[
                    TextBox['Some '],
                    InlineBox[TextBox['text']],
                ]
            ]
            BlockBox[
                LineBox[
                    TextBox['More text'],
                ]
            ]
        ]

    """
    if not isinstance(box, boxes.ParentBox):
        return box

    children = [inline_in_block(child) for child in box.children
                # Remove empty text boxes.
                # (They may have been emptied by process_whitespace().)
                if not (isinstance(child, boxes.TextBox) and not child.text)]

    if not isinstance(box, boxes.BlockContainerBox):
        return box.copy_with_children(children)

    new_line_children = []
    new_children = []
    for child_box in children:
        assert not isinstance(child_box, boxes.LineBox)
        if isinstance(child_box, boxes.InlineLevelBox):
            # Do not append white space at the start of a line:
            # It would be removed during layout.
            if new_line_children or not (
                    isinstance(child_box, boxes.TextBox) and
                    # Sequence of white-space was collapsed to a single
                    # space by process_whitespace().
                    child_box.text == ' ' and
                    child_box.style.white_space in (
                        'normal', 'nowrap', 'pre-line')):
                new_line_children.append(child_box)
        else:
            if new_line_children:
                # Inlines are consecutive no more: add this line box
                # and create a new one.
                line_box = boxes.LineBox.anonymous_from(box, new_line_children)
                anonymous = boxes.BlockBox.anonymous_from(box, [line_box])
                new_children.append(anonymous)
                new_line_children = []
            new_children.append(child_box)
    if new_line_children:
        # There were inlines at the end
        line_box = boxes.LineBox.anonymous_from(box, new_line_children)
        if new_children:
            anonymous = boxes.BlockBox.anonymous_from(box, [line_box])
            new_children.append(anonymous)
        else:
            # Only inline-level children: one line box
            new_children.append(line_box)

    return box.copy_with_children(new_children)


def block_in_inline(box):
    """Build the structure of blocks inside lines.

    Inline boxes containing block-level boxes will be broken in two
    boxes on each side on consecutive block-level boxes, each side wrapped
    in an anonymous block-level box.

    This is the second case in
    http://www.w3.org/TR/CSS21/visuren.html#anonymous-block-level

    Eg. if this is given::

        BlockBox[
            LineBox[
                InlineBox[
                    TextBox['Hello.'],
                ],
                InlineBox[
                    TextBox['Some '],
                    InlineBox[
                        TextBox['text']
                        BlockBox[LineBox[TextBox['More text']]],
                        BlockBox[LineBox[TextBox['More text again']]],
                    ],
                    BlockBox[LineBox[TextBox['And again.']]],
                ]
            ]
        ]

    this is returned::

        BlockBox[
            AnonymousBlockBox[
                LineBox[
                    InlineBox[
                        TextBox['Hello.'],
                    ],
                    InlineBox[
                        TextBox['Some '],
                        InlineBox[TextBox['text']],
                    ]
                ]
            ],
            BlockBox[LineBox[TextBox['More text']]],
            BlockBox[LineBox[TextBox['More text again']]],
            AnonymousBlockBox[
                LineBox[
                    InlineBox[
                    ]
                ]
            ],
            BlockBox[LineBox[TextBox['And again.']]],
            AnonymousBlockBox[
                LineBox[
                    InlineBox[
                    ]
                ]
            ],
        ]

    """
    if not isinstance(box, boxes.ParentBox):
        return box

    new_children = []
    changed = False

    for child in box.children:
        if isinstance(child, boxes.LineBox):
            assert len(box.children) == 1, ('Line boxes should have no '
                'siblings at this stage, got %r.' % box.children)
            stack = None
            while 1:
                new_line, block, stack = _inner_block_in_inline(child, stack)
                if block is None:
                    break
                anon = boxes.BlockBox.anonymous_from(box, [new_line])
                new_children.append(anon)
                new_children.append(block_in_inline(block))
                # Loop with the same child and the new stack.
            if new_children:
                # Some children were already added, this became a block
                # context.
                new_child = boxes.BlockBox.anonymous_from(box, [new_line])
            else:
                # Keep the single line box as-is, without anonymous blocks.
                new_child = new_line
        else:
            # Not in an inline formatting context.
            new_child = block_in_inline(child)

        if new_child is not child:
            changed = True
        new_children.append(new_child)

    if changed:
        return box.copy_with_children(new_children)
    else:
        return box


def _inner_block_in_inline(box, skip_stack=None):
    """Find a block-level box in an inline formatting context.

    If one is found, return ``(new_box, block_level_box, resume_at)``.
    ``new_box`` contains all of ``box`` content before the block-level box.
    ``resume_at`` can be passed as ``skip_stack`` in a new call to
    this function to resume the search just after the block-level box.

    If no block-level box is found after the position marked by
    ``skip_stack``, return ``(new_box, None, None)``

    """
    new_children = []
    block_level_box = None
    resume_at = None
    changed = False

    if skip_stack is None:
        skip = 0
    else:
        skip, skip_stack = skip_stack

    for index, child in box.enumerate_skip(skip):
        if isinstance(child, boxes.BlockLevelBox):
            assert skip_stack is None  # Should not skip here
            block_level_box = child
            index += 1  # Resume *after* the block
        else:
            if isinstance(child, boxes.InlineBox):
                recursion = _inner_block_in_inline(child, skip_stack)
                skip_stack = None
                new_child, block_level_box, resume_at = recursion
            else:
                assert skip_stack is None  # Should not skip here
                if isinstance(child, boxes.ParentBox):
                    # inline-block or inline-table.
                    new_child = block_in_inline(child)
                else:
                    # text or replaced box
                    new_child = child
                # block_level_box is still None.
            if new_child is not child:
                changed = True
            new_children.append(new_child)
        if block_level_box is not None:
            resume_at = (index, resume_at)
            box = box.copy_with_children(new_children)
            break
    else:
        if changed or skip:
            box = box.copy_with_children(new_children)

    return box, block_level_box, resume_at


def set_canvas_background(root_box):
    """
    Set a ``canvas_background`` attribute on the box for the root element,
    with style for the canvas background, taken from the root elememt
    or a <body> child of the root element.

    See http://www.w3.org/TR/CSS21/colors.html#background
    """
    chosen_box = root_box
    if (root_box.element_tag.lower() == 'html' and
            root_box.style.background_color.alpha == 0 and
            root_box.style.background_image == 'none'):
        for child in root_box.children:
            if child.element_tag.lower() == 'body':
                chosen_box = child
                break

    style = chosen_box.style
    root_box.canvas_background = style
    chosen_box.style = style.updated_copy(properties.BACKGROUND_INITIAL)
    return root_box


def set_viewport_overflow(root_box):
    """
    Set a ``viewport_overflow`` attribute on the box for the root element.

    Like backgrounds, ``overflow`` on the root element must be propagated
    to the viewport.

    See http://www.w3.org/TR/CSS21/visufx.html#overflow
    """
    chosen_box = root_box
    if (root_box.element_tag.lower() == 'html' and
            root_box.style.overflow == 'visible'):
        for child in root_box.children:
            if child.element_tag.lower() == 'body':
                chosen_box = child
                break

    root_box.viewport_overflow = chosen_box.style.overflow
    chosen_box.style = chosen_box.style.updated_copy({'overflow': 'visible'})
    return root_box
