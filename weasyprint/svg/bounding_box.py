"""Calculate bounding boxes of SVG tags."""

from math import atan, atan2, cos, inf, isinf, pi, radians, sin, sqrt, tan

from .path import PATH_LETTERS
from .utils import normalize, point

EMPTY_BOUNDING_BOX = inf, inf, 0, 0


def bounding_box(svg, node, font_size, stroke):
    """Bounding box for any node."""
    if node.tag not in BOUNDING_BOX_METHODS:
        return EMPTY_BOUNDING_BOX
    box = BOUNDING_BOX_METHODS[node.tag](svg, node, font_size)
    if not is_valid_bounding_box(box):
        return EMPTY_BOUNDING_BOX
    if stroke and node.tag != 'g' and any(svg.get_paint(node.get('stroke'))):
        stroke_width = svg.length(node.get('stroke-width', '1px'), font_size)
        box = (
            box[0] - stroke_width / 2, box[1] - stroke_width / 2,
            box[2] + stroke_width, box[3] + stroke_width)
    return box


def bounding_box_rect(svg, node, font_size):
    """Bounding box for rect node."""
    x, y = svg.point(node.get('x'), node.get('y'), font_size)
    width, height = svg.point(
        node.get('width'), node.get('height'), font_size)
    return x, y, width, height


def bounding_box_circle(svg, node, font_size):
    """Bounding box for circle node."""
    cx, cy = svg.point(node.get('cx'), node.get('cy'), font_size)
    r = svg.length(node.get('r'), font_size)
    return cx - r, cy - r, 2 * r, 2 * r


def bounding_box_ellipse(svg, node, font_size):
    """Bounding box for ellipse node."""
    rx, ry = svg.point(node.get('rx'), node.get('ry'), font_size)
    cx, cy = svg.point(node.get('cx'), node.get('cy'), font_size)
    return cx - rx, cy - ry, 2 * rx, 2 * ry


def bounding_box_line(svg, node, font_size):
    """Bounding box for line node."""
    x1, y1 = svg.point(node.get('x1'), node.get('y1'), font_size)
    x2, y2 = svg.point(node.get('x2'), node.get('y2'), font_size)
    x, y = min(x1, x2), min(y1, y2)
    width, height = max(x1, x2) - x, max(y1, y2) - y
    return x, y, width, height


def bounding_box_polyline(svg, node, font_size):
    """Bounding box for polyline node."""
    bounding_box = EMPTY_BOUNDING_BOX
    points = []
    normalized_points = normalize(node.get('points', ''))
    while normalized_points:
        x, y, normalized_points = point(svg, normalized_points, font_size)
        points.append((x, y))
    return extend_bounding_box(bounding_box, points)


