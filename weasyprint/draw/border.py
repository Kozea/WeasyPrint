"""Draw borders."""

from math import ceil, floor, pi, sqrt, tan

from ..formatting_structure import boxes
from ..layout import replaced
from ..layout.percent import percentage
from ..matrix import Matrix
from .color import get_color, styled_color
from .stack import stacked

SIDES = ('top', 'right', 'bottom', 'left')


def set_mask_border(stream, box):
    """Set ``box`` mask border as alpha state on ``stream``."""
    if box.style['mask_border_source'][0] == 'none' or box.mask_border_image is None:
        return
    x, y, w, h, tl, tr, br, bl = box.rounded_border_box()
    matrix = Matrix(e=x, f=y)
    matrix @= stream.ctm
    mask_stream = stream.set_alpha_state(x, y, w, h, box.style['mask_border_mode'])
    draw_border_image(
        box, mask_stream, box.mask_border_image, box.style['mask_border_slice'],
        box.style['mask_border_repeat'], box.style['mask_border_outset'],
        box.style['mask_border_width'])


def draw_border(stream, box):
    """Draw the box borders and column rules to a ``pdf.stream.Stream``."""

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
                rule_width = box.style['column_rule_width']
                rule_style = box.style['column_rule_style']
                if box.style['column_gap'] == 'normal':
                    gap = box.style['font_size']  # normal equals 1em
                else:
                    gap = percentage(box.style['column_gap'], box.width)
                position_x = (
                    child.position_x - (box.style['column_rule_width'] + gap) / 2)
                border_box = (position_x, child.position_y, rule_width, child.height)
                clip_border_segment(
                    stream, rule_style, rule_width, 'left', border_box, border_widths)
                color = styled_color(
                    rule_style, get_color(box.style, 'column_rule_color'), 'left')
                draw_rect_border(stream, border_box, border_widths, rule_style, color)

    # If there's a border image, that takes precedence.
    if box.style['border_image_source'][0] != 'none' and box.border_image is not None:
        draw_border_image(
            box, stream, box.border_image, box.style['border_image_slice'],
            box.style['border_image_repeat'], box.style['border_image_outset'],
            box.style['border_image_width'])
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


