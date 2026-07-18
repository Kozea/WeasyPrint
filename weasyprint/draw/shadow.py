"""Draw lossless CSS shadows."""

from .border import rounded_box


def _normalize_radii(width, height, corners):
    """Scale corner radii so opposing radii do not overlap."""
    top_left, top_right, bottom_right, bottom_left = corners
    ratio = min([1] + [
        extent / radii_sum
        for extent, radii_sum in (
            (width, top_left[0] + top_right[0]),
            (width, bottom_left[0] + bottom_right[0]),
            (height, top_left[1] + bottom_left[1]),
            (height, top_right[1] + bottom_right[1]),
        )
        if radii_sum > 0
    ])
    return tuple((x * ratio, y * ratio) for x, y in corners)


def _outset_radius(radius, spread, coverage):
    """Return one outset-adjusted radius dimension from CSS Backgrounds."""
    if spread <= 0:
        return max(0, radius + spread)
    if radius > spread or coverage > 1:
        return radius + spread
    ratio = radius / spread
    return radius + spread * (1 - (1 - ratio) ** 3 * (1 - coverage ** 3))


def _shadow_box(box, offset_x, offset_y, spread, inset):
    """Return the rounded perimeter casting an inner or outer shadow."""
    source = box.rounded_padding_box() if inset else box.rounded_border_box()
    x, y, width, height, *corners = source

    if inset:
        original_width, original_height = width, height
        x += offset_x + spread
        y += offset_y + spread
        width = max(0, width - 2 * spread)
        height = max(0, height - 2 * spread)
        if spread < 0:
            adjusted_corners = []
            for radius_x, radius_y in corners:
                coverage = 2 * min(
                    radius_x / original_width if original_width else 0,
                    radius_y / original_height if original_height else 0)
                adjusted_corners.append((
                    _outset_radius(radius_x, -spread, coverage),
                    _outset_radius(radius_y, -spread, coverage),
                ))
            corners = tuple(adjusted_corners)
        else:
            corners = tuple(
                (max(0, radius_x - spread), max(0, radius_y - spread))
                for radius_x, radius_y in corners)
    else:
        original_width, original_height = width, height
        x += offset_x - spread
        y += offset_y - spread
        width = max(0, width + 2 * spread)
        height = max(0, height + 2 * spread)
        adjusted_corners = []
        for radius_x, radius_y in corners:
            coverage = 2 * min(
                radius_x / original_width if original_width else 0,
                radius_y / original_height if original_height else 0)
            adjusted_corners.append((
                _outset_radius(radius_x, spread, coverage),
                _outset_radius(radius_y, spread, coverage),
            ))
        corners = tuple(adjusted_corners)

    corners = _normalize_radii(width, height, corners)
    return x, y, width, height, *corners


def _clip_outside_box(stream, box, painting_box):
    """Clip subsequent painting to the area outside ``box``."""
    x, y, width, height, *_ = box
    paint_x, paint_y, paint_width, paint_height, *_ = painting_box
    left = min(x, paint_x) - 1
    top = min(y, paint_y) - 1
    right = max(x + width, paint_x + paint_width) + 1
    bottom = max(y + height, paint_y + paint_height) + 1
    stream.rectangle(left, top, right - left, bottom - top)
    rounded_box(stream, box)
    stream.clip(even_odd=True)
    stream.end()


def draw_box_shadows(stream, box, inset):
    """Draw zero-blur inner or outer shadows in CSS painting order."""
    if box.style['visibility'] != 'visible':
        return

    source_box = box.rounded_padding_box() if inset else box.rounded_border_box()
    for offset_x, offset_y, blur, spread, shadow_inset, color in reversed(
            box.style['box_shadow']):
        assert blur == 0
        if shadow_inset != inset or color.alpha == 0:
            continue

        shadow_box = _shadow_box(box, offset_x, offset_y, spread, inset)
        with stream.artifact(), stream.stacked():
            stream.set_color(color)
            if inset:
                # Inner shadows are the shifted shadow perimeter's inverse,
                # clipped to the rounded padding edge. Use an outer rectangle
                # beyond the clip instead of repeating the padding path: two
                # coincident antialiased paths can otherwise leave a colored
                # seam on an edge that the shifted perimeter should clear.
                rounded_box(stream, source_box)
                stream.clip()
                stream.end()
                source_x, source_y, source_width, source_height, *_ = source_box
                shadow_x, shadow_y, shadow_width, shadow_height, *_ = shadow_box
                left = min(source_x, shadow_x) - 1
                top = min(source_y, shadow_y) - 1
                right = max(
                    source_x + source_width, shadow_x + shadow_width) + 1
                bottom = max(
                    source_y + source_height, shadow_y + shadow_height) + 1
                stream.rectangle(left, top, right - left, bottom - top)
                if shadow_box[2] and shadow_box[3]:
                    rounded_box(stream, shadow_box)
                stream.fill(even_odd=True)
            elif shadow_box[2] and shadow_box[3]:
                # Outer shadows are clipped out of the border box even when
                # the element's own background is transparent.
                _clip_outside_box(stream, source_box, shadow_box)
                rounded_box(stream, shadow_box)
                stream.fill()
