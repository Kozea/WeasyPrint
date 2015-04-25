# coding: utf8
"""
    weasyprint.tests.testing_utils
    ------------------------------

    Helpers for tests.

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals, print_function

import sys
import os.path
import logging
import contextlib
import functools
import wsgiref.simple_server
import threading
import shutil
import tempfile

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
                if logs:
                    for message in logs:
                        print(message, file=sys.stderr)
                    raise AssertionError('%i errors logged' % len(logs))
    return wrapper


def almost_equal(a, b):
    if (isinstance(a, list) and isinstance(b, list)
            or isinstance(a, tuple) and isinstance(b, tuple)):
        return len(a) == len(b) and all(
            almost_equal(aa, bb) for aa, bb in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        return round(abs(a - b), 6) == 0
    return a == b


@contextlib.contextmanager
def http_server(handlers):
    def wsgi_app(environ, start_response):
        handler = handlers.get(environ['PATH_INFO'])
        if handler:
            status = str('200 OK')
            response, headers = handler(environ)
            headers = [(str(name), str(value)) for name, value in headers]
        else:
            status = str('404 Not Found')
            response = b''
            headers = []
        start_response(status, headers)
        return [response]

    # Port 0: let the OS pick an available port number
    # http://stackoverflow.com/a/1365284/1162888
    server = wsgiref.simple_server.make_server('127.0.0.1', 0, wsgi_app)
    _host, port = server.socket.getsockname()
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        yield 'http://127.0.0.1:%s' % port
    finally:
        server.shutdown()
        thread.join()


@contextlib.contextmanager
def temp_directory():
    """Context manager that gives the path to a new temporary directory.

    Remove everything on exiting the context.

    """
    directory = tempfile.mkdtemp()
    try:
        yield directory
    finally:
        shutil.rmtree(directory)
