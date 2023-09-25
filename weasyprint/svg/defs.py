"""Parse and draw definitions: gradients, patterns, masks, uses…"""

from itertools import cycle
from math import ceil, hypot

from ..matrix import Matrix
from .bounding_box import is_valid_bounding_box
from .utils import color, parse_url, size, transform


def use(svg, node, font_size):
    """Draw use tags."""
    from . import NOT_INHERITED_ATTRIBUTES, SVG

    x, y = svg.point(node.get('x'), node.get('y'), font_size)

    for attribute in ('x', 'y', 'viewBox', 'mask'):
        if attribute in node.attrib:
            del node.attrib[attribute]

    parsed_url = parse_url(node.get_href(svg.url))
    svg_url = parse_url(svg.url)
    if svg_url.scheme == 'data':
        svg_url = parse_url('')
    same_origin = (
        parsed_url[:3] == ('', '', '') or
        parsed_url[:3] == svg_url[:3])
    if parsed_url.fragment and same_origin:
        if parsed_url.fragment in svg.use_cache:
            tree = svg.use_cache[parsed_url.fragment].copy()
        else:
            try:
                tree = svg.tree.get_child(parsed_url.fragment).copy()
            except Exception:
                return
            else:
                svg.use_cache[parsed_url.fragment] = tree
    else:
        url = parsed_url.geturl()
        try:
            bytestring_svg = svg.url_fetcher(url)
            use_svg = SVG(bytestring_svg, url)
        except Exception:
            return
        else:
            use_svg.get_intrinsic_size(font_size)
            tree = use_svg.tree

    if tree.tag in ('svg', 'symbol'):
        # Explicitely specified
        # https://www.w3.org/TR/SVG11/struct.html#UseElement
        tree._etree_node.tag = 'svg'
        if 'width' in node.attrib and 'height' in node.attrib:
            tree.attrib['width'] = node.attrib['width']
            tree.attrib['height'] = node.attrib['height']

    # Cascade
    for key, value in node.attrib.items():
        if key not in NOT_INHERITED_ATTRIBUTES:
            if key not in tree.attrib:
                tree.attrib[key] = value

    node.override_iter(iter((tree,)))
    svg.stream.transform(e=x, f=y)


def draw_gradient_or_pattern(svg, node, name, font_size, opacity, stroke):
    """Draw given gradient or pattern."""
    if name in svg.gradients:
        return draw_gradient(
            svg, node, svg.gradients[name], font_size, opacity, stroke)
    elif name in svg.patterns:
        return draw_pattern(
            svg, node, svg.patterns[name], font_size, opacity, stroke)


