"""
    weasyprint.draw
    ---------------

    Take an "after layout" box tree and draw it onto a cairo context.

"""

import contextlib
import operator
from math import ceil, floor, pi, sqrt, tan

import cairocffi as cairo

from .formatting_structure import boxes
from .images import SVGImage
from .layout import replaced
from .layout.backgrounds import BackgroundLayer
from .stacking import StackingContext
from .text import show_first_line

SIDES = ('top', 'right', 'bottom', 'left')
CROP = '''
  <!-- horizontal top left -->
  <path d="M0,{bleed_top} h{half_bleed_left}" />
  <!-- horizontal top right -->
  <path d="M0,{bleed_top} h{half_bleed_right}"
        transform="translate({width},0) scale(-1,1)" />
  <!-- horizontal bottom right -->
  <path d="M0,{bleed_bottom} h{half_bleed_right}"
        transform="translate({width},{height}) scale(-1,-1)" />
  <!-- horizontal bottom left -->
  <path d="M0,{bleed_bottom} h{half_bleed_left}"
        transform="translate(0,{height}) scale(1,-1)" />
  <!-- vertical top left -->
  <path d="M{bleed_left},0 v{half_bleed_top}" />
  <!-- vertical bottom right -->
  <path d="M{bleed_right},0 v{half_bleed_bottom}"
        transform="translate({width},{height}) scale(-1,-1)" />
  <!-- vertical bottom left -->
  <path d="M{bleed_left},0 v{half_bleed_bottom}"
        transform="translate(0,{height}) scale(1,-1)" />
  <!-- vertical top right -->
  <path d="M{bleed_right},0 v{half_bleed_top}"
        transform="translate({width},0) scale(-1,1)" />
'''
CROSS = '''
  <!-- top -->
  <circle r="{half_bleed_top}"
          transform="scale(0.5)
                     translate({width},{half_bleed_top}) scale(0.5)" />
  <path d="M-{half_bleed_top},{half_bleed_top} h{bleed_top}
           M0,0 v{bleed_top}"
        transform="scale(0.5) translate({width},0)" />
  <!-- bottom -->
  <circle r="{half_bleed_bottom}"
          transform="translate(0,{height}) scale(0.5)
                     translate({width},-{half_bleed_bottom}) scale(0.5)" />
  <path d="M-{half_bleed_bottom},-{half_bleed_bottom} h{bleed_bottom}
           M0,0 v-{bleed_bottom}"
        transform="translate(0,{height}) scale(0.5) translate({width},0)" />
  <!-- left -->
  <circle r="{half_bleed_left}"
          transform="scale(0.5)
                     translate({half_bleed_left},{height}) scale(0.5)" />
  <path d="M{half_bleed_left},-{half_bleed_left} v{bleed_left}
           M0,0 h{bleed_left}"
        transform="scale(0.5) translate(0,{height})" />
  <!-- right -->
  <circle r="{half_bleed_right}"
          transform="translate({width},0) scale(0.5)
                     translate(-{half_bleed_right},{height}) scale(0.5)" />
  <path d="M-{half_bleed_right},-{half_bleed_right} v{bleed_right}
           M0,0 h-{bleed_right}"
        transform="translate({width},0)
                   scale(0.5) translate(0,{height})" />
'''


@contextlib.contextmanager
def stacked(context):
    """Save and restore the context when used with the ``with`` keyword."""
    context.push_state()
    try:
        yield
    finally:
        context.pop_state()


def hsv2rgb(hue, saturation, value):
    """Transform a HSV color to a RGB color."""
    c = value * saturation
    x = c * (1 - abs((hue / 60) % 2 - 1))
    m = value - c
    if 0 <= hue < 60:
        return c + m, x + m, m
    elif 60 <= hue < 120:
        return x + m, c + m, m
    elif 120 <= hue < 180:
        return m, c + m, x + m
    elif 180 <= hue < 240:
        return m, x + m, c + m
    elif 240 <= hue < 300:
        return x + m, m, c + m
    elif 300 <= hue < 360:
        return c + m, m, x + m


