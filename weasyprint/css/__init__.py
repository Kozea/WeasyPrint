# coding: utf-8
"""
    weasyprint.css
    --------------

    This module takes care of steps 3 and 4 of “CSS 2.1 processing model”:
    Retrieve stylesheets associated with a document and annotate every element
    with a value for every CSS property.

    http://www.w3.org/TR/CSS21/intro.html#processing-model

    This module does this in more than two steps. The
    :func:`get_all_computed_styles` function does everything, but it is itsef
    based on other functions in this module.

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import re

import tinycss
import cssselect
import lxml.etree

from . import properties
from . import computed_values
from .validation import preprocess_declarations
from ..urls import (element_base_url, get_url_attribute, url_join,
                    URLFetchingError)
from ..logger import LOGGER
from ..compat import iteritems
from .. import CSS


PARSER = tinycss.make_parser('page3')


# Reject anything not in here:
PSEUDO_ELEMENTS = (None, 'before', 'after', 'first-line', 'first-letter')

# Selectors for @page rules can have a pseudo-class, one of :first, :left,
# :right or :blank. This maps pseudo-classes to lists of "page types" selected.
PAGE_PSEUDOCLASS_TARGETS = {
    'first': [
        'first_left_page', 'first_right_page',
        'first_blank_left_page', 'first_blank_right_page'],
    'left': [
        'left_page', 'first_left_page',
        'blank_left_page', 'first_blank_left_page'],
    'right': [
        'right_page', 'first_right_page',
        'blank_right_page', 'first_blank_right_page'],
    'blank': [
        'blank_left_page', 'first_blank_left_page',
        'blank_right_page', 'first_blank_right_page'],
    # no pseudo-class: all pages
    None: [
        'left_page', 'right_page', 'first_left_page', 'first_right_page',
        'blank_left_page', 'blank_right_page',
        'first_blank_left_page', 'first_blank_right_page'],
}

# A test function that returns True if the given property name has an
# initial value that is not always the same when computed.
RE_INITIAL_NOT_COMPUTED = re.compile(
    '^(display|(border_[a-z]+|outline)_(width|color))$').match


class StyleDict(object):
    """A mapping (dict-like) that allows attribute access to values.

    Allow eg. ``style.font_size`` instead of ``style['font-size']``.

    :param parent: if given, should be a mapping. Values missing from this
                   dict will be looked up in the parent dict. Setting a value
                   in this dict masks any value in the parent.

    """
    def __init__(self, data=None, parent=None):
        if data is None:
            data = {}
        else:
            data = dict(data)
        if parent is None:
            parent = {}
        # work around our own __setattr__
        object.__setattr__(self, '_storage', data)
        object.__setattr__(self, '_parent', parent)

    def __getitem__(self, key):
        storage = self._storage
        if key in storage:
            return storage[key]
        else:
            return self._parent[key]

    def __setitem__(self, key, value):
        self._storage[key] = value

    def get_color(self, key):
        value = self[key]
        return value if value != 'currentColor' else self.color

    def updated_copy(self, other):
        copy = self.copy()
        copy._storage.update(other)
        return copy

    def __contains__(self, key):
        return key in self._parent or key in self._storage

    __getattr__ = __getitem__  # May raise KeyError instead of AttributeError
    __setattr__ = __setitem__

    def copy(self):
        """Copy the ``StyleDict``.

        Create a new StyleDict with this one as the parent. This is a cheap
        "copy-on-write". Modifications in the copy will not affect
        the original, but modifications in the original *may* affect the
        copy.

        """
        if self._storage:
            parent = self
        else:
            parent = self._parent
        style = type(self)(parent=parent)
        if self.anonymous:
            object.__setattr__(style, 'anonymous', True)
        return style

    def inherit_from(self):
        """Return a new StyleDict with inherited properties from this one.

        Non-inherited properties get their initial values.
        This is the styles for an anonymous box.
        """
        style = computed_from_cascaded(
            cascaded={}, parent_style=self,
            # Only used by non-inherited properties. eg `content: attr(href)`
            element=None)
        object.__setattr__(style, 'anonymous', True)
        return style

    # Default values, may be overriden on instances
    anonymous = False


def get_child_text(element):
    """Return the text directly in the element, not descendants."""
    content = [element.text] if element.text else []
    for child in element:
        if child.tail:
            content.append(child.tail)
    return ''.join(content)


def find_stylesheets(element_tree, device_media_type, url_fetcher):
    """Yield the stylesheets in ``element_tree``.

    The output order is the same as the source order.

    """
    from ..html import element_has_link_type  # Work around circular imports.

    for element in element_tree.iter('style', 'link'):
        mime_type = element.get('type', 'text/css').split(';', 1)[0].strip()
        # Only keep 'type/subtype' from 'type/subtype ; param1; param2'.
        if mime_type != 'text/css':
            continue
        media_attr = element.get('media', '').strip() or 'all'
        media = [media_type.strip() for media_type in media_attr.split(',')]
        if not evaluate_media_query(media, device_media_type):
            continue
        if element.tag == 'style':
            # Content is text that is directly in the <style> element, not its
            # descendants
            content = get_child_text(element)
            # lxml should give us either unicode or ASCII-only bytestrings, so
            # we don't need `encoding` here.
            css = CSS(string=content, base_url=element_base_url(element),
                      url_fetcher=url_fetcher, media_type=device_media_type)
            yield css
        elif element.tag == 'link' and element.get('href'):
            if not element_has_link_type(element, 'stylesheet') or \
                    element_has_link_type(element, 'alternate'):
                continue
            href = get_url_attribute(element, 'href')
            if href is not None:
                try:
                    yield CSS(url=href, url_fetcher=url_fetcher,
                              _check_mime_type=True,
                              media_type=device_media_type)
                except URLFetchingError as exc:
                    LOGGER.warning('Failed to load stylesheet at %s : %s',
                                   href, exc)


def find_style_attributes(element_tree):
    """
    Yield ``element, declaration, base_url`` for elements with
    a "style" attribute.
    """
    parser = PARSER
    for element in element_tree.iter():
        style_attribute = element.get('style')
        if style_attribute:
            declarations, errors = parser.parse_style_attr(style_attribute)
            for error in errors:
                LOGGER.warning(error)
            yield element, declarations, element_base_url(element)


def evaluate_media_query(query_list, device_media_type):
    """Return the boolean evaluation of `query_list` for the given
    `device_media_type`.

    :attr query_list: a cssutilts.stlysheets.MediaList
    :attr device_media_type: a media type string (for now)

    """
    # TODO: actual support for media queries, not just media types
    return 'all' in query_list or device_media_type in query_list


def declaration_precedence(origin, importance):
    """Return the precedence for a declaration.

    Precedence values have no meaning unless compared to each other.

    Acceptable values for ``origin`` are the strings ``'author'``, ``'user'``
    and ``'user agent'``.

    """
    # See http://www.w3.org/TR/CSS21/cascade.html#cascading-order
    if origin == 'user agent':
        return 1
    elif origin == 'user' and not importance:
        return 2
    elif origin == 'author' and not importance:
        return 3
    elif origin == 'author':  # and importance
        return 4
    else:
        assert origin == 'user'  # and importance
        return 5


def add_declaration(cascaded_styles, prop_name, prop_values, weight, element,
                    pseudo_type=None):
    """Set the value for a property on a given element.

    The value is only set if there is no value of greater weight defined yet.

    """
    style = cascaded_styles.setdefault((element, pseudo_type), {})
    _values, previous_weight = style.get(prop_name, (None, None))
    if previous_weight is None or previous_weight <= weight:
        style[prop_name] = prop_values, weight


def set_computed_styles(cascaded_styles, computed_styles, element, parent,
                        root=None, pseudo_type=None):
    """Set the computed values of styles to ``element``.

    Take the properties left by ``apply_style_rule`` on an element or
    pseudo-element and assign computed values with respect to the cascade,
    declaration priority (ie. ``!important``) and selector specificity.

    """
    parent_style = computed_styles[parent, None] \
        if parent is not None else None
    # When specified on the font-size property of the root element, the rem
    # units refer to the property’s initial value.
    root_style = {'font_size': properties.INITIAL_VALUES['font_size']} \
        if element is root else computed_styles[root, None]
    cascaded = cascaded_styles.get((element, pseudo_type), {})

    computed_styles[element, pseudo_type] = computed_from_cascaded(
        element, cascaded, parent_style, pseudo_type, root_style
    )


def computed_from_cascaded(element, cascaded, parent_style, pseudo_type=None,
                           root_style=None):
    """Get a dict of computed style mixed from parent and cascaded styles."""
    if not cascaded and parent_style is not None:
        # Fast path for anonymous boxes:
        # no cascaded style, only implicitly initial or inherited values.
        computed = StyleDict(parent=properties.INITIAL_VALUES)
        for name in properties.INHERITED:
            computed[name] = parent_style[name]
        # border-*-style is none, so border-width computes to zero.
        # Other than that, properties that would need computing are
        # border-*-color, but they do not apply.
        for side in ('top', 'bottom', 'left', 'right'):
            computed['border_%s_width' % side] = 0
        computed['outline_width'] = 0
        return computed

    # Handle inheritance and initial values
    specified = StyleDict()
    computed = StyleDict()
    for name, initial in iteritems(properties.INITIAL_VALUES):
        if name in cascaded:
            value, _precedence = cascaded[name]
            keyword = value
        else:
            if name in properties.INHERITED:
                keyword = 'inherit'
            else:
                keyword = 'initial'

        if keyword == 'inherit' and parent_style is None:
            # On the root element, 'inherit' from initial values
            keyword = 'initial'

        if keyword == 'initial':
            value = initial
            if not RE_INITIAL_NOT_COMPUTED(name):
                # The value is the same as when computed
                computed[name] = value
        elif keyword == 'inherit':
            value = parent_style[name]
            # Values in parent_style are already computed.
            computed[name] = value

        specified[name] = value

    return computed_values.compute(
        element, pseudo_type, specified, computed, parent_style, root_style
    )


class Selector(object):
    def __init__(self, specificity, pseudo_element, match):
        self.specificity = specificity
        self.pseudo_element = pseudo_element
        self.match = match


def preprocess_stylesheet(device_media_type, base_url, rules, url_fetcher):
    """Do the work that can be done early on stylesheet, before they are
    in a document.

    """
    selector_to_xpath = cssselect.HTMLTranslator().selector_to_xpath
    for rule in rules:
        if not rule.at_keyword:
            declarations = list(preprocess_declarations(
                base_url, rule.declarations))
            if declarations:
                selector_string = rule.selector.as_css()
                try:
                    selector_list = []
                    for selector in cssselect.parse(selector_string):
                        xpath = selector_to_xpath(selector)
                        try:
                            lxml_xpath = lxml.etree.XPath(xpath)
                        except ValueError as exc:
                            # TODO: Some characters are not supported by lxml's
                            # XPath implementation (including control
                            # characters), but these characters are valid in
                            # the CSS2.1 specification.
                            raise cssselect.SelectorError(str(exc))
                        selector_list.append(Selector(
                            (0,) + selector.specificity(),
                            selector.pseudo_element, lxml_xpath))
                    for selector in selector_list:
                        if selector.pseudo_element not in PSEUDO_ELEMENTS:
                            raise cssselect.ExpressionError(
                                'Unknown pseudo-element: %s'
                                % selector.pseudo_element)
                except cssselect.SelectorError as exc:
                    LOGGER.warning("Invalid or unsupported selector '%s', %s",
                                   selector_string, exc)
                    continue
                yield rule, selector_list, declarations

        elif rule.at_keyword == '@import':
            if not evaluate_media_query(rule.media, device_media_type):
                continue
            url = url_join(base_url, rule.uri, '@import at %s:%s',
                           rule.line, rule.column)
            if url is not None:
                try:
                    stylesheet = CSS(url=url, url_fetcher=url_fetcher,
                                     media_type=device_media_type)
                except URLFetchingError as exc:
                    LOGGER.warning('Failed to load stylesheet at %s : %s',
                                   url, exc)
                else:
                    for result in stylesheet.rules:
                        yield result

        elif rule.at_keyword == '@media':
            if not evaluate_media_query(rule.media, device_media_type):
                continue
            for result in preprocess_stylesheet(
                    device_media_type, base_url, rule.rules, url_fetcher):
                yield result

        elif rule.at_keyword == '@page':
            page_name, pseudo_class = rule.selector
            # TODO: support named pages (see CSS3 Paged Media)
            if page_name is not None:
                LOGGER.warning('Named pages are not supported yet, the whole '
                               '@page %s rule was ignored.', page_name + (
                                   ':' + pseudo_class if pseudo_class else ''))
                continue
            declarations = list(preprocess_declarations(
                base_url, rule.declarations))

            # Use a double lambda to have a closure that holds page_types
            match = (lambda page_types: lambda _document: page_types)(
                PAGE_PSEUDOCLASS_TARGETS[pseudo_class])
            specificity = rule.specificity

            if declarations:
                selector_list = [Selector(specificity, None, match)]
                yield rule, selector_list, declarations

            for margin_rule in rule.at_rules:
                declarations = list(preprocess_declarations(
                    base_url, margin_rule.declarations))
                if declarations:
                    selector_list = [Selector(
                        specificity, margin_rule.at_keyword, match)]
                    yield margin_rule, selector_list, declarations


def get_all_computed_styles(html, user_stylesheets=None):
    """Compute all the computed styles of all elements
    in the given ``html`` document.

    Do everything from finding author stylesheets to parsing and applying them.

    Return a ``style_for`` function that takes an element and an optional
    pseudo-element type, and return a StyleDict object.

    """
    element_tree = html.root_element
    device_media_type = html.media_type
    url_fetcher = html.url_fetcher
    ua_stylesheets = html._ua_stylesheets()
    author_stylesheets = list(find_stylesheets(
        element_tree, device_media_type, url_fetcher))

    # keys: (element, pseudo_element_type)
    #    element: a lxml element object or the '@page' string for @page styles
    #    pseudo_element_type: a string such as 'first' (for @page) or 'after',
    #        or None for normal elements
    # values: dicts of
    #     keys: property name as a string
    #     values: (values, weight)
    #         values: a PropertyValue-like object
    #         weight: values with a greater weight take precedence, see
    #             http://www.w3.org/TR/CSS21/cascade.html#cascading-order
    cascaded_styles = {}

    for sheets, origin in (
        # Order here is not important ('origin' is).
        # Use this order for a regression test
        (ua_stylesheets or [], 'user agent'),
        (author_stylesheets, 'author'),
        (user_stylesheets or [], 'user'),
    ):
        for sheet in sheets:
            for _rule, selector_list, declarations in sheet.rules:
                for selector in selector_list:
                    specificity = selector.specificity
                    pseudo_type = selector.pseudo_element
                    for element in selector.match(element_tree):
                        for name, values, importance in declarations:
                            precedence = declaration_precedence(
                                origin, importance)
                            weight = (precedence, specificity)
                            add_declaration(
                                cascaded_styles, name, values, weight,
                                element, pseudo_type)

    specificity = (1, 0, 0, 0)
    for element, declarations, base_url in find_style_attributes(element_tree):
        for name, values, importance in preprocess_declarations(
                base_url, declarations):
            precedence = declaration_precedence('author', importance)
            weight = (precedence, specificity)
            add_declaration(cascaded_styles, name, values, weight, element)

    # keys: (element, pseudo_element_type), like cascaded_styles
    # values: StyleDict objects:
    #     keys: property name as a string
    #     values: a PropertyValue-like object
    computed_styles = {}

    # First, computed styles for "real" elements *in tree order*
    # Tree order is important so that parents have computed styles before
    # their children, for inheritance.

    # Iterate on all elements, even if there is no cascaded style for them.
    for element in element_tree.iter():
        set_computed_styles(cascaded_styles, computed_styles, element,
                            root=element_tree, parent=element.getparent())

    # Then computed styles for @page.

    # Iterate on all possible page types, even if there is no cascaded style
    # for them.
    for page_type in PAGE_PSEUDOCLASS_TARGETS[None]:
        set_computed_styles(
            cascaded_styles, computed_styles, page_type,
            # @page inherits from the root element:
            # http://lists.w3.org/Archives/Public/www-style/2012Jan/1164.html
            root=element_tree, parent=element_tree)

    # Then computed styles for pseudo elements, in any order.
    # Pseudo-elements inherit from their associated element so they come
    # last. Do them in a second pass as there is no easy way to iterate
    # on the pseudo-elements for a given element with the current structure
    # of cascaded_styles. (Keys are (element, pseudo_type) tuples.)

    # Only iterate on pseudo-elements that have cascaded styles. (Others
    # might as well not exist.)
    for element, pseudo_type in cascaded_styles:
        if pseudo_type:
            set_computed_styles(cascaded_styles, computed_styles,
                                element, pseudo_type=pseudo_type,
                                # The pseudo-element inherits from the element.
                                root=element_tree, parent=element)

    # This is mostly useful to make pseudo_type optional.
    def style_for(element, pseudo_type=None, __get=computed_styles.get):
        """
        Convenience function to get the computed styles for an element.
        """
        return __get((element, pseudo_type))

    return style_for
