"""
    weasyprint.layout.replaced
    --------------------------

    Layout for images and other replaced elements.
    http://dev.w3.org/csswg/css-images-3/#sizing

"""

from .percentages import percentage


def default_image_sizing(intrinsic_width, intrinsic_height, intrinsic_ratio,
                         specified_width, specified_height,
                         default_width, default_height):
    """Default sizing algorithm for the concrete object size.
    http://dev.w3.org/csswg/css-images-3/#default-sizing

    Return a ``(concrete_width, concrete_height)`` tuple.

    """
    if specified_width == 'auto':
        specified_width = None
    if specified_height == 'auto':
        specified_height = None

    if specified_width is not None and specified_height is not None:
        return specified_width, specified_height
    elif specified_width is not None:
        return specified_width, (
            specified_width / intrinsic_ratio if intrinsic_ratio is not None
            else intrinsic_height if intrinsic_height is not None
            else default_height)
    elif specified_height is not None:
        return (
            specified_height * intrinsic_ratio if intrinsic_ratio is not None
            else intrinsic_width if intrinsic_width is not None
            else default_width
        ), specified_height
    else:
        if intrinsic_width is not None or intrinsic_height is not None:
            return default_image_sizing(
                intrinsic_width, intrinsic_height, intrinsic_ratio,
                intrinsic_width, intrinsic_height, default_width,
                default_height)
        else:
            return contain_constraint_image_sizing(
                default_width, default_height, intrinsic_ratio)


def contain_constraint_image_sizing(
        constraint_width, constraint_height, intrinsic_ratio):
    """Cover constraint sizing algorithm for the concrete object size.
    http://dev.w3.org/csswg/css-images-3/#contain-constraint

    Return a ``(concrete_width, concrete_height)`` tuple.

    """
    return _constraint_image_sizing(
        constraint_width, constraint_height, intrinsic_ratio, cover=False)


def cover_constraint_image_sizing(
        constraint_width, constraint_height, intrinsic_ratio):
    """Cover constraint sizing algorithm for the concrete object size.
    http://dev.w3.org/csswg/css-images-3/#cover-constraint

    Return a ``(concrete_width, concrete_height)`` tuple.

    """
    return _constraint_image_sizing(
        constraint_width, constraint_height, intrinsic_ratio, cover=True)


def _constraint_image_sizing(
        constraint_width, constraint_height, intrinsic_ratio, cover):
    if intrinsic_ratio is None:
        return constraint_width, constraint_height
    elif cover ^ (constraint_width > constraint_height * intrinsic_ratio):
        return constraint_height * intrinsic_ratio, constraint_height
    else:
        return constraint_width, constraint_width / intrinsic_ratio


def replacedbox_layout(box):
    # TODO: respect box-sizing ?
    object_fit = box.style['object_fit']
    position = box.style['object_position']

    image = box.replacement
    intrinsic_width, intrinsic_height = image.get_intrinsic_size(
        box.style['image_resolution'], box.style['font_size'])
    if None in (intrinsic_width, intrinsic_height):
        intrinsic_width, intrinsic_height = contain_constraint_image_sizing(
            box.width, box.height, box.replacement.intrinsic_ratio)

    if object_fit == 'fill':
        draw_width, draw_height = box.width, box.height
    else:
        if object_fit == 'contain' or object_fit == 'scale-down':
            draw_width, draw_height = contain_constraint_image_sizing(
                box.width, box.height, box.replacement.intrinsic_ratio)
        elif object_fit == 'cover':
            draw_width, draw_height = cover_constraint_image_sizing(
                box.width, box.height, box.replacement.intrinsic_ratio)
        else:
            assert object_fit == 'none', object_fit
            draw_width, draw_height = intrinsic_width, intrinsic_height

        if object_fit == 'scale-down':
            draw_width = min(draw_width, intrinsic_width)
            draw_height = min(draw_height, intrinsic_height)

    origin_x, position_x, origin_y, position_y = position[0]
    ref_x = box.width - draw_width
    ref_y = box.height - draw_height

    position_x = percentage(position_x, ref_x)
    position_y = percentage(position_y, ref_y)
    if origin_x == 'right':
        position_x = ref_x - position_x
    if origin_y == 'bottom':
        position_y = ref_y - position_y

    position_x += box.content_box_x()
    position_y += box.content_box_y()

    return draw_width, draw_height, position_x, position_y
