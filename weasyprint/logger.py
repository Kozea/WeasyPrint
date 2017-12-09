# coding: utf-8
"""
    weasyprint.logging
    ------------------

    Logging setup.

    The rest of the code gets the logger through this module rather than
    ``logging.getLogger`` to make sure that it is configured.

    Logging levels are used for specific purposes:

    - errors are used for unreachable or unusable external resources, including
      unreachable stylesheets, unreachables images and unreadable images;
    - warnings are used for unknown or bad HTML/CSS syntaxes, unreachable local
      fonts and various non-fatal problems;
    - infos are used to advertise rendering steps.

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import logging

LOGGER = logging.getLogger('weasyprint')
LOGGER.setLevel(logging.WARNING)
LOGGER.addHandler(logging.NullHandler())
