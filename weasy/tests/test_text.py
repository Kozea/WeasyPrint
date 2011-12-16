# coding: utf8

#  WeasyPrint converts web documents (HTML, CSS, ...) to PDF.
#  Copyright (C) 2011  Simon Sapin
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Test the text management.

"""

import cssutils
import cairo
from attest import Tests, assert_hook  # pylint: disable=W0611

from ..css import effective_declarations, computed_from_cascaded
from ..text import TextFragment
from .test_layout import parse, body_children
from .testing_utils import FONTS, assert_no_logs


SUITE = Tests()
SUITE.context(assert_no_logs)


def make_text(text, width=-1, style=''):
    """
    Make and return a TextFragment built from a TextBox in an HTML document.
    """
    style = dict(effective_declarations(cssutils.parseStyle(
        'font-family: Nimbus Mono L, Liberation Mono, FreeMono, Monospace; '
        + style)))
    style = computed_from_cascaded(None, style, None)
    surface = cairo.SVGSurface(None, 1, 1)
    text = text.encode('utf8')
    return TextFragment(text, style, cairo.Context(surface), width)


@SUITE.test
def test_line_content():
    """Test the line break for various fixed-width lines."""
    for width, remaining in [(90, 'text for test'),
                             (45, 'is a text for test')]:
        text = 'This is a text for test'
        line = make_text(
            text, width, 'font-family: "%s"; font-size: 19px' % FONTS)
        _, length, _, _, _, resume_at = line.split_first_line()
        assert text[resume_at:] == remaining
        assert length == resume_at


@SUITE.test
def test_line_with_any_width():
    """Test the auto-fit width of lines."""
    line = make_text(u'some text')
    _, _, width, _, _, _ = line.split_first_line()

    line = make_text('some some some text some some some text')
    _, _, new_width, _, _, _ = line.split_first_line()

    assert width < new_width


@SUITE.test
def test_line_breaking():
    """Test the line breaking."""
    string = u'This is a text for test'

    # These two tests do not really rely on installed fonts
    line = make_text(string, 90, 'font-size: 1px')
    _, _, _, _, _, resume_at = line.split_first_line()
    assert resume_at is None

    line = make_text(string, 90, 'font-size: 100px')
    _, _, _, _, _, resume_at = line.split_first_line()
    assert string[resume_at:] == u'is a text for test'

    line = make_text(string, 90, 'font-family: "%s"; font-size: 19px' % FONTS)
    _, _, _, _, _, resume_at = line.split_first_line()
    assert string[resume_at:] == u'text for test'


@SUITE.test
def test_text_dimension():
    """Test the font size impact on the text dimension."""
    string = u'This is a text for test. This is a test for text.py'
    fragment = make_text(string, 200, 'font-size: 12px')
    _, _, width_1, height_1, _, _ = fragment.split_first_line()

    fragment = make_text(string, 200, 'font-size: 20px')
    _, _, width_2, height_2, _, _ = fragment.split_first_line()
    assert width_1 * height_1 < width_2 * height_2


@SUITE.test
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
