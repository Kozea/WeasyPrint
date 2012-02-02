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


# Map values of the image-rendering property to cairo FILTER values:
IMAGE_RENDERING_TO_FILTER = dict(
    optimizeSpeed=cairo.FILTER_FAST,
    auto=cairo.FILTER_GOOD,
    optimizeQuality=cairo.FILTER_BEST,
)


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
    draw_box(document, context, page, page)


def draw_box(document, context, page, box):
    """Draw a ``box`` on ``context``."""
    if box.style.visibility == 'visible':
        draw_box_background(document, context, page, box)
        draw_border(context, box)

        marker_box = getattr(box, 'outside_list_marker', None)
        if marker_box:
            draw_box(document, context, page, marker_box)

        if isinstance(box, boxes.TextBox):
            draw_text(context, box)
            return

        if isinstance(box, boxes.ReplacedBox):
            draw_replacedbox(context, box)

    if isinstance(box, boxes.TableBox):
        for child in box.column_groups:
            draw_box(document, context, page, child)

    # XXX TODO: check the painting order for page boxes
    if box is page:
        draw_canvas_background(document, context, page)

    if isinstance(box, boxes.ParentBox):
        for child in box.children:
            draw_box(document, context, page, child)


def box_rectangle(box, which_rectangle):
    if which_rectangle == 'border-box':
        return (
            box.border_box_x(),
            box.border_box_y(),
            box.border_width(),
            box.border_height(),
        )
    elif which_rectangle == 'padding-box':
        return (
            box.padding_box_x(),
            box.padding_box_y(),
            box.padding_width(),
            box.padding_height(),
        )
    elif which_rectangle == 'content-box':
        return (
            box.content_box_x(),
            box.content_box_y(),
            box.width,
            box.height,
        )
    else:
        raise ValueError(which_rectangle)


def background_positioning_area(page, box, style):
    if style.background_attachment == 'fixed' and box is not page:
        # Initial containing block
        return box_rectangle(page, 'content-box')
    else:
        return box_rectangle(box, box.style.background_origin)


def draw_canvas_background(document, context, page):
    if not page.children or isinstance(page.children[0], boxes.MarginBox):
        # Skip the canvas background on content-empty pages
        # TODO: remove this when content empty pages still get boxes
        # up to the break point, so that the backgrounds and borders are drawn.
        return
    root_box = page.children[0]
    style = root_box.canvas_background
    draw_background(document, context, style,
        painting_area=box_rectangle(page, 'padding-box'),
        positioning_area=background_positioning_area(page, root_box, style)
    )


def draw_box_background(document, context, page, box):
    """Draw the box background color and image to a ``cairo.Context``."""
    if box is page:
        painting_area = None
    else:
        painting_area=box_rectangle(box, box.style.background_clip)
    draw_background(document, context, box.style, painting_area,
        positioning_area=background_positioning_area(page, box, box.style))


def draw_background(document, context, style, painting_area, positioning_area):
    """Draw the background color and image to a ``cairo.Context``."""
    bg_color = style.background_color
    bg_image = style.background_image
    if bg_image == 'none':
        image = None
    else:
        image = document.get_image_from_uri(bg_image)
    if bg_color.alpha == 0 and image is None:
        # No background.
        return

    with context.stacked():
        if painting_area:
            context.rectangle(*painting_area)
            context.clip()
        #else: unrestricted, whole page box

        # Background color
        if bg_color.alpha > 0:
            context.set_source_colorvalue(bg_color)
            context.paint()

        # Background image
        if image is None:
            return

        def percentage(value, refer_to):
            percentage_value = get_percentage_value(value)
            if percentage_value is None:
                return value
            else:
                return refer_to * percentage_value / 100

        (positioning_x, positioning_y,
            positioning_width, positioning_height) = positioning_area
        context.translate(positioning_x, positioning_y)

        pattern, intrinsic_width, intrinsic_height = image

        bg_size = style.background_size
        if bg_size in ('cover', 'contain'):
            scale_x = scale_y = {'cover': max, 'contain': min}[bg_size](
                positioning_width / intrinsic_width,
                positioning_height / intrinsic_height)
            image_width = intrinsic_width * scale_x
            image_height = intrinsic_height * scale_y
        elif bg_size == ('auto', 'auto'):
            scale_x = scale_y = 1
            image_width = intrinsic_width
            image_height = intrinsic_height
        elif bg_size[0] == 'auto':
            image_height = percentage(bg_size[1], positioning_height)
            scale_x = scale_y = image_height / intrinsic_height
            image_width = intrinsic_width * scale_x
        elif bg_size[1] == 'auto':
            image_width = percentage(bg_size[0], positioning_width)
            scale_x = scale_y = image_width / intrinsic_width
            image_height = intrinsic_height * scale_y
        else:
            image_width = percentage(bg_size[0], positioning_width)
            image_height = percentage(bg_size[1], positioning_height)
            scale_x = image_width / intrinsic_width
            scale_y = image_height / intrinsic_height

        bg_position_x, bg_position_y = style.background_position
        context.translate(
            percentage(bg_position_x, positioning_width - image_width),
            percentage(bg_position_y, positioning_height - image_height),
        )

        bg_repeat = style.background_repeat
        if bg_repeat in ('repeat-x', 'repeat-y'):
            # Get the current clip rectangle. This is the same as
            # painting_area, but in new coordinates after translate()
            clip_x1, clip_y1, clip_x2, clip_y2 = context.clip_extents()
            clip_width = clip_x2 - clip_x1
            clip_height = clip_y2 - clip_y1

            if bg_repeat == 'repeat-x':
                # Limit the drawn area vertically
                clip_y1 = 0  # because of the last context.translate()
                clip_height = image_height
            else:
                # repeat-y
                # Limit the drawn area horizontally
                clip_x1 = 0  # because of the last context.translate()
                clip_width = image_width

            # Second clip for the background image
            context.rectangle(clip_x1, clip_y1, clip_width, clip_height)
            context.clip()

        if bg_repeat == 'no-repeat':
            # The same image/pattern may have been used
            # in a repeating background.
            pattern.set_extend(cairo.EXTEND_NONE)
        else:
            pattern.set_extend(cairo.EXTEND_REPEAT)
        # TODO: de-duplicate this with draw_replacedbox()
        pattern.set_filter(IMAGE_RENDERING_TO_FILTER[style.image_rendering])
        context.scale(scale_x, scale_y)
        context.set_source(pattern)
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
    pattern, intrinsic_width, intrinsic_height = box.replacement
    with context.stacked():
        context.translate(x, y)
        context.rectangle(0, 0, width, height)
        context.clip()
        scale_width = width / intrinsic_width
        scale_height = height / intrinsic_height
        context.scale(scale_width, scale_height)
        # The same image/pattern may have been used in a repeating background.
        pattern.set_extend(cairo.EXTEND_NONE)
        pattern.set_filter(IMAGE_RENDERING_TO_FILTER[
            box.style.image_rendering])
        context.set_source(pattern)
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
