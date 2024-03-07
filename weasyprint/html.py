"""Specific handling for some HTML elements, especially replaced elements.

Replaced elements (eg. <img> elements) are rendered externally and behave as an
atomic opaque box in CSS. In general, they may or may not have intrinsic
dimensions. But the only replaced elements currently supported in WeasyPrint
are images with intrinsic dimensions.

"""

try:
    # Available in Python 3.9+
    from importlib.resources import files
except ImportError:  # pragma: no cover
    # Deprecated in Python 3.11+
    from importlib.resources import read_text
else:
    def read_text(package, resource):
        return (files(package) / resource).read_text('utf-8')

import re

from . import CSS, Attachment, css
from .css import get_child_text
from .css.counters import CounterStyle
from .formatting_structure import boxes
from .images import SVGImage
from .logger import LOGGER
from .urls import get_url_attribute

HTML5_UA_COUNTER_STYLE = CounterStyle()
HTML5_UA = read_text(css, 'html5_ua.css')
HTML5_UA_FORM = read_text(css, 'html5_ua_form.css')
HTML5_PH = read_text(css, 'html5_ph.css')
HTML5_UA_STYLESHEET = CSS(
    string=HTML5_UA, counter_style=HTML5_UA_COUNTER_STYLE)
HTML5_UA_FORM_STYLESHEET = CSS(
    string=HTML5_UA_FORM, counter_style=HTML5_UA_COUNTER_STYLE)
HTML5_PH_STYLESHEET = CSS(string=HTML5_PH)

# https://html.spec.whatwg.org/multipage/#space-character
HTML_WHITESPACE = ' \t\n\f\r'
HTML_SPACE_SEPARATED_TOKENS_RE = re.compile(f'[^{HTML_WHITESPACE}]+')


def ascii_lower(string):
    r"""Transform (only) ASCII letters to lower case: A-Z is mapped to a-z.

    This is used for `ASCII case-insensitive
    <https://whatwg.org/C#ascii-case-insensitive>`_ matching.

    This is different from the :meth:`str.lower` method of Unicode strings
    which also affect non-ASCII characters,
    sometimes mapping them into the ASCII range:

    >>> keyword = 'Bac\N{KELVIN SIGN}ground'
    >>> assert keyword.lower() == 'background'
    >>> assert ascii_lower(keyword) != keyword.lower()
    >>> assert ascii_lower(keyword) == 'bac\N{KELVIN SIGN}ground'

    """
    # This turns out to be faster than unicode.translate()
    return string.encode().lower().decode()


def element_has_link_type(element, link_type):
    """Return whether element has a ``rel`` attribute with given link type."""
    tokens = HTML_SPACE_SEPARATED_TOKENS_RE.findall(element.get('rel', ''))
    return any(ascii_lower(token) == link_type for token in tokens)


# Maps HTML tag names to function taking an HTML element and returning a Box.
HTML_HANDLERS = {}


def handle_element(element, box, get_image_from_uri, base_url):
    """Handle HTML elements that need special care.

    :returns: a (possibly empty) list of boxes.
    """
    if box.element_tag in HTML_HANDLERS:
        return HTML_HANDLERS[element.tag](
            element, box, get_image_from_uri, base_url)
    else:
        return [box]


def handler(tag):
    """Return a decorator registering a function handling ``tag`` elements."""
    def decorator(function):
        """Decorator registering a function handling ``tag`` elements."""
        HTML_HANDLERS[tag] = function
        return function
    return decorator


def make_replaced_box(element, box, image):
    """Wrap an image in a replaced box.

    That box is either block-level or inline-level, depending on what the
    element should be.

    """
    type_ = (
        boxes.BlockReplacedBox if 'block' in box.style['display']
        else boxes.InlineReplacedBox)
    new_box = type_(element.tag, box.style, element, image)
    # TODO: check other attributes that need to be copied
    # TODO: find another solution
    new_box.string_set = box.string_set
    new_box.bookmark_label = box.bookmark_label
    return new_box


@handler('img')
def handle_img(element, box, get_image_from_uri, base_url):
    """Handle ``<img>`` elements.

    Return either an image or the alt-text.

    See: https://www.w3.org/TR/html5/embedded-content-1.html#the-img-element

    """
    src = get_url_attribute(element, 'src', base_url)
    alt = element.get('alt')
    if src:
        image = get_image_from_uri(
            url=src, orientation=box.style['image_orientation'])
        if image is not None:
            return [make_replaced_box(element, box, image)]
        else:
            # Invalid image, use the alt-text.
            if alt:
                box.children = [boxes.TextBox.anonymous_from(box, alt)]
                return [box]
            elif alt == '':
                # The element represents nothing
                return []
            else:
                assert alt is None
                # TODO: find some indicator that an image is missing.
                # For now, just remove the image.
                return []
    else:
        if alt:
            box.children = [boxes.TextBox.anonymous_from(box, alt)]
            return [box]
        else:
            return []


@handler('embed')
def handle_embed(element, box, get_image_from_uri, base_url):
    """Handle ``<embed>`` elements, return either an image or nothing.

    See: https://www.w3.org/TR/html5/embedded-content-0.html#the-embed-element

    """
    src = get_url_attribute(element, 'src', base_url)
    type_ = element.get('type', '').strip()
    if src:
        image = get_image_from_uri(
            url=src, forced_mime_type=type_,
            orientation=box.style['image_orientation'])
        if image is not None:
            return [make_replaced_box(element, box, image)]
    # No fallback.
    return []


