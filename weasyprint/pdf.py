# coding: utf8
"""
    weasyprint.pdf
    --------------

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals


class PDF(object):
    """PDF document post-processor adding links."""
    def __init__(self, bytesio, links, destinations):
        bytesio.seek(0)
        self.lines = bytesio.readlines()
        self.outlines = []
        self.xref = []
        self.trailer = []
        self.size = None
        self.info = None
        self.objects = {}
        self.active = None
        self.numbers = []
        self.added_numbers = []
        self.pages = []

        for line in self.lines:
            if line.endswith(b' obj\n'):
                self.active = 'object'
                number = int(line.split()[0])
                self.numbers.append(number)
            elif line == b'xref\n':
                self.active = 'xref'
            elif line == b'trailer\n':
                self.active = 'trailer'

            if line.endswith(b'/Type /Page\n'):
                self.pages.append(number)

            if self.active == 'size':
                self.size = int(line)
                self.active = None
            elif self.active == 'xref':
                self.xref.append(line)
            elif self.active == 'trailer':
                self.trailer.append(line)
                if b'/Info' in line:
                    self.info = int(line.rsplit()[-3])
            elif self.active == 'object':
                if number not in self.objects:
                    self.objects[number] = []
                self.objects[number].append(line)

            if line == b'startxref\n':
                self.active = 'size'
            elif line == b'endobj\n':
                self.active = None

        for i, line in enumerate(self.objects[self.info]):
            if b'/Creator' in line:
                pre = line.split(b'/Creator')[0]
                new_line = b'%s/Creator (%s)\n' % (pre, b'WeasyPrint')
                self.objects[self.info][i] = new_line
                offset_size = len(new_line) - len(line)
                self.replace_xref_size(self.info, offset_size)

        for pdf_page_number, link_page in zip(self.pages, links):
            annot_numbers = []
            for link, x1, y1, x2, y2 in link_page:
                text = b''.join((
                    b'<<',
                    b'/Type /Annot',
                    b'/Subtype /Link',
                    b'/Rect [%f %f %f %f]\n' % (x1, y1, x2, y2)))
                if link:
                    if link.startswith('#'):
                        if link[1:] in destinations:
                            text += b''.join((
                                b'/A <<',
                                b'/Type /Action',
                                b'/S /GoTo',
                                b'/D [%d /XYZ %d %d 1]\n' % (
                                    destinations[link[1:]])))
                    else:
                        text += b''.join((
                            b'/A <<',
                            b'/Type /Action',
                            b'/S /URI',
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
                pre = line.split(b'/Size')[0]
                new_line = b'%s/Size %s\n' % (
                    pre, b'%s' % (len(self.added_numbers) + len(self.numbers)))
                self.trailer[i] = new_line

        for line in self.lines:
            if line.endswith(b' obj\n'):
                self.active = 'object'
                number = int(line.split()[0])
                self.outlines.extend(self.objects[number])
            elif line == b'xref\n':
                self.active = 'xref'
                for added_number in self.added_numbers:
                    self.outlines.extend(self.objects[added_number])
                self.outlines.extend(self.xref)
            elif line == b'trailer\n':
                self.active = 'trailer'

            if self.active == 'size':
                self.outlines.append(b'%d\n' % self.size)
                self.active = None
            elif self.active == 'trailer':
                if self.trailer:
                    self.outlines.extend(self.trailer)
                    self.trailer = None
            elif self.active in ('xref', 'object'):
                pass  # xref and object are already handled
            else:
                self.outlines.append(line)

            if line == b'endobj\n':
                self.active = None
            elif line == b'startxref\n':
                self.active = 'size'

    def add_object(self, text):
        """Add an object with ``text`` content at the end of the objects."""
        next_number = len(self.numbers) + 1
        text = b'%d 0 obj\n%s\nendobj' % (next_number, text)
        last_size = int(
            self.xref[self.numbers[-1] + 2].split()[0].lstrip(b'0'))
        last_object_size = len(''.join(self.objects[self.numbers[-1]]))
        self.xref.append(b'%010d 00000 n \n' % (last_size + last_object_size))
        self.numbers.append(next_number)
        self.added_numbers.append(next_number)
        self.objects[next_number] = [
            line + b'\n' for line in text.split(b'\n')]
        self.size += len(text) + 1
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
        self.size += offset_size

    def write(self, target):
        for outline in self.outlines:
            target.write(outline)
