"""
    weasyprint.layout
    -----------------

    Transform a "before layout" box tree into an "after layout" tree.
    (Surprising, hu?)

    Break boxes across lines and pages; determine the size and dimension
    of each box fragement.

    Boxes in the new tree have *used values* in their ``position_x``,
    ``position_y``, ``width`` and ``height`` attributes, amongst others.

    See http://www.w3.org/TR/CSS21/cascade.html#used-value

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from collections import defaultdict

from ..formatting_structure import boxes
from ..logger import PROGRESS_LOGGER
from .absolute import absolute_box_layout, absolute_layout
from .backgrounds import layout_backgrounds
from .pages import make_all_pages, make_margin_boxes


def initialize_page_maker(context, root_box):
    """Initialize ``context.page_maker``.

    Collect the pagination's states required for page based counters.

    """
    context.page_maker = []

    # Special case the root box
    page_break = root_box.style['break_before']

    # TODO: take care of text direction and writing mode
    # https://www.w3.org/TR/css3-page/#progression
    if page_break in 'right':
        right_page = True
    elif page_break == 'left':
        right_page = False
    elif page_break in 'recto':
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
        [{'pages'}]  # counter_scopes
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
            yield absolute_box_layout(
                context, box, containing_page, absolute_boxes)
            while absolute_boxes:
                new_absolute_boxes = []
                for box in absolute_boxes:
                    absolute_layout(
                        context, box, containing_page, new_absolute_boxes)
                absolute_boxes = new_absolute_boxes


def layout_document(html, root_box, context, max_loops=8):
    """Lay out the whole document.

    This includes line breaks, page breaks, absolute size and position for all
    boxes. Page based counters might require multiple passes.

    :param root_box: root of the box tree (formatting structure of the html)
                     the pages' boxes are created from that tree, i.e. this
                     structure is not lost during pagination
    :returns: a list of laid out Page objects.

    """
    initialize_page_maker(context, root_box)
    pages = []
    actual_total_pages = 0

    for loop in range(max_loops):
        if loop > 0:
            PROGRESS_LOGGER.info(
                'Step 5 - Creating layout - Repagination #%i' % loop)

        initial_total_pages = actual_total_pages
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

    # Calculate string-sets and bookmark-label containing page based counters
    # when pagination is finished. No need to do that (maybe multiple times) in
    # make_page because they dont create boxes, only appear in MarginBoxes and
    # in the final PDF.
    for i, page in enumerate(pages):
        # We need the updated page_counter_values
        resume_at, next_page, right_page, page_state, remake_state = (
            context.page_maker[i + 1])
        page_counter_values = page_state[1]

        for child in page.descendants():
            # TODO: remove attribute or set a default value in Box class
            if hasattr(child, 'missing_link'):
                for (box, css_token), item in (
                        context.target_collector.counter_lookup_items.items()):
                    if child.missing_link == box and css_token != 'content':
                        item.parse_again(page_counter_values)
            # Collect the string_sets in the LayoutContext
            string_sets = child.string_set
            if string_sets and string_sets != 'none':
                for string_set in string_sets:
                    string_name, text = string_set
                    context.string_set[string_name][i+1].append(text)

    # Add margin boxes
    for i, page in enumerate(pages):
        root_children = []
        root, = page.children
        root_children.extend(layout_fixed_boxes(context, pages[:i], page))
        root_children.extend(root.children)
        root_children.extend(layout_fixed_boxes(context, pages[i + 1:], page))
        root.children = root_children
        context.current_page = i + 1  # page_number starts at 1

        # page_maker's page_state is ready for the MarginBoxes
        state = context.page_maker[context.current_page][3]
        page.children = (root,) + tuple(
            make_margin_boxes(context, page, state))
        layout_backgrounds(page, context.get_image_from_uri)
        yield page


class LayoutContext(object):
    def __init__(self, enable_hinting, style_for, get_image_from_uri,
                 font_config, target_collector):
        self.enable_hinting = enable_hinting
        self.style_for = style_for
        self.get_image_from_uri = get_image_from_uri
        self.font_config = font_config
        self.target_collector = target_collector
        self._excluded_shapes_lists = []
        self.excluded_shapes = None  # Not initialized yet
        self.string_set = defaultdict(lambda: defaultdict(lambda: list()))
        self.current_page = None
        self.forced_break = False

        # Cache
        self.strut_layouts = {}
        self.font_features = {}
        self.tables = {}
        self.dictionaries = {}

    def create_block_formatting_context(self):
        self.excluded_shapes = []
        self._excluded_shapes_lists.append(self.excluded_shapes)

    def finish_block_formatting_context(self, root_box):
        # See http://www.w3.org/TR/CSS2/visudet.html#root-height
        if root_box.style['height'] == 'auto' and self.excluded_shapes:
            box_bottom = root_box.content_box_y() + root_box.height
            max_shape_bottom = max([
                shape.position_y + shape.margin_height()
                for shape in self.excluded_shapes] + [box_bottom])
            root_box.height += max_shape_bottom - box_bottom
        self._excluded_shapes_lists.pop()
        if self._excluded_shapes_lists:
            self.excluded_shapes = self._excluded_shapes_lists[-1]
        else:
            self.excluded_shapes = None

    def get_string_set_for(self, page, name, keyword='first'):
        """Resolve value of string function (as set by string set).

        We'll have something like this that represents all assignments on a
        given page:

        {1: [u'First Header'], 3: [u'Second Header'],
         4: [u'Third Header', u'3.5th Header']}

        Value depends on current page.
        http://dev.w3.org/csswg/css-gcpm/#funcdef-string

        :param name: the name of the named string.
        :param keyword: indicates which value of the named string to use.
                        Default is the first assignment on the current page
                        else the most recent assignment (entry value)
        :returns: text

        """
        if self.current_page in self.string_set[name]:
            # A value was assigned on this page
            first_string = self.string_set[name][self.current_page][0]
            last_string = self.string_set[name][self.current_page][-1]
            if keyword == 'first':
                return first_string
            elif keyword == 'start':
                element = page
                while element:
                    if element.style['string_set'] != 'none':
                        for (string_name, _) in element.style['string_set']:
                            if string_name == name:
                                return first_string
                    if isinstance(element, boxes.ParentBox):
                        if element.children:
                            element = element.children[0]
                            continue
                    break
            elif keyword == 'last':
                return last_string
        # Search backwards through previous pages
        for previous_page in range(self.current_page - 1, 0, -1):
            if previous_page in self.string_set[name]:
                return self.string_set[name][previous_page][-1]
        return ''
