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


import cairo
import pangocairo

from .css.computed_values import LENGTHS_TO_PIXELS
from .formatting_structure import boxes
from . import text
import math

class CairoContext(cairo.Context):
    """
    A cairo.Context with a few more helper methods.
    """
    def show_layout(self, layout):
        pangocairo_context = pangocairo.CairoContext(self)
        pangocairo_context.set_antialias(cairo.ANTIALIAS_SUBPIXEL)
        pangocairo_context.show_layout(layout)

    def set_source_colorvalue(self, color):
        """Set the source pattern from a cssutils ColorValue object."""
        self.set_source_rgba(
            color.red / 255., color.green / 255., color.blue / 255.,
            color.alpha)

class Point(object):
    def __init__(self, x, y):
        self.x = round(x)
        self.y = round(y)

    def __repr__(self):
        return '<%s (%d, %d)>' % (type(self).__name__, self.x, self.y)

    def move_to(self, x, y):
        self.x +=x
        self.y +=y

    def copy(self):
        """Return copy of the point."""
        cls = type(self)
        return cls(self.x, self.y)

class Line(object):
    def __init__(self, point1, point2):
        self.first_point = point1
        self.second_point = point2
        self.type = "solid"

    def __repr__(self):
        return '<%s (%s, %s)>' % (type(self).__name__, self.first_point,
                                 self.second_point)

    def translate(self, x, y):
        self.first_point.move(x, y)
        self.second_point.move(x, y)

    @property
    def length(self):
        diff_x = self.second_point.x - self.first_point.x
        diff_y = self.second_point.y - self.first_point.y
        return math.sqrt(math.pow(diff_x, 2) + math.pow(diff_y, 2))

    def draw_path(self, context):
        context.move_to(self.first_point.x, self.first_point.y)
        context.line_to(self.second_point.x, self.second_point.y)

    def copy(self):
        """Return copy of the line."""
        cls = type(self)
        return cls(self.first_point.copy(), self.second_point.copy())


class Trapezoid(object):
    def __init__(self, line1, line2):
        if line1.length > line2.length:
            self.long_base = line1
            self.small_base = line2
        else:
            self.long_base = line2
            self.small_base = line1

    def __repr__(self):
        return '<%s (%s, %s)>' % (type(self).__name__, self.small_base,
                                  self.small_base)

    def get_points(self):
        return [self.long_base.first_point, self.small_base.first_point,
                self.small_base.second_point, self.long_base.second_point]

    def get_all_lines(self):
        points = list(self.get_points())
        n = len (points)
        for i, point in enumerate(points):
            yield Line(points[i], points[(i+1)%n])

    def get_side_lines(self):
        points = list(self.get_points())
        n = len (points)
        for i, point in enumerate(points):
            if i % 2 == 0:
                yield Line(points[i], points[(i+1)%n])

    def get_middle_line(self):
        if self.long_base.first_point.x != self.long_base.second_point.x:
            x1 = self.long_base.first_point.x
            x2 = self.long_base.second_point.x
        else:
            x1 = (self.long_base.first_point.x + self.small_base.first_point.x)
            x1 = x1 / 2.
            x2 = x1
        if self.long_base.first_point.y != self.long_base.second_point.y:
            y1 = self.long_base.first_point.y
            y2 = self.long_base.second_point.y
        else:
            y1 = (self.long_base.first_point.y + self.small_base.first_point.y)
            y1 = y1 / 2.
            y2 = y1
        return Line(Point(x1,y1), Point(x2, y2))

    def draw_path(self, context):
        for i, line in enumerate(self.get_all_lines()):
            if i == 0:
                context.move_to(line.first_point.x, line.first_point.y)
            context.line_to(line.second_point.x, line.second_point.y)

    def translate(self, x, y):
        self.first_point.translate(x, y)
        self.second_point.translate(x, y)


def draw_background(context, box):
    bg_color = box.style['background-color'][0]
    if bg_color.alpha > 0:
        context.rectangle(
            box.position_x + box.margin_left,
            box.position_y + box.margin_top,
            box.border_width(),
            box.border_height())
        context.set_source_colorvalue(bg_color)
        context.fill()


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
                #TODO:Find a way to make a dotted border
                context.set_dash([width], 0)
            elif style == "dashed":
                #TODO:Find a way to make a dashed border
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

def draw_box(context, box):
    draw_background(context, box)

    if isinstance(box, boxes.TextBox):
        draw_text(context, box)
        return

    for child in box.children:
        draw_box(context, child)
    if box.border_left_width > 0:
        draw_border(context, box)

def draw_page(page, context):
    """
    Draw the given PageBox to a Cairo context.
    The context should be scaled so that lengths are in CSS pixels.
    """
    draw_box(context, page.root_box)
