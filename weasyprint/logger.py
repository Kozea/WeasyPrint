"""Logging setup.

The rest of the code gets the logger through this module rather than
``logging.getLogger`` to make sure that it is configured.

Logging levels are used for specific purposes:

- errors are used in ``LOGGER`` for unreachable or unusable external resources,
  including unreachable stylesheets, unreachables images and unreadable images;
- warnings are used in ``LOGGER`` for unknown or bad HTML/CSS syntaxes,
  unreachable local fonts and various non-fatal problems;
- infos are used in ``PROCESS_LOGGER`` to advertise rendering steps.

"""

import logging

LOGGER = logging.getLogger('weasyprint')
if not LOGGER.handlers:  # pragma: no cover
    LOGGER.setLevel(logging.WARNING)
    LOGGER.addHandler(logging.NullHandler())

PROGRESS_LOGGER = logging.getLogger('weasyprint.progress')