def bounding_box_path(svg, node, font_size):
    """Bounding box for path node."""
    path_data = node.get('d', '')

    # Normalize path data for correct parsing
    for letter in PATH_LETTERS:
        path_data = path_data.replace(letter, f' {letter} ')
    path_data = normalize(path_data)

    bounding_box = EMPTY_BOUNDING_BOX
    previous_x = 0
    previous_y = 0
    letter = 'M'    # Move as default
    while path_data:
        path_data = path_data.strip()
        if path_data.split(' ', 1)[0] in PATH_LETTERS:
            letter, path_data = (f'{path_data} ').split(' ', 1)

        if letter in 'aA':
            # Elliptical arc curve
            rx, ry, path_data = point(svg, path_data, font_size)
            rotation, path_data = path_data.split(' ', 1)
            rotation = radians(float(rotation))

            # The large and sweep values are not always separated from the
            # following values, here is the crazy parser
            large, path_data = path_data[0], path_data[1:].strip()
            while not large[-1].isdigit():
                large, path_data = large + path_data[0], path_data[1:].strip()
            sweep, path_data = path_data[0], path_data[1:].strip()
            while not sweep[-1].isdigit():
                sweep, path_data = sweep + path_data[0], path_data[1:].strip()

            large, sweep = bool(int(large)), bool(int(sweep))

            x, y, path_data = point(svg, path_data, font_size)

            # Relative coordinate, convert to absolute
            if letter == 'a':
                x += previous_x
                y += previous_y

            # Extend bounding box with start and end coordinates
            arc_bounding_box = _bounding_box_elliptical_arc(
                previous_x, previous_y, rx, ry, rotation, large, sweep, x, y)
            x1, y1, width, height = arc_bounding_box
            x2 = x1 + width
            y2 = y1 + height
            points = (x1, y1), (x2, y2)
            bounding_box = extend_bounding_box(bounding_box, points)
            previous_x = x
            previous_y = y

        elif letter in 'cC':
            # Curve
            x1, y1, path_data = point(svg, path_data, font_size)
            x2, y2, path_data = point(svg, path_data, font_size)
            x, y, path_data = point(svg, path_data, font_size)

            # Relative coordinates, convert to absolute
            if letter == 'c':
                x1 += previous_x
                y1 += previous_y
                x2 += previous_x
                y2 += previous_y
                x += previous_x
                y += previous_y

            # Extend bounding box with all coordinates
            bounding_box = extend_bounding_box(
                bounding_box, ((x1, y1), (x2, y2), (x, y)))
            previous_x = x
            previous_y = y

        elif letter in 'hH':
            # Horizontal line
            x, path_data = (f'{path_data} ').split(' ', 1)
            x, _ = svg.point(x, 0, font_size)

            # Relative coordinate, convert to absolute
            if letter == 'h':
                x += previous_x

            # Extend bounding box with coordinate
            bounding_box = extend_bounding_box(
                bounding_box, ((x, previous_y),))
            previous_x = x

        elif letter in 'lLmMtT':
            # Line/Move/Smooth quadratic curve
            x, y, path_data = point(svg, path_data, font_size)

            # Relative coordinate, convert to absolute
            if letter in 'lmt':
                x += previous_x
                y += previous_y

            # Extend bounding box with coordinate
            bounding_box = extend_bounding_box(bounding_box, ((x, y),))
            previous_x = x
            previous_y = y

        elif letter in 'qQsS':
            # Quadratic curve/Smooth curve
            x1, y1, path_data = point(svg, path_data, font_size)
            x, y, path_data = point(svg, path_data, font_size)

            # Relative coordinates, convert to absolute
            if letter in 'qs':
                x1 += previous_x
                y1 += previous_y
                x += previous_x
                y += previous_y

            # Extend bounding box with coordinates
            bounding_box = extend_bounding_box(
                bounding_box, ((x1, y1), (x, y)))
            previous_x = x
            previous_y = y

        elif letter in 'vV':
            # Vertical line
            y, path_data = (f'{path_data} ').split(' ', 1)
            _, y = svg.point(0, y, font_size)

            # Relative coordinate, convert to absolute
            if letter == 'v':
                y += previous_y

            # Extend bounding box with coordinate
            bounding_box = extend_bounding_box(
                bounding_box, ((previous_x, y),))
            previous_y = y

        path_data = path_data.strip()

    return bounding_box


def bounding_box_text(svg, node, font_size):
    """Bounding box for text node."""
    return node.get('text_bounding_box')


def bounding_box_g(svg, node, font_size):
    """Bounding box for g node."""
    bounding_box = EMPTY_BOUNDING_BOX
    for child in node:
        child_bounding_box = svg.calculate_bounding_box(child, font_size)
        if is_valid_bounding_box(child_bounding_box):
            minx, miny, width, height = child_bounding_box
            maxx, maxy = minx + width, miny + height
            bounding_box = extend_bounding_box(
                bounding_box, ((minx, miny), (maxx, maxy)))
    return bounding_box


def bounding_box_use(svg, node, font_size):
    """Bounding box for use node."""
    from .defs import get_use_tree

    if (tree := get_use_tree(svg, node, font_size)) is None:
        return EMPTY_BOUNDING_BOX
    else:
        return bounding_box(svg, tree, font_size, True)


