from .utils import parse_url


def marker(svg, node, font_size):
    svg.parse_def(node)


def use(svg, node, font_size):
    from . import SVG

    svg.stream.push_state()
    svg.stream.transform(
        1, 0, 0, 1, *svg.point(node.get('x'), node.get('y'), font_size))

    for attribute in ('x', 'y', 'viewBox', 'mask'):
        if attribute in node.attrib:
            del node.attrib[attribute]

    parsed_url = parse_url(node.get_href())
    if parsed_url.fragment and not parsed_url.path:
        tree = svg.tree.get_child(parsed_url.fragment)
    else:
        url = parsed_url.geturl()
        try:
            bytestring_svg = svg.url_fetcher(url)
            use_svg = SVG(bytestring_svg, url)
        except TypeError:
            svg.stream.restore()
            return
        else:
            use_svg.get_intrinsic_size(font_size)
            tree = use_svg.tree

    if tree.tag in ('svg', 'symbol'):
        # Explicitely specified
        # http://www.w3.org/TR/SVG11/struct.html#UseElement
        tree.tag = 'svg'
        if 'width' in node.attrib and 'height' in node.attrib:
            tree.attrib['width'] = node['width']
            tree.attrib['height'] = node['height']

    svg.draw_node(tree, font_size)
    svg.stream.pop_state()
