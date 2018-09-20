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

    :copyright: Copyright 2011-2018 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from collections import namedtuple

import cssselect2
import tinycss2

from . import computed_values
from . import properties
from .properties import INITIAL_NOT_COMPUTED
from .utils import remove_whitespace, split_on_comma
from .validation import preprocess_declarations
from .validation.descriptors import preprocess_descriptors
from ..logger import LOGGER
from ..urls import get_url_attribute, url_join, URLFetchingError
from .. import CSS


# Reject anything not in here:
PSEUDO_ELEMENTS = (None, 'before', 'after', 'first-line', 'first-letter')


PageType = namedtuple('PageType', ['side', 'blank', 'first', 'name'])


def get_child_text(element):
    """Return the text directly in the element, not descendants."""
    content = [element.text] if element.text else []
    for child in element:
        if child.tail:
            content.append(child.tail)
    return ''.join(content)


def find_stylesheets(wrapper_element, device_media_type, url_fetcher, base_url,
                     font_config, page_rules):
    """Yield the stylesheets in ``element_tree``.

    The output order is the same as the source order.

    """
    from ..html import element_has_link_type  # Work around circular imports.

    for wrapper in wrapper_element.query_all('style', 'link'):
        element = wrapper.etree_element
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
            # ElementTree should give us either unicode or ASCII-only
            # bytestrings, so we don't need `encoding` here.
            css = CSS(
                string=content, base_url=base_url,
                url_fetcher=url_fetcher, media_type=device_media_type,
                font_config=font_config, page_rules=page_rules)
            yield css
        elif element.tag == 'link' and element.get('href'):
            if not element_has_link_type(element, 'stylesheet') or \
                    element_has_link_type(element, 'alternate'):
                continue
            href = get_url_attribute(element, 'href', base_url)
            if href is not None:
                try:
                    yield CSS(
                        url=href, url_fetcher=url_fetcher,
                        _check_mime_type=True, media_type=device_media_type,
                        font_config=font_config, page_rules=page_rules)
                except URLFetchingError as exc:
                    LOGGER.error(
                        'Failed to load stylesheet at %s : %s', href, exc)


