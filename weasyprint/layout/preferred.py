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
Preferred minimum width and preferred width, also know as shrink-to-fit.

"""

import cairo

from ..formatting_structure import boxes
from ..text import TextFragment
from .inlines import replaced_box_width
from .percentages import resolve_percentages


def inline_preferred_minimum_width(box):
    """Return the preferred minimum width for an ``InlineBox``.

    This is the width by breaking at every line-break opportunity.

    *Warning:* only TextBox and InlineReplacedBox children are supported
    for now. (No recursive InlineBox childdren.)

    """
    widest_line = 0
    for child in box.children:
        if isinstance(child, boxes.AtomicInlineLevelBox):
            # Images are on their own line
            current_line = replaced_preferred_width(child)
        else:
            assert isinstance(child, boxes.TextBox)
            current_line = max(text_lines_width(child, width=0))
        widest_line = max(widest_line, current_line)
    return widest_line


def inline_preferred_width(box):
    """Return the preferred width for an ``InlineBox``.

    This is the width by only breaking at forced line breaks.

    *Warning:* only TextBox and InlineReplacedBox children are supported
    for now. (No recursive InlineBox childdren.)

    """
    widest_line = 0
    current_line = 0
    for child in box.children:
        if isinstance(child, boxes.InlineReplacedBox):
            # No line break around images
            current_line += replaced_preferred_width(child)
        else:
            assert isinstance(child, boxes.TextBox)
            lines = list(text_lines_width(child, width=None))
            assert lines
            # The first text line goes on the current line
            current_line += lines[0]
            if len(lines) > 1:
                # Forced line break
                widest_line = max(widest_line, current_line)
                if len(lines) > 2:
                    widest_line = max(widest_line, max(lines[1:-1]))
                current_line = lines[-1]
    widest_line = max(widest_line, current_line)
    return widest_line


def text_lines_width(box, width):
    """Return the list of line widths for a ``TextBox``."""
    # TODO: find the real surface, to have correct hinting
    context = cairo.Context(cairo.PDFSurface(None, 1, 1))
    fragment = TextFragment(box.text, box.style, context, width=width)
    return fragment.line_widths()


def replaced_preferred_width(box):
    """Return the preferred (minimum) width for an ``InlineReplacedBox``."""
    # TODO: get the actual device size. Or do we really care?
    # TODO: what about percentage widths?
    resolve_percentages(box, containing_block=(0, 0))
    replaced_box_width(box, device_size=None)
    return box.width
