"""
    weasyprint.svg.image
    --------------------

    Draw image and svg tags.

"""

from urllib.parse import urljoin

from .utils import preserve_ratio


def svg(svg, node, font_size):
    """Draw svg tags."""
    scale_x, scale_y, translate_x, translate_y = preserve_ratio(
        svg, node, font_size, svg.concrete_width, svg.concrete_height)
    svg.stream.transform(scale_x, 0, 0, scale_y, translate_x, translate_y)


def image(svg, node, font_size):
    """Draw image tags."""
    from ..images import get_image_from_uri

    base_url = node.get('{http://www.w3.org/XML/1998/namespace}base')
    url = urljoin(base_url or svg.url, node.get_href())
    # TODO: handle cache, optimizations, image_rendering
    image = get_image_from_uri(
        {}, svg.url_fetcher, optimize_images=True, url=url,
        forced_mime_type='image/*')
    width, height = svg.point(node.get('width'), node.get('height'), font_size)
    image.draw(svg.stream, width, height, image_rendering='auto')
