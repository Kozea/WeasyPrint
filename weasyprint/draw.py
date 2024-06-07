"""Take an "after layout" box tree and draw it onto a pydyf stream."""

import contextlib
import operator
from colorsys import hsv_to_rgb, rgb_to_hsv
from io import BytesIO
from math import ceil, floor, pi, sqrt, tan
from xml.etree import ElementTree

from PIL import Image

from .formatting_structure import boxes
from .images import RasterImage, SVGImage
from .layout import replaced
from .layout.background import BackgroundLayer
from .layout.percent import percentage
from .matrix import Matrix
from .stacking import StackingContext
from .text.ffi import ffi, pango, units_from_double, units_to_double
from .text.fonts import get_hb_object_data
from .text.line_break import get_last_word_end

SIDES = ('top', 'right', 'bottom', 'left')


@contextlib.contextmanager
def stacked(stream):
    """Save and restore stream context when used with the ``with`` keyword."""
    stream.push_state()
    try:
        yield
    finally:
        stream.pop_state()


def get_color(style, key):
    value = style[key]
    return value if value != 'currentColor' else style['color']


def darken(color):
    """Return a darker color."""
    hue, saturation, value = rgb_to_hsv(color.red, color.green, color.blue)
    value /= 1.5
    saturation /= 1.25
    return (*hsv_to_rgb(hue, saturation, value), color.alpha)


def lighten(color):
    """Return a lighter color."""
    hue, saturation, value = rgb_to_hsv(color.red, color.green, color.blue)
    value = 1 - (1 - value) / 1.5
    if saturation:
        saturation = 1 - (1 - saturation) / 1.25
    return (*hsv_to_rgb(hue, saturation, value), color.alpha)


def draw_page(page, stream):
    """Draw the given PageBox."""
    marks = page.style['marks']
    stacking_context = StackingContext.from_page(page)
    draw_background(
        stream, stacking_context.box.background, clip_box=False,
        bleed=page.bleed, marks=marks)
    draw_background(stream, page.canvas_background, clip_box=False)
    draw_border(stream, page)
    draw_stacking_context(stream, stacking_context)


def draw_stacking_context(stream, stacking_context):
    """Draw a ``stacking_context`` on ``stream``."""
    # See https://www.w3.org/TR/CSS2/zindex.html
    with stacked(stream):
        box = stacking_context.box

        stream.begin_marked_content(box, mcid=True)

        # apply the viewport_overflow to the html box, see #35
        if box.is_for_root_element and (
                stacking_context.page.style['overflow'] != 'visible'):
            rounded_box_path(
                stream, stacking_context.page.rounded_padding_box())
            stream.clip()
            stream.end()

        if box.is_absolutely_positioned() and box.style['clip']:
            top, right, bottom, left = box.style['clip']
            if top == 'auto':
                top = 0
            if right == 'auto':
                right = 0
            if bottom == 'auto':
                bottom = box.border_height()
            if left == 'auto':
                left = box.border_width()
            stream.rectangle(
                box.border_box_x() + right, box.border_box_y() + top,
                left - right, bottom - top)
            stream.clip()
            stream.end()

        if box.style['opacity'] < 1:
            original_stream = stream
            stream = stream.add_group(*stream.page_rectangle)

        if box.transformation_matrix:
            if box.transformation_matrix.determinant:
                stream.transform(*box.transformation_matrix.values)
            else:
                stream.end_marked_content()
                return

        # Point 1 is done in draw_page

        # Point 2
        if isinstance(box, (boxes.BlockBox, boxes.MarginBox,
                            boxes.InlineBlockBox, boxes.TableCellBox,
                            boxes.FlexContainerBox, boxes.ReplacedBox)):
            # The canvas background was removed by layout_backgrounds
            draw_background(stream, box.background)
            draw_border(stream, box)

        with stacked(stream):
            # dont clip the PageBox, see #35
            if box.style['overflow'] != 'visible' and not isinstance(
                    box, boxes.PageBox):
                # Only clip the content and the children:
                # - the background is already clipped
                # - the border must *not* be clipped
                rounded_box_path(stream, box.rounded_padding_box())
                stream.clip()
                stream.end()

            # Point 3
            for child_context in stacking_context.negative_z_contexts:
                draw_stacking_context(stream, child_context)

            # Point 4
            for block in stacking_context.block_level_boxes:
                if isinstance(block, boxes.TableBox):
                    draw_table(stream, block)
                else:
                    draw_background(stream, block.background)
                    draw_border(stream, block)

            # Point 5
            for child_context in stacking_context.float_contexts:
                draw_stacking_context(stream, child_context)

            # Point 6
            if isinstance(box, boxes.InlineBox):
                draw_inline_level(stream, stacking_context.page, box)

            # Point 7
            for block in (box, *stacking_context.blocks_and_cells):
                if isinstance(block, boxes.ReplacedBox):
                    draw_replacedbox(stream, block)
                elif block.children:
                    if block != box:
                        stream.begin_marked_content(block, mcid=True)
                    if isinstance(block.children[-1], boxes.LineBox):
                        for child in block.children:
                            draw_inline_level(
                                stream, stacking_context.page, child)
                    if block != box:
                        stream.end_marked_content()

            # Point 8
            for child_context in stacking_context.zero_z_contexts:
                draw_stacking_context(stream, child_context)

            # Point 9
            for child_context in stacking_context.positive_z_contexts:
                draw_stacking_context(stream, child_context)

        # Point 10
        draw_outlines(stream, box)

        if box.style['opacity'] < 1:
            group_id = stream.id
            stream = original_stream
            with stacked(stream):
                stream.set_alpha(box.style['opacity'], stroke=True, fill=True)
                stream.draw_x_object(group_id)

        stream.end_marked_content()


def rounded_box_path(stream, radii):
    """Draw the path of the border radius box.

    ``widths`` is a tuple of the inner widths (top, right, bottom, left) from
    the border box. Radii are adjusted from these values. Default is (0, 0, 0,
    0).

    """
    x, y, w, h, tl, tr, br, bl = radii

    if all(0 in corner for corner in (tl, tr, br, bl)):
        # No radius, draw a rectangle
        stream.rectangle(x, y, w, h)
        return

    r = 0.45

    stream.move_to(x + tl[0], y)
    stream.line_to(x + w - tr[0], y)
    stream.curve_to(
        x + w - tr[0] * r, y, x + w, y + tr[1] * r, x + w, y + tr[1])
    stream.line_to(x + w, y + h - br[1])
    stream.curve_to(
        x + w, y + h - br[1] * r, x + w - br[0] * r, y + h, x + w - br[0],
        y + h)
    stream.line_to(x + bl[0], y + h)
    stream.curve_to(
        x + bl[0] * r, y + h, x, y + h - bl[1] * r, x, y + h - bl[1])
    stream.line_to(x, y + tl[1])
    stream.curve_to(
        x, y + tl[1] * r, x + tl[0] * r, y, x + tl[0], y)


