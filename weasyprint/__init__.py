"""The Awesome Document Factory.

The public API is what is accessible from this "root" packages without
importing sub-modules.

"""

import contextlib
from datetime import datetime
from os.path import getctime, getmtime
from pathlib import Path
from urllib.parse import urljoin

import cssselect2
import tinycss2
import tinyhtml5

VERSION = __version__ = '67.0'

#: Default values for command-line and Python API options. See
#: :func:`__main__.main` to learn more about specific options for
#: command-line.
#:
#: :param list stylesheets:
#:     An optional list of user stylesheets. The list can include
#:     are :class:`CSS` objects, filenames, URLs, or file-like
#:     objects. (See :ref:`Stylesheet Origins`.)
#: :param str media_type:
#:     Media type to use for @media.
#: :param list attachments:
#:     A list of additional file attachments for the generated PDF
#:     document or :obj:`None`. The list's elements are
#:     :class:`Attachment` objects, filenames, URLs or file-like objects.
#: :param bytes pdf_identifier:
#:     A bytestring used as PDF file identifier.
#: :param str pdf_variant:
#:     A PDF variant name.
#: :param str pdf_version:
#:     A PDF version number.
#: :param bool pdf_forms:
#:     Whether PDF forms have to be included.
#: :param bool pdf_tags:
#:     Whether PDF should be tagged for accessibility.
#: :param bool uncompressed_pdf:
#:     Whether PDF content should be compressed.
#: :param bool custom_metadata:
#:     Whether custom HTML metadata should be stored in the generated PDF.
#: :param bool presentational_hints:
#:     Whether HTML presentational hints are followed.
#: :param bool srgb:
#:     Whether sRGB color profile should be included and set as default for
#:     device-dependant RGB colors.
#: :param bool optimize_images:
#:     Whether size of embedded images should be optimized, with no quality
#:     loss.
#: :param int jpeg_quality:
#:     JPEG quality between 0 (worst) to 95 (best).
#: :param int dpi:
#:     Maximum resolution of images embedded in the PDF.
#: :param bool full_fonts:
#:     Whether unmodified font files should be embedded when possible.
#: :param bool hinting:
#:     Whether hinting information should be kept in embedded fonts.
#: :type cache: :obj:`dict`, :class:`pathlib.Path` or :obj:`str`
#: :param cache:
#:     A dictionary used to cache images in memory, or a folder path where
#:     images are temporarily stored.
DEFAULT_OPTIONS = {
    'stylesheets': None,
    'media_type': 'print',
    'attachments': None,
    'pdf_identifier': None,
    'pdf_variant': None,
    'pdf_version': None,
    'pdf_forms': None,
    'pdf_tags': False,
    'uncompressed_pdf': False,
    'custom_metadata': False,
    'presentational_hints': False,
    'srgb': False,
    'optimize_images': False,
    'jpeg_quality': None,
    'dpi': None,
    'full_fonts': False,
    'hinting': False,
    'cache': None,
}

__all__ = [
    'CSS', 'DEFAULT_OPTIONS', 'HTML', 'VERSION', 'Attachment', 'Document', 'Page',
    '__version__', 'default_url_fetcher']


# Import after setting the version, as the version is used in other modules
from .urls import (  # noqa: I001, E402
    fetch, default_url_fetcher, path2url, ensure_url, url_is_absolute)
from .logger import LOGGER, PROGRESS_LOGGER  # noqa: E402
# Some imports are at the end of the file (after the CSS class)
# to work around circular imports.


def _find_base_url(html_document, fallback_base_url):
    """Return the base URL for the document.

    See https://www.w3.org/TR/html5/urls.html#document-base-url

    """
    first_base_element = next(iter(html_document.iter('base')), None)
    if first_base_element is not None:
        href = first_base_element.get('href', '').strip()
        if href:
            return urljoin(fallback_base_url, href)
    return fallback_base_url


