# coding: utf8
"""
    weasyprint.backgrounds
    ----------------------

    :copyright: Copyright 2011-2013 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from collections import namedtuple
from itertools import cycle

from ..formatting_structure import boxes


Background = namedtuple('Background', 'color, layers, image_rendering')
BackgroundLayer = namedtuple(
    'BackgroundLayer',
    'image, size, position, repeat, unbounded, '
    'painting_area, positioning_area')


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

    images = [get_image_from_uri(url) if url != 'none' else None
              for url in style.background_image]
    color = style.get_color('background_color')
    if color.alpha == 0 and not any(images):
        box.background = None
        return

    box.background = Background(
        color=color, image_rendering=style.image_rendering, layers=[
            layout_background_layer(box, page, *layer)
            for layer in zip(images, *map(cycle, [
                style.background_size,
                style.background_clip,
                style.background_repeat,
                style.background_origin,
                style.background_position,
                style.background_attachment]))])


def layout_background_layer(box, page, image, size, clip, repeat, origin,
                            position, attachment):
    return BackgroundLayer(
        image=image,
        size=size,
        position=position,
        repeat=repeat,
        unbounded=(box is page),
        painting_area=(
            box_rectangle(box, clip) if box is not page
            else (0, 0, page.margin_width(), page.margin_height())),
        positioning_area=(
            # Initial containing block
            box_rectangle(page, 'content-box')
            if attachment == 'fixed' and box is not page
            else box_rectangle(box, origin)))


def set_canvas_background(page):
    """Set a ``canvas_background`` attribute on the PageBox,
    with style for the canvas background, taken from the root elememt
    or a <body> child of the root element.

    See http://www.w3.org/TR/CSS21/colors.html#background

    """
    assert not isinstance(page.children[0], boxes.MarginBox)
    root_box = page.children[0]
    chosen_box = root_box
    if root_box.element_tag.lower() == 'html' and root_box.background is None:
        for child in root_box.children:
            if child.element_tag.lower() == 'body':
                chosen_box = child
                break

    if chosen_box.background:
        page.canvas_background = chosen_box.background._replace(
            # TODO: shouldn’t background-clip be considered here?
            layers=[
                l._replace(painting_area=box_rectangle(page, 'padding-box'))
                for l in chosen_box.background.layers])
        chosen_box.background = None
    else:
        page.canvas_background = None


def layout_backgrounds(page, get_image_from_uri):
    layout_box_backgrounds(page, page, get_image_from_uri)
    set_canvas_background(page)
