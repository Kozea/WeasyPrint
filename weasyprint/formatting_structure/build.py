"""
    weasyprint.formatting_structure.build
    -------------------------------------

    Turn an element tree with associated CSS style (computed values)
    into a "before layout" formatting structure / box tree.

    This includes creating anonymous boxes and processing whitespace
    as necessary.

"""

import copy
import re
import unicodedata

import tinycss2.color3

from .. import html
from ..css import computed_values, properties
from ..logger import LOGGER
from . import boxes

# Maps values of the ``display`` CSS property to box types.
BOX_TYPE_FROM_DISPLAY = {
    ('block', 'flow'): boxes.BlockBox,
    ('inline', 'flow'): boxes.InlineBox,

    ('block', 'flow-root'): boxes.BlockBox,
    ('inline', 'flow-root'): boxes.InlineBlockBox,

    ('block', 'table'): boxes.TableBox,
    ('inline', 'table'): boxes.InlineTableBox,

    ('block', 'flex'): boxes.FlexBox,
    ('inline', 'flex'): boxes.InlineFlexBox,

    ('table-row',): boxes.TableRowBox,
    ('table-row-group',): boxes.TableRowGroupBox,
    ('table-header-group',): boxes.TableRowGroupBox,
    ('table-footer-group',): boxes.TableRowGroupBox,
    ('table-column',): boxes.TableColumnBox,
    ('table-column-group',): boxes.TableColumnGroupBox,
    ('table-cell',): boxes.TableCellBox,
    ('table-caption',): boxes.TableCaptionBox,
}

# http://stackoverflow.com/questions/16317534/
ASCII_TO_WIDE = {i: chr(i + 0xfee0) for i in range(0x21, 0x7f)}
ASCII_TO_WIDE.update({0x20: '\u3000', 0x2D: '\u2212'})


def create_anonymous_boxes(box):
    """Create anonymous boxes in box descendants according to layout rules."""
    box = anonymous_table_boxes(box)
    box = flex_boxes(box)
    box = inline_in_block(box)
    box = block_in_inline(box)
    return box


def build_formatting_structure(element_tree, style_for, get_image_from_uri,
                               base_url, target_collector, counter_style,
                               footnotes):
    """Build a formatting structure (box tree) from an element tree."""
    box_list = element_to_box(
        element_tree, style_for, get_image_from_uri, base_url,
        target_collector, counter_style, footnotes)
    if box_list:
        box, = box_list
    else:
        # No root element
        def root_style_for(element, pseudo_type=None):
            style = style_for(element, pseudo_type)
            if style is not None:
                if element == element_tree:
                    style['display'] = ('block', 'flow')
                else:
                    style['display'] = ('none',)
            return style
        box, = element_to_box(
            element_tree, root_style_for, get_image_from_uri, base_url,
            target_collector, counter_style, footnotes)

    target_collector.check_pending_targets()

    box.is_for_root_element = True
    # If this is changed, maybe update weasy.layout.page.make_margin_boxes()
    box = create_anonymous_boxes(box)
    box = set_viewport_overflow(box)
    return box


def make_box(element_tag, style, content, element):
    box = BOX_TYPE_FROM_DISPLAY[style['display'][:2]](
        element_tag, style, element, content)
    return box