def draw_gradient(svg, node, gradient, font_size, opacity, stroke):
    """Draw given gradient node."""
    # TODO: merge with Gradient.draw
    positions = []
    colors = []
    for child in gradient:
        positions.append(max(
            positions[-1] if positions else 0,
            size(child.get('offset'), font_size, 1)))
        stop_opacity = float(child.get('stop-opacity', 1)) * opacity
        stop_color = color(child.get('stop-color', 'black'))
        if stop_opacity < 1:
            stop_color = tuple(
                stop_color[:3] + (stop_color[3] * stop_opacity,))
        colors.append(stop_color)

    if not colors:
        return False
    elif len(colors) == 1:
        red, green, blue, alpha = colors[0]
        svg.stream.set_color_rgb(red, green, blue)
        if alpha != 1:
            svg.stream.set_alpha(alpha, stroke=stroke)
        return True

    bounding_box = svg.calculate_bounding_box(node, font_size, stroke)
    if not is_valid_bounding_box(bounding_box):
        return False
    if gradient.get('gradientUnits') == 'userSpaceOnUse':
        width, height = svg.inner_width, svg.inner_height
        matrix = Matrix()
    else:
        width, height = 1, 1
        e, f, a, d = bounding_box
        matrix = Matrix(a=a, d=d, e=e, f=f)

    spread = gradient.get('spreadMethod', 'pad')
    if spread in ('repeat', 'reflect'):
        if positions[0] > 0:
            positions.insert(0, 0)
            colors.insert(0, colors[0])
        if positions[-1] < 1:
            positions.append(1)
            colors.append(colors[-1])
    else:
        # Add explicit colors at boundaries if needed, because PDF doesn’t
        # extend color stops that are not displayed
        if positions[0] == positions[1]:
            if gradient.tag == 'radialGradient':
                # Avoid negative radius for radial gradients
                positions.insert(0, 0)
            else:
                positions.insert(0, positions[0] - 1)
            colors.insert(0, colors[0])
        if positions[-2] == positions[-1]:
            positions.append(positions[-1] + 1)
            colors.append(colors[-1])

    if 'gradientTransform' in gradient.attrib:
        transform_matrix = transform(
            gradient.get('gradientTransform'), font_size,
            svg.normalized_diagonal)
        matrix = transform_matrix @ matrix

    if gradient.tag == 'linearGradient':
        shading_type = 2
        x1, y1 = (
            size(gradient.get('x1', 0), font_size, width),
            size(gradient.get('y1', 0), font_size, height))
        x2, y2 = (
            size(gradient.get('x2', '100%'), font_size, width),
            size(gradient.get('y2', 0), font_size, height))
        positions, colors, coords = spread_linear_gradient(
            spread, positions, colors, x1, y1, x2, y2, bounding_box, matrix)
    else:
        assert gradient.tag == 'radialGradient'
        shading_type = 3
        cx, cy = (
            size(gradient.get('cx', '50%'), font_size, width),
            size(gradient.get('cy', '50%'), font_size, height))
        r = size(gradient.get('r', '50%'), font_size, hypot(width, height))
        fx, fy = (
            size(gradient.get('fx', cx), font_size, width),
            size(gradient.get('fy', cy), font_size, height))
        fr = size(gradient.get('fr', 0), font_size, hypot(width, height))
        positions, colors, coords = spread_radial_gradient(
            spread, positions, colors, fx, fy, fr, cx, cy, r, width, height,
            matrix)

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

    bx1, by1 = 0, 0
    if 'gradientTransform' in gradient.attrib:
        bx1, by1 = transform_matrix.invert.transform_point(bx1, by1)
        bx2, by2 = transform_matrix.invert.transform_point(width, height)
        width, height = bx2 - bx1, by2 - by1

    pattern = svg.stream.add_pattern(
        bx1, by1, width, height, width, height, matrix @ svg.stream.ctm)
    group = pattern.add_group(bx1, by1, width, height)

    domain = (positions[0], positions[-1])
    extend = spread not in ('repeat', 'reflect')
    encode = (len(colors) - 1) * (0, 1)
    bounds = positions[1:-1]
    sub_functions = (
        group.create_interpolation_function(domain, c0, c1, n)
        for c0, c1, n in color_couples)
    function = group.create_stitching_function(
        domain, encode, bounds, sub_functions)
    shading = group.add_shading(
        shading_type, 'RGB', domain, coords, extend, function)

    if any(alpha != 1 for alpha in alphas):
        alpha_stream = group.set_alpha_state(bx1, by1, width, height)
        domain = (positions[0], positions[-1])
        extend = spread not in ('repeat', 'reflect')
        encode = (len(colors) - 1) * (0, 1)
        bounds = positions[1:-1]
        sub_functions = (
            group.create_interpolation_function((0, 1), [c0], [c1], 1)
            for c0, c1 in alpha_couples)
        function = group.create_stitching_function(
            domain, encode, bounds, sub_functions)
        alpha_shading = alpha_stream.add_shading(
            shading_type, 'Gray', domain, coords, extend, function)
        alpha_stream.stream = [f'/{alpha_shading.id} sh']

    group.shading(shading.id)
    pattern.set_alpha(1)
    pattern.draw_x_object(group.id)
    svg.stream.color_space('Pattern', stroke=stroke)
    svg.stream.set_color_special(pattern.id, stroke=stroke)
    return True


def spread_linear_gradient(spread, positions, colors, x1, y1, x2, y2,
                           bounding_box, matrix):
    """Repeat linear gradient."""
    # TODO: merge with LinearGradient.layout
    from ..images import gradient_average_color, normalize_stop_positions

    first, last, positions = normalize_stop_positions(positions)
    if spread in ('repeat', 'reflect'):
        # Render as a solid color if the first and last positions are equal
        # See https://drafts.csswg.org/css-images-3/#repeating-gradients
        if first == last:
            average_color = gradient_average_color(colors, positions)
            return 1, 'solid', None, [], [average_color]

        # Define defined gradient length and steps between positions
        stop_length = last - first
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

        # Normalize bounding box
        bx1, by1, bw, bh = bounding_box
        bx1, bx2 = (bx1, bx1 + bw) if bw > 0 else (bx1 + bw, bx1)
        by1, by2 = (by1, by1 + bh) if bh > 0 else (by1 + bh, by1)

        # Transform gradient vector coordinates
        tx1, ty1 = matrix.transform_point(x1, y1)
        tx2, ty2 = matrix.transform_point(x2, y2)

        # Find the extremities of the repeating vector, by projecting the
        # bounding box corners on the gradient vector
        xb, yb = tx1, ty1
        xv, yv = tx2 - tx1, ty2 - ty1
        xa1, xa2 = (bx1, bx2) if tx1 < tx2 else (bx2, bx1)
        ya1, ya2 = (by1, by2) if ty1 < ty2 else (by2, by1)
        min_vector = ((xa1 - xb) * xv + (ya1 - yb) * yv) / hypot(xv, yv) ** 2
        max_vector = ((xa2 - xb) * xv + (ya2 - yb) * yv) / hypot(xv, yv) ** 2

        # Add colors after last step
        while last < max_vector:
            step = next(next_steps)
            colors.append(next(next_colors))
            positions.append(positions[-1] + step)
            last += step * stop_length

        # Add colors before first step
        while first > min_vector:
            step = next(previous_steps)
            colors.insert(0, next(previous_colors))
            positions.insert(0, positions[0] - step)
            first -= step * stop_length

    x1, x2 = x1 + (x2 - x1) * first, x1 + (x2 - x1) * last
    y1, y2 = y1 + (y2 - y1) * first, y1 + (y2 - y1) * last
    coords = (x1, y1, x2, y2)
    return positions, colors, coords


