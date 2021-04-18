"""
    weasyprint.document
    -------------------

"""

import collections
import functools
import hashlib
import io
import math
import shutil
import zlib
from os.path import basename
from urllib.parse import unquote, urlsplit

import pydyf
from fontTools import subset
from fontTools.ttLib import TTFont, TTLibError

from . import CSS, Attachment, __version__
from .css import get_all_computed_styles
from .css.counters import CounterStyle
from .css.targets import TargetCollector
from .draw import draw_page, stacked
from .formatting_structure import boxes
from .formatting_structure.build import build_formatting_structure
from .html import W3C_DATE_RE, get_html_metadata
from .images import get_image_from_uri as original_get_image_from_uri
from .layout import LayoutContext, layout_document
from .layout.percentages import percentage
from .logger import LOGGER, PROGRESS_LOGGER
from .text.ffi import ffi, pango
from .text.fonts import FontConfiguration
from .urls import URLFetchingError


def _w3c_date_to_pdf(string, attr_name):
    """Tranform W3C date to PDF format."""
    if string is None:
        return None
    match = W3C_DATE_RE.match(string)
    if match is None:
        LOGGER.warning(f'Invalid {attr_name} date: {string!r}')
        return None
    groups = match.groupdict()
    pdf_date = ''
    found = groups['hour']
    for key in ('second', 'minute', 'hour', 'day', 'month', 'year'):
        if groups[key]:
            found = True
            pdf_date = groups[key] + pdf_date
        elif found:
            pdf_date = f'{(key in ("day", "month")):02d}{pdf_date}'
    if groups['hour']:
        assert groups['minute']
        if groups['tz_hour']:
            assert groups['tz_hour'].startswith(('+', '-'))
            assert groups['tz_minute']
            tz_hour = int(groups['tz_hour'])
            tz_minute = int(groups['tz_minute'])
            pdf_date += f"{tz_hour:+03d}'{tz_minute:02d}"
        else:
            pdf_date += 'Z'
    return pdf_date


class Font:
    def __init__(self, file_content, pango_font):
        pango_metrics = pango.pango_font_get_metrics(pango_font, ffi.NULL)
        self._font_description = pango.pango_font_describe(pango_font)
        self.family = ffi.string(pango.pango_font_description_get_family(
            self._font_description))
        font_size = pango.pango_font_description_get_size(
            self._font_description)
        description_string = ffi.string(
            pango.pango_font_description_to_string(self._font_description))
        sha = hashlib.sha256()
        sha.update(description_string)

        self.file_content = file_content
        self.file_hash = hash(file_content)
        self.hash = ''.join(
            chr(65 + letter % 26) for letter in sha.digest()[:6])
        self.name = (
            b'/' + self.hash.encode('ascii') + b'+' +
            self.family.replace(b' ', b''))
        self.italic_angle = 0  # TODO: this should be different
        self.ascent = int(
            pango.pango_font_metrics_get_ascent(pango_metrics) /
            font_size * 1000)
        self.descent = -int(
            pango.pango_font_metrics_get_descent(pango_metrics) /
            font_size * 1000)
        self.stemv = 80
        self.stemh = 80
        self.bbox = [0, 0, 0, 0]
        self.widths = {}
        self.cmap = {}

    @property
    def flags(self):
        flags = 2 ** 3  # Symbolic, custom character set
        if pango.pango_font_description_get_style(self._font_description):
            flags += 2 ** 7  # Italic
        if b'Serif' in self.family.split():
            flags += 2 ** 2  # Serif
        widths = self.widths.values()
        if len(widths) > 1 and len(set(widths)) == 1:
            flags += 2 ** 1  # FixedPitch
        return flags


