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

from ..css.utils import get_single_keyword
from ..formatting_structure import boxes
from .. import text
from .figures import Point, Line, Trapezoid


def get_surface_from_uri(uri):
    try:
        fileimage = urllib.urlopen(uri)
        if fileimage.info().gettype() != 'image/png':
            raise NotImplementedError("Only png images are implemented")
        return cairo.ImageSurface.create_from_png(fileimage)
    except IOError:
        return

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


def draw_background_on_entire_canvas(context, box):
    draw_background(context, box, on_entire_canvas=True)
    # Do not draw it again.
    box.skip_background = True


def draw_background(context, box, on_entire_canvas=False):
    """
    Draw the box background color and image to a Cairo context.
    """
    if getattr(box, 'skip_background', False):
        return


    with context.stacked():
        # Change coordinates to make the rest easier.
        context.translate(
            box.position_x + box.margin_left,
            box.position_y + box.margin_top)
        if not on_entire_canvas:
            context.rectangle(0, 0, box.border_width(), box.border_height())
            context.clip()
        # Background color
        bg_color = box.style['background-color'][0]
        if bg_color.alpha > 0:
            context.set_source_colorvalue(bg_color)
            context.paint()
        # Background image
        uri = box.style.get("background-image")[0].value
        if uri != 'none':
            absolute_uri = urljoin(box.element.base_url, uri)
            surface = get_surface_from_uri(absolute_uri)
            if surface:
                x, y = box.border_box_x(), box.border_box_y()
                width, height = box.border_width(), box.border_height()
                pattern = cairo.SurfacePattern(surface)
                pattern.set_extend(cairo.EXTEND_REPEAT)
                context.set_source(pattern)
                context.paint()


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
            context.save()
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
            context.restore()

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
    context.save()
    context.translate(x, y)
    context.rectangle(0, 0, width, height)
    context.clip()
    scale_width = width/box.replacement.intrinsic_width()
    scale_height = height/box.replacement.intrinsic_height()
    context.scale(scale_width, scale_height)
    box.replacement.draw(context)
    context.restore()