def element_to_box(element, style_for, get_image_from_uri, base_url,
                   target_collector, counter_style, footnotes, state=None):
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
    if display == ('none',):
        return []

    if style['float'] == 'footnote':
        if style['footnote_display'] == 'block':
            style['display'] = ('block', 'flow')
        else:
            # TODO: handle compact footnotes
            style['display'] = ('inline', 'flow')

    box = make_box(element.tag, style, [], element)

    if state is None:
        # use a list to have a shared mutable object
        state = (
            # Shared mutable objects:
            [0],  # quote_depth: single integer
            # TODO: define the footnote counter where it can be updated by page
            {'footnote': [0]},  # counter_values: name -> stacked/scoped values
            [{'footnote'}]  # counter_scopes: element depths -> counter names
        )
    quote_depth, counter_values, counter_scopes = state

    update_counters(state, style)

    children = []

    # If this element’s direct children create new scopes, the counter
    # names will be in this new list
    counter_scopes.append(set())

    box.first_letter_style = style_for(element, 'first-letter')
    box.first_line_style = style_for(element, 'first-line')

    marker_boxes = []
    if 'list-item' in style['display']:
        marker_boxes = list(marker_to_box(
            element, state, style, style_for, get_image_from_uri,
            target_collector, counter_style))
        children.extend(marker_boxes)

    children.extend(before_after_to_box(
        element, 'before', state, style_for, get_image_from_uri,
        target_collector, counter_style))

    # collect anchor's counter_values, maybe it's a target.
    # to get the spec-conform counter_values we must do it here,
    # after the ::before is parsed and before the ::after is
    if style['anchor']:
        target_collector.store_target(style['anchor'], counter_values, box)

    text = element.text
    if text:
        children.append(boxes.TextBox.anonymous_from(box, text))

    for child_element in element:
        child_boxes = element_to_box(
            child_element, style_for, get_image_from_uri, base_url,
            target_collector, counter_style, footnotes, state)

        if child_boxes and child_boxes[0].style['float'] == 'footnote':
            footnote = child_boxes[0]
            footnote.style['float'] = 'none'
            footnotes.append(footnote)
            call_style = style_for(element, 'footnote-call')
            footnote_call = make_box(
                f'{element.tag}::footnote-call', call_style, [], element)
            footnote_call.children = content_to_boxes(
                call_style, footnote_call, quote_depth, counter_values,
                get_image_from_uri, target_collector, counter_style)
            footnote_call.footnote = footnote
            child_boxes = [footnote_call]

        children.extend(child_boxes)
        text = child_element.tail
        if text:
            text_box = boxes.TextBox.anonymous_from(box, text)
            if children and isinstance(children[-1], boxes.TextBox):
                children[-1].text += text_box.text
            else:
                children.append(text_box)

    children.extend(before_after_to_box(
        element, 'after', state, style_for, get_image_from_uri,
        target_collector, counter_style))

    # Scopes created by this element’s children stop here.
    for name in counter_scopes.pop():
        counter_values[name].pop()
        if not counter_values[name]:
            counter_values.pop(name)

    box.children = children
    process_whitespace(box)
    set_content_lists(
        element, box, style, counter_values, target_collector, counter_style)
    process_text_transform(box)

    if marker_boxes and len(box.children) == 1:
        # See https://www.w3.org/TR/css-lists-3/#list-style-position-outside
        #
        # "The size or contents of the marker box may affect the height of the
        #  principal block box and/or the height of its first line box, and in
        #  some cases may cause the creation of a new line box; this
        #  interaction is also not defined."
        #
        # We decide here to add a zero-width space to have a minimum
        # height. Adding text boxes is not the best idea, but it's not a good
        # moment to add an empty line box, and the specification lets us do
        # almost what we want, so…
        if style['list_style_position'] == 'outside':
            box.children.append(boxes.TextBox.anonymous_from(box, '​'))

    if style['float'] == 'footnote':
        counter_values['footnote'][-1] += 1
        marker_style = style_for(element, 'footnote-marker')
        marker = make_box(
            f'{element.tag}::footnote-marker', marker_style, [], element)
        marker.children = content_to_boxes(
            marker_style, box, quote_depth, counter_values, get_image_from_uri,
            target_collector, counter_style)
        box.children.insert(0, marker)

    # Specific handling for the element. (eg. replaced element)
    return html.handle_element(element, box, get_image_from_uri, base_url)


