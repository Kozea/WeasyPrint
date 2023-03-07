"""The Awesome Document Factory.

The public API is what is accessible from this "root" packages without
importing sub-modules.

"""

import contextlib
from pathlib import Path
from urllib.parse import urljoin

import cssselect2
import html5lib
import tinycss2

VERSION = __version__ = '58.1'

__all__ = [
    'HTML', 'CSS', 'Attachment', 'Document', 'Page', 'default_url_fetcher',
    'VERSION', '__version__']


# Import after setting the version, as the version is used in other modules
from .urls import (  # noqa isort:skip
    fetch, default_url_fetcher, path2url, ensure_url, url_is_absolute)
from .logger import LOGGER, PROGRESS_LOGGER  # noqa isort:skip
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
    """HTML document parsed by html5lib.

    You can just create an instance with a positional argument:
    ``doc = HTML(something)``
    The class will try to guess if the input is a filename, an absolute URL,
    or a :term:`file object`.

    Alternatively, use **one** named argument so that no guessing is involved:

    :type filename: str or pathlib.Path
    :param filename: A filename, relative to the current directory, or
        absolute.
    :param str url: An absolute, fully qualified URL.
    :type file_obj: :term:`file object`
    :param file_obj: Any object with a ``read`` method.
    :param str string: A string of HTML source.

    Specifying multiple inputs is an error:
    ``HTML(filename="foo.html", url="localhost://bar.html")``
    will raise a :obj:`TypeError`.

    You can also pass optional named arguments:

    :param str encoding: Force the source character encoding.
    :param str base_url: The base used to resolve relative URLs
        (e.g. in ``<img src="../foo.png">``). If not provided, try to use
        the input filename, URL, or ``name`` attribute of :term:`file objects
        <file object>`.
    :type url_fetcher: :term:`function`
    :param url_fetcher: A function or other callable
        with the same signature as :func:`default_url_fetcher` called to
        fetch external resources such as stylesheets and images.
        (See :ref:`URL Fetchers`.)
    :param str media_type: The media type to use for ``@media``.
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

    def render(self, stylesheets=None, presentational_hints=False,
               optimize_size=('fonts',), font_config=None, counter_style=None,
               image_cache=None, forms=False):
        """Lay out and paginate the document, but do not (yet) export it.

        This returns a :class:`document.Document` object which provides
        access to individual pages and various meta-data.
        See :meth:`write_pdf` to get a PDF directly.

        :param list stylesheets:
            An optional list of user stylesheets. List elements are
            :class:`CSS` objects, filenames, URLs, or file
            objects. (See :ref:`Stylesheet Origins`.)
        :param bool presentational_hints:
            Whether HTML presentational hints are followed.
        :param tuple optimize_size:
            Optimize size of generated PDF. Can contain "images" and "fonts".
        :type font_config: :class:`text.fonts.FontConfiguration`
        :param font_config: A font configuration handling ``@font-face`` rules.
        :type counter_style: :class:`css.counters.CounterStyle`
        :param counter_style: A dictionary storing ``@counter-style`` rules.
        :param dict image_cache: A dictionary used to cache images.
        :param bool forms: Whether PDF forms have to be included.
        :returns: A :class:`document.Document` object.

        """
        return Document._render(
            self, stylesheets, presentational_hints, optimize_size,
            font_config, counter_style, image_cache, forms)

    def write_pdf(self, target=None, stylesheets=None, zoom=1,
                  attachments=None, finisher=None, presentational_hints=False,
                  optimize_size=('fonts',), font_config=None,
                  counter_style=None, image_cache=None, identifier=None,
                  variant=None, version=None, forms=False,
                  custom_metadata=False):
        """Render the document to a PDF file.

        This is a shortcut for calling :meth:`render`, then
        :meth:`Document.write_pdf() <document.Document.write_pdf>`.

        :type target:
            :class:`str`, :class:`pathlib.Path` or :term:`file object`
        :param target:
            A filename where the PDF file is generated, a file object, or
            :obj:`None`.
        :param list stylesheets:
            An optional list of user stylesheets. The list's elements
            are :class:`CSS` objects, filenames, URLs, or file-like
            objects. (See :ref:`Stylesheet Origins`.)
        :param float zoom:
            The zoom factor in PDF units per CSS units.  **Warning**:
            All CSS units are affected, including physical units like
            ``cm`` and named sizes like ``A4``.  For values other than
            1, the physical CSS units will thus be "wrong".
        :param list attachments: A list of additional file attachments for the
            generated PDF document or :obj:`None`. The list's elements are
            :class:`Attachment` objects, filenames, URLs or file-like objects.
        :param finisher: A finisher function, that accepts the document and a
            :class:`pydyf.PDF` object as parameters, can be passed to perform
            post-processing on the PDF right before the trailer is written.
        :param bool presentational_hints: Whether HTML presentational hints are
            followed.
        :param tuple optimize_size:
            Optimize size of generated PDF. Can contain "images" and "fonts".
        :type font_config: :class:`text.fonts.FontConfiguration`
        :param font_config: A font configuration handling ``@font-face`` rules.
        :type counter_style: :class:`css.counters.CounterStyle`
        :param counter_style: A dictionary storing ``@counter-style`` rules.
        :param dict image_cache: A dictionary used to cache images.
        :param bytes identifier: A bytestring used as PDF file identifier.
        :param str variant: A PDF variant name.
        :param str version: A PDF version number.
        :param bool forms: Whether PDF forms have to be included.
        :param bool custom_metadata: Whether custom HTML metadata should be
            stored in the generated PDF.
        :returns:
            The PDF as :obj:`bytes` if ``target`` is not provided or
            :obj:`None`, otherwise :obj:`None` (the PDF is written to
            ``target``).

        """
        return (
            self.render(
                stylesheets, presentational_hints, optimize_size, font_config,
                counter_style, image_cache, forms)
            .write_pdf(
                target, zoom, attachments, finisher, identifier, variant,
                version, custom_metadata))


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
        preprocess_stylesheet(
            media_type, base_url, stylesheet, url_fetcher, self.matcher,
            self.page_rules, font_config, counter_style)


class Attachment:
    """File attachment for a PDF document.

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
            guess, filename, url, file_obj, string, base_url=base_url,
            url_fetcher=url_fetcher)
        self.description = description


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
from .css import preprocess_stylesheet  # noqa isort:skip
from .html import (  # noqa isort:skip
    HTML5_UA_COUNTER_STYLE, HTML5_UA_STYLESHEET, HTML5_UA_FORM_STYLESHEET,
    HTML5_PH_STYLESHEET)
from .document import Document, Page  # noqa isort:skip
