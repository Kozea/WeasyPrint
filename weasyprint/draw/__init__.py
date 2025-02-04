"""Take an "after layout" box tree and draw it onto a pydyf stream."""

import operator
from math import floor
from xml.etree import ElementTree

from ..formatting_structure import boxes
from ..images import SVGImage
from ..layout import replaced
from ..layout.background import BackgroundLayer
from ..matrix import Matrix
from ..stacking import StackingContext
from .border import draw_border, draw_line, draw_outline, rounded_box, set_mask_border
from .color import styled_color
from .stack import stacked
from .text import draw_text


def draw_page(page, stream):
    """Draw the given PageBox."""
    marks = page.style['marks']
    stacking_context = StackingContext.from_page(page)
    draw_background(
        stream, stacking_context.box.background, clip_box=False, bleed=page.bleed,
        marks=marks)
    set_mask_border(stream, page)
    draw_background(stream, page.canvas_background, clip_box=False)
    draw_border(stream, page)
    draw_stacking_context(stream, stacking_context)


def draw_stacking_context(stream, stacking_context):
    """Draw a ``stacking_context`` on ``stream``."""
    # See https://www.w3.org/TR/CSS2/zindex.html.
    with stacked(stream):
        box = stacking_context.box

        stream.begin_marked_content(box, mcid=True)

        # Apply the viewport_overflow to the html box, see #35.
        if box.is_for_root_element and (
                stacking_context.page.style['overflow'] != 'visible'):
            rounded_box(stream, stacking_context.page.rounded_padding_box())
            stream.clip()
            stream.end()

        if box.is_absolutely_positioned() and box.style['clip']:
            top, right, bottom, left = box.style['clip']
            if top == 'auto':
                top = 0
            if right == 'auto':
                right = 0
            if bottom == 'auto':
                bottom = box.border_height()
            if left == 'auto':
                left = box.border_width()
            stream.rectangle(
                box.border_box_x() + right, box.border_box_y() + top,
                left - right, bottom - top)
            stream.clip()
            stream.end()

        if box.style['opacity'] < 1:
            original_stream = stream
            stream = stream.add_group(*stream.page_rectangle)

        if box.transformation_matrix:
            if box.transformation_matrix.determinant:
                stream.transform(*box.transformation_matrix.values)
            else:
                stream.end_marked_content()
                return

        # Point 1 is done in draw_page.

        # Point 2.
        if isinstance(box, (boxes.BlockBox, boxes.MarginBox,
                            boxes.InlineBlockBox, boxes.TableCellBox,
                            boxes.FlexContainerBox, boxes.ReplacedBox)):
            set_mask_border(stream, box)
            # The canvas background was removed by layout_backgrounds
            draw_background(stream, box.background)
            draw_border(stream, box)

        with stacked(stream):
            # Dont clip the page box, see #35.
            clip = (
                box.style['overflow'] != 'visible' and
                not isinstance(box, boxes.PageBox))
            if clip:
                # Only clip the content and the children:
                # - the background is already clipped,
                # - the border must *not* be clipped.
                rounded_box(stream, box.rounded_padding_box())
                stream.clip()
                stream.end()

            # Point 3.
            for child_context in stacking_context.negative_z_contexts:
                draw_stacking_context(stream, child_context)

            # Point 4.
            for block in stacking_context.block_level_boxes:
                set_mask_border(stream, block)

                if isinstance(block, boxes.TableBox):
                    draw_table(stream, block)
                else:
                    draw_background(stream, block.background)
                    draw_border(stream, block)

            # Point 5.
            for child_context in stacking_context.float_contexts:
                draw_stacking_context(stream, child_context)

            # Point 6.
            if isinstance(box, boxes.InlineBox):
                draw_inline_level(stream, stacking_context.page, box)

            # Point 7.
            for block in (box, *stacking_context.blocks_and_cells):
                if isinstance(block, boxes.ReplacedBox):
                    draw_replacedbox(stream, block)
                elif block.children:
                    if block != box:
                        stream.begin_marked_content(block, mcid=True)
                    if isinstance(block.children[-1], boxes.LineBox):
                        for child in block.children:
                            draw_inline_level(stream, stacking_context.page, child)
                    if block != box:
                        stream.end_marked_content()

            # Point 8.
            for child_context in stacking_context.zero_z_contexts:
                draw_stacking_context(stream, child_context)

            # Point 9.
            for child_context in stacking_context.positive_z_contexts:
                draw_stacking_context(stream, child_context)

        # Point 10.
        draw_outline(stream, box)

        if box.style['opacity'] < 1:
            group_id = stream.id
            stream = original_stream
            with stacked(stream):
                stream.set_alpha(box.style['opacity'], stroke=True, fill=True)
                stream.draw_x_object(group_id)

        stream.end_marked_content()


