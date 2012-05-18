# coding: utf8
"""
    weasyprint.pdf
    --------------

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from . import VERSION_STRING
from .utils import iri_to_uri


def pdf_encode(unicode_string):
    """PDF uses either latin1 or UTF-16 BE with a BOM"""
    return ('\ufeff' + unicode_string).encode('utf-16-be')


def write(bytesio, target, links, destinations, bookmarks):
    """Write PDF from ``bytesio`` to ``target`` adding ``links``."""
    bytesio.seek(0)
    position = 0
    lines = iter(bytesio)
    current_line = next(lines)

    while not current_line.endswith(b' obj\n'):
        position += len(current_line)
        target.write(current_line)
        current_line = next(lines)

    pages = []
    objects = {}
    ordered_objects = []
    def add_object(object_id, parts):
        objects[object_id] = parts
        ordered_objects.append((object_id, parts))
        return parts

    while current_line != b'xref\n':
        if current_line.endswith(b' obj\n'):
            object_id = int(current_line.split()[0])
            current_object = add_object(object_id, [])
        current_object.append(current_line)

        if current_line.endswith(b'/Type /Page\n'):
            pages.append(object_id)

        if current_line.endswith(b'/Type /Catalog\n'):
            catalog_id = object_id
        current_line = next(lines)

    while current_line != b'trailer\n':
        current_line = next(lines)

    trailer = []
    while current_line != b'startxref\n':
        trailer.append(current_line)
        if b'/Info' in current_line:
            info = int(current_line.rsplit()[-3])
            for i, infoline in enumerate(objects[info]):
                if b'/Creator' in infoline:
                    objects[info][i] = b''.join([
                        infoline.split(b'/Creator')[0],
                        b'/Creator (',
                        pdf_encode(VERSION_STRING),
                        b')\n'])
        current_line = next(lines)

    next_object_id = [len(objects) + 1]
    def add_new_object(parts):
        object_id = next_object_id[0]
        next_object_id[0] += 1
        parts = [('%d 0 obj\n' % object_id).encode('ascii')] + parts
        parts.append(b'\nendobj\n')
        add_object(object_id, parts)
        return object_id

    for pdf_page_number, link_page in zip(pages, links):
        annot_ids = []

        for link, x1, y1, x2, y2 in link_page:
            text = [(
                '<< /Type /Annot /Subtype /Link '
                '/Rect [%f %f %f %f] /Border [0 0 0]\n'
                % (x1, y1, x2, y2)
            ).encode('ascii')]
            if link:
                if link.startswith('#'):
                    if link[1:] in destinations:
                        text.append((
                            '/A << /Type /Action /S /GoTo '
                            '/D [%d /XYZ %f %f 0]\n'
                            % destinations[link[1:]]
                        ).encode('ascii'))
                else:
                    text.extend([
                        b'/A << /Type /Action /S /URI /URI (',
                        iri_to_uri(link).encode('ascii'),
                        b')\n'])
            text.append(b'>>\n>>')
            annot_ids.append(add_new_object(text))

        if annot_ids:
            objects[pdf_page_number].insert(-2, b''.join([
                b'/Annots [',
                (' '.join(
                    '%d 0 R' % n for n in annot_ids).encode('ascii')),
                b']\n'
            ]))

    root, bookmarks = bookmarks
    if bookmarks:
        bookmark_root = add_new_object([])
        objects[bookmark_root][1:-1] = [(
            '<< /Type /Outlines '
            '/Count %d /First %d 0 R /Last %d 0 R\n>>' % (
                root['Count'],
                root['First'] + bookmark_root,
                root['Last'] + bookmark_root)
            ).encode('ascii')]
        objects[catalog_id].insert(
            -2, ('/Outlines %d 0 R\n' % bookmark_root).encode('ascii'))

        for bookmark in bookmarks:
            text = [b'<< /Title (']
            text.append(pdf_encode(bookmark['label']))
            text.append(b')\n')
            if bookmark['Count']:
                text.append(('/Count %d\n' % bookmark['Count']).encode('ascii'))
            # parent == 0 means no parent, as the root is not a bookmark
            for key in ['Parent', 'Prev', 'Next', 'First', 'Last']:
                if bookmark[key]:
                    text.append(('/%s %d 0 R\n' % (
                        key, bookmark[key] + bookmark_root)).encode('ascii'))
            text.append((
                '/A << /Type /Action /S /GoTo '
                '/D [%d /XYZ %f %f 0]\n>>\n>>'
                     % bookmark['destination']).encode('ascii'))
            add_new_object(text)

    assert len(ordered_objects) == len(objects)
    total_objects = len(objects)

    for i, line in enumerate(trailer):
        if b'/Size' in line:
            trailer[i] = (
                line.split(b'/Size', 1)[0]
                + ('/Size %d\n' % (total_objects + 1)).encode('ascii'))

    xref = [None] * total_objects
    for object_id, obj in ordered_objects:
        xref[object_id - 1] = ('%010d 00000 n \n' % position).encode('ascii')
        obj_bytes = b''.join(obj)
        position += len(obj_bytes)
        target.write(obj_bytes)
    target.write((
        'xref\n0 %d\n0000000000 65535 f \n' % (total_objects + 1)
    ).encode('ascii'))
    target.write(b''.join(xref))
    target.write(b''.join(trailer))
    target.write(('startxref\n%d\n%%EOF\n' % position).encode('ascii'))
