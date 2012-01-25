import functools

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
    return {'pages': map(serialize_page_box, document.pages)}


def serialize_box(box, attributes=BOX_ATTRIBUTES):
    rv = {name: getattr(box, name) for name in attributes}
    rv['style'] = serialize_style(box.style)

    children = getattr(box, 'children', None)
    if children is not None:
        rv['children'] = map(serialize_box, children)

    marker = getattr(box, 'outside_list_marker', None)
    if marker is not None:
        rv['children'].append(serialize_box(marker))

    text = getattr(box, 'text', None)
    if text is not None:
        rv['text'] = text

    return rv


@apply
def serialize_page_box():
    return functools.partial(serialize_box, attributes=PAGE_BOX_ATTRIBUTES)


def serialize_style(style):
    style = style.as_dict()
    for key, value in style.iteritems():
        if getattr(value, 'type', None) == 'COLOR_VALUE':
            style[key] = value.cssText
    style['background_position'] = [
        getattr(v, 'cssText', v) for v in style['background_position']]
    style['text_decoration'] = list(style['text_decoration'])
    return style