def _bounding_box_elliptical_arc(x1, y1, rx, ry, phi, large, sweep, x, y):
    """Bounding box of an elliptical arc in path node."""
    rx, ry = abs(rx), abs(ry)
    if 0 in (rx, ry):
        return min(x, x1), min(y, y1), abs(x - x1), abs(y - y1)

    x1prime = cos(phi) * (x1 - x) / 2 + sin(phi) * (y1 - y) / 2
    y1prime = -sin(phi) * (x1 - x) / 2 + cos(phi) * (y1 - y) / 2

    radicant = (
        rx ** 2 * ry ** 2 - rx ** 2 * y1prime ** 2 - ry ** 2 * x1prime ** 2)
    radicant /= rx ** 2 * y1prime ** 2 + ry ** 2 * x1prime ** 2
    cxprime = cyprime = 0

    if radicant < 0:
        ratio = rx / ry
        radicant = y1prime ** 2 + x1prime ** 2 / ratio ** 2
        if radicant < 0:
            return min(x, x1), min(y, y1), abs(x - x1), abs(y - y1)
        ry = sqrt(radicant)
        rx = ratio * ry
    else:
        factor = (-1 if large == sweep else 1) * sqrt(radicant)

        cxprime = factor * rx * y1prime / ry
        cyprime = -factor * ry * x1prime / rx

    cx = cxprime * cos(phi) - cyprime * sin(phi) + (x1 + x) / 2
    cy = cxprime * sin(phi) + cyprime * cos(phi) + (y1 + y) / 2

    if phi in (0, pi):
        minx = cx - rx
        tminx = atan2(0, -rx)
        maxx = cx + rx
        tmaxx = atan2(0, rx)
        miny = cy - ry
        tminy = atan2(-ry, 0)
        maxy = cy + ry
        tmaxy = atan2(ry, 0)
    elif phi in (pi / 2, 3 * pi / 2):
        minx = cx - ry
        tminx = atan2(0, -ry)
        maxx = cx + ry
        tmaxx = atan2(0, ry)
        miny = cy - rx
        tminy = atan2(-rx, 0)
        maxy = cy + rx
        tmaxy = atan2(rx, 0)
    else:
        tminx = -atan(ry * tan(phi) / rx)
        tmaxx = pi - atan(ry * tan(phi) / rx)
        minx = cx + rx * cos(tminx) * cos(phi) - ry * sin(tminx) * sin(phi)
        maxx = cx + rx * cos(tmaxx) * cos(phi) - ry * sin(tmaxx) * sin(phi)
        if minx > maxx:
            minx, maxx = maxx, minx
            tminx, tmaxx = tmaxx, tminx
        tmp_y = cy + rx * cos(tminx) * sin(phi) + ry * sin(tminx) * cos(phi)
        tminx = atan2(minx - cx, tmp_y - cy)
        tmp_y = cy + rx * cos(tmaxx) * sin(phi) + ry * sin(tmaxx) * cos(phi)
        tmaxx = atan2(maxx - cx, tmp_y - cy)

        tminy = atan(ry / (tan(phi) * rx))
        tmaxy = atan(ry / (tan(phi) * rx)) + pi
        miny = cy + rx * cos(tminy) * sin(phi) + ry * sin(tminy) * cos(phi)
        maxy = cy + rx * cos(tmaxy) * sin(phi) + ry * sin(tmaxy) * cos(phi)
        if miny > maxy:
            miny, maxy = maxy, miny
            tminy, tmaxy = tmaxy, tminy
        tmp_x = cx + rx * cos(tminy) * cos(phi) - ry * sin(tminy) * sin(phi)
        tminy = atan2(tmp_x - cx, miny - cy)
        tmp_x = cx + rx * cos(tmaxy) * cos(phi) - ry * sin(tmaxy) * sin(phi)
        tmaxy = atan2(maxy - cy, tmp_x - cx)

    angle1 = atan2(y1 - cy, x1 - cx)
    angle2 = atan2(y - cy, x - cx)

    if not sweep:
        angle1, angle2 = angle2, angle1

    other_arc = False
    if angle1 > angle2:
        angle1, angle2 = angle2, angle1
        other_arc = True

    if ((not other_arc and (angle1 > tminx or angle2 < tminx)) or
            (other_arc and not (angle1 > tminx or angle2 < tminx))):
        minx = min(x, x1)
    if ((not other_arc and (angle1 > tmaxx or angle2 < tmaxx)) or
            (other_arc and not (angle1 > tmaxx or angle2 < tmaxx))):
        maxx = max(x, x1)
    if ((not other_arc and (angle1 > tminy or angle2 < tminy)) or
            (other_arc and not (angle1 > tminy or angle2 < tminy))):
        miny = min(y, y1)
    if ((not other_arc and (angle1 > tmaxy or angle2 < tmaxy)) or
            (other_arc and not (angle1 > tmaxy or angle2 < tmaxy))):
        maxy = max(y, y1)

    return minx, miny, maxx - minx, maxy - miny


def extend_bounding_box(bounding_box, points):
    """Extend a bounding box to include given points."""
    minx, miny, width, height = bounding_box
    maxx, maxy = (
        -inf if isinf(minx) else minx + width,
        -inf if isinf(miny) else miny + height)
    x_list, y_list = zip(*points)
    minx, miny, maxx, maxy = (
        min(minx, *x_list), min(miny, *y_list),
        max(maxx, *x_list), max(maxy, *y_list))
    return minx, miny, maxx - minx, maxy - miny


def is_valid_bounding_box(bounding_box):
    """Check that a bounding box doesn’t have infinite boundaries."""
    return bounding_box and not isinf(bounding_box[0] + bounding_box[1])


BOUNDING_BOX_METHODS = {
    'rect': bounding_box_rect,
    'circle': bounding_box_circle,
    'ellipse': bounding_box_ellipse,
    'line': bounding_box_line,
    'polyline': bounding_box_polyline,
    'polygon': bounding_box_polyline,
    'path': bounding_box_path,
    'g': bounding_box_g,
    'use': bounding_box_use,
    'marker': bounding_box_g,
    'text': bounding_box_text,
    'tspan': bounding_box_text,
    'textPath': bounding_box_text,
}