def draw_background(stream, bg, clip_box=True, bleed=None, marks=()):
    """Draw the background color and image to a ``pdf.stream.Stream``.

    If ``clip_box`` is set to ``False``, the background is not clipped to the
    border box of the background, but only to the painting area.

    """
    if bg is None:
        return

    with stacked(stream):
        if clip_box:
            for box in bg.layers[-1].clipped_boxes:
                rounded_box(stream, box)
            stream.clip()
            stream.end()

        # Draw background color.
        if bg.color.alpha > 0:
            with stacked(stream):
                stream.set_color(bg.color)
                painting_area = bg.layers[-1].painting_area
                stream.rectangle(*painting_area)
                stream.clip()
                stream.end()
                stream.rectangle(*painting_area)
                stream.fill()

        # Draw crop marks and crosses.
        if bleed and marks:
            x, y, width, height = bg.layers[-1].painting_area
            half_bleed = {key: value * 0.5 for key, value in bleed.items()}
            svg = f'''
              <svg height="{height}" width="{width}"
                   fill="transparent" stroke="black" stroke-width="1"
                   xmlns="http://www.w3.org/2000/svg">
            '''
            if 'crop' in marks:
                svg += f'''
                  <path d="M0,{bleed['top']} h{half_bleed['left']}" />
                  <path d="M0,{bleed['top']} h{half_bleed['right']}"
                        transform="translate({width},0) scale(-1,1)" />
                  <path d="M0,{bleed['bottom']} h{half_bleed['right']}"
                        transform="translate({width},{height}) scale(-1,-1)" />
                  <path d="M0,{bleed['bottom']} h{half_bleed['left']}"
                        transform="translate(0,{height}) scale(1,-1)" />
                  <path d="M{bleed['left']},0 v{half_bleed['top']}" />
                  <path d="M{bleed['right']},0 v{half_bleed['bottom']}"
                        transform="translate({width},{height}) scale(-1,-1)" />
                  <path d="M{bleed['left']},0 v{half_bleed['bottom']}"
                        transform="translate(0,{height}) scale(1,-1)" />
                  <path d="M{bleed['right']},0 v{half_bleed['top']}"
                        transform="translate({width},0) scale(-1,1)" />
                '''
            if 'cross' in marks:
                svg += f'''
                  <circle r="{half_bleed['top']}" transform="scale(0.5)
                     translate({width},{half_bleed['top']}) scale(0.5)" />
                  <path transform="scale(0.5) translate({width},0)" d="
                    M-{half_bleed['top']},{half_bleed['top']} h{bleed['top']}
                    M0,0 v{bleed['top']}" />
                  <circle r="{half_bleed['bottom']}" transform="
                    translate(0,{height}) scale(0.5)
                    translate({width},-{half_bleed['bottom']}) scale(0.5)" />
                  <path d="M-{half_bleed['bottom']},-{half_bleed['bottom']}
                    h{bleed['bottom']} M0,0 v-{bleed['bottom']}" transform="
                    translate(0,{height}) scale(0.5) translate({width},0)" />
                  <circle r="{half_bleed['left']}" transform="scale(0.5)
                    translate({half_bleed['left']},{height}) scale(0.5)" />
                  <path d="M{half_bleed['left']},-{half_bleed['left']}
                    v{bleed['left']} M0,0 h{bleed['left']}"
                    transform="scale(0.5) translate(0,{height})" />
                  <circle r="{half_bleed['right']}" transform="
                    translate({width},0) scale(0.5)
                    translate(-{half_bleed['right']},{height}) scale(0.5)" />
                  <path d="M-{half_bleed['right']},-{half_bleed['right']}
                    v{bleed['right']} M0,0 h-{bleed['right']}" transform="
                    translate({width},0) scale(0.5) translate(0,{height})" />
                '''
            svg += '</svg>'
            tree = ElementTree.fromstring(svg)
            image = SVGImage(tree, None, None, stream)
            # Painting area is the PDF media box
            size = (width, height)
            position = (x, y)
            repeat = ('no-repeat', 'no-repeat')
            unbounded = True
            painting_area = position + size
            positioning_area = (0, 0, width, height)
            clipped_boxes = []
            layer = BackgroundLayer(
                image, size, position, repeat, unbounded, painting_area,
                positioning_area, clipped_boxes)
            bg.layers.insert(0, layer)
        # Paint in reversed order: first layer is "closest" to the viewer.
        for layer in reversed(bg.layers):
            draw_background_image(stream, layer, bg.image_rendering)