def spread_radial_gradient(spread, positions, colors, fx, fy, fr, cx, cy, r,
                           width, height, matrix):
    """Repeat radial gradient."""
    # TODO: merge with RadialGradient._repeat
    from ..images import gradient_average_color, normalize_stop_positions

    first, last, positions = normalize_stop_positions(positions)
    fr, r = fr + (r - fr) * first, fr + (r - fr) * last

    if spread in ('repeat', 'reflect'):
        # Keep original lists and values, they’re useful
        original_colors = colors.copy()
        original_positions = positions.copy()

        # Get the maximum distance between the center and the corners, to find
        # how many times we have to repeat the colors outside
        tw, th = matrix.invert.transform_point(width, height)
        max_distance = hypot(
            max(abs(fx), abs(tw - fx)), max(abs(fy), abs(th - fy)))
        gradient_length = r - fr
        repeat_after = ceil((max_distance - r) / gradient_length)
        if repeat_after > 0:
            # Repeat colors and extrapolate positions
            repeat = 1 + repeat_after
            if spread == 'repeat':
                colors *= repeat
            else:
                assert spread == 'reflect'
                colors = []
                for i in range(repeat):
                    colors += original_colors[::-1 if i % 2 else 1]
            positions = [
                i + position for i in range(repeat) for position in positions]
            r += gradient_length * repeat_after

        if fr == 0:
            # Inner circle has 0 radius, no need to repeat inside, return
            coords = (fx, fy, fr, cx, cy, r)
            return positions, colors, coords

        # Find how many times we have to repeat the colors inside
        repeat_before = fr / gradient_length

        # Set the inner circle size to 0
        fr = 0

        # Find how many times the whole gradient can be repeated
        full_repeat = int(repeat_before)
        if full_repeat:
            # Repeat colors and extrapolate positions
            if spread == 'repeat':
                colors += original_colors * full_repeat
            else:
                assert spread == 'reflect'
                for i in range(full_repeat):
                    colors += original_colors[
                        ::-1 if (i + repeat_after) % 2 else 1]
            positions = [
                i - full_repeat + position for i in range(full_repeat)
                for position in original_positions] + positions

        # Find the ratio of gradient that must be added to reach the center
        partial_repeat = repeat_before - full_repeat
        if partial_repeat == 0:
            # No partial repeat, return
            coords = (fx, fy, fr, cx, cy, r)
            return positions, colors, coords

        # Iterate through positions in reverse order, from the outer
        # circle to the original inner circle, to find positions from
        # the inner circle (including full repeats) to the center
        assert (original_positions[0], original_positions[-1]) == (0, 1)
        assert 0 < partial_repeat < 1
        reverse = original_positions[::-1]
        ratio = 1 - partial_repeat
        if spread == 'reflect':
            original_colors = original_colors[::-1]
        for i, position in enumerate(reverse, start=1):
            if position == ratio:
                # The center is a color of the gradient, truncate original
                # colors and positions and prepend them
                colors = original_colors[-i:] + colors
                new_positions = [
                    position - full_repeat - 1
                    for position in original_positions[-i:]]
                positions = new_positions + positions
                break
            if position < ratio:
                # The center is between two colors of the gradient,
                # define the center color as the average of these two
                # gradient colors
                color = original_colors[-i]
                next_color = original_colors[-(i - 1)]
                next_position = original_positions[-(i - 1)]
                average_colors = [color, color, next_color, next_color]
                average_positions = [position, ratio, ratio, next_position]
                zero_color = gradient_average_color(
                    average_colors, average_positions)
                colors = [zero_color] + original_colors[-(i - 1):] + colors
                new_positions = [
                    position - 1 - full_repeat for position
                    in original_positions[-(i - 1):]]
                positions = (
                    [ratio - 1 - full_repeat] + new_positions + positions)
                break

    coords = (fx, fy, fr, cx, cy, r)
    return positions, colors, coords


