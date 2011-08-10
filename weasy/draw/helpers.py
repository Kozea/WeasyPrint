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



from __future__ import division
import urllib
try:
    from urlparse import urljoin
except ImportError:
    # Python 3
    from urllib.parse import urljoin


import cairo
import cssutils.css.value

from ..css.utils import (get_single_keyword, get_keyword,
                         get_pixel_value, get_percentage_value)
from ..formatting_structure import boxes
from .. import text
from .figures import Point, Line, Trapezoid


def get_image_surface_from_uri(uri):
    try:
        fileimage = urllib.urlopen(uri)
        if fileimage.info().gettype() != 'image/png':
            raise NotImplementedError("Only png images are implemented")
        return cairo.ImageSurface.create_from_png(fileimage)
    except IOError:
        return None


def draw_box(context, box):
    if has_background(box):
        draw_background(context, box)

    if isinstance(box, boxes.TextBox):
        draw_text(context, box)
        return

    if isinstance(box, boxes.ReplacedBox):
        draw_replacedbox(context, box)

    if isinstance(box, boxes.ParentBox):
        for child in box.children:
            draw_box(context, child)

    draw_border(context, box)


def has_background(box):
    """
    Return the given box has any background.
    """
    return box.style['background-color'][0].alpha > 0 or \
        get_single_keyword(box.style['background-image']) != 'none'


def draw_canvas_background(context, page):
    """
    Draw the canvas’s background, taken from the root element.

    If the root element is "html" and has no background, the canvas’s
    background is taken from its "body" child.

    In both cases the background position is the same as if it was drawn on
    the element.

    See http://www.w3.org/TR/CSS21/colors.html#background
    """
    if has_background(page.root_box):
        draw_background(context, page.root_box, on_entire_canvas=True)
    elif page.root_box.element.tag.lower() == 'html':
        for child in page.root_box.children:
            if child.element.tag.lower() == 'body':
                # This must be drawn now, before anything on the root element.
                draw_background(context, child, on_entire_canvas=True)


def draw_background(context, box, on_entire_canvas=False):
    """
    Draw the box background color and image to a Cairo context.
    """
    if getattr(box, 'background_drawn', False):
        return

    box.background_drawn = True

    if not has_background(box):
        return

    with context.stacked():
        # Change coordinates to make the rest easier.
        context.translate(box.border_box_x(), box.border_box_y())
        bg_width = box.border_width()
        bg_height = box.border_height()

        if not on_entire_canvas:
            context.rectangle(0, 0, bg_width, bg_height)
            context.clip()

        # Background color
        bg_color = box.style['background-color'][0]
        if bg_color.alpha > 0:
            context.set_source_colorvalue(bg_color)
            context.paint()

        # Background image
        bg_image = box.style['background-image'][0]
        if bg_image.type != 'URI':
            return

        surface = get_image_surface_from_uri(bg_image.absoluteUri)
        if not surface:
            return

        image_width = surface.get_width()
        image_height = surface.get_height()

        context.translate(*absolute_background_position(
            box.style['background-position'], bg_width, bg_height,
            image_width, image_height))

        bg_repeat = get_single_keyword(box.style['background-repeat'])
        if bg_repeat != 'repeat':
            # Get the current clip rectangle
            clip_x1, clip_y1, clip_x2, clip_y2 = context.clip_extents()
            clip_width = clip_x2 - clip_x1
            clip_height = clip_y2 - clip_y1

            if bg_repeat in ('no-repeat', 'repeat-x'):
                # Limit the drawn area vertically
                clip_y1 = 0
                clip_height = image_height

            if bg_repeat in ('no-repeat', 'repeat-y'):
                # Limit the drawn area horizontally
                clip_x1 = 0
                clip_width = image_width

            # Second clip for the background image
            context.rectangle(clip_x1, clip_y1, clip_width, clip_height)
            context.clip()

        pattern = cairo.SurfacePattern(surface)
        pattern.set_extend(cairo.EXTEND_REPEAT)
        context.set_source(pattern)
        context.paint()


def make_css_value(value):
    return cssutils.css.value.PropertyValue(value)[0]