def draw_background_image(stream, layer, image_rendering):
    if layer.image is None or 0 in layer.size:
        return

    painting_x, painting_y, painting_width, painting_height = layer.painting_area
    positioning_x, positioning_y, positioning_width, positioning_height = (
        layer.positioning_area)
    position_x, position_y = layer.position
    repeat_x, repeat_y = layer.repeat
    image_width, image_height = layer.size

    if repeat_x == 'no-repeat' and repeat_y == 'no-repeat':
        # We don't use a pattern when we don't need to because some viewers
        # (e.g., Preview on Mac) introduce unnecessary pixelation when vector
        # images are used in patterns.
        if not layer.unbounded:
            stream.rectangle(painting_x, painting_y, painting_width,
                             painting_height)
            stream.clip()
            stream.end()
        # Put the image in a group so that masking outside the image and
        # masking within the image don't conflict.
        group = stream.add_group(*stream.page_rectangle)
        group.transform(e=position_x + positioning_x,
                         f=position_y + positioning_y)
        layer.image.draw(group, image_width, image_height, image_rendering)
        stream.draw_x_object(group.id)
        return

    if repeat_x == 'no-repeat':
        # We want at least the whole image_width drawn on sub_surface, but we
        # want to be sure it will not be repeated on the painting_width. We
        # double the painting width to ensure viewers don't incorrectly bleed
        # the edge of the pattern into the painting area. (See #1539.)
        repeat_width = max(image_width, 2 * painting_width)
    elif repeat_x in ('repeat', 'round'):
        # We repeat the image each image_width.
        repeat_width = image_width
    else:
        assert repeat_x == 'space'
        n_repeats = floor(positioning_width / image_width)
        if n_repeats >= 2:
            # The repeat width is the whole positioning width with one image
            # removed, divided by (the number of repeated images - 1). This
            # way, we get the width of one image + one space. We ignore
            # background-position for this dimension.
            repeat_width = (positioning_width - image_width) / (n_repeats - 1)
            position_x = 0
        else:
            # We don't repeat the image.
            repeat_width = positioning_width

    # Comments above apply here too.
    if repeat_y == 'no-repeat':
        repeat_height = max(image_height, 2 * painting_height)
    elif repeat_y in ('repeat', 'round'):
        repeat_height = image_height
    else:
        assert repeat_y == 'space'
        n_repeats = floor(positioning_height / image_height)
        if n_repeats >= 2:
            repeat_height = (positioning_height - image_height) / (n_repeats - 1)
            position_y = 0
        else:
            repeat_height = positioning_height

    matrix = Matrix(e=position_x + positioning_x, f=position_y + positioning_y)
    matrix @= stream.ctm
    pattern = stream.add_pattern(
        0, 0, image_width, image_height, repeat_width, repeat_height, matrix)
    group = pattern.add_group(0, 0, repeat_width, repeat_height)

    with stacked(stream):
        layer.image.draw(group, image_width, image_height, image_rendering)
        pattern.draw_x_object(group.id)
        stream.set_color_space('Pattern')
        stream.set_color_special(pattern.id)
        if layer.unbounded:
            x1, y1, x2, y2 = stream.page_rectangle
            stream.rectangle(x1, y1, x2 - x1, y2 - y1)
        else:
            stream.rectangle(painting_x, painting_y, painting_width, painting_height)
        stream.fill()