def draw_pattern(svg, node, pattern, font_size, opacity, stroke):
    """Draw given gradient node."""
    from . import Pattern

    pattern._etree_node.tag = 'svg'

    bounding_box = svg.calculate_bounding_box(node, font_size, stroke)
    if not is_valid_bounding_box(bounding_box):
        return False
    x, y = bounding_box[0], bounding_box[1]
    matrix = Matrix(e=x, f=y)
    if pattern.get('patternUnits') == 'userSpaceOnUse':
        pattern_width = size(pattern.get('width', 0), font_size, 1)
        pattern_height = size(pattern.get('height', 0), font_size, 1)
    else:
        width, height = bounding_box[2], bounding_box[3]
        pattern_width = (
            size(pattern.attrib.pop('width', '1'), font_size, 1) * width)
        pattern_height = (
            size(pattern.attrib.pop('height', '1'), font_size, 1) * height)
        if 'viewBox' not in pattern:
            pattern.attrib['width'] = pattern_width
            pattern.attrib['height'] = pattern_height
            if pattern.get('patternContentUnits') == 'objectBoundingBox':
                pattern.attrib['transform'] = f'scale({width}, {height})'

    # Fail if pattern has an invalid size
    if pattern_width == 0 or pattern_height == 0:
        return False

    if 'patternTransform' in pattern.attrib:
        transform_matrix = transform(
            pattern.get('patternTransform'), font_size, svg.inner_diagonal)
        matrix = transform_matrix @ matrix

    matrix = matrix @ svg.stream.ctm
    stream_pattern = svg.stream.add_pattern(
        0, 0, pattern_width, pattern_height, pattern_width, pattern_height,
        matrix)
    stream_pattern.set_alpha(opacity)

    group = stream_pattern.add_group(0, 0, pattern_width, pattern_height)
    Pattern(pattern, svg).draw(
        group, pattern_width, pattern_height, svg.base_url,
        svg.url_fetcher, svg.context)
    stream_pattern.draw_x_object(group.id)
    svg.stream.color_space('Pattern', stroke=stroke)
    svg.stream.set_color_special(stream_pattern.id, stroke=stroke)
    return True


def apply_filters(svg, node, filter_node, font_size):
    """Apply filters defined in given filter node."""
    for child in filter_node:
        if child.tag == 'feOffset':
            if filter_node.get('primitiveUnits') == 'objectBoundingBox':
                bounding_box = svg.calculate_bounding_box(node, font_size)
                if is_valid_bounding_box(bounding_box):
                    _, _, width, height = bounding_box
                    dx = size(child.get('dx', 0), font_size, 1) * width
                    dy = size(child.get('dy', 0), font_size, 1) * height
                else:
                    dx = dy = 0
            else:
                dx, dy = svg.point(
                    child.get('dx', 0), child.get('dy', 0), font_size)
            svg.stream.transform(e=dx, f=dy)
        elif child.tag == 'feBlend':
            mode = child.get('mode', 'normal')
            mode = mode.replace('-', ' ').title().replace(' ', '')
            svg.stream.set_blend_mode(mode)


def paint_mask(svg, node, mask, font_size):
    """Apply given mask node."""
    mask._etree_node.tag = 'g'

    if mask.get('maskUnits') == 'userSpaceOnUse':
        width_ref, height_ref = svg.inner_width, svg.inner_height
    else:
        width_ref, height_ref = svg.point(
            node.get('width'), node.get('height'), font_size)

    mask.attrib['x'] = size(mask.get('x', '-10%'), font_size, width_ref)
    mask.attrib['y'] = size(mask.get('y', '-10%'), font_size, height_ref)
    mask.attrib['height'] = size(
        mask.get('height', '120%'), font_size, height_ref)
    mask.attrib['width'] = size(
        mask.get('width', '120%'), font_size, width_ref)

    if mask.get('maskUnits') == 'userSpaceOnUse':
        x, y = mask.get('x'), mask.get('y')
        width, height = mask.get('width'), mask.get('height')
        mask.attrib['viewBox'] = f'{x} {y} {width} {height}'
    else:
        x, y = 0, 0
        width, height = width_ref, height_ref

    svg_stream = svg.stream
    svg.stream = svg.stream.set_alpha_state(x, y, width, height)
    svg.draw_node(mask, font_size)
    svg.stream = svg_stream


def clip_path(svg, node, font_size):
    """Store a clip path definition."""
    if 'id' in node.attrib:
        svg.paths[node.attrib['id']] = node
