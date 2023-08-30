"""Find and apply CSS.

This module takes care of steps 3 and 4 of “CSS 2.1 processing model”: Retrieve
stylesheets associated with a document and annotate every element with a value
for every CSS property.

https://www.w3.org/TR/CSS21/intro.html#processing-model

This module does this in more than two steps. The
:func:`get_all_computed_styles` function does everything, but it is itsef based
on other functions in this module.

"""

from collections import namedtuple
from logging import DEBUG, WARNING

import cssselect2
import tinycss2
import tinycss2.nth

from .. import CSS
from ..logger import LOGGER, PROGRESS_LOGGER
from ..urls import URLFetchingError, get_url_attribute, url_join
from . import computed_values, counters, media_queries
from .properties import INHERITED, INITIAL_NOT_COMPUTED, INITIAL_VALUES
from .utils import get_url, remove_whitespace
from .validation import preprocess_declarations
from .validation.descriptors import preprocess_descriptors

# Reject anything not in here:
PSEUDO_ELEMENTS = (
    None, 'before', 'after', 'marker', 'first-line', 'first-letter',
    'footnote-call', 'footnote-marker')

PageType = namedtuple('PageType', ['side', 'blank', 'first', 'index', 'name'])


class StyleFor:
    """Convenience function to get the computed styles for an element."""
    def __init__(self, html, sheets, presentational_hints, target_collector):
        # keys: (element, pseudo_element_type)
        #    element: an ElementTree Element or the '@page' string
        #    pseudo_element_type: a string such as 'first' (for @page) or
        #        'after', or None for normal elements
        # values: dicts of
        #     keys: property name as a string
        #     values: (values, weight)
        #         values: a PropertyValue-like object
        #         weight: values with a greater weight take precedence, see
        #             https://www.w3.org/TR/CSS21/cascade.html#cascading-order
        self._cascaded_styles = cascaded_styles = {}
        self._style_rel = StyleRelationship()
        self._sheets = sheets

        PROGRESS_LOGGER.info('Step 3 - Applying CSS')
        for specificity, attributes in find_style_attributes(
                html.etree_element, presentational_hints, html.base_url):
            element, declarations, base_url = attributes
            element_styles = cascaded_styles.get(element)
            if element_styles is None:
                cascaded_styles[element] = {}
                element_styles = cascaded_styles[element]
            style = element_styles.setdefault((element, None), {})
            for name, values, importance in preprocess_declarations(
                    base_url, declarations):
                precedence = declaration_precedence('author', importance)
                weight = (precedence, specificity)
                old_weight = style.get(name, (None, None))[1]
                if old_weight is None or old_weight <= weight:
                    style[name] = values, weight
            self._set_cascaded_style(element, None, style)

        # First, add declarations and set computed styles for "real" elements
        # *in tree order*. Tree order is important so that parents have
        # computed styles before their children, for inheritance.

        # Iterate on all elements, even if there is no cascaded style for them.
        for element in html.wrapper_element.iter_subtree():
            element_styles = cascaded_styles.get(element.etree_element)
            if element_styles is None:
                cascaded_styles[element.etree_element] = {}
                element_styles = cascaded_styles[element.etree_element]
            for sheet, origin, sheet_specificity in sheets:
                # Add declarations for matched elements
                for selector in sheet.matcher.match(element):
                    specificity, order, pseudo_type, declarations = selector
                    specificity = sheet_specificity or specificity
                    style = element_styles.setdefault(
                        (element.etree_element, pseudo_type), {})
                    for name, values, importance in declarations:
                        precedence = declaration_precedence(origin, importance)
                        weight = (precedence, specificity)
                        old_weight = style.get(name, (None, None))[1]
                        if old_weight is None or old_weight <= weight:
                            style_copy = style.copy()
                            style_copy[name] = values, weight
                            style = style_copy
                    self._set_cascaded_style(
                        element.etree_element, pseudo_type, style)
            parent = element.parent.etree_element if element.parent else None
            self.set_computed_styles(
                element.etree_element, root=html.etree_element, parent=parent,
                base_url=html.base_url, target_collector=target_collector)

        # Then computed styles for pseudo elements, in any order.
        # Pseudo-elements inherit from their associated element so they come
        # last. Do them in a second pass as there is no easy way to iterate
        # on the pseudo-elements for a given element with the current structure
        # of cascaded_styles. (Keys are (element, pseudo_type) tuples.)

        # Only iterate on pseudo-elements that have cascaded styles. (Others
        # might as well not exist.)
        for element_styles in cascaded_styles.values():
            for element, pseudo_type in element_styles:
                if pseudo_type and not isinstance(element, PageType):
                    self.set_computed_styles(
                        element, pseudo_type=pseudo_type,
                        # The pseudo-element inherits from the element.
                        root=html.etree_element, parent=element,
                        base_url=html.base_url,
                        target_collector=target_collector)

        # Clear the cascaded styles, we don't need them anymore. Keep the
        # dictionary, it is used later for page margins.
        self._cascaded_styles.clear()

    def __call__(self, element, pseudo_type=None):
        computed_style = self.get_computed_styles().get((element, pseudo_type))
        if computed_style:
            return computed_style["style"]
        else:
            return None

    def _set_cascaded_style(self, element, pseudo_type=None, style={}):
        """Set the cascade style"""
        cascaded_styles = self.get_cascaded_styles()
        element_styles = cascaded_styles.get(element)
        if element_styles is None:
            cascaded_styles[element] = {}
            element_styles = cascaded_styles[element]
        style_indexes = self._get_cascaded_style_indexes()
        key_str = str(sorted(style.keys())).encode('utf8')
        style_index = style_indexes.setdefault(key_str, {})
        if style_index:
            for i, values in sorted(style_index.items(), reverse=True):
                if style == values:
                    element_styles[(element, pseudo_type)] = style_index[i]
                    break
            else:
                index = max(style_index) + 1
                style_index[index] = style.copy()
                element_styles[(element, pseudo_type)] = style_index[index]
        else:
            style_index[0] = style.copy()
            element_styles[(element, pseudo_type)] = style_index[0]

    def set_computed_styles(self, element, parent, root=None, pseudo_type=None,
                            base_url=None, target_collector=None):
        """Set the computed values of styles to ``element``.

        Take the properties left by ``apply_style_rule`` on an element or
        pseudo-element and assign computed values with respect to the cascade,
        declaration priority (ie. ``!important``) and selector specificity.

        """
        cascaded_styles = self.get_cascaded_styles()
        element_styles = cascaded_styles.get(element)
        if element_styles is None:
            cascaded_styles[element] = {}
            element_styles = cascaded_styles[element]
        computed_styles = self.get_computed_styles()
        if element == root and pseudo_type is None:
            assert parent is None
            parent_style = None
            root_style = {
                # When specified on the font-size property of the root element,
                # the rem units refer to the property’s initial value.
                'font_size': INITIAL_VALUES['font_size'],
            }
        else:
            assert parent is not None
            parent_style = computed_styles[(parent, None)]["style"]
            root_style = computed_styles[(root, None)]["style"]

        cascaded = element_styles.get((element, pseudo_type), {})
        computed_style = computed_from_cascaded(
            element, cascaded, parent_style, pseudo_type, root_style, base_url,
            target_collector, self._style_rel)

        # The style of marker is deleted when display is different from
        # list-item.
        if pseudo_type is None:
            for pseudo in (None, 'before', 'after'):
                pseudo_style = element_styles.get((element, pseudo), {})
                if 'display' in pseudo_style:
                    if 'list-item' in pseudo_style['display'][0]:
                        break
            else:
                if (element, 'marker') in element_styles:
                    del element_styles[element, 'marker']

        if ('table' in computed_style['display'] and
                computed_style['border_collapse'] == 'collapse'):
            # Padding do not apply
            for side in ('top', 'bottom', 'left', 'right'):
                computed_style[f'padding_{side}'] = computed_values.ZERO_PIXELS
        if (len(computed_style['display']) == 1 and
                computed_style['display'][0].startswith('table-') and
                computed_style['display'][0] != 'table-caption'):
            # Margins do not apply
            for side in ('top', 'bottom', 'left', 'right'):
                computed_style[f'margin_{side}'] = computed_values.ZERO_PIXELS

    def add_page_declarations(self, page_type):
        cascaded_styles = self.get_cascaded_styles()
        element_styles = cascaded_styles.get(page_type)
        if element_styles is None:
            cascaded_styles[page_type] = {}
            element_styles = cascaded_styles[page_type]
        for sheet, origin, sheet_specificity in self._sheets:
            for _rule, selector_list, declarations in sheet.page_rules:
                for selector in selector_list:
                    specificity, pseudo_type, selector_page_type = selector
                    if self._page_type_match(selector_page_type, page_type):
                        specificity = sheet_specificity or specificity
                        style = element_styles.setdefault(
                            (page_type, pseudo_type), {})
                        for name, values, importance in declarations:
                            precedence = declaration_precedence(
                                origin, importance)
                            weight = (precedence, specificity)
                            old_weight = style.get(name, (None, None))[1]
                            if old_weight is None or old_weight <= weight:
                                style_copy = style.copy()
                                style_copy[name] = values, weight
                                style = style_copy
                        self._set_cascaded_style(
                            page_type, pseudo_type, style)

    def get_cascaded_styles(self):
        return self._cascaded_styles

    def _get_cascaded_style_indexes(self):
        return self._style_rel._cascaded_style_indexes

    def get_computed_styles(self):
        return self._style_rel.get_computed_styles()

    @staticmethod
    def _page_type_match(selector_page_type, page_type):
        if selector_page_type.side not in (None, page_type.side):
            return False
        if selector_page_type.blank not in (None, page_type.blank):
            return False
        if selector_page_type.first not in (None, page_type.first):
            return False
        if selector_page_type.name not in (None, page_type.name):
            return False
        if selector_page_type.index is not None:
            a, b, group = selector_page_type.index
            # TODO: handle group
            offset = page_type.index + 1 - b
            if a == 0:
                return offset == 0
            else:
                return offset / a >= 0 and not offset % a
        return True


