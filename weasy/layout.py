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


from .formatting_structure import boxes
from .utils import MultiFunction
from .css import computed_values
import text


def pixel_value(value):
    """
    Return the numeric value of a pixel length or None.
    """
    if len(value) == 1 and value[0].type == 'DIMENSION' \
            and value[0].dimension == 'px':
        # cssutils promises that `DimensionValue.value` is an int or float
        assert isinstance(value[0].value, (int, float))
        return value[0].value
    # 0 may not have a units
    elif len(value) == 1 and value[0].value == 0:
        return 0
    else:
        # Not a pixel length
        return None


def percentage_value(value):
    """
    Return the numeric value of a percentage or None.
    """
    if len(value) == 1 and value[0].type == 'PERCENTAGE': \
        # cssutils promises that `DimensionValue.value` is an int or float
        assert isinstance(value[0].value, (int, float))
        return value[0].value
    else:
        # Not a percentage
        return None


def resolve_one_percentage(box, property_name, refer_to):
    """
    Set a used length value from a computed length value.
    `refer_to` is the length for 100%.
    """
    # box.style has computed values
    value = box.style[property_name]
    pixels = pixel_value(value)
    if pixels is not None:
        # Absolute length (was converted to pixels in "computed values")
        result = pixels
    else:
        percentage = percentage_value(value)
        if percentage is not None:
            # A percentage
            result = percentage * refer_to / 100.
        else:
            result = value.value
            # Other than that, only 'auto' is allowed
            # TODO: it is only allowed on some properties. Check this here?
            assert result == 'auto'
    # box attributes are used values
    setattr(box, property_name.replace('-', '_'), result)


def resolve_percentages(box):
    """
    Set used values as attributes of the box object.
    """
    # cb = containing block
    cb_width, cb_height = box.containing_block_size()
    # TODO: background-position?
    for prop in ['margin-left', 'margin-right',
                 'padding-left', 'padding-right',
                 'text-indent', 'width', 'min-width']:
        resolve_one_percentage(box, prop, cb_width)
    # XXX later: top, bottom, left and right on positioned elements

    for prop in ['margin-top', 'margin-bottom',
                 'padding-top', 'padding-bottom']:
        if isinstance(box, boxes.PageBox):
            resolve_one_percentage(box, prop, cb_height)
        else:
            resolve_one_percentage(box, prop, cb_width)

    if box.style.max_width == 'none':
        box.max_width = None
    else:
        resolve_one_percentage(box, 'max-width', cb_width)

    if cb_height is None:
        # Special handling when the height of the containing block is not
        # known yet.
        box.min_height = 0
        box.max_height = None
        box.height = 'auto'
    else:
        if box.style.max_height == 'none':
            box.max_height = None
        else:
            resolve_one_percentage(box, 'max-height', cb_height)
        resolve_one_percentage(box, 'min-height', cb_height)
        resolve_one_percentage(box, 'height', cb_height)

    # Used value == computed value
    box.border_top_width = box.style.border_top_width
    box.border_right_width = box.style.border_right_width
    box.border_bottom_width = box.style.border_bottom_width
    box.border_left_width = box.style.border_left_width


# TODO: remove this if it is not needed?
@MultiFunction
def compute_dimensions(box):
    """
    Computes width, height and absolute position for all boxes in a box tree.
    """


def page_dimensions(box):
    box.outer_height = box.style._weasy_page_height
    box.outer_width = box.style._weasy_page_width

    resolve_percentages(box)

    box.position_x = 0
    box.position_y = 0
    box.width = box.outer_width - box.margin_left - box.margin_right
    box.height = box.outer_height - box.margin_top - box.margin_bottom
    box.root_box.position_x = box.margin_left
    box.root_box.position_y = box.margin_top

    compute_dimensions(box.root_box)


@compute_dimensions.register(boxes.BlockBox)
def block_dimensions(box):
    resolve_percentages(box)
    block_level_width(box)
    block_level_height(box)


