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
Specific handling for some HTML elements, especially replaced elements.

Replaced elements (eg. <img> elements) are rendered externally and behave
as an atomic opaque box in CSS. They may or may not have intrinsic dimensions.

"""

from __future__ import division

import cairo

from ..css.values import get_single_keyword, make_keyword
from ..formatting_structure import boxes
from ..utils import get_url_attribute
from ..draw.helpers import get_image_surface_from_uri


# Maps HTML tag names to function taking an HTML element and returning a Box.
HTML_HANDLERS = {}

# Marker saying that handle_element() has no special handling for this element
DEFAULT_HANDLING = object()


def handle_element(document, element):
    """Handle HTML elements that need special care.

    :returns: the :obj:`DEFAULT_HANDLING` constant if there is no special
              handling for this element, a :class:`Box` built with the special
              handling or, None if the element should be ignored.
    """
    if element.tag in HTML_HANDLERS:
        handler = HTML_HANDLERS[element.tag]
        return handler(document, element)
    else:
        return DEFAULT_HANDLING


def handler(tag):
    """
    Return a decorator that registers a function handling `tag` HTML elements.
    """
    def decorator(function):
        HTML_HANDLERS[tag] = function
        return function
    return decorator


def is_block_level(document, element):
    """
    Return True if the element is block-level, False if it is inline-level,
    and raise ValueError if it is neither.
    """
    display = get_single_keyword(document.style_for(element).display)

    if display in ('block', 'list-item', 'table'):
        return True
    elif display in ('inline', 'inline-table', 'inline-block'):
        return False
    else:
        raise ValueError('Unsupported display: ' + display)


def make_replaced_box(document, element, replacement):
    """
    Wrap a :class:`Replacement` object in either replaced box.
    That box is either block-level or inline-level, depending on what
    the element should be.
    """
    if is_block_level(document, element):
        type_ = boxes.BlockLevelReplacedBox
    else:
        type_ = boxes.InlineLevelReplacedBox
    return type_(document, element, replacement)


def make_text_box(document, element, text):
    """
    Make a text box and, if the element should be block-level, wrap it in
    a block box.
    """
    text_box = boxes.TextBox(document, element, text)
    if is_block_level(document, element):
        block = boxes.BlockBox(document, element)
        block.add_child(text_box)
        return block
    else:
        return text_box


@handler('img')
def handle_img(document, element):
    """
    Handle <img> tags: return either an image or the alt-text.

    http://www.w3.org/TR/html5/embedded-content-1.html#the-img-element
    """
    src = get_url_attribute(element, 'src')
    alt = element.get('alt')
    if src:
        surface = document.get_image_surface_from_uri(src)
        if surface is not None:
            replacement = ImageReplacement(surface)
            return make_replaced_box(document, element, replacement)
        else:
            # Invalid image, use the alt-text.
            if alt:
                return make_text_box(document, element, alt)
            elif alt == '':
                # The element represents nothing
                return None
            else:
                assert alt is None
                # TODO: find some indicator that an image is missing.
                # For now, just remove the image.
                return None
    else:
        if alt:
            return make_text_box(document, element, alt)
        else:
            return None


@handler('br')
def handle_br(document, element):
    """
    Handle <br> tags: return a preserved new-line character.
    """
    box = boxes.TextBox(document, element, '\n')
    box.style.white_space = [make_keyword('pre')]
    return box


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

    :param surface: a cairo :class:`ImageSurface` object.

    """
    def __init__(self, surface):
        self.surface = surface

    def intrinsic_width(self):
        return self.surface.get_width()

    def intrinsic_height(self):
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
