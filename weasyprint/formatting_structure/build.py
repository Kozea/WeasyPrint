"""
    weasyprint.formatting_structure.build
    -------------------------------------

    Turn an element tree with associated CSS style (computed values)
    into a "before layout" formatting structure / box tree.

    This includes creating anonymous boxes and processing whitespace
    as necessary.

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import re
import unicodedata

import tinycss2.color3

from . import boxes, counters
from .. import html
from ..css import properties
from ..css.targets import TARGET_COLLECTOR, TARGET_STATE
from ..logger import LOGGER

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
    'flex': boxes.FlexBox,
    'inline-flex': boxes.InlineFlexBox,
}


def build_formatting_structure(element_tree, style_for, get_image_from_uri,
                               base_url):
    """Build a formatting structure (box tree) from an element tree."""

    LOGGER.info('Step 4.1 - Verifying collected targets')
    # BTW: this step is *not* required. Dont't think it speeds up things a lot
    # by tagging UNDEFINED targets in advance
    TARGET_COLLECTOR.verify_collection()
    LOGGER.info('Step 4.2 - Building basic boxes')

    box_list = element_to_box(
        element_tree, style_for, get_image_from_uri, base_url)
    if box_list:
        box, = box_list
    else:
        # No root element
        def root_style_for(element, pseudo_type=None):
            style = style_for(element, pseudo_type)
            if style:
                # TODO: we should check that the element has a parent instead.
                if element.tag == 'html':
                    style['display'] = 'block'
                else:
                    style['display'] = 'none'
            return style
        box, = element_to_box(
            element_tree, root_style_for, get_image_from_uri, base_url)

    TARGET_COLLECTOR.check_peding_targets()
    # state now: no more pending targeds in pseudo-element's content boxes

    box.is_for_root_element = True
    # If this is changed, maybe update weasy.layout.pages.make_margin_boxes()
    process_whitespace(box)
    box = anonymous_table_boxes(box)
    box = flex_boxes(box)
    box = inline_in_block(box)
    box = block_in_inline(box)
    box = set_viewport_overflow(box)
    return box


def make_box(element_tag, style, content, get_image_from_uri):
    return BOX_TYPE_FROM_DISPLAY[style['display']](
        element_tag, style, content)


def element_to_box(element, style_for, get_image_from_uri, base_url,
                   state=None):
    """Convert an element and its children into a box with children.

    Return a list of boxes. Most of the time the list will have one item but
    may have zero or more than one.

    Eg.::

        <p>Some <em>emphasised</em> text.</p>

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
    if not isinstance(element.tag, str):
        # We ignore comments and XML processing instructions.
        return []

    style = style_for(element)

    # TODO: should be the used value. When does the used value for `display`
    # differ from the computer value?
    display = style['display']
    if display == 'none':
        return []

    box = make_box(element.tag, style, [], get_image_from_uri)

    if state is None:
        # use a list to have a shared mutable object
        state = (
            # Shared mutable objects:
            [0],  # quote_depth: single integer
            {},  # counter_values: name -> stacked/scoped values
            [set()]  # counter_scopes: element tree depths -> counter names
        )
    _quote_depth, counter_values, counter_scopes = state

    update_counters(state, style)

    children = []
    if display == 'list-item':
        children.extend(add_box_marker(
            box, counter_values, get_image_from_uri))

    # If this element’s direct children create new scopes, the counter
    # names will be in this new list
    counter_scopes.append(set())

    box.first_letter_style = style_for(element, 'first-letter')
    box.first_line_style = style_for(element, 'first-line')

    children.extend(before_after_to_box(
        element, 'before', state, style_for, get_image_from_uri))

    # collect anchor's counter_values, maybe it's a target.
    # to get the spec-conform counter_valuse we must do it here,
    # after the ::before is parsed and befor the ::after is
    if style['anchor']:
        TARGET_COLLECTOR.store_target(style['anchor'], counter_values, box)

    text = element.text
    if text:
        children.append(boxes.TextBox.anonymous_from(box, text))

    for child_element in element:
        children.extend(element_to_box(
            child_element, style_for, get_image_from_uri, base_url, state))
        text = child_element.tail
        if text:
            text_box = boxes.TextBox.anonymous_from(box, text)
            if children and isinstance(children[-1], boxes.TextBox):
                children[-1].text += text_box.text
            else:
                children.append(text_box)
    children.extend(before_after_to_box(
        element, 'after', state, style_for, get_image_from_uri))

    # Scopes created by this element’s children stop here.
    for name in counter_scopes.pop():
        counter_values[name].pop()
        if not counter_values[name]:
            counter_values.pop(name)

    box.children = children
    # calculate string-set and bookmark-label
    set_content_lists(element, box, style, counter_values)

    # Specific handling for the element. (eg. replaced element)
    return html.handle_element(element, box, get_image_from_uri, base_url)


