"""Test URLs."""

import re

import pytest

from .testing_utils import BASE_URL, FakeHTML, assert_no_logs, capture_logs


@pytest.mark.parametrize(('url', 'base_url'), [
    ('https://weasyprint.org]', BASE_URL),
    ('https://weasyprint.org]', 'https://weasyprint.org]'),
    ('https://weasyprint.org/', 'https://weasyprint.org]'),
])
def test_malformed_url_link(url, base_url):
    """Test malformed URLs."""
    with capture_logs() as logs:
        pdf = FakeHTML(
            string=f'<p><a href="{url}">My Link</a></p>',
            base_url=base_url).write_pdf()

    assert len(logs) == 1
    assert 'Malformed' in logs[0]
    assert ']' in logs[0]

    uris = re.findall(b'/URI \\((.*)\\)', pdf)
    types = re.findall(b'/S (/\\w*)', pdf)
    subtypes = re.findall(b'/Subtype (/\\w*)', pdf)

    assert uris.pop(0) == url.encode()
    assert subtypes.pop(0) == b'/Link'
    assert types.pop(0) == b'/URI'


@assert_no_logs
@pytest.mark.parametrize('whitespace', ['\t', '\n', '\r\n'])
def test_html_url_whitespace(whitespace):
    """Test HTML whitespace in URLs."""
    pdf = FakeHTML(string=(
        f'<a href=" \t\nhttps://weasyprint.org/foo{whitespace}bar\r\n ">'
        'My Link</a>')).write_pdf()

    assert re.findall(b'/URI \\((.*)\\)', pdf) == [
        b'https://weasyprint.org/foobar']


@assert_no_logs
def test_html_base_url_whitespace():
    """Test HTML whitespace in the base URL."""
    pdf = FakeHTML(string='''
        <base href=" https://weasyprint.org/foo\nbar/ ">
        <a href="baz">My Link</a>
    ''').write_pdf()

    assert re.findall(b'/URI \\((.*)\\)', pdf) == [
        b'https://weasyprint.org/foobar/baz']


@assert_no_logs
def test_base_url_in_var():
    # Regression test for #2789.
    FakeHTML(
        string='<p style="--b: url(pattern.png); background-image: var(--b)">',
        base_url=BASE_URL).write_pdf()