def before_after_to_box(element, pseudo_type, state, style_for,
                        get_image_from_uri, target_collector, counter_style):
    """Return the boxes for ::before or ::after pseudo-element."""
    style = style_for(element, pseudo_type)
    if pseudo_type and style is None:
        # Pseudo-elements with no style at all do not get a style dict.
        # Their initial content property computes to 'none'.
        return []

    # TODO: should be the computed value. When does the used value for
    # `display` differ from the computer value? It's at least wrong for
    # `content` where 'normal' computes as 'inhibit' for pseudo elements.
    display = style['display']
    if display == ('none',):
        return []
    content = style['content']
    if content in ('normal', 'inhibit', 'none'):
        return []
    box = make_box(f'{element.tag}::{pseudo_type}', style, [], element)

    quote_depth, counter_values, _counter_scopes = state
    update_counters(state, style)

    children = []

    if 'list-item' in display:
        marker_boxes = list(marker_to_box(
            element, state, style, style_for, get_image_from_uri,
            target_collector, counter_style))
        children.extend(marker_boxes)

    children.extend(content_to_boxes(
        style, box, quote_depth, counter_values, get_image_from_uri,
        target_collector, counter_style))

    box.children = children

    # calculate the bookmark-label
    if style['bookmark_label'] == 'none':
        box.bookmark_label = ''
    else:
        _quote_depth, counter_values, _counter_scopes = state
        compute_bookmark_label(
            element, box, style['bookmark_label'], counter_values,
            target_collector, counter_style)
    return [box]


def marker_to_box(element, state, parent_style, style_for, get_image_from_uri,
                  target_collector, counter_style):
    """Yield the box for ::marker pseudo-element if there is one.

    https://drafts.csswg.org/css-lists-3/#marker-pseudo

    """
    style = style_for(element, 'marker')

    children = []

    # TODO: should be the computed value. When does the used value for
    # `display` differ from the computer value? It's at least wrong for
    # `content` where 'normal' computes as 'inhibit' for pseudo elements.
    quote_depth, counter_values, _counter_scopes = state

    box = make_box(f'{element.tag}::marker', style, children, element)

    if style['display'] == ('none',):
        return

    image_type, image = style['list_style_image']

    if style['content'] not in ('normal', 'inhibit'):
        children.extend(content_to_boxes(
            style, box, quote_depth, counter_values, get_image_from_uri,
            target_collector, counter_style))

    else:
        if image_type == 'url':
            # image may be None here too, in case the image is not available.
            image = get_image_from_uri(url=image)
            if image is not None:
                box = boxes.InlineReplacedBox.anonymous_from(box, image)
                children.append(box)

        if not children and style['list_style_type'] != 'none':
            counter_value = counter_values.get('list-item', [0])[-1]
            counter_type = style['list_style_type']
            # TODO: rtl numbered list has the dot on the left
            marker_text = counter_style.render_marker(
                counter_type, counter_value)
            box = boxes.TextBox.anonymous_from(box, marker_text)
            box.style['white_space'] = 'pre-wrap'
            children.append(box)

    if not children:
        return

    if parent_style['list_style_position'] == 'outside':
        marker_box = boxes.BlockBox.anonymous_from(box, children)
        # We can safely edit everything that can't be changed by user style
        # See https://drafts.csswg.org/css-pseudo-4/#marker-pseudo
        marker_box.style['position'] = 'absolute'
        if parent_style['direction'] == 'ltr':
            translate_x = properties.Dimension(-100, '%')
        else:
            translate_x = properties.Dimension(100, '%')
        translate_y = computed_values.ZERO_PIXELS
        marker_box.style['transform'] = (
            ('translate', (translate_x, translate_y)),)
    else:
        marker_box = boxes.InlineBox.anonymous_from(box, children)
    yield marker_box


def _collect_missing_counter(counter_name, counter_values, missing_counters):
    """Collect missing counters."""
    if counter_name not in list(counter_values) + missing_counters:
        missing_counters.append(counter_name)