def find_style_attributes(tree, presentational_hints=False, base_url=None):
    """Yield ``specificity, (element, declaration, base_url)`` rules.

    Rules from "style" attribute are returned with specificity
    ``(1, 0, 0)``.

    If ``presentational_hints`` is ``True``, rules from presentational hints
    are returned with specificity ``(0, 0, 0)``.

    """
    def check_style_attribute(element, style_attribute):
        declarations = tinycss2.parse_declaration_list(style_attribute)
        return element, declarations, base_url

    for element in tree.iter():
        specificity = (1, 0, 0)
        style_attribute = element.get('style')
        if style_attribute:
            yield specificity, check_style_attribute(element, style_attribute)
        if not presentational_hints:
            continue
        specificity = (0, 0, 0)
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
                        element, style_attribute)
            if element.get('background'):
                style_attribute = 'background-image:url(%s)' % (
                    element.get('background'))
                yield specificity, check_style_attribute(
                    element, style_attribute)
            if element.get('bgcolor'):
                style_attribute = 'background-color:%s' % (
                    element.get('bgcolor'))
                yield specificity, check_style_attribute(
                    element, style_attribute)
            if element.get('text'):
                style_attribute = 'color:%s' % element.get('text')
                yield specificity, check_style_attribute(
                    element, style_attribute)
            # TODO: we should support link, vlink, alink
        elif element.tag == 'center':
            yield specificity, check_style_attribute(
                element, 'text-align:center')
        elif element.tag == 'div':
            align = element.get('align', '').lower()
            if align == 'middle':
                yield specificity, check_style_attribute(
                    element, 'text-align:center')
            elif align in ('center', 'left', 'right', 'justify'):
                yield specificity, check_style_attribute(
                    element, 'text-align:%s' % align)
        elif element.tag == 'font':
            if element.get('color'):
                yield specificity, check_style_attribute(
                    element, 'color:%s' % element.get('color'))
            if element.get('face'):
                yield specificity, check_style_attribute(
                    element, 'font-family:%s' % element.get('face'))
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
                        element, 'font-size:%s' % font_sizes[size])
        elif element.tag == 'table':
            # TODO: we should support cellpadding
            if element.get('cellspacing'):
                yield specificity, check_style_attribute(
                    element,
                    'border-spacing:%spx' % element.get('cellspacing'))
            if element.get('cellpadding'):
                cellpadding = element.get('cellpadding')
                if cellpadding.isdigit():
                    cellpadding += 'px'
                # TODO: don't match subtables cells
                for subelement in element.iter():
                    if subelement.tag in ('td', 'th'):
                        yield specificity, check_style_attribute(
                            subelement,
                            'padding-left:%s;padding-right:%s;'
                            'padding-top:%s;padding-bottom:%s;' % (
                                4 * (cellpadding,)))
            if element.get('hspace'):
                hspace = element.get('hspace')
                if hspace.isdigit():
                    hspace += 'px'
                yield specificity, check_style_attribute(
                    element,
                    'margin-left:%s;margin-right:%s' % (hspace, hspace))
            if element.get('vspace'):
                vspace = element.get('vspace')
                if vspace.isdigit():
                    vspace += 'px'
                yield specificity, check_style_attribute(
                    element,
                    'margin-top:%s;margin-bottom:%s' % (vspace, vspace))
            if element.get('width'):
                style_attribute = 'width:%s' % element.get('width')
                if element.get('width').isdigit():
                    style_attribute += 'px'
                yield specificity, check_style_attribute(
                    element, style_attribute)
            if element.get('height'):
                style_attribute = 'height:%s' % element.get('height')
                if element.get('height').isdigit():
                    style_attribute += 'px'
                yield specificity, check_style_attribute(
                    element, style_attribute)
            if element.get('background'):
                style_attribute = 'background-image:url(%s)' % (
                    element.get('background'))
                yield specificity, check_style_attribute(
                    element, style_attribute)
            if element.get('bgcolor'):
                style_attribute = 'background-color:%s' % (
                    element.get('bgcolor'))
                yield specificity, check_style_attribute(
                    element, style_attribute)
            if element.get('bordercolor'):
                style_attribute = 'border-color:%s' % (
                    element.get('bordercolor'))
                yield specificity, check_style_attribute(
                    element, style_attribute)
            if element.get('border'):
                style_attribute = 'border-width:%spx' % (
                    element.get('border'))
                yield specificity, check_style_attribute(
                    element, style_attribute)
        elif element.tag in ('tr', 'td', 'th', 'thead', 'tbody', 'tfoot'):
            align = element.get('align', '').lower()
            # TODO: we should align descendants too
            if align == 'middle':
                yield specificity, check_style_attribute(
                    element, 'text-align:center')
            elif align in ('center', 'left', 'right', 'justify'):
                yield specificity, check_style_attribute(
                    element, 'text-align:%s' % align)
            if element.get('background'):
                style_attribute = 'background-image:url(%s)' % (
                    element.get('background'))
                yield specificity, check_style_attribute(
                    element, style_attribute)
            if element.get('bgcolor'):
                style_attribute = 'background-color:%s' % (
                    element.get('bgcolor'))
                yield specificity, check_style_attribute(
                    element, style_attribute)
            if element.tag in ('tr', 'td', 'th'):
                if element.get('height'):
                    style_attribute = 'height:%s' % element.get('height')
                    if element.get('height').isdigit():
                        style_attribute += 'px'
                    yield specificity, check_style_attribute(
                        element, style_attribute)
                if element.tag in ('td', 'th'):
                    if element.get('width'):
                        style_attribute = 'width:%s' % element.get('width')
                        if element.get('width').isdigit():
                            style_attribute += 'px'
                        yield specificity, check_style_attribute(
                            element, style_attribute)
        elif element.tag == 'caption':
            align = element.get('align', '').lower()
            # TODO: we should align descendants too
            if align == 'middle':
                yield specificity, check_style_attribute(
                    element, 'text-align:center')
            elif align in ('center', 'left', 'right', 'justify'):
                yield specificity, check_style_attribute(
                    element, 'text-align:%s' % align)
        elif element.tag == 'col':
            if element.get('width'):
                style_attribute = 'width:%s' % element.get('width')
                if element.get('width').isdigit():
                    style_attribute += 'px'
                yield specificity, check_style_attribute(
                    element, style_attribute)
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
                        element, 'border-width:%spx' % (size / 2))
            elif size == 1:
                yield specificity, check_style_attribute(
                    element, 'border-bottom-width:0')
            elif size > 1:
                yield specificity, check_style_attribute(
                    element, 'height:%spx' % (size - 2))
            if element.get('width'):
                style_attribute = 'width:%s' % element.get('width')
                if element.get('width').isdigit():
                    style_attribute += 'px'
                yield specificity, check_style_attribute(
                    element, style_attribute)
            if element.get('color'):
                yield specificity, check_style_attribute(
                    element, 'color:%s' % element.get('color'))
        elif element.tag in (
                'iframe', 'applet', 'embed', 'img', 'input', 'object'):
            if (element.tag != 'input' or
                    element.get('type', '').lower() == 'image'):
                align = element.get('align', '').lower()
                if align in ('middle', 'center'):
                    # TODO: middle and center values are wrong
                    yield specificity, check_style_attribute(
                        element, 'vertical-align:middle')
                if element.get('hspace'):
                    hspace = element.get('hspace')
                    if hspace.isdigit():
                        hspace += 'px'
                    yield specificity, check_style_attribute(
                        element,
                        'margin-left:%s;margin-right:%s' % (hspace, hspace))
                if element.get('vspace'):
                    vspace = element.get('vspace')
                    if vspace.isdigit():
                        vspace += 'px'
                    yield specificity, check_style_attribute(
                        element,
                        'margin-top:%s;margin-bottom:%s' % (vspace, vspace))
                # TODO: img seems to be excluded for width and height, but a
                # lot of W3C tests rely on this attribute being applied to img
                if element.get('width'):
                    style_attribute = 'width:%s' % element.get('width')
                    if element.get('width').isdigit():
                        style_attribute += 'px'
                    yield specificity, check_style_attribute(
                        element, style_attribute)
                if element.get('height'):
                    style_attribute = 'height:%s' % element.get('height')
                    if element.get('height').isdigit():
                        style_attribute += 'px'
                    yield specificity, check_style_attribute(
                        element, style_attribute)
                if element.tag in ('img', 'object', 'input'):
                    if element.get('border'):
                        yield specificity, check_style_attribute(
                            element,
                            'border-width:%spx;border-style:solid' %
                            element.get('border'))
        elif element.tag == 'ol':
            # From https://www.w3.org/TR/css-lists-3/
            if element.get('start'):
                yield specificity, check_style_attribute(
                    element,
                    'counter-reset:list-item %s;'
                    'counter-increment:list-item -1' % element.get('start'))
        elif element.tag == 'ul':
            # From https://www.w3.org/TR/css-lists-3/
            if element.get('value'):
                yield specificity, check_style_attribute(
                    element,
                    'counter-reset:list-item %s;'
                    'counter-increment:none' % element.get('value'))


