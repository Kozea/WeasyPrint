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
from ..css.utils import get_single_keyword
from .. import replaced
from . import boxes


def build_formatting_structure(document):
    """
    Build a formatting structure (box tree) from a Document.
    """
    box = dom_to_box(document, document.dom)
    box = inline_in_block(box)
    box = block_in_inline(box)
    box = process_whitespace(box)
    return box


def dom_to_box(document, element):
    """
    Converts a DOM element (and its children) into a box (with children).

    Eg.

        <p>Some <em>emphasised</em> text.<p>

    gives (not actual syntax)

        BlockBox[
            TextBox['Some '],
            InlineBox[
                TextBox['emphasised'],
            ],
            TextBox[' text.'],
        ]

    TextBox`es are anonymous inline boxes:
    http://www.w3.org/TR/CSS21/visuren.html#anonymous
    """
    # TODO: should be the used value
    display = get_single_keyword(document.style_for(element).display)
    assert display != 'none'

    replacement = replaced.get_replaced_element(element)
    if replacement:
        if display in ('block', 'list-item', 'table'):
            type_ = boxes.BlockLevelReplacedBox
        elif display in ('inline', 'inline-table', 'inline-block'):
            type_ = boxes.InlineLevelReplacedBox
        else:
            raise NotImplementedError('Unsupported display: ' + display)
        box = type_(document, element, replacement)
        # The content is replaced, do not generate boxes for the element’s
        # text and children.
        return box

    if display in ('block', 'list-item'):
        box = boxes.BlockBox(document, element)
        #if display == 'list-item':
        #    TODO: add a box for the marker
    elif display == 'inline':
        box = boxes.InlineBox(document, element)
    elif display == 'inline-block':
        box = boxes.InlineBlockBox(document, element)
    else:
        raise NotImplementedError('Unsupported display: ' + display)

    # Ignore children on replaced elements.
    if isinstance(box, boxes.ParentBox):
        if element.text:
            box.add_child(boxes.TextBox(document, element, element.text))
        for child_element in element:
            if get_single_keyword(
                    document.style_for(child_element).display) != 'none':
                # TODO: We ignore html comments but also HTML/XML entities
                # we need find another way to ignore html comments
                if isinstance(child_element.tag, basestring):
                    box.add_child(dom_to_box(document, child_element))
            if child_element.tail:
                box.add_child(boxes.TextBox(
                    document, element, child_element.tail))

    return box


def process_whitespace(box):
    """
    First part of "The 'white-space' processing model"
    http://www.w3.org/TR/CSS21/text.html#white-space-model
    """
    following_collapsible_space = False
    for child in box.descendants():
        if not (hasattr(child, 'text') and child.text):
            continue

        text = child.text
        handling = get_single_keyword(child.style.white_space)

        text = re.sub('[\t\r ]*\n[\t\r ]*', '\n', text)
        if handling in ('pre', 'pre-wrap'):
            # \xA0 is the non-breaking space
            text = text.replace(' ', u'\xA0')
            if handling == 'pre-wrap':
                # "a line break opportunity at the end of the sequence"
                # \u200B is the zero-width space, marks a line break
                # opportunity.
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

        child.text = text
    return box


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
            TextBox['Some '],
            InlineBox[TextBox['text']],
            BlockBox[
                TextBox['More text'],
            ]
        ]

    is turned into

        BlockBox[
            AnonymousBlockBox[
                LineBox[
                    TextBox['Some '],
                    InlineBox[TextBox['text']],
                ]
            ]
            BlockBox[
                LineBox[
                    TextBox['More text'],
                ]
            ]
        ]
    """
    for child_box in getattr(box, 'children', []):
        inline_in_block(child_box)

    if not isinstance(box, boxes.BlockContainerBox):
        return

    line_box = boxes.LineBox(box.document, box.element)
    children = box.children
    box.empty()
    for child_box in children:
        if isinstance(child_box, boxes.BlockLevelBox):
            if line_box.children:
                # Inlines are consecutive no more: add this line box
                # and create a new one.
                anonymous = boxes.AnonymousBlockBox(box.document, box.element)
                anonymous.add_child(line_box)
                box.add_child(anonymous)
                line_box = boxes.LineBox(box.document, box.element)
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
            anonymous = boxes.AnonymousBlockBox(box.document, box.element)
            anonymous.add_child(line_box)
            box.add_child(anonymous)
        else:
            # Only inline-level children: one line box
            box.add_child(line_box)
    return box


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
                    TextBox['Hello.'],
                ],
                InlineBox[
                    TextBox['Some '],
                    InlineBox[
                        TextBox['text']
                        BlockBox[LineBox[TextBox['More text']]],
                        BlockBox[LineBox[TextBox['More text again']]],
                    ],
                    BlockBox[LineBox[TextBox['And again.']]],
                ]
            ]
        ]

    is turned into

        BlockBox[
            AnonymousBlockBox[
                LineBox[
                    InlineBox[
                        TextBox['Hello.'],
                    ],
                    InlineBox[
                        TextBox['Some '],
                        InlineBox[TextBox['text']],
                    ]
                ]
            ],
            BlockBox[LineBox[TextBox['More text']]],
            BlockBox[LineBox[TextBox['More text again']]],
            AnonymousBlockBox[
                LineBox[
                    InlineBox[
                    ]
                ]
            ],
            BlockBox[LineBox[TextBox['And again.']]],
            AnonymousBlockBox[
                LineBox[
                    InlineBox[
                    ]
                ]
            ],
        ]
    """
    # TODO: when splitting inline boxes, mark which are starting, ending, or
    # in the middle of the original box (for drawing borders).

    if not isinstance(box, boxes.ParentBox):
        return box

    new_box = box.copy()
    new_box.empty()
    for child in box.children:
        if isinstance(child, boxes.LineBox):
            assert len(box.children) == 1, ('Line boxes should have no '
                'siblings at this stage, got %r.' % box.children)
            while 1:
                new_line, block_level_box = _inner_block_in_inline(child)
                if block_level_box is None:
                    break
                _add_anonymous_block(new_box, new_line)
                new_box.add_child(block_level_box)
                # Loop with the same child
            if new_box.children:
                # Some children were already added, this became a block
                # context.
                _add_anonymous_block(new_box, new_line)
            else:
                # Keep the single line box as-is, without anonymous blocks.
                new_box.add_child(new_line)
        else:
            # Not in an inline formatting context.
            new_box.add_child(block_in_inline(child))
    return new_box


def _add_anonymous_block(box, child):
    """
    Wrap the child in an AnonymousBlockBox and add it to box.
    """
    anon_block = boxes.AnonymousBlockBox(box.document, box.element)
    anon_block.add_child(child)
    box.add_child(anon_block)


def _inner_block_in_inline(box):
    """
    Return (new_box, block_level_box)
    block_level_box is a box when breaking, None otherwise.
    """
    if not isinstance(box, boxes.ParentBox):
        return box, None

    new_box = box.copy()
    new_box.empty()
    block_level_box = None
    while box.children:
        # Empty the children list from the left so that we can continue
        # at the same point when we get here again after a break.
        child = box.children.popleft()
        if isinstance(child, boxes.BlockLevelBox):
            return new_box, child
        elif isinstance(child, (boxes.InlineBox, boxes.TextBox)):
            new_child, block_level_box = _inner_block_in_inline(child)
        else:
            # other inline-level: inline-block, inline-table, replaced
            new_child = block_in_inline(child)
        new_box.add_child(new_child)
        if block_level_box is not None:
            # Not finished with this child yet.
            box.children.appendleft(child)
            break
    return new_box, block_level_box
