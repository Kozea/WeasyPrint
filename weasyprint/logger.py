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

import contextlib
import logging

LOGGER = logging.getLogger('weasyprint')
if not LOGGER.handlers:  # pragma: no cover
    LOGGER.setLevel(logging.WARNING)
    LOGGER.addHandler(logging.NullHandler())

PROGRESS_LOGGER = logging.getLogger('weasyprint.progress')


class CallbackHandler(logging.Handler):
    """A logging handler that calls a function for every message."""
    def __init__(self, callback):
        logging.Handler.__init__(self)
        self.emit = callback


@contextlib.contextmanager
def capture_logs(logger='weasyprint', level=None):
    """Return a context manager that captures all logged messages."""
    if level is None:
        level = logging.INFO
    logger = logging.getLogger(logger)
    messages = []

    def emit(record):
        if record.name == 'weasyprint.progress':
            return
        if record.levelno < level:
            return
        messages.append(f'{record.levelname.upper()}: {record.getMessage()}')

    previous_handlers = logger.handlers
    previous_level = logger.level
    logger.handlers = []
    logger.addHandler(CallbackHandler(emit))
    logger.setLevel(logging.DEBUG)
    try:
        yield messages
    finally:
        logger.handlers = previous_handlers
        logger.level = previous_level
