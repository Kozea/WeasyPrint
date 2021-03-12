"""
    weasyprint.svg.svg
    ------------------

    Render svg tags.

"""

from .utils import size


def svg(svg, node, font_size):
    viewbox = svg.get_viewbox()
    if viewbox:
        width = size(node.get('width'), font_size, svg.concrete_width)
        height = size(node.get('height'), font_size, svg.concrete_height)
        scale_x = width / viewbox[2]
        scale_y = height / viewbox[3]
        svg.stream.transform(scale_x, 0, 0, scale_y, 0, 0)