class Stream(pydyf.Stream):
    """PDF stream object with context storing alpha states."""
    def __init__(self, document, page_rectangle, alpha_states, x_objects,
                 patterns, shadings, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.compress = True
        self.page_rectangle = page_rectangle
        self._document = document
        self._alpha_states = alpha_states
        self._x_objects = x_objects
        self._patterns = patterns
        self._shadings = shadings
        self._current_color = self._current_color_stroke = None
        self._current_alpha = self._current_alpha_stroke = None
        self._current_font = self._current_font_size = None
        self._old_font = self._old_font_size = None
        self._ctm_stack = [Matrix()]

        # These objects are used in text.show_first_line
        self.length = ffi.new('unsigned int *')
        self.ink_rect = ffi.new('PangoRectangle *')
        self.logical_rect = ffi.new('PangoRectangle *')

    @property
    def ctm(self):
        return self._ctm_stack[-1]

    def push_state(self):
        super().push_state()
        self._ctm_stack.append(self.ctm)

    def pop_state(self):
        super().pop_state()
        self._current_color = self._current_color_stroke = None
        self._current_alpha = self._current_alpha_stroke = None
        self._current_font = None
        self._ctm_stack.pop()
        assert self._ctm_stack

    def transform(self, a=1, b=0, c=0, d=1, e=0, f=0):
        super().transform(a, b, c, d, e, f)
        self._ctm_stack[-1] = Matrix(a, b, c, d, e, f) @ self.ctm

    def begin_text(self):
        if self.stream[-1] == b'ET':
            self._current_font = self._old_font
            self.stream.pop()
        else:
            super().begin_text()

    def end_text(self):
        self._old_font, self._current_font = self._current_font, None
        super().end_text()

    def set_color_rgb(self, r, g, b, stroke=False):
        if stroke:
            if (r, g, b) == self._current_color_stroke:
                return
            else:
                self._current_color_stroke = (r, g, b)
        else:
            if (r, g, b) == self._current_color:
                return
            else:
                self._current_color = (r, g, b)

        super().set_color_rgb(r, g, b, stroke)

    def set_font_size(self, font, size):
        if (font, size) == self._current_font:
            return
        self._current_font = (font, size)
        super().set_font_size(font, size)

    def set_alpha(self, alpha, stroke=False):
        if stroke:
            if alpha == self._current_alpha_stroke:
                return
            else:
                self._current_alpha_stroke = alpha
        else:
            if alpha == self._current_alpha:
                return
            else:
                self._current_alpha = alpha

        if alpha not in self._alpha_states:
            self._alpha_states[alpha] = pydyf.Dictionary()
            if stroke in (None, False):
                self._alpha_states[alpha]['ca'] = alpha
            if stroke in (None, True):
                self._alpha_states[alpha]['CA'] = alpha
        self.set_state(alpha)

    def add_font(self, font_hash, font_content, pango_font):
        self._document.fonts[font_hash] = Font(font_content, pango_font)
        return self._document.fonts[font_hash]

    def get_fonts(self):
        return self._document.fonts

    def add_transparency_group(self, bounding_box):
        alpha_states = pydyf.Dictionary()
        x_objects = pydyf.Dictionary()
        patterns = pydyf.Dictionary()
        shadings = pydyf.Dictionary()
        resources = pydyf.Dictionary({
            'ExtGState': alpha_states,
            'XObject': x_objects,
            'Pattern': patterns,
            'Shading': shadings,
            'Font': None,  # Will be set by _use_references
        })
        extra = pydyf.Dictionary({
            'Type': '/XObject',
            'Subtype': '/Form',
            'BBox': pydyf.Array(bounding_box),
            'Resources': resources,
            'Group': pydyf.Dictionary({
                'Type': '/Group',
                'S': '/Transparency',
                'I': 'true',
                'CS': '/DeviceRGB',
            }),
        })
        group = Stream(
            self._document, self.page_rectangle, alpha_states, x_objects,
            patterns, shadings, extra=extra)
        group.id = f'x{len(self._x_objects)}'
        self._x_objects[group.id] = group
        return group

    def add_image(self, pillow_image, image_rendering, optimize_image):
        if 'transparency' in pillow_image.info:
            pillow_image = pillow_image.convert('RGBA')
        elif pillow_image.mode in ('1', 'P'):
            pillow_image = pillow_image.convert('RGB')

        if pillow_image.mode in ('RGB', 'RGBA'):
            color_space = '/DeviceRGB'
        elif pillow_image.mode == 'L':
            color_space = '/DeviceGray'
        elif pillow_image.mode == 'CMYK':
            color_space = '/DeviceCMYK'
        else:
            LOGGER.warning('Unknown image mode: %s', pillow_image.mode)
            color_space = '/DeviceRGB'

        interpolate = 'true' if image_rendering == 'auto' else 'false'
        extra = pydyf.Dictionary({
            'Type': '/XObject',
            'Subtype': '/Image',
            'Width': pillow_image.width,
            'Height': pillow_image.height,
            'ColorSpace': color_space,
            'BitsPerComponent': 8,
            'Interpolate': interpolate,
        })

        image_file = io.BytesIO()
        if pillow_image.format == 'JPEG':
            extra['Filter'] = '/DCTDecode'
            pillow_image.save(
                image_file, format='JPEG', optimize=optimize_image)
        else:
            extra['Filter'] = '/JPXDecode'
            if pillow_image.mode == 'RGBA':
                alpha = pillow_image.getchannel('A')
                pillow_image = pillow_image.convert('RGB')
                alpha_file = io.BytesIO()
                alpha.save(
                    alpha_file, format='JPEG2000', optimize=optimize_image,
                    num_resolutions=1)
                extra['SMask'] = pydyf.Stream([alpha_file.getvalue()], extra={
                    'Filter': '/JPXDecode',
                    'Type': '/XObject',
                    'Subtype': '/Image',
                    'Width': pillow_image.width,
                    'Height': pillow_image.height,
                    'ColorSpace': '/DeviceGray',
                    'BitsPerComponent': 8,
                    'Interpolate': interpolate,
                })
            # Set number of resolutions to 1 because of
            # https://github.com/uclouvain/openjpeg/issues/215
            pillow_image.save(
                image_file, format='JPEG2000', optimize=optimize_image,
                num_resolutions=1)
        stream = [image_file.getvalue()]

        xobject = pydyf.Stream(stream, extra=extra)
        image_name = f'Im{len(self._x_objects)}'
        self._x_objects[image_name] = xobject
        return image_name

    def add_pattern(self, x, y, width, height, repeat_width, repeat_height,
                    matrix):
        alpha_states = pydyf.Dictionary()
        x_objects = pydyf.Dictionary()
        patterns = pydyf.Dictionary()
        shadings = pydyf.Dictionary()
        resources = pydyf.Dictionary({
            'ExtGState': alpha_states,
            'XObject': x_objects,
            'Pattern': patterns,
            'Shading': shadings,
            'Font': None,  # Will be set by _use_references
        })
        matrix = Matrix(1, 0, 0, 1, x, y) @ matrix
        extra = pydyf.Dictionary({
            'Type': '/Pattern',
            'PatternType': 1,
            'BBox': pydyf.Array([0, 0, width, height]),
            'XStep': repeat_width,
            'YStep': repeat_height,
            'TilingType': 1,
            'PaintType': 1,
            'Matrix': pydyf.Array(matrix.values),
            'Resources': resources,
        })
        pattern = Stream(
            self._document, self.page_rectangle, alpha_states, x_objects,
            patterns, shadings, extra=extra)
        pattern.id = f'p{len(self._patterns)}'
        self._patterns[pattern.id] = pattern
        return pattern

    def add_shading(self):
        shading = pydyf.Dictionary()
        shading.id = f's{len(self._shadings)}'
        self._shadings[shading.id] = shading
        return shading


BookmarkSubtree = collections.namedtuple(
    'BookmarkSubtree', ('label', 'destination', 'children', 'state'))


def _write_pdf_attachment(pdf, attachment, url_fetcher):
    """Write an attachment to the PDF stream.

    :return:
        the attachment PDF dictionary.

    """
    # Attachments from document links like <link> or <a> can only be URLs.
    # They're passed in as tuples
    url = ''
    if isinstance(attachment, tuple):
        url, description = attachment
        attachment = Attachment(
            url=url, url_fetcher=url_fetcher, description=description)
    elif not isinstance(attachment, Attachment):
        attachment = Attachment(guess=attachment, url_fetcher=url_fetcher)

    try:
        with attachment.source as (source_type, source, url, _):
            if isinstance(source, bytes):
                source = io.BytesIO(source)
            uncompressed_length = 0
            stream = b''
            md5 = hashlib.md5()
            compress = zlib.compressobj()
            for data in iter(lambda: source.read(4096), b''):
                uncompressed_length += len(data)
                md5.update(data)
                compressed = compress.compress(data)
                stream += compressed
            compressed = compress.flush(zlib.Z_FINISH)
            stream += compressed
            file_extra = pydyf.Dictionary({
                'Type': '/EmbeddedFile',
                'Filter': '/FlateDecode',
                'Params': pydyf.Dictionary({
                    'CheckSum': f'<{md5.hexdigest()}>',
                    'Size': uncompressed_length,
                })
            })
            file_stream = pydyf.Stream([stream], file_extra)
            pdf.add_object(file_stream)

    except URLFetchingError as exception:
        LOGGER.error('Failed to load attachment: %s', exception)
        return

    # TODO: Use the result object from a URL fetch operation to provide more
    # details on the possible filename.
    if url and urlsplit(url).path:
        filename = basename(unquote(urlsplit(url).path))
    else:
        filename = 'attachment.bin'

    attachment = pydyf.Dictionary({
        'Type': '/Filespec',
        'F': pydyf.String(),
        'UF': pydyf.String(filename),
        'EF': pydyf.Dictionary({'F': file_stream.reference}),
        'Desc': pydyf.String(attachment.description or ''),
    })
    pdf.add_object(attachment)
    return attachment


def create_bookmarks(bookmarks, pdf, parent=None):
    count = len(bookmarks)
    outlines = []
    for title, (page, x, y), children, state in bookmarks:
        destination = pydyf.Array((
            pdf.objects[pdf.pages['Kids'][page * 3]].reference,
            '/XYZ', x, y, 0))
        outline = pydyf.Dictionary({
            'Title': pydyf.String(title), 'Dest': destination})
        pdf.add_object(outline)
        children_outlines, children_count = create_bookmarks(
            children, pdf, parent=outline)
        outline['Count'] = children_count
        if state == 'closed':
            outline['Count'] *= -1
        else:
            count += children_count
        if outlines:
            outline['Prev'] = outlines[-1].reference
            outlines[-1]['Next'] = outline.reference
        if children_outlines:
            outline['First'] = children_outlines[0].reference
            outline['Last'] = children_outlines[-1].reference
        if parent is not None:
            outline['Parent'] = parent.reference
        outlines.append(outline)
    return outlines, count


def add_hyperlinks(links, anchors, matrix, pdf, page, names):
    """Include hyperlinks in current PDF page."""
    for link in links:
        link_type, link_target, rectangle, _ = link
        x1, y1 = matrix.transform_point(*rectangle[:2])
        x2, y2 = matrix.transform_point(*rectangle[2:])
        if link_type in ('internal', 'external'):
            annot = pydyf.Dictionary({
                'Type': '/Annot',
                'Subtype': '/Link',
                'Rect': pydyf.Array([x1, y1, x2, y2]),
                'BS': pydyf.Dictionary({'W': 0}),
            })
            if link_type == 'internal':
                annot['Dest'] = pydyf.String(link_target)
            else:
                annot['A'] = pydyf.Dictionary({
                    'Type': '/Action',
                    'S': '/URI',
                    'URI': pydyf.String(link_target),
                })
            pdf.add_object(annot)
            if 'Annots' not in page:
                page['Annots'] = pydyf.Array()
            page['Annots'].append(annot.reference)

    for anchor in anchors:
        anchor_name, x, y = anchor
        x, y = matrix.transform_point(x, y)
        names.append(pydyf.String(anchor_name))
        names.append(pydyf.Array([page.reference, '/XYZ', x, y, 0]))


def rectangle_aabb(matrix, pos_x, pos_y, width, height):
    """Apply a transformation matrix to an axis-aligned rectangle.

    Return its axis-aligned bounding box as ``(x1, y1, x2, y2)``.

    """
    transform_point = matrix.transform_point
    x1, y1 = transform_point(pos_x, pos_y)
    x2, y2 = transform_point(pos_x + width, pos_y)
    x3, y3 = transform_point(pos_x, pos_y + height)
    x4, y4 = transform_point(pos_x + width, pos_y + height)
    box_x1 = min(x1, x2, x3, x4)
    box_y1 = min(y1, y2, y3, y4)
    box_x2 = max(x1, x2, x3, x4)
    box_y2 = max(y1, y2, y3, y4)
    return box_x1, box_y1, box_x2, box_y2


def resolve_links(pages):
    """Resolve internal hyperlinks.

    Links to a missing anchor are removed with a warning.

    If multiple anchors have the same name, the first one is used.

    :returns:
        A generator yielding lists (one per page) like :attr:`Page.links`,
        except that ``target`` for internal hyperlinks is
        ``(page_number, x, y)`` instead of an anchor name.
        The page number is a 0-based index into the :attr:`pages` list,
        and ``x, y`` are in CSS pixels from the top-left of the page.

    """
    anchors = set()
    paged_anchors = []
    for i, page in enumerate(pages):
        paged_anchors.append([])
        for anchor_name, (point_x, point_y) in page.anchors.items():
            if anchor_name not in anchors:
                paged_anchors[-1].append((anchor_name, point_x, point_y))
                anchors.add(anchor_name)
    for page in pages:
        page_links = []
        for link in page.links:
            link_type, anchor_name, rectangle, _ = link
            if link_type == 'internal':
                if anchor_name not in anchors:
                    LOGGER.error(
                        'No anchor #%s for internal URI reference',
                        anchor_name)
                else:
                    page_links.append(
                        (link_type, anchor_name, rectangle, None))
            else:
                # External link
                page_links.append(link)
        yield page_links, paged_anchors.pop(0)


class Matrix(list):
    def __init__(self, a=1, b=0, c=0, d=1, e=0, f=0, matrix=None):
        if matrix is None:
            matrix = [[a, b, 0], [c, d, 0], [e, f, 1]]
        super().__init__(matrix)

    def __matmul__(self, other):
        assert len(self[0]) == len(other) == len(other[0]) == 3
        return Matrix(matrix=[
            [sum(self[i][k] * other[k][j] for k in range(3)) for j in range(3)]
            for i in range(len(self))])

    @property
    def determinant(self):
        assert len(self) == len(self[0]) == 3
        return (
            self[0][0] * (self[1][1] * self[2][2] - self[1][2] * self[2][1]) -
            self[1][0] * (self[0][1] * self[2][2] - self[0][2] * self[2][1]) +
            self[2][0] * (self[0][1] * self[1][2] - self[0][2] * self[1][1]))

    def transform_point(self, x, y):
        return (Matrix(matrix=[[x, y, 1]]) @ self)[0][:2]

    @property
    def values(self):
        (a, b), (c, d), (e, f) = [column[:2] for column in self]
        return a, b, c, d, e, f


class Page:
    """Represents a single rendered page.

    .. versionadded:: 0.15

    Should be obtained from :attr:`Document.pages` but not
    instantiated directly.

    """
    def __init__(self, page_box):
        #: The page width, including margins, in CSS pixels.
        self.width = page_box.margin_width()

        #: The page height, including margins, in CSS pixels.
        self.height = page_box.margin_height()

        #: The page bleed widths as a :obj:`dict` with ``'top'``, ``'right'``,
        #: ``'bottom'`` and ``'left'`` as keys, and values in CSS pixels.
        self.bleed = {
            side: page_box.style[f'bleed_{side}'].value
            for side in ('top', 'right', 'bottom', 'left')}

        #: The :obj:`list` of ``(bookmark_level, bookmark_label, target)``
        #: :obj:`tuples <tuple>`. ``bookmark_level`` and ``bookmark_label``
        #: are respectively an :obj:`int` and a :obj:`string <str>`, based on
        #: the CSS properties of the same names. ``target`` is an ``(x, y)``
        #: point in CSS pixels from the top-left of the page.
        self.bookmarks = []

        #: The :obj:`list` of ``(link_type, target, rectangle)`` :obj:`tuples
        #: <tuple>`. A ``rectangle`` is ``(x, y, width, height)``, in CSS
        #: pixels from the top-left of the page. ``link_type`` is one of three
        #: strings:
        #:
        #: * ``'external'``: ``target`` is an absolute URL
        #: * ``'internal'``: ``target`` is an anchor name (see
        #:   :attr:`Page.anchors`).
        #:   The anchor might be defined in another page,
        #:   in multiple pages (in which case the first occurence is used),
        #:   or not at all.
        #: * ``'attachment'``: ``target`` is an absolute URL and points
        #:   to a resource to attach to the document.
        self.links = []

        #: The :obj:`dict` mapping each anchor name to its target, an
        #: ``(x, y)`` point in CSS pixels from the top-left of the page.
        self.anchors = {}

        self._gather_links_and_bookmarks(page_box)
        self._page_box = page_box

    def _gather_links_and_bookmarks(self, box, parent_matrix=None):
        # Get box transformation matrix.
        # "Transforms apply to block-level and atomic inline-level elements,
        #  but do not apply to elements which may be split into
        #  multiple inline-level boxes."
        # http://www.w3.org/TR/css3-2d-transforms/#introduction
        if box.style['transform'] and not isinstance(box, boxes.InlineBox):
            border_width = box.border_width()
            border_height = box.border_height()
            origin_x, origin_y = box.style['transform_origin']
            offset_x = percentage(origin_x, border_width)
            offset_y = percentage(origin_y, border_height)
            origin_x = box.border_box_x() + offset_x
            origin_y = box.border_box_y() + offset_y

            matrix = Matrix(e=origin_x, f=origin_y)
            for name, args in box.style['transform']:
                a, b, c, d, e, f = 1, 0, 0, 1, 0, 0
                if name == 'scale':
                    a, d = args
                elif name == 'rotate':
                    a = d = math.cos(args)
                    b = math.sin(args)
                    c = -b
                elif name == 'translate':
                    e = percentage(args[0], border_width)
                    f = percentage(args[1], border_height)
                elif name == 'skew':
                    b, c = math.tan(args[1]), math.tan(args[0])
                else:
                    assert name == 'matrix'
                    a, b, c, d, e, f = args
                matrix = Matrix(a, b, c, d, e, f) @ matrix
            box.transformation_matrix = (
                Matrix(e=-origin_x, f=-origin_y) @ matrix)
            if parent_matrix:
                matrix = box.transformation_matrix @ parent_matrix
            else:
                matrix = box.transformation_matrix
        else:
            matrix = parent_matrix

        bookmark_label = box.bookmark_label
        if box.style['bookmark_level'] == 'none':
            bookmark_level = None
        else:
            bookmark_level = box.style['bookmark_level']
        state = box.style['bookmark_state']
        link = box.style['link']
        anchor_name = box.style['anchor']
        has_bookmark = bookmark_label and bookmark_level
        # 'link' is inherited but redundant on text boxes
        has_link = link and not isinstance(box, (boxes.TextBox, boxes.LineBox))
        # In case of duplicate IDs, only the first is an anchor.
        has_anchor = anchor_name and anchor_name not in self.anchors

        if has_bookmark or has_link or has_anchor:
            pos_x, pos_y, width, height = box.hit_area()
            if has_link:
                token_type, link = link
                assert token_type == 'url'
                link_type, target = link
                assert isinstance(target, str)
                if link_type == 'external' and box.is_attachment:
                    link_type = 'attachment'
                if matrix:
                    link = (
                        link_type, target,
                        rectangle_aabb(matrix, pos_x, pos_y, width, height),
                        box.download_name)
                else:
                    link = (
                        link_type, target,
                        (pos_x, pos_y, pos_x + width, pos_y + height),
                        box.download_name)
                self.links.append(link)
            if matrix and (has_bookmark or has_anchor):
                pos_x, pos_y = matrix.transform_point(pos_x, pos_y)
            if has_bookmark:
                self.bookmarks.append(
                    (bookmark_level, bookmark_label, (pos_x, pos_y), state))
            if has_anchor:
                self.anchors[anchor_name] = pos_x, pos_y

        for child in box.all_children():
            self._gather_links_and_bookmarks(child, matrix)

    def paint(self, context, left_x=0, top_y=0, scale=1, clip=False):
        """Paint the page into the PDF file.

        :type context: ``Context``
        :param context:
            A context object.
        :param float left_x:
            X coordinate of the left of the page, in PDF points.
        :param float top_y:
            Y coordinate of the top of the page, in PDF points.
        :param float scale:
            Zoom scale.
        :param bool clip:
            Whether to clip/cut content outside the page. If false or
            not provided, content can overflow.

        """
        with stacked(context):
            # Make (0, 0) the top-left corner, and make user units CSS pixels:
            context.transform(scale, 0, 0, scale, left_x, top_y)
            if clip:
                width = self.width
                height = self.height
                context.rectangle(0, 0, width, height)
                context.clip()
            draw_page(self._page_box, context)


class DocumentMetadata:
    """Meta-information belonging to a whole :class:`Document`.

    .. versionadded:: 0.20

    New attributes may be added in future versions of WeasyPrint.

    """
    def __init__(self, title=None, authors=None, description=None,
                 keywords=None, generator=None, created=None, modified=None,
                 attachments=None):
        #: The title of the document, as a string or :obj:`None`.
        #: Extracted from the ``<title>`` element in HTML
        #: and written to the ``/Title`` info field in PDF.
        self.title = title
        #: The authors of the document, as a list of strings.
        #: (Defaults to the empty list.)
        #: Extracted from the ``<meta name=author>`` elements in HTML
        #: and written to the ``/Author`` info field in PDF.
        self.authors = authors or []
        #: The description of the document, as a string or :obj:`None`.
        #: Extracted from the ``<meta name=description>`` element in HTML
        #: and written to the ``/Subject`` info field in PDF.
        self.description = description
        #: Keywords associated with the document, as a list of strings.
        #: (Defaults to the empty list.)
        #: Extracted from ``<meta name=keywords>`` elements in HTML
        #: and written to the ``/Keywords`` info field in PDF.
        self.keywords = keywords or []
        #: The name of one of the software packages
        #: used to generate the document, as a string or :obj:`None`.
        #: Extracted from the ``<meta name=generator>`` element in HTML
        #: and written to the ``/Creator`` info field in PDF.
        self.generator = generator
        #: The creation date of the document, as a string or :obj:`None`.
        #: Dates are in one of the six formats specified in
        #: `W3C’s profile of ISO 8601 <http://www.w3.org/TR/NOTE-datetime>`_.
        #: Extracted from the ``<meta name=dcterms.created>`` element in HTML
        #: and written to the ``/CreationDate`` info field in PDF.
        self.created = created
        #: The modification date of the document, as a string or :obj:`None`.
        #: Dates are in one of the six formats specified in
        #: `W3C’s profile of ISO 8601 <http://www.w3.org/TR/NOTE-datetime>`_.
        #: Extracted from the ``<meta name=dcterms.modified>`` element in HTML
        #: and written to the ``/ModDate`` info field in PDF.
        self.modified = modified
        #: File attachments, as a list of tuples of URL and a description or
        #: :obj:`None`. (Defaults to the empty list.)
        #: Extracted from the ``<link rel=attachment>`` elements in HTML
        #: and written to the ``/EmbeddedFiles`` dictionary in PDF.
        #:
        #: .. versionadded:: 0.22
        self.attachments = attachments or []


class Document:
    """A rendered document ready to be painted in a pydyf stream.

    Typically obtained from :meth:`HTML.render() <weasyprint.HTML.render>`, but
    can also be instantiated directly with a list of :class:`pages <Page>`, a
    set of :class:`metadata <DocumentMetadata>`, a :func:`url_fetcher
    <weasyprint.default_url_fetcher>` function, and a :class:`font_config
    <weasyprint.text.fonts.FontConfiguration>`.

    """

    @classmethod
    def _build_layout_context(cls, html, stylesheets,
                              presentational_hints=False,
                              optimize_images=False, font_config=None,
                              counter_style=None, image_cache=None):
        if font_config is None:
            font_config = FontConfiguration()
        if counter_style is None:
            counter_style = CounterStyle()
        target_collector = TargetCollector()
        page_rules = []
        user_stylesheets = []
        image_cache = {} if image_cache is None else image_cache
        for css in stylesheets or []:
            if not hasattr(css, 'matcher'):
                css = CSS(
                    guess=css, media_type=html.media_type,
                    font_config=font_config, counter_style=counter_style)
            user_stylesheets.append(css)
        style_for = get_all_computed_styles(
            html, user_stylesheets, presentational_hints, font_config,
            counter_style, page_rules, target_collector)
        get_image_from_uri = functools.partial(
            original_get_image_from_uri, image_cache, html.url_fetcher,
            optimize_images)
        PROGRESS_LOGGER.info('Step 4 - Creating formatting structure')
        context = LayoutContext(
            style_for, get_image_from_uri, font_config, counter_style,
            target_collector)
        return context

    @classmethod
    def _render(cls, html, stylesheets, presentational_hints=False,
                optimize_images=False, font_config=None, counter_style=None,
                image_cache=None):
        if font_config is None:
            font_config = FontConfiguration()

        if counter_style is None:
            counter_style = CounterStyle()

        context = cls._build_layout_context(
            html, stylesheets, presentational_hints, optimize_images,
            font_config, counter_style, image_cache)

        root_box = build_formatting_structure(
            html.etree_element, context.style_for, context.get_image_from_uri,
            html.base_url, context.target_collector, counter_style)

        page_boxes = layout_document(html, root_box, context)
        rendering = cls(
            [Page(page_box) for page_box in page_boxes],
            DocumentMetadata(**get_html_metadata(html)),
            html.url_fetcher, font_config)
        return rendering

    def _use_references(self, pdf, resources):
        # XObjects
        for key, x_object in resources.get('XObject', {}).items():
            pdf.add_object(x_object)
            resources['XObject'][key] = x_object.reference
            if 'SMask' in x_object.extra:
                pdf.add_object(x_object.extra['SMask'])
                x_object.extra['SMask'] = x_object.extra['SMask'].reference
            if 'Resources' in x_object.extra:
                if 'Font' in x_object.extra['Resources']:
                    x_object.extra['Resources']['Font'] = resources['Font']
                self._use_references(pdf, x_object.extra['Resources'])
                pdf.add_object(x_object.extra['Resources'])
                x_object.extra['Resources'] = (
                    x_object.extra['Resources'].reference)

        # Patterns
        for key, pattern in resources.get('Pattern', {}).items():
            pdf.add_object(pattern)
            resources['Pattern'][key] = pattern.reference
            if 'Resources' in pattern.extra:
                if 'Font' in pattern.extra['Resources']:
                    pattern.extra['Resources']['Font'] = resources['Font']
                self._use_references(pdf, pattern.extra['Resources'])
                pdf.add_object(pattern.extra['Resources'])
                pattern.extra['Resources'] = (
                    pattern.extra['Resources'].reference)

        # Shadings
        for key, shading in resources.get('Shading', {}).items():
            pdf.add_object(shading)
            resources['Shading'][key] = shading.reference

        # Alpha states
        for key, alpha in resources.get('ExtGState', {}).items():
            if 'SMask' in alpha and 'G' in alpha['SMask']:
                alpha['SMask']['G'] = alpha['SMask']['G'].reference

    def __init__(self, pages, metadata, url_fetcher, font_config):
        #: A list of :class:`Page` objects.
        self.pages = pages
        #: A :class:`DocumentMetadata` object.
        #: Contains information that does not belong to a specific page
        #: but to the whole document.
        self.metadata = metadata
        #: A function or other callable with the same signature as
        #: :func:`weasyprint.default_url_fetcher` called to fetch external
        #: resources such as stylesheets and images. (See :ref:`URL Fetchers`.)
        self.url_fetcher = url_fetcher
        #: A :obj:`dict` of fonts used by the document. Keys are hashes used to
        #: identify fonts, values are ``Font`` objects.
        self.fonts = {}
        # Keep a reference to font_config to avoid its garbage collection until
        # rendering is destroyed. This is needed as font_config.__del__ removes
        # fonts that may be used when rendering
        self._font_config = font_config

    def copy(self, pages='all'):
        """Take a subset of the pages.

        .. versionadded:: 0.15

        :type pages: :term:`iterable`
        :param pages:
            An iterable of :class:`Page` objects from :attr:`pages`.
        :return:
            A new :class:`Document` object.

        Examples:

        Write two PDF files for odd-numbered and even-numbered pages::

            # Python lists count from 0 but pages are numbered from 1.
            # [::2] is a slice of even list indexes but odd-numbered pages.
            document.copy(document.pages[::2]).write_pdf('odd_pages.pdf')
            document.copy(document.pages[1::2]).write_pdf('even_pages.pdf')

        Combine multiple documents into one PDF file,
        using metadata from the first::

            all_pages = [p for doc in documents for p in doc.pages]
            documents[0].copy(all_pages).write_pdf('combined.pdf')

        """
        if pages == 'all':
            pages = self.pages
        elif not isinstance(pages, list):
            pages = list(pages)
        return type(self)(
            pages, self.metadata, self.url_fetcher, self._font_config)

    def write_pdf(self, target=None, zoom=1, attachments=None, finisher=None):
        """Paint the pages in a PDF file, with metadata.

        :type target:
            :class:`str`, :class:`pathlib.Path` or :term:`file object`
        :param target:
            A filename where the PDF file is generated, a file object, or
            :obj:`None`.
        :param float zoom:
            The zoom factor in PDF units per CSS units.  **Warning**:
            All CSS units are affected, including physical units like
            ``cm`` and named sizes like ``A4``.  For values other than
            1, the physical CSS units will thus be "wrong".
        :param list attachments: A list of additional file attachments for the
            generated PDF document or :obj:`None`. The list's elements are
            ``Attachment`` objects, filenames, URLs or file-like objects.
        :param finisher: A finisher function, that accepts the document and a
            :class:`pydyf.PDF` object as parameters, can be passed to perform
            post-processing on the PDF right before the trailer is written.
        :returns:
            The PDF as :obj:`bytes` if ``target`` is not provided or
            :obj:`None`, otherwise :obj:`None` (the PDF is written to
            ``target``).

        """
        # 0.75 = 72 PDF point per inch / 96 CSS pixel per inch
        scale = zoom * 0.75

        PROGRESS_LOGGER.info('Step 6 - Creating PDF')

        pdf = pydyf.PDF()
        alpha_states = pydyf.Dictionary()
        x_objects = pydyf.Dictionary()
        patterns = pydyf.Dictionary()
        shadings = pydyf.Dictionary()
        resources = pydyf.Dictionary({
            'ExtGState': alpha_states,
            'XObject': x_objects,
            'Pattern': patterns,
            'Shading': shadings,
        })
        pdf.add_object(resources)
        pdf_names = pydyf.Array()

        # Links and anchors
        page_links_and_anchors = list(resolve_links(self.pages))
        attachment_links = [
            [link for link in page_links if link[0] == 'attachment']
            for page_links, page_anchors in page_links_and_anchors]

        # Annotations
        annot_files = {}
        # A single link can be split in multiple regions. We don't want to
        # embed a file multiple times of course, so keep a reference to every
        # embedded URL and reuse the object number.
        for page_links in attachment_links:
            for link_type, annot_target, rectangle, _ in page_links:
                if link_type == 'attachment' and target not in annot_files:
                    # TODO: Use the title attribute as description. The comment
                    # above about multiple regions won't always be correct,
                    # because two links might have the same href, but different
                    # titles.
                    annot_files[annot_target] = _write_pdf_attachment(
                        pdf, (annot_target, None), self.url_fetcher)

        # Bookmarks
        root = []
        # At one point in the document, for each "output" depth, how much
        # to add to get the source level (CSS values of bookmark-level).
        # E.g. with <h1> then <h3>, level_shifts == [0, 1]
        # 1 means that <h3> has depth 3 - 1 = 2 in the output.
        skipped_levels = []
        last_by_depth = [root]
        previous_level = 0

        for page_number, (page, links_and_anchors, page_links) in enumerate(
                zip(self.pages, page_links_and_anchors, attachment_links)):
            # Draw from the top-left corner
            matrix = Matrix(scale, 0, 0, -scale, 0, page.height * scale)

            # Links and anchors
            links, anchors = links_and_anchors

            page_width = scale * (
                page.width + page.bleed['left'] + page.bleed['right'])
            page_height = scale * (
                page.height + page.bleed['top'] + page.bleed['bottom'])
            left = -scale * page.bleed['left']
            top = -scale * page.bleed['top']
            right = left + page_width
            bottom = top + page_height

            page_rectangle = (
                left / scale, top / scale, right / scale, bottom / scale)
            stream = Stream(
                self, page_rectangle, alpha_states, x_objects, patterns,
                shadings)
            stream.transform(1, 0, 0, -1, 0, page.height * scale)
            page.paint(stream, scale=scale)
            pdf.add_object(stream)

            pdf_page = pydyf.Dictionary({
                'Type': '/Page',
                'Parent': pdf.pages.reference,
                'MediaBox': pydyf.Array([left, top, right, bottom]),
                'Contents': stream.reference,
                'Resources': resources.reference,
            })
            pdf.add_page(pdf_page)

            add_hyperlinks(links, anchors, matrix, pdf, pdf_page, pdf_names)

            # Bleed
            bleed = {key: value * 0.75 for key, value in page.bleed.items()}

            trim_left = left + bleed['left']
            trim_top = top + bleed['top']
            trim_right = right - bleed['right']
            trim_bottom = bottom - bleed['bottom']

            # Arbitrarly set PDF BleedBox between CSS bleed box (MediaBox) and
            # CSS page box (TrimBox) at most 10 points from the TrimBox.
            bleed_left = trim_left - min(10, bleed['left'])
            bleed_top = trim_top - min(10, bleed['top'])
            bleed_right = trim_right + min(10, bleed['right'])
            bleed_bottom = trim_bottom + min(10, bleed['bottom'])

            pdf_page['TrimBox'] = pydyf.Array([
                trim_left, trim_top, trim_right, trim_bottom])
            pdf_page['BleedBox'] = pydyf.Array([
                bleed_left, bleed_top, bleed_right, bleed_bottom])

            # Annotations
            # TODO: splitting a link into multiple independent rectangular
            # annotations works well for pure links, but rather mediocre for
            # other annotations and fails completely for transformed (CSS) or
            # complex link shapes (area). It would be better to use /AP for all
            # links and coalesce link shapes that originate from the same HTML
            # link. This would give a feeling similiar to what browsers do with
            # links that span multiple lines.
            for link_type, annot_target, rectangle, _ in page_links:
                annot_file = annot_files[annot_target]
                if link_type == 'attachment' and annot_file is not None:
                    rectangle = (
                        *matrix.transform_point(*rectangle[:2]),
                        *matrix.transform_point(*rectangle[2:]))
                    annot = pydyf.Dictionary({
                        'Type': '/Annot',
                        'Rect': pydyf.Array(rectangle),
                        'Subtype': '/FileAttachment',
                        'T': pydyf.String(),
                        'FS': annot_file.reference,
                        'AP': pydyf.Dictionary({'N': pydyf.Stream([], {
                            'Type': '/XObject',
                            'Subtype': '/Form',
                            'BBox': pydyf.Array(rectangle),
                            'Length': 0,
                        })})
                    })
                    pdf.add_object(annot)
                    if 'Annots' not in pdf_page:
                        pdf_page['Annots'] = pydyf.Array()
                    pdf_page['Annots'].append(annot.reference)

            # Bookmarks
            for level, label, (point_x, point_y), state in page.bookmarks:
                if level > previous_level:
                    # Example: if the previous bookmark is a <h2>, the next
                    # depth "should" be for <h3>. If now we get a <h6> we’re
                    # skipping two levels: append 6 - 3 - 1 = 2
                    skipped_levels.append(level - previous_level - 1)
                else:
                    temp = level
                    while temp < previous_level:
                        temp += 1 + skipped_levels.pop()
                    if temp > previous_level:
                        # We remove too many "skips", add some back:
                        skipped_levels.append(temp - previous_level - 1)

                previous_level = level
                depth = level - sum(skipped_levels)
                assert depth == len(skipped_levels)
                assert depth >= 1

                children = []
                point_x, point_y = matrix.transform_point(point_x, point_y)
                subtree = BookmarkSubtree(
                    label, (page_number, point_x, point_y), children, state)
                last_by_depth[depth - 1].append(subtree)
                del last_by_depth[depth:]
                last_by_depth.append(children)

        # Outlines
        outlines, count = create_bookmarks(root, pdf)
        if outlines:
            outlines_dictionary = pydyf.Dictionary({
                'Count': count,
                'First': outlines[0].reference,
                'Last': outlines[-1].reference,
            })
            pdf.add_object(outlines_dictionary)
            for outline in outlines:
                outline['Parent'] = outlines_dictionary.reference
            pdf.catalog['Outlines'] = outlines_dictionary.reference

        PROGRESS_LOGGER.info('Step 7 - Adding PDF metadata')

        # PDF information
        if self.metadata.title:
            pdf.info['Title'] = pydyf.String(self.metadata.title)
        if self.metadata.authors:
            pdf.info['Author'] = pydyf.String(
                ', '.join(self.metadata.authors))
        if self.metadata.description:
            pdf.info['Subject'] = pydyf.String(self.metadata.description)
        if self.metadata.keywords:
            pdf.info['Keywords'] = pydyf.String(
                ', '.join(self.metadata.keywords))
        if self.metadata.generator:
            pdf.info['Creator'] = pydyf.String(self.metadata.generator)
        pdf.info['Producer'] = pydyf.String(f'WeasyPrint {__version__}')
        if self.metadata.created:
            pdf.info['CreationDate'] = pydyf.String(
                _w3c_date_to_pdf(self.metadata.created, 'created'))
        if self.metadata.modified:
            pdf.info['ModDate'] = pydyf.String(
                _w3c_date_to_pdf(self.metadata.modified, 'modified'))

        # Embedded files
        attachments = self.metadata.attachments + (attachments or [])
        pdf_attachments = []
        for attachment in attachments:
            pdf_attachment = _write_pdf_attachment(
                pdf, attachment, self.url_fetcher)
            if pdf_attachment is not None:
                pdf_attachments.append(pdf_attachment)
        if pdf_attachments:
            content = pydyf.Dictionary({'Names': pydyf.Array()})
            for i, pdf_attachment in enumerate(pdf_attachments):
                content['Names'].append(pydyf.String(f'attachment{i}'))
                content['Names'].append(pdf_attachment.reference)
            pdf.add_object(content)
            if 'Names' not in pdf.catalog:
                pdf.catalog['Names'] = pydyf.Dictionary()
            pdf.catalog['Names']['EmbeddedFiles'] = content.reference

        # Embeded fonts
        pdf_fonts = pydyf.Dictionary()
        fonts_by_file_hash = {}
        for font in self.fonts.values():
            if font.file_hash in fonts_by_file_hash:
                fonts_by_file_hash[font.file_hash].append(font)
            else:
                fonts_by_file_hash[font.file_hash] = [font]
        font_references_by_file_hash = {}
        for file_hash, fonts in fonts_by_file_hash.items():
            # Optimize font
            cmap = {}
            for font in fonts:
                cmap = {**cmap, **font.cmap}
            full_font = io.BytesIO(fonts[0].file_content)
            optimized_font = io.BytesIO()
            try:
                ttfont = TTFont(full_font)
                options = subset.Options(
                    retain_gids=True, passthrough_tables=True)
                subsetter = subset.Subsetter(options)
                subsetter.populate(gids=cmap)
                subsetter.subset(ttfont)
                ttfont.save(optimized_font)
                content = optimized_font.getvalue()
            except TTLibError:
                content = fonts[0].file_content

            # Include font
            font_type = 'otf' if content[:4] == b'OTTO' else 'ttf'
            if font_type == 'otf':
                font_extra = pydyf.Dictionary({'Subtype': '/OpenType'})
            else:
                font_extra = pydyf.Dictionary({'Length1': len(content)})
            font_stream = pydyf.Stream([content], font_extra, compress=True)
            pdf.add_object(font_stream)
            font_references_by_file_hash[file_hash] = font_stream.reference

        for font in self.fonts.values():
            widths = pydyf.Array()
            for i in sorted(font.widths):
                if i - 1 not in font.widths:
                    widths.append(i)
                    current_widths = pydyf.Array()
                    widths.append(current_widths)
                current_widths.append(font.widths[i])
            font_descriptor = pydyf.Dictionary({
                'Type': '/FontDescriptor',
                'FontName': font.name,
                'FontFamily': pydyf.String(font.family),
                'Flags': font.flags,
                'FontBBox': pydyf.Array(font.bbox),
                'ItalicAngle': font.italic_angle,
                'Ascent': font.ascent,
                'Descent': font.descent,
                'CapHeight': font.bbox[3],
                'StemV': font.stemv,
                'StemH': font.stemh,
                (f'FontFile{"3" if font_type == "otf" else "2"}'):
                    font_references_by_file_hash[font.file_hash],
            })
            if font_type == 'otf':
                font_descriptor['Subtype'] = '/OpenType'
            pdf.add_object(font_descriptor)
            subfont_dictionary = pydyf.Dictionary({
                'Type': '/Font',
                'Subtype': f'/CIDFontType{"0" if font_type == "otf" else "2"}',
                'BaseFont': font.name,
                'CIDSystemInfo': pydyf.Dictionary({
                    'Registry': pydyf.String('Adobe'),
                    'Ordering': pydyf.String('Identity'),
                    'Supplement': 0,
                }),
                'W': widths,
                'FontDescriptor': font_descriptor.reference,
            })
            pdf.add_object(subfont_dictionary)
            to_unicode = pydyf.Stream([
                b'/CIDInit /ProcSet findresource begin',
                b'12 dict begin',
                b'begincmap',
                b'/CIDSystemInfo',
                b'<< /Registry (Adobe)',
                b'/Ordering (UCS)',
                b'/Supplement 0',
                b'>> def',
                b'/CMapName /Adobe-Identity-UCS def',
                b'/CMapType 2 def',
                b'1 begincodespacerange',
                b'<0000> <ffff>',
                b'endcodespacerange',
                f'{len(font.cmap)} beginbfchar'.encode('ascii')])
            for glyph, text in font.cmap.items():
                unicode_codepoints = ''.join(
                    f'{letter.encode("utf-16-be").hex()}' for letter in text)
                to_unicode.stream.append(
                    f'<{glyph:04x}> <{unicode_codepoints}>'.encode('ascii'))
            to_unicode.stream.extend([
                b'endbfchar',
                b'endcmap',
                b'CMapName currentdict /CMap defineresource pop',
                b'end',
                b'end'])
            pdf.add_object(to_unicode)
            font_dictionary = pydyf.Dictionary({
                'Type': '/Font',
                'Subtype': '/Type0',
                'BaseFont': font.name,
                'Encoding': '/Identity-H',
                'DescendantFonts': pydyf.Array([subfont_dictionary.reference]),
                'ToUnicode': to_unicode.reference,
            })
            pdf.add_object(font_dictionary)
            pdf_fonts[font.hash] = font_dictionary.reference

        pdf.add_object(pdf_fonts)
        resources['Font'] = pdf_fonts.reference
        self._use_references(pdf, resources)

        # Anchors
        if pdf_names:
            pdf.catalog['Names'] = pydyf.Dictionary(
                {'Dests': pydyf.Dictionary({'Names': pdf_names})})

        if finisher:
            finisher(self, pdf)

        file_obj = io.BytesIO()
        pdf.write(file_obj)

        if target is None:
            return file_obj.getvalue()
        else:
            file_obj.seek(0)
            if hasattr(target, 'write'):
                shutil.copyfileobj(file_obj, target)
            else:
                with open(target, 'wb') as fd:
                    shutil.copyfileobj(file_obj, fd)