def draw_background(stream, bg, clip_box=True, bleed=None, marks=()):
    """Draw the background color and image to a ``document.Stream``.

    If ``clip_box`` is set to ``False``, the background is not clipped to the
    border box of the background, but only to the painting area.

    """
    if bg is None:
        return

    with stacked(stream):
        if clip_box:
            for box in bg.layers[-1].clipped_boxes:
                rounded_box_path(stream, box)
            stream.clip()
            stream.end()

        # Background color
        if bg.color.alpha > 0:
            with stacked(stream):
                stream.set_color_rgb(*bg.color[:3])
                stream.set_alpha(bg.color.alpha)
                painting_area = bg.layers[-1].painting_area
                stream.rectangle(*painting_area)
                stream.clip()
                stream.end()
                stream.rectangle(*painting_area)
                stream.fill()

        if bleed and marks:
            x, y, width, height = bg.layers[-1].painting_area
            half_bleed = {key: value * 0.5 for key, value in bleed.items()}
            svg = f'''
              <svg height="{height}" width="{width}"
                   fill="transparent" stroke="black" stroke-width="1"
                   xmlns="http://www.w3.org/2000/svg">
            '''
            if 'crop' in marks:
                svg += f'''
                  <path d="M0,{bleed['top']} h{half_bleed['left']}" />
                  <path d="M0,{bleed['top']} h{half_bleed['right']}"
                        transform="translate({width},0) scale(-1,1)" />
                  <path d="M0,{bleed['bottom']} h{half_bleed['right']}"
                        transform="translate({width},{height}) scale(-1,-1)" />
                  <path d="M0,{bleed['bottom']} h{half_bleed['left']}"
                        transform="translate(0,{height}) scale(1,-1)" />
                  <path d="M{bleed['left']},0 v{half_bleed['top']}" />
                  <path d="M{bleed['right']},0 v{half_bleed['bottom']}"
                        transform="translate({width},{height}) scale(-1,-1)" />
                  <path d="M{bleed['left']},0 v{half_bleed['bottom']}"
                        transform="translate(0,{height}) scale(1,-1)" />
                  <path d="M{bleed['right']},0 v{half_bleed['top']}"
                        transform="translate({width},0) scale(-1,1)" />
                '''
            if 'cross' in marks:
                svg += f'''
                  <circle r="{half_bleed['top']}" transform="scale(0.5)
                     translate({width},{half_bleed['top']}) scale(0.5)" />
                  <path transform="scale(0.5) translate({width},0)" d="
                    M-{half_bleed['top']},{half_bleed['top']} h{bleed['top']}
                    M0,0 v{bleed['top']}" />
                  <circle r="{half_bleed['bottom']}" transform="
                    translate(0,{height}) scale(0.5)
                    translate({width},-{half_bleed['bottom']}) scale(0.5)" />
                  <path d="M-{half_bleed['bottom']},-{half_bleed['bottom']}
                    h{bleed['bottom']} M0,0 v-{bleed['bottom']}" transform="
                    translate(0,{height}) scale(0.5) translate({width},0)" />
                  <circle r="{half_bleed['left']}" transform="scale(0.5)
                    translate({half_bleed['left']},{height}) scale(0.5)" />
                  <path d="M{half_bleed['left']},-{half_bleed['left']}
                    v{bleed['left']} M0,0 h{bleed['left']}"
                    transform="scale(0.5) translate(0,{height})" />
                  <circle r="{half_bleed['right']}" transform="
                    translate({width},0) scale(0.5)
                    translate(-{half_bleed['right']},{height}) scale(0.5)" />
                  <path d="M-{half_bleed['right']},-{half_bleed['right']}
                    v{bleed['right']} M0,0 h-{bleed['right']}" transform="
                    translate({width},0) scale(0.5) translate(0,{height})" />
                '''
            svg += '</svg>'
            tree = ElementTree.fromstring(svg)
            image = SVGImage(tree, None, None, stream)
            # Painting area is the PDF media box
            size = (width, height)
            position = (x, y)
            repeat = ('no-repeat', 'no-repeat')
            unbounded = True
            painting_area = position + size
            positioning_area = (0, 0, width, height)
            clipped_boxes = []
            layer = BackgroundLayer(
                image, size, position, repeat, unbounded, painting_area,
                positioning_area, clipped_boxes)
            bg.layers.insert(0, layer)
        # Paint in reversed order: first layer is "closest" to the viewer.
        for layer in reversed(bg.layers):
            draw_background_image(stream, layer, bg.image_rendering)


def draw_background_image(stream, layer, image_rendering):
    if layer.image is None or 0 in layer.size:
        return

    painting_x, painting_y, painting_width, painting_height = (
        layer.painting_area)
    positioning_x, positioning_y, positioning_width, positioning_height = (
        layer.positioning_area)
    position_x, position_y = layer.position
    repeat_x, repeat_y = layer.repeat
    image_width, image_height = layer.size

    if repeat_x == 'no-repeat':
        # We want at least the whole image_width drawn on sub_surface, but we
        # want to be sure it will not be repeated on the painting_width. We
        # double the painting width to ensure viewers don't incorrectly bleed
        # the edge of the pattern into the painting area. (See #1539.)
        repeat_width = max(image_width, 2 * painting_width)
    elif repeat_x in ('repeat', 'round'):
        # We repeat the image each image_width.
        repeat_width = image_width
    else:
        assert repeat_x == 'space'
        n_repeats = floor(positioning_width / image_width)
        if n_repeats >= 2:
            # The repeat width is the whole positioning width with one image
            # removed, divided by (the number of repeated images - 1). This
            # way, we get the width of one image + one space. We ignore
            # background-position for this dimension.
            repeat_width = (positioning_width - image_width) / (n_repeats - 1)
            position_x = 0
        else:
            # We don't repeat the image.
            repeat_width = positioning_width

    # Comments above apply here too.
    if repeat_y == 'no-repeat':
        repeat_height = max(image_height, 2 * painting_height)
    elif repeat_y in ('repeat', 'round'):
        repeat_height = image_height
    else:
        assert repeat_y == 'space'
        n_repeats = floor(positioning_height / image_height)
        if n_repeats >= 2:
            repeat_height = (
                positioning_height - image_height) / (n_repeats - 1)
            position_y = 0
        else:
            repeat_height = positioning_height

    matrix = Matrix(e=position_x + positioning_x, f=position_y + positioning_y)
    matrix @= stream.ctm
    pattern = stream.add_pattern(
        0, 0, image_width, image_height, repeat_width, repeat_height, matrix)
    group = pattern.add_group(0, 0, repeat_width, repeat_height)

    with stacked(stream):
        layer.image.draw(group, image_width, image_height, image_rendering)
        pattern.draw_x_object(group.id)
        stream.color_space('Pattern')
        stream.set_color_special(pattern.id)
        if layer.unbounded:
            x1, y1, x2, y2 = stream.page_rectangle
            stream.rectangle(x1, y1, x2 - x1, y2 - y1)
        else:
            stream.rectangle(
                painting_x, painting_y, painting_width, painting_height)
        stream.fill()


