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


import lxml.html

from .css import get_all_computed_styles, HTML4_DEFAULT_STYLESHEET
from .formatting_structure.build import build_formatting_structure
from .layout import layout


class Document(object):
    def __init__(self, dom):
        assert getattr(dom, 'tag', None) == 'html', (
            'HTML document expected, got %r.' % (dom,))

        self.user_stylesheets = []
        self.user_agent_stylesheets = [HTML4_DEFAULT_STYLESHEET]

        #: lxml HtmlElement object
        self.dom = dom

        # These are None for the steps that were not done yet.

        #: dict of (element, pseudo_element_type) -> StyleDict
        #: StyleDict: a dict of property_name -> PropertyValue,
        #:    also with attribute access
        self.computed_styles = None

        #: The Box object for the root element.
        self.formatting_structure = None

        #: Layed-out pages and boxes
        self.pages = None

    @classmethod
    def from_string(cls, source):
        """
        Make a document from an HTML string.
        """
        return cls(lxml.html.document_fromstring(source))

    @classmethod
    def from_file(cls, file_or_filename_or_url):
        """
        Make a document from a filename or open file object.
        """
        return cls(lxml.html.parse(file_or_filename_or_url).getroot())

    def style_for(self, element, pseudo_type=None):
        """
        Convenience method to get the computed styles for an element.
        """
        return self.computed_styles[(element, pseudo_type)]

    def do_css(self):
        """
        Do the "CSS" step if it is not done yet: get computed styles for
        every element.
        """
        if self.computed_styles is None:
            self.computed_styles = get_all_computed_styles(
                self,
                user_stylesheets=self.user_stylesheets,
                ua_stylesheets=self.user_agent_stylesheets,
                medium='print')

    def do_boxes(self):
        """
        Do the "boxes" step if it is not done yet: build the formatting
        structure for the document a tree of boxes.
        """
        self.do_css()
        if self.formatting_structure is None:
            self.formatting_structure = build_formatting_structure(self)

    def do_layout(self):
        """
        Do the "layout" step if it is not done yet: build a list of layed-out
        pages with an absolute size and postition for every box.
        """
        self.do_boxes()
        if self.pages is None:
            self.pages = layout(self)