def rgb2hsv(red, green, blue):
    """Transform a RGB color to a HSV color."""
    cmax = max(red, green, blue)
    cmin = min(red, green, blue)
    delta = cmax - cmin
    if delta == 0:
        hue = 0
    elif cmax == red:
        hue = 60 * ((green - blue) / delta % 6)
    elif cmax == green:
        hue = 60 * ((blue - red) / delta + 2)
    elif cmax == blue:
        hue = 60 * ((red - green) / delta + 4)
    saturation = 0 if delta == 0 else delta / cmax
    return hue, saturation, cmax


def get_color(style, key):
    value = style[key]
    return value if value != 'currentColor' else style['color']


def darken(color):
    """Return a darker color."""
    hue, saturation, value = rgb2hsv(color.red, color.green, color.blue)
    value /= 1.5
    saturation /= 1.25
    return hsv2rgb(hue, saturation, value) + (color.alpha,)


def lighten(color):
    """Return a lighter color."""
    hue, saturation, value = rgb2hsv(color.red, color.green, color.blue)
    value = 1 - (1 - value) / 1.5
    if saturation:
        saturation = 1 - (1 - saturation) / 1.25
    return hsv2rgb(hue, saturation, value) + (color.alpha,)


def draw_page(page, context):
    """Draw the given PageBox."""
    bleed = {
        side: page.style['bleed_%s' % side].value
        for side in ('top', 'right', 'bottom', 'left')}
    marks = page.style['marks']
    stacking_context = StackingContext.from_page(page)
    draw_background(
        context, stacking_context.box.background, clip_box=False, bleed=bleed,
        marks=marks)
    draw_background(context, page.canvas_background, clip_box=False)
    draw_border(context, page)
    draw_stacking_context(context, stacking_context)


def draw_box_background_and_border(context, page, box):
    draw_background(context, box.background)
    if isinstance(box, boxes.TableBox):
        draw_table_backgrounds(context, page, box)
        if box.style['border_collapse'] == 'separate':
            draw_border(context, box)
            for row_group in box.children:
                for row in row_group.children:
                    for cell in row.children:
                        if (cell.style['empty_cells'] == 'show' or
                                not cell.empty):
                            draw_border(context, cell)
        else:
            draw_collapsed_borders(context, box)
    else:
        draw_border(context, box)


def draw_stacking_context(context, stacking_context):
    """Draw a ``stacking_context`` on ``context``."""
    # See http://www.w3.org/TR/CSS2/zindex.html
    with stacked(context):
        box = stacking_context.box
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
            context.rectangle(
                box.border_box_x() + right,
                box.border_box_y() + top,
                left - right,
                bottom - top)
            context.clip()
            context.end()

        if box.style['opacity'] < 1:
            context = context.push_group([
                box.border_box_x(), box.border_box_y(),
                box.border_box_x() + box.border_width(),
                box.border_box_y() + box.border_height()])

        if box.transformation_matrix:
            if box.transformation_matrix.determinant:
                ((a, b, _), (c, d, _), (e, f, _)) = box.transformation_matrix
                context.transform(a, b, c, d, e, f)
            else:
                return

        # Point 1 is done in draw_page

        # Point 2
        if isinstance(box, (boxes.BlockBox, boxes.MarginBox,
                            boxes.InlineBlockBox, boxes.TableCellBox,
                            boxes.FlexContainerBox)):
            # The canvas background was removed by set_canvas_background
            draw_box_background_and_border(
                context, stacking_context.page, box)

        with stacked(context):
            if box.style['overflow'] != 'visible':
                # Only clip the content and the children:
                # - the background is already clipped
                # - the border must *not* be clipped
                rounded_box_path(context, box.rounded_padding_box())
                context.clip()
                context.end()

            # Point 3
            for child_context in stacking_context.negative_z_contexts:
                draw_stacking_context(context, child_context)

            # Point 4
            for block in stacking_context.block_level_boxes:
                draw_box_background_and_border(
                    context, stacking_context.page, block)

            # Point 5
            for child_context in stacking_context.float_contexts:
                draw_stacking_context(context, child_context)

            # Point 6
            if isinstance(box, boxes.InlineBox):
                draw_inline_level(
                    context, stacking_context.page, box)

            # Point 7
            for block in [box] + stacking_context.blocks_and_cells:
                if isinstance(block, boxes.ReplacedBox):
                    draw_replacedbox(context, block)
                else:
                    for child in block.children:
                        if isinstance(child, boxes.LineBox):
                            draw_inline_level(
                                context, stacking_context.page, child)

            # Point 8
            for child_context in stacking_context.zero_z_contexts:
                draw_stacking_context(context, child_context)

            # Point 9
            for child_context in stacking_context.positive_z_contexts:
                draw_stacking_context(context, child_context)

        # Point 10
        draw_outlines(context, box)

        if box.style['opacity'] < 1:
            group_id = context.id
            context = context.pop_group()
            context.push_state()
            context.set_alpha(box.style['opacity'], stroke=None)
            context.draw_x_object(group_id)
            context.pop_state()


