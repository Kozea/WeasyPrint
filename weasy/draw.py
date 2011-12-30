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
Module drawing documents.

"""

from __future__ import division
import contextlib

import cairo

from .formatting_structure import boxes
from .css.values import get_percentage_value


class CairoContext(cairo.Context):
    """A ``cairo.Context`` with a few more helper methods."""

    def set_source_colorvalue(self, color, lighten=0):
        """Set the source pattern from a ``cssutils.ColorValue`` object."""
        self.set_source_rgba(
            color.red / 255. + lighten,
            color.green / 255. + lighten,
            color.blue / 255. + lighten,
            color.alpha)

    @contextlib.contextmanager
    def stacked(self):
        """Save and restore the context when used with the ``with`` keyword."""
        self.save()
        try:
            yield
        finally:
            self.restore()


def draw_page(document, page, context):
    """Draw the given PageBox to a Cairo context.

    The context should be scaled so that lengths are in CSS pixels.

    """
    draw_page_background(document, context, page)
    draw_box(document, context, page)


def draw_box(document, context, box):
    """Draw a ``box`` on ``context``."""
    if box.style.visibility == 'visible':
        if has_background(box):
            draw_background(document, context, box)

        draw_border(context, box)

        marker_box = getattr(box, 'outside_list_marker', None)
        if marker_box:
            draw_box(document, context, marker_box)

        if isinstance(box, boxes.TextBox):
            draw_text(context, box)
            return

        if isinstance(box, boxes.ReplacedBox):
            draw_replacedbox(context, box)

    if isinstance(box, boxes.TableBox):
        for child in box.column_groups:
            draw_box(document, context, child)

    if isinstance(box, boxes.ParentBox):
        for child in box.children:
            draw_box(document, context, child)



def has_background(box):
    """Return whether the given box has any background."""
    return box.style.background_color.alpha > 0 or \
        box.style.background_image != 'none'


def draw_page_background(document, context, page):
    """Draw the backgrounds for the page box (from @page style) and for the
    page area (from the root element).

    If the root element is "html" and has no background, the page area’s
    background is taken from its "body" child.

    In both cases the background position is the same as if it was drawn on
    the element.

    See http://www.w3.org/TR/CSS21/colors.html#background

    """
    # TODO: this one should have its origin at (0, 0), not the border box
    # of the page.
    # TODO: more tests for this, see
    # http://www.w3.org/TR/css3-page/#page-properties
    draw_background(document, context, page, clip=False)
    # Margin boxes come after the content for painting order,
    # so the box for the root element is the first child.
    root_box = page.children[0]
    if has_background(root_box):
        draw_background(document, context, root_box, clip=False)
    elif root_box.element_tag.lower() == 'html':
        for child in root_box.children:
            if child.element_tag.lower() == 'body':
                # This must be drawn now, before anything on the root element.
                draw_background(document, context, child, clip=False)


def draw_background(document, context, box, clip=True):
    """Draw the box background color and image to a ``cairo.Context``."""
    if getattr(box, 'background_drawn', False):
        return

    box.background_drawn = True

    if not has_background(box):
        return

    with context.stacked():
        bg_x = box.border_box_x()
        bg_y = box.border_box_y()
        bg_width = box.border_width()
        bg_height = box.border_height()

        bg_attachement = box.style.background_attachment
        if bg_attachement == 'fixed':
            # There should not be any clip yet
            x1, y1, x2, y2 = context.clip_extents()
            page_width = x2 - x1
            page_height = y2 - y1

        if clip:
            context.rectangle(bg_x, bg_y, bg_width, bg_height)
            context.clip()

        # Background color
        bg_color = box.style.background_color
        if bg_color.alpha > 0:
            context.set_source_colorvalue(bg_color)
            context.paint()

        if bg_attachement == 'scroll':
            # Change coordinates to make the rest easier.
            context.translate(bg_x, bg_y)
        else:
            assert bg_attachement == 'fixed'
            bg_width = page_width
            bg_height = page_height

        # Background image
        bg_image = box.style.background_image
        if bg_image == 'none':
            return

        image = document.get_image_surface_from_uri(bg_image)
        if image is None:
            return

        surface, image_width, image_height = image

        bg_position_x, bg_position_y = box.style.background_position

        percentage = get_percentage_value(bg_position_x)
        if percentage is not None:
            bg_position_x = (bg_width - image_width) * percentage / 100.

        percentage = get_percentage_value(bg_position_y)
        if percentage is not None:
            bg_position_y = (bg_height - image_height) * percentage / 100.

        context.translate(bg_position_x, bg_position_y)

        bg_repeat = box.style.background_repeat
        if bg_repeat != 'repeat':
            # Get the current clip rectangle
            clip_x1, clip_y1, clip_x2, clip_y2 = context.clip_extents()
            clip_width = clip_x2 - clip_x1
            clip_height = clip_y2 - clip_y1

            if bg_repeat in ('no-repeat', 'repeat-x'):
                # Limit the drawn area vertically
                clip_y1 = 0  # because of the last context.translate()
                clip_height = image_height

            if bg_repeat in ('no-repeat', 'repeat-y'):
                # Limit the drawn area horizontally
                clip_x1 = 0  # because of the last context.translate()
                clip_width = image_width

            # Second clip for the background image
            context.rectangle(clip_x1, clip_y1, clip_width, clip_height)
            context.clip()

        context.set_source_surface(surface)
        context.get_source().set_extend(cairo.EXTEND_REPEAT)
        context.paint()


def get_rectangle_edges(x, y, width, height):
    """Return the 4 edges of a rectangle as a list.

    Edges are in clock-wise order, starting from the top.

    Each edge is returned as ``(start_point, end_point)`` and each point
    as ``(x, y)`` coordinates.

    """
    # In clock-wise order, starting on top left
    corners = [
        (x, y),
        (x + width, y),
        (x + width, y + height),
        (x, y + height)]
    # clock-wise order, starting on top right
    shifted_corners = corners[1:] + corners[:1]
    return zip(corners, shifted_corners)


def xy_offset(x, y, offset_x, offset_y, offset):
    """Increment X and Y coordinates by the given offsets."""
    return x + offset_x * offset, y + offset_y * offset


def draw_border(context, box):
    """Draw the box border to a ``cairo.Context``."""
    if all(getattr(box, 'border_%s_width' % side) == 0
           for side in ['top', 'right', 'bottom', 'left']):
        # No border, return early.
        return

    for side, x_offset, y_offset, border_edge, padding_edge in zip(
        ['top', 'right', 'bottom', 'left'],
        [0, -1, 0, 1],
        [1, 0, -1, 0],
        get_rectangle_edges(
            box.border_box_x(), box.border_box_y(),
            box.border_width(), box.border_height(),
        ),
        get_rectangle_edges(
            box.padding_box_x(), box.padding_box_y(),
            box.padding_width(), box.padding_height(),
        ),
    ):
        width = getattr(box, 'border_%s_width' % side)
        if width == 0:
            continue
        color = box.style['border_%s_color' % side]
        if color.alpha == 0:
            continue
        style = box.style['border_%s_style' % side]
        with context.stacked():
            context.set_source_colorvalue(color)

            # Avoid an artefact in the corner joining two solid borders
            # of the same color.
            context.set_antialias(cairo.ANTIALIAS_NONE)

            if style not in ('dotted', 'dashed'):
                # Clip on the trapezoid shape
                """
                Clip on the trapezoid formed by the border edge (longer)
                and the padding edge (shorter).

                This is on the top side:

                  +---------------+    <= border edge      ^
                   \             /                         |
                    \           /                          |  top border width
                     \         /                           |
                      +-------+        <= padding edge     v

                  <-->         <-->    <=  left and right border widths

                """
                border_start, border_stop = border_edge
                padding_start, padding_stop = padding_edge
                context.move_to(*border_start)
                for point in [border_stop, padding_stop,
                              padding_start, border_start]:
                    context.line_to(*point)
                context.clip()

            if style == 'solid':
                # Fill the whole trapezoid
                context.paint()
            elif style in ('inset', 'outset'):
                lighten = (side in ('top', 'left')) ^ (style == 'inset')
                factor = 1 if lighten else -1
                context.set_source_colorvalue(color, lighten=0.5 * factor)
                context.paint()
            elif style in ('groove', 'ridge'):
                # TODO: these would look better with more color stops
                """
                Divide the width in 2 and stroke lines in different colors
                  +-------------+
                  1\           /2
                  1'\         / 2'
                     +-------+
                """
                lighten = (side in ('top', 'left')) ^ (style == 'groove')
                factor = 1 if lighten else -1
                context.set_line_width(width / 2)
                (x1, y1), (x2, y2) = border_edge
                # from the border edge to the center of the first line
                x1, y1 = xy_offset(x1, y1, x_offset, y_offset, width / 4)
                x2, y2 = xy_offset(x2, y2, x_offset, y_offset, width / 4)
                context.move_to(x1, y1)
                context.line_to(x2, y2)
                context.set_source_colorvalue(color, lighten=0.5 * factor)
                context.stroke()
                # Between the centers of both lines. 1/4 + 1/4 = 1/2
                x1, y1 = xy_offset(x1, y1, x_offset, y_offset, width / 2)
                x2, y2 = xy_offset(x2, y2, x_offset, y_offset, width / 2)
                context.move_to(x1, y1)
                context.line_to(x2, y2)
                context.set_source_colorvalue(color, lighten=-0.5 * factor)
                context.stroke()
            elif style == 'double':
                """
                Divide the width in 3 and stroke both outer lines
                  +---------------+
                  1\             /2
                    \           /
                  1' \         /  2'
                      +-------+
                """
                context.set_line_width(width / 3)
                (x1, y1), (x2, y2) = border_edge
                # from the border edge to the center of the first line
                x1, y1 = xy_offset(x1, y1, x_offset, y_offset, width / 6)
                x2, y2 = xy_offset(x2, y2, x_offset, y_offset, width / 6)
                context.move_to(x1, y1)
                context.line_to(x2, y2)
                context.stroke()
                # Between the centers of both lines. 1/6 + 1/3 + 1/6 = 2/3
                x1, y1 = xy_offset(x1, y1, x_offset, y_offset, 2 * width / 3)
                x2, y2 = xy_offset(x2, y2, x_offset, y_offset, 2 * width / 3)
                context.move_to(x1, y1)
                context.line_to(x2, y2)
                context.stroke()
            else:
                assert style in ('dotted', 'dashed')
                (x1, y1), (x2, y2) = border_edge
                if style == 'dotted':
                    # Half-way from the extremities of the border and padding
                    # edges.
                    (px1, py1), (px2, py2) = padding_edge
                    x1 = (x1 + px1) / 2
                    x2 = (x2 + px2) / 2
                    y1 = (y1 + py1) / 2
                    y2 = (y2 + py2) / 2
                    """
                      +---------------+
                       \             /
                        1           2
                         \         /
                          +-------+
                    """
                else:  # dashed
                    # From the border edge to the middle:
                    x1, y1 = xy_offset(x1, y1, x_offset, y_offset, width / 2)
                    x2, y2 = xy_offset(x2, y2, x_offset, y_offset, width / 2)
                    """
                      +---------------+
                       \             /
                      1 \           / 2
                         \         /
                          +-------+
                    """
                length = ((x2 - x1)**2 + (y2 - y1)**2) ** 0.5
                dash = 2 * width
                if style == 'dotted':
                    if context.user_to_device_distance(width, 0)[0] > 3:
                        # Round so that dash is a divisor of length,
                        # but not in the dots are too small.
                        dash = length / round(length / dash)
                    context.set_line_cap(cairo.LINE_CAP_ROUND)
                    context.set_dash([0, dash])
                else:  # dashed
                    # Round so that 2*dash is a divisor of length
                    dash = length / (2 * round(length / (2 * dash)))
                    context.set_dash([dash])
                # Stroke along the line in === above, as wide as the border
                context.move_to(x1, y1)
                context.line_to(x2, y2)
                context.set_line_width(width)
                context.stroke()


def draw_replacedbox(context, box):
    """Draw the given :class:`boxes.ReplacedBox` to a ``cairo.context``."""
    x, y = box.padding_box_x(), box.padding_box_y()
    width, height = box.width, box.height
    surface, intrinsic_width, intrinsic_height = box.replacement
    with context.stacked():
        context.translate(x, y)
        context.rectangle(0, 0, width, height)
        context.clip()
        scale_width = width / intrinsic_width
        scale_height = height / intrinsic_height
        context.scale(scale_width, scale_height)
        context.set_source_surface(surface)
        context.paint()

def draw_text(context, textbox):
    """Draw ``textbox`` to a ``cairo.Context`` from ``PangoCairo.Context``."""
    # Pango crashes with font-size: 0
    assert textbox.style.font_size

    context.move_to(textbox.position_x, textbox.position_y + textbox.baseline)
    context.set_source_colorvalue(textbox.style.color)
    textbox.show_line(context)
    values = textbox.style.text_decoration
    for value in values:
        if value == 'overline':
            draw_overline(context, textbox)
        elif value == 'underline':
            draw_underline(context, textbox)
        elif value == 'line-through':
            draw_line_through(context, textbox)


def draw_overline(context, textbox):
    """Draw overline of ``textbox`` to a ``cairo.Context``."""
    font_size = textbox.style.font_size
    position_y = textbox.baseline + textbox.position_y - (font_size * 0.15)
    draw_text_decoration(context, position_y, textbox)


def draw_underline(context, textbox):
    """Draw underline of ``textbox`` to a ``cairo.Context``."""
    font_size = textbox.style.font_size
    position_y = textbox.baseline + textbox.position_y + (font_size * 0.15)
    draw_text_decoration(context, position_y, textbox)


def draw_line_through(context, textbox):
    """Draw line-through of ``textbox`` to a ``cairo.Context``."""
    position_y = textbox.position_y + (textbox.height * 0.5)
    draw_text_decoration(context, position_y, textbox)


def draw_text_decoration(context, position_y, textbox):
    """Draw text-decoration of ``textbox`` to a ``cairo.Context``."""
    with context.stacked():
        context.set_source_colorvalue(textbox.style.color)
        context.set_line_width(1)  # TODO: make this proportional to font_size?
        context.move_to(textbox.position_x, position_y)
        context.rel_line_to(textbox.width, 0)
        context.stroke()