def before_after_to_box(element, pseudo_type, state, style_for,
                        get_image_from_uri):
    """Yield the box for ::before or ::after pseudo-element if there is one."""
    style = style_for(element, pseudo_type)
    if pseudo_type and style is None:
        # Pseudo-elements with no style at all do not get a style dict.
        # Their initial content property computes to 'none'.
        return

    # TODO: should be the used value. When does the used value for `display`
    # differ from the computer value?
    display = style['display']
    content = style['content']
    if 'none' in (display, content) or content == 'normal':
        return

    box = make_box(
        '%s::%s' % (element.tag, pseudo_type), style, [], get_image_from_uri)

    quote_depth, counter_values, _counter_scopes = state
    update_counters(state, style)

    # pseudo-elements can't be anchors, no need to call
    # TARGET_COLLECTOR.store_target(...)

    children = []
    if display == 'list-item':
        children.extend(add_box_marker(
            box, counter_values, get_image_from_uri))
    children.extend(content_to_boxes(
        style, box, quote_depth, counter_values, get_image_from_uri))

    # content_to_boxes detected an UNDEFINED target, discard the box
    if style['content'] == 'none':
        return

    box.children = children
    yield box


def compute_content_list(return_a_string,
                         content_list, parent_box, counter_values,
                         parse_again_func,
                         get_image_from_uri=None,
                         quote_depth=None, quote_style=None,
                         context=None, page=None):
    """
    Compute and return the string or the boxes corresponding
    to the content_list.

    :param return_a_string:
        True for string-set-string and bookmark-label,
        otherwise (content) a list of anonymous InlineBox(es) is returned
    :param parse_again_func:
        fnction to compute the content_list again
        when TARGET_COLLECTOR.lookup_target() detected a TARGET_STATE.PENDING

        build_formatting_structure calls
        TARGET_COLLECTOR.check_pending_targets
        after the first pass to do required reparsing
    """
    boxlist = []
    texts = []
    for type_, value in content_list:
        if type_ == 'STRING':
            texts.append(value)
        elif type_ == 'URI' and not return_a_string and \
                get_image_from_uri is not None:
            image = get_image_from_uri(value)
            if image is not None:
                text = ''.join(texts)
                if text:
                    boxlist.append(
                        boxes.TextBox.anonymous_from(parent_box, text))
                texts = []
                boxlist.append(
                    boxes.InlineReplacedBox.anonymous_from(parent_box, image))
        elif type_ == 'content' and return_a_string:
            added_text = TEXT_CONTENT_EXTRACTORS[value](parent_box)
            # Simulate the step of white space processing
            # (normally done during the layout)
            added_text = added_text.strip()
            texts.append(added_text)
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
        elif type_ == 'string' and context is not None and page is not None:
            # string() is only valid in @page context
            text = context.get_string_set_for(page, *value)
            texts.append(text)
        elif type_ == 'target-counter':
            target_name, counter_name, counter_style = value
            lookup_target = TARGET_COLLECTOR.lookup_target(
                target_name, parent_box, parse_again_func)
            if lookup_target.state == TARGET_STATE.UPTODATE:
                counter_value = lookup_target.target_counter_values.get(
                    counter_name, [0])[-1]
                texts.append(counters.format(counter_value, counter_style))
            else:
                texts = []
                break
        elif type_ == 'target-counters':
            target_name, counter_name, separator, counter_style = value
            lookup_target = TARGET_COLLECTOR.lookup_target(
                target_name, parent_box, parse_again_func)
            if lookup_target.state == TARGET_STATE.UPTODATE:
                target_counter_values = lookup_target.target_counter_values
                texts.append(separator.join(
                    counters.format(counter_value, counter_style)
                    for counter_value in target_counter_values.get(
                        counter_name, [0])
                ))
            else:
                texts = []
                break
        elif type_ == 'target-text':
            target_name, text_style = value
            lookup_target = TARGET_COLLECTOR.lookup_target(
                target_name, parent_box, parse_again_func)
            if lookup_target.state == TARGET_STATE.UPTODATE:
                target_box = lookup_target.target_box
                text = TEXT_CONTENT_EXTRACTORS[text_style](target_box)
                # Simulate the step of white space processing
                # (normally done during the layout)
                texts.append(text.strip())
            else:
                texts = []
                break
        elif type_ == 'QUOTE' and not return_a_string and \
                quote_depth is not None and quote_style is not None:
            is_open, insert = value
            if not is_open:
                quote_depth[0] = max(0, quote_depth[0] - 1)
            if insert:
                open_quotes, close_quotes = quote_style
                quotes = open_quotes if is_open else close_quotes
                texts.append(quotes[min(quote_depth[0], len(quotes) - 1)])
            if is_open:
                quote_depth[0] += 1
        else:
            # TODO: in previous versions an AssertionError was raised!
            pass
    text = ''.join(texts)
    if return_a_string:
        return text
    if text:
        boxlist.append(boxes.TextBox.anonymous_from(parent_box, text))
    return boxlist


