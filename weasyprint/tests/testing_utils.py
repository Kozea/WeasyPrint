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
from ..document import Document
from ..logger import LOGGER
from ..urls import default_url_fetcher


# TODO: find a way to not depend on a specific font
FONTS = 'Liberation Sans, Arial'

TEST_UA_STYLESHEET = CSS(os.path.join(
    os.path.dirname(__file__), '..', 'css', 'tests_ua.css'
))


class TestPNGDocument(Document):
    """A Document with a PNG backend and a different user-agent stylesheet.

    This stylesheet is shorter, which makes tests faster.

    """
    enable_hinting = True

    def __init__(self, html_source, base_url=None, user_stylesheets=(),
                 user_agent_stylesheets=(TEST_UA_STYLESHEET,)):
        super(TestPNGDocument, self).__init__(
            HTML(string=html_source, base_url=base_url).root_element,
            enable_hinting=self.enable_hinting,
            url_fetcher=default_url_fetcher,
            user_stylesheets=user_stylesheets,
            user_agent_stylesheets=user_agent_stylesheets)


class TestPDFDocument(TestPNGDocument):
    """A Document with a PDF backend and a different user-agent stylesheet.

    This stylesheet is shorter, which makes tests faster.

    """
    enable_hinting = False


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
        print(message, file=sys.stderr)

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