def styled_color(style, color, side):
    if style in ('inset', 'outset'):
        do_lighten = (side in ('top', 'left')) ^ (style == 'inset')
        return (lighten if do_lighten else darken)(color)
    elif style in ('ridge', 'groove'):
        if (side in ('top', 'left')) ^ (style == 'ridge'):
            return lighten(color), darken(color)
        else:
            return darken(color), lighten(color)
    return color


def draw_border(stream, box):
    """Draw the box borders and column rules to a ``document.Stream``."""

    # The box is hidden, easy.
    if box.style['visibility'] != 'visible':
        return

    # Draw column borders.
    columns = (
        isinstance(box, boxes.BlockContainerBox) and (
            box.style['column_width'] != 'auto' or
            box.style['column_count'] != 'auto'))
    if columns and box.style['column_rule_width']:
        border_widths = (0, 0, 0, box.style['column_rule_width'])
        skip_next = True
        for child in box.children:
            if child.style['column_span'] == 'all':
                skip_next = True
                continue
            elif skip_next:
                skip_next = False
                continue
            with stacked(stream):
                gap = percentage(box.style['column_gap'], box.width)
                position_x = (child.position_x - (
                    box.style['column_rule_width'] + gap) / 2)
                border_box = (
                    position_x, child.position_y,
                    box.style['column_rule_width'], child.height)
                clip_border_segment(
                    stream, box.style['column_rule_style'],
                    box.style['column_rule_width'], 'left', border_box,
                    border_widths)
                draw_rect_border(
                    stream, border_box, border_widths,
                    box.style['column_rule_style'], styled_color(
                        box.style['column_rule_style'],
                        get_color(box.style, 'column_rule_color'), 'left'))

    # If there's a border image, that takes precedence.
    if box.style['border_image_source'][0] != 'none' and box.border_image is not None:
        draw_border_image(box, stream)
        return

    widths = [getattr(box, f'border_{side}_width') for side in SIDES]

    if set(widths) == {0}:
        # No border, return early.
        return

    colors = [get_color(box.style, f'border_{side}_color') for side in SIDES]
    styles = [
        colors[i].alpha and box.style[f'border_{side}_style']
        for (i, side) in enumerate(SIDES)]

    simple_style = set(styles) in ({'solid'}, {'double'})  # one style, simple lines
    single_color = len(set(colors)) == 1  # one color
    four_sides = 0 not in widths  # no 0-width border, to avoid PDF artifacts
    if simple_style and single_color and four_sides:
        # Simple case, we only draw rounded rectangles.
        draw_rounded_border(stream, box, styles[0], colors[0])
        return

    # We're not smart enough to find a good way to draw the borders, we must
    # draw them side by side. Order is not specified, but this one seems to be
    # close to what other browsers do.
    values = tuple(zip(SIDES, widths, colors, styles))
    for index in (2, 3, 1, 0):
        side, width, color, style = values[index]
        if width == 0 or not color:
            continue
        with stacked(stream):
            clip_border_segment(
                stream, style, width, side, box.rounded_border_box()[:4],
                widths, box.rounded_border_box()[4:])
            draw_rounded_border(
                stream, box, style, styled_color(style, color, side))


