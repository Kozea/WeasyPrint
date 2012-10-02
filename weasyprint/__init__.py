# coding: utf8
"""
    WeasyPrint
    ==========

    WeasyPrint converts web documents to PDF.

    The public API is what is accessible from this "root" packages
    without importing sub-modules.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals


VERSION = '0.15'
__version__ = VERSION

# Used for 'User-Agent' in HTTP and 'Creator' in PDF
VERSION_STRING = 'WeasyPrint %s (http://weasyprint.org/)' % VERSION

import io
import sys


from .urls import default_url_fetcher
# Make sure the logger is configured early:
from .logger import LOGGER

# No other import here. For this module, do them in functions/methods instead.
# (This reduces the work for eg. 'weasyprint --help')


class HTML(object):
    """Represents an HTML document parsed by `lxml <http://lxml.de/>`_.

    You can just create an instance with a positional argument:
    ``doc = HTML(something)``
    The class will try to guess if the input is a filename, an absolute URL,
    or a file-like object.

    Alternatively, use **one** named argument so that no guessing is involved:

    :param filename: A filename, relative to the current directory or absolute.
    :param url: An absolute, fully qualified URL.
    :param file_obj: a file-like: any object with a :meth:`~file.read` method.
    :param string: a string of HTML source. (This argument must be named.)
    :param tree: a parsed lxml tree. (This argument must be named.)

    Specifying multiple inputs is an error: ``HTML(filename=foo, url=bar)``
    will raise.

    You can also pass optional named arguments:

    :param encoding: Force the source character encoding.
    :param base_url: The base used to resolve relative URLs
        (eg. in ``<img src="../foo.png">``). If not provided, try to use
        the input filename, URL, or ``name`` attribute of file objects.
    :param url_fetcher: The URL fetcher function. (See :ref:`url-fetchers`.)
    :param media_type: The media type to use for ``@media``.
        Defaults to ``'print'``. **Note:** In some cases like
        ``HTML(string=foo)`` relative URLs will be invalid if ``base_url``
        is not provided.

    """
    def __init__(self, guess=None, filename=None, url=None, file_obj=None,
                 string=None, tree=None, encoding=None, base_url=None,
                 url_fetcher=default_url_fetcher, media_type='print'):
        import lxml.html
        from .html import find_base_url
        from .urls import wrap_url_fetcher
        url_fetcher = wrap_url_fetcher(url_fetcher)

        source_type, source, base_url, protocol_encoding = _select_source(
            guess, filename, url, file_obj, string, tree, base_url,
            url_fetcher)

        if source_type == 'tree':
            result = source
        else:
            if source_type == 'string':
                parse = lxml.html.document_fromstring
            else:
                parse = lxml.html.parse
            if not encoding:
                encoding = protocol_encoding
            parser = lxml.html.HTMLParser(encoding=encoding)
            result = parse(source, parser=parser)
            if result is None:
                raise ValueError('Error while parsing HTML')
        base_url = find_base_url(result, base_url)
        if hasattr(result, 'getroot'):
            result.docinfo.URL = base_url
            result = result.getroot()
        else:
            result.getroottree().docinfo.URL = base_url
        self.root_element = result
        self.base_url = base_url
        self.url_fetcher = url_fetcher
        self.media_type = media_type

    def _ua_stylesheets(self):
        from .html import HTML5_UA_STYLESHEET
        return [HTML5_UA_STYLESHEET]

    def render(self, stylesheets=None, enable_hinting=False, resolution=96):
        """Render the document and return a list of Page objects.

        This is the low-level API. It provides individual pages that can
        paint to any type of cairo surface.

        :param stylesheets:
            An optional list of user stylesheets. (See
            :ref:`stylesheet-origins`\.) List elements are :class:`CSS`
            objects, filenames, URLs, or file-like objects.
        :type enable_hinting: bool
        :param enable_hinting:
            Whether text, borders and background should be *hinted* to fall
            at device pixel boundaries. Should be enabled for pixel-based
            output (like PNG) but not vector based output (like PDF).
        :type resolution: float
        :param resolution:
            The output resolution in cairo user units per CSS inch. At 96 dpi
            (the default), user units match the CSS ``px`` unit.
            For example, :class:`cairo.PDFSurface`’s device units are
            in PostScript points (72dpi), so ``resolution=72`` will set
            the right scale for physical units.
        :returns: A list of :class:`Page` objects.

        """
        import functools
        from .css import get_all_computed_styles
        from .formatting_structure.build import build_formatting_structure
        from .layout import layout_document
        from . import images

        style_for = get_all_computed_styles(self, user_stylesheets=[
            css if hasattr(css, 'rules')
            else CSS(guess=css, media_type=self.media_type)
            for css in stylesheets or []])
        get_image_from_uri =  functools.partial(
            images.get_image_from_uri, {}, self.url_fetcher)
        page_boxes = layout_document(
            enable_hinting, style_for, get_image_from_uri,
            build_formatting_structure(
                self.root_element, style_for, get_image_from_uri))
        return [Page(p, enable_hinting, resolution) for p in page_boxes]

    def write_pdf(self, target=None, stylesheets=None):
        """Render the document to PDF.

        :param target:
            Where the PDF output is written.
            A filename or a file-like object (anything with a
            :meth:`~file.write` method) or :obj:`None`.
        :param stylesheets:
            An optional list of user stylesheets. (See
            :ref:`stylesheet-origins`\.) The list’s elements are
            :class:`CSS` objects, filenames, URLs, or file-like objects.
        :returns:
            If :obj:`target` is :obj:`None`, a PDF byte string.

        """
        pages = self.render(stylesheets, enable_hinting=False, resolution=72)
        return pages_to_pdf(pages, target)

    def write_png(self, target=None, stylesheets=None, resolution=96):
        """Render the document to a single PNG image.

        Pages are arranged vertically without any decoration.

        :param target:
            Where the PNG output is written.
            A filename or a file-like object (anything with a
            :meth:`~file.write` method) or :obj:`None`.
        :param stylesheets:
            An optional list of user stylesheets. (See
            :ref:`stylesheet-origins`\.) The list’s elements are
            :class:`CSS` objects, filenames, URLs, or file-like objects.
        :type resolution: float
        :param resolution:
            The output resolution in PNG pixels per CSS inch. At 96 dpi
            (the default), PNG pixels match the CSS ``px`` unit.
        :returns:
            If :obj:`target` is :obj:`None`, a PNG byte string.

        """
        pages = self.render(stylesheets, enable_hinting=True,
                            resolution=resolution)
        return pages_to_png(pages, target)


class CSS(object):
    """Represents a CSS stylesheet parsed by tinycss.

    An instance is created in the same way as :class:`HTML`, except that
    the ``tree`` parameter is not available. All other parameters are the same.

    ``CSS`` objects have no public attribute or method. They are only meant to
    be used in methods such as ``write_pdf`` or ``write_png``. (See above.)

    """
    def __init__(self, guess=None, filename=None, url=None, file_obj=None,
                 string=None, encoding=None, base_url=None,
                 url_fetcher=default_url_fetcher, _check_mime_type=False,
                 media_type='print'):
        from .css import PARSER, preprocess_stylesheet

        source_type, source, base_url, protocol_encoding = _select_source(
            guess, filename, url, file_obj, string, tree=None,
            base_url=base_url, url_fetcher=url_fetcher,
            check_css_mime_type=_check_mime_type,)

        kwargs = dict(linking_encoding=encoding,
                      protocol_encoding=protocol_encoding)
        if source_type == 'string':
            if isinstance(source, bytes):
                method = 'parse_stylesheet_bytes'
            else:
                # unicode, no encoding
                method = 'parse_stylesheet'
                kwargs.clear()
        else:
            # file_obj or filename
            method = 'parse_stylesheet_file'
        # TODO: do not keep this?
        self.stylesheet = getattr(PARSER, method)(source, **kwargs)
        self.base_url = base_url
        self.rules = list(preprocess_stylesheet(
            media_type, base_url, self.stylesheet.rules, url_fetcher))
        for error in self.stylesheet.errors:
            LOGGER.warn(error)


def _select_source(guess=None, filename=None, url=None, file_obj=None,
                   string=None, tree=None, base_url=None,
                   url_fetcher=default_url_fetcher, check_css_mime_type=False):
    """
    Check that only one input is not None, and return it with the
    normalized ``base_url``.

    """
    from .urls import path2url, ensure_url, url_is_absolute
    from .urls import wrap_url_fetcher
    url_fetcher = wrap_url_fetcher(url_fetcher)

    if base_url is not None:
        base_url = ensure_url(base_url)

    nones = [guess is None, filename is None, url is None,
             file_obj is None, string is None, tree is None]
    if nones == [False, True, True, True, True, True]:
        if hasattr(guess, 'read'):
            type_ = 'file_obj'
        elif url_is_absolute(guess):
            type_ = 'url'
        else:
            type_ = 'filename'
        return _select_source(
            base_url=base_url, url_fetcher=url_fetcher,
            check_css_mime_type=check_css_mime_type,
            **{type_: guess})
    if nones == [True, False, True, True, True, True]:
        if base_url is None:
            base_url = path2url(filename)
        return 'filename', filename, base_url, None
    if nones == [True, True, False, True, True, True]:
        result = url_fetcher(url)
        if check_css_mime_type and result['mime_type'] != 'text/css':
            LOGGER.warn('Unsupported stylesheet type %s for %s',
                result['mime_type'], result['redirected_url'])
            return 'string', '', base_url, None
        protocol_encoding = result.get('encoding')
        if base_url is None:
            base_url = result.get('redirected_url', url)
        if 'string' in result:
            return 'string', result['string'], base_url, protocol_encoding
        else:
            return 'file_obj', result['file_obj'], base_url, protocol_encoding
    if nones == [True, True, True, False, True, True]:
        if base_url is None:
            # filesystem file objects have a 'name' attribute.
            name = getattr(file_obj, 'name', None)
            # Some streams have a .name like '<stdin>', not a filename.
            if name and not name.startswith('<'):
                base_url = ensure_url(name)
        return 'file_obj', file_obj, base_url, None
    if nones == [True, True, True, True, False, True]:
        return 'string', string, base_url, None
    if nones == [True, True, True, True, True, False]:
        return 'tree', tree, base_url, None

    raise TypeError('Expected exactly one source, got %i' % nones.count(False))


class Page(object):
    """Represents a single rendered page."""
    def __init__(self, page, enable_hinting=False, resolution=96):
        self._page_box = page
        self._enable_hinting = enable_hinting
        self._dppx = resolution / 96
        #: The page width, including margins, in cairo user units.
        self.width = page.margin_width() * self._dppx
        #: The page height, including margins, in cairo user units.
        self.height = page.margin_height() * self._dppx

    def paint(self, cairo_context, left_x=0, top_y=0, clip=False):
        """Paint the surface in cairo, on any type of surface.

        :param cairo_context: any :class:`cairo.Context` object.
        :type left_x: float
        :param left_x:
            X coordinate of the left of the page, in user units.
        :type top_y: float
        :param top_y:
            Y coordinate of the top of the page, in user units.
        :type clip: bool
        :param clip:
            Whether to clip/cut content outside the page. If false or
            not provided, content can overflow.

        """
        from .draw import draw_page, stacked
        with stacked(cairo_context):
            if self._enable_hinting:
                from math import ceil
                left_x, top_y = cairo_context.user_to_device(left_x, top_y)
                width, height = cairo_context.user_to_device_distance(
                    self.width, self.height)
                # Hint in device space
                left_x = int(left_x)
                top_y = int(top_y)
                width = int(ceil(width))
                height = int(ceil(height))
                left_x, top_y = cairo_context.device_to_user(left_x, top_y)
                width, height = cairo_context.device_to_user_distance(
                    width, height)
            else:
                width = self.width
                height = self.height
            cairo_context.translate(left_x, top_y)
            # The top-left corner is now (0, 0)
            if clip:
                cairo_context.rectangle(0, 0, width, height)
                cairo_context.clip()
            cairo_context.scale(self._dppx, self._dppx)
            # User units are now CSS pixels
            draw_page(self._page_box, cairo_context, self._enable_hinting)


def pages_to_pdf(pages, target=None):
    """Paint pages; write PDF bytes to ``target``, or return them
    if ``target`` is ``None``.

    This function also adds PDF metadata (bookmarks/outlines, hyperlinks, …).
    PDF files coming straight from :class:`cairo.PDFSurface` do not have
    such metadata.

    :param pages: a list of Page objects
    :param target: a filename, file object, or ``None``
    :returns: a bytestring if ``target`` is ``None``.

    """
    import shutil
    import cairo
    from .pdf import write_pdf_metadata

    # Use an in-memory buffer. We will need to seek for metadata
    # TODO: avoid this if target can seek? Benchmark first.
    file_obj = io.BytesIO()
    # (1, 1) is overridden by .set_size() below.
    surface = cairo.PDFSurface(file_obj, 1, 1)
    context = cairo.Context(surface)
    for page in pages:
        surface.set_size(page.width, page.height)
        page.paint(context)
        surface.show_page()
    surface.finish()

    write_pdf_metadata(pages, file_obj)

    if target is None:
        return file_obj.getvalue()
    else:
        file_obj.seek(0)
        if hasattr(target, 'write'):
            shutil.copyfileobj(file_obj, target)
        else:
            with open(target, 'wb') as fd:
                shutil.copyfileobj(file_obj, fd)


def pages_to_image_surface(pages):
    """Paint pages vertically for pixel output.

    :param pages: a list of :class:`~weasyprint.Page` objects
    :returns: a :class:`cairo.ImageSurface` object

    """
    import math
    import cairo
    from .draw import stacked
    from .compat import izip

    # This duplicates the hinting logic in Page.paint. There is a dependency
    # cycle otherwise: this → hinting logic → context → surface → this
    # But since we do no transform here, cairo_context.user_to_device and
    # friends are identity functions.
    widths = [int(math.ceil(p.width)) for p in pages]
    heights = [int(math.ceil(p.height)) for p in pages]
    max_width = max(widths)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, max_width, sum(heights))
    context = cairo.Context(surface)

    pos_y = 0
    for page, width, height in izip(pages, widths, heights):
        pos_x = (max_width - width) / 2
        with stacked(context):
            page.paint(context, pos_x, pos_y, clip=True)
        pos_y += height
    return surface


def surface_to_png(surface, target=None):
    """Write PNG bytes to ``target``, or return them if ``target`` is ``None``.

    :param surface: a :class:`cairo.ImageSurface` object
    :param target: a filename, file object, or ``None``
    :returns: a bytestring if ``target`` is ``None``.

    """
    from .urls import FILESYSTEM_ENCODING

    if target is None:
        target = io.BytesIO()
        surface.write_to_png(target)
        return target.getvalue()
    else:
        if sys.version_info[0] < 3 and isinstance(target, unicode):
            # py2cairo 1.8 does not support unicode filenames.
            target = target.encode(FILESYSTEM_ENCODING)
        surface.write_to_png(target)


def pages_to_png(pages, target=None):
    """Paint pages vertically; write PNG bytes to ``target``, or return them
    if ``target`` is ``None``.

    :param pages: a list of :class:`~weasyprint.Page` objects
    :param target: a filename, file object, or ``None``
    :returns: a bytestring if ``target`` is ``None``.

    """
    return surface_to_png(pages_to_image_surface(pages), target)
