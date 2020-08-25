"""
    WeasyPrint
    ==========

    WeasyPrint converts web documents to PDF.

    The public API is what is accessible from this "root" packages
    without importing sub-modules.

"""

import contextlib
import os
import sys
from pathlib import Path

import cssselect2
import html5lib
import tinycss2

if sys.version_info.major < 3:  # pragma: no cover
    raise RuntimeError(
        'WeasyPrint does not support Python 2.x anymore. '
        'Please use Python 3 or install an older version of WeasyPrint.')

if hasattr(sys, 'frozen'):  # pragma: no cover
    if hasattr(sys, '_MEIPASS'):
        # Frozen with PyInstaller
        # See https://github.com/Kozea/WeasyPrint/pull/540
        ROOT = Path(sys._MEIPASS) / 'weasyprint'
    else:
        # Frozen with something else (py2exe, etc.)
        # See https://github.com/Kozea/WeasyPrint/pull/269
        ROOT = Path(os.path.dirname(sys.executable))
else:
    ROOT = Path(os.path.dirname(__file__))

VERSION = __version__ = (ROOT / 'VERSION').read_text().strip()

# Used for 'User-Agent' in HTTP and 'Creator' in PDF
VERSION_STRING = 'WeasyPrint %s (http://weasyprint.org/)' % VERSION

__all__ = ['HTML', 'CSS', 'Attachment', 'Document', 'Page',
           'default_url_fetcher', 'VERSION']


# Import after setting the version, as the version is used in other modules
from .urls import (  # noqa isort:skip
    fetch, default_url_fetcher, path2url, ensure_url, url_is_absolute)
from .logger import LOGGER, PROGRESS_LOGGER  # noqa isort:skip
# Some imports are at the end of the file (after the CSS class)
# to work around circular imports.


