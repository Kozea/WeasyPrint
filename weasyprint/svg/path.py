"""
    weasyprint.svg.path
    -------------------

    Render paths.

"""

from math import atan2, cos, pi, radians, sin, tan

from .utils import normalize, point, quadratic_points, rotate

PATH_LETTERS = 'achlmqstvzACHLMQSTVZ'


def path(svg, node, font_size):
    from ..document import Matrix

    string = node.get('d', '')

    node.vertices = []

    for letter in PATH_LETTERS:
        string = string.replace(letter, ' {} '.format(letter))

    last_letter = None
    string = normalize(string)

    # TODO: get current point
    current_point = 0, 0
    svg.stream.move_to(0, 0)

    while string:
        string = string.strip()
        if string.split(' ', 1)[0] in PATH_LETTERS:
            letter, string = (string + ' ').split(' ', 1)
            if last_letter in (None, 'z', 'Z') and letter not in 'mM':
                node.vertices.append(current_point)
                first_path_point = current_point
        elif letter == 'M':
            letter = 'L'
        elif letter == 'm':
            letter = 'l'

        if last_letter in (None, 'm', 'M', 'z', 'Z'):
            first_path_point = None
        if letter not in (None, 'm', 'M', 'z', 'Z') and (
                first_path_point is None):
            first_path_point = current_point

        if letter in 'aA':
            # Elliptic curve
            # Drawn as an approximation using Bézier curves
            x1, y1 = current_point
            rx, ry, string = point(svg, string, font_size)
            rotation, string = string.split(' ', 1)
            rotation = radians(float(rotation))

            # The large and sweep values are not always separated from the
            # following values. These flags can only be 0 or 1, so reading a
            # single digit suffices.
            large, string = string[0], string[1:].strip()
            sweep, string = string[0], string[1:].strip()

            # Retrieve end point and set remainder (before checking flags)
            x3, y3, string = point(svg, string, font_size)
            if letter == 'a':
                x3 += x1
                y3 += y1

            # Only allow 0 or 1 for flags
            large, sweep = int(large), int(sweep)
            if large not in (0, 1) or sweep not in (0, 1):
                continue
            large, sweep = bool(large), bool(sweep)

            # rx=0 or ry=0 means straight line
            if not rx or not ry:
                if string and string[0] not in PATH_LETTERS:
                    # As we replace the current operation by l, we must be sure
                    # that the next letter is set to the real current letter (a
                    # or A) in case it’s omitted
                    next_letter = '{} '.format(letter)
                else:
                    next_letter = ''
                string = 'L {} {} {}{}'.format(x3, y3, next_letter, string)
                continue

            # Cancel the rotation of the second point
            xe, ye = rotate(x3 - x1, y3 - y1, -rotation)
            y_scale = ry / rx
            ye /= y_scale

            # Find the angle between the second point and the x axis
            angle = atan2(ye, xe)

            # Put the second point onto the x axis
            xe = (xe ** 2 + ye ** 2) ** .5
            ye = 0

            # Update the x radius if it is too small
            rx = max(rx, xe / 2)

            # Find one circle centre
            xc = xe / 2
            yc = (rx ** 2 - xc ** 2) ** .5

            # Choose between the two circles according to flags
            if large == sweep:
                yc = -yc

            # Put the second point and the center back to their positions
            xe, ye = rotate(xe, ye, angle)
            xc, yc = rotate(xc, yc, angle)

            # Find the drawing angles
            angle1 = atan2(-yc, -xc)
            angle2 = atan2(ye - yc, xe - xc)
            while angle1 < 0 or angle2 < 0:
                angle1 += 2 * pi
                angle2 += 2 * pi

            # Store the tangent angles
            node.vertices.append((-angle1, -angle2))

            # Fix angles to follow large arc flag
            if large == (abs(angle2 - angle1) < (pi + 0.001)):
                if angle1 > angle2:
                    angle1 -= 2 * pi
                else:
                    angle2 -= 2 * pi

            # Split arc into 3 Bézier curves when larger than pi
            if large:
                step = (angle2 - angle1) / 3
                angles = (
                    (angle1, angle1 + step),
                    (angle1 + step, angle1 + 2 * step),
                    (angle1 + 2 * step, angle2))
            else:
                angles = ((angle1, angle2),)

            # Draw Bézier curves
            matrix = Matrix(
                cos(rotation), sin(rotation),
                -sin(rotation) * y_scale, cos(rotation) * y_scale,
                x1, y1)
            h = 4 / 3 * tan((angles[0][1] - angles[0][0]) / 4)
            for angle1, angle2 in angles:
                point1 = matrix.transform_point(
                    xc + rx * cos(angle1) - h * rx * sin(angle1),
                    yc + rx * sin(angle1) + h * rx * cos(angle1))
                point2 = matrix.transform_point(
                    xc + rx * cos(angle2) + h * rx * sin(angle2),
                    yc + rx * sin(angle2) - h * rx * cos(angle2))
                point3 = matrix.transform_point(
                    xc + rx * cos(angle2),
                    yc + rx * sin(angle2))
                svg.stream.curve_to(*point1, *point2, *point3)

            current_point = x3, y3

        elif letter in 'cC':
            # Curve
            x1, y1, string = point(svg, string, font_size)
            x2, y2, string = point(svg, string, font_size)
            x3, y3, string = point(svg, string, font_size)
            if letter == 'c':
                x, y = current_point
                x1 += x
                x2 += x
                x3 += x
                y1 += y
                y2 += y
                y3 += y
            node.vertices.append((
                atan2(y1 - y2, x1 - x2), atan2(y3 - y2, x3 - x2)))
            svg.stream.curve_to(x1, y1, x2, y2, x3, y3)
            current_point = x3, y3

        elif letter in 'hH':
            # Horizontal line
            x, string = (string + ' ').split(' ', 1)
            old_x, old_y = current_point
            x, _ = svg.point(x, 0, font_size)
            if letter == 'h':
                x += old_x
            angle = 0 if x > old_x else pi
            node.vertices.append((pi - angle, angle))
            svg.stream.line_to(x, old_y)
            current_point = x, old_y

        elif letter in 'lL':
            # Straight line
            x, y, string = point(svg, string, font_size)
            old_x, old_y = current_point
            if letter == 'l':
                x += old_x
                y += old_y
            angle = atan2(y - old_y, x - old_x)
            node.vertices.append((pi - angle, angle))
            svg.stream.line_to(x, y)
            current_point = x, y

        elif letter in 'mM':
            # Current point move
            x, y, string = point(svg, string, font_size)
            if last_letter and last_letter not in 'zZ':
                node.vertices.append(None)
            if letter == 'm':
                x += current_point[0]
                y += current_point[1]
            svg.stream.move_to(x, y)
            current_point = x, y

        elif letter in 'qQ':
            # Quadratic curve
            x1, y1 = current_point
            x2, y2, string = point(svg, string, font_size)
            x3, y3, string = point(svg, string, font_size)
            if letter == 'q':
                x2 += x1
                x3 += x1
                y2 += y1
                y3 += y1
            xq1, yq1, xq2, yq2, xq3, yq3 = quadratic_points(
                x1, y1, x2, y2, x3, y3)
            svg.stream.curve_to(xq1, yq1, xq2, yq2, xq3, yq3)
            node.vertices.append((0, 0))
            current_point = x3, y3

        elif letter in 'sS':
            # Smooth curve
            x, y = current_point
            x1 = x3 + (x3 - x2) if last_letter in 'csCS' else x
            y1 = y3 + (y3 - y2) if last_letter in 'csCS' else y
            x2, y2, string = point(svg, string, font_size)
            x3, y3, string = point(svg, string, font_size)
            if letter == 's':
                x2 += x
                x3 += x
                y2 += y
                y3 += y
            node.vertices.append((
                atan2(y1 - y2, x1 - x2), atan2(y3 - y2, x3 - x2)))
            svg.stream.curve_to(x1, y1, x2, y2, x3, y3)
            current_point = x3, y3

        elif letter in 'tT':
            # Quadratic curve end
            x1, y1 = current_point
            if last_letter not in 'QqTt':
                x2, y2, x3, y3 = x, y, x, y
            x2 = x1 + x3 - x2
            y2 = y1 + y3 - y2
            x3, y3, string = point(svg, string, font_size)
            if letter == 't':
                x3 += x1
                y3 += y1
            xq1, yq1, xq2, yq2, xq3, yq3 = quadratic_points(
                x1, y1, x2, y2, x3, y3)
            node.vertices.append((0, 0))
            svg.stream.curve_to(xq1, yq1, xq2, yq2, xq3, yq3)
            current_point = x3, y3

        elif letter in 'vV':
            # Vertical line
            y, string = (string + ' ').split(' ', 1)
            old_x, old_y = current_point
            _, y = svg.point(0, y, font_size)
            if letter == 'v':
                y += old_y
            angle = pi / 2 if y > old_y else -pi / 2
            node.vertices.append((-angle, angle))
            svg.stream.line_to(old_x, y)
            current_point = old_x, y

        elif letter in 'zZ':
            # End of path
            node.vertices.append(None)
            svg.stream.close()
            current_point = first_path_point or (0, 0)

        if letter not in 'zZ':
            node.vertices.append(current_point)

        string = string.strip()
        last_letter = letter
