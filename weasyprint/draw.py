# coding: utf8
"""
    weasyprint.draw
    ---------------

    Take an "after layout" box tree and draw it onto a cairo context.

    :copyright: Copyright 2011-2013 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import contextlib
import math
import operator

import cairocffi as cairo

from .formatting_structure import boxes
from .stacking import StackingContext
from .text import show_first_line
from .compat import xrange


ARC_TO_BEZIER = 4 * (2 ** .5 - 1) / 3
SIDES = ('top', 'right', 'bottom', 'left')


@contextlib.contextmanager
def stacked(context):
    """Save and restore the context when used with the ``with`` keyword."""
    context.save()
    try:
        yield
    finally:
        context.restore()


def lighten(color, offset):
    """Return a lighter color (or darker, for negative offsets)."""
    return (
        color.red + offset,
        color.green + offset,
        color.blue + offset,
        color.alpha)


def draw_page(page, context, enable_hinting):
    """Draw the given PageBox."""
    stacking_context = StackingContext.from_page(page)
    draw_background(
        context, stacking_context.box.background, enable_hinting,
        clip_box=False)
    draw_background(
        context, page.canvas_background, enable_hinting, clip_box=False)
    draw_border(context, page, enable_hinting)
    draw_stacking_context(context, stacking_context, enable_hinting)


def draw_box_background_and_border(context, page, box, enable_hinting):
    draw_background(context, box.background, enable_hinting)
    if not isinstance(box, boxes.TableBox):
        draw_border(context, box, enable_hinting)
    else:
        for column_group in box.column_groups:
            draw_background(context, column_group.background, enable_hinting)
            for column in column_group.children:
                draw_background(context, column.background, enable_hinting)
        for row_group in box.children:
            draw_background(context, row_group.background, enable_hinting)
            for row in row_group.children:
                draw_background(context, row.background, enable_hinting)
                for cell in row.children:
                    draw_background(context, cell.background, enable_hinting)
        if box.style.border_collapse == 'separate':
            draw_border(context, box, enable_hinting)
            for row_group in box.children:
                for row in row_group.children:
                    for cell in row.children:
                        draw_border(context, cell, enable_hinting)
        else:
            draw_collapsed_borders(context, box, enable_hinting)


def draw_stacking_context(context, stacking_context, enable_hinting):
    """Draw a ``stacking_context`` on ``context``."""
    # See http://www.w3.org/TR/CSS2/zindex.html
    with stacked(context):
        box = stacking_context.box
        if box.is_absolutely_positioned() and box.style.clip:
            top, right, bottom, left = box.style.clip
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

        if box.style.opacity < 1:
            context.push_group()

        if box.transformation_matrix:
            context.transform(box.transformation_matrix)

        # Point 1 is done in draw_page

        # Point 2
        if isinstance(box, (boxes.BlockBox, boxes.MarginBox,
                            boxes.InlineBlockBox)):
            # The canvas background was removed by set_canvas_background
            draw_box_background_and_border(
                context, stacking_context.page, box, enable_hinting)

        with stacked(context):
            if box.style.overflow != 'visible':
                # Only clip the content and the children:
                # - the background is already clipped
                # - the border must *not* be clipped
                rounded_box_path(context, box.rounded_padding_box())
                context.clip()

            # Point 3
            for child_context in stacking_context.negative_z_contexts:
                draw_stacking_context(context, child_context, enable_hinting)

            # Point 4
            for block in stacking_context.block_level_boxes:
                draw_box_background_and_border(
                    context, stacking_context.page, block, enable_hinting)

            # Point 5
            for child_context in stacking_context.float_contexts:
                draw_stacking_context(context, child_context, enable_hinting)

            # Point 6
            if isinstance(box, boxes.InlineBox):
                draw_inline_level(
                    context, stacking_context.page, box, enable_hinting)

            # Point 7
            for block in [box] + stacking_context.blocks_and_cells:
                marker_box = getattr(block, 'outside_list_marker', None)
                if marker_box:
                    draw_inline_level(
                        context, stacking_context.page, marker_box,
                        enable_hinting)

                if isinstance(block, boxes.ReplacedBox):
                    draw_replacedbox(context, block)
                else:
                    for child in block.children:
                        if isinstance(child, boxes.LineBox):
                            # TODO: draw inline tables
                            draw_inline_level(
                                context, stacking_context.page, child,
                                enable_hinting)

            # Point 8
            for child_context in stacking_context.zero_z_contexts:
                draw_stacking_context(context, child_context, enable_hinting)

            # Point 9
            for child_context in stacking_context.positive_z_contexts:
                draw_stacking_context(context, child_context, enable_hinting)

        # Point 10
        draw_outlines(context, box, enable_hinting)

        if box.style.opacity < 1:
            context.pop_group_to_source()
            context.paint_with_alpha(box.style.opacity)


def rounded_box_path(context, radii):
    """Draw the path of the border radius box.

    ``widths`` is a tuple of the inner widths (top, right, bottom, left) from
    the border box. Radii are adjusted from these values. Default is (0, 0, 0,
    0).

    Inspired by Cairo Cookbook
    http://cairographics.org/cookbook/roundedrectangles/

    """
    x, y, w, h, tl, tr, br, bl = radii

    if 0 in tl:
        tl = (0, 0)
    if 0 in tr:
        tr = (0, 0)
    if 0 in br:
        br = (0, 0)
    if 0 in bl:
        bl = (0, 0)

    if (tl, tr, br, bl) == 4 * ((0, 0),):
        # No radius, draw a rectangle
        context.rectangle(x, y, w, h)
        return

    (tlh, tlv), (trh, trv), (brh, brv), (blh, blv) = tl, tr, br, bl

    context.move_to(x + tlh, y)
    context.rel_line_to(w - tlh - trh, 0)
    context.rel_curve_to(
        ARC_TO_BEZIER * trh, 0, trh, ARC_TO_BEZIER * trv, trh, trv)
    context.rel_line_to(0, h - trv - brv)
    context.rel_curve_to(
        0, ARC_TO_BEZIER * brv, -ARC_TO_BEZIER * brh, brv, -brh, brv)
    context.rel_line_to(-w + blh + brh, 0)
    context.rel_curve_to(
        -ARC_TO_BEZIER * blh, 0, -blh, -ARC_TO_BEZIER * blv, -blh, -blv)
    context.rel_line_to(0, -h + tlv + blv)
    context.rel_curve_to(
        0, -ARC_TO_BEZIER * tlv, ARC_TO_BEZIER * tlh, -tlv, tlh, -tlv)


def draw_background(context, bg, enable_hinting, clip_box=True):
    """Draw the background color and image to a ``cairo.Context``.

    If ``clip_box`` is set to ``False``, the background is not clipped to the
    border box of the background, but only to the painting area.

    """
    if bg is None:
        return

    with stacked(context):
        if enable_hinting:
            # Prefer crisp edges on background rectangles.
            context.set_antialias(cairo.ANTIALIAS_NONE)

        if clip_box:
            rounded_box_path(context, bg.layers[-1].rounded_box)
            context.clip()

        # Background color
        if bg.color.alpha > 0:
            with stacked(context):
                painting_area = bg.layers[-1].painting_area
                if painting_area:
                    context.rectangle(*painting_area)
                    context.clip()
                context.set_source_rgba(*bg.color)
                context.paint()

        # Paint in reversed order: first layer is "closest" to the viewer.
        for layer in reversed(bg.layers):
            draw_background_image(context, layer, bg.image_rendering)


def draw_background_image(context, layer, image_rendering):
    # Background image
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
        repeat_width = painting_width * 2
    elif repeat_x in ('repeat', 'round'):
        repeat_width = image_width
    else:
        assert repeat_x == 'space'
        n_repeats = math.floor(positioning_width / image_width)
        if n_repeats >= 2:
            repeat_width = (positioning_width - image_width) / (n_repeats - 1)
            position_x = 0  # Ignore background-position for this dimension
        else:
            repeat_width = image_width

    if repeat_y == 'no-repeat':
        repeat_height = painting_height * 2
    elif repeat_y in ('repeat', 'round'):
        repeat_height = image_height
    else:
        assert repeat_y == 'space'
        n_repeats = math.floor(positioning_height / image_height)
        if n_repeats >= 2:
            repeat_height = (
                positioning_height - image_height) / (n_repeats - 1)
            position_y = 0  # Ignore background-position for this dimension
        else:
            repeat_height = image_height

    sub_surface = cairo.PDFSurface(None, repeat_width, repeat_height)
    sub_context = cairo.Context(sub_surface)
    sub_context.rectangle(0, 0, image_width, image_height)
    sub_context.clip()
    layer.image.draw(sub_context, image_width, image_height, image_rendering)
    pattern = cairo.SurfacePattern(sub_surface)
    pattern.set_extend(cairo.EXTEND_REPEAT)

    with stacked(context):
        if not layer.unbounded:
            context.rectangle(painting_x, painting_y,
                              painting_width, painting_height)
            context.clip()
        #else: unrestricted, whole page box

        context.translate(positioning_x + position_x,
                          positioning_y + position_y)
        context.set_source(pattern)
        context.paint()


def xy_offset(x, y, offset_x, offset_y, offset):
    """Increment X and Y coordinates by the given offsets."""
    return x + offset_x * offset, y + offset_y * offset


def styled_color(style, color, side):
    if style in ('inset', 'outset'):
        do_lighten = (side in ('top', 'left')) ^ (style == 'inset')
        factor = 0.5 if do_lighten else -0.5
        return lighten(color, factor)
    elif style in ('ridge', 'groove'):
        do_lighten = (side in ('top', 'left')) ^ (style == 'ridge')
        factor = 0.5 if do_lighten else -0.5
        return lighten(color, factor), lighten(color, -factor)
    return color


def draw_border(context, box, enable_hinting):
    """Draw the box border to a ``cairo.Context``."""
    # We need a plan to draw beautiful borders, and that's difficult, no need
    # to lie. Let's try to find the cases that we can handle in a smart way.

    # The box is hidden, easy.
    if box.style.visibility == 'hidden':
        return

    widths = [getattr(box, 'border_%s_width' % side) for side in SIDES]

    # No border, return early.
    if all(width == 0 for width in widths):
        return

    colors = [box.style.get_color('border_%s_color' % side) for side in SIDES]
    styles = [
        colors[i].alpha and box.style['border_%s_style' % side]
        for (i, side) in enumerate(SIDES)]

    # The 4 sides are solid or double, and they have the same color. Oh yeah!
    # We can draw them so easily!
    if set(styles) in ({'solid'}, {'double'}) and len(set(colors)) == 1:
        draw_rounded_border(context, box, styles[0], colors[0])
        return

    # We're not smart enough to find a good way to draw the borders :/. We must
    # draw them side by side.
    for side, width, color, style in zip(SIDES, widths, colors, styles):
        if width == 0 or not color:
            continue
        with stacked(context):
            clip_border_segment(
                context, enable_hinting, style, width, side,
                box.rounded_border_box()[:4], widths,
                box.rounded_border_box()[4:])
            draw_rounded_border(
                context, box, style, styled_color(style, color, side))


def clip_border_segment(context, enable_hinting, style, width, side,
                        border_box, border_widths=None, radii=None):
    """Clip one segment of box border.

    The strategy is to remove the zones not needed because of the style or the
    side before painting.

    """
    if enable_hinting and style != 'dotted' and (
            # Borders smaller than 1 device unit would disappear
            # without anti-aliasing.
            math.hypot(*context.user_to_device(width, 0)) >= 1 and
            math.hypot(*context.user_to_device(0, width)) >= 1):
        # Avoid an artifact in the corner joining two solid borders
        # of the same color.
        context.set_antialias(cairo.ANTIALIAS_NONE)

    bbx, bby, bbw, bbh = border_box
    (tlh, tlv), (trh, trv), (brh, brv), (blh, blv) = radii or 4 * ((0, 0),)
    bt, br, bb, bl = border_widths or 4 * (width,)

    def transition_points(x1, y1, x2, y2):
        #TODO: Update doc
        """Get the point use for border transition.

        The extra boolean returned is ``True`` if the point is in the padding
        box (ie. the padding box is rounded).

        This point is not specified. We must be sure to be inside the rounded
        padding box, and in the zone defined in the "transition zone" allowed
        by the specification. We chose the corner of the transition zone. It's
        easy to get and gives quite good results, but it seems to be different
        from what other browsers do.

        """
        if abs(x1) > abs(x2) and abs(y1) > abs(y2):
            px, py = x1, y1
            rounded = True
        else:
            px, py = x2, y2
            rounded = False
        if rounded:
            tx = ty = min(abs(px), abs(py))
            tx *= -1 if px < 0 else 1
            ty *= -1 if py < 0 else 1
        else:
            tx, ty = px, py
        return (px, py), (tx, ty), rounded

    def corner_half_length(a, b):
        """Return the length of the half of one ellipsis corner.

        Inspired by [Ramanujan, S., "Modular Equations and Approximations to
        pi" Quart. J. Pure. Appl. Math., vol. 45 (1913-1914), pp. 350-372],
        wonderfully explained by Dr Rob.

        http://mathforum.org/dr.math/faq/formulas/faq.ellipse.circumference.html

        """
        x = (a - b) / (a + b)
        return math.pi / 8 * (a + b) * (
            1 + 3 * x ** 2 / (10 + math.sqrt(4 - 3 * x ** 2)))

    if side == 'top':
        context.move_to(bbx + bbw, bby)
        context.rel_line_to(-bbw, 0)
        (px1, py1), (tx1, ty1), rounded1 = transition_points(tlh, tlv, bl, bt)
        (px2, py2), (tx2, ty2), rounded2 = transition_points(-trh, trv, -br, bt)
        context.rel_line_to(tx1, ty1)
        context.rel_line_to(-tx1 + bbw + tx2, -ty1 + ty2)
        length = bbw
        width = bt
        way = 1
        angle = 1
        main_offset = bby
    elif side == 'right':
        context.move_to(bbx + bbw, bby + bbh)
        context.rel_line_to(0, -bbh)
        (px1, py1), (tx1, ty1), rounded1 = transition_points(-trh, trv, -br, bt)
        (px2, py2), (tx2, ty2), rounded2 = transition_points(-brh, -brv, -br, -bb)
        context.rel_line_to(tx1, ty1)
        context.rel_line_to(-tx1 + tx2, -ty1 + bbh + ty2)
        length = bbh
        width = br
        way = 1
        angle = 2
        main_offset = bbx + bbw
    elif side == 'bottom':
        context.move_to(bbx + bbw, bby + bbh)
        context.rel_line_to(-bbw, 0)
        (px1, py1), (tx1, ty1), rounded1 = transition_points(blh, -blv, bl, -bb)
        (px2, py2), (tx2, ty2), rounded2 = transition_points(-brh, -brv, -br, -bb)
        context.rel_line_to(tx1, ty1)
        context.rel_line_to(-tx1 + bbw + tx2, -ty1 + ty2)
        length = bbw
        width = bb
        way = -1
        angle = 3
        main_offset = bby + bbh
    elif side == 'left':
        context.move_to(bbx, bby + bbh)
        context.rel_line_to(0, -bbh)
        (px1, py1), (tx1, ty1), rounded1 = transition_points(tlh, tlv, bl, bt)
        (px2, py2), (tx2, ty2), rounded2 = transition_points(blh, -blv, bl, -bb)
        context.rel_line_to(tx1, ty1)
        context.rel_line_to(-tx1 + tx2, -ty1 + bbh + ty2)
        length = bbh
        width = bl
        way = -1
        angle = 4
        main_offset = bbx
    context.close_path()

    context.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    if style in ('dotted', 'dashed'):
        dash = width if style == 'dotted' else 3 * width
        if rounded1 or rounded2:
            # At least one of the two corners is rounded
            if side in ('top', 'bottom'):
                a1, b1 = px1 - bl / 2, way * py1 - width / 2
                a2, b2 = -px2 - br / 2, way * py2 - width / 2
                line_length = bbw - px1 + px2
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
                dashes1 = int(math.ceil((chl1 - dash / 2) / dash))
                dashes2 = int(math.ceil((chl2 - dash / 2) / dash))
                line = int(math.floor(line_length / dash))

                if dashes1:
                    for i in range(0, dashes1, 2):
                        i += 0.5  # half dash
                        angle1 = (
                            ((2 * angle - way) + i * way * dash / chl1)
                            / 4 * math.pi)
                        angle2 = (min if way > 0 else max)(
                            ((2 * angle - way) + (i + 1) * way * dash / chl1)
                            / 4 * math.pi,
                            angle * math.pi / 2)
                        if a1 >= b1:
                            c1 = math.sqrt(a1 ** 2 - b1 ** 2)
                            x1 = px1 - (dashes1 - i) / dashes1 * c1 / 2
                            x2 = (
                                px1 - (dashes1 - min(i + 1, dashes1)) /
                                dashes1 * c1 / 2)
                            context.move_to(bbx + x1, main_offset + py1)
                            context.line_to(bbx + x2, main_offset + py1)
                            context.line_to(
                                bbx + x2 -
                                a1 * math.sqrt(2) * math.cos(angle2),
                                main_offset + py1 -
                                a1 * math.sqrt(2) * math.sin(angle2))
                            context.line_to(
                                bbx + x1 -
                                a1 * math.sqrt(2) * math.cos(angle1),
                                main_offset + py1 -
                                a1 * math.sqrt(2) * math.sin(angle1))
                            context.close_path()
                        else:
                            c1 = math.sqrt(b1 ** 2 - a1 ** 2)
                            y1 = c1 - i / dashes1 * c1 / 2
                            y2 = (
                                c1 - min(i + 1, dashes1) /
                                dashes1 * c1 / 2)
                            context.move_to(bbx + px1, main_offset + y1)
                            context.line_to(bbx + px1, main_offset + y2)
                            context.line_to(
                                bbx + px1 -
                                b1 * math.sqrt(2) * math.cos(angle2),
                                main_offset + y2 -
                                b1 * math.sqrt(2) * math.sin(angle2))
                            context.line_to(
                                bbx + px1 -
                                b1 * math.sqrt(2) * math.cos(angle1),
                                main_offset + y1 -
                                b1 * math.sqrt(2) * math.sin(angle1))
                            context.close_path()
                        if angle2 == angle * math.pi / 2:
                            offset = way * (angle2 - angle1) / ((
                                ((2 * angle - way) + (i + 1) * way * dash / chl1)
                                / 4 * math.pi) - angle1)
                            line += 1
                            break
                    else:
                        offset = 1 - (
                            (angle * math.pi / 2 - angle2) / (angle2 - angle1))
                else:
                    offset = 0

                if dashes2:
                    for i in range(0, dashes2, 2):
                        i += 0.5  # half dash
                        angle1 = (
                            ((2 * angle + way) - (way * i * dash / chl2))
                            / 4 * math.pi)
                        angle2 = (min if way < 0 else max)(
                            ((2 * angle + way) - (way * (i + 1) * dash / chl2))
                            / 4 * math.pi,
                            angle * math.pi / 2)
                        if a2 >= b2:
                            c2 = math.sqrt(a2 ** 2 - b2 ** 2)
                            x1 = bbw + px2 + c2 / 2 - i / dashes2 * c2 / 2
                            x2 = (
                                bbw + px2 + c2 / 2 - min(i + 1, dashes2) /
                                dashes2 * c2 / 2)
                            context.move_to(bbx + x1, main_offset + py2)
                            context.line_to(bbx + x2, main_offset + py2)
                            context.line_to(
                                bbx + x2 -
                                a2 * math.sqrt(2) * math.cos(angle2),
                                main_offset + py2 -
                                a2 * math.sqrt(2) * math.sin(angle2))
                            context.line_to(
                                bbx + x1 -
                                a2 * math.sqrt(2) * math.cos(angle1),
                                main_offset + py2 -
                                a2 * math.sqrt(2) * math.sin(angle1))
                            context.close_path()
                        else:
                            c2 = math.sqrt(b2 ** 2 - a2 ** 2)
                            y1 = c2 - i / dashes2 * c2 / 2
                            y2 = (
                                c2 - min(i + 1, dashes2) /
                                dashes2 * c2 / 2)
                            context.move_to(bbx + bbw + px2, main_offset + y1)
                            context.line_to(bbx + bbw + px2, main_offset + y2)
                            context.line_to(
                                bbx + bbw + px2 -
                                b2 * math.sqrt(2) * math.cos(angle2),
                                main_offset + y2 -
                                b2 * math.sqrt(2) * math.sin(angle2))
                            context.line_to(
                                bbx + bbw + px2 -
                                b2 * math.sqrt(2) * math.cos(angle1),
                                main_offset + y1 -
                                b2 * math.sqrt(2) * math.sin(angle1))
                            context.close_path()
                        if angle2 == angle * math.pi / 2:
                            line += 1
                            break

                for i in range(0, line, 2):
                    i += offset
                    x1 = max(bbx + px1 + i * dash, bbx + px1)
                    x2 = min(bbx + px1 + (i + 1) * dash, bbx + bbw + px2)
                    y1 = main_offset - (width if way < 0 else 0)
                    y2 = y1 + width
                    context.rectangle(x1, y1, x2 - x1, y2 - y1)

            elif side in ('left', 'right'):
                a1, b1 = -way * px1 - width / 2, py1 - bt / 2
                a2, b2 = -way * px2 - width / 2, -py2 - bb / 2
                line_length = bbh - py1 + py2
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
                dashes1 = int(math.ceil((chl1 - dash / 2) / dash))
                dashes2 = int(math.ceil((chl2 - dash / 2) / dash))
                line = int(math.floor(line_length / dash))

                if dashes1:
                    for i in range(0, dashes1, 2):
                        i += 0.5  # half dash
                        angle1 = (
                            ((2 * angle - way) + i * way * dash / chl1)
                            / 4 * math.pi)
                        angle2 = (min if way > 0 else max)(
                            ((2 * angle - way) + (i + 1) * way * dash / chl1)
                            / 4 * math.pi,
                            angle * math.pi / 2)
                        if a1 >= b1:
                            c1 = math.sqrt(a1 ** 2 - b1 ** 2)
                            y1 = py1 - (dashes1 - i) / dashes1 * c1 / 2
                            y2 = (
                                py1 - (dashes1 - min(i + 1, dashes1)) /
                                dashes1 * c1 / 2)
                            context.move_to(main_offset + px1, bby + y1)
                            context.line_to(main_offset + px1, bby + y2)
                            context.line_to(
                                main_offset + px1 -
                                a1 * math.sqrt(2) * math.cos(angle2),
                                bby + y2 -
                                a1 * math.sqrt(2) * math.sin(angle2))
                            context.line_to(
                                main_offset + px1 -
                                a1 * math.sqrt(2) * math.cos(angle1),
                                bby + y1 -
                                a1 * math.sqrt(2) * math.sin(angle1))
                            context.close_path()
                        else:
                            c1 = math.sqrt(b1 ** 2 - a1 ** 2)
                            x1 = c1 - i / dashes1 * c1 / 2
                            x2 = (
                                c1 - min(i + 1, dashes1) /
                                dashes1 * c1 / 2)
                            context.move_to(main_offset + x1, bby + py1)
                            context.line_to(main_offset + x2, bby + py1)
                            context.line_to(
                                main_offset + x2 -
                                b1 * math.sqrt(2) * math.cos(angle2),
                                bby + py1 -
                                b1 * math.sqrt(2) * math.sin(angle2))
                            context.line_to(
                                main_offset + x1 -
                                b1 * math.sqrt(2) * math.cos(angle1),
                                bby + py1 -
                                b1 * math.sqrt(2) * math.sin(angle1))
                            context.close_path()
                        if angle2 == angle * math.pi / 2:
                            offset = way * (angle2 - angle1) / ((
                                ((2 * angle - way) + (i + 1) * way * dash / chl1)
                                / 4 * math.pi) - angle1)
                            line += 1
                            break
                    else:
                        offset = 1 - (
                            (angle * math.pi / 2 - angle2) / (angle2 - angle1))
                else:
                    offset = 0

                if dashes2:
                    for i in range(0, dashes2, 2):
                        i += 0.5  # half dash
                        angle1 = (
                            ((2 * angle + way) - (way * i * dash / chl2))
                            / 4 * math.pi)
                        angle2 = (min if way < 0 else max)(
                            ((2 * angle + way) - (way * (i + 1) * dash / chl2))
                            / 4 * math.pi,
                            angle * math.pi / 2)
                        if a2 >= b2:
                            c2 = math.sqrt(a2 ** 2 - b2 ** 2)
                            y1 = bbh + py2 + c2 / 2 - i / dashes2 * c2 / 2
                            y2 = (
                                bbh + py2 + c2 / 2 - min(i + 1, dashes2) /
                                dashes2 * c2 / 2)
                            context.move_to(main_offset + px2, bby + y1)
                            context.line_to(main_offset + px2, bby + y2)
                            context.line_to(
                                main_offset + px2 -
                                a2 * math.sqrt(2) * math.cos(angle2),
                                bby + y2 -
                                a2 * math.sqrt(2) * math.sin(angle2))
                            context.line_to(
                                main_offset + px2 -
                                a2 * math.sqrt(2) * math.cos(angle1),
                                bby + y1 -
                                a2 * math.sqrt(2) * math.sin(angle1))
                            context.close_path()
                        else:
                            c2 = math.sqrt(b2 ** 2 - a2 ** 2)
                            x1 = c2 - i / dashes2 * c2 / 2
                            x2 = (
                                c2 - min(i + 1, dashes2) /
                                dashes2 * c2 / 2)
                            context.move_to(main_offset + x1, bby + bbh + py2)
                            context.line_to(main_offset + x2, bby + bbh + py2)
                            context.line_to(
                                main_offset + x2 -
                                b2 * math.sqrt(2) * math.cos(angle2),
                                bby + bbh + py2 -
                                b2 * math.sqrt(2) * math.sin(angle2))
                            context.line_to(
                                main_offset + x1 -
                                b2 * math.sqrt(2) * math.cos(angle1),
                                bby + bbh + py2 -
                                b2 * math.sqrt(2) * math.sin(angle1))
                            context.close_path()
                        if angle2 == angle * math.pi / 2:
                            line += 1
                            break

                for i in range(0, line, 2):
                    i += offset
                    y1 = max(bby + py1 + i * dash, bby + py1)
                    y2 = min(bby + py1 + (i + 1) * dash, bby + bbh + py2)
                    x1 = main_offset - (width if way > 0 else 0)
                    x2 = x1 + width
                    context.rectangle(x1, y1, x2 - x1, y2 - y1)
        else:
            # 2x + 1 dashes
            dash = length / (
                round(length / dash) - (round(length / dash) + 1) % 2)
            for i in range(1, int(round(length / dash)), 2):
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
    context.clip()


def draw_rounded_border(context, box, style, color):
    context.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    rounded_box_path(context, box.rounded_padding_box())
    if style in ('ridge', 'groove'):
        rounded_box_path(context, box.rounded_box(1 / 2))
        context.set_source_rgba(*color[0])
        context.fill()
        rounded_box_path(context, box.rounded_box(1 / 2))
        rounded_box_path(context, box.rounded_border_box())
        context.set_source_rgba(*color[1])
        context.fill()
        return
    if style == 'double':
        rounded_box_path(context, box.rounded_box(1 / 3))
        rounded_box_path(context, box.rounded_box(2 / 3))
    rounded_box_path(context, box.rounded_border_box())
    context.set_source_rgba(*color)
    context.fill()


def draw_rect_border(context, box, widths, style, color):
    context.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    bbx, bby, bbw, bbh = box
    bt, br, bb, bl = widths
    context.rectangle(*box)
    if style in ('ridge', 'groove'):
        context.rectangle(
            bbx + bl / 2, bby + bt / 2,
            bbw - (bl + br) / 2, bbh - (bt + bb) / 2)
        context.set_source_rgba(*color[0])
        context.fill()
        context.rectangle(
            bbx + bl / 2, bby + bt / 2,
            bbw - (bl + br) / 2, bbh - (bt + bb) / 2)
        context.rectangle(
            bbx + bl, bby + bt, bbw - bl - br, bbh - bt - bb)
        context.set_source_rgba(*color[1])
        context.fill()
        return
    if style == 'double':
        context.rectangle(
            bbx + bl / 3, bby + bt / 3,
            bbw - (bl + br) / 3, bbh - (bt + bb) / 3)
        context.rectangle(
            bbx + bl * 2 / 3, bby + bt * 2 / 3,
            bbw - (bl + br) * 2 / 3, bbh - (bt + bb) * 2 / 3)
    context.rectangle(bbx + bl, bby + bt, bbw - bl - br, bbh - bt - bb)
    context.set_source_rgba(*color)
    context.fill()


def draw_outlines(context, box, enable_hinting):
    width = box.style.outline_width
    color = box.style.get_color('outline_color')
    style = box.style.outline_style
    if box.style.visibility != 'hidden' and width != 0 and color.alpha != 0:
        outline_box = (
            box.border_box_x() - width, box.border_box_y() - width,
            box.border_width() + 2 * width, box.border_height() + 2 * width)
        for side in SIDES:
            with stacked(context):
                clip_border_segment(
                    context, enable_hinting, style, width, side, outline_box)
                draw_rect_border(
                    context, outline_box, 4 * (width,), style,
                    styled_color(style, color, side))

    if isinstance(box, boxes.ParentBox):
        for child in box.children:
            if isinstance(child, boxes.Box):
                draw_outlines(context, child, enable_hinting)


def draw_collapsed_borders(context, table, enable_hinting):
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
    column_positions += [column_positions[-1] + column_widths[-1]]
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
        # TODO: change signs for rtl when we support rtl tables?
        pos_x1 = column_positions[x] - half_max_width(vertical_borders, [
            (y - 1, x), (y, x)])
        pos_x2 = column_positions[x + 1] + half_max_width(vertical_borders, [
            (y - 1, x + 1), (y, x + 1)])
        segments.append((
            score, style, width, color, 'top',
            (pos_x1, pos_y - width / 2, pos_x2 - pos_x1, 0)))

    for x in xrange(grid_width):
        add_horizontal(x, 0)
    for y in xrange(grid_height):
        add_vertical(0, y)
        for x in xrange(grid_width):
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
                context, enable_hinting, style, width, side, border_box,
                widths)
            draw_rect_border(
                context, border_box, widths, style,
                styled_color(style, color, side))


def draw_replacedbox(context, box):
    """Draw the given :class:`boxes.ReplacedBox` to a ``cairo.context``."""
    if box.style.visibility == 'hidden' or box.width == 0 or box.height == 0:
        return

    with stacked(context):
        context.translate(box.content_box_x(), box.content_box_y())
        context.rectangle(0, 0, box.width, box.height)
        context.clip()
        box.replacement.draw(
            context, box.width, box.height, box.style.image_rendering)


def draw_inline_level(context, page, box, enable_hinting):
    if isinstance(box, StackingContext):
        stacking_context = box
        assert isinstance(stacking_context.box, boxes.InlineBlockBox)
        draw_stacking_context(context, stacking_context, enable_hinting)
    else:
        draw_background(context, box.background, enable_hinting)
        draw_border(context, box, enable_hinting)
        if isinstance(box, (boxes.InlineBox, boxes.LineBox)):
            for child in box.children:
                if isinstance(child, boxes.TextBox):
                    draw_text(context, child, enable_hinting)
                else:
                    draw_inline_level(context, page, child, enable_hinting)
        elif isinstance(box, boxes.InlineReplacedBox):
            draw_replacedbox(context, box)
        else:
            assert isinstance(box, boxes.TextBox)
            # Should only happen for list markers
            draw_text(context, box, enable_hinting)


def draw_text(context, textbox, enable_hinting):
    """Draw ``textbox`` to a ``cairo.Context`` from ``PangoCairo.Context``."""
    # Pango crashes with font-size: 0
    assert textbox.style.font_size

    if textbox.style.visibility == 'hidden':
        return

    context.move_to(textbox.position_x, textbox.position_y + textbox.baseline)
    context.set_source_rgba(*textbox.style.color)
    show_first_line(context, textbox.pango_layout, enable_hinting)
    values = textbox.style.text_decoration

    metrics = textbox.pango_layout.get_font_metrics()
    thickness = textbox.style.font_size / 18  # That's what other browsers do
    if enable_hinting and thickness < 1:
        thickness = 1

    if 'overline' in values:
        draw_text_decoration(
            context, textbox,
            textbox.baseline - metrics.ascent + thickness / 2,
            thickness, enable_hinting)
    if 'underline' in values:
        draw_text_decoration(
            context, textbox,
            textbox.baseline - metrics.underline_position + thickness / 2,
            thickness, enable_hinting)
    if 'line-through' in values:
        draw_text_decoration(
            context, textbox,
            textbox.baseline - metrics.strikethrough_position,
            thickness, enable_hinting)


def draw_text_decoration(context, textbox, offset_y, thickness,
                         enable_hinting):
    """Draw text-decoration of ``textbox`` to a ``cairo.Context``."""
    with stacked(context):
        if enable_hinting:
            context.set_antialias(cairo.ANTIALIAS_NONE)
        context.set_source_rgba(*textbox.style.color)
        context.set_line_width(thickness)
        context.move_to(textbox.position_x, textbox.position_y + offset_y)
        context.rel_line_to(textbox.width, 0)
        context.stroke()
