from urllib.parse import urljoin


def image(svg, node, font_size):
    from ..images import get_image_from_uri

    base_url = node.get('{http://www.w3.org/XML/1998/namespace}base')
    url = urljoin(base_url or svg.url, node.get_href())
    # TODO: handle cache, optimizations, image_rendering
    image = get_image_from_uri(
        {}, svg.url_fetcher, optimize_images=True, url=url,
        forced_mime_type='image/*')
    width, height = svg.point(node.get('width'), node.get('height'), font_size)
    image.draw(svg.stream, width, height, image_rendering='auto')
