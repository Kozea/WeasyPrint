"""Test CSS errors and warnings."""

import pytest

from weasyprint import CSS

from ..testing_utils import assert_no_logs, capture_logs, render_pages


@assert_no_logs
@pytest.mark.parametrize('source, messages', (
    (':lipsum { margin: 2cm', ['WARNING: Invalid or unsupported selector']),
    ('::lipsum { margin: 2cm', ['WARNING: Invalid or unsupported selector']),
    ('foo { margin-color: red', ['WARNING: Ignored', 'unknown property']),
    ('foo { margin-top: red', ['WARNING: Ignored', 'invalid value']),
    ('@import "relative-uri.css"',
     ['ERROR: Relative URI reference without a base URI']),
    ('@import "invalid-protocol://absolute-URL"',
     ['ERROR: Failed to load stylesheet at']),
))
def test_warnings(source, messages):
    with capture_logs() as logs:
        CSS(string=source)
    assert len(logs) == 1, source
    for message in messages:
        assert message in logs[0]


@assert_no_logs
def test_warnings_stylesheet():
    with capture_logs() as logs:
        render_pages('<link rel=stylesheet href=invalid-protocol://absolute>')
    assert len(logs) == 1
    assert 'ERROR: Failed to load stylesheet at' in logs[0]


@assert_no_logs
@pytest.mark.parametrize('style', (
    '<style> html { color red; color: blue; color',
    '<html style="color; color: blue; color red">',
))
def test_error_recovery(style):
    with capture_logs() as logs:
        page, = render_pages(style)
        html, = page.children
        assert html.style['color'] == (0, 0, 1, 1)  # blue
    assert len(logs) == 2
