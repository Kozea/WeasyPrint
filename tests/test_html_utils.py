"""Tests for HTML microsyntax parsing utilities."""

from weasyprint.html_utils import is_ascii_digits


def test_is_ascii_digits_basic():
    assert is_ascii_digits('123')
    assert is_ascii_digits('0')
    assert is_ascii_digits('007')


def test_is_ascii_digits_rejects_empty():
    assert not is_ascii_digits('')


def test_is_ascii_digits_rejects_non_digits():
    assert not is_ascii_digits('abc')
    assert not is_ascii_digits('12px')
    assert not is_ascii_digits('100%')
    assert not is_ascii_digits(' 5')
    assert not is_ascii_digits('+3')
    assert not is_ascii_digits('-1')


def test_is_ascii_digits_rejects_non_ascii_digits():
    # Python's str.isdigit() returns True for these, but HTML spec
    # requires ASCII digits only.
    assert not is_ascii_digits('\u0660\u0661')  # Arabic-Indic digits
    assert not is_ascii_digits('\u0966')  # Devanagari digit
    assert not is_ascii_digits('3\u0660')  # mixed ASCII and non-ASCII