def draw_border_image(box, stream):
    """Draw ``box`` border image on ``stream``."""
    # See https://drafts.csswg.org/css-backgrounds-3/#border-images
    image = box.border_image
    width, height, ratio = image.get_intrinsic_size(
        box.style['image_resolution'], box.style['font_size'])
    intrinsic_width, intrinsic_height = replaced.default_image_sizing(
        width, height, ratio, specified_width=None, specified_height=None,
        default_width=box.border_width(), default_height=box.border_height())

    image_slice = box.style['border_image_slice'][:4]
    should_fill = box.style['border_image_slice'][4]

    def compute_slice_dimension(dimension, intrinsic):
        if isinstance(dimension, (int, float)):
            return min(dimension, intrinsic)
        else:
            assert dimension.unit == '%'
            return min(100, dimension.value) / 100 * intrinsic

    slice_top = compute_slice_dimension(image_slice[0], intrinsic_height)
    slice_right = compute_slice_dimension(image_slice[1], intrinsic_width)
    slice_bottom = compute_slice_dimension(image_slice[2], intrinsic_height)
    slice_left = compute_slice_dimension(image_slice[3], intrinsic_width)

    style_repeat_x, style_repeat_y = box.style['border_image_repeat']

    x, y, w, h, tl, tr, br, bl = box.rounded_border_box()
    px, py, pw, ph, ptl, ptr, pbr, pbl = box.rounded_padding_box()
    border_left = px - x
    border_top = py - y
    border_right = w - pw - border_left
    border_bottom = h - ph - border_top

    def compute_outset_dimension(dimension, from_border):
        if dimension.unit is None:
            return dimension.value * from_border
        else:
            assert dimension.unit == 'px'
            return dimension.value

    outsets = box.style['border_image_outset']
    outset_top = compute_outset_dimension(outsets[0], border_top)
    outset_right = compute_outset_dimension(outsets[1], border_right)
    outset_bottom = compute_outset_dimension(outsets[2], border_bottom)
    outset_left = compute_outset_dimension(outsets[3], border_left)

    x -= outset_left
    y -= outset_top
    w += outset_left + outset_right
    h += outset_top + outset_bottom

    def compute_width_adjustment(dimension, original, intrinsic,
                                 area_dimension):
        if dimension == 'auto':
            return intrinsic
        elif isinstance(dimension, (int, float)):
            return dimension * original
        elif dimension.unit == '%':
            return dimension.value / 100 * area_dimension
        else:
            assert dimension.unit == 'px'
            return dimension.value

    # We make adjustments to the border_* variables after handling outsets
    # because numerical outsets are relative to border-width, not
    # border-image-width. Also, the border image area that is used
    # for percentage-based border-image-width values includes any expanded
    # area due to border-image-outset.
    widths = box.style['border_image_width']
    border_top = compute_width_adjustment(
        widths[0], border_top, slice_top, h)
    border_right = compute_width_adjustment(
        widths[1], border_right, slice_right, w)
    border_bottom = compute_width_adjustment(
        widths[2], border_bottom, slice_bottom, h)
    border_left = compute_width_adjustment(
        widths[3], border_left, slice_left, w)

    def draw_border_image(x, y, width, height, slice_x, slice_y,
                          slice_width, slice_height,
                          repeat_x='stretch', repeat_y='stretch',
                          scale_x=None, scale_y=None):
        if 0 in (intrinsic_width, width, slice_width):
            scale_x = 0
        else:
            extra_dx = 0
            if not scale_x:
                scale_x = (height / slice_height) if height and slice_height else 1
            if repeat_x == 'repeat':
                n_repeats_x = ceil(width / slice_width / scale_x)
            elif repeat_x == 'space':
                n_repeats_x = floor(width / slice_width / scale_x)
                # Space is before the first repeat and after the last,
                # so there's one more space than repeat.
                extra_dx = (
                    (width / scale_x - n_repeats_x * slice_width) / (n_repeats_x + 1))
            elif repeat_x == 'round':
                n_repeats_x = max(1, round(width / slice_width / scale_x))
                scale_x = width / (n_repeats_x * slice_width)
            else:
                n_repeats_x = 1
                scale_x = width / slice_width

        if 0 in (intrinsic_height, height, slice_height):
            scale_y = 0
        else:
            extra_dy = 0
            if not scale_y:
                scale_y = (width / slice_width) if width and slice_width else 1
            if repeat_y == 'repeat':
                n_repeats_y = ceil(height / slice_height / scale_y)
            elif repeat_y == 'space':
                n_repeats_y = floor(height / slice_height / scale_y)
                # Space is before the first repeat and after the last,
                # so there's one more space than repeat.
                extra_dy = (
                    (height / scale_y - n_repeats_y * slice_height) / (n_repeats_y + 1))
            elif repeat_y == 'round':
                n_repeats_y = max(1, round(height / slice_height / scale_y))
                scale_y = height / (n_repeats_y * slice_height)
            else:
                n_repeats_y = 1
                scale_y = height / slice_height

        if 0 in (scale_x, scale_y):
            return scale_x, scale_y

        rendered_width = intrinsic_width * scale_x
        rendered_height = intrinsic_height * scale_y
        offset_x = rendered_width * slice_x / intrinsic_width
        offset_y = rendered_height * slice_y / intrinsic_height

        with stacked(stream):
            stream.rectangle(x, y, width, height)
            stream.clip()
            stream.end()
            stream.transform(e=x - offset_x + extra_dx, f=y - offset_y + extra_dy)
            stream.transform(a=scale_x, d=scale_y)
            for i in range(n_repeats_x):
                for j in range(n_repeats_y):
                    with stacked(stream):
                        translate_x = i * (slice_width + extra_dx)
                        translate_y = j * (slice_height + extra_dy)
                        stream.transform(e=translate_x, f=translate_y)
                        stream.rectangle(
                            offset_x / scale_x, offset_y / scale_y,
                            slice_width, slice_height)
                        stream.clip()
                        stream.end()
                        image.draw(
                            stream, intrinsic_width, intrinsic_height,
                            box.style['image_rendering'])

        return scale_x, scale_y

    # Top left.
    scale_left, scale_top = draw_border_image(
        x, y, border_left, border_top, 0, 0, slice_left, slice_top)
    # Top right.
    draw_border_image(
        x + w - border_right, y, border_right, border_top,
        intrinsic_width - slice_right, 0, slice_right, slice_top)
    # Bottom right.
    scale_right, scale_bottom = draw_border_image(
        x + w - border_right, y + h - border_bottom, border_right, border_bottom,
        intrinsic_width - slice_right, intrinsic_height - slice_bottom,
        slice_right, slice_bottom)
    # Bottom left.
    draw_border_image(
        x, y + h - border_bottom, border_left, border_bottom,
        0, intrinsic_height - slice_bottom, slice_left, slice_bottom)
    if slice_left + slice_right < intrinsic_width:
        # Top middle.
        draw_border_image(
            x + border_left, y, w - border_left - border_right, border_top,
            slice_left, 0, intrinsic_width - slice_left - slice_right,
            slice_top, repeat_x=style_repeat_x)
        # Bottom middle.
        draw_border_image(
            x + border_left, y + h - border_bottom,
            w - border_left - border_right, border_bottom,
            slice_left, intrinsic_height - slice_bottom,
            intrinsic_width - slice_left - slice_right, slice_bottom,
            repeat_x=style_repeat_x)
    if slice_top + slice_bottom < intrinsic_height:
        # Right middle.
        draw_border_image(
            x + w - border_right, y + border_top,
            border_right, h - border_top - border_bottom,
            intrinsic_width - slice_right, slice_top,
            slice_right, intrinsic_height - slice_top - slice_bottom,
            repeat_y=style_repeat_y)
        # Left middle.
        draw_border_image(
            x, y + border_top, border_left, h - border_top - border_bottom,
            0, slice_top, slice_left,
            intrinsic_height - slice_top - slice_bottom,
            repeat_y=style_repeat_y)
    if (should_fill and slice_left + slice_right < intrinsic_width
            and slice_top + slice_bottom < intrinsic_height):
        # Fill middle.
        draw_border_image(
            x + border_left, y + border_top, w - border_left - border_right,
            h - border_top - border_bottom, slice_left, slice_top,
            intrinsic_width - slice_left - slice_right,
            intrinsic_height - slice_top - slice_bottom,
            repeat_x=style_repeat_x, repeat_y=style_repeat_y,
            scale_x=scale_left or scale_right, scale_y=scale_top or scale_bottom)


