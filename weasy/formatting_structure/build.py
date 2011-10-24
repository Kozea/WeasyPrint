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
Building helpers.

Functions building a correct formatting structure from a DOM document,
including handling of anonymous boxes and whitespace processing.

"""

import re
from . import boxes
from .. import html


GLYPH_LIST_MARKERS = {
    'disc': u'•',  # U+2022, BULLET
    'circle': u'◦',  # U+25E6 WHITE BULLET
    'square': u'▪',  # U+25AA BLACK SMALL SQUARE
}


def build_formatting_structure(document):
    """Build a formatting structure (box tree) from a ``document``."""
    box = dom_to_box(document, document.dom)
    assert box is not None
    box = inline_in_block(box)
    box = block_in_inline(box)
    box = process_whitespace(box)
    return box


def dom_to_box(document, element):
    """Convert a DOM element and its children into a box with children.

    Eg.::

        <p>Some <em>emphasised</em> text.<p>

    gives (not actual syntax)::

        BlockBox[
            TextBox['Some '],
            InlineBox[
                TextBox['emphasised'],
            ],
            TextBox[' text.'],
        ]

    ``TextBox``es are anonymous inline boxes:
    See http://www.w3.org/TR/CSS21/visuren.html#anonymous

    """
    # TODO: should be the used value. When does the used value for `display`
    # differ from the computer value?
    style = document.style_for(element)
    display = style.display
    if display == 'none':
        return None

    result = html.handle_element(document, element)
    if result is not html.DEFAULT_HANDLING:
        # Specific handling for the element. (eg. replaced element)
        return result

    children = []

    if element.text:
        text = text_transform(element.text, style)
        children.append(boxes.TextBox(document, element, text))
    for child_element in element:
        # lxml.html already converts HTML entities to text.
        # Here we ignore comments and XML processing instructions.
        if isinstance(child_element.tag, basestring):
            child_box = dom_to_box(document, child_element)
            if child_box is not None:
                children.append(child_box)
            # else: child_element had `display: none`
        if child_element.tail:
            text = text_transform(child_element.tail, style)
            if children and isinstance(children[-1], boxes.TextBox):
                children[-1].utf8_text += text.encode('utf8')
            else:
                children.append(boxes.TextBox(document, element, text))

    if display in ('block', 'list-item'):
        box = boxes.BlockBox(document, element, children)
        if display == 'list-item':
            box = add_box_marker(box)
    elif display == 'inline':
        box = boxes.InlineBox(document, element, children)
    elif display == 'inline-block':
        box = boxes.InlineBlockBox(document, element, children)
    else:
        raise NotImplementedError('Unsupported display: ' + display)
    assert isinstance(box, boxes.ParentBox)

    return box


def add_box_marker(box):
    """Return a box with a list marker to elements with ``display: list-item``.

    See http://www.w3.org/TR/CSS21/generate.html#lists

    """
    image = box.style.list_style_image
    if image != 'none':
        # surface may be None here too, in case the image is not available.
        surface = box.document.get_image_surface_from_uri(image)
    else:
        surface = None

    if surface is None:
        type_ = box.style.list_style_type
        if type_ == 'none':
            return box
        marker = GLYPH_LIST_MARKERS[type_]
        marker_box = boxes.TextBox(box.document, box.element, marker)
    else:
        replacement = html.ImageReplacement(surface)
        marker_box = boxes.ImageMarkerBox(
            box.document, box.element, replacement)

    position = box.style.list_style_position
    if position == 'inside':
        # U+00A0, NO-BREAK SPACE
        spacer = boxes.TextBox(box.document, box.element, u'\u00a0')
        return box.copy_with_children((marker_box, spacer) + box.children)
    elif position == 'outside':
        box.outside_list_marker = marker_box
    return box


def process_whitespace(box):
    """First part of "The 'white-space' processing model".

    See http://www.w3.org/TR/CSS21/text.html#white-space-model

    """
    following_collapsible_space = False
    for child in box.descendants():
        if not (isinstance(child, boxes.TextBox) and child.utf8_text):
            continue

        # TODO: find a way to do less decoding and re-encoding
        text = child.utf8_text.decode('utf8')

        # Normalize line feeds
        text = re.sub(u'\r\n?', u'\n', text)

        handling = child.style.white_space

        if handling in ('normal', 'nowrap', 'pre-line'):
            # \r characters were removed/converted earlier
            text = re.sub('[\t ]*\n[\t ]*', '\n', text)
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

        child.utf8_text = text.encode('utf8')
    return box


def inline_in_block(box):
    """Build the structure of lines inside blocks and return a new box tree.

    Consecutive inline-level boxes in a block container box are wrapped into a
    line box, itself wrapped into an anonymous block box.

    This line box will be broken into multiple lines later.

    This is the first case in
    http://www.w3.org/TR/CSS21/visuren.html#anonymous-block-level

    Eg.::

        BlockBox[
            TextBox['Some '],
            InlineBox[TextBox['text']],
            BlockBox[
                TextBox['More text'],
            ]
        ]

    is turned into::

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
    new_children = []
    if isinstance(box, boxes.ParentBox):
        for child_box in getattr(box, 'children', []):
            new_child = inline_in_block(child_box)
            new_children.append(new_child)
        box = box.copy_with_children(new_children)

    if not isinstance(box, boxes.BlockContainerBox):
        return box

    new_line_children = []
    new_children = []
    for child_box in box.children:
        if isinstance(child_box, boxes.BlockLevelBox):
            if new_line_children:
                # Inlines are consecutive no more: add this line box
                # and create a new one.
                line_box = boxes.LineBox(
                    box.document, box.element, new_line_children)
                anonymous = boxes.AnonymousBlockBox(
                    box.document, box.element, [line_box])
                new_children.append(anonymous)
                new_line_children = []
            new_children.append(child_box)
        elif isinstance(child_box, boxes.LineBox):
            # Merge the line box we just found with the new one we are making
            for child in child_box.children:
                new_line_children.append(child)
        else:
            new_line_children.append(child_box)
    if new_line_children:
        # There were inlines at the end
        if new_children:
            line_box = boxes.LineBox(
                box.document, box.element, new_line_children)
            anonymous = boxes.AnonymousBlockBox(
                box.document, box.element, [line_box])
            new_children.append(anonymous)
        else:
            # Only inline-level children: one line box
            line_box = boxes.LineBox(
                box.document, box.element, new_line_children)
            new_children.append(line_box)

    return box.copy_with_children(new_children)


