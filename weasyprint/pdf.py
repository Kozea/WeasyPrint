# coding: utf-8
"""
    weasyprint.pdf
    --------------

    Post-process the PDF files created by cairo and add metadata such as
    hyperlinks and bookmarks.

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import hashlib
import io
import mimetypes
import sys
import zlib

import cairocffi as cairo
from pdfrw import PdfArray, PdfDict, PdfName, PdfReader, PdfString, PdfWriter

from . import VERSION_STRING, Attachment
from .compat import izip, unquote
from .html import W3C_DATE_RE
from .logger import LOGGER
from .urls import URLFetchingError, iri_to_uri, urlsplit


def convert_bookmarks_units(bookmarks, matrices):
    converted_bookmarks = []
    for label, target, children in bookmarks:
        page, x, y = target
        x, y = matrices[target[0]].transform_point(x, y)
        children = convert_bookmarks_units(children, matrices)
        converted_bookmarks.append((label, (page, x, y), children))
    return converted_bookmarks


def prepare_metadata(document, scale, pages):
    """Change metadata into data structures closer to the PDF objects.

    In particular, convert from WeasyPrint units (CSS pixels from
    the top-left corner) to PDF units (points from the bottom-left corner.)

    :param scale:
        PDF points per CSS pixels.
        Defaults to 0.75, but is affected by `zoom` in
        :meth:`weasyprint.document.Document.write_pdf`.

    """
    # X and width unchanged;  Y’ = page_height - Y;  height’ = -height
    matrices = [cairo.Matrix(xx=scale, yy=-scale, y0=page.height * scale)
                for page in document.pages]
    links = []
    for page_links, matrix in izip(document.resolve_links(), matrices):
        new_page_links = []
        for link_type, target, rectangle in page_links:
            if link_type == 'internal':
                target_page, target_x, target_y = target
                target = (
                    (pages[target_page].indirect,) +
                    matrices[target_page].transform_point(target_x, target_y))
            rect_x, rect_y, width, height = rectangle
            rect_x, rect_y = matrix.transform_point(rect_x, rect_y)
            width, height = matrix.transform_distance(width, height)
            # x, y, w, h => x0, y0, x1, y1
            rectangle = rect_x, rect_y, rect_x + width, rect_y + height
            new_page_links.append((link_type, target, rectangle))
        links.append(new_page_links)

    bookmarks = convert_bookmarks_units(
        document.make_bookmark_tree(), matrices)

    return bookmarks, links


def _create_compressed_file_object(source):
    """
    Create a file like object as ``/EmbeddedFile`` compressing it with deflate.

    :return:
        the object representing the compressed file stream object
    """
    md5 = hashlib.md5()
    compress = zlib.compressobj()

    pdf_file_object = PdfDict(
        Type=PdfName('EmbeddedFile'), Filter=PdfName('FlateDecode'))
    pdf_file_object.stream = b''
    size = 0
    for data in iter(lambda: source.read(4096), b''):
        size += len(data)
        md5.update(data)
        pdf_file_object.stream += compress.compress(data)
    pdf_file_object.stream += compress.flush(zlib.Z_FINISH)
    pdf_file_object.Params = PdfDict(
        CheckSum=PdfString('<{}>'.format(md5.hexdigest())), Size=size)
    return pdf_file_object


def _get_filename_from_result(url, result):
    """
    Derives a filename from a fetched resource. This is either the filename
    returned by the URL fetcher, the last URL path component or a synthetic
    name if the URL has no path
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
        if sys.version_info[0] < 3:
            # Python 3 unquotes with UTF-8 per default, here we have to do it
            # manually
            # TODO: this assumes that the filename has been quoted as UTF-8.
            # I'm not sure if this assumption holds, as there is some magic
            # involved with filesystem encoding in other parts of the code
            filename = unquote(filename)
            if not isinstance(filename, bytes):
                filename = filename.encode('latin1')
            filename = filename.decode('utf-8')
        else:
            filename = unquote(filename)

    return filename