def block_level_width(box):
    # cb = containing block
    cb_width, cb_height = box.containing_block_size()

    # http://www.w3.org/TR/CSS21/visudet.html#blockwidth

    # These names are waaay too long
    margin_l = box.margin_left
    margin_r = box.margin_right
    padding_l = box.padding_left
    padding_r = box.padding_right
    border_l = box.border_left_width
    border_r = box.border_right_width
    width = box.width

    # Only margin-left, margin-right and width can be 'auto'.
    # We want:  width of containing block ==
    #               margin-left + border-left-width + padding-left + width
    #               + padding-right + border-right-width + margin-right

    paddings_plus_borders = padding_l + padding_r + border_l + border_r
    if box.width != 'auto':
        total = paddings_plus_borders + width
        if margin_l != 'auto':
            total += margin_l
        if margin_r != 'auto':
            total += margin_r
        if total > cb_width:
            if margin_l == 'auto':
                margin_l = box.margin_left = 0
            if margin_r == 'auto':
                margin_r = box.margin_right = 0
    if width != 'auto' and margin_l != 'auto' and margin_r != 'auto':
        # The equation is over-constrained
        margin_sum = cb_width - paddings_plus_borders - width
        # This is the direction of the containing block, but the containing
        # block for block-level boxes in normal flow is always the parent.
        # TODO: is it?
        if box.parent.style.direction == 'ltr':
            margin_r = box.margin_right = margin_sum - margin_l
        else:
            margin_l = box.margin_left = margin_sum - margin_r
    if width == 'auto':
        if margin_l == 'auto':
            margin_l = box.margin_left = 0
        if margin_r == 'auto':
            margin_r = box.margin_right = 0
        width = box.width = cb_width - (
            paddings_plus_borders + margin_l + margin_r)
    margin_sum = cb_width - paddings_plus_borders - width
    if margin_l == 'auto' and margin_r == 'auto':
        box.margin_left = margin_sum / 2.
        box.margin_right = margin_sum / 2.
    elif margin_l == 'auto' and margin_r != 'auto':
        box.margin_left = margin_sum - margin_r
    elif margin_l != 'auto' and margin_r == 'auto':
        box.margin_right = margin_sum - margin_l

    # Sanity check
    total = (box.margin_left + box.margin_right + box.padding_left +
             box.padding_right + box.border_left_width +
             box.border_right_width + box.width)
    assert total == cb_width


def block_level_height(box):
    if box.style.overflow != 'visible':
        raise NotImplementedError

    if isinstance(box, boxes.ReplacedBox):
        raise NotImplementedError

    assert isinstance(box, boxes.BlockBox)

    if box.margin_top == 'auto':
        box.margin_top = 0
    if box.margin_bottom == 'auto':
        box.margin_bottom = 0

    position_x = box.position_x + box.margin_left + box.padding_left + \
        box.border_left_width
    position_y = box.position_y + box.margin_top + box.padding_top + \
        box.border_top_width
    initial_position_y = position_y
    for child in box.children:
        # TODO: collapse margins:
        # http://www.w3.org/TR/CSS21/visudet.html#normal-block
        child.position_x = position_x
        child.position_y = position_y

        compute_dimensions(child)

        child_outer_height = (
            child.height + child.margin_top + child.margin_bottom +
            child.border_top_width + child.border_bottom_width +
            child.padding_top + child.padding_bottom)
        position_y += child_outer_height

    if box.height == 'auto':
        box.height = position_y - initial_position_y


@compute_dimensions.register(boxes.LineBox)
def line_dimensions(box):
    # TODO: real line box height
    # box.height = box.style.line_height
    box.height = 0


def layout(root_box):
    """
    Take the block box for the root element, return a list of page boxes.
    """
    pages = []
    page = boxes.PageBox(root_box, 1)
    page_dimensions(page)
    pages.append(page)
    # TODO: do page breaks, split boxes into multiple pages
    return pages

