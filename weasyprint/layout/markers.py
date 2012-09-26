# coding: utf8
"""
    weasyprint.layout.markers
    -------------------------

    Layout for list markers (for ``display: list-item``).

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from .percentages import resolve_percentages
from ..text import split_first_line
from ..formatting_structure import boxes


def list_marker_layout(context, box):
    """Lay out the list markers of ``box``."""
    # List markers can be either 'inside' or 'outside'.
    # Inside markers are layed out just like normal inline content, but
    # outside markers need specific layout.
    # TODO: implement outside markers in terms of absolute positioning,
    # see CSS3 lists.
    marker = getattr(box, 'outside_list_marker', None)
    if marker:
        resolve_percentages(marker, containing_block=box)
        if isinstance(marker, boxes.TextBox):
            (marker.pango_layout, _, _, marker.width, marker.height,
                marker.baseline) = split_first_line(
                    marker.text, marker.style, context.enable_hinting,
                    max_width=None)
        else:
            # Image marker
            image_marker_layout(marker)

        # Align the top of the marker box with the top of its list-item’s
        # content-box.
        # TODO: align the baselines of the first lines instead?
        marker.position_y = box.content_box_y()
        # ... and its right with the left of its list-item’s padding box.
        # (Swap left and right for right-to-left text.)
        marker.position_x = box.border_box_x()

        half_em = 0.5 * box.style.font_size
        direction = box.style.direction
        if direction == 'ltr':
            marker.margin_right = half_em
            marker.position_x -= marker.margin_width()
        else:
            marker.margin_left = half_em
            marker.position_x += box.border_width()


def image_marker_layout(box):
    """Layout the :class:`boxes.ImageMarkerBox` ``box``.

    :class:`boxes.ImageMarkerBox` objects are :class:`boxes.ReplacedBox`
    objects, but their used size is computed differently.

    """
    _, width, height = box.replacement
    ratio = width / height
    one_em = box.style.font_size
    if width is not None and height is not None:
        box.width = width
        box.height = height
    elif width is not None and ratio is not None:
        box.width = width
        box.height = width / ratio
    elif height is not None and ratio is not None:
        box.width = height * ratio
        box.height = height
    elif ratio is not None:
        # ratio >= 1 : width >= height
        if ratio >= 1:
            box.width = one_em
            box.height = one_em / ratio
        else:
            box.width = one_em * ratio
            box.height = one_em
    else:
        box.width = width if width is not None else one_em
        box.height = height if height is not None else one_em
