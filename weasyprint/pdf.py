# coding: utf8
"""
    weasyprint.pdf
    --------------

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

from . import VERSION


class PDF(object):
    """PDF document post-processor adding links."""
    def __init__(self, bytesio, links, destinations):
        self.xref = []
        self.trailer = []
        self.objects = {}
        self.numbers = []
        self.pages = []
        self.outlines = []

        bytesio.seek(0)
        lines = bytesio.readlines()

        while not lines[0].endswith(b' obj\n'):
            self.outlines.append(lines.pop(0))

        while lines[0] != b'xref\n':
            line = lines.pop(0)
            if line.endswith(b' obj\n'):
                number = int(line.split()[0])
                self.numbers.append(number)
                self.objects[number] = []

            self.objects[number].append(line)

            if line.endswith(b'/Type /Page\n'):
                self.pages.append(number)

        while lines[0] != b'trailer\n':
            self.xref.append(lines.pop(0))

        while lines[0] != b'startxref\n':
            line = lines.pop(0)
            self.trailer.append(line)
            if b'/Info' in line:
                info = int(line.rsplit()[-3])
                for i, info_line in enumerate(self.objects[info]):
                    if b'/Creator' in info_line:
                        new_line = b'%s/Creator (WeasyPrint %s)\n' % (
                            info_line.split(b'/Creator')[0], bytes(VERSION))
                        self.objects[info][i] = new_line
                        self.replace_xref_size(
                            info, len(new_line) - len(info_line))

        for pdf_page_number, link_page in zip(self.pages, links):
            annot_numbers = []

            for link, x1, y1, x2, y2 in link_page:
                text = b''.join((
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
                            b'/A << /Type /Action /S /URI',
                            b'/URI (%s)\n' % link))
                text += b'>>\n>>'
                annot_numbers.append(self.add_object(text))

            if annot_numbers:
                string = b'/Annots [%s]\n' % b' '.join(
                    b'%d 0 R' % number for number in annot_numbers)
                self.objects[pdf_page_number].insert(-2, string)
                self.replace_xref_size(pdf_page_number, len(string))

        for i, line in enumerate(self.trailer):
            if b'/Size' in line:
                self.trailer[i] = b'%s/Size %d\n' % (
                    line.split(b'/Size')[0], len(self.numbers) + 1)

        for number in self.numbers:
            self.outlines.extend(self.objects[number])
        size = sum([len(line) for line in self.outlines])
        self.outlines.extend(self.xref + self.trailer)
        self.outlines.append(b'startxref\n%d\n%%EOF\n' % size)

    def add_object(self, text):
        """Add an object with ``text`` content at the end of the objects."""
        next_number = len(self.numbers) + 1
        text = b'%d 0 obj\n%s\nendobj' % (next_number, text)
        last_size = int(
            self.xref[self.numbers[-1] + 2].split()[0].lstrip(b'0'))
        last_object_size = len(''.join(self.objects[self.numbers[-1]]))
        self.xref.append(b'%010d 00000 n \n' % (last_size + last_object_size))
        self.numbers.append(next_number)
        self.objects[next_number] = [
            line + b'\n' for line in text.split(b'\n')]
        self.xref[1] = b'0 %d\n' % (next_number + 1)
        return next_number

    def replace_xref_size(self, number, offset_size):
        """Update xref adding ``offset_size`` bytes to ``object[number]``."""
        index = self.numbers.index(number)
        for next_number in self.numbers[index + 1:len(self.numbers)]:
            out = self.xref[next_number + 2]
            old_size, content = out.split(b' ', 1)
            old_size = int(old_size.lstrip(b'0')) + offset_size
            self.xref[next_number + 2] = b'%010d %s' % (old_size, content)

    def write(self, target):
        """Write the PDF content into the ``target`` stream."""
        for outline in self.outlines:
            target.write(outline)