def clip_border_segment(stream, style, width, side, border_box,
                        border_widths=None, radii=None):
    """Clip one segment of box border.

    The strategy is to remove the zones not needed because of the style or the
    side before painting.

    """
    bbx, bby, bbw, bbh = border_box
    (tlh, tlv), (trh, trv), (brh, brv), (blh, blv) = radii or 4 * ((0, 0),)
    bt, br, bb, bl = border_widths or 4 * (width,)

    def transition_point(x1, y1, x2, y2):
        """Get the point use for border transition.

        The extra boolean returned is ``True`` if the point is in the padding
        box (ie. the padding box is rounded).

        This point is not specified. We must be sure to be inside the rounded
        padding box, and in the zone defined in the "transition zone" allowed
        by the specification. We chose the corner of the transition zone. It's
        easy to get and gives quite good results, but it seems to be different
        from what other browsers do.

        """
        return (
            ((x1, y1), True) if abs(x1) > abs(x2) and abs(y1) > abs(y2)
            else ((x2, y2), False))

    def corner_half_length(a, b):
        """Return the length of the half of one ellipsis corner.

        Inspired by [Ramanujan, S., "Modular Equations and Approximations to
        pi" Quart. J. Pure. Appl. Math., vol. 45 (1913-1914), pp. 350-372],
        wonderfully explained by Dr Rob.

        https://mathforum.org/dr.math/faq/formulas/

        """
        x = (a - b) / (a + b)
        return pi / 8 * (a + b) * (
            1 + 3 * x ** 2 / (10 + sqrt(4 - 3 * x ** 2)))

    if side == 'top':
        (px1, py1), rounded1 = transition_point(tlh, tlv, bl, bt)
        (px2, py2), rounded2 = transition_point(-trh, trv, -br, bt)
        width = bt
        way = 1
        angle = 1
        main_offset = bby
    elif side == 'right':
        (px1, py1), rounded1 = transition_point(-trh, trv, -br, bt)
        (px2, py2), rounded2 = transition_point(-brh, -brv, -br, -bb)
        width = br
        way = 1
        angle = 2
        main_offset = bbx + bbw
    elif side == 'bottom':
        (px1, py1), rounded1 = transition_point(blh, -blv, bl, -bb)
        (px2, py2), rounded2 = transition_point(-brh, -brv, -br, -bb)
        width = bb
        way = -1
        angle = 3
        main_offset = bby + bbh
    elif side == 'left':
        (px1, py1), rounded1 = transition_point(tlh, tlv, bl, bt)
        (px2, py2), rounded2 = transition_point(blh, -blv, bl, -bb)
        width = bl
        way = -1
        angle = 4
        main_offset = bbx

    if side in ('top', 'bottom'):
        a1, b1 = px1 - bl / 2, way * py1 - width / 2
        a2, b2 = -px2 - br / 2, way * py2 - width / 2
        line_length = bbw - px1 + px2
        length = bbw
        stream.move_to(bbx + bbw, main_offset)
        stream.line_to(bbx, main_offset)
        stream.line_to(bbx + px1, main_offset + py1)
        stream.line_to(bbx + bbw + px2, main_offset + py2)
    elif side in ('left', 'right'):
        a1, b1 = -way * px1 - width / 2, py1 - bt / 2
        a2, b2 = -way * px2 - width / 2, -py2 - bb / 2
        line_length = bbh - py1 + py2
        length = bbh
        stream.move_to(main_offset, bby + bbh)
        stream.line_to(main_offset, bby)
        stream.line_to(main_offset + px1, bby + py1)
        stream.line_to(main_offset + px2, bby + bbh + py2)

    if style in ('dotted', 'dashed'):
        dash = width if style == 'dotted' else 3 * width
        if rounded1 or rounded2:
            # At least one of the two corners is rounded
            chl1 = corner_half_length(a1, b1)
            chl2 = corner_half_length(a2, b2)
            length = line_length + chl1 + chl2
            dash_length = round(length / dash)
            if rounded1 and rounded2:
                # 2x dashes
                dash = length / (dash_length + dash_length % 2)
            else:
                # 2x - 1/2 dashes
                dash = length / (dash_length + dash_length % 2 - 0.5)
            dashes1 = int(ceil((chl1 - dash / 2) / dash))
            dashes2 = int(ceil((chl2 - dash / 2) / dash))
            line = int(floor(line_length / dash))

            def draw_dots(dashes, line, way, x, y, px, py, chl):
                if not dashes:
                    return line + 1, 0
                for i in range(0, dashes, 2):
                    i += 0.5  # half dash
                    angle1 = (
                        ((2 * angle - way) + i * way * dash / chl) /
                        4 * pi)
                    angle2 = (min if way > 0 else max)(
                        ((2 * angle - way) + (i + 1) * way * dash / chl) /
                        4 * pi,
                        angle * pi / 2)
                    if side in ('top', 'bottom'):
                        stream.move_to(x + px, main_offset + py)
                        stream.line_to(
                            x + px - way * px * 1 / tan(angle2), main_offset)
                        stream.line_to(
                            x + px - way * px * 1 / tan(angle1), main_offset)
                    elif side in ('left', 'right'):
                        stream.move_to(main_offset + px, y + py)
                        stream.line_to(
                            main_offset, y + py + way * py * tan(angle2))
                        stream.line_to(
                            main_offset, y + py + way * py * tan(angle1))
                    if angle2 == angle * pi / 2:
                        offset = (angle1 - angle2) / ((
                            ((2 * angle - way) + (i + 1) * way * dash / chl) /
                            4 * pi) - angle1)
                        line += 1
                        break
                else:
                    offset = 1 - (
                        (angle * pi / 2 - angle2) / (angle2 - angle1))
                return line, offset

            line, offset = draw_dots(
                dashes1, line, way, bbx, bby, px1, py1, chl1)
            line = draw_dots(
                dashes2, line, -way, bbx + bbw, bby + bbh, px2, py2, chl2)[0]

            if line_length > 1e-6:
                for i in range(0, line, 2):
                    i += offset
                    if side in ('top', 'bottom'):
                        x1 = max(bbx + px1 + i * dash, bbx + px1)
                        x2 = min(bbx + px1 + (i + 1) * dash, bbx + bbw + px2)
                        y1 = main_offset - (width if way < 0 else 0)
                        y2 = y1 + width
                    elif side in ('left', 'right'):
                        y1 = max(bby + py1 + i * dash, bby + py1)
                        y2 = min(bby + py1 + (i + 1) * dash, bby + bbh + py2)
                        x1 = main_offset - (width if way > 0 else 0)
                        x2 = x1 + width
                    stream.rectangle(x1, y1, x2 - x1, y2 - y1)
        else:
            # 2x + 1 dashes
            stream.clip(even_odd=True)
            stream.end()
            dash = length / (
                round(length / dash) - (round(length / dash) + 1) % 2) or 1
            for i in range(0, int(round(length / dash)), 2):
                if side == 'top':
                    stream.rectangle(bbx + i * dash, bby, dash, width)
                elif side == 'right':
                    stream.rectangle(
                        bbx + bbw - width, bby + i * dash, width, dash)
                elif side == 'bottom':
                    stream.rectangle(
                        bbx + i * dash, bby + bbh - width, dash, width)
                elif side == 'left':
                    stream.rectangle(bbx, bby + i * dash, width, dash)
    stream.clip(even_odd=True)
    stream.end()


def draw_rounded_border(stream, box, style, color):
    if style in ('ridge', 'groove'):
        stream.set_color_rgb(*color[0][:3])
        stream.set_alpha(color[0][3])
        rounded_box_path(stream, box.rounded_padding_box())
        rounded_box_path(stream, box.rounded_box_ratio(1 / 2))
        stream.fill(even_odd=True)
        stream.set_color_rgb(*color[1][:3])
        stream.set_alpha(color[1][3])
        rounded_box_path(stream, box.rounded_box_ratio(1 / 2))
        rounded_box_path(stream, box.rounded_border_box())
        stream.fill(even_odd=True)
        return
    stream.set_color_rgb(*color[:3])
    stream.set_alpha(color[3])
    rounded_box_path(stream, box.rounded_padding_box())
    if style == 'double':
        rounded_box_path(stream, box.rounded_box_ratio(1 / 3))
        rounded_box_path(stream, box.rounded_box_ratio(2 / 3))
    rounded_box_path(stream, box.rounded_border_box())
    stream.fill(even_odd=True)


def draw_rect_border(stream, box, widths, style, color):
    bbx, bby, bbw, bbh = box
    bt, br, bb, bl = widths
    if style in ('ridge', 'groove'):
        stream.set_color_rgb(*color[0][:3])
        stream.set_alpha(color[0][3])
        stream.rectangle(*box)
        stream.rectangle(
            bbx + bl / 2, bby + bt / 2,
            bbw - (bl + br) / 2, bbh - (bt + bb) / 2)
        stream.fill(even_odd=True)
        stream.rectangle(
            bbx + bl / 2, bby + bt / 2,
            bbw - (bl + br) / 2, bbh - (bt + bb) / 2)
        stream.rectangle(bbx + bl, bby + bt, bbw - bl - br, bbh - bt - bb)
        stream.set_color_rgb(*color[1][:3])
        stream.set_alpha(color[1][3])
        stream.fill(even_odd=True)
        return
    stream.set_color_rgb(*color[:3])
    stream.set_alpha(color[3])
    stream.rectangle(*box)
    if style == 'double':
        stream.rectangle(
            bbx + bl / 3, bby + bt / 3,
            bbw - (bl + br) / 3, bbh - (bt + bb) / 3)
        stream.rectangle(
            bbx + bl * 2 / 3, bby + bt * 2 / 3,
            bbw - (bl + br) * 2 / 3, bbh - (bt + bb) * 2 / 3)
    stream.rectangle(bbx + bl, bby + bt, bbw - bl - br, bbh - bt - bb)
    stream.fill(even_odd=True)