def rounded_box_path(context, radii):
    """Draw the path of the border radius box.

    ``widths`` is a tuple of the inner widths (top, right, bottom, left) from
    the border box. Radii are adjusted from these values. Default is (0, 0, 0,
    0).

    """
    x, y, w, h, tl, tr, br, bl = radii

    if all(0 in corner for corner in (tl, tr, br, bl)):
        # No radius, draw a rectangle
        context.rectangle(x, y, w, h)
        return

    r = 0.45

    context.move_to(x + tl[0], y)
    context.line_to(x + w - tr[0], y)
    context.curve_to(
        x + w - tr[0] * r, y, x + w, y + tr[1] * r, x + w, y + tr[1])
    context.line_to(x + w, y + h - br[1])
    context.curve_to(
        x + w, y + h - br[1] * r, x + w - br[0] * r, y + h, x + w - br[0],
        y + h)
    context.line_to(x + bl[0], y + h)
    context.curve_to(
        x + bl[0] * r, y + h, x, y + h - bl[1] * r, x, y + h - bl[1])
    context.line_to(x, y + tl[1])
    context.curve_to(
        x, y + tl[1] * r, x + tl[0] * r, y, x + tl[0], y)


def draw_background(context, bg, clip_box=True, bleed=None, marks=()):
    """Draw the background color and image to a ``document.Context``.

    If ``clip_box`` is set to ``False``, the background is not clipped to the
    border box of the background, but only to the painting area.

    """
    if bg is None:
        return

    with stacked(context):
        if clip_box:
            for box in bg.layers[-1].clipped_boxes:
                rounded_box_path(context, box)
            context.clip()
            context.end()

        # Background color
        if bg.color.alpha > 0:
            with stacked(context):
                painting_area = bg.layers[-1].painting_area
                if painting_area:
                    if bleed:
                        # Painting area is the PDF BleedBox
                        x, y, width, height = painting_area
                        painting_area = (
                            x - bleed['left'], y - bleed['top'],
                            width + bleed['left'] + bleed['right'],
                            height + bleed['top'] + bleed['bottom'])
                    context.rectangle(*painting_area)
                    context.clip()
                    context.end()
                # TODO: how to paint the whole page?
                context.rectangle(-10**10, -10**10, 2 * 10**10, 2 * 10**10)
                context.set_color_rgb(*bg.color[:3])
                context.set_alpha(bg.color.alpha)
                context.fill()

        if bleed and marks:
            x, y, width, height = bg.layers[-1].painting_area
            x -= bleed['left']
            y -= bleed['top']
            width += bleed['left'] + bleed['right']
            height += bleed['top'] + bleed['bottom']
            svg = '''
              <svg height="{height}" width="{width}"
                   fill="transparent" stroke="black" stroke-width="1"
                   xmlns="http://www.w3.org/2000/svg"
                   xmlns:xlink="http://www.w3.org/1999/xlink">
            '''
            if 'crop' in marks:
                svg += CROP
            if 'cross' in marks:
                svg += CROSS
            svg += '</svg>'
            half_bleed = {key: value * 0.5 for key, value in bleed.items()}
            image = SVGImage(svg.format(
                height=height, width=width,
                bleed_left=bleed['left'], bleed_right=bleed['right'],
                bleed_top=bleed['top'], bleed_bottom=bleed['bottom'],
                half_bleed_left=half_bleed['left'],
                half_bleed_right=half_bleed['right'],
                half_bleed_top=half_bleed['top'],
                half_bleed_bottom=half_bleed['bottom'],
            ), '', None)
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
            draw_background_image(context, layer, bg.image_rendering)


