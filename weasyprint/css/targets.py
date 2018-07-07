"""
    weasyprint.formatting_structure.targets
    ---------------------------------------

    Handle target-counter, target-counters and target-text.

    The TargetCollector is a structure providing required targets'
    counter_values and stuff needed to build pending targets later,
    when the layout of all targetted anchors has been done.

    :copyright: Copyright 2018 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import copy

from ..logger import LOGGER


class TargetLookupItem(object):
    """
    Item to control pending targets and page based target counters.
    Collected in the TargetColector's ``items``
    """

    def __init__(self, state='pending'):
        self.state = state
        # Required by target-counter and target-counters to access the
        # target's .cached_counter_values.
        # Needed for target-text via TEXT_CONTENT_EXTRACTORS
        self.target_box = None
        # stuff for pending targets
        self.pending_boxes = {}
        # stuff for page based counters
        # the target_box's page_counters during pagination
        self.cached_page_counter_values = {}


class CounterLookupItem(object):
    """
    Item to control page based counters.
    Collected in the TargetColector's ``counter_lookup_items``
    """

    def __init__(self, parse_again_func, missing_counters,
                 missing_target_counters):
        self.parse_again = parse_again_func
        self.missing_counters = missing_counters
        self.missing_target_counters = missing_target_counters
        # the targeting box's page_counters during pagination
        self.cached_page_counter_values = {}


class TargetCollector(object):
    """Collector of HTML targets used by CSS content with ``target-*``."""

    def __init__(self):
        self.had_pending_targets = False
        self.existing_anchors = []
        self.items = {}
        # when collecting == True, compute_content_list() collects missing
        # page counters (CounterLookupItems) otherwise it mixes in the
        # TargetLookupItem's cached_page_counter_values.
        # Is switched to False in check_pending_targets()
        self.collecting = True
        self.counter_lookup_items = {}

    def _anchor_name_from_token(self, anchor_token):
        """Get anchor name from string or uri token."""
        if anchor_token[0] == 'string' and anchor_token[1].startswith('#'):
            return anchor_token[1][1:]
        elif anchor_token[0] == 'url' and anchor_token[1][0] == 'internal':
            return anchor_token[1][1]

    def collect_anchor(self, anchor_name):
        """Store ``anchor_name`` in ``existing_anchors``."""
        if anchor_name and isinstance(anchor_name, str):
            if anchor_name in self.existing_anchors:
                LOGGER.warning('Anchor defined twice: %s', anchor_name)
            else:
                self.existing_anchors.append(anchor_name)

    def collect_computed_target(self, anchor_token):
        """Store a computed internal target's ``anchor_name``.

        ``anchor_name`` must not start with '#' and be already unquoted.

        """
        anchor_name = self._anchor_name_from_token(anchor_token)
        if anchor_name:
            self.items.setdefault(anchor_name, TargetLookupItem())

    def lookup_target(self, anchor_token, source_box, css_token,
                      parse_again_function):
        """Get a TargetLookupItem corresponding to ``anchor_token``.

        If it is already filled by a previous anchor-element, the status is
        'up-to-date'. Otherwise, it is 'pending', we must parse the whole
        tree again.

        """
        anchor_name = self._anchor_name_from_token(anchor_token)
        item = self.items.get(anchor_name, TargetLookupItem('undefined'))

        if item.state == 'pending':
            if anchor_name in self.existing_anchors:
                self.had_pending_targets = True
                item.pending_boxes.setdefault(
                    (source_box, css_token), parse_again_function)
            else:
                item.state = 'undefined'

        if item.state == 'undefined':
            LOGGER.error(
                'Content discarded: target points to undefined anchor "%s"',
                anchor_token)

        return item

    def store_target(self, anchor_name, target_counter_values, target_box):
        """Store a target called ``anchor_name``.

        If there is a pending TargetLookupItem, it is updated. Only previously
        collected anchors are stored.

        """
        item = self.items.get(anchor_name)
        if item and item.state == 'pending':
            item.state = 'up-to-date'
            item.target_box = target_box
            # Store the counter_values in the target_box like
            # compute_content_list does.
            if not hasattr(target_box, 'cached_counter_values'):
                target_box.cached_counter_values = \
                    copy.deepcopy(target_counter_values)

    def collect_missing_counters(self, parent_box, css_token,
                                 parse_again_function, missing_counters,
                                 missing_target_counters):
        """
        Collect missing, probably page based, counters during formatting.
        The MissingCounterItems are re-used during pagination.
        The ``missing_link`` attribute added to the parent_box is required
        to connect the paginated box(es) to their originating parent_box
        resp. their counter_lookup_items.
        """
        # no counter collection during pagination
        if not self.collecting:
            return
        # no need to add empty miss-lists
        if missing_counters or missing_target_counters:
            # trick 17: ensure connection!
            if not hasattr(parent_box, 'missing_link'):
                parent_box.missing_link = parent_box
            self.counter_lookup_items.setdefault(
                (parent_box, css_token),
                CounterLookupItem(parse_again_function,
                                  missing_counters,
                                  missing_target_counters))

    def check_pending_targets(self):
        """Check pending targets if needed."""
        if self.had_pending_targets:
            for key, item in self.items.items():
                for (box, _css_token), function in item.pending_boxes.items():
                    function()
            self.had_pending_targets = False
        # ready for pagination, info@compute_content_list
        self.collecting = False
