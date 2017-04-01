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

import tinycss2
import cssselect
import lxml.etree

from . import properties
from . import computed_values
from .descriptors import preprocess_descriptors
from .validation import (preprocess_declarations, remove_whitespace,
                         split_on_comma)
from ..urls import (element_base_url, get_url_attribute, url_join,
                    URLFetchingError)
from ..logger import LOGGER
from ..compat import iteritems
from .. import CSS


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
    '^(display|column_gap|'
    '(border_[a-z]+|outline|column_rule)_(width|color))$').match


class StyleDict(dict):
    """A mapping (dict-like) that allows attribute access to values.

    Allow eg. ``style.font_size`` instead of ``style['font-size']``.

    """

    # TODO: We should remove that. Some attributes (eg. "clear") exist as
    # dict methods and can only be accessed with getitem.
    __getattr__ = dict.__getitem__

    def get_color(self, key):
        value = self[key]
        return value if value != 'currentColor' else self['color']

    def copy(self):
        """Copy the ``StyleDict``."""
        style = type(self)(self)
        style.anonymous = self.anonymous
        return style

    def inherit_from(self):
        """Return a new StyleDict with inherited properties from this one.

        Non-inherited properties get their initial values.
        This is the method used for an anonymous box.

        """
        style = computed_from_cascaded(
            cascaded={}, parent_style=self,
            # Only used by non-inherited properties. eg `content: attr(href)`
            element=None)
        style.anonymous = True
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


def find_stylesheets(element_tree, device_media_type, url_fetcher,
                     font_config):
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
            css = CSS(
                string=content, base_url=element_base_url(element),
                url_fetcher=url_fetcher, media_type=device_media_type,
                font_config=font_config)
            yield css
        elif element.tag == 'link' and element.get('href'):
            if not element_has_link_type(element, 'stylesheet') or \
                    element_has_link_type(element, 'alternate'):
                continue
            href = get_url_attribute(element, 'href')
            if href is not None:
                try:
                    yield CSS(
                        url=href, url_fetcher=url_fetcher,
                        _check_mime_type=True, media_type=device_media_type,
                        font_config=font_config)
                except URLFetchingError as exc:
                    LOGGER.warning('Failed to load stylesheet at %s : %s',
                                   href, exc)


def check_style_attribute(_parser, element, style_attribute):
    declarations = tinycss2.parse_declaration_list(style_attribute)
    return element, declarations, element_base_url(element)