def breaking_linebox(linebox):
    """
    Eg.

    LineBox[
        InlineBox[
            TextBox('Hello.'),
        ],
        InlineBox[
            InlineBox[TextBox('Word :D')],
            TextBox('This is a long long long text'),
        ]
    ]

    is turned into

    [
        LineBox[
            InlineBox[
                TextBox('Hello.'),
            ],
            InlineBox[
                InlineBox[TextBox('Word :D')],
                TextBox('This is a long'),
            ]
        ], LineBox[
            InlineBox[
                TextBox(' long long text'),
            ]
        ]
    ]
    """
    cb_width = linebox.containing_block_size()[0]
    children = list(linebox.children)
    lines = []
    while len(children) != 0:
        # We copy the linebox without children
        line = linebox.copy()
        insert_in_the_linebox(line, cb_width, children)
        widths, heights = ([], [])
        for child in line.children:
            widths.append(child.width + child.horizontal_spacing)
            heights.append(child.height + child.vertical_spacing)
        # TODO:We need manage the collapse of margin
        line.width, line.height = sum(widths), max(heights)
        lines.append(line)
    return lines

def insert_in_the_linebox(linebox, width, children):
    """ Insert the maximum children in the line before the line break """
    if width == 0 or len(children) == 0:
        return linebox, children
    child = children.pop(0)
    #If first element is None, then it means we force the line break
    if child is None:
        return linebox, children
    child_width = compute_linebox_width_element(child)
    if child_width <= width:
        width -= child_width
        linebox.add_child(child)
        return insert_in_the_linebox(linebox, width, children)
    else:
        first_child, second_child = breaking_linebox_child(child, width)
        #If second element is None, it means we can't cut the child element
        if second_child is None:
            # We check if it will be the only element in the line
            if len(linebox.children) == 0:
                #Then we add the element in the line and force the line break
                linebox.add_child(first_child)
                return linebox, children
            else:
                # Else we try to insert the element in the next line
                children.insert(0, first_child)
                children.insert(0, second_child)
                return insert_in_the_linebox(linebox, width, children)
        else:
            children.insert(0, second_child)
            children.insert(0, first_child)
        return insert_in_the_linebox(linebox, width, children)

def compute_linebox_width_element(box):
    """Add the width and height in the box attributes and return total width."""
    sum_width = 0
    max_height = 0
    if isinstance(box, boxes.InlineBox):
        children_heights = []
        for child in inlinebox_children_size(inlinebox):
            #set css style in TextLineFragment
            text_fragment = text.TextLineFragment()
            text_fragment.set_textbox(child)
            child.width, child.height = text_fragment.get_size()
            children_heights.append(child.height)
            sum_width += child.width
        box.width, box.height = sum_width, max(children_heights)
        return sum_width
    elif isinstance(box, boxes.TextBox):
        text_fragment = text.TextLineFragment()
        text_fragment.set_textbox(box)
        box.width, box.height = text_fragment.get_size()
        return box.width
    elif isinstance(box, boxes.InlineBlockBox):
        pass
    elif isinstance(box, boxes.InlineLevelReplacedBox):
        pass

def inlinebox_children_size(inlinebox):
    """ Return something :(
    the horizontal_spacing and the vertical_spacing of all its ancestors
    """
    for child in flatten_inlinebox_tree(inlinebox):
        if isinstance(child, boxes.TextBox):
            horizontal_spacing = 0
            vertical_spacing = 0
            # return the branch between a decendent and an ancestor
            for ancestor in child.ancestors():
                if ancestor != inlinebox:
                    horizontal_spacing += ancestor.horizontal_spacing
                    vertical_spacing += ancestor.vertical_spacing
            text_fragment = text.TextLineFragment()
            text_fragment.set_textbox(child)
            child.width, child.height = text_fragment.get_size()
            yield child.width, child.height
        elif isinstance(child, boxes.InlineBlockBox):
            raise NotImplementedError
        elif isinstance(child, boxes.InlineLevelReplacedBox):
            raise NotImplementedError


