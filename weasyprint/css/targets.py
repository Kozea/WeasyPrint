"""Handle target-counter, target-counters and target-text.

The TargetCollector is a structure providing required targets' counter_values
and stuff needed to build pending targets later, when the layout of all
targeted anchors has been done.

"""

import copy

from ..logger import LOGGER
from ..urls import get_url_tuple


def anchor_name_from_token(anchor_token):
    """Get anchor name from string or uri token."""
    if anchor_token[0] == 'string' and anchor_token[1].startswith('#'):
        return anchor_token[1][1:]
    elif anchor_token[0] == 'url' and anchor_token[1][0] == 'internal':
        return anchor_token[1][1]


class Target:
    """Item controlling pending targets and page based target counters.

    Collected in the TargetCollector's ``targets``.

    """
    def __init__(self, state='pending'):
        self.state = state
        # Required by target-counter and target-counters to access the
        # target's .cached_counter_values.
        # Needed for target-text via extract_text().
        self.target_box = None
        # Functions that have to been called to check pending targets.
        self.parse_again_functions = []
        # Anchor page index during pagination.
        self.page_maker_index = None
        # target_box's page_counters during pagination.
        self.cached_page_counter_values = {}


class Counter:
    """Item controlling page based counters.

    Collected in the TargetCollector's ``counters``.

    """
    def __init__(self, parse_again, missing_counters, missing_target_counters):
        # Function that have to been called to check pending counter.
        self.parse_again = parse_again
        # Missing counters and target counters.
        self.missing_counters = missing_counters
        self.missing_target_counters = missing_target_counters
        # Box page index position during pagination.
        self.page_maker_index = None
        # Marker for make_page.
        self.pending = False
        # Targeting box's page_counters during pagination.
        self.cached_page_counter_values = {}


class TargetCollector:
    """Collector of HTML targets used by CSS content with ``target-*``."""
    def __init__(self):
        # Lookup items for targets and page counters.
        self.targets = {}
        self.counters = {}
        # had_pending_targets is set to True when a target is needed but has
        # not been seen yet. check_pending_targets then uses this information
        # to call the needed parse_again functions.
        self.had_pending_targets = False

    def collect_anchor(self, anchor_name):
        """Create a Target for the given `anchor_name``."""
        if anchor_name in self.targets:
            LOGGER.warning('Anchor defined twice: %r', anchor_name)
        else:
            self.targets[anchor_name] = Target()

    def lookup_target(self, anchor_token, source_box, css_token, parse_again):
        """Get a Target corresponding to ``anchor_token``.

        If it is already filled by a previous anchor-element, the status is
        'up-to-date'. Otherwise, it is 'pending', we must parse the whole
        tree again.

        """
        if anchor_token[0] == 'attr()':
            attr_name, type_, fallback = anchor_token[1]
            attr_value = source_box.element.get(attr_name, fallback)
            if type_ == 'string':
                anchor_token = ('string', attr_value)
            elif type_ == 'url':
                url_tuple = get_url_tuple(attr_value, source_box.style.base_url)
                anchor_token = ('url', url_tuple)
        anchor_name = anchor_name_from_token(anchor_token)
        item = self.targets.get(anchor_name, Target('undefined'))

        if item.state == 'pending':
            self.had_pending_targets = True
            item.parse_again_functions.append(parse_again)

        if item.state == 'undefined':
            LOGGER.error(
                'Content discarded: target points to undefined anchor %r', anchor_token)

        return item

    def store_target(self, anchor_name, target_counter_values, target_box):
        """Store a target called ``anchor_name``.

        If there is a pending Target, it is updated. Only previously collected anchors
        are stored.

        """
        item = self.targets.get(anchor_name)
        if item and item.state == 'pending':
            item.state = 'up-to-date'
            item.target_box = target_box
            # Store the counter_values in the target_box like compute_content_list does.
            if target_box.cached_counter_values is None:
                target_box.cached_counter_values = {
                    key: value.copy() for key, value in target_counter_values.items()}

    def collect_missing_counters(self, parent_box, css_token, parse_again_function,
                                 missing_counters, missing_target_counters):
        """Collect missing (probably page-based) counters during formatting.

        The ``missing_counters`` are re-used during pagination.

        The ``missing_link`` attribute added to the parent_box is required to
        connect the paginated boxes to their originating ``parent_box``.

        """
        # No need to add empty miss-lists.
        if missing_counters or missing_target_counters:
            if parent_box.missing_link is None:
                parent_box.missing_link = parent_box
            self.counters[parent_box, css_token] = Counter(
                parse_again_function, missing_counters, missing_target_counters)

    def check_pending_targets(self):
        """Check pending targets if needed."""
        if self.had_pending_targets:
            for item in self.targets.values():
                for function in item.parse_again_functions:
                    function({})
            self.had_pending_targets = False

    def cache_target_page_counters(self, anchor_name, page_counter_values,
                                   page_maker_index, page_maker):
        """Store target's current ``page_maker_index`` and page counter values.

        Eventually update associated targeting boxes.

        """
        item = self.targets.get(anchor_name)
        if not item or item.state != 'up-to-date':
            return
        if item.cached_page_counter_values == page_counter_values:
            return

        item.page_maker_index = page_maker_index
        item.cached_page_counter_values = copy.deepcopy(page_counter_values)

        # Spread the news: update boxes affected by a change in the
        # anchor's page counter values.
        for (_, css_token), item in self.counters.items():
            # Only update items that need counters in their content.
            if css_token != 'content':
                continue

            # Don't update if item has no missing target counter.
            missing_counters = item.missing_target_counters.get(anchor_name)
            if missing_counters is None:
                continue

            # Pending marker for make_page.
            if page_maker_index is None or page_maker_index >= len(page_maker):
                item.pending = True
                continue
