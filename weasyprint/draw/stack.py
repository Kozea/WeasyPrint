"""Drawing stack context manager."""

from contextlib import contextmanager


@contextmanager
def stacked(stream):
    """Save and restore stream context when used with the ``with`` keyword."""
    stream.push_state()
    try:
        yield
    finally:
        stream.pop_state()
