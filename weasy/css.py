from cssutils import parseString, parseUrl
from cssutils.stylesheets import StyleSheetList, MediaList

from . import properties


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

def find_stylesheets(html_document):
    """
    Return a `StyleSheetList` from a DOM document.
    """
    sheets = StyleSheetList()
    sheets.extend(find_style_elements(html_document))
    sheets.extend(find_link_stylesheet_elements(html_document))
    return sheets


def evaluate_media_query(query_list, medium):
    """
    Return the boolean evaluation of `query_list` for the given `medium`
    
    :attr query_list: a cssutilts.stlysheets.MediaList
    :attr medium: a media type string (for now)
    
    TODO: actual support for media queries, not just media types
    """
    return any(query.mediaText in (medium, 'all') for query in query_list)


def resolve_import_media(sheets, medium):
    """
    Resolves @import and @media rules in the given StlyleSheetList, and yields
    applicable rules for `medium`.
    """
    for sheet in sheets:
        if not evaluate_media_query(sheet.media, medium):
            continue
        for rule in sheet.cssRules:
            if rule.type in (rule.CHARSET_RULE, rule.COMMENT):
                pass # ignored
            elif rule.type == rule.IMPORT_RULE:
                subsheet = rule.styleSheet
            elif rule.type == rule.MEDIA_RULE:
                # CSSMediaRule is kinda like a CSSStyleSheet: it has media and
                # cssRules attributes.
                subsheet = rule
            else:
                yield rule # pass other rules through
                continue # no sub-stylesheet here.
            for subrule in resolve_import_media([subsheet], medium):
                yield subrule


def expand_shorthands(sheet):
    """
    Changes IN-PLACE the given stylesheet and its imported stylesheets
    (recursively) to expand shorthand properties.
    eg. margin becomes margin-top, margin-right, margin-bottom and margin-left.
    """
    for rule in sheet.cssRules:
        if rule.type == rule.IMPORT_RULE:
            expand_shorthands(rule.styleSheet)
        elif rule.type == rule.MEDIA_RULE:
            # CSSMediaRule is kinda like a CSSStyleSheet: it has media and
            # cssRules attributes.
            expand_shorthands(rule)
        elif rule.type in (rule.STYLE_RULE, rule.PAGE_RULE):
            for name, expander in properties.SHORTHANDS.iteritems():
                property = rule.style.getProperty(name)
                if not property:
                    continue
                for new_property in expander(property):
                    rule.style.setProperty(new_property)
                rule.style.removeProperty(property.name)