@handler('object')
def handle_object(element, box, get_image_from_uri, base_url):
    """Handle ``<object>`` elements, return either an image or the fallback.

    See: https://www.w3.org/TR/html5/embedded-content-0.html#the-object-element

    """
    data = get_url_attribute(element, 'data', base_url)
    type_ = element.get('type', '').strip()
    if data:
        image = get_image_from_uri(
            url=data, forced_mime_type=type_,
            orientation=box.style['image_orientation'])
        if image is not None:
            return [make_replaced_box(element, box, image)]
    # The element’s children are the fallback.
    return [box]


@handler('colgroup')
def handle_colgroup(element, box, _get_image_from_uri, _base_url):
    """Handle the ``span`` attribute."""
    if isinstance(box, boxes.TableColumnGroupBox):
        if not any(child.tag == 'col' for child in element):
            box.children = [
                boxes.TableColumnBox.anonymous_from(box, [])
                for _ in range(box.span)]
    return [box]


@handler('col')
def handle_col(element, box, _get_image_from_uri, _base_url):
    """Handle the ``span`` attribute."""
    if isinstance(box, boxes.TableColumnBox) and box.span > 1:
        # Generate multiple boxes
        # https://lists.w3.org/Archives/Public/www-style/2011Nov/0293.html
        return [box.copy() for _i in range(box.span)]
    return [box]


@handler('{http://www.w3.org/2000/svg}svg')
def handle_svg(element, box, get_image_from_uri, base_url):
    """Handle ``<svg>`` elements.

    Return either an image or the fallback content.

    """
    # TODO: handle href base for inline svg tags
    url_fetcher = get_image_from_uri.keywords['url_fetcher']
    context = get_image_from_uri.keywords['context']
    try:
        image = SVGImage(element, base_url, url_fetcher, context)
    except Exception as exception:  # pragma: no cover
        LOGGER.error('Failed to load inline SVG: %s', exception)
        return []
    else:
        return [make_replaced_box(element, box, image)]


def get_html_metadata(html):
    """Get metadata dictionary out of HTML object.

    Relevant specs:

    https://www.whatwg.org/html#the-title-element
    https://www.whatwg.org/html#standard-metadata-names
    https://wiki.whatwg.org/wiki/MetaExtensions
    https://microformats.org/wiki/existing-rel-values#HTML5_link_type_extensions

    """
    title = None
    description = None
    generator = None
    keywords = []
    authors = []
    created = None
    modified = None
    attachments = []
    custom = {}
    lang = html.etree_element.attrib.get('lang', None)
    for element in html.wrapper_element.query_all('title', 'meta', 'link'):
        element = element.etree_element
        if element.tag == 'title' and title is None:
            title = get_child_text(element)
        elif element.tag == 'meta':
            name = ascii_lower(element.get('name', ''))
            content = element.get('content', '')
            if name == 'keywords':
                for keyword in map(strip_whitespace, content.split(',')):
                    if keyword not in keywords:
                        keywords.append(keyword)
            elif name == 'author':
                authors.append(content)
            elif name == 'description':
                if description is None:
                    description = content
            elif name == 'generator':
                if generator is None:
                    generator = content
            elif name == 'dcterms.created':
                if created is None:
                    created = parse_w3c_date(name, content)
            elif name == 'dcterms.modified':
                if modified is None:
                    modified = parse_w3c_date(name, content)
            elif name and name not in custom:
                custom[name] = content
        elif element.tag == 'link' and element_has_link_type(
                element, 'attachment'):
            url = get_url_attribute(element, 'href', html.base_url)
            attachment_title = element.get('title', None)
            if url is None:
                LOGGER.error('Missing href in <link rel="attachment">')
            else:
                attachment = Attachment(
                    url=url, description=attachment_title,
                    url_fetcher=html.url_fetcher)
                attachments.append(attachment)
    return {
        'title': title,
        'description': description,
        'generator': generator,
        'keywords': keywords,
        'authors': authors,
        'created': created,
        'modified': modified,
        'attachments': attachments,
        'lang': lang,
        'custom': custom,
    }


def strip_whitespace(string):
    """Use the HTML definition of "space character",
    not all Unicode Whitespace.

    https://www.whatwg.org/html#strip-leading-and-trailing-whitespace
    https://www.whatwg.org/html#space-character

    """
    return string.strip(HTML_WHITESPACE)


# YYYY (eg 1997)
# YYYY-MM (eg 1997-07)
# YYYY-MM-DD (eg 1997-07-16)
# YYYY-MM-DDThh:mmTZD (eg 1997-07-16T19:20+01:00)
# YYYY-MM-DDThh:mm:ssTZD (eg 1997-07-16T19:20:30+01:00)
# YYYY-MM-DDThh:mm:ss.sTZD (eg 1997-07-16T19:20:30.45+01:00)

W3C_DATE_RE = re.compile('''
    ^
    [ \t\n\f\r]*
    (?P<year>\\d\\d\\d\\d)
    (?:
        -(?P<month>0\\d|1[012])
        (?:
            -(?P<day>[012]\\d|3[01])
            (?:
                T(?P<hour>[01]\\d|2[0-3])
                :(?P<minute>[0-5]\\d)
                (?:
                    :(?P<second>[0-5]\\d)
                    (?:\\.\\d+)?  # Second fraction, ignored
                )?
                (?:
                    Z |  # UTC
                    (?P<tz_hour>[+-](?:[01]\\d|2[0-3]))
                    :(?P<tz_minute>[0-5]\\d)
                )
            )?
        )?
    )?
    [ \t\n\f\r]*
    $
''', re.VERBOSE)


def parse_w3c_date(meta_name, string):
    """Parse datetimes as defined by the W3C.

    See https://www.w3.org/TR/NOTE-datetime

    """
    if W3C_DATE_RE.match(string):
        return string
    else:
        LOGGER.warning(
            'Invalid date in <meta name="%s"> %r', meta_name, string)
