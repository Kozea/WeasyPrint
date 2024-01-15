"""Test urls."""
import re

from .testing_utils import FakeHTML, resource_path, capture_logs


def test_malformed_url_link():
    """Test malformed URLs that contain a [ or ] character, which can be confused with a malformed IPv6 URL"""
    with capture_logs() as logs:
        pdf = FakeHTML(string='''
          <p><a href="https://weasyprint.org]">My Link</a></p>
        ''', base_url=resource_path('<inline HTML>')).write_pdf()

        assert len(logs) == 1
        assert "Malformed URL" in logs[0]

        uris = re.findall(b'/URI \\((.*)\\)', pdf)
        types = re.findall(b'/S (/\\w*)', pdf)
        subtypes = re.findall(b'/Subtype (/\\w*)', pdf)

        # 30pt wide (like the image), 20pt high (like line-height)
        assert uris.pop(0) == b'https://weasyprint.org]'
        assert subtypes.pop(0) == b'/Link'
        assert types.pop(0) == b'/URI'
