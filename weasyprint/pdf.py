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

from . import VERSION


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
                    objects[info][i] = (
                        b'%s/Creator (WeasyPrint %s)\n' % (
                            infoline.split(b'/Creator')[0], bytes(VERSION)))

    number = len(objects) + 1
    for pdf_page_number, link_page in zip(pages, links):
        annot_numbers = []

        for link, x1, y1, x2, y2 in link_page:
            text = b''.join((
                b'%d 0 obj\n' % number,
                b'<< /Type /Annot /Subtype /Link',
                b'/Rect [%f %f %f %f]\n' % (x1, y1, x2, y2)))
            if link:
                if link.startswith('#'):
                    if link[1:] in destinations:
                        text += b''.join((
                            b'/A << /Type /Action /S /GoTo',
                            b'/D [%d /XYZ %d %d 1]\n' % (
                                destinations[link[1:]])))
                else:
                    text += b''.join((
                        b'/A << /Type /Action /S /URI', b'/URI (%s)\n' % link))
            text += b'>>\n>>\nendobj\n'
            objects[number] = [text]
            annot_numbers.append(number)
            number += 1

        if annot_numbers:
            objects[pdf_page_number].insert(-2, b'/Annots [%s]\n' % b' '.join(
                b'%d 0 R' % annot_number for annot_number in annot_numbers))

    for i, line in enumerate(trailer):
        if b'/Size' in line:
            trailer[i] = b'%s/Size %d\n' % (line.split(b'/Size')[0], number)

    xref = (number - 1) * [None]
    for number, obj in objects.items():
        xref[number - 1] = b'%010d 00000 n \n' % position
        for line in obj:
            position += len(line)
            target.write(line)
    target.write(b'xref\n0 %d\n0000000000 65535 f \n' % (number + 1))
    for table in (xref, trailer):
        for line in table:
            target.write(line)
    target.write(b'startxref\n%d\n%%EOF\n' % position)