def matching_page_types(page_type, names=()):
    sides = ['left', 'right', None] if page_type.side is None else [
        page_type.side]
    blanks = (True, False) if page_type.blank is False else (True,)
    firsts = (True, False) if page_type.first is False else (True,)
    names = (
        tuple(names) + (None,) if page_type.name is None
        else (page_type.name,))
    for side in sides:
        for blank in blanks:
            for first in firsts:
                for name in names:
                    yield PageType(
                        side=side, blank=blank, first=first, name=name)


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
                        root=None, pseudo_type=None, base_url=None,
                        target_collector=None):
    """Set the computed values of styles to ``element``.

    Take the properties left by ``apply_style_rule`` on an element or
    pseudo-element and assign computed values with respect to the cascade,
    declaration priority (ie. ``!important``) and selector specificity.

    """
    if element == root and pseudo_type is None:
        assert parent is None
        parent_style = None
        root_style = {
            # When specified on the font-size property of the root element, the
            # rem units refer to the property’s initial value.
            'font_size': properties.INITIAL_VALUES['font_size'],
        }
    else:
        assert parent is not None
        parent_style = computed_styles[parent, None]
        root_style = computed_styles[root, None]

    cascaded = cascaded_styles.get((element, pseudo_type), {})
    computed_styles[element, pseudo_type] = computed_from_cascaded(
        element, cascaded, parent_style, pseudo_type, root_style, base_url,
        target_collector)