def get_child_text(element):
    """Return the text directly in the element, not descendants."""
    content = [element.text] if element.text else []
    for child in element:
        if child.tail:
            content.append(child.tail)
    return ''.join(content)


def text_decoration(key, value, parent_value, cascaded):
    # The text-decoration-* properties are not inherited but propagated
    # using specific rules.
    # See https://drafts.csswg.org/css-text-decor-3/#line-decoration
    # TODO: these rules don’t follow the specification.
    if key in ('text_decoration_color', 'text_decoration_style'):
        if not cascaded:
            value = parent_value
    elif key == 'text_decoration_line':
        if parent_value != 'none':
            if value == 'none':
                value = parent_value
            else:
                value = value | parent_value
    return value


def find_stylesheets(wrapper_element, device_media_type, url_fetcher, base_url,
                     font_config, counter_style, page_rules):
    """Yield the stylesheets in ``element_tree``.

    The output order is the same as the source order.

    """
    from ..html import element_has_link_type

    for wrapper in wrapper_element.query_all('style', 'link'):
        element = wrapper.etree_element
        mime_type = element.get('type', 'text/css').split(';', 1)[0].strip()
        # Only keep 'type/subtype' from 'type/subtype ; param1; param2'.
        if mime_type != 'text/css':
            continue
        media_attr = element.get('media', '').strip() or 'all'
        media = [media_type.strip() for media_type in media_attr.split(',')]
        if not media_queries.evaluate_media_query(media, device_media_type):
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
                font_config=font_config, counter_style=counter_style,
                page_rules=page_rules)
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
                        font_config=font_config, counter_style=counter_style,
                        page_rules=page_rules)
                except URLFetchingError as exc:
                    LOGGER.error(
                        'Failed to load stylesheet at %s: %s', href, exc)


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
                for prop in (f'margin{part}', f'{position}margin'):
                    if element.get(prop):
                        style_attribute = (
                            f'margin-{position}:{element.get(prop)}px')
                        break
                if style_attribute:
                    yield specificity, check_style_attribute(
                        element, style_attribute)
            if element.get('background'):
                style_attribute = (
                    f'background-image:url({element.get("background")})')
                yield specificity, check_style_attribute(
                    element, style_attribute)
            if element.get('bgcolor'):
                style_attribute = f'background-color:{element.get("bgcolor")}'
                yield specificity, check_style_attribute(
                    element, style_attribute)
            if element.get('text'):
                style_attribute = f'color:{element.get("text")}'
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
                    element, f'text-align:{align}')
        elif element.tag == 'font':
            if element.get('color'):
                yield specificity, check_style_attribute(
                    element, f'color:{element.get("color")}')
            if element.get('face'):
                yield specificity, check_style_attribute(
                    element, f'font-family:{element.get("face")}')
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
                        element, f'font-size:{font_sizes[size]}')
        elif element.tag == 'table':
            if element.get('cellspacing'):
                yield specificity, check_style_attribute(
                    element, f'border-spacing:{element.get("cellspacing")}px')
            if element.get('cellpadding'):
                cellpadding = element.get('cellpadding')
                if cellpadding.isdigit():
                    cellpadding += 'px'
                # TODO: don't match subtables cells
                for subelement in element.iter():
                    if subelement.tag in ('td', 'th'):
                        yield specificity, check_style_attribute(
                            subelement,
                            f'padding-left:{cellpadding};'
                            f'padding-right:{cellpadding};'
                            f'padding-top:{cellpadding};'
                            f'padding-bottom:{cellpadding};')
            if element.get('hspace'):
                hspace = element.get('hspace')
                if hspace.isdigit():
                    hspace += 'px'
                yield specificity, check_style_attribute(
                    element, f'margin-left:{hspace};margin-right:{hspace}')
            if element.get('vspace'):
                vspace = element.get('vspace')
                if vspace.isdigit():
                    vspace += 'px'
                yield specificity, check_style_attribute(
                    element, f'margin-top:{vspace};margin-bottom:{vspace}')
            if element.get('width'):
                style_attribute = f'width:{element.get("width")}'
                if element.get('width').isdigit():
                    style_attribute += 'px'
                yield specificity, check_style_attribute(
                    element, style_attribute)
            if element.get('height'):
                style_attribute = f'height:{element.get("height")}'
                if element.get('height').isdigit():
                    style_attribute += 'px'
                yield specificity, check_style_attribute(
                    element, style_attribute)
            if element.get('background'):
                style_attribute = (
                    f'background-image:url({element.get("background")})')
                yield specificity, check_style_attribute(
                    element, style_attribute)
            if element.get('bgcolor'):
                style_attribute = f'background-color:{element.get("bgcolor")}'
                yield specificity, check_style_attribute(
                    element, style_attribute)
            if element.get('bordercolor'):
                style_attribute = f'border-color:{element.get("bordercolor")}'
                yield specificity, check_style_attribute(
                    element, style_attribute)
            if element.get('border'):
                style_attribute = f'border-width:{element.get("border")}px'
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
                    element, f'text-align:{align}')
            if element.get('background'):
                style_attribute = (
                    f'background-image:url({element.get("background")})')
                yield specificity, check_style_attribute(
                    element, style_attribute)
            if element.get('bgcolor'):
                style_attribute = f'background-color:{element.get("bgcolor")}'
                yield specificity, check_style_attribute(
                    element, style_attribute)
            if element.tag in ('tr', 'td', 'th'):
                if element.get('height'):
                    style_attribute = f'height:{element.get("height")}'
                    if element.get('height').isdigit():
                        style_attribute += 'px'
                    yield specificity, check_style_attribute(
                        element, style_attribute)
                if element.tag in ('td', 'th'):
                    if element.get('width'):
                        style_attribute = f'width:{element.get("width")}'
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
                    element, f'text-align:{align}')
        elif element.tag == 'col':
            if element.get('width'):
                style_attribute = f'width:{element.get("width")}'
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
                        element, f'border-width:{size / 2}px')
            elif size == 1:
                yield specificity, check_style_attribute(
                    element, 'border-bottom-width:0')
            elif size > 1:
                yield specificity, check_style_attribute(
                    element, f'height:{size - 2}px')
            if element.get('width'):
                style_attribute = f'width:{element.get("width")}'
                if element.get('width').isdigit():
                    style_attribute += 'px'
                yield specificity, check_style_attribute(
                    element, style_attribute)
            if element.get('color'):
                yield specificity, check_style_attribute(
                    element, f'color:{element.get("color")}')
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
                        element, f'margin-left:{hspace};margin-right:{hspace}')
                if element.get('vspace'):
                    vspace = element.get('vspace')
                    if vspace.isdigit():
                        vspace += 'px'
                    yield specificity, check_style_attribute(
                        element, f'margin-top:{vspace};margin-bottom:{vspace}')
                # TODO: img seems to be excluded for width and height, but a
                # lot of W3C tests rely on this attribute being applied to img
                if element.get('width'):
                    style_attribute = f'width:{element.get("width")}'
                    if element.get('width').isdigit():
                        style_attribute += 'px'
                    yield specificity, check_style_attribute(
                        element, style_attribute)
                if element.get('height'):
                    style_attribute = f'height:{element.get("height")}'
                    if element.get('height').isdigit():
                        style_attribute += 'px'
                    yield specificity, check_style_attribute(
                        element, style_attribute)
                if element.tag in ('img', 'object', 'input'):
                    if element.get('border'):
                        yield specificity, check_style_attribute(
                            element,
                            f'border-width:{element.get("border")}px;'
                            f'border-style:solid')
        elif element.tag == 'ol':
            # From https://www.w3.org/TR/css-lists-3/#ua-stylesheet
            if element.get('start'):
                yield specificity, check_style_attribute(
                    element,
                    f'counter-reset:list-item {element.get("start")};'
                    'counter-increment:list-item -1')
        elif element.tag == 'li':
            # From https://www.w3.org/TR/css-lists-3/#ua-stylesheet
            if element.get('value'):
                yield specificity, check_style_attribute(
                    element,
                    f'counter-reset:list-item {element.get("value")};'
                    'counter-increment:none')


