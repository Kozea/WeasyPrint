# coding: utf8
"""
    weasyprint.document
    -------------------

    Entry point to the rendering process.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from .css import get_all_computed_styles
from .formatting_structure.build import build_formatting_structure
from . import layout
from . import draw
from . import images


class Document(object):
    """Abstract output document."""
    def __init__(self, backend, dom, user_stylesheets, user_agent_stylesheets):
        self.backend = backend
        self.surface = backend.get_dummy_surface()
        self.dom = dom  #: lxml HtmlElement object
        self.user_stylesheets = user_stylesheets
        self.user_agent_stylesheets = user_agent_stylesheets
        self._image_cache = {}
        self._computed_styles = None
        self._formatting_structure = None
        self._pages = None
        self._excluded_shapes_lists = []

        self.create_block_formatting_context()

        # TODO: remove this when Margin boxes variable dimension is correct.
        self._auto_margin_boxes_warning_shown = False

    def style_for(self, element, pseudo_type=None):
        """
        Convenience method to get the computed styles for an element.
        """
        return self.computed_styles.get((element, pseudo_type))

    @property
    def computed_styles(self):
        """
        dict of (element, pseudo_element_type) -> StyleDict
        StyleDict: a dict of property_name -> PropertyValue,
                   also with attribute access
        """
        if self._computed_styles is None:
            self._computed_styles = get_all_computed_styles(
                self,
                user_stylesheets=self.user_stylesheets,
                ua_stylesheets=self.user_agent_stylesheets,
                medium='print')
        return self._computed_styles

    @property
    def formatting_structure(self):
        """
        The root of the formatting structure tree, ie. the Box
        for the root element.
        """
        if self._formatting_structure is None:
            self._formatting_structure = build_formatting_structure(
                self, self.computed_styles)
        return self._formatting_structure

    @property
    def pages(self):
        """
        List of layed-out pages with an absolute size and postition
        for every box.
        """
        if self._pages is None:
            self._pages = list(layout.layout_document(
                self, self.formatting_structure))
        return self._pages

    def get_image_from_uri(self, uri, type_=None):
        return images.get_image_from_uri(self._image_cache, uri, type_)

    def write_to(self, target):
        backend = self.backend(target)
        for page in self.pages:
            context = backend.start_page(page.outer_width, page.outer_height)
            draw.draw_page(self, page, context)

        backend.finish(self)

    def create_block_formatting_context(self):
        self.excluded_shapes = []
        self._excluded_shapes_lists.append(self.excluded_shapes)

    def finish_block_formatting_context(self, root_box):
        excluded_shapes = self._excluded_shapes_lists.pop()
        self.excluded_shapes = self._excluded_shapes_lists[-1]

        # See http://www.w3.org/TR/CSS2/visudet.html#root-height
        if root_box.style.height == 'auto':
            box_bottom = root_box.content_box_y() + root_box.height
            for shape in excluded_shapes:
                shape_bottom = shape.position_y + shape.margin_height()
                if shape_bottom > box_bottom:
                    root_box.height += shape_bottom - box_bottom
