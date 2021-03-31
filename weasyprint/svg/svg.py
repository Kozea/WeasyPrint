"""
    weasyprint.svg.svg
    ------------------

    Render svg tags.

"""

from .utils import preserve_ratio


def svg(svg, node, font_size):
    scale_x, scale_y, translate_x, translate_y = preserve_ratio(
        svg, node, font_size, svg.concrete_width, svg.concrete_height)
    svg.stream.transform(scale_x, 0, 0, scale_y, translate_x, translate_y)