def content_to_boxes(style, parent_box, quote_depth, counter_values,
                     get_image_from_uri, context=None, page=None):
    """Takes the value of a ``content`` property and returns boxes."""
    def parse_again():
        """
        closure to parse the parent_boxes children all again
        when TARGET_COLLECTOR.lookup_target() detected a TARGET_STATE.PENDING,
        Thx to closure no need to explicitly copy.deepcopy the whole stuff,
        """
        local_children = []
        if style['display'] == 'list-item':
            local_children.extend(add_box_marker(
                parent_box, counter_values, get_image_from_uri))
        local_children.extend(content_to_boxes(
            style, parent_box,
            quote_depth, counter_values,
            get_image_from_uri))
        parent_box.children = local_children

    # Can't use `yield`! Must `return` the boxes otherwise set_content_lists,
    # calling compute_content_list for `contents()`, will fail
    return compute_content_list(
        False,
        style['content'],
        parent_box, counter_values,
        parse_again,
        get_image_from_uri, quote_depth, style['quotes'],
        context, page)


def compute_string_set_string(box, string_name, content_list, counter_values):
    """For ``string-set`` property:
    Parses the content-list value of the string named `string_name`
    and append the resulting string to the boxes string_set
    """
    def parse_again():
        """
        closure to parse the string-set-string value all again
        when TARGET_COLLECTOR.lookup_target() detected a TARGET_STATE.PENDING
        """
        compute_string_set_string(
            box, string_name, content_list, counter_values)

    s = compute_content_list(
        True,
        content_list, box,
        counter_values,
        parse_again)
    if s:
        box.string_set.append((string_name, s))


def compute_bookmark_label(box, content_list, counter_values):
    """For ``bookmark-label`` property:
    Parses the content-list value and put it in the boxes .bookmark_label
    """
    def parse_again():
        compute_bookmark_label(
            box, content_list, counter_values)

    box.bookmark_label = compute_content_list(
        True,
        content_list, box, counter_values,
        parse_again)


def set_content_lists(element, box, style, counter_values):
    """Set the content-lists by strings.

    These content-lists are used in GCPM properties like ``string-set`` and
    ``bookmark-label``.
    """
    box.string_set = []
    if style['string_set'] != 'none':
        for i, (string_name, string_values) in enumerate(style['string_set']):
            compute_string_set_string(
                box, string_name, string_values, counter_values)
    if style['bookmark_label'] == 'none':
        box.bookmark_label = ''
    else:
        compute_bookmark_label(
            box, style['bookmark_label'], counter_values)


def update_counters(state, style):
    """Handle the ``counter-*`` properties."""
    _quote_depth, counter_values, counter_scopes = state
    sibling_scopes = counter_scopes[-1]

    for name, value in style['counter_reset']:
        if name in sibling_scopes:
            counter_values[name].pop()
        else:
            sibling_scopes.add(name)
        counter_values.setdefault(name, []).append(value)

    # XXX Disabled for now, only exists in Lists3’s editor’s draft.
