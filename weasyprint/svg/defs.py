from itertools import cycle
from math import hypot

import pydyf

from .colors import color
from .utils import parse_url, size


def linear_gradient(svg, node, font_size):
    svg.parse_def(node)


def marker(svg, node, font_size):
    svg.parse_def(node)


def use(svg, node, font_size):
    from . import SVG

    svg.stream.push_state()
    svg.stream.transform(
        1, 0, 0, 1, *svg.point(node.get('x'), node.get('y'), font_size))

    for attribute in ('x', 'y', 'viewBox', 'mask'):
        if attribute in node.attrib:
            del node.attrib[attribute]

    parsed_url = parse_url(node.get_href())
    if parsed_url.fragment and not parsed_url.path:
        tree = svg.tree.get_child(parsed_url.fragment)
    else:
        url = parsed_url.geturl()
        try:
            bytestring_svg = svg.url_fetcher(url)
            use_svg = SVG(bytestring_svg, url)
        except TypeError:
            svg.stream.restore()
            return
        else:
            use_svg.get_intrinsic_size(font_size)
            tree = use_svg.tree

    if tree.tag in ('svg', 'symbol'):
        # Explicitely specified
        # http://www.w3.org/TR/SVG11/struct.html#UseElement
        tree.tag = 'svg'
        if 'width' in node.attrib and 'height' in node.attrib:
            tree.attrib['width'] = node['width']
            tree.attrib['height'] = node['height']

    svg.draw_node(tree, font_size)
    svg.stream.pop_state()


def draw_gradient_or_pattern(svg, node, name, font_size, stroke):
    if name in svg.gradients:
        return draw_gradient(svg, node, svg.gradients[name], font_size, stroke)
    elif name in svg.patterns:
        # return draw_pattern(svg, node, name)
        return False