def _collect_missing_target_counter(counter_name, lookup_counter_values,
                                    anchor_name, missing_target_counters):
    """Collect missing target counters.

    The corresponding TargetLookupItem caches the target's page based
    counter values during pagination.

    """
    if counter_name not in lookup_counter_values:
        missing_counters = missing_target_counters.setdefault(anchor_name, [])
        if counter_name not in missing_counters:
            missing_counters.append(counter_name)


def compute_content_list(content_list, parent_box, counter_values, css_token,
                         parse_again, target_collector, counter_style,
                         get_image_from_uri=None, quote_depth=None,
                         quote_style=None, context=None, page=None,
                         element=None):
    """Compute and return the boxes corresponding to the ``content_list``.

    ``parse_again`` is called to compute the ``content_list`` again when
    ``target_collector.lookup_target()`` detected a pending target.

    ``build_formatting_structure`` calls
    ``target_collector.check_pending_targets()`` after the first pass to do
    required reparsing.

    """
    # TODO: Some computation done here may be done in computed_values
    # instead. We currently miss at least style_for, counters and quotes
    # context in computer. Some work will still need to be done here though,
    # like box creation for URIs.

    content_boxes = []
    has_text = set()  # Use a set because variable is modified in add_text

    def add_text(text):
        has_text.add(True)
        if text:
            if content_boxes and isinstance(content_boxes[-1], boxes.TextBox):
                content_boxes[-1].text += text
            else:
                content_boxes.append(
                    boxes.TextBox.anonymous_from(parent_box, text))

    missing_counters = []
    missing_target_counters = {}
    in_page_context = context is not None and page is not None

    # Collect missing counters during build_formatting_structure.
    # Pointless to collect missing target counters in MarginBoxes.
    need_collect_missing = target_collector.collecting and not in_page_context

    # TODO: remove attribute or set a default value in Box class
    if not hasattr(parent_box, 'cached_counter_values'):
        # Store the counter_values in the parent_box to make them accessible
        # in @page context. Obsoletes the parse_again function's deepcopy.
        # TODO: Is propbably superfluous in_page_context.
        parent_box.cached_counter_values = copy.deepcopy(counter_values)
    for type_, value in content_list:
        if type_ == 'string':
            add_text(value)
        elif type_ == 'url' and get_image_from_uri is not None:
            origin, uri = value
            if origin != 'external':
                # Embedding internal references is impossible
                continue
            image = get_image_from_uri(url=uri)
            if image is not None:
                content_boxes.append(
                    boxes.InlineReplacedBox.anonymous_from(parent_box, image))
        elif type_ == 'content()':
            added_text = TEXT_CONTENT_EXTRACTORS[value](parent_box)
            # Simulate the step of white space processing
            # (normally done during the layout)
            add_text(added_text.strip())
        elif type_ == 'counter()':
            counter_name, counter_type = value
            if need_collect_missing:
                _collect_missing_counter(
                    counter_name, counter_values, missing_counters)
            if counter_type != 'none':
                counter_value = counter_values.get(counter_name, [0])[-1]
                add_text(
                    counter_style.render_value(counter_value, counter_type))
        elif type_ == 'counters()':
            counter_name, separator, counter_type = value
            if need_collect_missing:
                _collect_missing_counter(
                    counter_name, counter_values, missing_counters)
            if counter_type != 'none':
                add_text(separator.join(
                    counter_style.render_value(counter_value, counter_type)
                    for counter_value
                    in counter_values.get(counter_name, [0])))
        elif type_ == 'string()':
            if not in_page_context:
                # string() is currently only valid in @page context
                # See https://github.com/Kozea/WeasyPrint/issues/723
                LOGGER.warning(
                    '"string(%s)" is only allowed in page margins',
                    ' '.join(value))
                continue
            add_text(context.get_string_set_for(page, *value))
        elif type_ == 'target-counter()':
            anchor_token, counter_name, counter_type = value
            lookup_target = target_collector.lookup_target(
                anchor_token, parent_box, css_token, parse_again)
            if lookup_target.state == 'up-to-date':
                target_values = lookup_target.target_box.cached_counter_values
                if need_collect_missing:
                    _collect_missing_target_counter(
                        counter_name, target_values,
                        target_collector.anchor_name_from_token(anchor_token),
                        missing_target_counters)
                # Mixin target's cached page counters.
                # cached_page_counter_values are empty during layout.
                local_counters = (
                    lookup_target.cached_page_counter_values.copy())
                local_counters.update(target_values)
                if counter_type != 'none':
                    counter_value = local_counters.get(counter_name, [0])[-1]
                    add_text(counter_style.render_value(
                        counter_value, counter_type))
            else:
                break
        elif type_ == 'target-counters()':
            anchor_token, counter_name, separator, counter_type = value
            lookup_target = target_collector.lookup_target(
                anchor_token, parent_box, css_token, parse_again)
            if lookup_target.state == 'up-to-date':
                if separator[0] != 'string':
                    break
                separator_string = separator[1]
                target_values = lookup_target.target_box.cached_counter_values
                if need_collect_missing:
                    _collect_missing_target_counter(
                        counter_name, target_values,
                        target_collector.anchor_name_from_token(anchor_token),
                        missing_target_counters)
                # Mixin target's cached page counters.
                # cached_page_counter_values are empty during layout.
                local_counters = (
                    lookup_target.cached_page_counter_values.copy())
                local_counters.update(target_values)
                if counter_type != 'none':
                    add_text(separator_string.join(
                        counter_style.render_value(counter_value, counter_type)
                        for counter_value
                        in local_counters.get(counter_name, [0])))
            else:
                break
        elif type_ == 'target-text()':
            anchor_token, text_style = value
            lookup_target = target_collector.lookup_target(
                anchor_token, parent_box, css_token, parse_again)
            if lookup_target.state == 'up-to-date':
                target_box = lookup_target.target_box
                # TODO: 'before'- and 'after'- content referring missing
                # counters are not properly set.
                text = TEXT_CONTENT_EXTRACTORS[text_style](target_box)
                # Simulate the step of white space processing
                # (normally done during the layout)
                add_text(text.strip())
            else:
                break
        elif (type_ == 'quote' and
                quote_depth is not None and
                quote_style is not None):
            is_open = 'open' in value
            insert = not value.startswith('no-')
            if not is_open:
                quote_depth[0] = max(0, quote_depth[0] - 1)
            if insert:
                open_quotes, close_quotes = quote_style
                quotes = open_quotes if is_open else close_quotes
                add_text(quotes[min(quote_depth[0], len(quotes) - 1)])
            if is_open:
                quote_depth[0] += 1
        elif type_ == 'element()':
            if not in_page_context:
                LOGGER.warning(
                    '"element(%s)" is only allowed in page margins',
                    ' '.join(value))
                continue
            new_box = context.get_running_element_for(page, *value)
            if new_box is None:
                continue
            new_box = new_box.deepcopy()
            new_box.style['position'] = 'static'
            if isinstance(new_box, boxes.ParentBox):
                for child in new_box.descendants():
                    if child.style['content'] in ('normal', 'none'):
                        continue
                    child.children = content_to_boxes(
                        child.style, child, quote_depth, counter_values,
                        get_image_from_uri, target_collector, counter_style,
                        context=context, page=page)
            content_boxes.append(new_box)
        elif type_ == 'leader()':
            text_box = boxes.TextBox.anonymous_from(parent_box, value[1])
            leader_box = boxes.InlineBox.anonymous_from(
                parent_box, (text_box,))
            # Avoid breaks inside the leader box
            leader_box.style['white_space'] = 'pre'
            # Prevent whitespaces from being removed from the text box
            text_box.style['white_space'] = 'pre'
            leader_box.is_leader = True
            content_boxes.append(leader_box)

    if has_text or content_boxes:
        # Only add CounterLookupItem if the content_list actually produced text
        target_collector.collect_missing_counters(
            parent_box, css_token, parse_again, missing_counters,
            missing_target_counters)
        return content_boxes


