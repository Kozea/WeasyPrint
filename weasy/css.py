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

"""
    weasy.css
    ---------
    
    This module takes care of steps 3 and 4 of “CSS 2.1 processing model”:
    Retrieve stylesheets associated with a document and annotate every element
    with a value for every CSS property.
    http://www.w3.org/TR/CSS21/intro.html#processing-model
    
    This module does this in more than two steps. The `annotate_document`
    function does everything, butthere is also a function for each step:
    
     * ``find_stylesheets``: Find and parse all author stylesheets in a document
     * ``remove_ignored_declarations``: Remove illegal and unsupported
       declarations
     * ``make_urls_absolute``
     * ``expand_shorthand``: Replace shorthand properties
     * ``resolve_import_media``: Resolve @media and @import rules
     * ``apply_style_rule``: Apply a CSSStyleRule to a document
     * ``assign_properties``: Assign on computed value for each property to
       every DOM element.
"""
import os.path
from cssutils import parseString, parseUrl, parseStyle, parseFile
from cssutils.css import Value

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


def make_urls_absolute(sheet):
    # TODO
    pass


def remove_ignored_declarations(sheet):
    # TODO
    pass
    

def evaluate_media_query(query_list, medium):
    """
    Return the boolean evaluation of `query_list` for the given `medium`
    
    :attr query_list: a cssutilts.stlysheets.MediaList
    :attr medium: a media type string (for now)
    
    """
    # TODO: actual support for media queries, not just media types
    return query_list.mediaText == 'all' \
        or any(query.mediaText == medium for query in query_list)


def resolve_import_media(sheet, medium):
    """
    Resolves @import and @media rules in the given CSSStlyleSheet, and yields
    applicable rules for `medium`.
    """
    if not evaluate_media_query(sheet.media, medium):
        return
    for rule in sheet.cssRules:
        if rule.type in (rule.CHARSET_RULE, rule.COMMENT):
            continue # ignored
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


def build_lxml_proxy_cache(document):
    """
    Build as needed a proxy cache for an lxml document.
    
    ``Element`` python objects in lxml are only proxies to C space memory
    (libxml2 data structures.) These objects may be created and destroyed at
    any time, so we can generally not keep state in them.

    The lxml documentation[1] only gives one guarantee: if a reference to a
    proxy object is kept, this same object will always be used and we can keep
    data there. A proxy cache is a list of these proxy objects for all elements,
    just to make sure that they are kept alive.

    [1] http://lxml.de/element_classes.html#element-initialization
    """
    if not hasattr(document, 'proxy_cache'):
        document.proxy_cache = list(document.iter())
    

def declaration_precedence(origin, priority):
    """
    Return the precedence for a rule. Precedence values have no meaning unless
    compared to each other.

    Acceptable values for `origin` are the strings 'author', 'user' and
    'user agent'.
    """
    # See http://www.w3.org/TR/CSS21/cascade.html#cascading-order
    if origin == 'user agent':
        return 1
    elif origin == 'user' and not priority:
        return 2
    elif origin == 'author' and not priority:
        return 3
    elif origin == 'author': # and priority
        return 4
    elif origin == 'user': # and priority
        return 5
    else:
        assert ValueError('Unkown origin: %r' % origin)
        

def apply_style_rule(rule, document, origin):
    """
    Apply a CSSStyleRule to a document according to its selectors, attaching
    Property objects with their precedence to DOM elements.
    
    Acceptable values for `origin` are the strings 'author', 'user' and
    'user agent'.
    """
    build_lxml_proxy_cache(document)
    for selector in rule.selectorList:
        for element in document.cssselect(selector.selectorText):
            if not hasattr(element, 'applicable_properties'):
                element.applicable_properties = []
            for prop in rule.style:
                # TODO: ignore properties that do not apply to the current 
                # medium? http://www.w3.org/TR/CSS21/intro.html#processing-model
                precedence = (
                    declaration_precedence(origin, prop.priority),
                    selector.specificity
                )
                element.applicable_properties.append((precedence, prop))


