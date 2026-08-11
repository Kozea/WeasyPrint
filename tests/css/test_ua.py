"""Test the user-agent stylesheet."""

import pytest

from weasyprint.html import CSS, PH, UA, UA_FORM

from ..testing_utils import assert_no_logs


@assert_no_logs
@pytest.mark.parametrize('css', [UA, UA_FORM, PH])
def test_ua_stylesheets(css):
    CSS(string=css)