def content_to_boxes(style, parent_box, quote_depth, counter_values,
                     get_image_from_uri, target_collector, counter_style,
                     context=None, page=None):
    """Take the value of a ``content`` property and return boxes."""
    def parse_again(mixin_pagebased_counters=None):
        """Closure to parse the ``parent_boxes`` children all again."""

        # Neither alters the mixed-in nor the cached counter values, no
        # need to deepcopy here
        if mixin_pagebased_counters is None:
            local_counters = {}
        else:
            local_counters = mixin_pagebased_counters.copy()
        local_counters.update(parent_box.cached_counter_values)

        local_children = []
        local_children.extend(content_to_boxes(
            style, parent_box, orig_quote_depth, local_counters,
            get_image_from_uri, target_collector, counter_style))

        # TODO: do we need to add markers here?
        # TODO: redo the formatting structure of the parent instead of hacking
        # the already formatted structure. Find why inline_in_blocks has
        # sometimes already been called, and sometimes not.
        if (len(parent_box.children) == 1 and
                isinstance(parent_box.children[0], boxes.LineBox)):
            parent_box.children[0].children = local_children
        else:
            parent_box.children = local_children

    if style['content'] == 'inhibit':
        return []

    orig_quote_depth = quote_depth[:]
    css_token = 'content'
    box_list = compute_content_list(
        style['content'], parent_box, counter_values, css_token, parse_again,
        target_collector, counter_style, get_image_from_uri, quote_depth,
        style['quotes'], context, page)
    return box_list or []