def find_style_attributes(element_tree, presentational_hints=False):
    """Yield ``specificity, (element, declaration, base_url)`` rules.

    Rules from "style" attribute are returned with specificity
    ``(1, 0, 0, 0)``.

    If ``presentational_hints`` is ``True``, rules from presentational hints
    are returned with specificity ``(0, 0, 0, 0)``.

    """
    parser = None  # FIXME remove this
    for element in element_tree.iter():
        specificity = (1, 0, 0, 0)
        style_attribute = element.get('style')
        if style_attribute:
            yield specificity, check_style_attribute(
                parser, element, style_attribute)
        if not presentational_hints:
            continue
        specificity = (0, 0, 0, 0)
        if element.tag == 'body':
            # TODO: we should check the container frame element
            for part, position in (
                    ('height', 'top'), ('height', 'bottom'),
                    ('width', 'left'), ('width', 'right')):
                style_attribute = None
                for prop in ('margin%s' % part, '%smargin' % position):
                    if element.get(prop):
                        style_attribute = 'margin-%s:%spx' % (
                            position, element.get(prop))
                        break
                if style_attribute:
                    yield specificity, check_style_attribute(
                        parser, element, style_attribute)
            if element.get('background'):
                style_attribute = 'background-image:url(%s)' % (
                    element.get('background'))
                yield specificity, check_style_attribute(
                    parser, element, style_attribute)
            if element.get('bgcolor'):
                style_attribute = 'background-color:%s' % (
                    element.get('bgcolor'))
                yield specificity, check_style_attribute(
                    parser, element, style_attribute)
            if element.get('text'):
                style_attribute = 'color:%s' % element.get('text')
                yield specificity, check_style_attribute(
                    parser, element, style_attribute)
            # TODO: we should support link, vlink, alink
        elif element.tag == 'center':
            yield specificity, check_style_attribute(
                parser, element, 'text-align:center')
        elif element.tag == 'div':
            align = element.get('align', '').lower()
            if align == 'middle':
                yield specificity, check_style_attribute(
                    parser, element, 'text-align:center')
            elif align in ('center', 'left', 'right', 'justify'):
                yield specificity, check_style_attribute(
                    parser, element, 'text-align:%s' % align)
        elif element.tag == 'font':
            if element.get('color'):
                yield specificity, check_style_attribute(
                    parser, element, 'color:%s' % element.get('color'))
            if element.get('face'):
                yield specificity, check_style_attribute(
                    parser, element, 'font-family:%s' % element.get('face'))
            if element.get('size'):
                size = element.get('size').strip()
                relative_plus = size.startswith('+')
                relative_minus = size.startswith('-')
                if relative_plus or relative_minus:
                    size = size[1:].strip()
                try:
                    size = int(size)
                except ValueError:
                    LOGGER.warning('Invalid value for size: %s', size)
                else:
                    font_sizes = {
                        1: 'x-small',
                        2: 'small',
                        3: 'medium',
                        4: 'large',
                        5: 'x-large',
                        6: 'xx-large',
                        7: '48px',  # 1.5 * xx-large
                    }
                    if relative_plus:
                        size += 3
                    elif relative_minus:
                        size -= 3
                    size = max(1, min(7, size))
                    yield specificity, check_style_attribute(
                        parser, element, 'font-size:%s' % font_sizes[size])
        elif element.tag == 'table':
            # TODO: we should support cellpadding
            if element.get('cellspacing'):
                yield specificity, check_style_attribute(
                    parser, element,
                    'border-spacing:%spx' % element.get('cellspacing'))
            if element.get('cellpadding'):
                cellpadding = element.get('cellpadding')
                if cellpadding.isdigit():
                    cellpadding += 'px'
                # TODO: don't match subtables cells
                for subelement in element.iter():
                    if subelement.tag in ('td', 'th'):
                        yield specificity, check_style_attribute(
                            parser, subelement,
                            'padding-left:%s;padding-right:%s;'
                            'padding-top:%s;padding-bottom:%s;' % (
                                4 * (cellpadding,)))
            if element.get('hspace'):
                hspace = element.get('hspace')
                if hspace.isdigit():
                    hspace += 'px'
                yield specificity, check_style_attribute(
                    parser, element,
                    'margin-left:%s;margin-right:%s' % (hspace, hspace))
            if element.get('vspace'):
                vspace = element.get('vspace')
                if vspace.isdigit():
                    vspace += 'px'
                yield specificity, check_style_attribute(
                    parser, element,
                    'margin-top:%s;margin-bottom:%s' % (vspace, vspace))
            if element.get('width'):
                style_attribute = 'width:%s' % element.get('width')
                if element.get('width').isdigit():
                    style_attribute += 'px'
                yield specificity, check_style_attribute(
                    parser, element, style_attribute)
            if element.get('height'):
                style_attribute = 'height:%s' % element.get('height')
                if element.get('height').isdigit():
                    style_attribute += 'px'
                yield specificity, check_style_attribute(
                    parser, element, style_attribute)
            if element.get('background'):
                style_attribute = 'background-image:url(%s)' % (
                    element.get('background'))
                yield specificity, check_style_attribute(
                    parser, element, style_attribute)
            if element.get('bgcolor'):
                style_attribute = 'background-color:%s' % (
                    element.get('bgcolor'))
                yield specificity, check_style_attribute(
                    parser, element, style_attribute)
            if element.get('bordercolor'):
                style_attribute = 'border-color:%s' % (
                    element.get('bordercolor'))
                yield specificity, check_style_attribute(
                    parser, element, style_attribute)
            if element.get('border'):
                style_attribute = 'border-width:%spx' % (
                    element.get('border'))
                yield specificity, check_style_attribute(
                    parser, element, style_attribute)
        elif element.tag in ('tr', 'td', 'th', 'thead', 'tbody', 'tfoot'):
            align = element.get('align', '').lower()
            if align in ('left', 'right', 'justify'):
                # TODO: we should align descendants too
                yield specificity, check_style_attribute(
                    parser, element, 'text-align:%s' % align)
            if element.get('background'):
                style_attribute = 'background-image:url(%s)' % (
                    element.get('background'))
                yield specificity, check_style_attribute(
                    parser, element, style_attribute)
            if element.get('bgcolor'):
                style_attribute = 'background-color:%s' % (
                    element.get('bgcolor'))
                yield specificity, check_style_attribute(
                    parser, element, style_attribute)
            if element.tag in ('tr', 'td', 'th'):
                if element.get('height'):
                    style_attribute = 'height:%s' % element.get('height')
                    if element.get('height').isdigit():
                        style_attribute += 'px'
                    yield specificity, check_style_attribute(
                        parser, element, style_attribute)
                if element.tag in ('td', 'th'):
                    if element.get('width'):
                        style_attribute = 'width:%s' % element.get('width')
                        if element.get('width').isdigit():
                            style_attribute += 'px'
                        yield specificity, check_style_attribute(
                            parser, element, style_attribute)
        elif element.tag == 'caption':
            align = element.get('align', '').lower()
            # TODO: we should align descendants too
            if align in ('left', 'right', 'justify'):
                yield specificity, check_style_attribute(
                    parser, element, 'text-align:%s' % align)
        elif element.tag == 'col':
            if element.get('width'):
                style_attribute = 'width:%s' % element.get('width')
                if element.get('width').isdigit():
                    style_attribute += 'px'
                yield specificity, check_style_attribute(
                    parser, element, style_attribute)
        elif element.tag == 'hr':
            size = 0
            if element.get('size'):
                try:
                    size = int(element.get('size'))
                except ValueError:
                    LOGGER.warning('Invalid value for size: %s', size)
            if (element.get('color'), element.get('noshade')) != (None, None):
                if size >= 1:
                    yield specificity, check_style_attribute(
                        parser, element, 'border-width:%spx' % (size / 2))
            elif size == 1:
                yield specificity, check_style_attribute(
                    parser, element, 'border-bottom-width:0')
            elif size > 1:
                yield specificity, check_style_attribute(
                    parser, element, 'height:%spx' % (size - 2))
            if element.get('width'):
                style_attribute = 'width:%s' % element.get('width')
                if element.get('width').isdigit():
                    style_attribute += 'px'
                yield specificity, check_style_attribute(
                    parser, element, style_attribute)
            if element.get('color'):
                yield specificity, check_style_attribute(
                    parser, element, 'color:%s' % element.get('color'))
        elif element.tag in (
                'iframe', 'applet', 'embed', 'img', 'input', 'object'):
            if (element.tag != 'input' or
                    element.get('type', '').lower() == 'image'):
                align = element.get('align', '').lower()
                if align in ('middle', 'center'):
                    # TODO: middle and center values are wrong
                    yield specificity, check_style_attribute(
                        parser, element, 'vertical-align:middle')
                if element.get('hspace'):
                    hspace = element.get('hspace')
                    if hspace.isdigit():
                        hspace += 'px'
                    yield specificity, check_style_attribute(
                        parser, element,
                        'margin-left:%s;margin-right:%s' % (hspace, hspace))
                if element.get('vspace'):
                    vspace = element.get('vspace')
                    if vspace.isdigit():
                        vspace += 'px'
                    yield specificity, check_style_attribute(
                        parser, element,
                        'margin-top:%s;margin-bottom:%s' % (vspace, vspace))
                # TODO: img seems to be excluded for width and height, but a
                # lot of W3C tests rely on this attribute being applied to img
                if element.get('width'):
                    style_attribute = 'width:%s' % element.get('width')
                    if element.get('width').isdigit():
                        style_attribute += 'px'
                    yield specificity, check_style_attribute(
                        parser, element, style_attribute)
                if element.get('height'):
                    style_attribute = 'height:%s' % element.get('height')
                    if element.get('height').isdigit():
                        style_attribute += 'px'
                    yield specificity, check_style_attribute(
                        parser, element, style_attribute)
                if element.tag in ('img', 'object', 'input'):
                    if element.get('border'):
                        yield specificity, check_style_attribute(
                            parser, element,
                            'border-width:%spx;border-style:solid' %
                            element.get('border'))
        elif element.tag == 'ol':
            # From https://www.w3.org/TR/css-lists-3/
            if element.get('start'):
                yield specificity, check_style_attribute(
                    parser, element,
                    'counter-reset:list-item %s;'
                    'counter-increment:list-item -1' % element.get('start'))
        elif element.tag == 'ul':
            # From https://www.w3.org/TR/css-lists-3/
            if element.get('value'):
                yield specificity, check_style_attribute(
                    parser, element,
                    'counter-reset:list-item %s;'
                    'counter-increment:none' % element.get('value'))


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
        computed = StyleDict(properties.INITIAL_VALUES)
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


