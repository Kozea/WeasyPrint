"""PDF links and bookmarks management."""

import math

from .formatting_structure import boxes
from .layout.percent import percentage
from .logger import LOGGER
from .matrix import Matrix


def resolve_links(pages):
    """Resolve internal hyperlinks.

    Links to a missing anchor are removed with a warning.

    If multiple anchors have the same name, the first one is used.

    :returns:
        A generator yielding lists (one per page) like :attr:`Page.links`,
        except that ``target`` for internal hyperlinks is
        ``(page_number, x, y)`` instead of an anchor name.
        The page number is a 0-based index into the :attr:`pages` list,
        and ``x, y`` are in CSS pixels from the top-left of the page.

    """
    anchors = set()
    paged_anchors = []
    for i, page in enumerate(pages):
        paged_anchors.append([])
        for anchor_name, (point_x, point_y) in page.anchors.items():
            if anchor_name not in anchors:
                paged_anchors[-1].append((anchor_name, point_x, point_y))
                anchors.add(anchor_name)
    for page in pages:
        page_links = []
        for link in page.links:
            link_type, anchor_name, rectangle, _ = link
            if link_type == 'internal':
                if anchor_name not in anchors:
                    LOGGER.error(
                        'No anchor #%s for internal URI reference',
                        anchor_name)
                else:
                    page_links.append(
                        (link_type, anchor_name, rectangle, None))
            else:
                # External link
                page_links.append(link)
        yield page_links, paged_anchors.pop(0)


def rectangle_aabb(matrix, pos_x, pos_y, width, height):
    """Apply a transformation matrix to an axis-aligned rectangle.

    Return its axis-aligned bounding box as ``(x1, y1, x2, y2)``.

    """
    if not matrix:
        return pos_x, pos_y, pos_x + width, pos_y + height
    transform_point = matrix.transform_point
    x1, y1 = transform_point(pos_x, pos_y)
    x2, y2 = transform_point(pos_x + width, pos_y)
    x3, y3 = transform_point(pos_x, pos_y + height)
    x4, y4 = transform_point(pos_x + width, pos_y + height)
    box_x1 = min(x1, x2, x3, x4)
    box_y1 = min(y1, y2, y3, y4)
    box_x2 = max(x1, x2, x3, x4)
    box_y2 = max(y1, y2, y3, y4)
    return box_x1, box_y1, box_x2, box_y2


def gather_links_and_bookmarks(box, anchors, links, bookmarks,
                               parent_matrix=None):
    # Get box transformation matrix.
    # "Transforms apply to block-level and atomic inline-level elements,
    #  but do not apply to elements which may be split into
    #  multiple inline-level boxes."
    # http://www.w3.org/TR/css3-2d-transforms/#introduction
    if box.style['transform'] and not isinstance(box, boxes.InlineBox):
        border_width = box.border_width()
        border_height = box.border_height()
        origin_x, origin_y = box.style['transform_origin']
        offset_x = percentage(origin_x, border_width)
        offset_y = percentage(origin_y, border_height)
        origin_x = box.border_box_x() + offset_x
        origin_y = box.border_box_y() + offset_y

        matrix = Matrix(e=origin_x, f=origin_y)
        for name, args in box.style['transform']:
            a, b, c, d, e, f = 1, 0, 0, 1, 0, 0
            if name == 'scale':
                a, d = args
            elif name == 'rotate':
                a = d = math.cos(args)
                b = math.sin(args)
                c = -b
            elif name == 'translate':
                e = percentage(args[0], border_width)
                f = percentage(args[1], border_height)
            elif name == 'skew':
                b, c = math.tan(args[1]), math.tan(args[0])
            else:
                assert name == 'matrix'
                a, b, c, d, e, f = args
            matrix = Matrix(a, b, c, d, e, f) @ matrix
        box.transformation_matrix = (
            Matrix(e=-origin_x, f=-origin_y) @ matrix)
        if parent_matrix:
            matrix = box.transformation_matrix @ parent_matrix
        else:
            matrix = box.transformation_matrix
    else:
        matrix = parent_matrix

    bookmark_label = box.bookmark_label
    if box.style['bookmark_level'] == 'none':
        bookmark_level = None
    else:
        bookmark_level = box.style['bookmark_level']
    state = box.style['bookmark_state']
    link = box.style['link']
    anchor_name = box.style['anchor']
    has_bookmark = bookmark_label and bookmark_level
    # 'link' is inherited but redundant on text boxes
    has_link = link and not isinstance(box, (boxes.TextBox, boxes.LineBox))
    # In case of duplicate IDs, only the first is an anchor.
    has_anchor = anchor_name and anchor_name not in anchors

    if has_bookmark or has_link or has_anchor:
        pos_x, pos_y, width, height = box.hit_area()
        if has_link:
            token_type, link = link
            assert token_type == 'url'
            link_type, target = link
            assert isinstance(target, str)
            if link_type == 'external' and box.is_attachment:
                link_type = 'attachment'
            rectangle = rectangle_aabb(matrix, pos_x, pos_y, width, height)
            link = (link_type, target, rectangle, box.download_name)
            links.append(link)
        if matrix and (has_bookmark or has_anchor):
            pos_x, pos_y = matrix.transform_point(pos_x, pos_y)
        if has_bookmark:
            bookmark = (bookmark_level, bookmark_label, (pos_x, pos_y), state)
            bookmarks.append(bookmark)
        if has_anchor:
            anchors[anchor_name] = pos_x, pos_y

    for child in box.all_children():
        gather_links_and_bookmarks(child, anchors, links, bookmarks, matrix)


def make_page_bookmark_tree(page, skipped_levels, last_by_depth,
                            previous_level, page_number, matrix):
    """Make a tree of all bookmarks in a given page."""
    for level, label, (point_x, point_y), state in page.bookmarks:
        if level > previous_level:
            # Example: if the previous bookmark is a <h2>, the next
            # depth "should" be for <h3>. If now we get a <h6> we’re
            # skipping two levels: append 6 - 3 - 1 = 2
            skipped_levels.append(level - previous_level - 1)
        else:
            temp = level
            while temp < previous_level:
                temp += 1 + skipped_levels.pop()
            if temp > previous_level:
                # We remove too many "skips", add some back:
                skipped_levels.append(temp - previous_level - 1)

        previous_level = level
        depth = level - sum(skipped_levels)
        assert depth == len(skipped_levels)
        assert depth >= 1

        children = []
        point_x, point_y = matrix.transform_point(point_x, point_y)
        subtree = (label, (page_number, point_x, point_y), children, state)
        last_by_depth[depth - 1].append(subtree)
        del last_by_depth[depth:]
        last_by_depth.append(children)
    return previous_level