def block_in_inline(box):
    """Build the structure of blocks inside lines.

    Inline boxes containing block-level boxes will be broken in two
    boxes on each side on consecutive block-level boxes, each side wrapped
    in an anonymous block-level box.

    This is the second case in
    http://www.w3.org/TR/CSS21/visuren.html#anonymous-block-level

    Eg. if this is given::

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

    this is returned::

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
    if not isinstance(box, boxes.ParentBox):
        return box

    new_children = []
    changed = False

    for child in box.children:
        if isinstance(child, boxes.LineBox):
            assert len(box.children) == 1, ('Line boxes should have no '
                'siblings at this stage, got %r.' % box.children)
            stack = None
            while 1:
                new_line, block, stack = _inner_block_in_inline(child, stack)
                if block is None:
                    break
                anon = boxes.AnonymousBlockBox(
                    box.document, box.element, [new_line])
                new_children.append(anon)
                new_children.append(block_in_inline(block))
                # Loop with the same child and the new stack.
            if new_children:
                # Some children were already added, this became a block
                # context.
                new_child = boxes.AnonymousBlockBox(
                    box.document, box.element, [new_line])
            else:
                # Keep the single line box as-is, without anonymous blocks.
                new_child = new_line
        else:
            # Not in an inline formatting context.
            new_child = block_in_inline(child)

        if new_child is not child:
            changed = True
        new_children.append(new_child)

    if changed:
        return box.copy_with_children(new_children)
    else:
        return box


def _inner_block_in_inline(box, skip_stack=None):
    """Find a block-level box in an inline formatting context.

    If one is found, return ``(new_box, block_level_box, resume_at)``.
    ``new_box`` contains all of ``box`` content before the block-level box.
    ``resume_at`` can be passed as ``skip_stack`` in a new call to
    this function to resume the search just after thes block-level box.

    If no block-level box is found after the position marked by
    ``skip_stack``, return ``(new_box, None, None)``

    """
    new_children = []
    block_level_box = None
    resume_at = None
    changed = False

    if skip_stack is None:
        skip = 0
    else:
        skip, skip_stack = skip_stack

    for index, child in box.enumerate_skip(skip):
        if isinstance(child, boxes.BlockLevelBox):
            assert skip_stack is None  # Should not skip here
            block_level_box = child
            index += 1  # Resume *after* the block
        else:
            if isinstance(child, boxes.InlineBox):
                recursion = _inner_block_in_inline(child, skip_stack)
                skip_stack = None
                new_child, block_level_box, resume_at = recursion
            else:
                assert skip_stack is None  # Should not skip here
                if isinstance(child, boxes.ParentBox):
                    # inline-block or inline-table.
                    new_child = block_in_inline(child)
                else:
                    # text or replaced box
                    new_child = child
                # block_level_box is still None.
            if new_child is not child:
                changed = True
            new_children.append(new_child)
        if block_level_box is not None:
            resume_at = (index, resume_at)
            box = box.copy_with_children(new_children)
            break
    else:
        if changed or skip:
            box = box.copy_with_children(new_children)

    return box, block_level_box, resume_at


def text_transform(text, style):
    """Handle the `text-transform` CSS property.

    Takes a Unicode text and a :cls:`StyleDict`, returns a new Unicode text.
    """
    transform = style.text_transform
    if transform == 'none':
        return text
    elif transform == 'capitalize':
        return text.title()  # Python’s unicode.captitalize is not the same.
    elif transform == 'uppercase':
        return text.upper()
    elif transform == 'lowercase':
        return text.lower()