def draw_gradient(svg, node, gradient, font_size, stroke):
    from ..images import gradient_average_color, normalize_stop_positions

    bounding_box = svg.calculate_bounding_box(node, font_size)
    if not bounding_box:
        return False
    _, _, width, height = bounding_box

    x1, y1 = (
        size(gradient.get('x1', 0), font_size, width),
        size(gradient.get('y1', 0), font_size, height))
    x2, y2 = (
        size(gradient.get('x2', '100%'), font_size, width),
        size(gradient.get('y2', 0), font_size, height))
    vector_length = hypot(x2 - x1, y2 - y1)

    positions = []
    colors = []
    for child in gradient:
        positions.append(max(
            positions[-1] if positions else 0,
            size(child.get('offset'), font_size, 1)))
        colors.append(color(child.get('stop-color', 'black')))

    if len(colors) == 1:
        red, green, blue, alpha = colors[0]
        svg.stream.set_color_rgb(red, green, blue)
        if alpha != 1:
            svg.stream.set_alpha(alpha, stroke=stroke)
        return True

    spread = gradient.get('spreadMethod', 'pad')
    if spread not in ('repeat', 'reflect'):
        # Add explicit colors at boundaries if needed, because PDF doesn’t
        # extend color stops that are not displayed
        if positions[0] == positions[1]:
            positions.insert(0, positions[0] - 1)
            colors.insert(0, colors[0])
        if positions[-2] == positions[-1]:
            positions.append(positions[-1] + 1)
            colors.append(colors[-1])

    first, last, positions = normalize_stop_positions(positions)
    if spread in ('repeat', 'reflect'):
        # Render as a solid color if the first and last positions are equal
        # See https://drafts.csswg.org/css-images-3/#repeating-gradients
        if first == last:
            average_color = gradient_average_color(colors, positions)
            return 1, 'solid', None, [], [average_color]

        # Define defined gradient length and steps between positions
        stop_length = last - first
        assert stop_length > 0
        position_steps = [
            positions[i + 1] - positions[i]
            for i in range(len(positions) - 1)]

        # Create cycles used to add colors
        if spread == 'repeat':
            next_steps = cycle([0] + position_steps)
            next_colors = cycle(colors)
            previous_steps = cycle([0] + position_steps[::-1])
            previous_colors = cycle(colors[::-1])
        else:
            assert spread == 'reflect'
            next_steps = cycle(
                [0] + position_steps[::-1] + [0] + position_steps)
            next_colors = cycle(colors[::-1] + colors)
            previous_steps = cycle(
                [0] + position_steps + [0] + position_steps[::-1])
            previous_colors = cycle(colors + colors[::-1])

        # Add colors after last step
        while last < vector_length:
            step = next(next_steps)
            colors.append(next(next_colors))
            positions.append(positions[-1] + step)
            last += step * stop_length

        # Add colors before last step
        while first > 0:
            step = next(previous_steps)
            colors.insert(0, next(previous_colors))
            positions.insert(0, positions[0] - step)
            first -= step * stop_length

    # Define the coordinates of the starting and ending points
    x1, x2 = x1 + (x2 - x1) * first, x1 + (x2 - x1) * last
    y1, y2 = y1 + (y2 - y1) * first, y1 + (y2 - y1) * last
    points = (x1, y1, x2, y2)

    alphas = [color[3] for color in colors]
    alpha_couples = [
        (alphas[i], alphas[i + 1])
        for i in range(len(alphas) - 1)]
    color_couples = [
        [colors[i][:3], colors[i + 1][:3], 1]
        for i in range(len(colors) - 1)]

    # Premultiply colors
    for i, alpha in enumerate(alphas):
        if alpha == 0:
            if i > 0:
                color_couples[i - 1][1] = color_couples[i - 1][0]
            if i < len(colors) - 1:
                color_couples[i][0] = color_couples[i][1]
    for i, (a0, a1) in enumerate(alpha_couples):
        if 0 not in (a0, a1) and (a0, a1) != (1, 1):
            color_couples[i][2] = a0 / a1

    pattern = svg.stream.add_pattern(
        0, 0, width, height, width, height, svg.stream.ctm)
    child = pattern.add_transparency_group([0, 0, width, height])

    shading = child.add_shading()
    shading['ShadingType'] = 2
    shading['ColorSpace'] = '/DeviceRGB'
    shading['Domain'] = pydyf.Array([positions[0], positions[-1]])
    shading['Coords'] = pydyf.Array(points)
    shading['Function'] = pydyf.Dictionary({
        'FunctionType': 3,
        'Domain': pydyf.Array([positions[0], positions[-1]]),
        'Encode': pydyf.Array((len(colors) - 1) * [0, 1]),
        'Bounds': pydyf.Array(positions[1:-1]),
        'Functions': pydyf.Array([
            pydyf.Dictionary({
                'FunctionType': 2,
                'Domain': pydyf.Array([positions[0], positions[-1]]),
                'C0': pydyf.Array(c0),
                'C1': pydyf.Array(c1),
                'N': n,
            }) for c0, c1, n in color_couples
        ]),
    })
    if spread not in ('repeat', 'reflect'):
        shading['Extend'] = pydyf.Array([b'true', b'true'])

    if any(alpha != 1 for alpha in alphas):
        alpha_stream = child.add_transparency_group(
            [0, 0, svg.concrete_width, svg.concrete_height])
        alpha_state = pydyf.Dictionary({
            'Type': '/ExtGState',
            'SMask': pydyf.Dictionary({
                'Type': '/Mask',
                'S': '/Luminosity',
                'G': alpha_stream,
            }),
            'ca': 1,
            'AIS': 'false',
        })
        alpha_state_id = f'as{len(child._alpha_states)}'
        child._alpha_states[alpha_state_id] = alpha_state
        child.set_state(alpha_state_id)

        alpha_shading = alpha_stream.add_shading()
        alpha_shading['ShadingType'] = 2
        alpha_shading['ColorSpace'] = '/DeviceGray'
        alpha_shading['Domain'] = pydyf.Array(
            [positions[0], positions[-1]])
        alpha_shading['Coords'] = pydyf.Array(points)
        alpha_shading['Function'] = pydyf.Dictionary({
            'FunctionType': 3,
            'Domain': pydyf.Array([positions[0], positions[-1]]),
            'Encode': pydyf.Array((len(colors) - 1) * [0, 1]),
            'Bounds': pydyf.Array(positions[1:-1]),
            'Functions': pydyf.Array([
                pydyf.Dictionary({
                    'FunctionType': 2,
                    'Domain': pydyf.Array([0, 1]),
                    'C0': pydyf.Array([c0]),
                    'C1': pydyf.Array([c1]),
                    'N': 1,
                }) for c0, c1 in alpha_couples
            ]),
        })
        if spread == 'pad':
            alpha_shading['Extend'] = pydyf.Array([b'true', b'true'])
        alpha_stream.stream = [f'/{alpha_shading.id} sh']

    child.shading(shading.id)

    pattern.draw_x_object(child.id)
    svg.stream.color_space('Pattern', stroke=stroke)
    svg.stream.set_color_special(pattern.id, stroke=stroke)
    return True