def handle_style_attribute(element):
    """
    Return the element’s ``applicable_properties`` list after adding properties
    from the `style` attribute.
    """
    declarations = getattr(element, 'applicable_properties', [])
    style_attribute = element.get('style')
    if style_attribute:
        # TODO: no href for parseStyle. What about relative URLs?
        # CSS3 says we should resolve relative to the attribute:
        # http://www.w3.org/TR/css-style-attr/#interpret
        for prop in parseStyle(style_attribute):
            precedence = (
                declaration_precedence('author', prop.priority),
                # 1 for being a style attribute, 0 as there is no selector.
                (1, 0, 0, 0)
            )
            declarations.append((precedence, prop))
    return declarations


def handle_inheritance(element):
    """
    The specified value is the parent element’s computed value iif one of the
    following is true:
     * The cascade did not result in a value, and the the property is inherited
     * The the value is the keyword 'inherit'.
    """
    style = element.style
    parent = element.getparent()
    if parent is None: # root element
        for name, value in style.iteritems():
            # The PropertyValue object has value attribute
            if value.value == 'inherit':
                # The root element can not inherit from anything:
                # use the initial value.
                style[name] = Value('initial')
    else:
        # The parent appears before in tree order, so we should already have
        # finished with its computed values.
        for name, value in style.iteritems():
            if value.value == 'inherit':
                style[name] = parent.style[name]
        for name in properties.INHERITED:
            if name not in style:
                style[name] = parent.style[name]


def handle_initial_values(element):
    """
    Properties that do not have a value after inheritance or whose value is the
    'initial' keyword (CSS3) get their initial value.
    """
    style = element.style
    for name, initial in properties.INITIAL_VALUES.iteritems():
        # Explicit 'initial' values are new in CSS3
        # http://www.w3.org/TR/css3-values/#computed0
        if style.get(name, Value('initial')).value == 'initial':
            style[name] = initial

    # Special cases for initial values that can not be expressed as CSS
    
    # border-color: same as color
    for name in ('border-top-color', 'border-right-color',
                 'border-bottom-color', 'border-left-color'):
        if style.get(name, Value('initial')).value == 'initial':
            style[name] = style['color']

    # text-align: left in left-to-right text, right in right-to-left
    if style.get('text-align', Value('initial')).value == 'initial':
        if style['direction'].value == 'rtl':
            style['text-align'] = Value('right')
        else:
            style['text-align'] = Value('left')


def handle_computed_values(element):
    """
    Normalize values as much as possible without rendering the document.
    """
    style = element.style
    parent = element.getparent()
    # TODO: http://www.w3.org/TR/css3-values/#computed0


def assign_properties(document):
    """
    For every element of the document, take the properties left by
    ``apply_style_rule`` and assign computed values with respect to the cascade,
    declaration priority (ie. ``!important``) and selector specificity.
    """
    build_lxml_proxy_cache(document)
    for element in document.iter():
        declarations = handle_style_attribute(element)
        
        # If apply_style_rule() was called in appearance order, the stability
        # of Python's sort fulfills rule 4 of the cascade.
        # This lambda has one parameter deconstructed as a tuple
        declarations.sort(key=lambda (precedence, prop): precedence)
        element.style = style = {}
        for precedence, prop in declarations:
            style[prop.name] = prop.propertyValue
        
        handle_inheritance(element)    
        handle_initial_values(element)
        handle_computed_values(element)
        

def annotate_document(document, user_stylesheets=None, ua_stylesheets=None,
                      medium='print'):
    """
    Do everything from finding author stylesheets in the given HTML document
    to parsing and applying them, to finish with a `style` attribute on
    every DOM element: a dictionary with values for all CSS 2.1 properties.
    """
    document.make_links_absolute()
    author_stylesheets = find_stylesheets(document)
    for sheets, origin in ((author_stylesheets, 'author'),
                           (user_stylesheets, 'user'),
                           (ua_stylesheets, 'user agent')):
        for sheet in sheets:
            # TODO: UA and maybe user stylesheets might only need to be expanded
            # once, not for every document.
            remove_ignored_declarations(sheet)
            make_urls_absolute(sheet)
            expand_shorthands(sheet)
            for rule in resolve_import_media(sheet, medium):
                print sheet.href.split('/')[-1], origin, rule
                if rule.type == rule.STYLE_RULE:
                    apply_style_rule(rule, document, origin)
                # TODO: handle @font-face, @namespace, @page, and @variables
    assign_properties(document)

