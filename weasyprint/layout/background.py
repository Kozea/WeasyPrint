"""Manage background position and size."""

from collections import namedtuple
from itertools import cycle

from tinycss2.color3 import parse_color

from ..formatting_structure import boxes
from . import replaced
from .percent import percentage, resolve_radii_percentages

Background = namedtuple('Background', 'color, layers, image_rendering')
BackgroundLayer = namedtuple(
    'BackgroundLayer',
    'image, size, position, repeat, unbounded, '
    'painting_area, positioning_area, clipped_boxes')


def box_rectangle(box, which_rectangle):
    if which_rectangle == 'border-box':
        return (
            box.border_box_x(), box.border_box_y(),
            box.border_width(), box.border_height())
    elif which_rectangle == 'padding-box':
        return (
            box.padding_box_x(), box.padding_box_y(),
            box.padding_width(), box.padding_height())
    else:
        assert which_rectangle == 'content-box', which_rectangle
        return (
            box.content_box_x(), box.content_box_y(),
            box.width, box.height)


def layout_box_backgrounds(page, box, get_image_from_uri, layout_children=True,
                           style=None):
    """Fetch and position background images."""
    from ..draw import get_color

    # Resolve percentages in border-radius properties
    resolve_radii_percentages(box)

    if layout_children:
        for child in box.all_children():
            layout_box_backgrounds(page, child, get_image_from_uri)

    if style is None:
        style = box.style

    if style['visibility'] == 'hidden':
        images = []
        color = parse_color('transparent')
    else:
        images = [
            get_image_from_uri(url=value) if type_ == 'url' else value
            for type_, value in style['background_image']]
        color = get_color(style, 'background_color')

    if color.alpha == 0 and not any(images):
        if box != page:  # Pages need a background for bleed box
            box.background = None
            return

    layers = [
        layout_background_layer(box, page, style['image_resolution'], *layer)
        for layer in zip(images, *map(cycle, [
            style['background_size'],
            style['background_clip'],
            style['background_repeat'],
            style['background_origin'],
            style['background_position'],
            style['background_attachment']]))]
    box.background = Background(color, layers, style['image_rendering'])


def layout_background_layer(box, page, resolution, image, size, clip, repeat,
                            origin, position, attachment):

    # TODO: respect box-sizing for table cells?
    clipped_boxes = []
    painting_area = 0, 0, 0, 0
    if box is page:
        painting_area = 0, 0, page.margin_width(), page.margin_height()
        # XXX: how does border-radius work on pages?
        clipped_boxes = [box.rounded_border_box()]
    elif isinstance(box, boxes.TableRowGroupBox):
        clipped_boxes = []
        total_height = 0
        for row in box.children:
            if row.children:
                clipped_boxes += [
                    cell.rounded_border_box() for cell in row.children]
                total_height = max(total_height, max(
                    cell.border_height() for cell in row.children))
        painting_area = [
            box.border_box_x(), box.border_box_y(),
            box.border_width(), total_height]
    elif isinstance(box, boxes.TableRowBox):
        if box.children:
            clipped_boxes = [
                cell.rounded_border_box() for cell in box.children]
            height = max(cell.border_height() for cell in box.children)
            painting_area = [
                box.border_box_x(), box.border_box_y(),
                box.border_width(), height]
    elif isinstance(box, (boxes.TableColumnGroupBox, boxes.TableColumnBox)):
        cells = box.get_cells()
        if cells:
            clipped_boxes = [cell.rounded_border_box() for cell in cells]
            min_x = min(cell.border_box_x() for cell in cells)
            max_x = max(
                cell.border_box_x() + cell.border_width() for cell in cells)
            painting_area = [
                min_x, box.border_box_y(), max_x - min_x, box.border_height()]
    else:
        painting_area = box_rectangle(box, clip)
        if clip == 'border-box':
            clipped_boxes = [box.rounded_border_box()]
        elif clip == 'padding-box':
            clipped_boxes = [box.rounded_padding_box()]
        else:
            assert clip == 'content-box', clip
            clipped_boxes = [box.rounded_content_box()]

    if image is not None:
        intrinsic_width, intrinsic_height, ratio = image.get_intrinsic_size(
            resolution, box.style['font_size'])
    if image is None or 0 in (intrinsic_width, intrinsic_height):
        return BackgroundLayer(
            image=None, unbounded=False, painting_area=painting_area,
            size='unused', position='unused', repeat='unused',
            positioning_area='unused', clipped_boxes=clipped_boxes)

    if attachment == 'fixed':
        # Initial containing block
        positioning_area = box_rectangle(page, 'content-box')
    else:
        positioning_area = box_rectangle(box, origin)

    positioning_x, positioning_y, positioning_width, positioning_height = (
        positioning_area)
    painting_x, painting_y, painting_width, painting_height = painting_area

    if size == 'cover':
        image_width, image_height = replaced.cover_constraint_image_sizing(
            positioning_width, positioning_height, ratio)
    elif size == 'contain':
        image_width, image_height = replaced.contain_constraint_image_sizing(
            positioning_width, positioning_height, ratio)
    else:
        size_width, size_height = size
        image_width, image_height = replaced.default_image_sizing(
            intrinsic_width, intrinsic_height, ratio,
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
        unbounded=False,
        painting_area=painting_area,
        positioning_area=positioning_area,
        clipped_boxes=clipped_boxes)


def layout_backgrounds(page, get_image_from_uri):
    """Layout backgrounds on the page box and on its children.

    This function takes care of the canvas background, taken from the root
    elememt or a <body> child of the root element.

    See https://www.w3.org/TR/CSS21/colors.html#background

    """
    layout_box_backgrounds(page, page, get_image_from_uri)
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
        original_background = page.background
        layout_box_backgrounds(
            page, page, get_image_from_uri, layout_children=False,
            style=chosen_box.style)
        page.canvas_background = page.background._replace(
            # TODO: shouldn’t background-clip be considered here?
            layers=[
                layer._replace(painting_area=painting_area)
                for layer in page.background.layers])
        page.background = original_background
        chosen_box.background = None
    else:
        page.canvas_background = None
