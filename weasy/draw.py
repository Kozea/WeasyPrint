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
import urllib

import cairo
from StringIO import StringIO

from .formatting_structure import boxes
from .css.values import get_percentage_value
from .utils import urlopen


SUPPORTED_IMAGES = ['image/png', 'image/gif', 'image/jpeg', 'image/bmp']


def get_image_surface_from_uri(uri):
    """Get a :class:`cairo.ImageSurface`` from an image URI."""
    file_like, mime_type, _charset = urlopen(uri)
    # TODO: implement image type sniffing?
    # http://www.w3.org/TR/html5/fetching-resources.html#content-type-sniffing:-image
    if mime_type in SUPPORTED_IMAGES:
        if mime_type == "image/png":
            image = file_like
        else:
            from PIL import Image
            pil_image = Image.open(StringIO(file_like.read()))
            image = StringIO()
            pil_image = pil_image.convert('RGBA')
            pil_image.save(image, "PNG")
            image.seek(0)
        return cairo.ImageSurface.create_from_png(image)


class CairoContext(cairo.Context):
    """A ``cairo.Context`` with a few more helper methods."""

    def set_source_colorvalue(self, color):
        """Set the source pattern from a ``cssutils.ColorValue`` object."""
        self.set_source_rgba(
            color.red / 255., color.green / 255., color.blue / 255.,
            color.alpha)

    @contextlib.contextmanager
    def stacked(self):
        """Save and restore the context when used with the ``with`` keyword."""
        self.save()
        try:
            yield
        finally:
            self.restore()


def draw_page(page, context):
    """Draw the given PageBox to a Cairo context.

    The context should be scaled so that lengths are in CSS pixels.

    """
    draw_page_background(context, page)
    draw_border(context, page)
    draw_box(context, page.root_box)


def draw_box(context, box):
    """Draw a ``box`` on ``context``."""
    if box.style.visibility == 'visible':
        if has_background(box):
            draw_background(context, box)

        draw_border(context, box)

        marker_box = getattr(box, 'outside_list_marker', None)
        if marker_box:
            draw_box(context, marker_box)

        if isinstance(box, boxes.TextBox):
            draw_text(context, box)
            return

        if isinstance(box, boxes.ReplacedBox):
            draw_replacedbox(context, box)

    if isinstance(box, boxes.ParentBox):
        for child in box.children:
            draw_box(context, child)



def has_background(box):
    """Return whether the given box has any background."""
    return box.style.background_color.alpha > 0 or \
        box.style.background_image != 'none'


def draw_page_background(context, page):
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
    draw_background(context, page, clip=False)
    if has_background(page.root_box):
        draw_background(context, page.root_box, clip=False)
    elif page.root_box.element.tag.lower() == 'html':
        for child in page.root_box.children:
            if child.element.tag.lower() == 'body':
                # This must be drawn now, before anything on the root element.
                draw_background(context, child, clip=False)


def draw_background(context, box, clip=True):
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

        surface = box.document.get_image_surface_from_uri(bg_image)
        if surface is None:
            return

        image_width = surface.get_width()
        image_height = surface.get_height()

        bg_position = box.style.background_position
        bg_position_x, bg_position_y = absolute_background_position(
            bg_position, (bg_width, bg_height), (image_width, image_height))
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


def absolute_background_position(css_values, bg_dimensions, image_dimensions):
    """Return the background's ``position_x, position_y`` in pixels.

    http://www.w3.org/TR/CSS21/colors.html#propdef-background-position

    :param css_values: a list of one or two cssutils Value objects.
    :param bg_dimensions: ``width, height`` of the background positionning area
    :param image_dimensions: ``width, height`` of the background image

    """
    values = list(css_values)

    if len(css_values) == 1:
        values.append('center')
    else:
        assert len(css_values) == 2

    if values[1] in ('left', 'right') or values[0] in ('top', 'bottom'):
        values.reverse()
    # Order is now [horizontal, vertical]

    kw_to_percentage = dict(top=0, left=0, center=50, bottom=100, right=100)

    for value, bg_dimension, image_dimension in zip(
            values, bg_dimensions, image_dimensions):
        percentage = kw_to_percentage.get(value, get_percentage_value(value))
        if percentage is not None:
            yield (bg_dimension - image_dimension) * percentage / 100.
        else:
            yield value


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
            """
            Both edges form a trapezoid. This is the top one:

              +---------------+
               \             /
              =================
                 \         /
                  +-------+

            We clip on its outline on draw on the big line on the middle.
            """
            # TODO: implement other styles.
            if not style in ['dotted', 'dashed']:
                border_start, border_stop = border_edge
                padding_start, padding_stop = padding_edge
                # Move to one of the Trapezoid’s corner
                context.move_to(*border_start)
                for point in [border_stop, padding_stop,
                              padding_start, border_start]:
                    context.line_to(*point)
                context.clip()
            elif style == 'dotted':
                # TODO: find a way to make a real dotted border
                context.set_dash([width], 0)
            elif style == 'dashed':
                # TODO: find a way to make a real dashed border
                context.set_dash([4 * width], 0)
            (x1, y1), (x2, y2) = border_edge
            offset = width / 2
            x_offset *= offset
            y_offset *= offset
            x1 += x_offset
            x2 += x_offset
            y1 += y_offset
            y2 += y_offset
            context.move_to(x1, y1)
            context.line_to(x2, y2)
            context.set_source_colorvalue(color)
            context.set_line_width(width)
            context.stroke()


def draw_replacedbox(context, box):
    """Draw the given :class:`boxes.ReplacedBox` to a ``cairo.context``."""
    x, y = box.padding_box_x(), box.padding_box_y()
    width, height = box.width, box.height
    with context.stacked():
        context.translate(x, y)
        context.rectangle(0, 0, width, height)
        context.clip()
        scale_width = width / box.replacement.intrinsic_width()
        scale_height = height / box.replacement.intrinsic_height()
        context.scale(scale_width, scale_height)
        box.replacement.draw(context)


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
