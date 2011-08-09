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
import math

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

class Rectangle(object):
    def __init__(self, point1, point3):
        self.point1 = point1
        self.point2 = Point(point3.x, point1.y)
        self.point3 = point3
        self.point4 = Point(point1.x, point3.y)

    def get_points(self):
        return [self.point1, self.point3, self.point3, self.point4]


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