def declaration_precedence(origin, importance):
    """Return the precedence for a declaration.

    Precedence values have no meaning unless compared to each other.

    Acceptable values for ``origin`` are the strings ``'author'``, ``'user'``
    and ``'user agent'``.

    """
    # See https://www.w3.org/TR/CSS21/cascade.html#cascading-order
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


class AnonymousStyle(dict):
    """Computed style used for anonymous boxes."""
    def __init__(self, parent_style):
        # border-*-style is none, so border-width computes to zero.
        # Other than that, properties that would need computing are
        # border-*-color, but they do not apply.
        self.update({
            'border_top_width': 0,
            'border_bottom_width': 0,
            'border_left_width': 0,
            'border_right_width': 0,
            'outline_width': 0,
        })
        self.parent_style = parent_style
        self.specified = self
        if parent_style:
            self.cache = parent_style.cache
        else:
            self.cache = {'ratio_ch': {}, 'ratio_ex': {}}

    def copy(self):
        copy = AnonymousStyle(self.parent_style)
        copy.update(self)
        return copy

    def __missing__(self, key):
        if key in INHERITED or key[:2] == '__':
            value = self[key] = self.parent_style[key]
        elif key == 'page':
            # page is not inherited but taken from the ancestor if 'auto'
            value = self[key] = self.parent_style[key]
        elif key[:16] == 'text_decoration_':
            value = self[key] = text_decoration(
                key, INITIAL_VALUES[key], self.parent_style[key],
                cascaded=False)
        else:
            value = self[key] = INITIAL_VALUES[key]
        return value


