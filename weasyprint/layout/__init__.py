"""Transform a "before layout" box tree into an "after layout" tree.

Break boxes across lines and pages; determine the size and dimension of each
box fragement.

Boxes in the new tree have *used values* in their ``position_x``,
``position_y``, ``width`` and ``height`` attributes, amongst others.

See https://www.w3.org/TR/CSS21/cascade.html#used-value

"""

from collections import defaultdict
from functools import partial
from math import inf

from ..formatting_structure import boxes, build
from ..logger import PROGRESS_LOGGER
from .absolute import absolute_box_layout, absolute_layout
from .background import layout_backgrounds
from .block import block_level_layout
from .page import make_all_pages, make_margin_boxes


def initialize_page_maker(context, root_box):
    """Initialize ``context.page_maker``.

    Collect the pagination's states required for page based counters.

    """
    context.page_maker = []

    # Special case the root box
    page_break = root_box.style['break_before']

    # TODO: take care of text direction and writing mode
    # https://www.w3.org/TR/css-page-3/#progression
    if page_break == 'right':
        right_page = True
    elif page_break == 'left':
        right_page = False
    elif page_break == 'recto':
        right_page = root_box.style['direction'] == 'ltr'
    elif page_break == 'verso':
        right_page = root_box.style['direction'] == 'rtl'
    else:
        right_page = root_box.style['direction'] == 'ltr'
    resume_at = None
    next_page = {'break': 'any', 'page': root_box.page_values()[0]}

    # page_state is prerequisite for filling in missing page based counters
    # although neither a variable quote_depth nor counter_scopes are needed
    # in page-boxes -- reusing
    # `formatting_structure.build.update_counters()` to avoid redundant
    # code requires a full `state`.
    # The value of **pages**, of course, is unknown until we return and
    # might change when 'content_changed' triggers re-pagination...
    # So we start with an empty state
    page_state = (
        # Shared mutable objects:
        [0],  # quote_depth: single integer
        {'pages': [0]},
        [{'pages'}],  # counter_scopes
        [] # page_groups
    )

    # Initial values
    remake_state = {
        'content_changed': False,
        'pages_wanted': False,
        'anchors': [],  # first occurrence of anchor
        'content_lookups': []  # first occurr. of content-CounterLookupItem
    }
    context.page_maker.append((
        resume_at, next_page, right_page, page_state, remake_state))


def layout_fixed_boxes(context, pages, containing_page):
    """Lay out and yield fixed boxes of ``pages`` on ``containing_page``."""
    for page in pages:
        for box in page.fixed_boxes:
            # As replaced boxes are never copied during layout, ensure that we
            # have different boxes (with a possibly different layout) for
            # each pages.
            if isinstance(box, boxes.ReplacedBox):
                box = box.copy()
            # Absolute boxes in fixed boxes are rendered as fixed boxes'
            # children, even when they are fixed themselves.
            absolute_boxes = []
            absolute_box, _ = absolute_box_layout(
                context, box, containing_page, absolute_boxes,
                bottom_space=-inf, skip_stack=None)
            yield absolute_box
            while absolute_boxes:
                new_absolute_boxes = []
                for box in absolute_boxes:
                    absolute_layout(
                        context, box, containing_page, new_absolute_boxes,
                        bottom_space=-inf, skip_stack=None)
                absolute_boxes = new_absolute_boxes