def preprocess_stylesheet(device_media_type, base_url, stylesheet_rules,
                          url_fetcher, rules, fonts, font_config):
    """Do the work that can be done early on stylesheet, before they are
    in a document.

    """
    selector_to_xpath = cssselect.HTMLTranslator().selector_to_xpath
    for rule in stylesheet_rules:
        if rule.type == 'qualified-rule':
            declarations = list(preprocess_declarations(
                base_url, tinycss2.parse_declaration_list(rule.content)))
            if declarations:
                selector_string = tinycss2.serialize(rule.prelude)
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
                rules.append((rule, selector_list, declarations))

        elif rule.type == 'at-rule' and rule.at_keyword == 'import':
            tokens = remove_whitespace(rule.prelude)
            if tokens and tokens[0].type in ('url', 'string'):
                url = tokens[0].value
            else:
                continue
            media = parse_media_query(tokens[1:])
            if media is None:
                LOGGER.warning('Invalid media type "%s" '
                               'the whole @import rule was ignored at %s:%s.',
                               tinycss2.serialize(rule.prelude),
                               rule.source_line, rule.source_column)
            if not evaluate_media_query(media, device_media_type):
                continue
            url = url_join(
                base_url, url, allow_relative=False,
                context='@import at %s:%s',
                context_args=(rule.source_line, rule.source_column))
            if url is not None:
                try:
                    stylesheet = CSS(
                        url=url, url_fetcher=url_fetcher,
                        media_type=device_media_type, font_config=font_config)
                except URLFetchingError as exc:
                    LOGGER.warning('Failed to load stylesheet at %s : %s',
                                   url, exc)
                else:
                    for result in stylesheet.rules:
                        rules.append(result)

        elif rule.type == 'at-rule' and rule.at_keyword == 'media':
            media = parse_media_query(rule.prelude)
            if media is None:
                LOGGER.warning('Invalid media type "%s" '
                               'the whole @media rule was ignored at %s:%s.',
                               tinycss2.serialize(rule.prelude),
                               rule.source_line, rule.source_column)
                continue
            if not evaluate_media_query(media, device_media_type):
                continue
            content_rules = tinycss2.parse_rule_list(rule.content)
            preprocess_stylesheet(
                device_media_type, base_url, content_rules, url_fetcher, rules,
                fonts, font_config)

        elif rule.type == 'at-rule' and rule.at_keyword == 'page':
            tokens = remove_whitespace(rule.prelude)
            # TODO: support named pages (see CSS3 Paged Media)
            if not tokens:
                pseudo_class = None
                specificity = (0, 0)
            elif (len(tokens) == 2 and
                    tokens[0].type == 'literal' and
                    tokens[0].value == ':' and
                    tokens[1].type == 'ident'):
                pseudo_class = tokens[1].lower_value
                specificity = {
                    'first': (1, 0), 'blank': (1, 0),
                    'left': (0, 1), 'right': (0, 1),
                }.get(pseudo_class)
                if not specificity:
                    LOGGER.warning('Unknown @page pseudo-class "%s", '
                                   'the whole @page rule was ignored '
                                   'at %s:%s.',
                                   pseudo_class,
                                   rule.source_line, rule.source_column)
                    continue
            else:
                LOGGER.warning('Unsupported @page selector "%s", '
                               'the whole @page rule was ignored at %s:%s.',
                               tinycss2.serialize(rule.prelude),
                               rule.source_line, rule.source_column)
                continue
            content = tinycss2.parse_declaration_list(rule.content)
            declarations = list(preprocess_declarations(base_url, content))

            # Use a double lambda to have a closure that holds page_types
            match = (lambda page_types: lambda _document: page_types)(
                PAGE_PSEUDOCLASS_TARGETS[pseudo_class])

            if declarations:
                selector_list = [Selector(specificity, None, match)]
                rules.append((rule, selector_list, declarations))

            for margin_rule in content:
                if margin_rule.type != 'at-rule':
                    continue
                declarations = list(preprocess_declarations(
                    base_url,
                    tinycss2.parse_declaration_list(margin_rule.content)))
                if declarations:
                    selector_list = [Selector(
                        specificity, '@' + margin_rule.at_keyword, match)]
                    rules.append((margin_rule, selector_list, declarations))

        elif rule.type == 'at-rule' and rule.at_keyword == 'font-face':
            content = tinycss2.parse_declaration_list(rule.content)
            rule_descriptors = dict(preprocess_descriptors(
                base_url, content))
            for key in ('src', 'font_family'):
                if key not in rule_descriptors:
                    LOGGER.warning(
                        "Missing %s descriptor in '@font-face' rule at %s:%s",
                        key.replace('_', '-'),
                        rule.source_line, rule.source_column)
                    break
            else:
                if font_config is not None:
                    font_filename = font_config.add_font_face(
                        rule_descriptors, url_fetcher)
                    if font_filename:
                        fonts.append(font_filename)


