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
Classes and helpers for HTML replaced elements.

Replaced elements (eg. <img> elements) are rendered externally and behave
as an atomic opaque box in CSS. They may or may not have intrinsic dimensions.

"""

from __future__ import division

import cairo

from .utils import get_url_attribute
from .draw.helpers import get_image_surface_from_uri


REPLACEMENT_HANDLERS = {}


def get_replaced_element(element):
    """Return a :class:`Replacement` object if ``element`` is replaced."""
    if element.tag in REPLACEMENT_HANDLERS:
        handler = REPLACEMENT_HANDLERS[element.tag]
        return handler(element)


def register(tag):
    """
    Return a decorator that registers a function handling replacements for
    `tag` HTML elements.
    """
    def decorator(function):
        REPLACEMENT_HANDLERS[tag] = function
        return function
    return decorator


@register('img')
def handle_img(element):
    """
    Handle <img> tags: return either an image or the alt-text.
    """
    # TODO: somehow use the alt-text on broken images.
    src = get_url_attribute(element, 'src')
    return ImageReplacement(src)


class Replacement(object):
    """Abstract base class for replaced elements. """
    def intrinsic_width(self):
        """Intrinsic width if defined."""

    def intrinsic_height(self):
        """Intrinsic height if defined."""

    def intrinsic_ratio(self):
        """Intrinsic ratio if defined."""
        if (self.intrinsic_width() is not None and
            self.intrinsic_width() != 0 and
            self.intrinsic_height() is not None and
            self.intrinsic_height() != 0):
            return self.intrinsic_width() / self.intrinsic_height()


class ImageReplacement(Replacement):
    """Replaced ``<img>`` element.

    :param image_uri: uri where to get the image.

    """
    def __init__(self, image_uri):
        self.surface = get_image_surface_from_uri(image_uri)

    def intrinsic_width(self):
        if self.surface:
            return self.surface.get_width()

    def intrinsic_height(self):
        if self.surface:
            return self.surface.get_height()

    def draw(self, context):
        """Draw the element on the Cairo context."""
        if not self.surface:
            # TODO Draw the alternative text ?
            pass
        else:
            pattern = cairo.SurfacePattern(self.surface)
            context.set_source(pattern)
            context.paint()

