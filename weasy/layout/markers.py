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
Functions laying out the markers.

"""

from __future__ import division

import cairo

from .percentages import resolve_percentages
from ..text import TextFragment
from ..formatting_structure import boxes


def list_marker_layout(document, box, containing_block):
    """Lay out the list markers of ``box``."""
    # List markers can be either 'inside' or 'outside'.
    # Inside markers are layed out just like normal inline content, but
    # outside markers need specific layout.
    # TODO: implement outside markers in terms of absolute positioning,
    # see CSS3 lists.
    marker = getattr(box, 'outside_list_marker', None)
    if marker:
        resolve_percentages(marker, containing_block)
        if isinstance(marker, boxes.TextBox):
            text_fragment = TextFragment(marker.text, marker.style,
                context=cairo.Context(document.surface))
            result = text_fragment.split_first_line()
            (marker.show_line, _, marker.width, marker.height,
                marker.baseline, _) = result
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
    image, width, height = box.replacement
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