class HTML:
    """HTML document parsed by tinyhtml5.

    You can just create an instance with a positional argument:
    ``doc = HTML(something)``
    The class will try to guess if the input is a filename, an absolute URL,
    or a :term:`file object`.

    Alternatively, use **one** named argument so that no guessing is involved:

    :type filename: str or pathlib.Path
    :param filename:
        A filename, relative to the current directory, or absolute.
    :param str url:
        An absolute, fully qualified URL.
    :type file_obj: :term:`file object`
    :param file_obj:
        Any object with a ``read`` method.
    :param str string:
        A string of HTML source.

    Specifying multiple inputs is an error:
    ``HTML(filename="foo.html", url="localhost://bar.html")``
    will raise a :obj:`TypeError`.

    You can also pass optional named arguments:

    :param str encoding:
        Force the source character encoding.
    :type base_url: str or pathlib.Path
    :param base_url:
        The base used to resolve relative URLs (e.g. in
        ``<img src="../foo.png">``). If not provided, try to use the input
        filename, URL, or ``name`` attribute of
        :term:`file objects <file object>`.
    :type url_fetcher: :term:`callable`
    :param url_fetcher:
        A function or other callable with the same signature as
        :func:`default_url_fetcher` called to fetch external resources such as
        stylesheets and images. (See :ref:`URL Fetchers`.)
    :param str media_type:
        The media type to use for ``@media``. Defaults to ``'print'``.
        **Note:** In some cases like ``HTML(string=foo)`` relative URLs will be
        invalid if ``base_url`` is not provided.

    """
    def __init__(self, guess=None, filename=None, url=None, file_obj=None,
                 string=None, encoding=None, base_url=None,
                 url_fetcher=default_url_fetcher, media_type='print'):
        PROGRESS_LOGGER.info(
            'Step 1 - Fetching and parsing HTML - %s',
            guess or filename or url or
            getattr(file_obj, 'name', 'HTML string'))
        if isinstance(base_url, Path):
            base_url = str(base_url)
        result = _select_source(
            guess, filename, url, file_obj, string, base_url, url_fetcher)
        with result as (source_type, source, base_url, protocol_encoding):
            if isinstance(source, str):
                result = tinyhtml5.parse(source, namespace_html_elements=False)
            else:
                kwargs = {'namespace_html_elements': False}
                if protocol_encoding is not None:
                    kwargs['transport_encoding'] = protocol_encoding
                if encoding is not None:
                    kwargs['override_encoding'] = encoding
                result = tinyhtml5.parse(source, **kwargs)
        self.base_url = _find_base_url(result, base_url)
        self.url_fetcher = url_fetcher
        self.media_type = media_type
        self.wrapper_element = cssselect2.ElementWrapper.from_html_root(
            result, content_language=None)
        self.etree_element = self.wrapper_element.etree_element

    def _ua_stylesheets(self, forms=False):
        if forms:
            return [HTML5_UA_STYLESHEET, HTML5_UA_FORM_STYLESHEET]
        return [HTML5_UA_STYLESHEET]

    def _ua_counter_style(self):
        return [HTML5_UA_COUNTER_STYLE.copy()]

    def _ph_stylesheets(self):
        return [HTML5_PH_STYLESHEET]

    def render(self, font_config=None, counter_style=None, color_profiles=None,
               **options):
        """Lay out and paginate the document, but do not (yet) export it.

        This returns a :class:`document.Document` object which provides
        access to individual pages and various meta-data.
        See :meth:`write_pdf` to get a PDF directly.

        :type font_config: :class:`text.fonts.FontConfiguration`
        :param font_config:
            A font configuration handling ``@font-face`` rules.
        :type counter_style: :class:`css.counters.CounterStyle`
        :param counter_style:
            A dictionary storing ``@counter-style`` rules.
        :param options:
            The ``options`` parameter includes by default the
            :data:`DEFAULT_OPTIONS` values.
        :returns: A :class:`document.Document` object.

        """
        for unknown in set(options) - set(DEFAULT_OPTIONS):
            LOGGER.warning('Unknown rendering option: %s.', unknown)
        new_options = DEFAULT_OPTIONS.copy()
        new_options.update(options)
        options = new_options
        return Document._render(
            self, font_config, counter_style, color_profiles, options)

    def write_pdf(self, target=None, zoom=1, finisher=None,
                  font_config=None, counter_style=None, color_profiles=None, **options):
        """Render the document to a PDF file.

        This is a shortcut for calling :meth:`render`, then
        :meth:`Document.write_pdf() <document.Document.write_pdf>`.

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
        :type finisher: :term:`callable`
        :param finisher:
            A finisher function or callable that accepts the document and a
            :class:`pydyf.PDF` object as parameters. Can be passed to perform
            post-processing on the PDF right before the trailer is written.
        :type font_config: :class:`text.fonts.FontConfiguration`
        :param font_config:
            A font configuration handling ``@font-face`` rules.
        :type counter_style: :class:`css.counters.CounterStyle`
        :param counter_style:
            A dictionary storing ``@counter-style`` rules.
        :param options:
            The ``options`` parameter includes by default the
            :data:`DEFAULT_OPTIONS` values.
        :returns:
            The PDF as :obj:`bytes` if ``target`` is not provided or
            :obj:`None`, otherwise :obj:`None` (the PDF is written to
            ``target``).

        """
        new_options = DEFAULT_OPTIONS.copy()
        new_options.update(options)
        options = new_options
        return (
            self.render(font_config, counter_style, color_profiles, **options)
            .write_pdf(target, zoom, finisher, **options))


