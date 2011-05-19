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


import re
from . import css


class Box(object):
    def __init__(self, element):
        # Should never be None
        self.element = element
        # No parent yet. Will be set when this box is added to another box’s
        # children. Only the root box should stay without a parent.
        self.parent = None
        self.children = []
        # Computed values
        #self.style = ...
    
    def add_child(self, child):
        """
        Add the new child to this box’s children list and set this box as the
        child’s parent.
        """
        child.parent = self
        self.children.append(child)


class BlockLevelBox(Box):
    pass


class LineBox(Box):
    pass


class InlineLevelBox(Box):
    pass


class TextBox(Box):
    def __init__(self, element, text):
        super(TextBox, self).__init__(element)
        self.children = None
        self.text = text



def dom_to_box(element):
    """
    Converts a DOM element (and its children) into a box (with children).
    
    Eg.
    
        <p>Some <em>emphasised</em> text.<p>
    
    gives (not actual syntax)
    
        BlockLevelBox[
            TextBox('Some '),
            InlineLevelBox[
                TextBox('emphasised'),
            ],
            TextBox(' text.'),
        ]
    
    TextBox`es are anonymous inline boxes:
    http://www.w3.org/TR/CSS21/visuren.html#anonymous
    """
    display = element.style.display # TODO: should be the used value
    assert display != 'none'
    
    if display in ('block', 'list-item', 'table') \
            or display.startswith('table-'):
        # The element generates a block-level box
        box = BlockLevelBox(element)
    elif display in ('inline', 'inline-block', 'inline-table', 'ruby'):
        # inline-level box
        box = InlineLevelBox(element)
    else:
        raise NotImplementedError('Unsupported display: ' + display)
    
    if element.text:
        box.add_child(TextBox(element, element.text))
    for child_element in element:
        if child_element.style.display != 'none':
            box.add_child(dom_to_box(child_element))
        if child_element.tail:
            box.add_child(TextBox(element, child_element.tail))
    
    return box
    


