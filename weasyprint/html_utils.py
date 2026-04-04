"""Utility functions for HTML microsyntax parsing."""

# https://html.spec.whatwg.org/multipage/#space-character
HTML_WHITESPACE = ' \t\n\f\r'
ASCII_DIGITS = frozenset('0123456789')


def parse_html_integer(string):
    """Parse an integer from an HTML attribute value.

    Follow the HTML specification rules for parsing integers:
    https://html.spec.whatwg.org/#rules-for-parsing-integers

    Return an integer, or ``None`` on error.

    """
    position = 0
    length = len(string)

    # Skip ASCII whitespace.
    while position < length and string[position] in HTML_WHITESPACE:
        position += 1

    if position >= length:
        return None

    # Determine sign.
    sign = 1
    if string[position] == '-':
        sign = -1
        position += 1
    elif string[position] == '+':
        position += 1

    if position >= length or string[position] not in ASCII_DIGITS:
        return None

    # Collect sequence of ASCII digits.
    digits_start = position
    while position < length and string[position] in ASCII_DIGITS:
        position += 1

    return sign * int(string[digits_start:position])