def layout_document(html, root_box, context, max_loops=8):
    """Lay out the whole document.

    This includes line breaks, page breaks, absolute size and position for all
    boxes. Page based counters might require multiple passes.

    :param root_box:
        Root of the box tree (formatting structure of the HTML). The page boxes
        are created from that tree, this structure is not lost during
        pagination.
    :returns:
        A list of laid out Page objects.

    """
    initialize_page_maker(context, root_box)
    pages = []
    original_footnotes = []
    actual_total_pages = 0

    for loop in range(max_loops):
        if loop > 0:
            PROGRESS_LOGGER.info(
                'Step 5 - Creating layout - Repagination #%d', loop)
            context.footnotes = original_footnotes.copy()

        initial_total_pages = actual_total_pages
        if loop == 0:
            original_footnotes = context.footnotes.copy()
        pages = list(make_all_pages(context, root_box, html, pages))
        actual_total_pages = len(pages)

        # Check whether another round is required
        reloop_content = False
        reloop_pages = False
        for page_data in context.page_maker:
            # Update pages
            _, _, _, page_state, remake_state = page_data
            page_counter_values = page_state[1]
            page_counter_values['pages'] = [actual_total_pages]
            if remake_state['content_changed']:
                reloop_content = True
            if remake_state['pages_wanted']:
                reloop_pages = initial_total_pages != actual_total_pages

        # No need for another loop, stop here
        if not reloop_content and not reloop_pages:
            break

    # Calculate string-sets and bookmark-labels containing page based counters
    # when pagination is finished. No need to do that (maybe multiple times) in
    # make_page because they dont create boxes, only appear in MarginBoxes and
    # in the final PDF.
    # Prevent repetition of bookmarks (see #1145).

    watch_elements = []
    watch_elements_before = []
    watch_elements_after = []
    for i, page in enumerate(pages):
        # We need the updated page_counter_values
        _, _, _, page_state, _ = context.page_maker[i + 1]
        page_counter_values = page_state[1]

        for child in page.descendants():
            # Only one bookmark per original box
            if child.bookmark_label:
                if child.element_tag.endswith('::before'):
                    checklist = watch_elements_before
                elif child.element_tag.endswith('::after'):
                    checklist = watch_elements_after
                else:
                    checklist = watch_elements
                if child.element in checklist:
                    child.bookmark_label = ''
                else:
                    checklist.append(child.element)

            if child.missing_link:
                for (box, css_token), item in (
                        context.target_collector.counter_lookup_items.items()):
                    if child.missing_link == box and css_token != 'content':
                        if (css_token == 'bookmark-label' and
                                not child.bookmark_label):
                            # don't refill it!
                            continue
                        item.parse_again(page_counter_values)
                        # string_set is a pointer, but the bookmark_label is
                        # just a string: copy it
                        if css_token == 'bookmark-label':
                            child.bookmark_label = box.bookmark_label
            # Collect the string_sets in the LayoutContext
            string_sets = child.string_set
            if string_sets and string_sets != 'none':
                for string_set in string_sets:
                    string_name, text = string_set
                    context.string_set[string_name][i+1].append(text)

    # Add margin boxes
    for i, page in enumerate(pages):
        root_children = []
        root, footnote_area = page.children
        root_children.extend(layout_fixed_boxes(context, pages[:i], page))
        root_children.extend(root.children)
        root_children.extend(layout_fixed_boxes(context, pages[i + 1:], page))
        root.children = root_children
        context.current_page = i + 1  # page_number starts at 1

        # page_maker's page_state is ready for the MarginBoxes
        state = context.page_maker[context.current_page][3]
        page.children = (root,)
        if footnote_area.children:
            page.children += (footnote_area,)
        page.children += tuple(make_margin_boxes(context, page, state))
        layout_backgrounds(page, context.get_image_from_uri)
        yield page


class FakeList(list):
    """List in which you can’t append objects."""
    def append(self, item):
        pass