class CSS:
    """CSS stylesheet parsed by tinycss2.

    An instance is created in the same way as :class:`HTML`, with the same
    arguments.

    An additional argument called ``font_config`` must be provided to handle
    ``@font-face`` rules. The same ``text.fonts.FontConfiguration`` object
    must be used for different ``CSS`` objects applied to the same document.

    ``CSS`` objects have no public attributes or methods. They are only meant
    to be used in the :meth:`HTML.write_pdf` and :meth:`HTML.render` methods
    of :class:`HTML` objects.

    """
    def __init__(self, guess=None, filename=None, url=None, file_obj=None,
                 string=None, encoding=None, base_url=None,
                 url_fetcher=default_url_fetcher, _check_mime_type=False,
                 media_type='print', font_config=None, counter_style=None,
                 color_profiles=None, matcher=None, page_rules=None, layers=None,
                 layer=None):
        PROGRESS_LOGGER.info(
            'Step 2 - Fetching and parsing CSS - %s',
            filename or url or getattr(file_obj, 'name', 'CSS string'))
        result = _select_source(
            guess, filename, url, file_obj, string,
            base_url=base_url, url_fetcher=url_fetcher,
            check_css_mime_type=_check_mime_type)
        with result as (source_type, source, base_url, protocol_encoding):
            if source_type == 'file_obj':
                source = source.read()
            if isinstance(source, str):
                # unicode, no encoding
                stylesheet = tinycss2.parse_stylesheet(source)
            else:
                stylesheet, encoding = tinycss2.parse_stylesheet_bytes(
                    source, environment_encoding=encoding,
                    protocol_encoding=protocol_encoding)
        self.base_url = base_url
        self.matcher = matcher or cssselect2.Matcher()
        self.page_rules = [] if page_rules is None else page_rules
        self.layers = [] if layers is None else layers
        counter_style = {} if counter_style is None else counter_style
        color_profiles = {} if color_profiles is None else color_profiles
        preprocess_stylesheet(
            media_type, base_url, stylesheet, url_fetcher, self.matcher,
            self.page_rules, self.layers, font_config, counter_style, color_profiles,
            layer=layer)


class Attachment:
    """File attachment for a PDF document.

    An instance is created in the same way as :class:`HTML`, except that the
    HTML specific arguments (``encoding`` and ``media_type``) are not
    supported.

    :param str name:
        The name of the attachment to be included in the PDF document.
        May be :obj:`None`.
    :param str description:
        A description of the attachment to be included in the PDF document.
        May be :obj:`None`.
    :type created: :obj:`datetime.datetime`
    :param created:
        Creation date and time. Default is current date and time.
    :type modified: :obj:`datetime.datetime`
    :param modified:
        Modification date and time. Default is current date and time.
    :param str relationship:
        A string that represents the relationship between the attachment and
        the PDF it is embedded in. Default is 'Unspecified', other common
        values are defined in ISO-32000-2:2020, 7.11.3.

    """
    def __init__(self, guess=None, filename=None, url=None, file_obj=None,
                 string=None, base_url=None, url_fetcher=default_url_fetcher,
                 name=None, description=None, created=None, modified=None,
                 relationship='Unspecified'):
        self.source = _select_source(
            guess, filename, url, file_obj, string, base_url=base_url,
            url_fetcher=url_fetcher)
        self.name = name
        self.description = description
        self.relationship = relationship
        self.md5 = None

        if created is None:
            if filename:
                created = datetime.fromtimestamp(getctime(filename))
            else:
                created = datetime.now()
        if modified is None:
            if filename:
                modified = datetime.fromtimestamp(getmtime(filename))
            else:
                modified = datetime.now()
        self.created = created
        self.modified = modified


@contextlib.contextmanager
def _select_source(guess=None, filename=None, url=None, file_obj=None,
                   string=None, base_url=None, url_fetcher=default_url_fetcher,
                   check_css_mime_type=False):
    """If only one input is given, return it with normalized ``base_url``."""
    if base_url is not None:
        base_url = ensure_url(base_url)

    selected_params = [
        param for param in (guess, filename, url, file_obj, string) if
        param is not None]
    if len(selected_params) != 1:
        source = ', '.join(selected_params) or 'nothing'
        raise TypeError(f'Expected exactly one source, got {source}')
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
from .css import preprocess_stylesheet  # noqa: I001, E402
from .html import (  # noqa: E402
    HTML5_UA_COUNTER_STYLE, HTML5_UA_STYLESHEET, HTML5_UA_FORM_STYLESHEET,
    HTML5_PH_STYLESHEET)
from .document import Document, Page  # noqa: E402