class ComputedStyle():
    """Computed style used for non-anonymous boxes."""
    def __init__(self, parent_style, cascaded, element, pseudo_type,
                 root_style, base_url, style_rel):
        self.specified = {}
        self.parent_style = parent_style
        self.cascaded = cascaded
        self.is_root_element = parent_style is None
        self.element = element
        self.pseudo_type = pseudo_type
        self.root_style = root_style
        self.base_url = base_url
        self.style_rel = style_rel
        if parent_style:
            self.cache = parent_style.cache
        else:
            self.cache = {'ratio_ch': {}, 'ratio_ex': {}}

        style_rel.set_computed_style(element, pseudo_type, self, {})

    def copy(self):
        copy = ComputedStyle(
            self.parent_style, self.cascaded, self.element, self.pseudo_type,
            self.root_style, self.base_url, self.style_rel)
        return copy

    def get_style_keys(self):
        return self.style_rel.get_computed_styles()[(
            self.element, self.pseudo_type)]["properties"]

    def get(self, key, default=None):
        computed_keys = self.get_style_keys()
        if key in computed_keys:
            return computed_keys[key]
        else:
            if default:
                computed_keys[key] = default
                return default
            else:
                return None

    def __getitem__(self, key):
        computed_keys = self.get_style_keys()
        if key in computed_keys:
            return computed_keys[key]
        else:
            return self.__missing__(key)

    def __setitem__(self, key, value):
        computed_keys = self.get_style_keys()
        computed_keys_copy = computed_keys.copy()
        computed_keys_copy[key] = value
        self.style_rel.set_computed_style_key(
            self.element, self.pseudo_type, computed_keys_copy)

    def __delitem__(self, key):
        computed_keys = self.get_style_keys()
        computed_keys_copy = computed_keys.copy()
        del computed_keys_copy[key]
        self.style_rel.set_computed_style_key(
            self.element, self.pseudo_type, computed_keys_copy)

    def __missing__(self, key):
        if key == 'float':
            # Set specified value for position, needed for computed value
            self['position']
        elif key == 'display':
            # Set specified value for float, needed for computed value
            self['float']

        if key in self.cascaded:
            value = keyword = self.cascaded[key][0]
        else:
            if key in INHERITED or key[:2] == '__':
                keyword = 'inherit'
            else:
                keyword = 'initial'

        if keyword == 'inherit' and self.parent_style is None:
            # On the root element, 'inherit' from initial values
            keyword = 'initial'

        if keyword == 'initial':
            value = None if key[:2] == '__' else INITIAL_VALUES[key]
            if key not in INITIAL_NOT_COMPUTED:
                # The value is the same as when computed
                self[key] = value
        elif keyword == 'inherit':
            # Values in parent_style are already computed.
            self[key] = value = self.parent_style[key]

        if key[:16] == 'text_decoration_' and self.parent_style:
            value = text_decoration(
                key, value, self.parent_style[key], key in self.cascaded)
            if key in self.get_style_keys():
                del self[key]
        elif key == 'page' and value == 'auto':
            # The page property does not inherit. However, if the page
            # value on an element is auto, then its used value is the value
            # specified on its nearest ancestor with a non-auto value. When
            # specified on the root element, the used value for auto is the
            # empty string.
            value = (
                '' if self.parent_style is None else self.parent_style['page'])
            if key in self.get_style_keys():
                del self[key]
        elif key in ('position', 'float', 'display'):
            self.specified[key] = value

        if key in self.get_style_keys():
            return self[key]

        function = computed_values.COMPUTER_FUNCTIONS.get(key)
        already_computed_value = False

        if value:
            converted_to_list = False

            if not isinstance(value, list):
                converted_to_list = True
                value = [value]

            for i, v in enumerate(value):
                value[i], already_computed_value = (
                    computed_values.compute_variable(
                        v, key, self, self.base_url, self.parent_style))

            if converted_to_list:
                value, = value

        if function is not None and not already_computed_value:
            value = function(self, key, value)
        # else: same as specified

        self[key] = value
        return value


