# coding: utf8
"""
    weasyprint.logging
    ------------------

    Logging setup.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import logging


LOGGER = logging.getLogger('weasyprint')

# Default to logging to stderr.
LOGGER.addHandler(logging.StreamHandler())
LOGGER.setLevel(logging.INFO)
