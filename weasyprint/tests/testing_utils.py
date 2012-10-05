# coding: utf8
"""
    weasyprint.tests.testing_utils
    ------------------------------

    Helpers for tests.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals, print_function

import sys
import os.path
import logging
import contextlib
import functools

from .. import HTML, CSS
from ..logger import LOGGER


# TODO: find a way to not depend on a specific font
FONTS = 'Liberation Sans, Arial'

TEST_UA_STYLESHEET = CSS(filename=os.path.join(
    os.path.dirname(__file__), '..', 'css', 'tests_ua.css'
))


class TestHTML(HTML):
    """Like weasyprint.HTML, but with a lighter UA stylesheet."""
    def _ua_stylesheets(self):
        return [TEST_UA_STYLESHEET]


def resource_filename(basename):
    """Return the absolute path of the resource called ``basename``."""
    return os.path.join(os.path.dirname(__file__), 'resources', basename)


class CallbackHandler(logging.Handler):
    """A logging handler that calls a function for every message."""
    def __init__(self, callback):
        logging.Handler.__init__(self)
        self.emit = callback


@contextlib.contextmanager
def capture_logs():
    """Return a context manager that captures all logged messages."""
    logger = LOGGER
    messages = []

    def emit(record):
        message = '%s: %s' % (record.levelname.upper(), record.getMessage())
        messages.append(message)

    previous_handlers = logger.handlers
    logger.handlers = []
    logger.addHandler(CallbackHandler(emit))
    try:
        yield messages
    finally:
        logger.handlers = previous_handlers


def assert_no_logs(function):
    """Decorator that asserts that nothing is logged in a function."""
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        with capture_logs() as logs:
            try:
                function(*args, **kwargs)
            except Exception:  # pragma: no cover
                if logs:
                    print('%i errors logged:' % len(logs), file=sys.stderr)
                    for message in logs:
                        print(message, file=sys.stderr)
                raise
            else:
                assert len(logs) == 0, '%i errors logged:' % len(logs)
                for message in logs:
                    print(message, file=sys.stderr)
    return wrapper
