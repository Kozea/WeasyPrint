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
from ..document import PNGDocument
from ..css import PARSER
from ..logger import LOGGER


# TODO: find a way to not depend on a specific font
FONTS = 'Liberation Sans, Arial'

TEST_UA_STYLESHEET = CSS(os.path.join(
    os.path.dirname(__file__), '..', 'css', 'tests_ua.css'
))


class TestPNGDocument(PNGDocument):
    """Like PNGDocument, but with a different user-agent stylesheet.

    This stylesheet is shorter, which makes tests faster.

    """
    def __init__(self, html_source, base_url=None, user_stylesheets=()):
        super(TestPNGDocument, self).__init__(
            HTML(string=html_source, base_url=base_url).root_element,
            user_stylesheets=user_stylesheets,
            user_agent_stylesheets=[TEST_UA_STYLESHEET])


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
    loggers = [LOGGER, logging.getLogger('CSSUTILS')]
    previous_handlers = []
    messages = []

    def emit(record):
        message = '%s: %s' % (record.levelname.upper(), record.getMessage())
        messages.append(message)
        print(message, file=sys.stderr)

    for logger in loggers:
        previous_handlers.append((logger, logger.handlers))
        logger.handlers = []
        logger.addHandler(CallbackHandler(emit))
    try:
        yield messages
    finally:
        for logger, handlers in previous_handlers:
            logger.handlers = handlers


def assert_no_logs(function):
    """Decorator that asserts that nothing is logged in a function."""
    @functools.wraps(function)
    def wrapper():
        with capture_logs() as logs:
            try:
                function()
            except Exception:  # pragma: no cover
                if logs:
                    print('%i errors logged:' % len(logs), file=sys.stderr)
                raise
            else:
                assert len(logs) == 0, '%i errors logged:' % len(logs)
    return wrapper