def parse_media_query(tokens):
    tokens = remove_whitespace(tokens)
    if not tokens:
        return ['all']
    else:
        media = []
        for part in split_on_comma(tokens):
            types = [token.type for token in part]
            if types == ['ident']:
                media.append(part[0].lower_value)
            else:
                LOGGER.warning('Expected a media type, got ' +
                               tinycss2.serialize(part))
                return
        return media


def get_all_computed_styles(html, user_stylesheets=None,
                            presentational_hints=False, font_config=None):
    """Compute all the computed styles of all elements in ``html`` document.

    Do everything from finding author stylesheets to parsing and applying them.

    Return a ``style_for`` function that takes an element and an optional
    pseudo-element type, and return a StyleDict object.

    """
    element_tree = html.root_element
    device_media_type = html.media_type
    url_fetcher = html.url_fetcher
    ua_stylesheets = html._ua_stylesheets()
    author_stylesheets = list(find_stylesheets(
        element_tree, device_media_type, url_fetcher, font_config))
    if presentational_hints:
        ph_stylesheets = html._ph_stylesheets()
    else:
        ph_stylesheets = []

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

    for specificity, attributes in find_style_attributes(
            element_tree, presentational_hints):
        element, declarations, base_url = attributes
        for name, values, importance in preprocess_declarations(
                base_url, declarations):
            precedence = declaration_precedence('author', importance)
            weight = (precedence, specificity)
            add_declaration(cascaded_styles, name, values, weight, element)

    for sheets, origin, sheet_specificity in (
        # Order here is not important ('origin' is).
        # Use this order for a regression test
        (ua_stylesheets or [], 'user agent', None),
        (ph_stylesheets, 'author', (0, 0, 0, 0)),
        (author_stylesheets, 'author', None),
        (user_stylesheets or [], 'user', None),
    ):
        for sheet in sheets:
            for _rule, selector_list, declarations in sheet.rules:
                for selector in selector_list:
                    specificity = sheet_specificity or selector.specificity
                    pseudo_type = selector.pseudo_element
                    for element in selector.match(element_tree):
                        for name, values, importance in declarations:
                            precedence = declaration_precedence(
                                origin, importance)
                            weight = (precedence, specificity)
                            add_declaration(
                                cascaded_styles, name, values, weight,
                                element, pseudo_type)

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
