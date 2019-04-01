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

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import logging

LOGGER = logging.getLogger('weasyprint')
if not LOGGER.handlers:
    LOGGER.setLevel(logging.WARNING)
    LOGGER.addHandler(logging.NullHandler())

PROGRESS_LOGGER = logging.getLogger('weasyprint.progress')
