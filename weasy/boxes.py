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


class AnonymousBlockLevelBox(BlockLevelBox):
    pass
    # self.style['display'] = PropertyValue('block')


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
    

def inline_in_block(box):
    """
    Consecutive inline-level boxes in a block-level box are wrapped into a
    line box, itself wrapped into an anonymous block-level box.
    (This line box will be broken into multiple lines later.)
    
    The box tree is changed *in place*.
    
    This is the first case in
    http://www.w3.org/TR/CSS21/visuren.html#anonymous-block-level
    
    Eg.
    
        BlockLevelBox[
            TextBox('Some '),
            InlineLevelBox[TextBox('text')],
            BlockLevelBox[
                TextBox('More text'),
            ]
        ]
    
    is turned into
    
        BlockLevelBox[
            AnonymousBlockLevelBox[
                LineBox[
                    TextBox('Some '),
                    InlineLevelBox[TextBox('text')],
                ]
            ]
            BlockLevelBox[
                LineBox[
                    TextBox('More text'),
                ]
            ]
        ]
    """
    for child_box in box.children or []:
        inline_in_block(child_box)

    if not isinstance(box, BlockLevelBox):
        return
    
    if len(box.children) == 1 and isinstance(box.children[0], LineBox):
        # It seems that this work was already done on this box.
        return
        
    line_box = LineBox(box.element)
    children = box.children
    box.children = []
    for child_box in children:
        assert not isinstance(child_box, LineBox)
        if isinstance(child_box, BlockLevelBox):
            if line_box.children:
                # Inlines are consecutive no more: add this line box
                # and create a new one.
                anonymous = AnonymousBlockLevelBox(box.element)
                anonymous.add_child(line_box)
                box.add_child(anonymous)
                line_box = LineBox(box.element)
            box.add_child(child_box)
        else:
            line_box.add_child(child_box)
    if line_box.children:
        # There were inlines at the end
        if box.children:
            anonymous = AnonymousBlockLevelBox(box.element)
            anonymous.add_child(line_box)
            box.add_child(anonymous)
        else:
            # Only inline-level children: one line box
            box.add_child(line_box)


def block_in_inline(box):
    """
    Inline-level boxes containing block-level boxes will be broken in two
    boxes on each side on consecutive block-level boxes, each side wrapped
    in an anonymous block-level box.

    This is the second case in
    http://www.w3.org/TR/CSS21/visuren.html#anonymous-block-level
    
    Eg.
    
        BlockLevelBox[
            LineBox[
                InlineLevelBox[
                    TextBox('Hello.'),
                ],
                InlineLevelBox[
                    TextBox('Some '),
                    InlineLevelBox[
                        TextBox('text')
                        BlockLevelBox[LineBox[TextBox('More text')]],
                        BlockLevelBox[LineBox[TextBox('More text again')]],
                    ],
                    BlockLevelBox[LineBox[TextBox('And again.')]],
                ]
            ]
        ]
    
    is turned into

        BlockLevelBox[
            AnonymousBlockLevelBox[
                LineBox[
                    InlineLevelBox[
                        TextBox('Hello.'),
                    ],
                    InlineLevelBox[
                        TextBox('Some '),
                        InlineLevelBox[TextBox('text')],
                    ]
                ]
            ],
            BlockLevelBox[LineBox[TextBox('More text')]],
            BlockLevelBox[LineBox[TextBox('More text again')]],
            AnonymousBlockLevelBox[
                LineBox[
                    InlineLevelBox[
                    ]
                ]
            ],
            BlockLevelBox[LineBox[TextBox('And again.')]],
            AnonymousBlockLevelBox[
                LineBox[
                    InlineLevelBox[
                    ]
                ]
            ],
        ]
    """
    # TODO: when splitting inline boxes, mark which are starting, ending, or
    # in the middle of the orginial box (for drawing borders).
    for child_box in box.children or []:
        block_in_inline(child_box)
    
    # TODO


