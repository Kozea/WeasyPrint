"""
    weasyprint.tests.testing_utils
    ------------------------------

    Helpers for tests.

"""

import contextlib
import functools
import logging
import os.path
import sys
import threading
import wsgiref.simple_server

import pytest

from .. import CSS, HTML, text
from ..logger import LOGGER
from ..urls import path2url

# Lists of fonts with many variants (including condensed)
if sys.platform.startswith('win'):  # pragma: no cover
    SANS_FONTS = 'DejaVu Sans, Arial Nova, Arial, sans'
    MONO_FONTS = 'Courier New, Courier, monospace'
else:  # pragma: no cover
    SANS_FONTS = 'DejaVu Sans, sans'
    MONO_FONTS = 'DejaVu Sans Mono, monospace'

TEST_UA_STYLESHEET = CSS(filename=os.path.join(
    os.path.dirname(__file__), '..', 'css', 'tests_ua.css'
))


class FakeHTML(HTML):
    """Like weasyprint.HTML, but with a lighter UA stylesheet."""
    def _ua_stylesheets(self):
        return [TEST_UA_STYLESHEET]


def resource_filename(basename):
    """Return the absolute path of the resource called ``basename``."""
    return os.path.join(os.path.dirname(__file__), 'resources', basename)


# Dummy filename, but in the right directory.
BASE_URL = path2url(resource_filename('<test>'))


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
        if record.name == 'weasyprint.progress':
            return
        message = '%s: %s' % (record.levelname.upper(), record.getMessage())
        messages.append(message)

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
                if logs:  # pragma: no cover
                    for message in logs:
                        print(message, file=sys.stderr)
                    raise AssertionError('%i errors logged' % len(logs))
    return wrapper


@contextlib.contextmanager
def http_server(handlers):
    def wsgi_app(environ, start_response):
        handler = handlers.get(environ['PATH_INFO'])
        if handler:
            status = str('200 OK')
            response, headers = handler(environ)
            headers = [(str(name), str(value)) for name, value in headers]
        else:  # pragma: no cover
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


def requires(library_name, expected_tuple):
    library = getattr(text, library_name)
    library_version = '%06i' % getattr(library, '%s_version' % library_name)()
    library_tuple = tuple(int(i) for i in (
        library_version[:2], library_version[2:4], library_version[4:]))
    return pytest.mark.skipif(
        library_tuple < expected_tuple,
        reason='Running %s %s but this test requires %s+' % (
            library_name, '%i.%i.%i' % library_tuple,
            '%i.%i.%i' % expected_tuple))