def draw_table_backgrounds(context, page, table):
    """Draw the background color and image of the table children."""
    for column_group in table.column_groups:
        draw_background(context, column_group.background)
        for column in column_group.children:
            draw_background(context, column.background)
    for row_group in table.children:
        draw_background(context, row_group.background)
        for row in row_group.children:
            draw_background(context, row.background)
            for cell in row.children:
                if (table.style['border_collapse'] == 'collapse' or
                        cell.style['empty_cells'] == 'show' or
                        not cell.empty):
                    draw_background(context, cell.background)


def draw_background_image(context, layer, image_rendering):
    if layer.image is None:
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
        # want to be sure it will not be repeated on the painting_width.
        repeat_width = max(image_width, painting_width)
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
            repeat_width = image_width

    # Comments above apply here too.
    if repeat_y == 'no-repeat':
        repeat_height = max(image_height, painting_height)
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
            repeat_height = image_height

    sub_surface = cairo.PDFSurface(None, repeat_width, repeat_height)
    sub_context = cairo.Context(sub_surface)
    sub_context.rectangle(0, 0, image_width, image_height)
    sub_context.clip()
    sub_context.end()
    layer.image.draw(sub_context, image_width, image_height, image_rendering)
    pattern = cairo.SurfacePattern(sub_surface)

    if repeat_x == repeat_y == 'no-repeat':
        pattern.set_extend(cairo.EXTEND_NONE)
    else:
        pattern.set_extend(cairo.EXTEND_REPEAT)

    with stacked(context):
        if not layer.unbounded:
            context.rectangle(
                painting_x, painting_y, painting_width, painting_height)
            context.clip()
            context.end()
        # else: unrestricted, whole page box

        context.transform(
            0, 0, 0, 0, positioning_x + position_x, positioning_y + position_y)
        # TODO: handle this
        # context.set_source(pattern)
        # context.paint()


def xy_offset(x, y, offset_x, offset_y, offset):
    """Increment X and Y coordinates by the given offsets."""
    return x + offset_x * offset, y + offset_y * offset


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


def draw_border(context, box):
    """Draw the box border to a ``document.Context``."""
    # We need a plan to draw beautiful borders, and that's difficult, no need
    # to lie. Let's try to find the cases that we can handle in a smart way.

    def draw_column_border():
        """Draw column borders."""
        columns = (
            isinstance(box, boxes.BlockContainerBox) and (
                box.style['column_width'] != 'auto' or
                box.style['column_count'] != 'auto'))
        if columns and box.style['column_rule_width']:
            border_widths = (0, 0, 0, box.style['column_rule_width'])
            for child in box.children[1:]:
                with stacked(context):
                    position_x = (child.position_x - (
                        box.style['column_rule_width'] +
                        box.style['column_gap']) / 2)
                    border_box = (
                        position_x, child.position_y,
                        box.style['column_rule_width'], box.height)
                    clip_border_segment(
                        context, box.style['column_rule_style'],
                        box.style['column_rule_width'], 'left', border_box,
                        border_widths)
                    draw_rect_border(
                        context, border_box, border_widths,
                        box.style['column_rule_style'], styled_color(
                            box.style['column_rule_style'],
                            get_color(box.style, 'column_rule_color'), 'left'))

    # The box is hidden, easy.
    if box.style['visibility'] != 'visible':
        draw_column_border()
        return

    widths = [getattr(box, 'border_%s_width' % side) for side in SIDES]

    # No border, return early.
    if all(width == 0 for width in widths):
        draw_column_border()
        return

    colors = [get_color(box.style, 'border_%s_color' % side) for side in SIDES]
    styles = [
        colors[i].alpha and box.style['border_%s_style' % side]
        for (i, side) in enumerate(SIDES)]

    # The 4 sides are solid or double, and they have the same color. Oh yeah!
    # We can draw them so easily!
    if set(styles) in (set(('solid',)), set(('double',))) and (
            len(set(colors)) == 1):
        draw_rounded_border(context, box, styles[0], colors[0])
        draw_column_border()
        return

    # We're not smart enough to find a good way to draw the borders :/. We must
    # draw them side by side.
    for side, width, color, style in zip(SIDES, widths, colors, styles):
        if width == 0 or not color:
            continue
        with stacked(context):
            clip_border_segment(
                context, style, width, side, box.rounded_border_box()[:4],
                widths, box.rounded_border_box()[4:])
            draw_rounded_border(
                context, box, style, styled_color(style, color, side))

    draw_column_border()


