# coding: utf8

#  WeasyPrint converts web documents (HTML, CSS, ...) to PDF.
#  Copyright (C) 2011-2012 Simon Sapin and contributors.
#  See AUTHORS for more details.
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
WeasyPrint testing suite.

"""

from __future__ import division, unicode_literals, print_function

import sys
import os.path
import logging
import contextlib
import functools

from .. import HTML
from ..document import PNGDocument
from ..css import PARSER as CSS_PARSER
from ..logger import LOGGER

# TODO: find a way to not depend on a specific font
FONTS = 'Liberation Sans, Arial'

TEST_UA_STYLESHEET = CSS_PARSER.parseFile(os.path.join(
    os.path.dirname(__file__), '..', 'css', 'tests_ua.css'
))


class TestPNGDocument(PNGDocument):
    """Like PNGDocument, but with a different user-agent stylesheet.

    This stylesheet is shorter, which makes tests faster.

    """
    def __init__(self, html_source, base_url=None):
        super(TestPNGDocument, self).__init__(
            HTML(string=html_source, base_url=base_url).root_element,
            user_stylesheets=[],
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
            except Exception:
                if logs:
                    print('%i errors logged:' % len(logs), file=sys.stderr)
                raise
            else:
                assert len(logs) == 0, '%i errors logged:' % len(logs)
    return wrapper
