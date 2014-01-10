# coding: utf8
"""
    weasyprint.backgrounds
    ----------------------

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from collections import namedtuple
from itertools import cycle

from ..formatting_structure import boxes
from . import replaced
from .percentages import resolve_radiii_percentages


Background = namedtuple('Background', 'color, layers, image_rendering')
BackgroundLayer = namedtuple(
    'BackgroundLayer',
    'image, size, position, repeat, unbounded, '
    'painting_area, positioning_area, rounded_box')


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
    # Resolve percentages in border-radius properties
    resolve_radiii_percentages(box)

    for child in box.all_children():
        layout_box_backgrounds(page, child, get_image_from_uri)

    style = box.style
    if style.visibility == 'hidden':
        box.background = None
        return

    images = [get_image_from_uri(value) if type_ == 'url' else value
              for type_, value in style.background_image]
    color = style.get_color('background_color')
    if color.alpha == 0 and not any(images):
        box.background = None
        return

    box.background = Background(
        color=color, image_rendering=style.image_rendering, layers=[
            layout_background_layer(box, page, style.image_resolution, *layer)
            for layer in zip(images, *map(cycle, [
                style.background_size,
                style.background_clip,
                style.background_repeat,
                style.background_origin,
                style.background_position,
                style.background_attachment]))])


def percentage(value, refer_to):
    """Return the evaluated percentage value, or the value unchanged."""
    if value == 'auto':
        return value
    elif value.unit == 'px':
        return value.value
    else:
        assert value.unit == '%'
        return refer_to * value.value / 100


def layout_background_layer(box, page, resolution, image, size, clip, repeat,
                            origin, position, attachment):

    if box is not page:
        painting_area = box_rectangle(box, clip)
        if clip == 'border-box':
            rounded_box = box.rounded_border_box()
        elif clip == 'padding-box':
            rounded_box = box.rounded_padding_box()
        else:
            assert clip == 'content-box', clip
            rounded_box = box.rounded_content_box()
    else:
        painting_area = 0, 0, page.margin_width(), page.margin_height()
        # XXX: how does border-radius work on pages?
        rounded_box = box.rounded_border_box()

    if image is None or 0 in image.get_intrinsic_size(1):
        return BackgroundLayer(
            image=None, unbounded=(box is page), painting_area=painting_area,
            size='unused', position='unused', repeat='unused',
            positioning_area='unused', rounded_box=box.rounded_border_box())

    if attachment == 'fixed':
        # Initial containing block
        positioning_area = box_rectangle(page, 'content-box')
    else:
        positioning_area = box_rectangle(box, origin)

    positioning_x, positioning_y, positioning_width, positioning_height = (
        positioning_area)
    painting_x, painting_y, painting_width, painting_height = (
        painting_area)

    if size == 'cover':
        image_width, image_height = replaced.cover_constraint_image_sizing(
            positioning_width, positioning_height, image.intrinsic_ratio)
    elif size == 'contain':
        image_width, image_height = replaced.contain_constraint_image_sizing(
            positioning_width, positioning_height, image.intrinsic_ratio)
    else:
        size_width, size_height = size
        iwidth, iheight = image.get_intrinsic_size(resolution)
        image_width, image_height = replaced.default_image_sizing(
            iwidth, iheight, image.intrinsic_ratio,
            percentage(size_width, positioning_width),
            percentage(size_height, positioning_height),
            positioning_width, positioning_height)

    origin_x, position_x, origin_y, position_y = position
    ref_x = positioning_width - image_width
    ref_y = positioning_height - image_height
    position_x = percentage(position_x, ref_x)
    position_y = percentage(position_y, ref_y)
    if origin_x == 'right':
        position_x = ref_x - position_x
    if origin_y == 'bottom':
        position_y = ref_y - position_y

    repeat_x, repeat_y = repeat

    if repeat_x == 'round':
        n_repeats = max(1, round(positioning_width / image_width))
        new_width = positioning_width / n_repeats
        position_x = 0  # Ignore background-position for this dimension
        if repeat_y != 'round' and size[1] == 'auto':
            image_height *= new_width / image_width
        image_width = new_width
    if repeat_y == 'round':
        n_repeats = max(1, round(positioning_height / image_height))
        new_height = positioning_height / n_repeats
        position_y = 0  # Ignore background-position for this dimension
        if repeat_x != 'round' and size[0] == 'auto':
            image_width *= new_height / image_height
        image_height = new_height

    return BackgroundLayer(
        image=image,
        size=(image_width, image_height),
        position=(position_x, position_y),
        repeat=repeat,
        unbounded=(box is page),
        painting_area=painting_area,
        positioning_area=positioning_area,
        rounded_box=rounded_box)


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
        painting_area = box_rectangle(page, 'padding-box')
        page.canvas_background = chosen_box.background._replace(
            # TODO: shouldn’t background-clip be considered here?
            layers=[
                l._replace(painting_area=painting_area)
                for l in chosen_box.background.layers])
        chosen_box.background = None
    else:
        page.canvas_background = None


def layout_backgrounds(page, get_image_from_uri):
    layout_box_backgrounds(page, page, get_image_from_uri)
    set_canvas_background(page)
