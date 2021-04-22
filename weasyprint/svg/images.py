"""
    weasyprint.svg.image
    --------------------

    Draw image and svg tags.

"""

from urllib.parse import urljoin

from .utils import preserve_ratio


def svg(svg, node, font_size):
    """Draw svg tags."""
    if svg.tree == node:
        width, height = svg.concrete_width, svg.concrete_height
    else:
        width, height = svg.point(
            node.get('width'), node.get('height'), font_size)
    scale_x, scale_y, translate_x, translate_y = preserve_ratio(
        svg, node, font_size, width, height)
    svg.stream.transform(scale_x, 0, 0, scale_y, translate_x, translate_y)


def image(svg, node, font_size):
    """Draw image tags."""
    base_url = node.get('{http://www.w3.org/XML/1998/namespace}base')
    url = urljoin(base_url or svg.url, node.get_href())
    image = svg.context.get_image_from_uri(url, forced_mime_type='image/*')
    if image is None:
        return
    width, height = svg.point(node.get('width'), node.get('height'), font_size)
    width = width or image._intrinsic_width
    height = height or image._intrinsic_height
    image.draw(svg.stream, width, height, image_rendering='auto')
