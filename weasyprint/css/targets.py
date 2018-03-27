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
        self.reset()

    def reset(self):
        self.had_pending_targets = False
        self.existing_anchors = []
        self.items = {}

    def _addtarget(self, anchor_name):
        return self.items.setdefault(anchor_name, TargetLookupItem())

    def collect_anchor(self, anchor_name):
        """
        stores `anchor_name` in `existing_anchors`
        should be called by computed_values.anchor()
        """
        if anchor_name and isinstance(anchor_name, str):
            if anchor_name in self.existing_anchors:
                LOGGER.warning('Anchor defined twice: %s', anchor_name)
            else:
                self.existing_anchors.append(anchor_name)

    def collect_computed_target(self, anchor_name):
        """
        stores a `computed` target's (internal!) anchor name,
        verified by computed_values.content()

        anchor_name without '#' and already unquoted
        """
        if anchor_name and isinstance(anchor_name, str):
            self._addtarget(anchor_name)

    def lookup_target(self, anchor_name, source_box, parse_again_function):
        """ called in content_to_boxes() when the source_box needs a target-*
        returns a TargetLookupItem
        if already filled by a previous anchor-element: up-to-date
        else: pending, we must parse the whole thing again
        """
        item = self.items.get(
            anchor_name,
            TargetLookupItem('undefined'))
        if item.state == 'pending':
            if anchor_name not in self.existing_anchors:
                item.state = 'undefined'
            else:
                self.had_pending_targets = True
                item.pending_boxes.setdefault(source_box, parse_again_function)

        if item.state == 'undefined':
            LOGGER.error(
                'content discarded: target points to undefined anchor "%s"',
                anchor_name)
            # feedback to invoker: discard the parent_box
            # at the moment it's `build.before_after_to_box()` which cares
            source_box.style['content'] = 'none'
        return item

    def store_target(self, anchor_name, target_counter_values, target_box):
        """
        called by every anchor-element in build.element_to_box
        if there is a pending TargetLookupItem, it is updated
        only previously collected anchor_names are stored
        """
        item = self.items.get(anchor_name, None)
        if item and item.state == 'pending':
            item.state = 'up-to-date'
            item.target_counter_values = copy.deepcopy(target_counter_values)
            item.target_box = target_box

    def check_pending_targets(self):
        if not self.had_pending_targets:
            return
        self.had_pending_targets = False
        for key, item in self.items.items():
            for _, function in item.pending_boxes.items():
                function()
