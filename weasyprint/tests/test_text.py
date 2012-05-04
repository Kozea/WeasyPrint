# coding: utf8
"""
    weasyprint.tests.test_text
    --------------------------

    Test the text layout.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import cairo

from ..css import StyleDict, PARSER
from ..css.properties import INITIAL_VALUES
from ..text import TextFragment
from .test_layout import parse, body_children
from .testing_utils import FONTS, assert_no_logs


def make_text(text, width=-1, **style):
    """
    Make and return a TextFragment built from a TextBox in an HTML document.
    """
    style = StyleDict({
        'font_family': 'Nimbus Mono L, Liberation Mono, FreeMono, Monospace',
    }, INITIAL_VALUES).updated_copy(style)
    surface = cairo.SVGSurface(None, 1, 1)
    return TextFragment(text, style, cairo.Context(surface), width)


@assert_no_logs
def test_line_content():
    """Test the line break for various fixed-width lines."""
    for width, remaining in [(120, 'text for test'),
                             (45, 'is a text for test')]:
        text = 'This is a text for test'
        line = make_text(
            text, width, font_family=FONTS, font_size=19)
        _, length, _, _, _, resume_at = line.split_first_line()
        assert text[resume_at:] == remaining
        assert length == resume_at


@assert_no_logs
def test_line_with_any_width():
    """Test the auto-fit width of lines."""
    line = make_text('some text')
    _, _, width, _, _, _ = line.split_first_line()

    line = make_text('some some some text some some some text')
    _, _, new_width, _, _, _ = line.split_first_line()

    assert width < new_width


@assert_no_logs
def test_line_breaking():
    """Test the line breaking."""
    string = 'This is a text for test'

    # These two tests do not really rely on installed fonts
    line = make_text(string, 90, font_size=1)
    _, _, _, _, _, resume_at = line.split_first_line()
    assert resume_at is None

    line = make_text(string, 90, font_size=100)
    _, _, _, _, _, resume_at = line.split_first_line()
    assert string[resume_at:] == 'is a text for test'

    line = make_text(string, 120, font_family=FONTS, font_size=19)
    _, _, _, _, _, resume_at = line.split_first_line()
    assert string[resume_at:] == 'text for test'


@assert_no_logs
def test_text_dimension():
    """Test the font size impact on the text dimension."""
    string = 'This is a text for test. This is a test for text.py'
    fragment = make_text(string, 200, font_size=12)
    _, _, width_1, height_1, _, _ = fragment.split_first_line()

    fragment = make_text(string, 200, font_size=20)
    _, _, width_2, height_2, _, _ = fragment.split_first_line()
    assert width_1 * height_1 < width_2 * height_2


@assert_no_logs
def test_text_font_size_zero():
    """Test a text with a font size set to 0."""
    page, = parse('''
        <style>
            p { font-size: 0; }
        </style>
        <p>test font size zero</p>
    ''')
    paragraph, = body_children(page)
    # zero-sized text boxes are removed
    line, = paragraph.children
    assert not line.children
    assert line.height == 0
    assert paragraph.height == 0
