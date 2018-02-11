"""
    weasyprint.formatting_structure.targets
    -------------------------------------

    An attempt to implement target-counter, target-counters and target-text

    The TARGET_COLLECTOR is a structure providing required targets'
    counter_values and stuff needed to build PENDING targets later,
    when all targetted anchors have been 'layouted'

    :copyright: Copyright 2018 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import copy  # deepcopy needed!
from ..logger import LOGGER

# not shure what's the Python way  to create consts, maybe a namedtuple?
# thx [Jon Betts](https://stackoverflow.com/a/23274028)
class _STATE(object):
    """constants for target states"""
    PENDING        = 0
    UPTODATE       = 1
    UNDEFINED      = 2
    __stateToName = {
        PENDING        : 'PENDING',
        UPTODATE       : 'UPTODATE',
        UNDEFINED      : 'UNDEFINED',
    }
    def __setattr__(self, *_):
        """prohibit changes"""
        pass
    def name(self, state):
        """ return human readable state-name"""
        return self.__stateToName.get(state, 'Invalid state')

TARGET_STATE = _STATE()

class TargetLookupItem(object):
    """item collected by the TargetColector"""

    def __init__(self, state=TARGET_STATE.PENDING):
        self.state = state
        # required by target-counter and target-counters
        self.target_counter_values = {}
        # neede for target-text via TEXT_CONTENT_EXTRACTORS
        self.target_box = None
        # stuff for PENDING targets
        self.pending_boxes = {}

class _TargetCollector(object):
    """collect and provide stuff for css content with `target-*`"""

    def __init__(self):
        self.reset()

    def reset(self):
        self.had_peding_targets = False
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
                LOGGER.warning('  ! anchor redefined: %s', anchor_name)
            else:
                self.existing_anchors.append(anchor_name)
                LOGGER.debug('  + anchor added: "%s" ', anchor_name)


    def collect_computed_target(self, anchor_name):
        """
        stores a `computed` target's (internal!) anchor name,
        verified by computed_values.content()

        anchor_name without '#' and already unquoted
        """
        if anchor_name and isinstance(anchor_name, str):
            self._addtarget(anchor_name)


    def verify_collection(self):
        """obsolete function, only needed for testing"""
        LOGGER.debug('------- collected targets -------------')
        for key, item in self.items.items():
            # mark target names not in existing_anchors as UNDEFINED
            if not key in self.existing_anchors:
               item.state = TARGET_STATE.UNDEFINED
            LOGGER.debug(key, TARGET_STATE.name(item.state))
        LOGGER.debug('------- existing anchors -------------')
        LOGGER.debug(self.existing_anchors)


    def lookup_target(self, anchor_name, source_box, parse_again_function):
        """ called in content_to_boxes() when the source_box needs a target-*
        returns a TargetLookupItem
        if already filled by a previous anchor-element: UPDTODATE
        else: PENDING, we must parse the whole thing again
        """
        item = self.items.get(anchor_name, TargetLookupItem(TARGET_STATE.UNDEFINED))
        LOGGER.debug('lookup_target', anchor_name, TARGET_STATE.name(item.state) )
        if item.state == TARGET_STATE.PENDING:
            if not anchor_name in self.existing_anchors:
                item.state = TARGET_STATE.UNDEFINED
            else:
                self.had_peding_targets = True
                LOGGER.debug('   -> still pending. Keep infos.')
                item.pending_boxes.setdefault(source_box, parse_again_function)

        if item.state == TARGET_STATE.UNDEFINED:
            LOGGER.error('content discarded: target points to undefined anchor "%s"', anchor_name)
            # feedback to invoker: discard the parent_box
            # at the moment it's `build.before_after_to_box()` which cares
            source_box.style['content'] = 'none'
        return item

    def store_target(self, anchor_name, target_counter_values, target_box):
        """
        called by every anchor-element in build.element_to_box
        if there is a PENDING TargetLookupItem, it is updated
        only previously collected anchor_names are stored
        """
        item = self.items.get(anchor_name, None)
        if item:
            LOGGER.debug('store_target?' , anchor_name,  TARGET_STATE.name(item.state) )
            if item.state == TARGET_STATE.PENDING:
                LOGGER.debug('   -> update:', target_counter_values)
                # need A REAL DUPLICATE UNCONNECTED SEPARATE COPY!!
                item.state = TARGET_STATE.UPTODATE
                item.target_counter_values = copy.deepcopy(target_counter_values);
                item.target_box = target_box
            else:
                LOGGER.debug('   -> duplicate anchor definition: %s' % anchor_name)
        else:
            LOGGER.debug('    -> achor %s not targetted' % anchor_name)

    def check_peding_targets(self):
        if not self.had_peding_targets:
            return
        LOGGER.info('Step 4.3 Reparsing pending targets')
        self.had_peding_targets = False
        for key, item in self.items.items():
            # create the pending content boxes NOW
            # UNDEFINED items never hava a `parse_again` function
            for abox, func in item.pending_boxes.items():
                func()


TARGET_COLLECTOR = _TargetCollector()

