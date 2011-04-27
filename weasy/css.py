from cssutils import parseString, parseUrl
from cssutils.stylesheets import StyleSheetList, MediaList


__all__ = ['find_stylesheets']


def strip_mimetype_parameters(mimetype):
    """Only keep 'type/subtype' from 'type/subtype ; param1; param2'."""
    if mimetype:
        return mimetype.split(';', 1)[0].strip()

def is_not_css(element):
    """
    Return True if the element has a `type` attribute with a MIME type other
    than 'text/css'.
    """
    mimetype = element.get('type')
    return mimetype and strip_mimetype_parameters(mimetype) != 'text/css'

def media_attr(element):
    """Returns the `media` attribute if it is not just whitespace."""
    media = element.get('media')
    if media and media.strip():
        return media
    # cssutils translates None to 'all'.

def find_style_elements(document):
    for style in document.iter('style'):
        # TODO: handle the `scoped` attribute
        # Content is text that is directly in the <style> element, not its
        # descendants
        content = [style.text]
        for child in style:
            content.append(child.tail)
        content = ''.join(content)
        if is_not_css(style):
            continue
        # lxml should give us either unicode or ASCII-only bytestrings, so
        # we don't need `encoding` here.
        yield parseString(content, href=style.base_url, media=media_attr(style),
                          title=style.get('title'))

def find_link_stylesheet_elements(document):
    for link in document.iter('link'):
        if (
            ' stylesheet ' not in ' %s ' % link.get('rel', '')
            or not link.get('href')
            or is_not_css(link)
        ):
            continue
        # URLs should have been made absolute earlier
        yield parseUrl(link.get('href'), media=media_attr(link),
                       title=link.get('title'))

def find_stylesheets(document):
    """
    Return a `StyleSheetList` from a DOM document.
    """
    sheets = StyleSheetList()
    sheets.extend(find_style_elements(document))
    sheets.extend(find_link_stylesheet_elements(document))
    return sheets
