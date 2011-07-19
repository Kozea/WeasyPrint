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
This module builds a correct formatting structure from a DOM document,
including handling of anonymous boxes and whitespace processing.
"""


import re
from .. import replaced
from . import boxes


def build_formatting_structure(document):
    """
    Build a formatting structure (box tree) from a DOM document.
    """
    box = dom_to_box(document)
    inline_in_block(box)
    block_in_inline(box)
    process_whitespace(box)
    return box


def dom_to_box(element):
    """
    Converts a DOM element (and its children) into a box (with children).

    Eg.

        <p>Some <em>emphasised</em> text.<p>

    gives (not actual syntax)

        BlockBox[
            TextBox('Some '),
            InlineBox[
                TextBox('emphasised'),
            ],
            TextBox(' text.'),
        ]

    TextBox`es are anonymous inline boxes:
    http://www.w3.org/TR/CSS21/visuren.html#anonymous
    """
    display = element.style.display # TODO: should be the used value
    assert display != 'none'

    replacement = replaced.get_replaced_element(element)
    if replacement:
        if display in ('block', 'list-item', 'table'):
            box = boxes.BlockLevelReplacedBox(element, replacement)
        elif display in ('inline', 'inline-table', 'inline-block'):
            box = boxes.InlineLevelReplacedBox(element, replacement)
        else:
            raise NotImplementedError('Unsupported display: ' + display)
        # The content is replaced, do not generate boxes for the element’s
        # text and children.
        return box

    if display in ('block', 'list-item'):
        box = boxes.BlockBox(element)
        #if display == 'list-item':
        #    TODO: add a box for the marker
    elif display == 'inline':
        box = boxes.InlineBox(element)
    elif display == 'inline-block':
        box = boxes.InlineBlockBox(element)
    else:
        raise NotImplementedError('Unsupported display: ' + display)

    if element.text:
        box.add_child(boxes.TextBox(element, element.text))
    for child_element in element:
        if child_element.style.display != 'none':
            box.add_child(dom_to_box(child_element))
        if child_element.tail:
            box.add_child(boxes.TextBox(element, child_element.tail))

    return box


def process_whitespace(box):
    """
    First part of "The 'white-space' processing model"
    http://www.w3.org/TR/CSS21/text.html#white-space-model
    """
    following_collapsible_space = False
    for box in box.descendants():
        if not (hasattr(box, 'text') and box.text):
            continue

        text = box.text
        handling = box.style.white_space

        text = re.sub('[\t\r ]*\n[\t\r ]*', '\n', text)
        if handling in ('pre', 'pre-wrap'):
            # \xA0 is the non-breaking space
            text = text.replace(' ', u'\xA0')
            if handling == 'pre-wrap':
                # "a line break opportunity at the end of the sequence"
                # \u200B is the zero-width space, marks a line break opportunity.
                text = re.sub(u'\xA0([^\xA0]|$)', u'\xA0\u200B\\1', text)
        elif handling in ('normal', 'nowrap'):
            # TODO: this should be language-specific
            # Could also replace with a zero width space character (U+200B),
            # or no character
            # CSS3: http://www.w3.org/TR/css3-text/#line-break-transform
            text = text.replace('\n', ' ')

        if handling in ('normal', 'nowrap', 'pre-line'):
            text = text.replace('\t', ' ')
            text = re.sub(' +', ' ', text)
            if following_collapsible_space and text.startswith(' '):
                text = text[1:]
            following_collapsible_space = text.endswith(' ')
        else:
            following_collapsible_space = False

        box.text = text


def inline_in_block(box):
    """
    Consecutive inline-level boxes in a block container box are wrapped into a
    line box, itself wrapped into an anonymous block box.
    (This line box will be broken into multiple lines later.)

    The box tree is changed *in place*.

    This is the first case in
    http://www.w3.org/TR/CSS21/visuren.html#anonymous-block-level

    Eg.

        BlockBox[
            TextBox('Some '),
            InlineBox[TextBox('text')],
            BlockBox[
                TextBox('More text'),
            ]
        ]

    is turned into

        BlockBox[
            AnonymousBlockBox[
                LineBox[
                    TextBox('Some '),
                    InlineBox[TextBox('text')],
                ]
            ]
            BlockBox[
                LineBox[
                    TextBox('More text'),
                ]
            ]
        ]
    """
    for child_box in getattr(box, 'children', []):
        inline_in_block(child_box)

    if not isinstance(box, boxes.BlockContainerBox):
        return

    line_box = boxes.LineBox(box.element)
    children = box.children
    box.children = []
    for child_box in children:
        if isinstance(child_box, boxes.BlockLevelBox):
            if line_box.children:
                # Inlines are consecutive no more: add this line box
                # and create a new one.
                anonymous = boxes.AnonymousBlockBox(box.element)
                anonymous.add_child(line_box)
                box.add_child(anonymous)
                line_box = boxes.LineBox(box.element)
            box.add_child(child_box)
        elif isinstance(child_box, boxes.LineBox):
            # Merge the line box we just found with the new one we are making
            for child in child_box.children:
                line_box.add_child(child)
        else:
            line_box.add_child(child_box)
    if line_box.children:
        # There were inlines at the end
        if box.children:
            anonymous = boxes.AnonymousBlockBox(box.element)
            anonymous.add_child(line_box)
            box.add_child(anonymous)
        else:
            # Only inline-level children: one line box
            box.add_child(line_box)


def block_in_inline(box):
    """
    Inline boxes containing block-level boxes will be broken in two
    boxes on each side on consecutive block-level boxes, each side wrapped
    in an anonymous block-level box.

    This is the second case in
    http://www.w3.org/TR/CSS21/visuren.html#anonymous-block-level

    Eg.

        BlockBox[
            LineBox[
                InlineBox[
                    TextBox('Hello.'),
                ],
                InlineBox[
                    TextBox('Some '),
                    InlineBox[
                        TextBox('text')
                        BlockBox[LineBox[TextBox('More text')]],
                        BlockBox[LineBox[TextBox('More text again')]],
                    ],
                    BlockBox[LineBox[TextBox('And again.')]],
                ]
            ]
        ]

    is turned into

        BlockBox[
            AnonymousBlockBox[
                LineBox[
                    InlineBox[
                        TextBox('Hello.'),
                    ],
                    InlineBox[
                        TextBox('Some '),
                        InlineBox[TextBox('text')],
                    ]
                ]
            ],
            BlockBox[LineBox[TextBox('More text')]],
            BlockBox[LineBox[TextBox('More text again')]],
            AnonymousBlockBox[
                LineBox[
                    InlineBox[
                    ]
                ]
            ],
            BlockBox[LineBox[TextBox('And again.')]],
            AnonymousBlockBox[
                LineBox[
                    InlineBox[
                    ]
                ]
            ],
        ]
    """
    # TODO: when splitting inline boxes, mark which are starting, ending, or
    # in the middle of the orginial box (for drawing borders).
    for child_box in getattr(box, 'children', []):
        block_in_inline(child_box)

    if not (isinstance(box, boxes.BlockLevelBox) and box.parent
            and isinstance(box.parent, boxes.InlineBox)):
        return

    # Find all ancestry until a line box.
    inline_parents = []
    for parent in box.ancestors():
        inline_parents.append(parent)
        if not isinstance(parent, boxes.InlineBox):
            assert isinstance(parent, boxes.LineBox)
            parent_line_box = parent
            break

    # Add an anonymous block level box before the block box
    if isinstance(parent_line_box.parent, boxes.AnonymousBlockBox):
        previous_anonymous_box = parent_line_box.parent
    else:
        previous_anonymous_box = boxes.AnonymousBlockBox(
            parent_line_box.element)
        parent_line_box.parent.add_child(
            previous_anonymous_box, parent_line_box.index)
        parent_line_box.parent.children.remove(parent_line_box)
        previous_anonymous_box.add_child(parent_line_box)

    # Add an anonymous block level box after the block box
    next_anonymous_box = boxes.AnonymousBlockBox(parent_line_box.element)
    previous_anonymous_box.parent.add_child(
        next_anonymous_box, previous_anonymous_box.index + 1)

    # Recreate anonymous inline boxes clones from the split inline boxes
    clone_box = next_anonymous_box
    while inline_parents:
        parent = inline_parents.pop()
        next_clone_box = type(parent)(parent.element)
        clone_box.add_child(next_clone_box)
        clone_box = next_clone_box

    splitter_box = box
    for parent in box.ancestors():
        if parent == parent_line_box:
            break

        next_children = parent.children[splitter_box.index + 1:]
        parent.children = parent.children[:splitter_box.index + 1]

        for child in next_children:
            clone_box.add_child(child)

        splitter_box = parent
        clone_box = clone_box.parent

    # Put the block element before the next_anonymous_box
    box.parent.children.remove(box)
    previous_anonymous_box.parent.add_child(
        box, previous_anonymous_box.index + 1)