#    for name, value in style['counter_set']:
#        values = counter_values.setdefault(name, [])
#        if not values:
#            assert name not in sibling_scopes
#            sibling_scopes.add(name)
#            values.append(0)
#        values[-1] = value

    counter_increment = style['counter_increment']
    if counter_increment == 'auto':
        # 'auto' is the initial value but is not valid in stylesheet:
        # there was no counter-increment declaration for this element.
        # (Or the winning value was 'initial'.)
        # http://dev.w3.org/csswg/css3-lists/#declaring-a-list-item
        if style['display'] == 'list-item':
            counter_increment = [('list-item', 1)]
        else:
            counter_increment = []
    for name, value in counter_increment:
        values = counter_values.setdefault(name, [])
        if not values:
            assert name not in sibling_scopes
            sibling_scopes.add(name)
            values.append(0)
        values[-1] += value


def add_box_marker(box, counter_values, get_image_from_uri):
    """Add a list marker to boxes for elements with ``display: list-item``,
    and yield children to add a the start of the box.

    See http://www.w3.org/TR/CSS21/generate.html#lists

    """
    style = box.style
    image_type, image = style['list_style_image']
    if image_type == 'url':
        # surface may be None here too, in case the image is not available.
        image = get_image_from_uri(image)

    if image is None:
        type_ = style['list_style_type']
        if type_ == 'none':
            return
        counter_value = counter_values.get('list-item', [0])[-1]
        marker_text = counters.format_list_marker(counter_value, type_)
        marker_box = boxes.TextBox.anonymous_from(box, marker_text)
    else:
        marker_box = boxes.InlineReplacedBox.anonymous_from(box, image)
        marker_box.is_list_marker = True
    marker_box.element_tag += '::marker'

    position = style['list_style_position']
    if position == 'inside':
        yield marker_box
    elif position == 'outside':
        box.outside_list_marker = marker_box


def is_whitespace(box, _has_non_whitespace=re.compile('\S').search):
    """Return True if ``box`` is a TextBox with only whitespace."""
    return isinstance(box, boxes.TextBox) and not _has_non_whitespace(box.text)


def wrap_improper(box, children, wrapper_type, test=None):
    """
    Wrap consecutive children that do not pass ``test`` in a box of type
    ``wrapper_type``.

    ``test`` defaults to children being of the same type as ``wrapper_type``.

    """
    if test is None:
        def test(child):
            return isinstance(child, wrapper_type)
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
            if isinstance(box, boxes.FlexContainerBox):
                # The display value of a flex item must be "blockified", see
                # https://www.w3.org/TR/css-flexbox-1/#flex-items
                # TODO: These blocks are currently ignored, we should
                # "blockify" them and their children.
                pass
            else:
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
    children = [anonymous_table_boxes(child) for child in box.children]
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
                        for _i in range(box.span)]

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

    if isinstance(box, boxes.TableBox):
        # Rule 2.1
        children = wrap_improper(
            box, children, boxes.TableRowBox,
            lambda child: child.proper_table_child)
    elif isinstance(box, boxes.TableRowGroupBox):
        # Rule 2.2
        children = wrap_improper(box, children, boxes.TableRowBox)

    if isinstance(box, boxes.TableRowBox):
        # Rule 2.3
        children = wrap_improper(box, children, boxes.TableCellBox)
    else:
        # Rule 3.1
        children = wrap_improper(
            box, children, boxes.TableRowBox,
            lambda child: not isinstance(child, boxes.TableCellBox))

    # Rule 3.2
    if isinstance(box, boxes.InlineBox):
        children = wrap_improper(
            box, children, boxes.InlineTableBox,
            lambda child: not child.proper_table_child)
    else:
        parent_type = type(box)
        children = wrap_improper(
            box, children, boxes.TableBox,
            lambda child: (not child.proper_table_child or
                           parent_type in child.proper_parents))

    if isinstance(box, boxes.TableBox):
        return wrap_table(box, children)
    else:
        box.children = list(children)
        return box


