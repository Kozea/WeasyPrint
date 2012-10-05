# coding: utf8
"""
    weasyprint.backgrounds
    ----------------------

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from collections import namedtuple

from ..formatting_structure import boxes


Background = namedtuple('Background', 'color, image, size, position, repeat, '
    'image_rendering, painting_area, positioning_area')


def box_rectangle(box, which_rectangle):
    if which_rectangle == 'border-box':
        return (
            box.border_box_x(),
            box.border_box_y(),
            box.border_width(),
            box.border_height(),
        )
    elif which_rectangle == 'padding-box':
        return (
            box.padding_box_x(),
            box.padding_box_y(),
            box.padding_width(),
            box.padding_height(),
        )
    else:
        assert which_rectangle == 'content-box', which_rectangle
        return (
            box.content_box_x(),
            box.content_box_y(),
            box.width,
            box.height,
        )


def layout_box_backgrounds(page, box, get_image_from_uri):
    """Fetch and position background images."""
    for child in box.all_children():
        layout_box_backgrounds(page, child, get_image_from_uri)

    style = box.style
    if style.visibility == 'hidden':
        box.background = None
        return

    image = (get_image_from_uri(style.background_image)
             if style.background_image != 'none' else None)
    color = style.background_color
    if image is None and color.alpha == 0:
        box.background = None
        return

    box.background = Background(
        color=color,
        image=image,
        size=style.background_size,
        position=style.background_position,
        repeat=style.background_repeat,
        image_rendering=style.image_rendering,
        painting_area=(box_rectangle(box, box.style.background_clip)
                       if box is not page else None),
        positioning_area=(
            # Initial containing block
            box_rectangle(page, 'content-box')
            if style.background_attachment == 'fixed' and box is not page
            else box_rectangle(box, box.style.background_origin)))


def set_canvas_background(page):
    """Set a ``canvas_background`` attribute on the PageBox,
    with style for the canvas background, taken from the root elememt
    or a <body> child of the root element.

    See http://www.w3.org/TR/CSS21/colors.html#background

    """
    assert not isinstance(page.children[0], boxes.MarginBox)
    root_box = page.children[0]
    chosen_box = root_box
    if (root_box.element_tag.lower() == 'html' and
            root_box.style.background_color.alpha == 0 and
            root_box.style.background_image == 'none'):
        for child in root_box.children:
            if child.element_tag.lower() == 'body':
                chosen_box = child
                break

    if chosen_box.background:
        page.canvas_background = chosen_box.background._replace(
            painting_area=box_rectangle(page, 'padding-box'))
        chosen_box.background = None
    else:
        page.canvas_background = None


def layout_backgrounds(page, get_image_from_uri):
    layout_box_backgrounds(page, page, get_image_from_uri)
    set_canvas_background(page)
