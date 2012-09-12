# coding: utf8
"""
    weasyprint.document
    -------------------

    Entry point to the rendering process.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import io
import sys
import math
import functools

import cairo

from .css import get_all_computed_styles
from .formatting_structure.build import build_formatting_structure
from . import layout
from . import images


class Document(object):
    """Abstract output document."""
    def __init__(self, element_tree, enable_hinting, url_fetcher, media_type,
                 user_stylesheets, ua_stylesheets):
        self.element_tree = element_tree  #: lxml HtmlElement object
        self.enable_hinting = enable_hinting
        self.style_for = get_all_computed_styles(
            element_tree, media_type, url_fetcher,
            user_stylesheets, ua_stylesheets)
        self.get_image_from_uri =  functools.partial(
            images.get_image_from_uri, {}, url_fetcher)

    def render_pages(self):
        """Do the layout and return a list of page boxes."""
        return list(layout.layout_document(
            self.enable_hinting, self.style_for, self.get_image_from_uri,
            build_formatting_structure(
                self.element_tree, self.style_for, self.get_image_from_uri)))
