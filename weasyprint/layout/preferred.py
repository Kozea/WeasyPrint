# coding: utf8
"""
    weasyprint.layout.preferred
    ---------------------------

    Preferred and minimum preferred width, aka. the shrink-to-fit algorithm.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import cairo

from ..css.values import get_percentage_value
from ..formatting_structure import boxes
from ..text import TextFragment


def variable_and_fixed_widths(box, width=None):
    """Return ``(variable_ratio, fixed_width)`` of ``box``.

    ``'auto'`` margins are ignored. ``'auto'`` width is not allowed.

    """
    if width is None:
        width = box.style.width

    assert width is not 'auto'

    if isinstance(width, (int, float)):
        fixed_width = width
        variable_ratio = 0
    else:
        fixed_width = 0
        variable_ratio = get_percentage_value(width) / 100.

    for value in ('margin_left', 'margin_right',
                  'border_left_width', 'border_right_width',
                  'padding_left', 'padding_right'):
        style_value = box.style[value]
        if isinstance(style_value, (int, float)):
            fixed_width += style_value
        elif style_value != 'auto':
            variable_ratio += get_percentage_value(style_value) / 100.

    return variable_ratio, fixed_width


def shrink_to_fit(box, available_width):
    """Return the shrink-to-fit width of ``box``.

    http://www.w3.org/TR/CSS21/visudet.html#float-width

    """
    return min(
        max(preferred_mimimum_width(box), available_width),
        preferred_width(box))


def preferred_mimimum_width(box):
    """Return the preferred minimum width for ``box``.

    This is the width by breaking at every line-break opportunity.

    """
    if isinstance(box, boxes.BlockContainerBox):
        return block_preferred_minimum_width(box)
    elif isinstance(box, (boxes.InlineBox, boxes.LineBox)):
        return inline_preferred_minimum_width(box)
    else:
        raise TypeError(
            'Preferred minimum width for %s not handled yet' %
            type(box).__name__)


def preferred_width(box):
    """Return the preferred width for ``box``.

    This is the width by only breaking at forced line breaks.

    """
    if isinstance(box, boxes.BlockContainerBox):
        return block_preferred_width(box)
    elif isinstance(box, (boxes.InlineBox, boxes.LineBox)):
        return inline_preferred_width(box)
    else:
        raise TypeError(
            'Preferred width for %s not handled yet' % type(box).__name__)


def _block_preferred_width(box, function):
    """Helper to create ``block_preferred_*_width.``"""
    if not isinstance(box.style.width, (int, float)):
        # % and 'auto' width
        if box.children:
            width = max(function(child) for child in box.children)
        else:
            width = 0
    else:
        width = None

    variable_ratio, fixed_width = variable_and_fixed_widths(box, width)
    if variable_ratio < 1:
        return fixed_width / (1 - variable_ratio)
    else:
        return 0


def block_preferred_minimum_width(box):
    """Return the preferred minimum width for a ``BlockBox``."""
    return _block_preferred_width(box, preferred_mimimum_width)


def block_preferred_width(box):
    """Return the preferred width for a ``BlockBox``."""
    return _block_preferred_width(box, preferred_width)


def inline_preferred_minimum_width(box):
    """Return the preferred minimum width for an ``InlineBox``.

    *Warning:* only TextBox and InlineReplacedBox children are supported
    for now. (No recursive InlineBox children.)

    """
    widest_line = 0
    for child in box.children:
        if isinstance(child, boxes.InlineReplacedBox):
            # Images are on their own line
            current_line = replaced_preferred_width(child)
        elif isinstance(child, boxes.InlineBlockBox):
            current_line = block_preferred_minimum_width(child)
        else:
            assert isinstance(child, boxes.TextBox)
            current_line = max(text_lines_width(child, width=0))
        widest_line = max(widest_line, current_line)
    return widest_line


def inline_preferred_width(box):
    """Return the preferred width for an ``InlineBox``.

    *Warning:* only TextBox and InlineReplacedBox children are supported
    for now. (No recursive InlineBox children.)

    """
    widest_line = 0
    current_line = 0
    for child in box.children:
        if isinstance(child, boxes.InlineReplacedBox):
            # No line break around images
            current_line += replaced_preferred_width(child)
        elif isinstance(child, boxes.InlineBlockBox):
            current_line += block_preferred_width(child)
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
    if isinstance(box, (int, float)):
        width = box.style.width
    else:
        # TODO: handle the images with no intinsic width
        _, width, _ = box.replacement

    variable_ratio, fixed_width = variable_and_fixed_widths(box, width)
    if variable_ratio < 1:
        return fixed_width / (1 - variable_ratio)
    else:
        return 0
