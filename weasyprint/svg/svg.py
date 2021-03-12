"""
    weasyprint.svg.svg
    ------------------

    Render svg tags.

"""

from .utils import size


def svg(svg, node, font_size):
    viewbox = svg.get_viewbox()
    scale_x = (
        size(node.get('width'), font_size, svg.concrete_width) / viewbox[2])
    scale_y = (
        size(node.get('height'), font_size, svg.concrete_height) / viewbox[3])
    svg.stream.transform(scale_x, 0, 0, scale_y, 0, 0)