def flatten_inlinebox_tree(inlinebox):
    """
    Return all children TextBox in a flatten tree (list)
    Eg.
        InlineBox[
            TextBox('first'),
            InlineBox[
                TextBox('second')
            ]
            TextBox('third')
        ]

    is turned into

        [
            TextBox('first'),
            TextBox('second'),
            TextBox('third')
        ]
    """
    for child in inlinebox.children:
        if isinstance(child, boxes.InlineBox):
            yield flatten_inlinebox_tree(child)
        elif isinstance(child, boxes.TextBox):
            yield child
        elif isinstance(child, boxes.InlineBlockBox):
            raise NotImplementedError
        elif isinstance(child, boxes.InlineLevelReplacedBox):
            raise NotImplementedError


def breaking_linebox_child(box, allocate_width):
    """ Cut the Box that sticks out the LineBox"""
    if isinstance(box, boxes.InlineBox):
        return breaking_inlinebox(box, allocate_width)
    elif isinstance(box, boxes.TextBox):
        return breaking_textbox(box, allocate_width)
    elif isinstance(box, boxes.InlineBlockBox):
        raise NotImplementedError
    elif isinstance(box, boxes.InlineLevelReplacedBox):
        raise NotImplementedError

def breaking_inlinebox(inlinebox, allocate_width):
    """
    Cut the InlineBox that sticks out the LineBox

    Eg.
        InlineBox[
            InlineBox[TextBox('Hello ')],
            TextBox('This is a long long long long text'),
            InlineBox[TextBox('Word !!')],
        ]

    is turned into

        [
            InlineBox[
                InlineBox[TextBox('Hello :D')],
                TextBox('This is a long')
            ], InlineBox[
                TextBox('long long long text'),
                InlineBox[TextBox('Word !!')],
            ]
        ]
    """
    # TODO: finish this function...:'(
    raise NotImplementedError
    allocate_width -= textbox.h_spacing_content
    if allocate_width < 0:
        text_fragment = text.TextLineFragment()
        text_fragment.set_text_box(textbox)
        textbox_width, textbox_height = text_fragment.get_size()
        return (textbox, None)
    else:
        text_fragment.set_text_box(textbox)
        textbox.width =  textbox.height = text_fragment.get_size()
        text_fragment = text.TextFragment(child.text)
    return ()

def breaking_textbox(textbox, allocate_width):
    """
    Cut the long TextBox that sticks out the LineBox only if the TextBox
    can be cut by a line break

    >>> breaking_textbox(textbox, allocate_width)
    (first_element, second_element)

    Eg.
        TextBox('This is a long long long long text')

    is turned into

        (
            TextBox('This is a long long'),
            TextBox(' long long text')
        )

    but
        TextBox('Thisisalonglonglonglongtext')

    is turned into

        (
            TextBox('Thisisalonglonglonglongtext'),
            None
        )

    and

        TextBox('Thisisalonglonglonglong Thisisalonglonglonglong')

    is turned into

        (
            TextBox('Thisisalonglonglonglong'),
            TextBox(' Thisisalonglonglonglong')
        )
    """
    text_fragment = text.TextLineFragment(width=allocate_width)
    # Set css style in TextLineFragment
    text_fragment.set_textbox(textbox)
    # We create a new TextBox with the first part of the cutting text
    first_textbox = textbox.copy(text_fragment.get_text())
    # And we check the remaining text
    if text_fragment.get_remaining_text() == "":
        return (first_textbox, None)
    else:
        text_second_tb = text_fragment.get_remaining_text()
        second_textbox = textbox.copy(text_second_tb)
        return (first_textbox, second_textbox)