def _create_pdf_attachment(attachment, url_fetcher):
    """
    Create an attachment to the PDF stream

    :return:
        the object representing the ``/Filespec`` object or :obj:`None` if the
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
            pdf_file_object = _create_compressed_file_object(source)
    except URLFetchingError as exc:
        LOGGER.error('Failed to load attachment: %s', exc)
        return None

    # TODO: Use the result object from a URL fetch operation to provide more
    # details on the possible filename
    return PdfDict(
        Type=PdfName('Filespec'), F=PdfString.encode(''),
        UF=PdfString.encode(_get_filename_from_result(url, None)),
        EF=PdfDict(F=pdf_file_object),
        Desc=PdfString.encode(attachment.description or ''))


def create_bookmarks(bookmarks, pages, parent=None):
    count = len(bookmarks)
    bookmark_objects = []
    for label, target, children in bookmarks:
        destination = (
            pages[target[0]].indirect,
            PdfName('XYZ'), target[1], target[2], 0)
        bookmark_object = PdfDict(
            Title=PdfString.encode(label), A=PdfDict(
                Type=PdfName('Action'), S=PdfName('GoTo'),
                D=PdfArray(destination)))
        bookmark_object.indirect = True
        children_objects, children_count = create_bookmarks(
            children, pages, parent=bookmark_object)
        bookmark_object.Count = 1 + children_count
        if bookmark_objects:
            bookmark_object.Prev = bookmark_objects[-1]
            bookmark_objects[-1].Next = bookmark_object
        if children_objects:
            bookmark_object.First = children_objects[0]
            bookmark_object.Last = children_objects[-1]
        if parent is not None:
            bookmark_object.Parent = parent
        count += children_count
        bookmark_objects.append(bookmark_object)
    return bookmark_objects, count


def write_pdf_metadata(document, fileobj, scale, metadata, attachments,
                       url_fetcher):
    """Append to a seekable file-like object to add PDF metadata."""
    fileobj.seek(0)
    trailer = PdfReader(fileobj)
    pages = trailer.Root.Pages.Kids

    bookmarks, links = prepare_metadata(document, scale, pages)
    if bookmarks:
        bookmark_objects, count = create_bookmarks(bookmarks, pages)
        trailer.Root.Outlines = PdfDict(
            Type=PdfName('Outlines'), Count=count,
            First=bookmark_objects[0], Last=bookmark_objects[-1])

    attachments = metadata.attachments + (attachments or [])
    if attachments:
        embedded_files = []
        for attachment in attachments:
            attachment_object = _create_pdf_attachment(attachment, url_fetcher)
            if attachment_object is not None:
                embedded_files.append(PdfString.encode('attachment'))
                embedded_files.append(attachment_object)
        if embedded_files:
            trailer.Root.Names = PdfDict(
                EmbeddedFiles=PdfDict(Names=PdfArray(embedded_files)))

    # A single link can be split in multiple regions. We don't want to embedded
    # a file multiple times of course, so keep a reference to every embedded
    # URL and reuse the object number.
    # TODO: If we add support for descriptions this won't always be correct,
    # because two links might have the same href, but different titles.
    annot_files = {}
    for page_links in links:
        for link_type, target, rectangle in page_links:
            if link_type == 'attachment' and target not in annot_files:
                # TODO: use the title attribute as description
                annot_files[target] = _create_pdf_attachment(
                    (target, None), url_fetcher)

    # TODO: splitting a link into multiple independent rectangular annotations
    # works well for pure links, but rather mediocre for other annotations and
    # fails completely for transformed (CSS) or complex link shapes (area).
    # It would be better to use /AP for all links and coalesce link shapes that
    # originate from the same HTML link. This would give a feeling similiar to
    # what browsers do with links that span multiple lines.
    for page, page_links in zip(pages, links):
        annotations = PdfArray()
        for link_type, target, rectangle in page_links:
            if link_type != 'attachment' or annot_files[target] is None:
                annotation = PdfDict(
                    Type=PdfName('Annot'), Subtype=PdfName('Link'),
                    Rect=PdfArray(rectangle), Border=PdfArray((0, 0, 0)))
                if link_type == 'internal':
                    destination = (
                        target[0], PdfName('XYZ'), target[1], target[2], 0)
                    annotation.A = PdfDict(
                        Type=PdfName('Action'), S=PdfName('GoTo'),
                        D=PdfArray(destination))
                else:
                    annotation.A = PdfDict(
                        Type=PdfName('Action'), S=PdfName('URI'),
                        URI=PdfString.encode(iri_to_uri(target)))
            else:
                assert annot_files[target] is not None
                ap = PdfDict(N=PdfDict(
                    BBox=PdfArray(rectangle), Subtype=PdfName('Form'),
                    Type=PdfName('XObject')))
                # evince needs /T or fails on an internal assertion. PDF
                # doesn't require it.
                annotation = PdfDict(
                    Type=PdfName('Annot'), Subtype=PdfName('FileAttachment'),
                    T=PdfString.encode(''), Rect=PdfArray(rectangle),
                    Border=PdfArray((0, 0, 0)), FS=annot_files[target],
                    AP=ap)
            annotations.append(annotation)

        if annotations:
            page.Annots = annotations

    trailer.Info.Producer = VERSION_STRING
    for attr, key in (('title', 'Title'), ('description', 'Subject'),
                      ('generator', 'Creator')):
        value = getattr(metadata, attr)
        if value is not None:
            setattr(trailer.Info, key, value)
    for attr, key in (('authors', 'Author'), ('keywords', 'Keywords')):
        value = getattr(metadata, attr)
        if value is not None:
            setattr(trailer.Info, key, ', '.join(getattr(metadata, attr)))
    for attr, key in (('created', 'CreationDate'), ('modified', 'ModDate')):
        value = w3c_date_to_pdf(getattr(metadata, attr), attr)
        if value is not None:
            setattr(trailer.Info, key, value)

    for page, document_page in zip(pages, document.pages):
        left, top, right, bottom = (float(value) for value in page.MediaBox)
        # Convert pixels into points
        bleed = {
            key: value * 0.75 for key, value in document_page.bleed.items()}

        trim_left = left + bleed['left']
        trim_top = top + bleed['top']
        trim_right = right - bleed['right']
        trim_bottom = bottom - bleed['bottom']
        page.TrimBox = PdfArray((trim_left, trim_top, trim_right, trim_bottom))

        # Arbitrarly set PDF BleedBox between CSS bleed box (PDF MediaBox) and
        # CSS page box (PDF TrimBox), at most 10 points from the TrimBox.
        bleed_left = trim_left - min(10, bleed['left'])
        bleed_top = trim_top - min(10, bleed['top'])
        bleed_right = trim_right + min(10, bleed['right'])
        bleed_bottom = trim_bottom + min(10, bleed['bottom'])
        page.BleedBox = PdfArray(
            (bleed_left, bleed_top, bleed_right, bleed_bottom))

    fileobj.seek(0)
    PdfWriter().write(fileobj, trailer=trailer)
    fileobj.truncate()


def w3c_date_to_pdf(string, attr_name):
    """
    YYYYMMDDHHmmSSOHH'mm'

    """
    if string is None:
        return None
    match = W3C_DATE_RE.match(string)
    if match is None:
        LOGGER.warning('Invalid %s date: %r', attr_name, string)
        return None
    groups = match.groupdict()
    pdf_date = (groups['year'] +
                (groups['month'] or '') +
                (groups['day'] or '') +
                (groups['hour'] or '') +
                (groups['minute'] or '') +
                (groups['second'] or ''))
    if groups['hour']:
        assert groups['minute']
        if not groups['second']:
            pdf_date += '00'
        if groups['tz_hour']:
            assert groups['tz_hour'].startswith(('+', '-'))
            assert groups['tz_minute']
            pdf_date += "%s'%s'" % (groups['tz_hour'], groups['tz_minute'])
        else:
            pdf_date += 'Z'  # UTC
    return pdf_date
