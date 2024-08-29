"""Test the UrlFetcher class"""

import pytest
from urllib.request import pathname2url
import os

from weasyprint.urls import UrlFetcher


@pytest.mark.parametrize('url, allowed_schemes', (
    ('http://weasyprint.org/', ('https',)),
    ('file:///etc/passwd', ('http', 'https',)),
))
def test_forbidden_scheme(url, allowed_schemes):
    fetcher = UrlFetcher(allowed_schemes=allowed_schemes)
    with pytest.raises(ValueError):
        fetcher.validate(url)


@pytest.mark.parametrize('url, allowed_schemes', (
    ('http://weasyprint.org/', ('http', 'https')),
    ('https://weasyprint.org/', ('http', 'https')),
    ('https://weasyprint.org/', ('https',)),
    ('https://weasyprint.org/', None),
    ('file:///home/me/my_photo.jpg', ('http', 'https', 'file')),
))
def test_allowed_scheme(url, allowed_schemes):
    fetcher = UrlFetcher(allowed_schemes=allowed_schemes)
    assert fetcher.validate(url) == url


@pytest.mark.parametrize('url, allowed_domains', (
    ('https://evil.net/', ('weasyprint.org',)),
))
def test_forbidden_domain(url, allowed_domains):
    fetcher = UrlFetcher(allowed_domains=allowed_domains)
    with pytest.raises(ValueError):
        fetcher.validate(url)


@pytest.mark.parametrize('url, allowed_domains', (
    ('https://weasyprint.org/', ('weasyprint.org',)),
    ('https://weasyprint.org/', ('weasyprint.org', 'example.com')),
    ('https://example.com/', ('weasyprint.org', 'example.com')),
    ('https://weasyprint.org/', None),
))
def test_allowed_domain(url, allowed_domains):
    fetcher = UrlFetcher(allowed_domains=allowed_domains)
    assert fetcher.validate(url) == url


def test_fetch_https():
    fetcher = UrlFetcher(allowed_domains=('weasyprint.org',), allowed_schemes=('https',))
    result = fetcher('https://weasyprint.org/css/img/logotype-black.svg')
    assert 'string' in result or 'file_obj' in result


def test_fetch_file():
    fetcher = UrlFetcher(allowed_schemes=('file',))
    result = fetcher('file://%s' % pathname2url(os.path.abspath('./resources/icon.png')))
    assert 'string' in result or 'file_obj' in result
    