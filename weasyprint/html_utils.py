"""Utility functions for HTML microsyntax parsing."""

ASCII_DIGITS = frozenset('0123456789')


def is_ascii_digits(string):
    """Return whether string is non-empty and contains only ASCII digits.

    Unlike Python's str.isdigit(), this rejects non-ASCII digit characters
    (e.g. Arabic-Indic digits) per the HTML specification:
    https://infra.spec.whatwg.org/#ascii-digit

    """
    return bool(string) and all(c in ASCII_DIGITS for c in string)
