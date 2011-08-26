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

from . import helpers


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
    helpers.draw_page_background(context, page)
    helpers.draw_border(context, page)
    helpers.draw_box(context, page.root_box)