def draw_line(stream, x1, y1, x2, y2, thickness, style, color, offset=0):
    assert x1 == x2 or y1 == y2  # Only works for vertical or horizontal lines

    with stacked(stream):
        if style not in ('ridge', 'groove'):
            stream.set_color_rgb(*color[:3], stroke=True)
            stream.set_alpha(color[3], stroke=True)

        if style == 'dashed':
            stream.set_dash([5 * thickness], offset)
        elif style == 'dotted':
            stream.set_dash([thickness], offset)

        if style == 'double':
            stream.set_line_width(thickness / 3)
            if x1 == x2:
                stream.move_to(x1 - thickness / 3, y1)
                stream.line_to(x2 - thickness / 3, y2)
                stream.move_to(x1 + thickness / 3, y1)
                stream.line_to(x2 + thickness / 3, y2)
            elif y1 == y2:
                stream.move_to(x1, y1 - thickness / 3)
                stream.line_to(x2, y2 - thickness / 3)
                stream.move_to(x1, y1 + thickness / 3)
                stream.line_to(x2, y2 + thickness / 3)
        elif style in ('ridge', 'groove'):
            stream.set_line_width(thickness / 2)
            stream.set_color_rgb(*color[0][:3], stroke=True)
            stream.set_alpha(color[0][3], stroke=True)
            if x1 == x2:
                stream.move_to(x1 + thickness / 4, y1)
                stream.line_to(x2 + thickness / 4, y2)
            elif y1 == y2:
                stream.move_to(x1, y1 + thickness / 4)
                stream.line_to(x2, y2 + thickness / 4)
            stream.stroke()
            stream.set_color_rgb(*color[1][:3], stroke=True)
            stream.set_alpha(color[1][3], stroke=True)
            if x1 == x2:
                stream.move_to(x1 - thickness / 4, y1)
                stream.line_to(x2 - thickness / 4, y2)
            elif y1 == y2:
                stream.move_to(x1, y1 - thickness / 4)
                stream.line_to(x2, y2 - thickness / 4)
        elif style == 'wavy':
            assert y1 == y2  # Only allowed for text decoration
            up = 1
            radius = 0.75 * thickness

            stream.rectangle(x1, y1 - 2 * radius, x2 - x1, 4 * radius)
            stream.clip()
            stream.end()

            x = x1 - offset
            stream.move_to(x, y1)
            while x < x2:
                stream.curve_to(
                    x + radius / 2, y1 + up * radius,
                    x + 3 * radius / 2, y1 + up * radius,
                    x + 2 * radius, y1)
                x += 2 * radius
                up *= -1
        else:
            stream.set_line_width(thickness)
            stream.move_to(x1, y1)
            stream.line_to(x2, y2)
        stream.stroke()


def draw_outlines(stream, box):
    width = box.style['outline_width']
    color = get_color(box.style, 'outline_color')
    style = box.style['outline_style']
    if box.style['visibility'] == 'visible' and width and color.alpha:
        outline_box = (
            box.border_box_x() - width, box.border_box_y() - width,
            box.border_width() + 2 * width, box.border_height() + 2 * width)
        for side in SIDES:
            with stacked(stream):
                clip_border_segment(stream, style, width, side, outline_box)
                draw_rect_border(
                    stream, outline_box, 4 * (width,), style,
                    styled_color(style, color, side))

    for child in box.children:
        if isinstance(child, boxes.Box):
            draw_outlines(stream, child)


def draw_table(stream, table):
    # Draw backgrounds
    draw_background(stream, table.background)
    for column_group in table.column_groups:
        draw_background(stream, column_group.background)
        for column in column_group.children:
            draw_background(stream, column.background)
    for row_group in table.children:
        draw_background(stream, row_group.background)
        for row in row_group.children:
            draw_background(stream, row.background)
            for cell in row.children:
                if (table.style['border_collapse'] == 'collapse' or
                        cell.style['empty_cells'] == 'show' or
                        not cell.empty):
                    draw_background(stream, cell.background)

    # Draw borders
    if table.style['border_collapse'] == 'collapse':
        return draw_collapsed_borders(stream, table)
    draw_border(stream, table)
    for row_group in table.children:
        for row in row_group.children:
            for cell in row.children:
                if cell.style['empty_cells'] == 'show' or not cell.empty:
                    draw_border(stream, cell)