def absolute_background_position(css_values, bg_width, bg_height,
                                 image_width, image_height):
    """
    Parse cssutils Value objects for background-position and return
    (position_x, position_y) relative to the background’s top left corner,
    in pixels.

    http://www.w3.org/TR/CSS21/colors.html#propdef-background-position
    """
    if len(css_values) == 1:
        css_values = [css_values[0], make_css_value('center')]
    else:
        assert len(css_values) == 2

    horizontal = None
    vertical = None
    non_keywords = []
    for value in css_values:
        keyword = get_keyword(value)
        if keyword == 'top':
            assert vertical is None
            vertical = make_css_value('0%')
        elif keyword == 'bottom':
            assert vertical is None
            vertical = make_css_value('100%')
        elif keyword == 'left':
            assert horizontal is None
            horizontal = make_css_value('0%')
        elif keyword == 'right':
            assert horizontal is None
            horizontal = make_css_value('100%')
        elif keyword == 'center':
            if horizontal is None:
                horizontal = make_css_value('50%')
            else:
                vertical = make_css_value('50%')
        else:
            assert keyword is None
            non_keywords.append(value)

    # In that order. If both value are non-keyword, the first one
    # is horizontal and the second one vertical. list.pop() gives
    # the last value.
    if vertical is None:
        vertical = non_keywords.pop()
    if horizontal is None:
        horizontal = non_keywords.pop()

    vertical_pixels = background_position_value(
        vertical, bg_height, image_height)
    horizontal_pixels = background_position_value(
        horizontal, bg_width, image_width)
    return horizontal_pixels, vertical_pixels


def background_position_value(value, bg_size, image_size):
    pixels = get_pixel_value(value)
    if pixels is not None:
        return pixels

    percentage = get_percentage_value(value)
    assert percentage is not None
    return (bg_size - image_size) * percentage / 100.



def draw_border(context, box):
    """
    Draw the box border to a Cairo context.
    """
    # TODO: implement border-spacing, border-collapse and the other border style

    def get_edge(x, y, width, height):
        return (Point(x,y), Point(x+width,y), Point(x+width, y+height),
                Point(x, y+height))

    def get_border_area():
        # border area
        x = box.position_x + box.margin_left
        y = box.position_y + box.margin_top
        border_edge = get_edge(x, y, box.border_width(), box.border_height())
        # padding area
        x = x + box.border_left_width
        y = y + box.border_top_width
        padding_edge = get_edge(x, y, box.padding_width(), box.padding_height())
        return border_edge, padding_edge

    def get_lines(rectangle):
        n = len (rectangle)
        for i, point in enumerate(rectangle):
            yield Line(rectangle[i], rectangle[(i+1) % n])

    def get_trapezoids():
        border_edge, padding_edge = get_border_area()
        for line1,line2 in zip(get_lines(border_edge), get_lines(padding_edge)):
            yield Trapezoid(line1, line2)

    def draw_border_side(side, trapezoid):
        width = float(box.style['border-%s-width'%side][0].value)
        if box.style['border-%s-width'%side] == 0:
            return
        color = box.style['border-%s-color'%side][0]
        style = box.style['border-%s-style'%side][0].value
        if color.alpha > 0:
            with context.stacked():
                if not style in ["dotted", "dashed"]:
                    trapezoid.draw_path(context)
                    context.clip()
                elif style == "dotted":
                    #TODO:Find a way to make a real dotted border
                    context.set_dash([width], 0)
                elif style == "dashed":
                    #TODO:Find a way to make a real dashed border
                    context.set_dash([4*width], 0)
                line = trapezoid.get_middle_line()
                line.draw_path(context)
                context.set_source_colorvalue(color)
                context.set_line_width(width)
                context.stroke()

    trapezoids_side = zip(["top", "right", "bottom", "left"], get_trapezoids())

    for side, trapezoid in trapezoids_side:
        draw_border_side(side, trapezoid)


def draw_text(context, textbox):
    """
    Draw the given TextBox to a Cairo context from Pangocairo Context
    """
    fragment = text.TextLineFragment.from_textbox(textbox)
    context.move_to(textbox.position_x, textbox.position_y)
    context.show_layout(fragment.get_layout())


def draw_replacedbox(context, box):
    """
    Draw the given ReplacedBox to a Cairo context
    """
    x, y = box.padding_box_x(), box.padding_box_y()
    width, height = box.width, box.height
    with context.stacked():
        context.translate(x, y)
        context.rectangle(0, 0, width, height)
        context.clip()
        scale_width = width/box.replacement.intrinsic_width()
        scale_height = height/box.replacement.intrinsic_height()
        context.scale(scale_width, scale_height)
        box.replacement.draw(context)
