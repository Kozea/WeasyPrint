from __future__ import division

import functools
from io import BytesIO
import cairo



BOX_ATTRIBUTES = '''
    position_x position_y
    width height
    margin_top margin_bottom margin_left margin_right
    padding_top padding_bottom padding_left padding_right
    border_top_width border_bottom_width border_left_width border_right_width
'''.split()

PAGE_BOX_ATTRIBUTES = BOX_ATTRIBUTES + ['outer_width', 'outer_height']


def serialize(document):
    """
    Serialize a WeasyPrint Document object to JSON-compatible data types
    for in-browser rendering.
    """
    return {'pages': [
        serialize_page_box(document, page)
        for page in document.pages]}


def serialize_box(document, box, attributes=BOX_ATTRIBUTES):
    rv = {name: getattr(box, name) for name in attributes}
    rv['style'] = serialize_style(document, box.style)

    children = getattr(box, 'children', None)
    if children is not None:
        rv['children'] = [serialize_box(document, child) for child in children]

    marker = getattr(box, 'outside_list_marker', None)
    if marker is not None:
        rv['children'].append(serialize_box(document, marker))

    text = getattr(box, 'text', None)
    if text is not None:
        rv['text'] = text

    replacement = getattr(box, 'replacement', None)
    if replacement is not None:
        width = int(box.width)
        height = int(box.height)
        rv['width'] = width
        rv['height'] = height
        rv['image'] = serialize_replacement(replacement, width, height)

    return rv


def serialize_replacement(replacement, scaled_width=None, scaled_height=None):
    pattern, width, height = replacement

    if scaled_width is None:
        scaled_width = width
    if scaled_height is None:
        scaled_height = height

    surface = cairo.ImageSurface(
        cairo.FORMAT_ARGB32, scaled_width, scaled_height)
    context = cairo.Context(surface)
    context.scale(scaled_width / width, scaled_height / height)
    context.set_source(pattern)
    context.paint()
    file_like = BytesIO()
    surface.write_to_png(file_like)
    return file_like.getvalue().encode('base64').replace('\n', '')


@apply
def serialize_page_box():
    return functools.partial(serialize_box, attributes=PAGE_BOX_ATTRIBUTES)


def serialize_style(document, style):
    style = style.as_dict()
    for key, value in style.iteritems():
        if getattr(value, 'type', None) == 'COLOR_VALUE':
            style[key] = value.cssText
    bg_image = style['background_image']
    if bg_image == 'None':
        bg_image = None
    else:
        bg_image = document.get_image_from_uri(style['background_image'])
        if bg_image is not None:
            bg_image = serialize_replacement(bg_image)
    style['background_image'] = bg_image
    style['background_position'] = [
        getattr(v, 'cssText', v)
        for v in style['background_position']]
    style['text_decoration'] = ' '.join(style['text_decoration']) or 'none'
    return style
