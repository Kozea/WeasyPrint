"""
    weasyprint.layout.replaced
    --------------------------

    Layout for images and other replaced elements.
    http://dev.w3.org/csswg/css-images-3/#sizing

    :copyright: Copyright 2011-2018 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""


def image_marker_layout(box):
    """Layout the :class:`boxes.ImageMarkerBox` ``box``.

    :class:`boxes.ImageMarkerBox` objects are :class:`boxes.ReplacedBox`
    objects, but their used size is computed differently.

    """
    image = box.replacement
    one_em = box.style['font_size']
    iwidth, iheight = image.get_intrinsic_size(
        box.style['image_resolution'], one_em)
    box.width, box.height = default_image_sizing(
        iwidth, iheight, image.intrinsic_ratio, box.width, box.height,
        default_width=one_em, default_height=one_em)


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
