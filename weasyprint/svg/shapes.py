"""
    weasyprint.svg.shapes
    ---------------------

    Draw simple shapes.

"""

from math import atan2, pi, sqrt

from .utils import normalize, point


def circle(svg, node, font_size):
    """Draw circle tag."""
    r = svg.length(node.get('r'), font_size)
    if not r:
        return
    ratio = r / sqrt(pi)
    cx, cy = svg.point(node.get('cx'), node.get('cy'), font_size)

    svg.stream.move_to(cx + r, cy)
    svg.stream.curve_to(cx + r, cy + ratio, cx + ratio, cy + r, cx, cy + r)
    svg.stream.curve_to(cx - ratio, cy + r, cx - r, cy + ratio, cx - r, cy)
    svg.stream.curve_to(cx - r, cy - ratio, cx - ratio, cy - r, cx, cy - r)
    svg.stream.curve_to(cx + ratio, cy - r, cx + r, cy - ratio, cx + r, cy)
    svg.stream.close()


def ellipse(svg, node, font_size):
    """Draw ellipse tag."""
    rx, ry = svg.point(node.get('rx'), node.get('ry'), font_size)
    if not rx or not ry:
        return
    ratio_x = rx / sqrt(pi)
    ratio_y = ry / sqrt(pi)
    cx, cy = svg.point(node.get('cx'), node.get('cy'), font_size)

    svg.stream.move_to(cx + rx, cy)
    svg.stream.curve_to(
        cx + rx, cy + ratio_y, cx + ratio_x, cy + ry, cx, cy + ry)
    svg.stream.curve_to(
        cx - ratio_x, cy + ry, cx - rx, cy + ratio_y, cx - rx, cy)
    svg.stream.curve_to(
        cx - rx, cy - ratio_y, cx - ratio_x, cy - ry, cx, cy - ry)
    svg.stream.curve_to(
        cx + ratio_x, cy - ry, cx + rx, cy - ratio_y, cx + rx, cy)
    svg.stream.close()


def rect(svg, node, font_size):
    """Draw rect tag."""
    width, height = svg.point(node.get('width'), node.get('height'), font_size)
    if width <= 0 or height <= 0:
        return

    x, y = svg.point(node.get('x'), node.get('y'), font_size)

    rx = node.get('rx')
    ry = node.get('ry')
    if rx and ry is None:
        ry = rx
    elif ry and rx is None:
        rx = ry
    rx, ry = svg.point(rx, ry, font_size)

    if rx == 0 or ry == 0:
        svg.stream.rectangle(x, y, width, height)
        return

    if rx > width / 2:
        rx = width / 2
    if ry > height / 2:
        ry = height / 2

    # Inspired by Cairo Cookbook
    # http://cairographics.org/cookbook/roundedrectangles/
    ARC_TO_BEZIER = 4 * (2 ** .5 - 1) / 3
    c1, c2 = ARC_TO_BEZIER * rx, ARC_TO_BEZIER * ry

    svg.stream.move_to(x + rx, y)
    svg.stream.line_to(x + width - rx, y)
    svg.stream.curve_to(
        x + width - rx + c1, y, x + width, y + c2, x + width, y + ry)
    svg.stream.line_to(x + width, y + height - ry)
    svg.stream.curve_to(
        x + width, y + height - ry + c2, x + width + c1 - rx, y + height,
        x + width - rx, y + height)
    svg.stream.line_to(x + rx, y + height)
    svg.stream.curve_to(
        x + rx - c1, y + height, x, y + height - c2, x, y + height - ry)
    svg.stream.line_to(x, y + ry)
    svg.stream.curve_to(x, y + ry - c2, x + rx - c1, y, x + rx, y)
    svg.stream.close()


def line(svg, node, font_size):
    """Draw line tag."""
    x1, y1 = svg.point(node.get('x1'), node.get('y1'), font_size)
    x2, y2 = svg.point(node.get('x2'), node.get('y2'), font_size)
    svg.stream.move_to(x1, y1)
    svg.stream.line_to(x2, y2)
    angle = atan2(y2 - y1, x2 - x1)
    node.vertices = [(x1, y1), (pi - angle, angle), (x2, y2)]


def polygon(svg, node, font_size):
    """Draw polygon tag."""
    polyline(svg, node, font_size)
    svg.stream.close()


def polyline(svg, node, font_size):
    """Draw polyline tag."""
    points = normalize(node.get('points'))
    if points:
        x, y, points = point(svg, points, font_size)
        svg.stream.move_to(x, y)
        node.vertices = [(x, y)]
        while points:
            x_old, y_old = x, y
            x, y, points = point(svg, points, font_size)
            angle = atan2(x - x_old, y - y_old)
            node.vertices.append((pi - angle, angle))
            svg.stream.line_to(x, y)
            node.vertices.append((x, y))
