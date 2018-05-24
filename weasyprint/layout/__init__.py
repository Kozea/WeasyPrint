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

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from collections import defaultdict

from .absolute import absolute_box_layout
from .pages import make_all_pages, make_margin_boxes
from .backgrounds import layout_backgrounds
from ..formatting_structure import boxes


def layout_fixed_boxes(context, pages):
    """Lay out and yield the fixed boxes of ``pages``."""
    for page in pages:
        for box in page.fixed_boxes:
            # Use an empty list as last argument because the fixed boxes in the
            # fixed box has already been added to page.fixed_boxes, we don't
            # want to get them again
            yield absolute_box_layout(context, box, page, [])


def layout_document(enable_hinting, style_for, get_image_from_uri, root_box,
                    font_config, html, cascaded_styles, computed_styles,
                    target_collector):
    """Lay out the whole document.

    This includes line breaks, page breaks, absolute size and position for all
    boxes.

    :param context: a LayoutContext object.
    :returns: a list of laid out Page objects.

    """
    context = LayoutContext(
        enable_hinting, style_for, get_image_from_uri, font_config,
        target_collector)
    pages = list(make_all_pages(
        context, root_box, html, cascaded_styles, computed_styles))

    # although neither a variable quote_depth nor counter_scopes are needed
    # in page-boxes -- reusing `formatting_structure.build.update_counters()`
    # to avoid redundant code requires a full `state`
    state = (
        # Shared mutable objects:
        [0],  # quote_depth: single integer
        # initialize with the fixed `pages` counter
        {'pages': [len(pages)]},   # counter_values
        [{'pages'}]  # counter_scopes
    )
    for i, page in enumerate(pages):
        root_children = []
        root, = page.children
        root_children.extend(layout_fixed_boxes(context, pages[:i]))
        root_children.extend(root.children)
        root_children.extend(layout_fixed_boxes(context, pages[i + 1:]))
        root.children = root_children
        context.current_page = i+1  # page_number starts at 1
        page.children = (root,) + tuple(
            make_margin_boxes(context, page, state, target_collector))
        layout_backgrounds(page, get_image_from_uri)
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
