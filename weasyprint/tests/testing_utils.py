# coding: utf8

#  WeasyPrint converts web documents (HTML, CSS, ...) to PDF.
#  Copyright (C) 2011  Simon Sapin
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

import sys
import os.path
import logging
import contextlib

from cssutils import parseFile
from attest import assert_hook

from ..document import PNGDocument

# TODO: find a way to not depend on a specific font
FONTS = u"Liberation Sans, Arial"
TEST_USER_AGENT_STYLESHEETS = (
    parseFile(os.path.join(
        os.path.dirname(__file__), '..', 'css', 'tests_ua.css'
    )),
)


class TestPNGDocument(PNGDocument):
    """Like PNGDocument, but with a different user-agent stylesheet.

    This stylesheet is shorter, which makes tests faster.

    """
    def __init__(self, dom, user_stylesheets=None,
                 user_agent_stylesheets=TEST_USER_AGENT_STYLESHEETS):
        super(TestPNGDocument, self).__init__(
            dom, user_stylesheets, user_agent_stylesheets)


def resource_filename(basename):
    """Return the absolute path of the resource called ``basename``."""
    return os.path.join(os.path.dirname(__file__), 'resources', basename)


class CallbackHandler(logging.Handler):
    """A logging handler that calls a function for every message."""
    def __init__(self, callback):
        super(CallbackHandler, self).__init__()
        self.emit = callback


@contextlib.contextmanager
def capture_logs(logger_names=('WEASYPRINT', 'CSSUTILS')):
    """Return a context manager that captures all logged messages."""
    previous_handlers = []
    messages = []

    def emit(record):
        messages.append('%s: %s' % (record.levelname.upper(),
                                    record.getMessage()))

    for name in set(logger_names):
        logger = logging.getLogger(name)
        previous_handlers.append((logger, logger.handlers))
        logger.handlers = []
        logger.addHandler(CallbackHandler(emit))
    try:
        yield messages
    finally:
        for logger, handlers in previous_handlers:
            logger.handlers = handlers


def assert_no_logs():
    """
    When passed to ``attest.Tests.context()``, asserts that nothing is logged.
    """
    with capture_logs() as logs:
        try:
            yield
        except:
            if logs:
                sys.stderr.write('%i errors logged:\n%s\n' % (
                    len(logs), '\n'.join(logs)))
            raise
        else:
            # The assert hook prints the log.
            assert not logs, ('%i errors logged' % len(logs))