def compute_string_set(element, box, string_name, content_list,
                       counter_values, target_collector, counter_style):
    """Parse the content-list value of ``string_name`` for ``string-set``."""
    def parse_again(mixin_pagebased_counters=None):
        """Closure to parse the string-set string value all again."""

        # Neither alters the mixed-in nor the cached counter values, no
        # need to deepcopy here
        if mixin_pagebased_counters is None:
            local_counters = {}
        else:
            local_counters = mixin_pagebased_counters.copy()
        local_counters.update(box.cached_counter_values)

        compute_string_set(
            element, box, string_name, content_list, local_counters,
            target_collector, counter_style)

    css_token = f'string-set::{string_name}'
    box_list = compute_content_list(
        content_list, box, counter_values, css_token, parse_again,
        target_collector, counter_style, element=element)
    if box_list is not None:
        string = ''.join(
            box.text for box in box_list if isinstance(box, boxes.TextBox))
        # Avoid duplicates, care for parse_again and missing counters, don't
        # change the pointer
        for string_set_tuple in box.string_set:
            if string_set_tuple[0] == string_name:
                box.string_set.remove(string_set_tuple)
                break
        box.string_set.append((string_name, string))


def compute_bookmark_label(element, box, content_list, counter_values,
                           target_collector, counter_style):
    """Parses the content-list value for ``bookmark-label``."""
    def parse_again(mixin_pagebased_counters={}):
        """Closure to parse the bookmark-label all again."""
        # Neither alters the mixed-in nor the cached counter values, no
        # need to deepcopy here
        if mixin_pagebased_counters is None:
            local_counters = {}
        else:
            local_counters = mixin_pagebased_counters.copy()
        local_counters = mixin_pagebased_counters.copy()
        local_counters.update(box.cached_counter_values)
        compute_bookmark_label(
            element, box, content_list, local_counters, target_collector,
            counter_style)

    css_token = 'bookmark-label'
    box_list = compute_content_list(
        content_list, box, counter_values, css_token, parse_again,
        target_collector, counter_style, element=element)
    if box_list:
        box.bookmark_label = ''.join(box_text(box) for box in box_list)


