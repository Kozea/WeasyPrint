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

class CairoContext(cairo.Context):
    """
    A cairo.Context with a few more helper methods.
    """

    def set_source_colorvalue(self, color):
        """Set the source pattern from a cssutils ColorValue object."""
        self.set_source_rgba(
            color.red / 255., color.green / 255., color.blue / 255.,
            color.alpha)

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

def draw_text(context, textbox):
    """
    Draw the given TextBox to a Cairo context from Pangocairo Context
    """
    fragment = text.TextLineFragment()
    fragment.set_textbox(textbox)
    layout = fragment.get_layout()
    context.move_to(textbox.position_x, textbox.position_y)
    pangocairo_context = pangocairo.CairoContext(context)
#    pangocairo_context.set_antialias(cairo.ANTIALIAS_SUBPIXEL)
    pangocairo_context.show_layout(layout)


def draw_box(context, box):
    draw_background(context, box)

    if isinstance(box, boxes.TextBox):
        draw_text(context, box)
        return

    for child in box.children:
        draw_box(context, child)


def draw_page(page, context):
    """
    Draw the given PageBox to a Cairo context.
    """
    draw_box(context, page.root_box)


def draw_page_to_png(page, file_like):
    """
    Draw the given PageBox to a PNG file.
    """
    width = int(page.outer_width)
    height = int(page.outer_height)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    context = CairoContext(surface)
    draw_page(page, context)
    surface.write_to_png(file_like)
    surface.finish()


def draw_to_pdf(pages, file_like):
    """
    Draw the given PageBox’es to a PDF file.
    """
    # Use a dummy page size initially
    surface = cairo.PDFSurface(file_like, 1, 1)
    px_to_pt = 1 / LENGTHS_TO_PIXELS['pt']
    for page in pages:
        # Actual page size is here. May be different between pages.
        surface.set_size(
            page.outer_width * px_to_pt,
            page.outer_height * px_to_pt)
        context = CairoContext(surface)
        context.scale(px_to_pt, px_to_pt)
        draw_page(page, context)
        surface.show_page()
    surface.finish()
