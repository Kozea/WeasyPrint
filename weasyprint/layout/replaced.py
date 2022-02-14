"""Layout for images and other replaced elements.

See http://dev.w3.org/csswg/css-images-3/#sizing

"""

from .min_max import handle_min_max_height, handle_min_max_width
from .percent import percentage


def default_image_sizing(intrinsic_width, intrinsic_height, intrinsic_ratio,
                         specified_width, specified_height,
                         default_width, default_height):
    """Default sizing algorithm for the concrete object size.

    Return a ``(concrete_width, concrete_height)`` tuple.

    See http://dev.w3.org/csswg/css-images-3/#default-sizing

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


def contain_constraint_image_sizing(constraint_width, constraint_height,
                                    intrinsic_ratio):
    """Contain constraint sizing algorithm for the concrete object size.

    Return a ``(concrete_width, concrete_height)`` tuple.

    See http://dev.w3.org/csswg/css-images-3/#contain-constraint

    """
    return _constraint_image_sizing(
        constraint_width, constraint_height, intrinsic_ratio, cover=False)


def cover_constraint_image_sizing(constraint_width, constraint_height,
                                  intrinsic_ratio):
    """Cover constraint sizing algorithm for the concrete object size.

    Return a ``(concrete_width, concrete_height)`` tuple.

    See http://dev.w3.org/csswg/css-images-3/#cover-constraint

    """
    return _constraint_image_sizing(
        constraint_width, constraint_height, intrinsic_ratio, cover=True)


def _constraint_image_sizing(constraint_width, constraint_height,
                             intrinsic_ratio, cover):
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
    intrinsic_width, intrinsic_height, intrinsic_ratio = (
        image.get_intrinsic_size(
            box.style['image_resolution'], box.style['font_size']))
    if None in (intrinsic_width, intrinsic_height):
        intrinsic_width, intrinsic_height = contain_constraint_image_sizing(
            box.width, box.height, intrinsic_ratio)

    if object_fit == 'fill':
        draw_width, draw_height = box.width, box.height
    else:
        if object_fit == 'contain' or object_fit == 'scale-down':
            draw_width, draw_height = contain_constraint_image_sizing(
                box.width, box.height, intrinsic_ratio)
        elif object_fit == 'cover':
            draw_width, draw_height = cover_constraint_image_sizing(
                box.width, box.height, intrinsic_ratio)
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


@handle_min_max_width
def replaced_box_width(box, containing_block):
    """Set the used width for replaced boxes."""
    from .block import block_level_width

    width, height, ratio = box.replacement.get_intrinsic_size(
        box.style['image_resolution'], box.style['font_size'])

    # This algorithm simply follows the different points of the specification:
    # http://www.w3.org/TR/CSS21/visudet.html#inline-replaced-width
    if box.height == 'auto' and box.width == 'auto':
        if width is not None:
            # Point #1
            box.width = width
        elif ratio is not None:
            if height is not None:
                # Point #2 first part
                box.width = height * ratio
            else:
                # Point #3
                block_level_width(box, containing_block)

    if box.width == 'auto':
        if ratio is not None:
            # Point #2 second part
            box.width = box.height * ratio
        elif width is not None:
            # Point #4
            box.width = width
        else:
            # Point #5
            # It's pretty useless to rely on device size to set width.
            box.width = 300


@handle_min_max_height
def replaced_box_height(box):
    """Compute and set the used height for replaced boxes."""
    # http://www.w3.org/TR/CSS21/visudet.html#inline-replaced-height
    width, height, ratio = box.replacement.get_intrinsic_size(
        box.style['image_resolution'], box.style['font_size'])

    # Test 'auto' on the computed width, not the used width
    if box.height == 'auto' and box.width == 'auto':
        box.height = height
    elif box.height == 'auto' and ratio:
        box.height = box.width / ratio

    if box.height == 'auto' and box.width == 'auto' and height is not None:
        box.height = height
    elif ratio is not None and box.height == 'auto':
        box.height = box.width / ratio
    elif box.height == 'auto' and height is not None:
        box.height = height
    elif box.height == 'auto':
        # It's pretty useless to rely on device size to set width.
        box.height = 150


def inline_replaced_box_layout(box, containing_block):
    """Lay out an inline :class:`boxes.ReplacedBox` ``box``."""
    for side in ['top', 'right', 'bottom', 'left']:
        if getattr(box, f'margin_{side}') == 'auto':
            setattr(box, f'margin_{side}', 0)
    inline_replaced_box_width_height(box, containing_block)


def inline_replaced_box_width_height(box, containing_block):
    if box.style['width'] == 'auto' and box.style['height'] == 'auto':
        replaced_box_width.without_min_max(box, containing_block)
        replaced_box_height.without_min_max(box)
        min_max_auto_replaced(box)
    else:
        replaced_box_width(box, containing_block)
        replaced_box_height(box)


def min_max_auto_replaced(box):
    """Resolve min/max constraints on replaced elements with 'auto' sizes."""
    width = box.width
    height = box.height
    min_width = box.min_width
    min_height = box.min_height
    max_width = max(min_width, box.max_width)
    max_height = max(min_height, box.max_height)

    # (violation_width, violation_height)
    violations = (
        'min' if width < min_width else 'max' if width > max_width else '',
        'min' if height < min_height else 'max' if height > max_height else '')

    # Work around divisions by zero. These are pathological cases anyway.
    # TODO: is there a cleaner way?
    if width == 0:
        width = 1e-6
    if height == 0:
        height = 1e-6

    # ('', ''): nothing to do
    if violations == ('max', ''):
        box.width = max_width
        box.height = max(max_width * height / width, min_height)
    elif violations == ('min', ''):
        box.width = min_width
        box.height = min(min_width * height / width, max_height)
    elif violations == ('', 'max'):
        box.width = max(max_height * width / height, min_width)
        box.height = max_height
    elif violations == ('', 'min'):
        box.width = min(min_height * width / height, max_width)
        box.height = min_height
    elif violations == ('max', 'max'):
        if max_width / width <= max_height / height:
            box.width = max_width
            box.height = max(min_height, max_width * height / width)
        else:
            box.width = max(min_width, max_height * width / height)
            box.height = max_height
    elif violations == ('min', 'min'):
        if min_width / width <= min_height / height:
            box.width = min(max_width, min_height * width / height)
            box.height = min_height
        else:
            box.width = min_width
            box.height = min(max_height, min_width * height / width)
    elif violations == ('min', 'max'):
        box.width = min_width
        box.height = max_height
    elif violations == ('max', 'min'):
        box.width = max_width
        box.height = min_height


def block_replaced_box_layout(context, box, containing_block):
    """Lay out the block :class:`boxes.ReplacedBox` ``box``."""
    from .block import block_level_width
    from .float import avoid_collisions

    box = box.copy()
    if box.style['width'] == 'auto' and box.style['height'] == 'auto':
        computed_margins = box.margin_left, box.margin_right
        block_replaced_width.without_min_max(
            box, containing_block)
        replaced_box_height.without_min_max(box)
        min_max_auto_replaced(box)
        box.margin_left, box.margin_right = computed_margins
        block_level_width.without_min_max(box, containing_block)
    else:
        block_replaced_width(box, containing_block)
        replaced_box_height(box)

    # Don't collide with floats
    # http://www.w3.org/TR/CSS21/visuren.html#floats
    box.position_x, box.position_y, _ = avoid_collisions(
        context, box, containing_block, outer=False)
    resume_at = None
    next_page = {'break': 'any', 'page': None}
    adjoining_margins = []
    collapsing_through = False
    return box, resume_at, next_page, adjoining_margins, collapsing_through


@handle_min_max_width
def block_replaced_width(box, containing_block):
    from .block import block_level_width

    # http://www.w3.org/TR/CSS21/visudet.html#block-replaced-width
    replaced_box_width.without_min_max(box, containing_block)
    block_level_width.without_min_max(box, containing_block)