class LayoutContext:
    def __init__(self, style_for, get_image_from_uri, font_config,
                 counter_style, target_collector):
        self.style_for = style_for
        self.get_image_from_uri = partial(get_image_from_uri, context=self)
        self.font_config = font_config
        self.counter_style = counter_style
        self.target_collector = target_collector
        self._excluded_shapes_root_boxes = []
        self._excluded_shapes = {}
        self.footnotes = []
        self.page_footnotes = {}
        self.current_page_footnotes = []
        self.reported_footnotes = []
        self.current_footnote_area = None  # Not initialized yet
        self.page_bottom = None
        self.string_set = defaultdict(lambda: defaultdict(list))
        self.running_elements = defaultdict(lambda: defaultdict(list))
        self.current_page = None
        self.forced_break = False
        self.broken_out_of_flow = {}
        self.in_column = False

        # Cache
        self.tables = {}
        self.dictionaries = {}

    def overflows_page(self, bottom_space, position_y):
        return self.overflows(self.page_bottom - bottom_space, position_y)

    @staticmethod
    def overflows(bottom, position_y):
        # Use a small fudge factor to avoid floating numbers errors.
        # The 1e-9 value comes from PEP 485.
        return position_y > bottom * (1 + 1e-9)

    @property
    def excluded_shapes(self):
        return self._excluded_shapes[self._excluded_shapes_root_boxes[-1]]

    @excluded_shapes.setter
    def excluded_shapes(self, excluded_shapes):
        self._excluded_shapes[self._excluded_shapes_root_boxes[-1]] = excluded_shapes

    def create_block_formatting_context(self, root_box=None, new_list=None):
        assert root_box not in self._excluded_shapes_root_boxes
        self._excluded_shapes_root_boxes.append(root_box)
        if root_box not in self._excluded_shapes:
            self._excluded_shapes[root_box] = [] if new_list is None else new_list

    def finish_block_formatting_context(self, root_box=None):
        # See https://www.w3.org/TR/CSS2/visudet.html#root-height
        if root_box and root_box.style['height'] == 'auto' and self.excluded_shapes:
            box_bottom = root_box.content_box_y() + root_box.height
            max_shape_bottom = max([
                shape.position_y + shape.margin_height()
                for shape in self.excluded_shapes] + [box_bottom])
            root_box.height += max_shape_bottom - box_bottom
        self._excluded_shapes.pop(self._excluded_shapes_root_boxes.pop())

    def create_flex_formatting_context(self, root_box):
        self.create_block_formatting_context(root_box, FakeList())

    def finish_flex_formatting_context(self, root_box):
        self.finish_block_formatting_context(root_box)

    def add_broken_out_of_flow(self, new_box, box, containing_block, resume_at):
        self.broken_out_of_flow[new_box] = (
            box, containing_block, self._excluded_shapes_root_boxes[-1], resume_at)

    def get_string_set_for(self, page, name, keyword='first'):
        """Resolve value of string function."""
        return self.get_string_or_element_for(
            self.string_set, page, name, keyword)

    def get_running_element_for(self, page, name, keyword='first'):
        """Resolve value of element function."""
        return self.get_string_or_element_for(
            self.running_elements, page, name, keyword)

    def get_string_or_element_for(self, store, page, name, keyword):
        """Resolve value of string or element function.

        We'll have something like this that represents all assignments on a
        given page:

        {1: ['First Header'], 3: ['Second Header'],
         4: ['Third Header', '3.5th Header']}

        Value depends on current page.
        https://drafts.csswg.org/css-gcpm/#funcdef-string

        :param dict store:
            Dictionary where the resolved value is stored.
        :param page:
            Current page.
        :param str name:
            Name of the named string or running element.
        :param str keyword:
            Indicates which value of the named string or running element to
            use. Default is the first assignment on the current page else the
            most recent assignment.
        :returns:
            Text for string set, box for running element.

        """
        if self.current_page in store[name]:
            # A value was assigned on this page
            first_string = store[name][self.current_page][0]
            last_string = store[name][self.current_page][-1]
            if keyword == 'first':
                return first_string
            elif keyword == 'start':
                element = page
                while element:
                    if element.style['string_set'] != 'none':
                        for (string_name, _) in element.style['string_set']:
                            if string_name == name:
                                return first_string
                    if element.children:
                        element = element.children[0]
                        continue
                    break
            elif keyword == 'last':
                return last_string
            elif keyword == 'first-except':
                return
        # Search backwards through previous pages
        for previous_page in range(self.current_page - 1, 0, -1):
            if previous_page in store[name]:
                return store[name][previous_page][-1]

    def layout_footnote(self, footnote):
        """Add a footnote to the layout for this page."""
        self.footnotes.remove(footnote)
        self.current_page_footnotes.append(footnote)
        return self._update_footnote_area()

    def unlayout_footnote(self, footnote):
        """Remove a footnote from the layout and return it to the waitlist."""
        # TODO: Handle unlayouting a footnote that hasn't been laid out yet or
        # has already been unlayouted
        if footnote not in self.footnotes:
            self.footnotes.append(footnote)
            if footnote in self.current_page_footnotes:
                self.current_page_footnotes.remove(footnote)
            elif footnote in self.reported_footnotes:
                self.reported_footnotes.remove(footnote)
            self._update_footnote_area()

    def report_footnote(self, footnote):
        """Mark a footnote as being moved to the next page."""
        self.current_page_footnotes.remove(footnote)
        self.reported_footnotes.append(footnote)
        self._update_footnote_area()

    def _update_footnote_area(self):
        """Update the page bottom size and our footnote area height."""
        if self.current_footnote_area.height != 'auto' and not self.in_column:
            self.page_bottom += self.current_footnote_area.margin_height()
        self.current_footnote_area.children = self.current_page_footnotes
        if self.current_footnote_area.children:
            footnote_area = build.create_anonymous_boxes(
                self.current_footnote_area.deepcopy())
            footnote_area = block_level_layout(
                self, footnote_area, -inf, None,
                self.current_footnote_area.page)[0]
            self.current_footnote_area.height = footnote_area.height
            if not self.in_column:
                self.page_bottom -= footnote_area.margin_height()
            last_child = footnote_area.children[-1]
            last_child_bottom = (
                last_child.position_y + last_child.margin_height() -
                last_child.margin_bottom)
            footnote_area_bottom = (
                footnote_area.position_y + footnote_area.margin_height() -
                footnote_area.margin_bottom)
            overflow = last_child_bottom > footnote_area_bottom
            return overflow
        else:
            self.current_footnote_area.height = 0
            if not self.in_column:
                self.page_bottom -= self.current_footnote_area.margin_height()
            return False