def computed_from_cascaded(element, cascaded, parent_style, pseudo_type=None,
                           root_style=None, base_url=None,
                           target_collector=None, style_rel=None):
    """Get a dict of computed style mixed from parent and cascaded styles."""
    if not cascaded and parent_style is not None:
        style = AnonymousStyle(parent_style)

    else:
        style = ComputedStyle(
            parent_style, cascaded, element, pseudo_type, root_style, base_url,
            style_rel)
        if target_collector and style['anchor']:
            target_collector.collect_anchor(style['anchor'])

    if style_rel:
        style_rel.set_computed_style(
            element, pseudo_type, style, {})

    return style


def parse_page_selectors(rule):
    """Parse a page selector rule.

    Return a list of page data if the rule is correctly parsed. Page data are a
    dict containing:

    - 'side' ('left', 'right' or None),
    - 'blank' (True or None),
    - 'first' (True or None),
    - 'index' (page number or None),
    - 'name' (page name string or None), and
    - 'specificity' (list of numbers).

    Return ``None` if something went wrong while parsing the rule.

    """
    # See https://drafts.csswg.org/css-page-3/#syntax-page-selector

    tokens = list(remove_whitespace(rule.prelude))
    page_data = []

    # TODO: Specificity is probably wrong, should clean and test that.
    if not tokens:
        page_data.append({
            'side': None, 'blank': None, 'first': None, 'index': None,
            'name': None, 'specificity': [0, 0, 0]})
        return page_data

    while tokens:
        types = {
            'side': None, 'blank': None, 'first': None, 'index': None,
            'name': None, 'specificity': [0, 0, 0]}

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
                if not tokens:
                    return None

                if tokens[0].type == 'ident':
                    ident = tokens.pop(0)
                    pseudo_class = ident.lower_value

                    if pseudo_class in ('left', 'right'):
                        if types['side'] and types['side'] != pseudo_class:
                            return None
                        types['side'] = pseudo_class
                        types['specificity'][2] += 1
                        continue

                    elif pseudo_class in ('blank', 'first'):
                        types[pseudo_class] = True
                        types['specificity'][1] += 1
                        continue

                elif tokens[0].type == 'function':
                    function = tokens.pop(0)
                    if function.name != 'nth':
                        return None
                    for i, argument in enumerate(function.arguments):
                        if argument.type == 'ident' and argument.value == 'of':
                            nth = function.arguments[:i - 1]
                            group = function.arguments[i:]
                            break
                    else:
                        nth = function.arguments
                        group = None

                    nth_values = tinycss2.nth.parse_nth(nth)
                    if nth_values is None:
                        return None

                    if group is not None:
                        group = [
                            token for token in group
                            if token.type not in (
                                'comment', 'whitespacespace')]
                        if len(group) != 1:
                            return None
                        group, = group
                        if group.type != 'ident':
                            return None
                        group = group.value

                        # TODO: handle page groups
                        return None

                    types['index'] = (*nth_values, group)
                    # TODO: specificity is not specified yet
                    # https://github.com/w3c/csswg-drafts/issues/3524
                    types['specificity'][1] += 1
                    continue

                return None
            elif literal.value == ',':
                if tokens and any(types['specificity']):
                    break
                else:
                    return None

        page_data.append(types)

    return page_data


