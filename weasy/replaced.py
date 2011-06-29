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
Replaced elements (eg. <img> elements) are rendered externally and behave
as an atomic opaque box in CSS. They may or may not have intrinsic dimensions.
"""


def get_replaced_element(element):
    """
    Take a DOM element, determines whether it is replaced, and return a
    Replacement object if it is, None if it is not.
    """
    # TODO: maybe allow registering new replaced elements
    if element.tag == 'img':
        return ImageReplacement(element)
    else:
        return None


class Replacement(object):
    """
    Abstract base class for replaced elements
    """

    def __init__(self, element):
        self.element = element


class ImageReplacement(Replacement):
    """
    A replaced <img> element.
    """

