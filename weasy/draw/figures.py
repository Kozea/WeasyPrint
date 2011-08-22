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
Classes defining geometrical figures.

"""

from __future__ import division


class Point(object):
    """Couple of integer coordinates."""
    def __init__(self, x, y):
        self.x = round(x)
        self.y = round(y)

    def __repr__(self):
        return '<%s (%d, %d)>' % (type(self).__name__, self.x, self.y)

    def move_to(self, x, y):
        """Change the coordinates."""
        self.x += x
        self.y += y

    def copy(self):
        """Return a copy of the point."""
        return type(self)(self.x, self.y)


class Line(object):
    """Couple of :class:`Point` objects."""
    def __init__(self, point1, point2):
        self.first_point = point1
        self.second_point = point2
        self.type = 'solid'

    def __repr__(self):
        return '<%s (%s, %s)>' % (
            type(self).__name__, self.first_point, self.second_point)

    @property
    def length(self):
        """Distance between the 2 points of the line."""
        diff_x = self.second_point.x - self.first_point.x
        diff_y = self.second_point.y - self.first_point.y
        return (diff_x ** 2 + diff_y ** 2) ** 0.5

    def draw_path(self, context):
        """Draw the line path on the ``context``."""
        context.move_to(self.first_point.x, self.first_point.y)
        context.line_to(self.second_point.x, self.second_point.y)

    def copy(self):
        """Return a copy of the line with a copy of its points."""
        return type(self)(self.first_point.copy(), self.second_point.copy())


class Trapezoid(object):
    """Horizontal or vertical trapezoid."""
    def __init__(self, line1, line2):
        if line1.length > line2.length:
            self.long_base, self.small_base = line1, line2
        else:
            self.long_base, self.small_base = line2, line1

    def __repr__(self):
        return '<%s (%s, %s)>' % (
            type(self).__name__, self.small_base, self.small_base)

    def get_points(self):
        """Get the 4 points of the trapezoid."""
        return [self.long_base.first_point, self.small_base.first_point,
                self.small_base.second_point, self.long_base.second_point]

    def get_all_lines(self):
        """Get the 4 lines of the trapezoid."""
        points = list(self.get_points())
        lines_number = len(points)
        for i in range(lines_number):
            yield Line(points[i], points[(i + 1) % lines_number])

    def get_side_lines(self):
        """Get the non horizontal or vertical sides of the trapezoid."""
        points = list(self.get_points())
        lines_number = len(points)
        for i in range(lines_number):
            if not i % 2:
                yield Line(points[i], points[(i + 1) % lines_number])

    def get_middle_line(self):
        r"""Get the middle line of trapezoid.

        Here is what the middle line is for an horizontal trapezoid::

          +---------------+
           \             /
          =================
             \         /
              +-------+

        The middle line is the line drawn by the equal '=' sign.

        """
        if self.long_base.first_point.x != self.long_base.second_point.x:
            x1 = self.long_base.first_point.x
            x2 = self.long_base.second_point.x
        else:
            x1 = self.long_base.first_point.x + self.small_base.first_point.x
            x1, x2 = x1 / 2, x1
        if self.long_base.first_point.y != self.long_base.second_point.y:
            y1 = self.long_base.first_point.y
            y2 = self.long_base.second_point.y
        else:
            y1 = self.long_base.first_point.y + self.small_base.first_point.y
            y1, y2 = y1 / 2, y1
        return Line(Point(x1, y1), Point(x2, y2))

    def draw_path(self, context):
        """Draw the path of the trapezoid on the ``context``."""
        for i, line in enumerate(self.get_all_lines()):
            if i == 0:
                context.move_to(line.first_point.x, line.first_point.y)
            context.line_to(line.second_point.x, line.second_point.y)
