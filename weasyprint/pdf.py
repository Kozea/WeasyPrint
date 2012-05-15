# coding: utf8
"""
    weasyprint.pdf
    --------------

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

from . import VERSION_STRING
from .utils import safe_urlquote


def pdf_encode(unicode_string):
    """PDF uses either latin1 or UTF-16 BE with a BOM"""
    return ('\ufeff' + unicode_string).encode('utf-16-be')


def write(bytesio, target, links, destinations):
    """Write PDF from ``bytesio`` to ``target`` adding ``links``."""
    bytesio.seek(0)
    position = 0
    lines = bytesio.readlines()

    while not lines[0].endswith(b' obj\n'):
        line = lines.pop(0)
        position += len(line)
        target.write(line)

    pages = []
    objects = OrderedDict()
    while lines[0] != b'xref\n':
        line = lines.pop(0)
        if line.endswith(b' obj\n'):
            number = int(line.split()[0])
            objects[number] = []
        objects[number].append(line)

        if line.endswith(b'/Type /Page\n'):
            pages.append(number)

    while lines[0] != b'trailer\n':
        lines.pop(0)

    trailer = []
    while lines[0] != b'startxref\n':
        line = lines.pop(0)
        trailer.append(line)
        if b'/Info' in line:
            info = int(line.rsplit()[-3])
            for i, infoline in enumerate(objects[info]):
                if b'/Creator' in infoline:
                    objects[info][i] = b''.join([
                        infoline.split(b'/Creator')[0],
                        b'/Creator (',
                        pdf_encode(VERSION_STRING),
                        b')\n'])

    number = len(objects) + 1
    for pdf_page_number, link_page in zip(pages, links):
        annot_numbers = []

        for link, x1, y1, x2, y2 in link_page:
            text = [(
                '%d 0 obj\n'
                '<< /Type /Annot /Subtype /Link/Rect [%f %f %f %f]\n'
                % (number, x1, y1, x2, y2)
            ).encode('ascii')]
            if link:
                if link.startswith('#'):
                    if link[1:] in destinations:
                        text.append((
                            '/A << /Type /Action /S /GoTo'
                            '/D [%d /XYZ %d %d 1]\n'
                            % destinations[link[1:]]
                        ).encode('ascii'))
                else:
                    text.extend([
                        b'/A << /Type /Action /S /URI /URI (',
                        safe_urlquote(link),
                        b')\n'])
            text.append(b'>>\n>>\nendobj\n')
            objects[number] = text
            annot_numbers.append(number)
            number += 1

        if annot_numbers:
            objects[pdf_page_number].insert(-2, b''.join([
                b'/Annots [',
                (' '.join(
                    '%d 0 R' % n for n in annot_numbers).encode('ascii')),
                b']\n'
            ]))

    for i, line in enumerate(trailer):
        if b'/Size' in line:
            trailer[i] = (
                line.split(b'/Size', 1)[0]
                + ('/Size %d\n' % number).encode('ascii'))

    xref = (number - 1) * [None]
    for number, obj in objects.items():
        xref[number - 1] = ('%010d 00000 n \n' % position).encode('ascii')
        obj_bytes = b''.join(obj)
        position += len(obj_bytes)
        target.write(obj_bytes)
    target.write(
        ('xref\n0 %d\n0000000000 65535 f \n' % (number + 1)).encode('ascii'))
    target.write(b''.join(xref))
    target.write(b''.join(trailer))
    target.write(('startxref\n%d\n%%EOF\n' % position).encode('ascii'))
