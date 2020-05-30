"""
    weasyprint.formatting_structure.targets
    ---------------------------------------

    Handle target-counter, target-counters and target-text.

    The TargetCollector is a structure providing required targets'
    counter_values and stuff needed to build pending targets later,
    when the layout of all targeted anchors has been done.

"""

import copy

from ..logger import LOGGER


class TargetLookupItem:
    """Item controlling pending targets and page based target counters.

    Collected in the TargetCollector's ``target_lookup_items``.

    """
    def __init__(self, state='pending'):
        self.state = state

        # Required by target-counter and target-counters to access the
        # target's .cached_counter_values.
        # Needed for target-text via TEXT_CONTENT_EXTRACTORS.
        self.target_box = None

        # Functions that have to been called to check pending targets.
        # Keys are (source_box, css_token).
        self.parse_again_functions = {}

        # Anchor position during pagination (page_number - 1)
        self.page_maker_index = None

        # target_box's page_counters during pagination
        self.cached_page_counter_values = {}


class CounterLookupItem:
    """Item controlling page based counters.

    Collected in the TargetCollector's ``counter_lookup_items``.

    """
    def __init__(self, parse_again, missing_counters, missing_target_counters):
        # Function that have to been called to check pending counter.
        self.parse_again = parse_again

        # Missing counters and target counters
        self.missing_counters = missing_counters
        self.missing_target_counters = missing_target_counters

        # Box position during pagination (page_number - 1)
        self.page_maker_index = None

        # Marker for remake_page
        self.pending = False

        # Targeting box's page_counters during pagination
        self.cached_page_counter_values = {}


class TargetCollector:
    """Collector of HTML targets used by CSS content with ``target-*``."""

    def __init__(self):
        # Lookup items for targets and page counters
        self.target_lookup_items = {}
        self.counter_lookup_items = {}

        # When collecting is True, compute_content_list() collects missing
        # page counters in CounterLookupItems. Otherwise, it mixes in the
        # TargetLookupItem's cached_page_counter_values.
        # Is switched to False in check_pending_targets().
        self.collecting = True

        # had_pending_targets is set to True when a target is needed but has
        # not been seen yet. check_pending_targets then uses this information
        # to call the needed parse_again functions.
        self.had_pending_targets = False

    def anchor_name_from_token(self, anchor_token):
        """Get anchor name from string or uri token."""
        if anchor_token[0] == 'string' and anchor_token[1].startswith('#'):
            return anchor_token[1][1:]
        elif anchor_token[0] == 'url' and anchor_token[1][0] == 'internal':
            return anchor_token[1][1]

    def collect_anchor(self, anchor_name):
        """Create a TargetLookupItem for the given `anchor_name``."""
        if anchor_name and isinstance(anchor_name, str):
            if self.target_lookup_items.get(anchor_name) is not None:
                LOGGER.warning('Anchor defined twice: %r', anchor_name)
            else:
                self.target_lookup_items.setdefault(
                    anchor_name, TargetLookupItem())

    def lookup_target(self, anchor_token, source_box, css_token, parse_again):
        """Get a TargetLookupItem corresponding to ``anchor_token``.

        If it is already filled by a previous anchor-element, the status is
        'up-to-date'. Otherwise, it is 'pending', we must parse the whole
        tree again.

        """
        anchor_name = self.anchor_name_from_token(anchor_token)
        item = self.target_lookup_items.get(
            anchor_name, TargetLookupItem('undefined'))

        if item.state == 'pending':
            self.had_pending_targets = True
            item.parse_again_functions.setdefault(
                (source_box, css_token), parse_again)

        if item.state == 'undefined':
            LOGGER.error(
                'Content discarded: target points to undefined anchor %r',
                anchor_token)

        return item

    def store_target(self, anchor_name, target_counter_values, target_box):
        """Store a target called ``anchor_name``.

        If there is a pending TargetLookupItem, it is updated. Only previously
        collected anchors are stored.

        """
        item = self.target_lookup_items.get(anchor_name)
        if item and item.state == 'pending':
            item.state = 'up-to-date'
            item.target_box = target_box
            # Store the counter_values in the target_box like
            # compute_content_list does.
            # TODO: remove attribute or set a default value in Box class
            if not hasattr(target_box, 'cached_counter_values'):
                target_box.cached_counter_values = copy.deepcopy(
                    target_counter_values)

    def collect_missing_counters(self, parent_box, css_token,
                                 parse_again_function, missing_counters,
                                 missing_target_counters):
        """Collect missing (probably page-based) counters during formatting.

        The ``missing_counters`` are re-used during pagination.

        The ``missing_link`` attribute added to the parent_box is required to
        connect the paginated boxes to their originating ``parent_box``.

        """
        # No counter collection during pagination
        if not self.collecting:
            return

        # No need to add empty miss-lists
        if missing_counters or missing_target_counters:
            # TODO: remove attribute or set a default value in Box class
            if not hasattr(parent_box, 'missing_link'):
                parent_box.missing_link = parent_box
            counter_lookup_item = CounterLookupItem(
                parse_again_function, missing_counters,
                missing_target_counters)
            self.counter_lookup_items.setdefault(
                (parent_box, css_token), counter_lookup_item)

    def check_pending_targets(self):
        """Check pending targets if needed."""
        if self.had_pending_targets:
            for item in self.target_lookup_items.values():
                for function in item.parse_again_functions.values():
                    function()
            self.had_pending_targets = False
        # Ready for pagination
        self.collecting = False

    def cache_target_page_counters(self, anchor_name, page_counter_values,
                                   page_maker_index, page_maker):
        """Store target's current ``page_maker_index`` and page counter values.

        Eventually update associated targeting boxes.

        """
        # Only store page counters when paginating
        if self.collecting:
            return

        item = self.target_lookup_items.get(anchor_name)
        if item and item.state == 'up-to-date':
            item.page_maker_index = page_maker_index
            if item.cached_page_counter_values != page_counter_values:
                item.cached_page_counter_values = copy.deepcopy(
                    page_counter_values)

                # Spread the news: update boxes affected by a change in the
                # anchor's page counter values.
                for (_, css_token), item in self.counter_lookup_items.items():
                    # Only update items that need counters in their content
                    if css_token != 'content':
                        continue

                    # Don't update if item has no missing target counter
                    missing_counters = item.missing_target_counters.get(
                        anchor_name)
                    if missing_counters is None:
                        continue

                    # Pending marker for remake_page
                    if (item.page_maker_index is None or
                            item.page_maker_index >= len(page_maker)):
                        item.pending = True
                        continue

                    # TODO: Is the item at all interested in the new
                    # page_counter_values? It probably is and this check is a
                    # brake.
                    for counter_name in missing_counters:
                        counter_value = page_counter_values.get(counter_name)
                        if counter_value is not None:
                            remake_state = (
                                page_maker[item.page_maker_index][-1])
                            remake_state['content_changed'] = True
                            item.parse_again(item.cached_page_counter_values)
                            break
                    # Hint: the box's own cached page counters trigger a
                    # separate 'content_changed'.
