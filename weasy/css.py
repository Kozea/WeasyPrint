from cssutils import parseString, parseUrl
# coding: utf8

#  WeasyPrint converts web documents (HTML, CSS, ...) to PDF.
#  Copyright (C) 2011  Simon Sapin
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

from cssutils.css import CSSStyleDeclaration

from . import properties


HTML4_DEFAULT_STYLESHEET = parseFile(os.path.join(os.path.dirname(__file__),
    'html4_default.css'))


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
    Yield stylesheets from a DOM document.
    """
    # TODO: merge these to give them in tree order
    for sheet in find_style_elements(html_document):
        yield sheet
    for sheet in find_link_stylesheet_elements(html_document):
        yield sheet


def evaluate_media_query(query_list, medium):
    """
    Return the boolean evaluation of `query_list` for the given `medium`
    
    :attr query_list: a cssutilts.stlysheets.MediaList
    :attr medium: a media type string (for now)
    
    TODO: actual support for media queries, not just media types
    """
    return any(query.mediaText in (medium, 'all') for query in query_list)


def resolve_import_media(sheet, medium):
    """
    Resolves @import and @media rules in the given CSSStlyleSheet, and yields
    applicable rules for `medium`.
    """
    if not evaluate_media_query(sheet.media, medium):
        return
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
            # pass other rules through: "normal" rulesets, @font-face,
            # @namespace, @page, and @variables
            yield rule
            continue # no sub-stylesheet here.
        for subrule in resolve_import_media(subsheet, medium):
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
            rule.style = properties.expand_shorthands_in_declaration(rule.style)
        # TODO: @font-face

