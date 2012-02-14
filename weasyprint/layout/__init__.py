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
Module managing the layout creation before drawing a document.

"""

from .pages import make_all_pages, add_margin_boxes


def layout(document):
    """Lay out the whole document.

    This includes line breaks, page breaks, absolute size and position for all
    boxes.

    :param document: a Document object.
    :returns: a list of laid out Page objects.

    """
    pages = list(make_all_pages(document))
    return list(add_margin_boxes(document, pages))