def wrap_table(box, children):
    """Take a table box and return it in its table wrapper box.

    Also re-order children and assign grid positions to each column and cell.

    Because of colspan/rowspan works, grid_y is implicitly the index of a row,
    but grid_x is an explicit attribute on cells, columns and column group.

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
        captions[caption.style['caption_side']].append(caption)

    # Assign X positions on the grid to column boxes
    column_groups = list(wrap_improper(
        box, columns, boxes.TableColumnGroupBox))
    grid_x = 0
    for group in column_groups:
        group.grid_x = grid_x
        if group.children:
            for column in group.children:
                # There's no need to take care of group's span, as "span=x"
                # already generates x TableColumnBox children
                column.grid_x = grid_x
                grid_x += 1
            group.span = len(group.children)
        else:
            grid_x += group.span
    grid_width = grid_x

    row_groups = wrap_improper(box, rows, boxes.TableRowGroupBox)
    # Extract the optional header and footer groups.
    body_row_groups = []
    header = None
    footer = None
    for group in row_groups:
        display = group.style['display']
        if display == 'table-header-group' and header is None:
            group.is_header = True
            header = group
        elif display == 'table-footer-group' and footer is None:
            group.is_footer = True
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
    grid_height = 0
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
                    max_rowspan = len(occupied_cells_by_row) + 1
                    if cell.rowspan == 0:
                        # All rows until the end of the group
                        spanned_rows = occupied_cells_by_row
                        cell.rowspan = max_rowspan
                    else:
                        cell.rowspan = min(cell.rowspan, max_rowspan)
                        spanned_rows = occupied_cells_by_row[:cell.rowspan - 1]
                    spanned_columns = range(grid_x, new_grid_x)
                    for occupied_cells in spanned_rows:
                        occupied_cells.update(spanned_columns)
                grid_x = new_grid_x
                grid_width = max(grid_width, grid_x)
        grid_height += len(group.children)

    table = box.copy_with_children(row_groups)
    table.column_groups = tuple(column_groups)
    if table.style['border_collapse'] == 'collapse':
        table.collapsed_border_grid = collapse_table_borders(
            table, grid_width, grid_height)

    if isinstance(box, boxes.InlineTableBox):
        wrapper_type = boxes.InlineBlockBox
    else:
        wrapper_type = boxes.BlockBox

    wrapper = wrapper_type.anonymous_from(
        box, captions['top'] + [table] + captions['bottom'])
    wrapper.style = wrapper.style.copy()
    wrapper.is_table_wrapper = True
    # Non-inherited properties of the table element apply to one
    # of the wrapper and the table. The other get the initial value.
    # TODO: put this in a method of the table object
    for name in properties.TABLE_WRAPPER_BOX_PROPERTIES:
        wrapper.style[name] = table.style[name]
        table.style[name] = properties.INITIAL_VALUES[name]

    return wrapper


TRANSPARENT = tinycss2.color3.parse_color('transparent')


def collapse_table_borders(table, grid_width, grid_height):
    """Resolve border conflicts for a table in the collapsing border model.

    Take a :class:`TableBox`; set appropriate border widths on the table,
    column group, column, row group, row, and cell boxes; and return
    a data structure for the resolved collapsed border grid.

    """
    if not (grid_width and grid_height):
        # Don’t bother with empty tables
        return [], []

    style_scores = dict((v, i) for i, v in enumerate(reversed([
        'hidden', 'double', 'solid', 'dashed', 'dotted', 'ridge',
        'outset', 'groove', 'inset', 'none'])))
    style_map = {'inset': 'ridge', 'outset': 'groove'}
    transparent = TRANSPARENT
    weak_null_border = (
        (0, 0, style_scores['none']), ('none', 0, transparent))
    vertical_borders = [[weak_null_border for x in range(grid_width + 1)]
                        for y in range(grid_height)]
    horizontal_borders = [[weak_null_border for x in range(grid_width)]
                          for y in range(grid_height + 1)]

    def set_one_border(border_grid, box_style, side, grid_x, grid_y):
        from ..draw import get_color

        style = box_style['border_%s_style' % side]
        width = box_style['border_%s_width' % side]
        color = get_color(box_style, 'border_%s_color' % side)

        # http://www.w3.org/TR/CSS21/tables.html#border-conflict-resolution
        score = ((1 if style == 'hidden' else 0), width, style_scores[style])

        style = style_map.get(style, style)
        previous_score, _ = border_grid[grid_y][grid_x]
        # Strict < so that the earlier call wins in case of a tie.
        if previous_score < score:
            border_grid[grid_y][grid_x] = (score, (style, width, color))

    def set_borders(box, x, y, w, h):
        style = box.style
        for yy in range(y, y + h):
            set_one_border(vertical_borders, style, 'left', x, yy)
            set_one_border(vertical_borders, style, 'right', x + w, yy)
        for xx in range(x, x + w):
            set_one_border(horizontal_borders, style, 'top', xx, y)
            set_one_border(horizontal_borders, style, 'bottom', xx, y + h)

    # The order is important here:
    # "A style set on a cell wins over one on a row, which wins over a
    #  row group, column, column group and, lastly, table"
    # See http://www.w3.org/TR/CSS21/tables.html#border-conflict-resolution
    strong_null_border = (
        (1, 0, style_scores['hidden']), ('hidden', 0, transparent))
    grid_y = 0
    for row_group in table.children:
        for row in row_group.children:
            for cell in row.children:
                # No border inside of a cell with rowspan or colspan
                for xx in range(cell.grid_x + 1, cell.grid_x + cell.colspan):
                    for yy in range(grid_y, grid_y + cell.rowspan):
                        vertical_borders[yy][xx] = strong_null_border
                for xx in range(cell.grid_x, cell.grid_x + cell.colspan):
                    for yy in range(grid_y + 1, grid_y + cell.rowspan):
                        horizontal_borders[yy][xx] = strong_null_border
                # The cell’s own borders
                set_borders(cell, x=cell.grid_x, y=grid_y,
                            w=cell.colspan, h=cell.rowspan)
            grid_y += 1

    grid_y = 0
    for row_group in table.children:
        for row in row_group.children:
            set_borders(row, x=0, y=grid_y, w=grid_width, h=1)
            grid_y += 1

    grid_y = 0
    for row_group in table.children:
        rowspan = len(row_group.children)
        set_borders(row_group, x=0, y=grid_y, w=grid_width, h=rowspan)
        grid_y += rowspan

    for column_group in table.column_groups:
        for column in column_group.children:
            set_borders(column, x=column.grid_x, y=0, w=1, h=grid_height)

    for column_group in table.column_groups:
        set_borders(column_group, x=column_group.grid_x, y=0,
                    w=column_group.span, h=grid_height)

    set_borders(table, x=0, y=0, w=grid_width, h=grid_height)

    # Now that all conflicts are resolved, set transparent borders of
    # the correct widths on each box. The actual border grid will be
    # painted separately.
    def set_transparent_border(box, side, twice_width):
        box.style['border_%s_style' % side] = 'solid',
        box.style['border_%s_width' % side] = twice_width / 2
        box.style['border_%s_color' % side] = transparent

    def remove_borders(box):
        set_transparent_border(box, 'top', 0)
        set_transparent_border(box, 'right', 0)
        set_transparent_border(box, 'bottom', 0)
        set_transparent_border(box, 'left', 0)

    def max_vertical_width(x, y, h):
        return max(
            width for grid_row in vertical_borders[y:y + h]
            for _, (_, width, _) in [grid_row[x]])

    def max_horizontal_width(x, y, w):
        return max(
            width for _, (_, width, _) in horizontal_borders[y][x:x + w])

    grid_y = 0
    for row_group in table.children:
        remove_borders(row_group)
        for row in row_group.children:
            remove_borders(row)
            for cell in row.children:
                set_transparent_border(cell, 'top', max_horizontal_width(
                    x=cell.grid_x, y=grid_y, w=cell.colspan))
                set_transparent_border(cell, 'bottom', max_horizontal_width(
                    x=cell.grid_x, y=grid_y + cell.rowspan, w=cell.colspan))
                set_transparent_border(cell, 'left', max_vertical_width(
                    x=cell.grid_x, y=grid_y, h=cell.rowspan))
                set_transparent_border(cell, 'right', max_vertical_width(
                    x=cell.grid_x + cell.colspan, y=grid_y, h=cell.rowspan))
            grid_y += 1

    for column_group in table.column_groups:
        remove_borders(column_group)
        for column in column_group.children:
            remove_borders(column)

    set_transparent_border(table, 'top', max_horizontal_width(
        x=0, y=0, w=grid_width))
    set_transparent_border(table, 'bottom', max_horizontal_width(
        x=0, y=grid_height, w=grid_width))
    # "UAs must compute an initial left and right border width for the table
    #  by examining the first and last cells in the first row of the table."
    # http://www.w3.org/TR/CSS21/tables.html#collapsing-borders
    # ... so h=1, not grid_height:
    set_transparent_border(table, 'left', max_vertical_width(
        x=0, y=0, h=1))
    set_transparent_border(table, 'right', max_vertical_width(
        x=grid_width, y=0, h=1))

    return vertical_borders, horizontal_borders


def flex_boxes(box):
    """Remove and add boxes according to the flex model.

    Take and return a ``Box`` object.

    See http://www.w3.org/TR/css-flexbox-1/#flex-items

    """
    if not isinstance(box, boxes.ParentBox):
        return box

    # Do recursion.
    children = [flex_boxes(child) for child in box.children]
    box.children = flex_children(box, children)
    return box


def flex_children(box, children):
    if isinstance(box, boxes.FlexContainerBox):
        flex_children = []
        for child in children:
            if not child.is_absolutely_positioned():
                child.is_flex_item = True
            if isinstance(child, boxes.TextBox) and not child.text.strip(' '):
                # TODO: ignore texts only containing "characters that can be
                # affected by the white-space property"
                # https://www.w3.org/TR/css-flexbox-1/#flex-items
                continue
            if isinstance(child, boxes.InlineLevelBox):
                # TODO: Only create block boxes for text runs, not for other
                # inline level boxes. This is false but currently needed
                # because block_level_width and block_level_layout are called
                # in layout.flex.
                if isinstance(child, boxes.ParentBox):
                    anonymous = boxes.BlockBox.anonymous_from(
                        box, child.children)
                    anonymous.style = child.style
                else:
                    anonymous = boxes.BlockBox.anonymous_from(box, [child])
                anonymous.is_flex_item = True
                flex_children.append(anonymous)
            else:
                flex_children.append(child)
        return flex_children
    else:
        return children


def process_whitespace(box, following_collapsible_space=False):
    """First part of "The 'white-space' processing model".

    See http://www.w3.org/TR/CSS21/text.html#white-space-model
    http://dev.w3.org/csswg/css3-text/#white-space-rules

    """
    if isinstance(box, boxes.TextBox):
        text = box.text
        if not text:
            return following_collapsible_space

        # Normalize line feeds
        text = re.sub('\r\n?', '\n', text)

        new_line_collapse = box.style['white_space'] in ('normal', 'nowrap')
        space_collapse = box.style['white_space'] in (
            'normal', 'nowrap', 'pre-line')

        if space_collapse:
            # \r characters were removed/converted earlier
            text = re.sub('[\t ]*\n[\t ]*', '\n', text)

        if new_line_collapse:
            # TODO: this should be language-specific
            # Could also replace with a zero width space character (U+200B),
            # or no character
            # CSS3: http://www.w3.org/TR/css3-text/#line-break-transform
            text = text.replace('\n', ' ')

        if space_collapse:
            text = text.replace('\t', ' ')
            text = re.sub(' +', ' ', text)
            previous_text = text
            if following_collapsible_space and text.startswith(' '):
                text = text[1:]
                box.leading_collapsible_space = True
            following_collapsible_space = previous_text.endswith(' ')
        else:
            following_collapsible_space = False

        box.text = text
        return following_collapsible_space

    if isinstance(box, boxes.ParentBox):
        for child in box.children:
            if isinstance(child, (boxes.TextBox, boxes.InlineBox)):
                following_collapsible_space = process_whitespace(
                    child, following_collapsible_space)
            else:
                process_whitespace(child)
                if child.is_in_normal_flow():
                    following_collapsible_space = False

    return following_collapsible_space


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

    box_children = list(box.children)

    if box_children and box.leading_collapsible_space is False:
        box.leading_collapsible_space = (
            box_children[0].leading_collapsible_space)

    children = []
    trailing_collapsible_space = False
    for child in box_children:
        # Keep track of removed collapsing spaces for wrap opportunities, and
        # remove empty text boxes.
        # (They may have been emptied by process_whitespace().)

        if trailing_collapsible_space:
            child.leading_collapsible_space = True

        if isinstance(child, boxes.TextBox) and not child.text:
            trailing_collapsible_space = child.leading_collapsible_space
        else:
            trailing_collapsible_space = False
            children.append(inline_in_block(child))

    if box.trailing_collapsible_space is False:
        box.trailing_collapsible_space = trailing_collapsible_space

    if not isinstance(box, boxes.BlockContainerBox):
        box.children = children
        return box

    new_line_children = []
    new_children = []
    for child_box in children:
        assert not isinstance(child_box, boxes.LineBox)
        if new_line_children and child_box.is_absolutely_positioned():
            new_line_children.append(child_box)
        elif isinstance(child_box, boxes.InlineLevelBox) or (
                new_line_children and child_box.is_floated()):
            # Do not append white space at the start of a line:
            # It would be removed during layout.
            if new_line_children or not (
                    isinstance(child_box, boxes.TextBox) and
                    # Sequence of white-space was collapsed to a single
                    # space by process_whitespace().
                    child_box.text == ' ' and
                    child_box.style['white_space'] in (
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

    box.children = new_children
    return box


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
            assert len(box.children) == 1, (
                'Line boxes should have no '
                'siblings at this stage, got %r.' % box.children)
            stack = None
            while 1:
                new_line, block, stack = _inner_block_in_inline(
                    child, skip_stack=stack)
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
        box.children = new_children
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

    is_start = skip_stack is None
    if is_start:
        skip = 0
    else:
        skip, skip_stack = skip_stack

    for index, child in box.enumerate_skip(skip):
        if isinstance(child, boxes.BlockLevelBox) and \
                child.is_in_normal_flow():
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
                new_child = block_in_inline(child)
                # block_level_box is still None.
            if new_child is not child:
                changed = True
            new_children.append(new_child)
        if block_level_box is not None:
            resume_at = (index, resume_at)
            box = box.copy_with_children(
                new_children, is_start=is_start, is_end=False)
            break
    else:
        if changed or skip:
            box = box.copy_with_children(
                new_children, is_start=is_start, is_end=True)

    return box, block_level_box, resume_at


def set_viewport_overflow(root_box):
    """
    Set a ``viewport_overflow`` attribute on the box for the root element.

    Like backgrounds, ``overflow`` on the root element must be propagated
    to the viewport.

    See http://www.w3.org/TR/CSS21/visufx.html#overflow
    """
    chosen_box = root_box
    if (root_box.element_tag.lower() == 'html' and
            root_box.style['overflow'] == 'visible'):
        for child in root_box.children:
            if child.element_tag.lower() == 'body':
                chosen_box = child
                break

    root_box.viewport_overflow = chosen_box.style['overflow']
    chosen_box.style['overflow'] = 'visible'
    return root_box


def box_text(box):
    if isinstance(box, boxes.TextBox):
        return box.text
    elif isinstance(box, boxes.ParentBox):
        return ''.join(
            child.text for child in box.descendants()
            if not child.element_tag.endswith('::before') and
            not child.element_tag.endswith('::after') and
            isinstance(child, boxes.TextBox))
    else:
        return ''


def box_text_first_letter(box):
    # TODO: use the same code as in inlines.first_letter_to_box
    character_found = False
    first_letter = ''
    text = box_text(box)
    while text:
        next_letter = text[0]
        category = unicodedata.category(next_letter)
        if category not in ('Ps', 'Pe', 'Pi', 'Pf', 'Po'):
            if character_found:
                break
            character_found = True
        first_letter += next_letter
        text = text[1:]
    return first_letter


def box_text_before(box):
    if isinstance(box, boxes.ParentBox):
        return ''.join(
            box_text(child) for child in box.descendants()
            if child.element_tag.endswith('::before') and
            not isinstance(child, boxes.ParentBox))
    else:
        return ''


def box_text_after(box):
    if isinstance(box, boxes.ParentBox):
        return ''.join(
            box_text(child) for child in box.descendants()
            if child.element_tag.endswith('::after') and
            not isinstance(child, boxes.ParentBox))
    else:
        return ''


TEXT_CONTENT_EXTRACTORS = {
    'text': box_text,
    'before': box_text_before,
    'after': box_text_after,
    'first-letter': box_text_first_letter}
