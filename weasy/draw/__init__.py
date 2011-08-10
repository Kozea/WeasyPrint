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
import contextlib

import cairo
import pangocairo

from .helpers import has_background, draw_box, draw_background_on_entire_canvas


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

    @contextlib.contextmanager
    def stacked(self):
        self.save()
        try:
            yield
        finally:
            self.restore()


def draw_page(page, context):
    """
    Draw the given PageBox to a Cairo context.
    The context should be scaled so that lengths are in CSS pixels.
    """
    # http://www.w3.org/TR/CSS21/colors.html#background
    # Background for the root element is drawn on the entire canvas.
    # If the root is "html" and has no background, the background
    # for its "body" child is drawn on the entire canvas.
    # However backgrounds positions stay the same.
    if has_background(page.root_box):
        draw_background_on_entire_canvas(context, page.root_box)
    elif page.root_box.element.tag.lower() == 'html':
        for child in page.root_box.children:
            if child.element.tag.lower() == 'body' and has_background(child):
                # This must be drawn now, before anything on the root element.
                draw_background_on_entire_canvas(context, child)
                break

    draw_box(context, page.root_box)
