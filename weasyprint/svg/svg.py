"""
    weasyprint.svg.svg
    ------------------

    Render svg tags.

"""


def svg(svg, node, font_size):
    viewbox = svg.get_viewbox()
    if viewbox:
        width, height = svg.point(
            node.get('width'), node.get('height'), font_size)
        scale_x = width / viewbox[2]
        scale_y = height / viewbox[3]
        svg.stream.transform(scale_x, 0, 0, scale_y, 0, 0)