def computed_from_cascaded(element, cascaded, parent_style, pseudo_type=None,
                           root_style=None, base_url=None,
                           target_collector=None):
    """Get a dict of computed style mixed from parent and cascaded styles."""
    if not cascaded and parent_style is not None:
        # Fast path for anonymous boxes:
        # no cascaded style, only implicitly initial or inherited values.
        computed = dict(properties.INITIAL_VALUES)
        for name in properties.INHERITED:
            computed[name] = parent_style[name]
        # page is not inherited but taken from the ancestor if 'auto'
        computed['page'] = parent_style['page']
        # border-*-style is none, so border-width computes to zero.
        # Other than that, properties that would need computing are
        # border-*-color, but they do not apply.
        for side in ('top', 'bottom', 'left', 'right'):
            computed['border_%s_width' % side] = 0
        computed['outline_width'] = 0
        return computed

    # Handle inheritance and initial values
    specified = {}
    computed = {}
    for name, initial in properties.INITIAL_VALUES.items():
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
            if name not in INITIAL_NOT_COMPUTED:
                # The value is the same as when computed
                computed[name] = value
        elif keyword == 'inherit':
            value = parent_style[name]
            # Values in parent_style are already computed.
            computed[name] = value

        specified[name] = value

    if specified['page'] == 'auto':
        # The page property does not inherit. However, if the page value on
        # an element is auto, then its used value is the value specified on
        # its nearest ancestor with a non-auto value. When specified on the
        # root element, the used value for auto is the empty string.
        computed['page'] = specified['page'] = (
            '' if parent_style is None else parent_style['page'])

    return computed_values.compute(
        element, pseudo_type, specified, computed, parent_style, root_style,
        base_url, target_collector)


def parse_page_selectors(rule):
    """Parse a page selector rule.

    Return a list of page data if the rule is correctly parsed. Page data are a
    dict containing:

    - 'side' ('left', 'right' or None),
    - 'blank' (True or False),
    - 'first' (True or False),
    - 'name' (page name string or None), and
    - 'spacificity' (list of numbers).

    Return ``None` if something went wrong while parsing the rule.

    """
    # See https://drafts.csswg.org/css-page-3/#syntax-page-selector

    tokens = list(remove_whitespace(rule.prelude))
    page_data = []

    # TODO: Specificity is probably wrong, should clean and test that.
    if not tokens:
        page_data.append({
            'side': None, 'blank': False, 'first': False, 'name': None,
            'specificity': [0, 0, 0]})
        return page_data

    while tokens:
        types = {
            'side': None, 'blank': False, 'first': False, 'name': None,
            'specificity': [0, 0, 0]}

        if tokens[0].type == 'ident':
            token = tokens.pop(0)
            types['name'] = token.value
            types['specificity'][0] = 1

        if len(tokens) == 1:
            return None
        elif not tokens:
            page_data.append(types)
            return page_data

        while tokens:
            literal = tokens.pop(0)
            if literal.type != 'literal':
                return None

            if literal.value == ':':
                if not tokens or tokens[0].type != 'ident':
                    return None
                ident = tokens.pop(0)
                pseudo_class = ident.lower_value
                if pseudo_class in ('left', 'right'):
                    if types['side']:
                        return None
                    types['side'] = pseudo_class
                    types['specificity'][2] += 1
                elif pseudo_class in ('blank', 'first'):
                    if types[pseudo_class]:
                        return None
                    types[pseudo_class] = True
                    types['specificity'][1] += 1
                else:
                    return None
            elif literal.value == ',':
                if tokens and any(types['specificity']):
                    break
                else:
                    return None

        page_data.append(types)

    return page_data