def clip_border_segment(context, style, width, side, border_box,
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

        http://mathforum.org/dr.math/faq/formulas/

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
        context.move_to(bbx + bbw, main_offset)
        context.line_to(bbx, main_offset)
        context.line_to(bbx + px1, main_offset + py1)
        context.line_to(bbx + bbw + px2, main_offset + py2)
    elif side in ('left', 'right'):
        a1, b1 = -way * px1 - width / 2, py1 - bt / 2
        a2, b2 = -way * px2 - width / 2, -py2 - bb / 2
        line_length = bbh - py1 + py2
        length = bbh
        context.move_to(main_offset, bby + bbh)
        context.line_to(main_offset, bby)
        context.line_to(main_offset + px1, bby + py1)
        context.line_to(main_offset + px2, bby + bbh + py2)

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
                        context.move_to(x + px, main_offset + py)
                        context.line_to(
                            x + px - way * px * 1 / tan(angle2),
                            main_offset)
                        context.line_to(
                            x + px - way * px * 1 / tan(angle1),
                            main_offset)
                    elif side in ('left', 'right'):
                        context.move_to(main_offset + px, y + py)
                        context.line_to(
                            main_offset,
                            y + py + way * py * tan(angle2))
                        context.line_to(
                            main_offset,
                            y + py + way * py * tan(angle1))
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
                    context.rectangle(x1, y1, x2 - x1, y2 - y1)
        else:
            # 2x + 1 dashes
            context.clip(even_odd=True)
            context.end()
            dash = length / (
                round(length / dash) - (round(length / dash) + 1) % 2) or 1
            for i in range(0, int(round(length / dash)), 2):
                if side == 'top':
                    context.rectangle(
                        bbx + i * dash, bby, dash, width)
                elif side == 'right':
                    context.rectangle(
                        bbx + bbw - width, bby + i * dash, width, dash)
                elif side == 'bottom':
                    context.rectangle(
                        bbx + i * dash, bby + bbh - width, dash, width)
                elif side == 'left':
                    context.rectangle(
                        bbx, bby + i * dash, width, dash)
    context.clip(even_odd=True)
    context.end()


def draw_rounded_border(context, box, style, color):
    rounded_box_path(context, box.rounded_padding_box())
    if style in ('ridge', 'groove'):
        rounded_box_path(context, box.rounded_box_ratio(1 / 2))
        context.set_color_rgb(*color[0][:3])
        context.set_alpha(color[0][3])
        context.fill(even_odd=True)
        rounded_box_path(context, box.rounded_box_ratio(1 / 2))
        rounded_box_path(context, box.rounded_border_box())
        context.set_color_rgb(*color[1][:3])
        context.set_alpha(color[1][3])
        context.fill(even_odd=True)
        return
    if style == 'double':
        rounded_box_path(context, box.rounded_box_ratio(1 / 3))
        rounded_box_path(context, box.rounded_box_ratio(2 / 3))
    rounded_box_path(context, box.rounded_border_box())
    context.set_color_rgb(*color[:3])
    context.set_alpha(color[3])
    context.fill(even_odd=True)


def draw_rect_border(context, box, widths, style, color):
    bbx, bby, bbw, bbh = box
    bt, br, bb, bl = widths
    context.rectangle(*box)
    if style in ('ridge', 'groove'):
        context.rectangle(
            bbx + bl / 2, bby + bt / 2,
            bbw - (bl + br) / 2, bbh - (bt + bb) / 2)
        context.set_color_rgb(*color[0][:3])
        context.set_alpha(color[0][3])
        context.fill(even_odd=True)
        context.rectangle(
            bbx + bl / 2, bby + bt / 2,
            bbw - (bl + br) / 2, bbh - (bt + bb) / 2)
        context.rectangle(
            bbx + bl, bby + bt, bbw - bl - br, bbh - bt - bb)
        context.set_color_rgb(*color[1][:3])
        context.set_alpha(color[1][3])
        context.fill(even_odd=True)
        return
    if style == 'double':
        context.rectangle(
            bbx + bl / 3, bby + bt / 3,
            bbw - (bl + br) / 3, bbh - (bt + bb) / 3)
        context.rectangle(
            bbx + bl * 2 / 3, bby + bt * 2 / 3,
            bbw - (bl + br) * 2 / 3, bbh - (bt + bb) * 2 / 3)
    context.rectangle(bbx + bl, bby + bt, bbw - bl - br, bbh - bt - bb)
    context.set_color_rgb(*color[:3])
    context.set_alpha(color[3])
    context.fill(even_odd=True)


def draw_outlines(context, box):
    width = box.style['outline_width']
    color = get_color(box.style, 'outline_color')
    style = box.style['outline_style']
    if box.style['visibility'] == 'visible' and width and color.alpha:
        outline_box = (
            box.border_box_x() - width, box.border_box_y() - width,
            box.border_width() + 2 * width, box.border_height() + 2 * width)
        for side in SIDES:
            with stacked(context):
                clip_border_segment(context, style, width, side, outline_box)
                draw_rect_border(
                    context, outline_box, 4 * (width,), style,
                    styled_color(style, color, side))

    if isinstance(box, boxes.ParentBox):
        for child in box.children:
            if isinstance(child, boxes.Box):
                draw_outlines(context, child)


def draw_collapsed_borders(context, table):
    """Draw borders of table cells when they collapse."""
    row_heights = [row.height for row_group in table.children
                   for row in row_group.children]
    column_widths = table.column_widths
    if not (row_heights and column_widths):
        # One of the list is empty: don’t bother with empty tables
        return
    row_positions = [row.position_y for row_group in table.children
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
    if header_rows == 0:
        header_rows = -1
    if footer_rows:
        first_footer_row = grid_height - footer_rows - 1
    else:
        first_footer_row = grid_height + 1
    original_grid_height = len(vertical_borders)
    footer_rows_offset = original_grid_height - grid_height

    def row_number(y, horizontal):
        if y < (header_rows + int(horizontal)):
            return y
        elif y >= (first_footer_row + int(horizontal)):
            return y + footer_rows_offset
        else:
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
        pos_y1 = row_positions[y] - half_max_width(horizontal_borders, [
            (y, x - 1), (y, x)], vertical=False)
        pos_y2 = row_positions[y + 1] + half_max_width(horizontal_borders, [
            (y + 1, x - 1), (y + 1, x)], vertical=False)
        segments.append((
            score, style, width, color, 'left',
            (pos_x - width / 2, pos_y1, 0, pos_y2 - pos_y1)))

    def add_horizontal(x, y):
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
            (pos_x1, pos_y - width / 2, pos_x2 - pos_x1, 0)))

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
        if side == 'top':
            widths = (width, 0, 0, 0)
        else:
            widths = (0, 0, 0, width)
        with stacked(context):
            clip_border_segment(
                context, style, width, side, border_box, widths)
            draw_rect_border(
                context, border_box, widths, style,
                styled_color(style, color, side))


