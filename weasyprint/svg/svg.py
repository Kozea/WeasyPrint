"""
    weasyprint.svg.svg
    ------------------

    Render svg tags.

"""

from .utils import preserve_ratio


def svg(svg, node, font_size):
    width, height = svg.get_intrinsic_size(font_size)
    width = width or svg.concrete_width
    height = height or svg.concrete_height
    scale_x, scale_y, translate_x, translate_y = preserve_ratio(
        svg, node, font_size, width, height)
    svg.stream.transform(scale_x, 0, 0, scale_y, translate_x, translate_y)