def draw_table(stream, table):
    # Draw backgrounds.
    draw_background(stream, table.background)
    for column_group in table.column_groups:
        draw_background(stream, column_group.background)
        for column in column_group.children:
            draw_background(stream, column.background)
    for row_group in table.children:
        draw_background(stream, row_group.background)
        for row in row_group.children:
            draw_background(stream, row.background)
            for cell in row.children:
                draw_cell_background = (
                    table.style['border_collapse'] == 'collapse' or
                    cell.style['empty_cells'] == 'show' or
                    not cell.empty)
                if draw_cell_background:
                    draw_background(stream, cell.background)

    # Draw borders.
    if table.style['border_collapse'] == 'collapse':
        return draw_collapsed_borders(stream, table)
    draw_border(stream, table)
    for row_group in table.children:
        for row in row_group.children:
            for cell in row.children:
                if cell.style['empty_cells'] == 'show' or not cell.empty:
                    draw_border(stream, cell)


def draw_collapsed_borders(stream, table):
    """Draw borders of table cells when they collapse."""
    row_heights = [
        row.height for row_group in table.children
        for row in row_group.children]
    column_widths = table.column_widths
    if not (row_heights and column_widths):
        # One of the list is empty: don’t bother with empty tables.
        return
    row_positions = [
        row.position_y for row_group in table.children
        for row in row_group.children]
    column_positions = list(table.column_positions)
    grid_height = len(row_heights)
    grid_width = len(column_widths)
    assert grid_width == len(column_positions)
    vertical_borders, horizontal_borders = table.collapsed_border_grid
    # Add the end of the last column.
    column_positions.append(column_positions[-1] + column_widths[-1])
    # Add the end of the last row.
    row_positions.append(row_positions[-1] + row_heights[-1])
    if table.children[0].is_header:
        header_rows = len(table.children[0].children)
    else:
        header_rows = 0
    if table.children[-1].is_footer:
        footer_rows = len(table.children[-1].children)
    else:
        footer_rows = 0
    skipped_rows = table.skipped_rows
    if skipped_rows:
        body_rows_offset = skipped_rows - header_rows
    else:
        body_rows_offset = 0
    original_grid_height = len(vertical_borders)
    footer_rows_offset = original_grid_height - grid_height

    def row_number(y, horizontal):
        # Examples in comments for 2 headers rows, 5 body rows, 3 footer rows.
        if header_rows and y < header_rows + int(horizontal):
            # Row in header: y < 2 for vertical, y < 3 for horizontal.
            return y
        elif footer_rows and y >= grid_height - footer_rows - int(horizontal):
            # Row in footer: y >= 7 for vertical, y >= 6 for horizontal.
            return y + footer_rows_offset
        else:
            # Row in body: 2 >= y > 7 for vertical, 3 >= y > 6 for horizontal.
            return y + body_rows_offset

    segments = []

    def half_max_width(border_list, yx_pairs, vertical=True):
        result = 0
        for y, x in yx_pairs:
            if vertical:
                inside = 0 <= y < grid_height and 0 <= x <= grid_width
            else:
                inside = 0 <= y <= grid_height and 0 <= x < grid_width
            if inside:
                yy = row_number(y, horizontal=not vertical)
                _, (_, width, _) = border_list[yy][x]
                result = max(result, width)
        return result / 2

    def add_vertical(x, y):
        yy = row_number(y, horizontal=False)
        score, (style, width, color) = vertical_borders[yy][x]
        if width == 0 or color.alpha == 0:
            return
        pos_x = column_positions[x]
        pos_y1 = row_positions[y]
        if y != 0 or not table.skip_cell_border_top:
            pos_y1 -= half_max_width(
                horizontal_borders, [(y, x - 1), (y, x)], vertical=False)
        pos_y2 = row_positions[y + 1]
        if y != grid_height - 1 or not table.skip_cell_border_bottom:
            pos_y2 += half_max_width(
                horizontal_borders, [(y + 1, x - 1), (y + 1, x)], vertical=False)
        segments.append((
            score, style, width, color, 'left', (pos_x, pos_y1, 0, pos_y2 - pos_y1)))

    def add_horizontal(x, y):
        if y == 0 and table.skip_cell_border_top:
            return
        if y == grid_height and table.skip_cell_border_bottom:
            return
        yy = row_number(y, horizontal=True)
        score, (style, width, color) = horizontal_borders[yy][x]
        if width == 0 or color.alpha == 0:
            return
        pos_y = row_positions[y]
        shift_before = half_max_width(vertical_borders, [(y - 1, x), (y, x)])
        shift_after = half_max_width(vertical_borders, [(y - 1, x + 1), (y, x + 1)])
        pos_x1 = column_positions[x] - shift_before
        pos_x2 = column_positions[x + 1] + shift_after
        segments.append((
            score, style, width, color, 'top', (pos_x1, pos_y, pos_x2 - pos_x1, 0)))

    for x in range(grid_width):
        add_horizontal(x, 0)
    for y in range(grid_height):
        add_vertical(0, y)
        for x in range(grid_width):
            add_vertical(x + 1, y)
            add_horizontal(x, y + 1)

    # Sort bigger scores last (painted later, on top).
    segments.sort(key=operator.itemgetter(0))

    for segment in segments:
        _, style, width, color, side, border_box = segment
        with stacked(stream):
            bx, by, bw, bh = border_box
            color = styled_color(style, color, side)
            draw_line(stream, bx, by, bx + bw, by + bh, width, style, color)


