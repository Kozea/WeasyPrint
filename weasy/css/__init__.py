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
function does everything, but there is also a function for each step:

 * ``find_stylesheets``: Find and parse all author stylesheets in a document
 * ``effective_rules``: Resolve @media and @import rules
 * ``match_selectors``: Find elements in a document that match a selector list
 * ``find_style_attributes``: Find and parse all `style` HTML attributes
 * ``effective_declarations``: Remove ignored properties and expand shorthands
 * ``add_property``: Take applicable properties and only keep those with
   highest weight.
 * ``set_computed_styles``: Handle initial values, inheritance and computed
   values.
"""

import os.path
try:
    from urlparse import urljoin
except ImportError:
    # Python 3
    from urllib.parse import urljoin

from cssutils import parseString, parseUrl, parseStyle, parseFile
from cssutils.css import PropertyValue
from lxml import cssselect

from . import shorthands
from . import inheritance
from . import initial_values
from . import computed_values
from . import page


HTML4_DEFAULT_STYLESHEET = parseFile(os.path.join(os.path.dirname(__file__),
    'html4_default.css'))


# Pseudo-classes and pseudo-elements are the same to lxml.cssselect.parse().
# List the identifiers for all CSS3 pseudo elements here to distinguish them.
PSEUDO_ELEMENTS = ('before', 'after', 'first-line', 'first-letter')


def find_stylesheets(document):
    """
    Find and parse stylesheets in a Document object. Return an iterable of
    stylesheets, in tree order.
    """
    for element in document.dom.iter():
        mimetype = element.get('type')
        # Only keep 'type/subtype' from 'type/subtype ; param1; param2'.
        if mimetype and mimetype.split(';', 1)[0].strip() != 'text/css':
            continue
        # cssutils translates '' to 'all'.
        media_attr = element.get('media', '').strip()
        if element.tag == 'style':
            # TODO: handle the `scoped` attribute
            # Content is text that is directly in the <style> element, not its
            # descendants
            content = [element.text]
            for child in element:
                content.append(child.tail)
            content = ''.join(content)
            # lxml should give us either unicode or ASCII-only bytestrings, so
            # we don't need `encoding` here.
            yield parseString(content, href=element.base_url,
                              media=media_attr, title=element.get('title'))
        elif element.tag == 'link' and element.get('href') \
                and ' stylesheet ' in ' %s ' % element.get('rel', ''):
            # URLs should NOT have been made absolute earlier
            # TODO: support the <base> HTML element, but do not use
            # lxml.html.HtmlElement.make_links_absolute() that changes the tree
            href = urljoin(element.base_url, element.get('href'))
            yield parseUrl(href, media=media_attr, title=element.get('title'))


def find_style_attributes(document):
    """
    Find and parse style HTML attributes in the given document. Return an
    iterable of (element, declaration_block).
    """
    for element in document.dom.iter():
        style_attribute = element.get('style')
        if style_attribute:
            # TODO: no href for parseStyle. What about relative URLs?
            # CSS3 says we should resolve relative to the attribute:
            # http://www.w3.org/TR/css-style-attr/#interpret
            yield element, parseStyle(style_attribute)


def evaluate_media_query(query_list, medium):
    """
    Return the boolean evaluation of `query_list` for the given `medium`

    :attr query_list: a cssutilts.stlysheets.MediaList
    :attr medium: a media type string (for now)

    """
    # TODO: actual support for media queries, not just media types
    return query_list.mediaText == 'all' \
        or any(query.mediaText == medium for query in query_list)


def effective_rules(sheet, medium):
    """
    Resolves @import and @media rules in the given CSSStlyleSheet, and yields
    applicable rules for `medium`.
    """
    # sheet.media is not intrinsic but comes from where the stylesheet was
    # found: media HTML attribute, @import or @media rule.
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
        # subsheet has the .media attribute from the @import or @media rule.
        for subrule in effective_rules(subsheet, medium):
            yield subrule


def declaration_is_valid(prop):
    """
    Return whether the given Property object is invalid or unsupported,
    and thus should be ignored.

    ***Not implemented yet.***
    """
    # TODO implement validation

    # TODO: ignore properties that do not apply to the current
    # medium? http://www.w3.org/TR/CSS21/intro.html#processing-model
    return True


def effective_declarations(declaration_block):
    """
    In the given declaration block, ignore invalid or unsupported declarations
    and expand shorthand properties. Return a iterable of
    (property_name, property_value_list, importance) tuples.
    """
    for declaration in declaration_block:
        if declaration_is_valid(declaration):
            for name, values in shorthands.expand_shorthand(declaration):
                yield name, values, declaration.priority
        else:
            # TODO: log that something was ignored
            pass


def declaration_precedence(origin, importance):
    """
    Return the precedence for a declaration. Precedence values have no meaning
    unless compared to each other.

    Acceptable values for `origin` are the strings 'author', 'user' and
    'user agent'.
    """
    # See http://www.w3.org/TR/CSS21/cascade.html#cascading-order
    if origin == 'user agent':
        return 1
    elif origin == 'user' and not importance:
        return 2
    elif origin == 'author' and not importance:
        return 3
    elif origin == 'author': # and importance
        return 4
    elif origin == 'user': # and importance
        return 5
    else:
        assert ValueError('Unkown origin: %r' % origin)


def add_declaration(document, prop_name, prop_values, weight, element,
                    pseudo_type=None):
    """
    Set the value for a property on a given element unless there already
    is a value of greater weight.
    """
    style = document.cascaded_styles.setdefault((element, pseudo_type), {})
    _values, previous_weight = style.get(prop_name, (None, None))
    if previous_weight is None or previous_weight <= weight:
        style[prop_name] = prop_values, weight


def match_selectors(document, selector_list):
    """
    Match a list of selectors against a document and return an iterable of
    (element, pseudo_element_type, selector_specificity) tuples.

    selector_list should be an iterable of cssutils’ Selector objects.

    If any of the selectors is invalid, an empty iterable is returned as the
    whole rule should be ignored.
    """
    selectors = []
    for selector in selector_list:
        parsed_selector = cssselect.parse(selector.selectorText)
        # cssutils made sure that `selector` is not a "group of selectors"
        # in CSS3 terms (`rule.selectorList` is) so `parsed_selector` cannot be
        # of type `cssselect.Or`.
        # This leaves only three cases:
        #  * The selector ends with a pseudo-element. As `cssselect.parse()`
        #    parses left-to-right, `parsed_selector` is a `cssselect.Pseudo`
        #    instance that we can unwrap. This is the only place where CSS
        #    allows pseudo-element selectors.
        #  * The selector has a pseudo-element not at the end. This is invalid
        #    and the whole ruleset should be ignored.
        #  * The selector has no pseudo-element and is supported by
        #    `cssselect.CSSSelector`.
        if isinstance(parsed_selector, cssselect.Pseudo) \
                and parsed_selector.ident in PSEUDO_ELEMENTS:
            pseudo_type = parsed_selector.ident
            # Remove the pseudo-element from the selector
            parsed_selector = parsed_selector.element
        else:
            # No pseudo-element or invalid selector.
            pseudo_type = None

        try:
            selector_callable = cssselect.CSSSelector(parsed_selector)
        except cssselect.ExpressionError:
            # Invalid selector, ignore the whole ruleset.
            # TODO: log this error.
            return
        selectors.append((selector_callable, pseudo_type,
                          selector.specificity))

    # Only apply to elements after seeing all selectors, as we want to
    # ignore he whole ruleset if just one selector is invalid.
    # TODO: test that ignoring actually happens.
    for selector, pseudo_type, specificity in selectors:
        for element in selector(document.dom):
            yield element, pseudo_type, specificity


def match_page_selector(selector):
    """
    Return an iterable of ('@page', page_type, selector_specificity)
    for the given page selector text.

    '@page' is the marker for page pseudo-elements. It is added so that this
    function has the same return type as `match_selectors()`.

    Return an empty iterable if the selector is invalid or unsupported.
    """
    # TODO: support "page names" in page selectors (see CSS3 Paged Media)
    pseudo_class = selector or None
    page_types = page.PAGE_PSEUDOCLASS_TARGETS.get(pseudo_class, None)
    specificity = page.PAGE_PSEUDOCLASS_SPECIFICITY[pseudo_class]
    if page_types is not None:
        for page_type in page_types:
            yield '@page', page_type, specificity
    else:
        # Invalid/unsupported selector, ignore the whole rule
        # TODO: log/warn that something was ignored
        pass


class StyleDict(dict):
    """
    Allow attribute access to values, eg. style.font_size instead of
    style['font-size']

    This returns the numeric value for pixel lengths or zero lengths;
    and the string representation for any other value.

        >>> style = StyleDict({'margin-left': PropertyValue('12px'),
        ...                    'display': PropertyValue('block')}
        >>> assert style.display == 'block'
        >>> assert style.margin_left == 12

    Attributes can be set in the same way: numeric values become pixels lengths
    and strings are parsed as CSS values.

    CSS numbers without units (eg. font-weight: 700) are returned as strings
    to distinguish them from pixel lengths. Pixel lengths were favored as they
    are much more common. (Pixels are the unit for all computed lengths.)
    """
    def __getattr__(self, key):
        try:
            value = self[key.replace('_', '-')]
        except KeyError:
            raise AttributeError(key)
        if len(value) == 1 and value[0].type == 'DIMENSION' \
                and value[0].dimension == 'px':
            # cssutils promises that `DimensionValue.value` is an int or float
            assert isinstance(value[0].value, (float, int, long))
            return value[0].value
        elif len(value) == 1 and value[0].value == 0:
            return 0
        else:
            return value.value # PropertyValue.value: string representation

    def __setattr__(self, key, value):
        if isinstance(value, (float, int, long)):
            value = PropertyValue(str(value) + 'px')
        elif isinstance(value, basestring):
            value = PropertyValue(value)
        #else: assume a PropertyValue-like
        self[key.replace('_', '-')] = value

    def copy(self):
        """
        Same as dict.copy, but return an object of the same class.
        (dict.copy() always return a dict.)
        """
        return self.__class__(self)


def set_computed_styles(document, element, pseudo_type=None):
    """
    Take the properties left by ``apply_style_rule`` on an element or
    pseudo-element and assign computed values with respect to the cascade,
    declaration priority (ie. ``!important``) and selector specificity.
    """
    if element == '@page':
        parent = None
    elif pseudo_type:
        parent = element
    else:
        parent = element.getparent() # None for the root element

    if parent is None:
        parent_style = None
    else:
        parent_style = document.computed_styles[parent, None]

    cascaded = document.cascaded_styles.get((element, pseudo_type), {})
    style = computed_from_cascaded(element, cascaded, parent_style, pseudo_type)
    document.computed_styles[element, pseudo_type] = style


def computed_from_cascaded(element, cascaded, parent_style, pseudo_type=None):
    """
    Return a dict of computed styles from cascaded styles and the computed
    styles for the parent element.
    """
    style = StyleDict(
        (name, value)
        for name, (value, _precedence) in cascaded.iteritems())
    inheritance.handle_inheritance(style, parent_style)
    initial_values.handle_initial_values(style)
    computed_values.compute_values(element, pseudo_type, style, parent_style)
    return style


def annotate_document(document, user_stylesheets=None,
                      ua_stylesheets=(HTML4_DEFAULT_STYLESHEET,),
                      medium='print'):
    """
    Do everything from finding author stylesheets in the given HTML document
    to parsing and applying them, to end up with a `style` attribute on
    every DOM element: a dictionary with values for all CSS 2.1 properties.

    Given stylesheets will be modified in place.
    """
    document.cascaded_styles = {}
    author_stylesheets = find_stylesheets(document)

    for sheets, origin in ((author_stylesheets, 'author'),
                           (user_stylesheets or [], 'user'),
                           (ua_stylesheets or [], 'user agent')):
        for sheet in sheets:
            # TODO: UA and maybe user stylesheets might only need to be
            # expanded once, not for every document.
            for rule in effective_rules(sheet, medium):
                if rule.type == rule.STYLE_RULE:
                    matched = match_selectors(document, rule.selectorList)
                elif rule.type == rule.PAGE_RULE:
                    matched = match_page_selector(rule.selectorText)
                else:
                    # TODO: handle @font-face, @namespace, and @variables
                    continue

                declarations = list(effective_declarations(rule.style))

                for element, pseudo_type, specificity in matched:
                    for name, values, importance in declarations:
                        precedence = declaration_precedence(origin, importance)
                        weight = (precedence, specificity)
                        add_declaration(document, name, values, weight,
                                        element, pseudo_type)

    for element, declarations in find_style_attributes(document):
        for name, values, importance in effective_declarations(declarations):
            precedence = declaration_precedence('author', importance)
            # 1 for being a style attribute, 0 as there is no selector.
            weight = (precedence, (1, 0, 0, 0))
            add_declaration(document, name, values, weight,
                            element, pseudo_type)

    document.computed_styles = {}

    # First, computed styles for "real" elements *in tree order*
    # Tree order is important so that parents have computed styles before
    # their children, for inheritance.

    # Iterate on all elements, even if there is no cascaded style for them.
    for element in document.dom.iter():
        set_computed_styles(document, element)

    # Then computed styles for pseudo elements, in any order.
    # Pseudo-elements inherit from their associated element so they come
    # after. Do them in a second pass as there is no easy way to iterate
    # on the pseudo-elements for a given element with the current structure
    # of document.cascaded_styles. (Keys are (element, pseudo_type) tuples.)

    # Only iterate on pseudo-elements that have cascaded styles. (Others
    # might as well not exist.)
    for element, pseudo_type in document.cascaded_styles:
        if pseudo_type and element != '@page':
            set_computed_styles(document, element, pseudo_type)

    # Then computed styles for @page. (They could be done at any time.)

    # Iterate on all possible page types, even if there is no cascaded style
    # for them.
    for page_type in page.PAGE_PSEUDOCLASS_TARGETS[None]:
        set_computed_styles(document, '@page', page_type)