def draw_collapsed_borders(stream, table):
    """Draw borders of table cells when they collapse."""
    row_heights = [
        row.height for row_group in table.children
        for row in row_group.children]
    column_widths = table.column_widths
    if not (row_heights and column_widths):
        # One of the list is empty: don’t bother with empty tables
        return
    row_positions = [
        row.position_y for row_group in table.children
        for row in row_group.children]
    column_positions = list(table.column_positions)
    grid_height = len(row_heights)
    grid_width = len(column_widths)
    assert grid_width == len(column_positions)
    # Add the end of the last column, but make a copy from the table attr.
    if table.style['direction'] == 'ltr':
        column_positions.append(column_positions[-1] + column_widths[-1])
    else:
        column_positions.insert(0, column_positions[0] + column_widths[0])
    # Add the end of the last row. No copy here, we own this list
    row_positions.append(row_positions[-1] + row_heights[-1])
    vertical_borders, horizontal_borders = table.collapsed_border_grid
    if table.children[0].is_header:
        header_rows = len(table.children[0].children)
    else:
        header_rows = 0
    if table.children[-1].is_footer:
        footer_rows = len(table.children[-1].children)
    else:
        footer_rows = 0
    skipped_rows = table.skipped_rows
    if skipped_rows:
        body_rows_offset = skipped_rows - header_rows
    else:
        body_rows_offset = 0
    original_grid_height = len(vertical_borders)
    footer_rows_offset = original_grid_height - grid_height

    def row_number(y, horizontal):
        # Examples in comments for 2 headers rows, 5 body rows, 3 footer rows
        if header_rows and y < header_rows + int(horizontal):
            # Row in header: y < 2 for vertical, y < 3 for horizontal
            return y
        elif footer_rows and y >= grid_height - footer_rows - int(horizontal):
            # Row in footer: y >= 7 for vertical, y >= 6 for horizontal
            return y + footer_rows_offset
        else:
            # Row in body: 2 >= y > 7 for vertical, 3 >= y > 6 for horizontal
            return y + body_rows_offset

    segments = []

    def half_max_width(border_list, yx_pairs, vertical=True):
        result = 0
        for y, x in yx_pairs:
            if (
                (0 <= y < grid_height and 0 <= x <= grid_width)
                if vertical else
                (0 <= y <= grid_height and 0 <= x < grid_width)
            ):
                yy = row_number(y, horizontal=not vertical)
                _, (_, width, _) = border_list[yy][x]
                result = max(result, width)
        return result / 2

    def add_vertical(x, y):
        yy = row_number(y, horizontal=False)
        score, (style, width, color) = vertical_borders[yy][x]
        if width == 0 or color.alpha == 0:
            return
        pos_x = column_positions[x]
        pos_y1 = row_positions[y]
        if y != 0 or not table.skip_cell_border_top:
            pos_y1 -= half_max_width(horizontal_borders, [
                (y, x - 1), (y, x)], vertical=False)
        pos_y2 = row_positions[y + 1]
        if y != grid_height - 1 or not table.skip_cell_border_bottom:
            pos_y2 += half_max_width(horizontal_borders, [
                (y + 1, x - 1), (y + 1, x)], vertical=False)
        segments.append((
            score, style, width, color, 'left',
            (pos_x, pos_y1, 0, pos_y2 - pos_y1)))

    def add_horizontal(x, y):
        if y == 0 and table.skip_cell_border_top:
            return
        if y == grid_height and table.skip_cell_border_bottom:
            return
        yy = row_number(y, horizontal=True)
        score, (style, width, color) = horizontal_borders[yy][x]
        if width == 0 or color.alpha == 0:
            return
        pos_y = row_positions[y]
        shift_before = half_max_width(vertical_borders, [(y - 1, x), (y, x)])
        shift_after = half_max_width(
            vertical_borders, [(y - 1, x + 1), (y, x + 1)])
        if table.style['direction'] == 'ltr':
            pos_x1 = column_positions[x] - shift_before
            pos_x2 = column_positions[x + 1] + shift_after
        else:
            pos_x1 = column_positions[x + 1] - shift_after
            pos_x2 = column_positions[x] + shift_before
        segments.append((
            score, style, width, color, 'top',
            (pos_x1, pos_y, pos_x2 - pos_x1, 0)))

    for x in range(grid_width):
        add_horizontal(x, 0)
    for y in range(grid_height):
        add_vertical(0, y)
        for x in range(grid_width):
            add_vertical(x + 1, y)
            add_horizontal(x, y + 1)

    # Sort bigger scores last (painted later, on top)
    # Since the number of different scores is expected to be small compared
    # to the number of segments, there should be little changes and Timsort
    # should be closer to O(n) than O(n * log(n))
    segments.sort(key=operator.itemgetter(0))

    for segment in segments:
        _, style, width, color, side, border_box = segment
        with stacked(stream):
            bx, by, bw, bh = border_box
            draw_line(
                stream, bx, by, bx + bw, by + bh, width, style,
                styled_color(style, color, side))


def draw_replacedbox(stream, box):
    """Draw the given :class:`boxes.ReplacedBox` to a ``document.Stream``."""
    if box.style['visibility'] != 'visible' or not box.width or not box.height:
        return

    draw_width, draw_height, draw_x, draw_y = replaced.replacedbox_layout(box)
    if draw_width <= 0 or draw_height <= 0:
        return

    with stacked(stream):
        stream.set_alpha(1)
        stream.transform(e=draw_x, f=draw_y)
        with stacked(stream):
            # TODO: Use the real intrinsic size here, not affected by
            # 'image-resolution'?
            box.replacement.draw(
                stream, draw_width, draw_height, box.style['image_rendering'])


def draw_inline_level(stream, page, box, offset_x=0, text_overflow='clip',
                      block_ellipsis='none'):
    if isinstance(box, StackingContext):
        stacking_context = box
        assert isinstance(stacking_context.box, (
            boxes.InlineBlockBox, boxes.InlineFlexBox, boxes.InlineGridBox))
        draw_stacking_context(stream, stacking_context)
    else:
        draw_background(stream, box.background)
        draw_border(stream, box)
        if isinstance(box, (boxes.InlineBox, boxes.LineBox)):
            link_annotation = None
            if isinstance(box, boxes.LineBox):
                text_overflow = box.text_overflow
                block_ellipsis = box.block_ellipsis
            else:
                link_annotation = box.link_annotation
            ellipsis = 'none'
            if link_annotation:
                stream.begin_marked_content(box, mcid=True, tag='Link')
            for i, child in enumerate(box.children):
                if i == len(box.children) - 1:
                    # Last child
                    ellipsis = block_ellipsis
                if isinstance(child, StackingContext):
                    child_offset_x = offset_x
                else:
                    child_offset_x = (
                        offset_x + child.position_x - box.position_x)
                if isinstance(child, boxes.TextBox):
                    draw_text(
                        stream, child, child_offset_x, text_overflow, ellipsis)
                else:
                    draw_inline_level(
                        stream, page, child, child_offset_x, text_overflow,
                        ellipsis)
            if link_annotation:
                stream.end_marked_content()
        elif isinstance(box, boxes.InlineReplacedBox):
            draw_replacedbox(stream, box)
        else:
            assert isinstance(box, boxes.TextBox)
            # Should only happen for list markers
            draw_text(stream, box, offset_x, text_overflow)


def draw_text(stream, textbox, offset_x, text_overflow, block_ellipsis):
    """Draw a textbox to a pydyf stream."""
    # Pango crashes with font-size: 0
    assert textbox.style['font_size']

    if textbox.style['visibility'] != 'visible':
        return

    text_decoration_values = textbox.style['text_decoration_line']
    text_decoration_color = get_color(textbox.style, 'text_decoration_color')
    if 'overline' in text_decoration_values:
        thickness = textbox.pango_layout.underline_thickness
        offset_y = (
            textbox.baseline - textbox.pango_layout.ascent + thickness / 2)
        draw_text_decoration(
            stream, textbox, offset_x, offset_y, thickness,
            text_decoration_color)
    if 'underline' in text_decoration_values:
        thickness = textbox.pango_layout.underline_thickness
        offset_y = (
            textbox.baseline - textbox.pango_layout.underline_position +
            thickness / 2)
        draw_text_decoration(
            stream, textbox, offset_x, offset_y, thickness,
            text_decoration_color)

    x, y = textbox.position_x, textbox.position_y + textbox.baseline
    stream.set_color_rgb(*textbox.style['color'][:3])
    stream.set_alpha(textbox.style['color'][3])

    textbox.pango_layout.reactivate(textbox.style)
    stream.begin_text()
    emojis = draw_first_line(
        stream, textbox, text_overflow, block_ellipsis, Matrix(d=-1, e=x, f=y))
    stream.end_text()

    draw_emojis(stream, textbox.style['font_size'], x, y, emojis)

    if 'line-through' in text_decoration_values:
        thickness = textbox.pango_layout.strikethrough_thickness
        offset_y = (
            textbox.baseline - textbox.pango_layout.strikethrough_position)
        draw_text_decoration(
            stream, textbox, offset_x, offset_y, thickness,
            text_decoration_color)

    textbox.pango_layout.deactivate()


def draw_emojis(stream, font_size, x, y, emojis):
    for image, font, a, d, e, f in emojis:
        with stacked(stream):
            stream.transform(a=a, d=d, e=x + e * font_size, f=y + f)
            image.draw(stream, font_size, font_size, None)