def preprocess_stylesheet(device_media_type, base_url, stylesheet_rules,
                          url_fetcher, matcher, page_rules, fonts,
                          font_config, ignore_imports=False):
    """Do the work that can be done early on stylesheet, before they are
    in a document.

    """
    for rule in stylesheet_rules:
        if getattr(rule, 'content', None) is None and (
                rule.type != 'at-rule' or rule.lower_at_keyword != 'import'):
            continue

        if rule.type == 'qualified-rule':
            declarations = list(preprocess_declarations(
                base_url, tinycss2.parse_declaration_list(rule.content)))
            if declarations:
                try:
                    selectors = cssselect2.compile_selector_list(rule.prelude)
                    for selector in selectors:
                        matcher.add_selector(selector, declarations)
                        if selector.pseudo_element not in PSEUDO_ELEMENTS:
                            raise cssselect2.SelectorError(
                                'Unknown pseudo-element: %s'
                                % selector.pseudo_element)
                    ignore_imports = True
                except cssselect2.SelectorError as exc:
                    LOGGER.warning("Invalid or unsupported selector '%s', %s",
                                   tinycss2.serialize(rule.prelude), exc)
                    continue
            else:
                ignore_imports = True

        elif rule.type == 'at-rule' and rule.lower_at_keyword == 'import':
            if ignore_imports:
                LOGGER.warning('@import rule "%s" not at the beginning of the '
                               'the whole rule was ignored at %s:%s.',
                               tinycss2.serialize(rule.prelude),
                               rule.source_line, rule.source_column)
                continue

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
                continue
            if not evaluate_media_query(media, device_media_type):
                continue
            url = url_join(
                base_url, url, allow_relative=False,
                context='@import at %s:%s',
                context_args=(rule.source_line, rule.source_column))
            if url is not None:
                try:
                    CSS(
                        url=url, url_fetcher=url_fetcher,
                        media_type=device_media_type, font_config=font_config,
                        matcher=matcher, page_rules=page_rules)
                except URLFetchingError as exc:
                    LOGGER.error(
                        'Failed to load stylesheet at %s : %s', url, exc)

        elif rule.type == 'at-rule' and rule.lower_at_keyword == 'media':
            media = parse_media_query(rule.prelude)
            if media is None:
                LOGGER.warning('Invalid media type "%s" '
                               'the whole @media rule was ignored at %s:%s.',
                               tinycss2.serialize(rule.prelude),
                               rule.source_line, rule.source_column)
                continue
            ignore_imports = True
            if not evaluate_media_query(media, device_media_type):
                continue
            content_rules = tinycss2.parse_rule_list(rule.content)
            preprocess_stylesheet(
                device_media_type, base_url, content_rules, url_fetcher,
                matcher, page_rules, fonts, font_config, ignore_imports=True)

        elif rule.type == 'at-rule' and rule.lower_at_keyword == 'page':
            data = parse_page_selectors(rule)

            if data is None:
                LOGGER.warning(
                    'Unsupported @page selector "%s", '
                    'the whole @page rule was ignored at %s:%s.',
                    tinycss2.serialize(rule.prelude),
                    rule.source_line, rule.source_column)
                continue

            ignore_imports = True
            for page_type in data:
                specificity = page_type.pop('specificity')
                page_type = PageType(**page_type)
                # Use a double lambda to have a closure that holds page_types
                match = (lambda page_type: lambda page_names: list(
                    matching_page_types(page_type, names=page_names)))(
                        page_type)
                content = tinycss2.parse_declaration_list(rule.content)
                declarations = list(preprocess_declarations(base_url, content))

                if declarations:
                    selector_list = [(specificity, None, match)]
                    page_rules.append((rule, selector_list, declarations))

                for margin_rule in content:
                    if margin_rule.type != 'at-rule' or (
                            margin_rule.content is None):
                        continue
                    declarations = list(preprocess_declarations(
                        base_url,
                        tinycss2.parse_declaration_list(margin_rule.content)))
                    if declarations:
                        selector_list = [(
                            specificity, '@' + margin_rule.lower_at_keyword,
                            match)]
                        page_rules.append(
                            (margin_rule, selector_list, declarations))

        elif rule.type == 'at-rule' and rule.lower_at_keyword == 'font-face':
            ignore_imports = True
            content = tinycss2.parse_declaration_list(rule.content)
            rule_descriptors = dict(preprocess_descriptors(base_url, content))
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
                LOGGER.warning(
                    'Expected a media type, got %s', tinycss2.serialize(part))
                return
        return media


