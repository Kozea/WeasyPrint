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
    """Item collected by the TargetColector."""

    def __init__(self, state='pending'):
        self.state = state
        # required by target-counter and target-counters
        self.target_counter_values = {}
        # needed for target-text via TEXT_CONTENT_EXTRACTORS
        self.target_box = None
        # stuff for pending targets
        self.pending_boxes = {}


class TargetCollector(object):
    """Collector of HTML targets used by CSS content with ``target-*``."""

    def __init__(self):
        self.had_pending_targets = False
        self.existing_anchors = []
        self.items = {}

    def collect_anchor(self, anchor_name):
        """Store ``anchor_name`` in ``existing_anchors``."""
        if anchor_name and isinstance(anchor_name, str):
            if anchor_name in self.existing_anchors:
                LOGGER.warning('Anchor defined twice: %s', anchor_name)
            else:
                self.existing_anchors.append(anchor_name)

    def collect_computed_target(self, anchor_name):
        """Store a computed internal target's ``anchor_name``.

        ``anchor_name`` must not start with '#' and be already unquoted.

        """
        if anchor_name and isinstance(anchor_name, str):
            self.items.setdefault(anchor_name, TargetLookupItem())

    def lookup_target(self, anchor_name, source_box, parse_again_function):
        """Get a TargetLookupItem corresponding to ``anchor_name``.

        If it is already filled by a previous anchor-element, the status is
        'up-to-date'. Otherwise, it is 'pending', we must parse the whole
        tree again.

        """
        item = self.items.get(anchor_name, TargetLookupItem('undefined'))

        if item.state == 'pending':
            if anchor_name in self.existing_anchors:
                self.had_pending_targets = True
                item.pending_boxes.setdefault(source_box, parse_again_function)
            else:
                item.state = 'undefined'

        if item.state == 'undefined':
            LOGGER.error(
                'Content discarded: target points to undefined anchor "%s"',
                anchor_name)

        return item

    def store_target(self, anchor_name, target_counter_values, target_box):
        """Store a target called ``anchor_name``.

        If there is a pending TargetLookupItem, it is updated. Only previously
        collected anchors are stored.

        """
        item = self.items.get(anchor_name)
        if item and item.state == 'pending':
            item.state = 'up-to-date'
            item.target_counter_values = copy.deepcopy(target_counter_values)
            item.target_box = target_box

    def check_pending_targets(self):
        """Check pending targets if needed."""
        if not self.had_pending_targets:
            return
        for key, item in self.items.items():
            for _, function in item.pending_boxes.items():
                function()
        self.had_pending_targets = False