def draw_border_image(box, stream, image, border_slice, border_repeat, border_outset,
                      border_width):
    """Draw ``image`` as a border image for ``box`` on ``stream`` as specified."""
    # Shared by border-image-* and mask-border-*.
    width, height, ratio = image.get_intrinsic_size(
        box.style['image_resolution'], box.style['font_size'])
    intrinsic_width, intrinsic_height = replaced.default_image_sizing(
        width, height, ratio, specified_width=None, specified_height=None,
        default_width=box.border_width(), default_height=box.border_height())

    image_slice = border_slice[:4]
    should_fill = border_slice[4]

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

    repeat_x, repeat_y = border_repeat

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

    outset_top = compute_outset_dimension(border_outset[0], border_top)
    outset_right = compute_outset_dimension(border_outset[1], border_right)
    outset_bottom = compute_outset_dimension(border_outset[2], border_bottom)
    outset_left = compute_outset_dimension(border_outset[3], border_left)

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
    border_top = compute_width_adjustment(
        border_width[0], border_top, slice_top, h)
    border_right = compute_width_adjustment(
        border_width[1], border_right, slice_right, w)
    border_bottom = compute_width_adjustment(
        border_width[2], border_bottom, slice_bottom, h)
    border_left = compute_width_adjustment(
        border_width[3], border_left, slice_left, w)

    def draw_border_image_region(x, y, width, height, slice_x, slice_y, slice_width,
                                 slice_height, repeat_x='stretch', repeat_y='stretch',
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
    scale_left, scale_top = draw_border_image_region(
        x, y, border_left, border_top, 0, 0, slice_left, slice_top)
    # Top right.
    draw_border_image_region(
        x + w - border_right, y, border_right, border_top,
        intrinsic_width - slice_right, 0, slice_right, slice_top)
    # Bottom right.
    scale_right, scale_bottom = draw_border_image_region(
        x + w - border_right, y + h - border_bottom, border_right, border_bottom,
        intrinsic_width - slice_right, intrinsic_height - slice_bottom,
        slice_right, slice_bottom)
    # Bottom left.
    draw_border_image_region(
        x, y + h - border_bottom, border_left, border_bottom,
        0, intrinsic_height - slice_bottom, slice_left, slice_bottom)
    if x_middle := slice_left + slice_right < intrinsic_width:
        # Top middle.
        draw_border_image_region(
            x + border_left, y, w - border_left - border_right, border_top,
            slice_left, 0, intrinsic_width - slice_left - slice_right,
            slice_top, repeat_x=repeat_x)
        # Bottom middle.
        draw_border_image_region(
            x + border_left, y + h - border_bottom,
            w - border_left - border_right, border_bottom,
            slice_left, intrinsic_height - slice_bottom,
            intrinsic_width - slice_left - slice_right, slice_bottom,
            repeat_x=repeat_x)
    if y_middle := slice_top + slice_bottom < intrinsic_height:
        # Right middle.
        draw_border_image_region(
            x + w - border_right, y + border_top,
            border_right, h - border_top - border_bottom,
            intrinsic_width - slice_right, slice_top,
            slice_right, intrinsic_height - slice_top - slice_bottom,
            repeat_y=repeat_y)
        # Left middle.
        draw_border_image_region(
            x, y + border_top, border_left, h - border_top - border_bottom,
            0, slice_top, slice_left,
            intrinsic_height - slice_top - slice_bottom,
            repeat_y=repeat_y)
    if should_fill and x_middle and y_middle:
        # Fill middle.
        draw_border_image_region(
            x + border_left, y + border_top, w - border_left - border_right,
            h - border_top - border_bottom, slice_left, slice_top,
            intrinsic_width - slice_left - slice_right,
            intrinsic_height - slice_top - slice_bottom,
            repeat_x=repeat_x, repeat_y=repeat_y,
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
        stream.set_color(color[0])
        rounded_box(stream, box.rounded_padding_box())
        rounded_box(stream, box.rounded_box_ratio(1 / 2))
        stream.fill(even_odd=True)
        stream.set_color(color[1])
        rounded_box(stream, box.rounded_box_ratio(1 / 2))
        rounded_box(stream, box.rounded_border_box())
        stream.fill(even_odd=True)
        return
    stream.set_color(color)
    rounded_box(stream, box.rounded_padding_box())
    if style == 'double':
        rounded_box(stream, box.rounded_box_ratio(1 / 3))
        rounded_box(stream, box.rounded_box_ratio(2 / 3))
    rounded_box(stream, box.rounded_border_box())
    stream.fill(even_odd=True)


def draw_rect_border(stream, box, widths, style, color):
    bbx, bby, bbw, bbh = box
    bt, br, bb, bl = widths
    if style in ('ridge', 'groove'):
        stream.set_color(color[0])
        stream.rectangle(*box)
        stream.rectangle(
            bbx + bl / 2, bby + bt / 2,
            bbw - (bl + br) / 2, bbh - (bt + bb) / 2)
        stream.fill(even_odd=True)
        stream.rectangle(
            bbx + bl / 2, bby + bt / 2,
            bbw - (bl + br) / 2, bbh - (bt + bb) / 2)
        stream.rectangle(bbx + bl, bby + bt, bbw - bl - br, bbh - bt - bb)
        stream.set_color(color[1])
        stream.fill(even_odd=True)
        return
    stream.set_color(color)
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
            stream.set_color(color, stroke=True)

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
            stream.set_color(color[0], stroke=True)
            if x1 == x2:
                stream.move_to(x1 + thickness / 4, y1)
                stream.line_to(x2 + thickness / 4, y2)
            elif y1 == y2:
                stream.move_to(x1, y1 + thickness / 4)
                stream.line_to(x2, y2 + thickness / 4)
            stream.stroke()
            stream.set_color(color[1], stroke=True)
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
                stream.set_line_width(thickness)
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


def draw_outline(stream, box):
    width = box.style['outline_width']
    offset = box.style['outline_offset']
    color = get_color(box.style, 'outline_color')
    style = box.style['outline_style']
    if box.style['visibility'] == 'visible' and width and color.alpha:
        outline_box = (
            box.border_box_x() - width - offset,
            box.border_box_y() - width - offset,
            box.border_width() + 2 * width + 2 * offset,
            box.border_height() + 2 * width + 2 * offset)
        for side in SIDES:
            with stacked(stream):
                clip_border_segment(stream, style, width, side, outline_box)
                draw_rect_border(
                    stream, outline_box, 4 * (width,), style,
                    styled_color(style, color, side))

    for child in box.children:
        if isinstance(child, boxes.Box):
            draw_outline(stream, child)


def rounded_box(stream, radii):
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