def preprocess_stylesheet(device_media_type, base_url, stylesheet_rules,
                          url_fetcher, matcher, page_rules, font_config,
                          counter_style, ignore_imports=False):
    """Do what can be done early on stylesheet, before being in a document."""
    for rule in stylesheet_rules:
        if getattr(rule, 'content', None) is None and (
                rule.type != 'at-rule' or rule.lower_at_keyword != 'import'):
            continue

        if rule.type == 'qualified-rule':
            declarations = list(preprocess_declarations(
                base_url, tinycss2.parse_declaration_list(rule.content)))
            if declarations:
                logger_level = WARNING
                try:
                    selectors = cssselect2.compile_selector_list(rule.prelude)
                    for selector in selectors:
                        matcher.add_selector(selector, declarations)
                        if selector.pseudo_element not in PSEUDO_ELEMENTS:
                            if selector.pseudo_element.startswith('-'):
                                logger_level = DEBUG
                                raise cssselect2.SelectorError(
                                    'ignored prefixed pseudo-element: '
                                    f'{selector.pseudo_element}')
                            else:
                                raise cssselect2.SelectorError(
                                    'unknown pseudo-element: '
                                    f'{selector.pseudo_element}')
                    ignore_imports = True
                except cssselect2.SelectorError as exc:
                    LOGGER.log(
                        logger_level,
                        "Invalid or unsupported selector '%s', %s",
                        tinycss2.serialize(rule.prelude), exc)
                    continue
            else:
                ignore_imports = True

        elif rule.type == 'at-rule' and rule.lower_at_keyword == 'import':
            if ignore_imports:
                LOGGER.warning(
                    '@import rule %r not at the beginning of the '
                    'the whole rule was ignored at %d:%d.',
                    tinycss2.serialize(rule.prelude),
                    rule.source_line, rule.source_column)
                continue

            tokens = remove_whitespace(rule.prelude)
            url = None
            if tokens:
                if tokens[0].type == 'string':
                    url = url_join(
                        base_url, tokens[0].value, allow_relative=False,
                        context='@import at %s:%s',
                        context_args=(rule.source_line, rule.source_column))
                else:
                    url_tuple = get_url(tokens[0], base_url)
                    if url_tuple and url_tuple[1][0] == 'external':
                        url = url_tuple[1][1]
            if url is None:
                continue
            media = media_queries.parse_media_query(tokens[1:])
            if media is None:
                LOGGER.warning(
                    'Invalid media type %r '
                    'the whole @import rule was ignored at %d:%d.',
                    tinycss2.serialize(rule.prelude),
                    rule.source_line, rule.source_column)
                continue
            if not media_queries.evaluate_media_query(
                    media, device_media_type):
                continue
            if url is not None:
                try:
                    CSS(
                        url=url, url_fetcher=url_fetcher,
                        media_type=device_media_type, font_config=font_config,
                        counter_style=counter_style, matcher=matcher,
                        page_rules=page_rules)
                except URLFetchingError as exc:
                    LOGGER.error(
                        'Failed to load stylesheet at %s : %s', url, exc)

        elif rule.type == 'at-rule' and rule.lower_at_keyword == 'media':
            media = media_queries.parse_media_query(rule.prelude)
            if media is None:
                LOGGER.warning(
                    'Invalid media type %r '
                    'the whole @media rule was ignored at %d:%d.',
                    tinycss2.serialize(rule.prelude),
                    rule.source_line, rule.source_column)
                continue
            ignore_imports = True
            if not media_queries.evaluate_media_query(
                    media, device_media_type):
                continue
            content_rules = tinycss2.parse_rule_list(rule.content)
            preprocess_stylesheet(
                device_media_type, base_url, content_rules, url_fetcher,
                matcher, page_rules, font_config, counter_style,
                ignore_imports=True)

        elif rule.type == 'at-rule' and rule.lower_at_keyword == 'page':
            data = parse_page_selectors(rule)

            if data is None:
                LOGGER.warning(
                    'Unsupported @page selector %r, '
                    'the whole @page rule was ignored at %d:%d.',
                    tinycss2.serialize(rule.prelude),
                    rule.source_line, rule.source_column)
                continue

            ignore_imports = True
            for page_type in data:
                specificity = page_type.pop('specificity')
                page_type = PageType(**page_type)
                content = tinycss2.parse_declaration_list(rule.content)
                declarations = list(preprocess_declarations(base_url, content))

                if declarations:
                    selector_list = [(specificity, None, page_type)]
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
                            specificity, f'@{margin_rule.lower_at_keyword}',
                            page_type)]
                        page_rules.append(
                            (margin_rule, selector_list, declarations))

        elif rule.type == 'at-rule' and rule.lower_at_keyword == 'font-face':
            ignore_imports = True
            content = tinycss2.parse_declaration_list(rule.content)
            rule_descriptors = dict(
                preprocess_descriptors('font-face', base_url, content))
            for key in ('src', 'font_family'):
                if key not in rule_descriptors:
                    LOGGER.warning(
                        "Missing %s descriptor in '@font-face' rule at %d:%d",
                        key.replace('_', '-'),
                        rule.source_line, rule.source_column)
                    break
            else:
                if font_config is not None:
                    font_config.add_font_face(rule_descriptors, url_fetcher)

        elif (rule.type == 'at-rule' and
                rule.lower_at_keyword == 'counter-style'):
            name = counters.parse_counter_style_name(
                rule.prelude, counter_style)
            if name is None:
                LOGGER.warning(
                    'Invalid counter style name %r, the whole '
                    '@counter-style rule was ignored at %d:%d.',
                    tinycss2.serialize(rule.prelude), rule.source_line,
                    rule.source_column)
                continue

            ignore_imports = True
            content = tinycss2.parse_declaration_list(rule.content)
            counter = {
                'system': None,
                'negative': None,
                'prefix': None,
                'suffix': None,
                'range': None,
                'pad': None,
                'fallback': None,
                'symbols': None,
                'additive_symbols': None,
            }
            rule_descriptors = preprocess_descriptors(
                'counter-style', base_url, content)

            for descriptor_name, descriptor_value in rule_descriptors:
                counter[descriptor_name] = descriptor_value

            if counter['system'] is None:
                system = (None, 'symbolic', None)
            else:
                system = counter['system']

            if system[0] is None:
                if system[1] in ('cyclic', 'fixed', 'symbolic'):
                    if len(counter['symbols'] or []) < 1:
                        LOGGER.warning(
                            'In counter style %r at %d:%d, '
                            'counter style %r needs at least one symbol',
                            name, rule.source_line, rule.source_column,
                            system[1])
                        continue
                elif system[1] in ('alphabetic', 'numeric'):
                    if len(counter['symbols'] or []) < 2:
                        LOGGER.warning(
                            'In counter style %r at %d:%d, '
                            'counter style %r needs at least two symbols',
                            name, rule.source_line, rule.source_column,
                            system[1])
                        continue
                elif system[1] == 'additive':
                    if len(counter['additive_symbols'] or []) < 2:
                        LOGGER.warning(
                            'In counter style %r at %d:%d, '
                            'counter style "additive" '
                            'needs at least two additive symbols',
                            name, rule.source_line, rule.source_column)
                        continue

            counter_style[name] = counter


