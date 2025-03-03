"""Test the user-agent stylesheet."""

import pytest

from weasyprint.html import CSS, HTML5_PH, HTML5_UA, HTML5_UA_FORM

from ..testing_utils import assert_no_logs


@assert_no_logs
@pytest.mark.parametrize('css', (HTML5_UA, HTML5_UA_FORM, HTML5_PH))
def test_ua_stylesheets(css):
    CSS(string=css)
