"""
    weasyprint.pdf
    --------------

    Post-process the PDF files created by cairo and extra metadata (including
    attachments, embedded files, trim & bleed boxes).

    Rather than trying to parse any valid PDF, we make some assumptions
    that hold for cairo in order to simplify the code:

    * All newlines are '\n', not '\r' or '\r\n'
    * Except for number 0 (which is always free) there is no "free" object.
    * Most white space separators are made of a single 0x20 space.
    * Indirect dictionary objects do not contain '>>' at the start of a line
      except to mark the end of the object, followed by 'endobj'.
      (In other words, '>>' markers for sub-dictionaries are indented.)
    * The Page Tree is flat: all kids of the root page node are page objects,
      not page tree nodes.

    However the code uses a lot of assert statements so that if an assumptions
    is not true anymore, the code should (hopefully) fail with an exception
    rather than silently behave incorrectly.


    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import hashlib
import io
import mimetypes
import os
import re
import string
import zlib
from urllib.parse import unquote, urlsplit

import cairocffi as cairo

from . import Attachment
from .logger import LOGGER
from .urls import URLFetchingError


def pdf_escape(value):
    """Escape parentheses and backslashes in ``value``.

    ``value`` must be unicode, or latin1 bytestring.

    """
    if isinstance(value, bytes):
        value = value.decode('latin1')
    return value.translate({40: r'\(', 41: r'\)', 92: r'\\'})


class PDFFormatter(string.Formatter):
    """Like str.format except:

    * Results are byte strings
    * The new !P conversion flags encodes a PDF string.
      (UTF-16 BE with a BOM, then backslash-escape parentheses.)

    Except for fields marked !P, everything should be ASCII-only.

    """
    def convert_field(self, value, conversion):
        if conversion == 'P':
            # Make a round-trip back through Unicode for the .translate()
            # method. (bytes.translate only maps to single bytes.)
            # Use latin1 to map all byte values.
            return '({0})'.format(pdf_escape(
                ('\ufeff' + value).encode('utf-16-be').decode('latin1')))
        else:
            return super().convert_field(value, conversion)

    def vformat(self, format_string, args, kwargs):
        result = super().vformat(format_string, args, kwargs)
        return result.encode('latin1')


pdf_format = PDFFormatter().format


class PDFDictionary(object):
    def __init__(self, object_number, byte_string):
        self.object_number = object_number
        self.byte_string = byte_string

    def __repr__(self):
        return self.__class__.__name__ + repr(
            (self.object_number, self.byte_string))

    _re_cache = {}

    def get_value(self, key, value_re):
        regex = self._re_cache.get((key, value_re))
        if not regex:
            regex = re.compile(pdf_format('/{0} {1}', key, value_re))
            self._re_cache[key, value_re] = regex
        return regex.search(self.byte_string).group(1)

    def get_type(self):
        """Get dictionary type.

        :returns: the value for the /Type key.

        """
        # No end delimiter, + defaults to greedy
        return self.get_value('Type', '/(\\w+)').decode('ascii')

    def get_indirect_dict(self, key, pdf_file):
        """Read the value for `key` and follow the reference.

        We assume that it is an indirect dictionary object.

        :return: a new PDFDictionary instance.

        """
        object_number = int(self.get_value(key, '(\\d+) 0 R'))
        return type(self)(object_number, pdf_file.read_object(object_number))

    def get_indirect_dict_array(self, key, pdf_file):
        """Read the value for `key` and follow the references.

        We assume that it is an array of indirect dictionary objects.

        :return: a list of new PDFDictionary instance.

        """
        parts = self.get_value(key, '\\[(.+?)\\]').split(b' 0 R')
        # The array looks like this: ' <a> 0 R <b> 0 R <c> 0 R '
        # so `parts` ends up like this [' <a>', ' <b>', ' <c>', ' ']
        # With the trailing white space in the list.
        trail = parts.pop()
        assert not trail.strip()
        class_ = type(self)
        read = pdf_file.read_object
        return [class_(n, read(n)) for n in map(int, parts)]


class PDFFile(object):
    trailer_re = re.compile(
        b'\ntrailer\n(.+)\nstartxref\n(\\d+)\n%%EOF\n$', re.DOTALL)

    def __init__(self, fileobj):
        # cairo’s trailer only has Size, Root and Info.
        # The trailer + startxref + EOF is typically under 100 bytes
        fileobj.seek(-200, os.SEEK_END)
        trailer, startxref = self.trailer_re.search(fileobj.read()).groups()
        trailer = PDFDictionary(None, trailer)
        startxref = int(startxref)

        fileobj.seek(startxref)
        line = next(fileobj)
        assert line == b'xref\n'

        line = next(fileobj)
        first_object, total_objects = line.split()
        assert first_object == b'0'
        total_objects = int(total_objects)

        line = next(fileobj)
        assert line == b'0000000000 65535 f \n'

        objects_offsets = [None]
        for object_number in range(1, total_objects):
            line = next(fileobj)
            assert line[10:] == b' 00000 n \n'
            objects_offsets.append(int(line[:10]))

        self.fileobj = fileobj
        #: Maps object number -> bytes from the start of the file
        self.objects_offsets = objects_offsets

        info = trailer.get_indirect_dict('Info', self)
        catalog = trailer.get_indirect_dict('Root', self)
        page_tree = catalog.get_indirect_dict('Pages', self)
        pages = page_tree.get_indirect_dict_array('Kids', self)
        # Check that the tree is flat
        assert all(p.get_type() == 'Page' for p in pages)

        self.startxref = startxref
        self.info = info
        self.catalog = catalog
        self.page_tree = page_tree
        self.pages = pages

        self.finished = False
        self.overwritten_objects_offsets = {}
        self.new_objects_offsets = []

    def read_object(self, object_number):
        """
        :param object_number:
            An integer N so that 1 <= N < len(self.objects_offsets)
        :returns:
            The object content as a byte string.

        """
        fileobj = self.fileobj
        fileobj.seek(self.objects_offsets[object_number])
        line = next(fileobj)
        assert line.endswith(b' 0 obj\n')
        assert int(line[:-7]) == object_number  # len(b' 0 obj\n') == 7
        object_lines = []
        for line in fileobj:
            if line == b'>>\n':
                assert next(fileobj) == b'endobj\n'
                # No newline, we’ll add it when writing.
                object_lines.append(b'>>')
                return b''.join(object_lines)
            object_lines.append(line)

    def overwrite_object(self, object_number, byte_string):
        """Write the new content for an existing object at the end of the file.

        :param object_number:
            An integer N so that 1 <= N < len(self.objects_offsets)
        :param byte_string:
            The new object content as a byte string.

        """
        self.overwritten_objects_offsets[object_number] = (
            self._write_object(object_number, byte_string))

    def extend_dict(self, dictionary, new_content):
        """Overwrite a dictionary object.

        Content is added inside the << >> delimiters.

        """
        assert dictionary.byte_string.endswith(b'>>')
        self.overwrite_object(
            dictionary.object_number,
            dictionary.byte_string[:-2] + new_content + b'\n>>')

    def next_object_number(self):
        """Return object number that would be used by write_new_object()."""
        return len(self.objects_offsets) + len(self.new_objects_offsets)

    def write_new_object(self, byte_string):
        """Write a new object at the end of the file.

        :param byte_string:
            The object content as a byte string.
        :return:
            The new object number.

        """
        object_number = self.next_object_number()
        self.new_objects_offsets.append(
            self._write_object(object_number, byte_string))
        return object_number

    def finish(self):
        """Write cross-ref table and trailer for new and overwritten objects.

        This makes `fileobj` a valid (updated) PDF file.

        """
        new_startxref, write = self._start_writing()
        self.finished = True
        write(b'xref\n')

        # Don’t bother sorting or finding contiguous numbers,
        # just write a new sub-section for each overwritten object.
        for object_number, offset in self.overwritten_objects_offsets.items():
            write(pdf_format(
                '{0} 1\n{1:010} 00000 n \n', object_number, offset))

        if self.new_objects_offsets:
            first_new_object = len(self.objects_offsets)
            write(pdf_format(
                '{0} {1}\n', first_new_object, len(self.new_objects_offsets)))
            for object_number, offset in enumerate(
                    self.new_objects_offsets, start=first_new_object):
                write(pdf_format('{0:010} 00000 n \n', offset))

        write(pdf_format(
            'trailer\n<< '
            '/Size {size} /Root {root} 0 R /Info {info} 0 R /Prev {prev}'
            ' >>\nstartxref\n{startxref}\n%%EOF\n',
            size=self.next_object_number(),
            root=self.catalog.object_number,
            info=self.info.object_number,
            prev=self.startxref,
            startxref=new_startxref))

    def _write_object(self, object_number, byte_string):
        offset, write = self._start_writing()
        write(pdf_format('{0} 0 obj\n', object_number))
        write(byte_string)
        write(b'\nendobj\n')
        return offset

    def _start_writing(self):
        assert not self.finished
        fileobj = self.fileobj
        fileobj.seek(0, os.SEEK_END)
        return fileobj.tell(), fileobj.write


def _write_compressed_file_object(pdf, file):
    """Write a compressed file like object as ``/EmbeddedFile``.

    Compressing is done with deflate. In fact, this method writes multiple PDF
    objects to include length, compressed length and MD5 checksum.

    :return:
        the object number of the compressed file stream object

    """

    object_number = pdf.next_object_number()
    # Make sure we stay in sync with our object numbers
    expected_next_object_number = object_number + 4

    length_number = object_number + 1
    md5_number = object_number + 2
    uncompressed_length_number = object_number + 3

    offset, write = pdf._start_writing()
    write(pdf_format('{0} 0 obj\n', object_number))
    write(pdf_format(
        '<< /Type /EmbeddedFile /Length {0} 0 R /Filter '
        '/FlateDecode /Params << /CheckSum {1} 0 R /Size {2} 0 R >> >>\n',
        length_number, md5_number, uncompressed_length_number))
    write(b'stream\n')

    uncompressed_length = 0
    compressed_length = 0

    md5 = hashlib.md5()
    compress = zlib.compressobj()
    for data in iter(lambda: file.read(4096), b''):
        uncompressed_length += len(data)

        md5.update(data)

        compressed = compress.compress(data)
        compressed_length += len(compressed)

        write(compressed)

    compressed = compress.flush(zlib.Z_FINISH)
    compressed_length += len(compressed)
    write(compressed)

    write(b'\nendstream\n')
    write(b'endobj\n')

    pdf.new_objects_offsets.append(offset)

    pdf.write_new_object(pdf_format("{0}", compressed_length))
    pdf.write_new_object(pdf_format("<{0}>", md5.hexdigest()))
    pdf.write_new_object(pdf_format("{0}", uncompressed_length))

    assert pdf.next_object_number() == expected_next_object_number

    return object_number


def _get_filename_from_result(url, result):
    """Derive a filename from a fetched resource.

    This is either the filename returned by the URL fetcher, the last URL path
    component or a synthetic name if the URL has no path.

    """

    filename = None

    # A given filename will always take precedence
    if result:
        filename = result.get('filename')
        if filename:
            return filename

    # The URL path likely contains a filename, which is a good second guess
    if url:
        split = urlsplit(url)
        if split.scheme != 'data':
            filename = split.path.split("/")[-1]
            if filename == '':
                filename = None

    if filename is None:
        # The URL lacks a path altogether. Use a synthetic name.

        # Using guess_extension is a great idea, but sadly the extension is
        # probably random, depending on the alignment of the stars, which car
        # you're driving and which software has been installed on your machine.
        #
        # Unfortuneatly this isn't even imdepodent on one machine, because the
        # extension can depend on PYTHONHASHSEED if mimetypes has multiple
        # extensions to offer
        extension = None
        if result:
            mime_type = result.get('mime_type')
            if mime_type == 'text/plain':
                # text/plain has a phletora of extensions - all garbage
                extension = '.txt'
            else:
                extension = mimetypes.guess_extension(mime_type) or '.bin'
        else:
            extension = '.bin'

        filename = 'attachment' + extension
    else:
        filename = unquote(filename)

    return filename


def _write_pdf_embedded_files(pdf, attachments, url_fetcher):
    """Write attachments as embedded files (document attachments).

    :return:
        the object number of the name dictionary or :obj:`None`

    """
    file_spec_ids = []
    for attachment in attachments:
        file_spec_id = _write_pdf_attachment(pdf, attachment, url_fetcher)
        if file_spec_id is not None:
            file_spec_ids.append(file_spec_id)

    # We might have failed to write any attachment at all
    if len(file_spec_ids) == 0:
        return None

    content = [b'<< /Names [']
    for fs in file_spec_ids:
        content.append(pdf_format('\n(attachment{0}) {0} 0 R ',
                       fs))
    content.append(b'\n] >>')
    return pdf.write_new_object(b''.join(content))


def _write_pdf_attachment(pdf, attachment, url_fetcher):
    """Write an attachment to the PDF stream.

    :return:
        the object number of the ``/Filespec`` object or :obj:`None` if the
        attachment couldn't be read.

    """
    try:
        # Attachments from document links like <link> or <a> can only be URLs.
        # They're passed in as tuples
        if isinstance(attachment, tuple):
            url, description = attachment
            attachment = Attachment(
                url=url, url_fetcher=url_fetcher, description=description)
        elif not isinstance(attachment, Attachment):
            attachment = Attachment(guess=attachment, url_fetcher=url_fetcher)

        with attachment.source as (source_type, source, url, _):
            if isinstance(source, bytes):
                source = io.BytesIO(source)
            file_stream_id = _write_compressed_file_object(pdf, source)
    except URLFetchingError as exc:
        LOGGER.error('Failed to load attachment: %s', exc)
        return None

    # TODO: Use the result object from a URL fetch operation to provide more
    # details on the possible filename
    filename = _get_filename_from_result(url, None)

    return pdf.write_new_object(pdf_format(
        '<< /Type /Filespec /F () /UF {0!P} /EF << /F {1} 0 R >> '
        '/Desc {2!P}\n>>',
        filename,
        file_stream_id,
        attachment.description or ''))


def write_pdf_metadata(fileobj, scale, url_fetcher, attachments,
                       attachment_links, pages):
    """Add PDF metadata that are not handled by cairo.

    Includes:
    - attachments
    - embedded files
    - trim box
    - bleed box

    """
    pdf = PDFFile(fileobj)

    # Add embedded files

    embedded_files_id = _write_pdf_embedded_files(
        pdf, attachments, url_fetcher)
    if embedded_files_id is not None:
        params = b''
        if embedded_files_id is not None:
            params += pdf_format(' /Names << /EmbeddedFiles {0} 0 R >>',
                                 embedded_files_id)
        pdf.extend_dict(pdf.catalog, params)

    # Add attachments

    # A single link can be split in multiple regions. We don't want to embed
    # a file multiple times of course, so keep a reference to every embedded
    # URL and reuse the object number.
    # TODO: If we add support for descriptions this won't always be correct,
    # because two links might have the same href, but different titles.
    annot_files = {}
    for page_links in attachment_links:
        for link_type, target, rectangle in page_links:
            if link_type == 'attachment' and target not in annot_files:
                # TODO: use the title attribute as description
                annot_files[target] = _write_pdf_attachment(
                    pdf, (target, None), url_fetcher)

    for pdf_page, document_page, page_links in zip(
            pdf.pages, pages, attachment_links):

        # Add bleed box

        media_box = pdf_page.get_value(
            'MediaBox', '\\[(.+?)\\]').decode('ascii').strip()
        left, top, right, bottom = (
            float(value) for value in media_box.split(' '))
        # Convert pixels into points
        bleed = {
            key: value * 0.75 for key, value in document_page.bleed.items()}

        trim_left = left + bleed['left']
        trim_top = top + bleed['top']
        trim_right = right - bleed['right']
        trim_bottom = bottom - bleed['bottom']

        # Arbitrarly set PDF BleedBox between CSS bleed box (PDF MediaBox) and
        # CSS page box (PDF TrimBox), at most 10 points from the TrimBox.
        bleed_left = trim_left - min(10, bleed['left'])
        bleed_top = trim_top - min(10, bleed['top'])
        bleed_right = trim_right + min(10, bleed['right'])
        bleed_bottom = trim_bottom + min(10, bleed['bottom'])

        pdf.extend_dict(pdf_page, pdf_format(
            '/TrimBox [ {} {} {} {} ] /BleedBox [ {} {} {} {} ]'.format(
                trim_left, trim_top, trim_right, trim_bottom,
                bleed_left, bleed_top, bleed_right, bleed_bottom)))

        # Add links to attachments

        # TODO: splitting a link into multiple independent rectangular
        # annotations works well for pure links, but rather mediocre for other
        # annotations and fails completely for transformed (CSS) or complex
        # link shapes (area). It would be better to use /AP for all links and
        # coalesce link shapes that originate from the same HTML link. This
        # would give a feeling similiar to what browsers do with links that
        # span multiple lines.
        annotations = []
        for link_type, target, rectangle in page_links:
            if link_type == 'attachment' and annot_files[target] is not None:
                matrix = cairo.Matrix(
                    xx=scale, yy=-scale, y0=document_page.height * scale)
                rect_x, rect_y, width, height = rectangle
                rect_x, rect_y = matrix.transform_point(rect_x, rect_y)
                width, height = matrix.transform_distance(width, height)
                # x, y, w, h => x0, y0, x1, y1
                rectangle = rect_x, rect_y, rect_x + width, rect_y + height
                content = [pdf_format(
                    '<< /Type /Annot '
                    '/Rect [{0:f} {1:f} {2:f} {3:f}] /Border [0 0 0]\n',
                    *rectangle)]
                link_ap = pdf.write_new_object(pdf_format(
                    '<< /Type /XObject /Subtype /Form '
                    '/BBox [{0:f} {1:f} {2:f} {3:f}] /Length 0 >>\n'
                    'stream\n'
                    'endstream',
                    *rectangle))
                content.append(b'/Subtype /FileAttachment ')
                # evince needs /T or fails on an internal assertion. PDF
                # doesn't require it.
                content.append(pdf_format(
                    '/T () /FS {0} 0 R /AP << /N {1} 0 R >>',
                    annot_files[target], link_ap))
                content.append(b'>>')
                annotations.append(pdf.write_new_object(b''.join(content)))

        if annotations:
            pdf.extend_dict(pdf_page, pdf_format(
                '/Annots [{0}]', ' '.join(
                    '{0} 0 R'.format(n) for n in annotations)))

    pdf.finish()