def get_all_computed_styles(html, user_stylesheets=None,
                            presentational_hints=False, font_config=None,
                            counter_style=None, page_rules=None,
                            target_collector=None, forms=False):
    """Compute all the computed styles of all elements in ``html`` document.

    Do everything from finding author stylesheets to parsing and applying them.

    Return a ``style_for`` function that takes an element and an optional
    pseudo-element type, and return a style dict object.

    """
    # List stylesheets. Order here is not important ('origin' is).
    sheets = []
    if counter_style is None:
        counter_style = counters.CounterStyle()
    for style in html._ua_counter_style():
        for key, value in style.items():
            counter_style[key] = value
    for sheet in (html._ua_stylesheets(forms) or []):
        sheets.append((sheet, 'user agent', None))
    if presentational_hints:
        for sheet in (html._ph_stylesheets() or []):
            sheets.append((sheet, 'author', (0, 0, 0)))
    for sheet in find_stylesheets(
            html.wrapper_element, html.media_type, html.url_fetcher,
            html.base_url, font_config, counter_style, page_rules):
        sheets.append((sheet, 'author', None))
    for sheet in (user_stylesheets or []):
        sheets.append((sheet, 'user', None))

    return StyleFor(html, sheets, presentational_hints, target_collector)


class StyleRelationship(dict):
    """Parent-child relationship of elements."""
    def __init__(self):
        # keys: (element, pseudo_element_type), like cascaded_styles
        # values: dicts, like cascaded_styles
        # Save cascade style reference
        self._cascaded_style_indexes = {}
        # keys: (element, pseudo_element_type), like cascaded_styles
        # values: (style_object, add_keys)
        #     style_object: CoputedStyle or AnonymousStyle
        #     add_keys: add css properties
        self._computed_key_indexes = {}

    def __call__(self, element, pseudo_type=None):
        return self.get(
            (element, pseudo_type),  {"style": None, "properties": {}})

    def get_computed_styles(self):
        return self

    def _get_computed_key_indexs(self):
        return self._computed_key_indexes

    def set_computed_style(self, element, pseudo_type=None,
                           style=None, style_keys={}):
        """Set the computed style"""
        styles = self.get_computed_styles()
        styles[(element, pseudo_type)] = {"style": style, "properties": {}}
        self.set_computed_style_key(element, pseudo_type, style_keys)

    def set_computed_style_key(self, element, pseudo_type=None, style_keys={}):
        """Set the computed style keys"""
        styles = self.get_computed_styles()
        key_indexes = self._get_computed_key_indexs()
        key_str = str(sorted(style_keys.keys())).encode('utf8')
        key_index = key_indexes.setdefault(key_str, {})
        if key_index:
            for i, values in sorted(key_index.items(), reverse=True):
                if style_keys == values:
                    styles[(element, pseudo_type)]["properties"] = key_index[i]
                    break
            else:
                index = max(key_index) + 1
                key_index[index] = style_keys.copy()
                styles[(element, pseudo_type)]["properties"] = key_index[index]
        else:
            key_index[0] = style_keys.copy()
            styles[(element, pseudo_type)]["properties"] = key_index[0]