def draw_first_line(stream, textbox, text_overflow, block_ellipsis, matrix):
    """Draw the given ``textbox`` line to the document ``stream``."""
    # Don’t draw lines with only invisible characters
    if not textbox.text.strip():
        return []

    font_size = textbox.style['font_size']
    if font_size < 1e-6:  # Default float precision used by pydyf
        return []

    pango.pango_layout_set_single_paragraph_mode(
        textbox.pango_layout.layout, True)

    if text_overflow == 'ellipsis' or block_ellipsis != 'none':
        assert textbox.pango_layout.max_width is not None
        max_width = textbox.pango_layout.max_width
        pango.pango_layout_set_width(
            textbox.pango_layout.layout, units_from_double(max_width))
        if text_overflow == 'ellipsis':
            pango.pango_layout_set_ellipsize(
                textbox.pango_layout.layout, pango.PANGO_ELLIPSIZE_END)
        else:
            if block_ellipsis == 'auto':
                ellipsis = '…'
            else:
                assert block_ellipsis[0] == 'string'
                ellipsis = block_ellipsis[1]

            # Remove last word if hyphenated
            new_text = textbox.pango_layout.text
            if new_text.endswith(textbox.style['hyphenate_character']):
                last_word_end = get_last_word_end(
                    new_text[:-len(textbox.style['hyphenate_character'])],
                    textbox.style['lang'])
                if last_word_end:
                    new_text = new_text[:last_word_end]

            textbox.pango_layout.set_text(new_text + ellipsis)

    first_line, index = textbox.pango_layout.get_first_line()

    if block_ellipsis != 'none':
        while index:
            last_word_end = get_last_word_end(
                textbox.pango_layout.text[:-len(ellipsis)],
                textbox.style['lang'])
            if last_word_end is None:
                break
            new_text = textbox.pango_layout.text[:last_word_end]
            textbox.pango_layout.set_text(new_text + ellipsis)
            first_line, index = textbox.pango_layout.get_first_line()

    utf8_text = textbox.pango_layout.text.encode()
    previous_utf8_position = 0
    stream.text_matrix(*matrix.values)
    last_font = None
    string = ''
    x_advance = 0
    emojis = []
    run = first_line.runs[0]
    while run != ffi.NULL:
        # Pango objects
        glyph_item = run.data
        run = run.next
        glyph_string = glyph_item.glyphs
        glyphs = glyph_string.glyphs
        num_glyphs = glyph_string.num_glyphs
        offset = glyph_item.item.offset
        clusters = glyph_string.log_clusters

        # Font content
        pango_font = glyph_item.item.analysis.font
        font = stream.add_font(pango_font)

        # Positions of the glyphs in the UTF-8 string
        utf8_positions = [offset + clusters[i] for i in range(1, num_glyphs)]
        utf8_positions.append(offset + glyph_item.item.length)

        # Go through the run glyphs
        if font != last_font:
            if string:
                stream.show_text(string)
            string = ''
            stream.set_font_size(font.hash, 1 if font.bitmap else font_size)
            last_font = font
        string += '<'
        for i in range(num_glyphs):
            glyph_info = glyphs[i]
            glyph = glyph_info.glyph
            width = glyph_info.geometry.width
            if (glyph == pango.PANGO_GLYPH_EMPTY or
                    glyph & pango.PANGO_GLYPH_UNKNOWN_FLAG):
                string += f'>{-width / font_size}<'
                continue
            utf8_position = utf8_positions[i]

            offset = glyph_info.geometry.x_offset / font_size
            rise = glyph_info.geometry.y_offset / 1000
            if rise:
                if string[-1] == '<':
                    string = string[:-1]
                else:
                    string += '>'
                stream.show_text(string)
                stream.set_text_rise(-rise)
                string = ''
                if offset:
                    string = f'{-offset}'
                string += f'<{glyph:02x}>' if font.bitmap else f'<{glyph:04x}>'
                stream.show_text(string)
                stream.set_text_rise(0)
                string = '<'
            else:
                if offset:
                    string += f'>{-offset}<'
                string += f'{glyph:02x}' if font.bitmap else f'{glyph:04x}'

            # Ink bounding box and logical widths in font
            if glyph not in font.widths:
                pango.pango_font_get_glyph_extents(
                    pango_font, glyph, stream.ink_rect, stream.logical_rect)
                font.widths[glyph] = int(round(
                    units_to_double(stream.logical_rect.width * 1000) /
                    font_size))

            # Kerning, word spacing, letter spacing
            kerning = int(
                font.widths[glyph] -
                units_to_double(width * 1000) / font_size +
                offset)
            if kerning:
                string += f'>{kerning}<'

            # Mapping between glyphs and characters
            if glyph not in font.cmap:
                utf8_slice = slice(previous_utf8_position, utf8_position)
                font.cmap[glyph] = utf8_text[utf8_slice].decode()
            previous_utf8_position = utf8_position

            if font.svg:
                svg_data = get_hb_object_data(font.hb_face, 'svg', glyph)
                if svg_data:
                    # Do as explained in specification
                    # https://learn.microsoft.com/typography/opentype/spec/svg
                    tree = ElementTree.fromstring(svg_data)
                    defs = ElementTree.Element('defs')
                    for child in list(tree):
                        defs.append(child)
                        tree.remove(child)
                    tree.append(defs)
                    ElementTree.SubElement(
                        tree, 'use', attrib={'href': f'#glyph{glyph}'})
                    image = SVGImage(tree, None, None, stream)
                    a = d = font.widths[glyph] / 1000 / font.upem * font_size
                    emojis.append([image, font, a, d, x_advance, 0])
            elif font.png:
                png_data = get_hb_object_data(font.hb_font, 'png', glyph)
                if png_data:
                    pillow_image = Image.open(BytesIO(png_data))
                    image_id = f'{font.hash}{glyph}'
                    image = RasterImage(pillow_image, image_id, png_data)
                    d = font.widths[glyph] / 1000
                    a = pillow_image.width / pillow_image.height * d
                    pango.pango_font_get_glyph_extents(
                        pango_font, glyph, stream.ink_rect,
                        stream.logical_rect)
                    f = units_to_double(
                        (-stream.logical_rect.y - stream.logical_rect.height))
                    f = f / font_size - font_size
                    emojis.append([image, font, a, d, x_advance, f])

            x_advance += (font.widths[glyph] + offset - kerning) / 1000

        # Close the last glyphs list, remove if empty
        if string[-1] == '<':
            string = string[:-1]
        else:
            string += '>'

    # Draw text
    stream.show_text(string)

    return emojis


def draw_text_decoration(stream, textbox, offset_x, offset_y, thickness,
                         color):
    """Draw text-decoration of ``textbox`` to a ``document.Stream``."""
    draw_line(
        stream, textbox.position_x, textbox.position_y + offset_y,
        textbox.position_x + textbox.width, textbox.position_y + offset_y,
        thickness, textbox.style['text_decoration_style'], color, offset_x)
