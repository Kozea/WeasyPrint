"""
    WeasyPrint
    ==========

    WeasyPrint converts web documents to PDF.

    The public API is what is accessible from this "root" packages
    without importing sub-modules.

    :copyright: Copyright 2011-2018 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import os
import sys
from pathlib import Path

import contextlib
import html5lib
import cssselect2
import tinycss2


if sys.version_info.major < 3:
    raise RuntimeError(
        'WeasyPrint does not support Python 2.x anymore. '
        'Please use Python 3 or install an older version of WeasyPrint.')

if hasattr(sys, 'frozen'):
    if hasattr(sys, '_MEIPASS'):
        # Frozen with PyInstaller
        # See https://github.com/Kozea/WeasyPrint/pull/540
        ROOT = sys._MEIPASS
    else:
        # Frozen with something else (py2exe, etc.)
        # See https://github.com/Kozea/WeasyPrint/pull/269
        ROOT = os.path.dirname(sys.executable)
else:
    ROOT = os.path.dirname(__file__)

with open(os.path.join(ROOT, 'VERSION')) as fp:
    VERSION = __version__ = fp.read().strip()

# Used for 'User-Agent' in HTTP and 'Creator' in PDF
VERSION_STRING = 'WeasyPrint %s (http://weasyprint.org/)' % VERSION

__all__ = ['HTML', 'CSS', 'Attachment', 'Document', 'Page',
           'default_url_fetcher', 'VERSION']


# Import after setting the version, as the version is used in other modules
from .urls import (fetch, default_url_fetcher, path2url, ensure_url,
                   url_is_absolute)  # noqa
from .logger import LOGGER  # noqa
# Some imports are at the end of the file (after the CSS class)
# to work around circular imports.


class HTML(object):
    """Represents an HTML document parsed by html5lib.

    You can just create an instance with a positional argument:
    ``doc = HTML(something)``
    The class will try to guess if the input is a filename, an absolute URL,
    or a file-like object.

    Alternatively, use **one** named argument so that no guessing is involved:

    :param filename: A filename, relative to the current directory, or
        absolute.
    :param url: An absolute, fully qualified URL.
    :param file_obj: A file-like: any object with a :meth:`~file.read` method.
    :param string: A string of HTML source. (This argument must be named.)

    Specifying multiple inputs is an error:
    ``HTML(filename="foo.html", url="localhost://bar.html")``
    will raise a TypeError.

    You can also pass optional named arguments:

    :param encoding: Force the source character encoding.
    :param base_url: The base used to resolve relative URLs
        (e.g. in ``<img src="../foo.png">``). If not provided, try to use
        the input filename, URL, or ``name`` attribute of file-like objects.
    :param url_fetcher: A function or other callable
        with the same signature as :func:`default_url_fetcher` called to
        fetch external resources such as stylesheets and images.
        (See :ref:`url-fetchers`.)
    :param media_type: The media type to use for ``@media``.
        Defaults to ``'print'``. **Note:** In some cases like
        ``HTML(string=foo)`` relative URLs will be invalid if ``base_url``
        is not provided.

    """
    def __init__(self, guess=None, filename=None, url=None, file_obj=None,
                 string=None, encoding=None, base_url=None,
                 url_fetcher=default_url_fetcher, media_type='print'):
        LOGGER.info(
            'Step 1 - Fetching and parsing HTML - %s',
            guess or filename or url or
            getattr(file_obj, 'name', 'HTML string'))
        result = _select_source(
            guess, filename, url, file_obj, string, base_url, url_fetcher)
        with result as (source_type, source, base_url, protocol_encoding):
            if isinstance(source, str):
                result = html5lib.parse(source, namespaceHTMLElements=False)
            else:
                result = html5lib.parse(
                    source, override_encoding=encoding,
                    transport_encoding=protocol_encoding,
                    namespaceHTMLElements=False)
            assert result
        self.base_url = find_base_url(result, base_url)
        self.url_fetcher = url_fetcher
        self.media_type = media_type
        self.wrapper_element = cssselect2.ElementWrapper.from_html_root(
            result, content_language=None)
        self.etree_element = self.wrapper_element.etree_element

    def _ua_stylesheets(self):
        return [HTML5_UA_STYLESHEET]

    def _ph_stylesheets(self):
        return [HTML5_PH_STYLESHEET]

    def _get_metadata(self):
        return get_html_metadata(self.wrapper_element, self.base_url)

    def render(self, stylesheets=None, enable_hinting=False,
               presentational_hints=False, font_config=None):
        """Lay out and paginate the document, but do not (yet) export it
        to PDF or another format.

        This returns a :class:`~document.Document` object which provides
        access to individual pages and various meta-data.
        See :meth:`write_pdf` to get a PDF directly.

        .. versionadded:: 0.15

        :param stylesheets:
            An optional list of user stylesheets. List elements are
            :class:`CSS` objects, filenames, URLs, or file-like
            objects. (See :ref:`stylesheet-origins`.)
        :type enable_hinting: bool
        :param enable_hinting:
            Whether text, borders and background should be *hinted* to fall
            at device pixel boundaries. Should be enabled for pixel-based
            output (like PNG) but not for vector-based output (like PDF).
        :type presentational_hints: bool
        :param presentational_hints: Whether HTML presentational hints are
            followed.
        :type font_config: :class:`~fonts.FontConfiguration`
        :param font_config: A font configuration handling @font-face rules.
        :returns: A :class:`~document.Document` object.

        """
        return Document._render(
            self, stylesheets, enable_hinting, presentational_hints,
            font_config)

    def write_pdf(self, target=None, stylesheets=None, zoom=1,
                  attachments=None, presentational_hints=False,
                  font_config=None):
        """Render the document to a PDF file.

        This is a shortcut for calling :meth:`render`, then
        :meth:`Document.write_pdf() <document.Document.write_pdf>`.

        :param target:
            A filename, file-like object, or :obj:`None`.
        :param stylesheets:
            An optional list of user stylesheets. The list's elements
            are :class:`CSS` objects, filenames, URLs, or file-like
            objects.  (See :ref:`stylesheet-origins`.)
        :type zoom: float
        :param zoom:
            The zoom factor in PDF units per CSS units.  **Warning**:
            All CSS units are affected, including physical units like
            ``cm`` and named sizes like ``A4``.  For values other than
            1, the physical CSS units will thus be "wrong".
        :param attachments: A list of additional file attachments for the
            generated PDF document or :obj:`None`. The list's elements are
            :class:`Attachment` objects, filenames, URLs or file-like objects.
        :type presentational_hints: bool
        :param presentational_hints: Whether HTML presentational hints are
            followed.
        :type font_config: :class:`~fonts.FontConfiguration`
        :param font_config: A font configuration handling @font-face rules.
        :returns:
            The PDF as byte string if :obj:`target` is not provided or
            :obj:`None`, otherwise :obj:`None` (the PDF is written to
            :obj:`target`).

        """
        return self.render(
            stylesheets, enable_hinting=False,
            presentational_hints=presentational_hints,
            font_config=font_config).write_pdf(
                target, zoom, attachments)

    def write_image_surface(self, stylesheets=None, resolution=96,
                            presentational_hints=False, font_config=None):
        surface, _width, _height = (
            self.render(stylesheets, enable_hinting=True,
                        presentational_hints=presentational_hints,
                        font_config=font_config)
            .write_image_surface(resolution))
        return surface

    def write_png(self, target=None, stylesheets=None, resolution=96,
                  presentational_hints=False, font_config=None):
        """Paint the pages vertically to a single PNG image.

        There is no decoration around pages other than those specified in CSS
        with ``@page`` rules. The final image is as wide as the widest page.
        Each page is below the previous one, centered horizontally.

        This is a shortcut for calling :meth:`render`, then
        :meth:`Document.write_png() <document.Document.write_png>`.

        :param target:
            A filename, file-like object, or :obj:`None`.
        :param stylesheets:
            An optional list of user stylesheets.  The list's elements
            are :class:`CSS` objects, filenames, URLs, or file-like
            objects. (See :ref:`stylesheet-origins`.)
        :type resolution: float
        :param resolution:
            The output resolution in PNG pixels per CSS inch. At 96 dpi
            (the default), PNG pixels match the CSS ``px`` unit.
        :type presentational_hints: bool
        :param presentational_hints: Whether HTML presentational hints are
            followed.
        :type font_config: :class:`~fonts.FontConfiguration`
        :param font_config: A font configuration handling @font-face rules.
        :returns:
            The image as byte string if :obj:`target` is not provided or
            :obj:`None`, otherwise :obj:`None` (the image is written to
            :obj:`target`.)

        """
        png_bytes, _width, _height = (
            self.render(stylesheets, enable_hinting=True,
                        presentational_hints=presentational_hints,
                        font_config=font_config)
            .write_png(target, resolution))
        return png_bytes


class CSS(object):
    """Represents a CSS stylesheet parsed by tinycss2.

    An instance is created in the same way as :class:`HTML`, except that
    the ``tree`` argument is not available. All other arguments are the same.

    An additional argument called ``font_config`` must be provided to handle
    ``@font-config`` rules. The same ``fonts.FontConfiguration`` object must be
    used for different ``CSS`` objects applied to the same document.

    ``CSS`` objects have no public attribute or method. They are only meant to
    be used in the :meth:`~HTML.write_pdf`, :meth:`~HTML.write_png` and
    :meth:`~HTML.render` methods of :class:`HTML` objects.

    """
    def __init__(self, guess=None, filename=None, url=None, file_obj=None,
                 string=None, encoding=None, base_url=None,
                 url_fetcher=default_url_fetcher, _check_mime_type=False,
                 media_type='print', font_config=None, matcher=None,
                 page_rules=None):
        LOGGER.info(
            'Step 2 - Fetching and parsing CSS - %s',
            filename or url or getattr(file_obj, 'name', 'CSS string'))
        result = _select_source(
            guess, filename, url, file_obj, string,
            base_url=base_url, url_fetcher=url_fetcher,
            check_css_mime_type=_check_mime_type)
        with result as (source_type, source, base_url, protocol_encoding):
            if source_type == 'string' and not isinstance(source, bytes):
                # unicode, no encoding
                stylesheet = tinycss2.parse_stylesheet(source)
            else:
                if source_type == 'file_obj':
                    source = source.read()
                stylesheet, encoding = tinycss2.parse_stylesheet_bytes(
                    source, environment_encoding=encoding,
                    protocol_encoding=protocol_encoding)
        self.base_url = base_url
        self.matcher = matcher or cssselect2.Matcher()
        self.page_rules = [] if page_rules is None else page_rules
        # TODO: fonts are stored here and should be cleaned after rendering
        self.fonts = []
        preprocess_stylesheet(
            media_type, base_url, stylesheet, url_fetcher, self.matcher,
            self.page_rules, self.fonts, font_config)


class Attachment(object):
    """Represents a file attachment for a PDF document.

    An instance is created in the same way as :class:`HTML`, except that
    the HTML specific arguments are not supported. An optional description can
    be provided with the ``description`` argument.

    :param description: A description of the attachment to be included in the
        PDF document. May be :obj:`None`

    """
    def __init__(self, guess=None, filename=None, url=None, file_obj=None,
                 string=None, base_url=None, url_fetcher=default_url_fetcher,
                 description=None):
        self.source = _select_source(
            guess, filename, url, file_obj, string,
            base_url=base_url, url_fetcher=url_fetcher)
        self.description = description


@contextlib.contextmanager
def _select_source(guess=None, filename=None, url=None, file_obj=None,
                   string=None, base_url=None, url_fetcher=default_url_fetcher,
                   check_css_mime_type=False):
    """
    Check that only one input is not None, and return it with the
    normalized ``base_url``.

    """
    if base_url is not None:
        base_url = ensure_url(base_url)

    selected_params = [
        param for param in (guess, filename, url, file_obj, string) if
        param is not None]
    if len(selected_params) != 1:
        raise TypeError('Expected exactly one source, got ' + (
            ', '.join(selected_params) or 'nothing'
        ))
    elif guess is not None:
        if hasattr(guess, 'read'):
            type_ = 'file_obj'
        elif isinstance(guess, Path):
            type_ = 'filename'
        elif url_is_absolute(guess):
            type_ = 'url'
        else:
            type_ = 'filename'
        result = _select_source(
            base_url=base_url, url_fetcher=url_fetcher,
            check_css_mime_type=check_css_mime_type,
            **{type_: guess})
        with result as result:
            yield result
    elif filename is not None:
        if isinstance(filename, Path):
            filename = str(filename)
        if base_url is None:
            base_url = path2url(filename)
        with open(filename, 'rb') as file_obj:
            yield 'file_obj', file_obj, base_url, None
    elif url is not None:
        with fetch(url_fetcher, url) as result:
            if check_css_mime_type and result['mime_type'] != 'text/css':
                LOGGER.error(
                    'Unsupported stylesheet type %s for %s',
                    result['mime_type'], result['redirected_url'])
                yield 'string', '', base_url, None
            else:
                proto_encoding = result.get('encoding')
                if base_url is None:
                    base_url = result.get('redirected_url', url)
                if 'string' in result:
                    yield 'string', result['string'], base_url, proto_encoding
                else:
                    yield (
                        'file_obj', result['file_obj'], base_url,
                        proto_encoding)
    elif file_obj is not None:
        if base_url is None:
            # filesystem file-like objects have a 'name' attribute.
            name = getattr(file_obj, 'name', None)
            # Some streams have a .name like '<stdin>', not a filename.
            if name and not name.startswith('<'):
                base_url = ensure_url(name)
        yield 'file_obj', file_obj, base_url, None
    elif string is not None:
        yield 'string', string, base_url, None
    else:
        sources = dict(locals())
        sources_names = ', '.join(
            name for name in ('guess', 'filename', 'url', 'file_obj', 'string')
            if sources[name] is not None) or 'nothing'
        raise TypeError('Expected exactly one source, got ' + sources_names)

# Work around circular imports.
from .css import preprocess_stylesheet  # noqa
from .html import (
    find_base_url, HTML5_UA_STYLESHEET, HTML5_PH_STYLESHEET,
    get_html_metadata)  # noqa
from .document import Document, Page  # noqa
