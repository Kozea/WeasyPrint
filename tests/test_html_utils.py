"""Tests for HTML microsyntax parsing utilities."""

from weasyprint.html_utils import parse_html_integer


def test_parse_html_integer_basic():
    assert parse_html_integer('42') == 42
    assert parse_html_integer('0') == 0
    assert parse_html_integer('100') == 100


def test_parse_html_integer_sign():
    assert parse_html_integer('+123') == 123
    assert parse_html_integer('-42') == -42
    assert parse_html_integer('+0') == 0
    assert parse_html_integer('-0') == 0


def test_parse_html_integer_leading_whitespace():
    assert parse_html_integer('  42') == 42
    assert parse_html_integer('\t7') == 7
    assert parse_html_integer(' \n -5') == -5
    assert parse_html_integer('   +0') == 0


def test_parse_html_integer_trailing_non_digits():
    assert parse_html_integer('100%') == 100
    assert parse_html_integer('42px') == 42
    assert parse_html_integer('100,000') == 100
    assert parse_html_integer('3.14') == 3
    assert parse_html_integer('23.4') == 23


def test_parse_html_integer_error_cases():
    assert parse_html_integer('') is None
    assert parse_html_integer('   ') is None
    assert parse_html_integer('abc') is None
    assert parse_html_integer('+') is None
    assert parse_html_integer('-') is None
    assert parse_html_integer('+ 1') is None


def test_parse_html_integer_non_ascii_digits():
    # Python's isdigit() matches non-ASCII digits, but the HTML spec
    # requires ASCII digits only.
    assert parse_html_integer('\u0660\u0661') is None  # Arabic-Indic digits
    # ASCII digits followed by non-ASCII digit: stops at non-ASCII
    assert parse_html_integer('3\u0660') == 3