def draw_replacedbox(context, box):
    """Draw the given :class:`boxes.ReplacedBox` to a ``document.Context``."""
    if box.style['visibility'] != 'visible' or not box.width or not box.height:
        return

    draw_width, draw_height, draw_x, draw_y = replaced.replacedbox_layout(box)

    with stacked(context):
        rounded_box_path(context, box.rounded_content_box())
        context.clip()
        context.end()
        context.transform(1, 0, 0, 1, draw_x, draw_y)
        box.replacement.draw(
            context, draw_width, draw_height, box.style['image_rendering'])


def draw_inline_level(context, page, box, offset_x=0, text_overflow='clip'):
    if isinstance(box, StackingContext):
        stacking_context = box
        assert isinstance(
            stacking_context.box, (boxes.InlineBlockBox, boxes.InlineFlexBox))
        draw_stacking_context(context, stacking_context)
    else:
        draw_background(context, box.background)
        draw_border(context, box)
        if isinstance(box, (boxes.InlineBox, boxes.LineBox)):
            if isinstance(box, boxes.LineBox):
                text_overflow = box.text_overflow
            for child in box.children:
                if isinstance(child, StackingContext):
                    child_offset_x = offset_x
                else:
                    child_offset_x = (
                        offset_x + child.position_x - box.position_x)
                if isinstance(child, boxes.TextBox):
                    draw_text(context, child, child_offset_x, text_overflow)
                else:
                    draw_inline_level(
                        context, page, child, child_offset_x, text_overflow)
        elif isinstance(box, boxes.InlineReplacedBox):
            draw_replacedbox(context, box)
        else:
            assert isinstance(box, boxes.TextBox)
            # Should only happen for list markers
            draw_text(context, box, offset_x, text_overflow)