class HTML:
    """Represents an HTML document parsed by html5lib.

    You can just create an instance with a positional argument:
    ``doc = HTML(something)``
    The class will try to guess if the input is a filename, an absolute URL,
    or a :term:`file object`.

    Alternatively, use **one** named argument so that no guessing is involved:

    :type filename: str or pathlib.Path
    :param filename: A filename, relative to the current directory, or
        absolute.
    :type url: str
    :param url: An absolute, fully qualified URL.
    :type file_obj: :term:`file object`
    :param file_obj: Any object with a ``read`` method.
    :type string: str
    :param string: A string of HTML source.

    Specifying multiple inputs is an error:
    ``HTML(filename="foo.html", url="localhost://bar.html")``
    will raise a :obj:`TypeError`.

    You can also pass optional named arguments:

    :type encoding: str
    :param encoding: Force the source character encoding.
    :type base_url: str
    :param base_url: The base used to resolve relative URLs
        (e.g. in ``<img src="../foo.png">``). If not provided, try to use
        the input filename, URL, or ``name`` attribute of :term:`file objects
        <file object>`.
    :type url_fetcher: function
    :param url_fetcher: A function or other callable
        with the same signature as :func:`default_url_fetcher` called to
        fetch external resources such as stylesheets and images.
        (See :ref:`url-fetchers`.)
    :type media_type: str
    :param media_type: The media type to use for ``@media``.
        Defaults to ``'print'``. **Note:** In some cases like
        ``HTML(string=foo)`` relative URLs will be invalid if ``base_url``
        is not provided.

    """
    def __init__(self, guess=None, filename=None, url=None, file_obj=None,
                 string=None, encoding=None, base_url=None,
                 url_fetcher=default_url_fetcher, media_type='print'):
        PROGRESS_LOGGER.info(
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
        self.base_url = find_base_url(result, base_url)
        self.url_fetcher = url_fetcher
        self.media_type = media_type
        self.wrapper_element = cssselect2.ElementWrapper.from_html_root(
            result, content_language=None)
        self.etree_element = self.wrapper_element.etree_element

    def _ua_stylesheets(self):
        return [HTML5_UA_STYLESHEET]

    def _ua_counter_style(self):
        return [HTML5_UA_COUNTER_STYLE.copy()]

    def _ph_stylesheets(self):
        return [HTML5_PH_STYLESHEET]

    def _get_metadata(self):
        return get_html_metadata(self.wrapper_element, self.base_url)

    def render(self, stylesheets=None, enable_hinting=False,
               presentational_hints=False, optimize_images=False,
               font_config=None, counter_style=None, image_cache=None):
        """Lay out and paginate the document, but do not (yet) export it
        to PDF or PNG.

        This returns a :class:`~document.Document` object which provides
        access to individual pages and various meta-data.
        See :meth:`write_pdf` to get a PDF directly.

        .. versionadded:: 0.15

        :type stylesheets: list
        :param stylesheets:
            An optional list of user stylesheets. List elements are
            :class:`CSS` objects, filenames, URLs, or file
            objects. (See :ref:`stylesheet-origins`.)
        :type enable_hinting: bool
        :param enable_hinting:
            Whether text, borders and background should be *hinted* to fall
            at device pixel boundaries. Should be enabled for pixel-based
            output (like PNG) but not for vector-based output (like PDF).
        :type presentational_hints: bool
        :param presentational_hints: Whether HTML presentational hints are
            followed.
        :type optimize_images: bool
        :param optimize_images: Try to optimize the size of embedded images.
        :type font_config: :class:`~fonts.FontConfiguration`
        :param font_config: A font configuration handling ``@font-face`` rules.
        :type counter_style: :class:`~css.counters.CounterStyle`
        :param counter_style: A dictionary storing ``@counter-style`` rules.
        :type image_cache: dict
        :param image_cache: A dictionary used to cache images.
        :returns: A :class:`~document.Document` object.

        """
        return Document._render(
            self, stylesheets, enable_hinting, presentational_hints,
            optimize_images, font_config, counter_style, image_cache)

    def write_pdf(self, target=None, stylesheets=None, zoom=1,
                  attachments=None, presentational_hints=False,
                  optimize_images=False, font_config=None, counter_style=None,
                  image_cache=None):
        """Render the document to a PDF file.

        This is a shortcut for calling :meth:`render`, then
        :meth:`Document.write_pdf() <document.Document.write_pdf>`.

        :type target: str, pathlib.Path or file object
        :param target:
            A filename where the PDF file is generated, a file object, or
            :obj:`None`.
        :type stylesheets: list
        :param stylesheets:
            An optional list of user stylesheets. The list's elements
            are :class:`CSS` objects, filenames, URLs, or file-like
            objects. (See :ref:`stylesheet-origins`.)
        :type zoom: float
        :param zoom:
            The zoom factor in PDF units per CSS units.  **Warning**:
            All CSS units are affected, including physical units like
            ``cm`` and named sizes like ``A4``.  For values other than
            1, the physical CSS units will thus be "wrong".
        :type attachments: list
        :param attachments: A list of additional file attachments for the
            generated PDF document or :obj:`None`. The list's elements are
            :class:`Attachment` objects, filenames, URLs or file-like objects.
        :type presentational_hints: bool
        :param presentational_hints: Whether HTML presentational hints are
            followed.
        :type optimize_images: bool
        :param optimize_images: Try to optimize the size of embedded images.
        :type font_config: :class:`~fonts.FontConfiguration`
        :param font_config: A font configuration handling ``@font-face`` rules.
        :type counter_style: :class:`~css.counters.CounterStyle`
        :param counter_style: A dictionary storing ``@counter-style`` rules.
        :type image_cache: dict
        :param image_cache: A dictionary used to cache images.
        :returns:
            The PDF as :obj:`bytes` if ``target`` is not provided or
            :obj:`None`, otherwise :obj:`None` (the PDF is written to
            ``target``).

        """
        return (
            self.render(
                stylesheets, enable_hinting=False,
                presentational_hints=presentational_hints,
                optimize_images=optimize_images, font_config=font_config,
                counter_style=counter_style, image_cache=image_cache)
            .write_pdf(target, zoom, attachments))

    def write_image_surface(self, stylesheets=None, resolution=96,
                            presentational_hints=False, optimize_images=False,
                            font_config=None, counter_style=None,
                            image_cache=None):
        """Render pages vertically on a cairo image surface.

        .. versionadded:: 0.17

        There is no decoration around pages other than those specified in CSS
        with ``@page`` rules. The final image is as wide as the widest page.
        Each page is below the previous one, centered horizontally.

        This is a shortcut for calling :meth:`render`, then
        :meth:`Document.write_image_surface()
        <document.Document.write_image_surface>`.

        :type stylesheets: list
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
        :type optimize_images: bool
        :param optimize_images: Try to optimize the size of embedded images.
        :type font_config: :class:`~fonts.FontConfiguration`
        :param font_config: A font configuration handling ``@font-face`` rules.
        :type counter_style: :class:`~css.counters.CounterStyle`
        :param counter_style: A dictionary storing ``@counter-style`` rules.
        :type image_cache: dict
        :param image_cache: A dictionary used to cache images.
        :returns: A cairo :class:`ImageSurface <cairocffi.ImageSurface>`.

        """
        surface, _width, _height = (
            self.render(
                stylesheets, enable_hinting=True,
                presentational_hints=presentational_hints,
                font_config=font_config, optimize_images=optimize_images,
                image_cache=image_cache)
            .write_image_surface(resolution))
        return surface

    def write_png(self, target=None, stylesheets=None, resolution=96,
                  presentational_hints=False, optimize_images=False,
                  font_config=None, counter_style=None, image_cache=None):
        """Paint the pages vertically to a single PNG image.

        There is no decoration around pages other than those specified in CSS
        with ``@page`` rules. The final image is as wide as the widest page.
        Each page is below the previous one, centered horizontally.

        This is a shortcut for calling :meth:`render`, then
        :meth:`Document.write_png() <document.Document.write_png>`.

        :type target: str, pathlib.Path or file object
        :param target:
            A filename where the PNG file is generated, a file object, or
            :obj:`None`.
        :type stylesheets: list
        :param stylesheets:
            An optional list of user stylesheets. The list's elements
            are :class:`CSS` objects, filenames, URLs, or file-like
            objects. (See :ref:`stylesheet-origins`.)
        :type resolution: float
        :param resolution:
            The output resolution in PNG pixels per CSS inch. At 96 dpi
            (the default), PNG pixels match the CSS ``px`` unit.
        :type presentational_hints: bool
        :param presentational_hints: Whether HTML presentational hints are
            followed.
        :type optimize_images: bool
        :param optimize_images: Try to optimize the size of embedded images.
        :type font_config: :class:`~fonts.FontConfiguration`
        :param font_config: A font configuration handling ``@font-face`` rules.
        :type counter_style: :class:`~css.counters.CounterStyle`
        :param counter_style: A dictionary storing ``@counter-style`` rules.
        :type image_cache: dict
        :param image_cache: A dictionary used to cache images.
        :returns:
            The image as :obj:`bytes` if ``target`` is not provided or
            :obj:`None`, otherwise :obj:`None` (the image is written to
            ``target``.)

        """
        png_bytes, _width, _height = (
            self.render(
                stylesheets, enable_hinting=True,
                presentational_hints=presentational_hints,
                optimize_images=optimize_images, font_config=font_config,
                counter_style=counter_style, image_cache=image_cache)
            .write_png(target, resolution))
        return png_bytes


class CSS:
    """Represents a CSS stylesheet parsed by tinycss2.

    An instance is created in the same way as :class:`HTML`, with the same
    arguments.

    An additional argument called ``font_config`` must be provided to handle
    ``@font-config`` rules. The same ``fonts.FontConfiguration`` object must be
    used for different ``CSS`` objects applied to the same document.

    ``CSS`` objects have no public attributes or methods. They are only meant
    to be used in the :meth:`~HTML.write_pdf`, :meth:`~HTML.write_png` and
    :meth:`~HTML.render` methods of :class:`HTML` objects.

    """
    def __init__(self, guess=None, filename=None, url=None, file_obj=None,
                 string=None, encoding=None, base_url=None,
                 url_fetcher=default_url_fetcher, _check_mime_type=False,
                 media_type='print', font_config=None, counter_style=None,
                 matcher=None, page_rules=None):
        PROGRESS_LOGGER.info(
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
        self.fonts = []
        preprocess_stylesheet(
            media_type, base_url, stylesheet, url_fetcher, self.matcher,
            self.page_rules, self.fonts, font_config, counter_style)


class Attachment:
    """Represents a file attachment for a PDF document.

    .. versionadded:: 0.22

    An instance is created in the same way as :class:`HTML`, except that the
    HTML specific arguments (``encoding`` and ``media_type``) are not
    supported. An optional description can be provided with the ``description``
    argument.

    :param description: A description of the attachment to be included in the
        PDF document. May be :obj:`None`.

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
    else:
        assert string is not None
        yield 'string', string, base_url, None

# Work around circular imports.
from .css import preprocess_stylesheet  # noqa isort:skip
from .html import (  # noqa isort:skip
    HTML5_UA_COUNTER_STYLE, HTML5_UA_STYLESHEET, HTML5_PH_STYLESHEET,
    find_base_url, get_html_metadata)
from .document import Document, Page  # noqa isort:skip