def get_all_computed_styles(html, user_stylesheets=None,
                            presentational_hints=False, font_config=None,
                            page_rules=None, target_collector=None):
    """Compute all the computed styles of all elements in ``html`` document.

    Do everything from finding author stylesheets to parsing and applying them.

    Return a ``style_for`` function that takes an element and an optional
    pseudo-element type, and return a style dict object.

    """
    # List stylesheets. Order here is not important ('origin' is).
    sheets = []
    for sheet in (html._ua_stylesheets() or []):
        sheets.append((sheet, 'user agent', None))
    if presentational_hints:
        for sheet in (html._ph_stylesheets() or []):
            sheets.append((sheet, 'author', (0, 0, 0)))
    for sheet in find_stylesheets(
            html.wrapper_element, html.media_type, html.url_fetcher,
            html.base_url, font_config, page_rules):
        sheets.append((sheet, 'author', None))
    for sheet in (user_stylesheets or []):
        sheets.append((sheet, 'user', None))

    # keys: (element, pseudo_element_type)
    #    element: an ElementTree Element or the '@page' string for @page styles
    #    pseudo_element_type: a string such as 'first' (for @page) or 'after',
    #        or None for normal elements
    # values: dicts of
    #     keys: property name as a string
    #     values: (values, weight)
    #         values: a PropertyValue-like object
    #         weight: values with a greater weight take precedence, see
    #             http://www.w3.org/TR/CSS21/cascade.html#cascading-order
    cascaded_styles = {}

    LOGGER.info('Step 3 - Applying CSS')
    for specificity, attributes in find_style_attributes(
            html.etree_element, presentational_hints, html.base_url):
        element, declarations, base_url = attributes
        for name, values, importance in preprocess_declarations(
                base_url, declarations):
            precedence = declaration_precedence('author', importance)
            weight = (precedence, specificity)
            add_declaration(cascaded_styles, name, values, weight, element)

    # keys: (element, pseudo_element_type), like cascaded_styles
    # values: style dict objects:
    #     keys: property name as a string
    #     values: a PropertyValue-like object
    computed_styles = {}

    # First, add declarations and set computed styles for "real" elements *in
    # tree order*. Tree order is important so that parents have computed
    # styles before their children, for inheritance.

    # Iterate on all elements, even if there is no cascaded style for them.
    for element in html.wrapper_element.iter_subtree():
        for sheet, origin, sheet_specificity in sheets:
            # Add declarations for matched elements
            for selector in sheet.matcher.match(element):
                specificity, order, pseudo_type, declarations = selector
                specificity = sheet_specificity or specificity
                for name, values, importance in declarations:
                    precedence = declaration_precedence(origin, importance)
                    weight = (precedence, specificity)
                    add_declaration(
                        cascaded_styles, name, values, weight,
                        element.etree_element, pseudo_type)
        set_computed_styles(
            cascaded_styles, computed_styles, element.etree_element,
            root=html.etree_element,
            parent=(element.parent.etree_element if element.parent else None),
            base_url=html.base_url, target_collector=target_collector)

    page_names = set(style['page'] for style in computed_styles.values())

    for sheet, origin, sheet_specificity in sheets:
        # Add declarations for page elements
        for _rule, selector_list, declarations in sheet.page_rules:
            for selector in selector_list:
                specificity, pseudo_type, match = selector
                specificity = sheet_specificity or specificity
                for page_type in match(page_names):
                    for name, values, importance in declarations:
                        precedence = declaration_precedence(origin, importance)
                        weight = (precedence, specificity)
                        add_declaration(
                            cascaded_styles, name, values, weight, page_type,
                            pseudo_type)

    # Then computed styles for pseudo elements, in any order.
    # Pseudo-elements inherit from their associated element so they come
    # last. Do them in a second pass as there is no easy way to iterate
    # on the pseudo-elements for a given element with the current structure
    # of cascaded_styles. (Keys are (element, pseudo_type) tuples.)

    # Only iterate on pseudo-elements that have cascaded styles. (Others
    # might as well not exist.)
    for element, pseudo_type in cascaded_styles:
        if pseudo_type and not isinstance(element, PageType):
            set_computed_styles(
                cascaded_styles, computed_styles, element,
                pseudo_type=pseudo_type,
                # The pseudo-element inherits from the element.
                root=html.etree_element, parent=element,
                base_url=html.base_url, target_collector=target_collector)

    # This is mostly useful to make pseudo_type optional.
    def style_for(element, pseudo_type=None, __get=computed_styles.get):
        """Convenience function to get the computed styles for an element."""
        style = __get((element, pseudo_type))

        if style:
            if 'table' in style['display']:
                if (style['display'] in ('table', 'inline-table') and
                        style['border_collapse'] == 'collapse'):
                    # Padding do not apply
                    for side in ['top', 'bottom', 'left', 'right']:
                        style['padding_' + side] = computed_values.ZERO_PIXELS
                if (style['display'].startswith('table-') and
                        style['display'] != 'table-caption'):
                    # Margins do not apply
                    for side in ['top', 'bottom', 'left', 'right']:
                        style['margin_' + side] = computed_values.ZERO_PIXELS

        return style

    return style_for, cascaded_styles, computed_styles