def draw_text(context, textbox, offset_x, text_overflow):
    """Draw ``textbox`` to a ``cairo.Context`` from ``PangoCairo.Context``."""
    # Pango crashes with font-size: 0
    assert textbox.style['font_size']

    if textbox.style['visibility'] != 'visible':
        return

    x, y = textbox.position_x, textbox.position_y + textbox.baseline
    context.move_to(x, y)
    context.set_color_rgb(*textbox.style['color'][:3])
    context.set_alpha(textbox.style['color'][3])

    textbox.pango_layout.reactivate(textbox.style)
    show_first_line(context, textbox, text_overflow, x, y)

    values = textbox.style['text_decoration_line']

    thickness = textbox.style['font_size'] / 18  # Like other browsers do

    color = textbox.style['text_decoration_color']
    if color == 'currentColor':
        color = textbox.style['color']

    if ('overline' in values or
            'line-through' in values or
            'underline' in values):
        metrics = textbox.pango_layout.get_font_metrics()
    if 'overline' in values:
        draw_text_decoration(
            context, textbox, offset_x,
            textbox.baseline - metrics.ascent + thickness / 2,
            thickness, color)
    if 'underline' in values:
        draw_text_decoration(
            context, textbox, offset_x,
            textbox.baseline - metrics.underline_position + thickness / 2,
            thickness, color)
    if 'line-through' in values:
        draw_text_decoration(
            context, textbox, offset_x,
            textbox.baseline - metrics.strikethrough_position,
            thickness, color)

    textbox.pango_layout.deactivate()


def draw_wave(context, x, y, width, offset_x, radius):
    up = 1
    max_x = x + width

    context.rectangle(x, y - 2 * radius, width, 4 * radius)
    context.clip()
    context.end()

    print(x, offset_x, radius)
    x -= offset_x
    context.move_to(x, y)

    while x < max_x:
        context.curve_to(
            x + radius / 2, y + up * radius,
            x + 3 * radius / 2, y + up * radius,
            x + 2 * radius, y)
        x += 2 * radius
        up *= -1


def draw_text_decoration(context, textbox, offset_x, offset_y, thickness,
                         color):
    """Draw text-decoration of ``textbox`` to a ``document.Context``."""
    style = textbox.style['text_decoration_style']
    with stacked(context):
        context.set_color_rgb(*color[:3], stroke=True)
        context.set_alpha(color[3], stroke=True)

        if style == 'dashed':
            context.set_dash([5 * thickness], offset_x)
        elif style == 'dotted':
            context.set_dash([thickness], offset_x)

        if style == 'wavy':
            thickness *= 0.75
            draw_wave(
                context,
                textbox.position_x, textbox.position_y + offset_y,
                textbox.width, offset_x, thickness)
        else:
            context.move_to(textbox.position_x, textbox.position_y + offset_y)
            context.line_to(
                textbox.position_x + textbox.width,
                textbox.position_y + offset_y)

        context.set_line_width(thickness)

        if style == 'double':
            delta = 2 * thickness
            context.move_to(
                textbox.position_x, textbox.position_y + offset_y + delta)
            context.line_to(
                textbox.position_x + textbox.width,
                textbox.position_y + offset_y + delta)

        context.stroke()