def draw_replacedbox(stream, box):
    """Draw the given :class:`boxes.ReplacedBox` to a ``pdf.stream.Stream``."""
    if box.style['visibility'] != 'visible' or not box.width or not box.height:
        return

    draw_width, draw_height, draw_x, draw_y = replaced.replacedbox_layout(box)
    if draw_width <= 0 or draw_height <= 0:
        return

    with stacked(stream):
        stream.set_alpha(1)
        stream.transform(e=draw_x, f=draw_y)
        with stacked(stream):
            # TODO: Use the real intrinsic size here, not affected by
            # 'image-resolution'?
            box.replacement.draw(
                stream, draw_width, draw_height, box.style['image_rendering'])


def draw_inline_level(stream, page, box, offset_x=0, text_overflow='clip',
                      block_ellipsis='none'):
    if isinstance(box, StackingContext):
        stacking_context = box
        allowed_boxes = (boxes.InlineBlockBox, boxes.InlineFlexBox, boxes.InlineGridBox)
        assert isinstance(stacking_context.box, allowed_boxes)
        draw_stacking_context(stream, stacking_context)
    else:
        set_mask_border(stream, box)
        draw_background(stream, box.background)
        draw_border(stream, box)
        if isinstance(box, (boxes.InlineBox, boxes.LineBox)):
            link_annotation = None
            if isinstance(box, boxes.LineBox):
                text_overflow = box.text_overflow
                block_ellipsis = box.block_ellipsis
            else:
                link_annotation = box.link_annotation
            ellipsis = 'none'
            if link_annotation:
                stream.begin_marked_content(box, mcid=True, tag='Link')
            for i, child in enumerate(box.children):
                if i == len(box.children) - 1:
                    # Last child
                    ellipsis = block_ellipsis
                if isinstance(child, StackingContext):
                    child_offset_x = offset_x
                else:
                    child_offset_x = offset_x + child.position_x - box.position_x
                if isinstance(child, boxes.TextBox):
                    draw_text(stream, child, child_offset_x, text_overflow, ellipsis)
                else:
                    draw_inline_level(
                        stream, page, child, child_offset_x, text_overflow, ellipsis)
            if link_annotation:
                stream.end_marked_content()
        elif isinstance(box, boxes.InlineReplacedBox):
            draw_replacedbox(stream, box)
        else:
            assert isinstance(box, boxes.TextBox)
            # Should only happen for list markers.
            draw_text(stream, box, offset_x, text_overflow)
