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

from ..formatting_structure import boxes
from ..text import TextFragment


def shrink_to_fit(box, available_width):
    """Return the shrink-to-fit width of ``box``.

    http://www.w3.org/TR/CSS21/visudet.html#float-width

    """
    return min(
        max(preferred_minimum_width(box, outer=False), available_width),
        preferred_width(box, outer=False))


def preferred_minimum_width(box, outer=True):
    """Return the preferred minimum width for ``box``.

    This is the width by breaking at every line-break opportunity.

    """
    if isinstance(box, boxes.BlockContainerBox):
        return block_preferred_minimum_width(box, outer)
    elif isinstance(box, (boxes.InlineBox, boxes.LineBox)):
        return inline_preferred_minimum_width(box, outer)
    else:
        raise TypeError(
            'Preferred minimum width for %s not handled yet' %
            type(box).__name__)


def preferred_width(box, outer=True):
    """Return the preferred width for ``box``.

    This is the width by only breaking at forced line breaks.

    """
    if isinstance(box, boxes.BlockContainerBox):
        return block_preferred_width(box, outer)
    elif isinstance(box, (boxes.InlineBox, boxes.LineBox)):
        return inline_preferred_width(box, outer)
    else:
        raise TypeError(
            'Preferred width for %s not handled yet' % type(box).__name__)


def _block_preferred_width(box, function, outer):
    """Helper to create ``block_preferred_*_width.``"""
    width = box.style.width
    if width == 'auto' or width.unit == '%':
        # "percentages on the following properties are treated instead as
        #  though they were the following: width: auto"
        # http://dbaron.org/css/intrinsic/#outer-intrinsic
        if box.children:
            width = max(function(child, outer=True) for child in box.children)
        else:
            width = 0
    else:
        assert width.unit == 'px'
        width = width.value

    return adjust(box, outer, width)


def adjust(box, outer, fixed_width, variable_ratio=0):
    if outer:
        fixed_width += (box.style.border_left_width
                      + box.style.border_right_width)
        for value in ('margin_left', 'margin_right',
                      'padding_left', 'padding_right'):
            style_value = box.style[value]
            if style_value != 'auto':
                if style_value.unit == 'px':
                    fixed_width += style_value.value
                else:
                    assert style_value.unit == '%'
                    variable_ratio += style_value.value / 100.

    if variable_ratio < 1:
        return fixed_width / (1 - variable_ratio)
    else:
        return 0


def block_preferred_minimum_width(box, outer=True):
    """Return the preferred minimum width for a ``BlockBox``."""
    return _block_preferred_width(box, preferred_minimum_width, outer)


def block_preferred_width(box, outer=True):
    """Return the preferred width for a ``BlockBox``."""
    return _block_preferred_width(box, preferred_width, outer)


def inline_preferred_minimum_width(box, outer=True):
    """Return the preferred minimum width for an ``InlineBox``.

    """
    widest_line = 0
    for child in box.children:
        if isinstance(child, boxes.InlineReplacedBox):
            # Images are on their own line
            current_line = replaced_preferred_width(child)
        elif isinstance(child, boxes.InlineBlockBox):
            current_line = block_preferred_minimum_width(child)
        elif isinstance(child, boxes.InlineBox):
            # TODO: handle forced line breaks
            current_line = inline_preferred_minimum_width(child)
        else:
            assert isinstance(child, boxes.TextBox)
            current_line = max(text_lines_width(child, width=0))
        widest_line = max(widest_line, current_line)
    return widest_line


def inline_preferred_width(box, outer=True):
    """Return the preferred width for an ``InlineBox``.

    """
    widest_line = 0
    current_line = 0
    for child in box.children:
        if isinstance(child, boxes.InlineReplacedBox):
            # No line break around images
            current_line += replaced_preferred_width(child)
        elif isinstance(child, boxes.InlineBlockBox):
            current_line += block_preferred_width(child)
        elif isinstance(child, boxes.InlineBox):
            # TODO: handle forced line breaks
            current_line += inline_preferred_width(child)
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

    return adjust(box, outer, widest_line)


def text_lines_width(box, width):
    """Return the list of line widths for a ``TextBox``."""
    # TODO: find the real surface, to have correct hinting
    context = cairo.Context(cairo.PDFSurface(None, 1, 1))
    fragment = TextFragment(box.text, box.style, context, width=width)
    return fragment.line_widths()


def replaced_preferred_width(box, outer=True):
    """Return the preferred minimum width for an ``InlineReplacedBox``."""
    variable_ratio = 0
    fixed_width = 0

    width = box.style.width
    if width == 'auto':
        # TODO: handle the images with no intinsic width
        _, fixed_width, _ = box.replacement
    elif width.unit == 'px':
        fixed_width = width.value
    else:
        assert width.unit == '%'
        variable_ratio = width.value / 100.

    return adjust(box, outer, fixed_width, variable_ratio)