def set_content_lists(element, box, style, counter_values, target_collector,
                      counter_style):
    """Set the content-lists values.

    These content-lists are used in GCPM properties like ``string-set`` and
    ``bookmark-label``.

    """
    box.string_set = []
    if style['string_set'] != 'none':
        for i, (string_name, string_values) in enumerate(style['string_set']):
            compute_string_set(
                element, box, string_name, string_values, counter_values,
                target_collector, counter_style)
    if style['bookmark_label'] == 'none':
        box.bookmark_label = ''
    else:
        compute_bookmark_label(
            element, box, style['bookmark_label'], counter_values,
            target_collector, counter_style)


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

    for name, value in style['counter_set']:
        values = counter_values.setdefault(name, [])
        if not values:
            assert name not in sibling_scopes
            sibling_scopes.add(name)
            values.append(0)
        values[-1] = value

    counter_increment = style['counter_increment']
    if counter_increment == 'auto':
        # 'auto' is the initial value but is not valid in stylesheet:
        # there was no counter-increment declaration for this element.
        # (Or the winning value was 'initial'.)
        # http://dev.w3.org/csswg/css3-lists/#declaring-a-list-item
        if 'list-item' in style['display']:
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


def is_whitespace(box, _has_non_whitespace=re.compile('\\S').search):
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
    if not isinstance(box, boxes.ParentBox) or box.is_running():
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
        if display == ('table-header-group',) and header is None:
            group.is_header = True
            header = group
        elif display == ('table-footer-group',) and footer is None:
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

        style = box_style[f'border_{side}_style']
        width = box_style[f'border_{side}_width']
        color = get_color(box_style, f'border_{side}_color')

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
        box.style[f'border_{side}_style'] = 'solid'
        box.style[f'border_{side}_width'] = twice_width / 2
        box.style[f'border_{side}_color'] = transparent

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
    if not isinstance(box, boxes.ParentBox) or box.is_running():
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

    if isinstance(box, boxes.ParentBox) and not box.is_running():
        for child in box.children:
            if isinstance(child, (boxes.TextBox, boxes.InlineBox)):
                following_collapsible_space = process_whitespace(
                    child, following_collapsible_space)
            else:
                process_whitespace(child)
                if child.is_in_normal_flow():
                    following_collapsible_space = False

    return following_collapsible_space


def process_text_transform(box):
    if isinstance(box, boxes.TextBox):
        text_transform = box.style['text_transform']
        if text_transform != 'none':
            box.text = {
                'uppercase': lambda text: text.upper(),
                'lowercase': lambda text: text.lower(),
                # Python’s unicode.captitalize is not the same.
                'capitalize': lambda text: text.title(),
                'full-width': lambda text: text.translate(ASCII_TO_WIDE),
            }[text_transform](box.text)
        if box.style['hyphens'] == 'none':
            box.text = box.text.replace('\u00AD', '')  # U+00AD is soft hyphen

    if isinstance(box, boxes.ParentBox) and not box.is_running():
        for child in box.children:
            if isinstance(child, (boxes.TextBox, boxes.InlineBox)):
                process_text_transform(child)


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
    if not isinstance(box, boxes.ParentBox) or box.is_running():
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
                new_line_children and not child_box.is_in_normal_flow()):
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
    if not isinstance(box, boxes.ParentBox) or box.is_running():
        return box

    new_children = []
    changed = False

    for child in box.children:
        if isinstance(child, boxes.LineBox):
            assert len(box.children) == 1, (
                'Line boxes should have no '
                'siblings at this stage, got %r.' % box.children)
            stack = None
            while True:
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
        (skip, skip_stack), = skip_stack.items()

    for i, child in enumerate(box.children[skip:]):
        index = i + skip
        if (isinstance(child, boxes.BlockLevelBox) and
                child.is_in_normal_flow()):
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
            resume_at = {index: resume_at}
            box = box.copy_with_children(new_children)
            break
    else:
        if changed or skip:
            box = box.copy_with_children(new_children)

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
            not child.element_tag.endswith('::marker') and
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
    'content': box_text,
    'before': box_text_before,
    'after': box_text_after,
    'first-letter': box_text_first_letter}
