"""Find and apply CSS.

This module takes care of steps 3 and 4 of “CSS 2.1 processing model”: Retrieve
stylesheets associated with a document and annotate every element with a value
for every CSS property.

https://www.w3.org/TR/CSS21/intro.html#processing-model

This module does this in more than two steps. The
:func:`get_all_computed_styles` function does everything, but it is itsef based
on other functions in this module.

"""

import math
from collections import namedtuple
from itertools import groupby
from logging import DEBUG, WARNING
from math import inf

import cssselect2
import tinycss2
import tinycss2.ast
import tinycss2.nth
from PIL.ImageCms import ImageCmsProfile

from .. import CSS
from ..logger import LOGGER, PROGRESS_LOGGER
from ..text.fonts import FontConfiguration
from ..urls import URLFetchingError, fetch, get_url_attribute, url_join
from . import counters, media_queries
from .computed_values import COMPUTER_FUNCTIONS
from .functions import Function, check_math, check_var
from .properties import INHERITED, INITIAL_NOT_COMPUTED, INITIAL_VALUES, ZERO_PIXELS
from .units import ANGLE_UNITS, FONT_UNITS, LENGTH_UNITS, to_pixels, to_radians
from .validation import preprocess_declarations
from .validation.descriptors import preprocess_descriptors
from .validation.properties import validate_non_shorthand

from .tokens import (  # isort:skip
    E, MINUS_INFINITY, NAN, PI, PLUS_INFINITY, FontUnitInMath, InvalidValues, Pending,
    PercentageInMath, get_angle, get_url, remove_whitespace, split_on_comma, tokenize)

# Reject anything not in here:
PSEUDO_ELEMENTS = (
    None, 'before', 'after', 'marker', 'first-line', 'first-letter',
    'footnote-call', 'footnote-marker')

PageSelectorType = namedtuple(
    'PageSelectorType', ['side', 'blank', 'first', 'index', 'name'])


class StyleFor:
    """Convenience function to get the computed styles for an element."""
    def __init__(self, html, sheets, presentational_hints, font_config,
                 target_collector):
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

        # keys: (element, pseudo_element_type), like cascaded_styles
        # values: style dict objects:
        #     keys: property name as a string
        #     values: a PropertyValue-like object
        self._computed_styles = {}

        self._sheets = sheets
        self.font_config = font_config

        PROGRESS_LOGGER.info('Step 3 - Applying CSS')
        layer_order = inf
        for specificity, attributes in find_style_attributes(
                html.etree_element, presentational_hints, html.base_url):
            element, declarations, base_url = attributes
            style = cascaded_styles.setdefault((element, None), {})
            for name, values, importance in preprocess_declarations(
                    base_url, declarations):
                precedence = declaration_precedence('author', importance)
                weight = (precedence, layer_order, specificity)
                old_weight = style.get(name, (None, None))[1]
                if old_weight is None or old_weight <= weight:
                    style[name] = values, weight

        # First, add declarations and set computed styles for "real" elements
        # *in tree order*. Tree order is important so that parents have
        # computed styles before their children, for inheritance.

        # Iterate on all elements, even if there is no cascaded style for them.
        for element in html.wrapper_element.iter_subtree():
            for sheet, origin, sheet_specificity in sheets:
                # Add declarations for matched elements
                for selector in sheet.matcher.match(element):
                    specificity, order, pseudo_type, (declarations, layer) = selector
                    layer_order = inf if layer is None else sheet.layers.index(layer)
                    specificity = sheet_specificity or specificity
                    style = cascaded_styles.setdefault(
                        (element.etree_element, pseudo_type), {})
                    for name, values, importance in declarations:
                        precedence = declaration_precedence(origin, importance)
                        weight = (precedence, layer_order, specificity)
                        old_weight = style.get(name, (None, None))[1]
                        if old_weight is None or old_weight <= weight:
                            style[name] = values, weight
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
        for element, pseudo_type in cascaded_styles:
            if pseudo_type:
                self.set_computed_styles(
                    element, pseudo_type=pseudo_type,
                    # The pseudo-element inherits from the element.
                    root=html.etree_element, parent=element,
                    base_url=html.base_url, target_collector=target_collector)

        # Clear the cascaded styles, we don't need them anymore. Keep the
        # dictionary, it is used later for page margins.
        self._cascaded_styles.clear()

    def __call__(self, element, pseudo_type=None):
        if style := self._computed_styles.get((element, pseudo_type)):
            if 'table' in style['display'] and style['border_collapse'] == 'collapse':
                # Padding does not apply.
                for side in ('top', 'bottom', 'left', 'right'):
                    style[f'padding_{side}'] = ZERO_PIXELS
            if len(style['display']) == 1:
                display, = style['display']
                if display.startswith('table-') and display != 'table-caption':
                    # Margins do not apply.
                    for side in ('top', 'bottom', 'left', 'right'):
                        style[f'margin_{side}'] = ZERO_PIXELS
        return style

    def set_computed_styles(self, element, parent, root=None, pseudo_type=None,
                            base_url=None, target_collector=None):
        """Set the computed values of styles to ``element``.

        Take the properties left by ``apply_style_rule`` on an element or
        pseudo-element and assign computed values with respect to the cascade,
        declaration priority (ie. ``!important``) and selector specificity.

        """
        cascaded_styles = self.get_cascaded_styles()
        computed_styles = self.get_computed_styles()
        if element == root and pseudo_type is None:
            assert parent is None
            parent_style = None
            root_style = InitialStyle(self.font_config)
        else:
            assert parent is not None
            parent_style = computed_styles[parent, None]
            root_style = computed_styles[root, None]

        cascaded = cascaded_styles.get((element, pseudo_type), {})
        computed = computed_styles[element, pseudo_type] = ComputedStyle(
            parent_style, cascaded, element, pseudo_type, root_style, base_url,
            self.font_config)
        if target_collector and computed['anchor']:
            target_collector.collect_anchor(computed['anchor'])

    def add_page_declarations(self, page_type):
        # TODO: use real layer order.
        layer_order = None
        for sheet, origin, sheet_specificity in self._sheets:
            for _rule, selector_list, declarations in sheet.page_rules:
                for selector in selector_list:
                    specificity, pseudo_type, page_selector_type = selector
                    if self._page_type_match(page_selector_type, page_type):
                        specificity = sheet_specificity or specificity
                        style = self._cascaded_styles.setdefault(
                            (page_type, pseudo_type), {})
                        for name, values, importance in declarations:
                            precedence = declaration_precedence(origin, importance)
                            weight = (precedence, layer_order, specificity)
                            old_weight = style.get(name, (None, None))[1]
                            if old_weight is None or old_weight <= weight:
                                style[name] = values, weight

    def get_cascaded_styles(self):
        return self._cascaded_styles

    def get_computed_styles(self):
        return self._computed_styles

    @staticmethod
    def _page_type_match(page_selector_type, page_type):
        if page_selector_type.side not in (None, page_type.side):
            return False
        if page_selector_type.blank not in (None, page_type.blank):
            return False
        if page_selector_type.first not in (None, page_type.index == 0):
            return False
        if page_selector_type.name not in (None, page_type.name):
            return False
        if page_selector_type.index is not None:
            a, b, name = page_selector_type.index
            if name is None:
                index = page_type.index
                offset = index + 1 - b
                return offset == 0 if a == 0 else (offset / a >= 0 and not offset % a)
            if name != page_type.name:
                return False
            for group_name, index in page_type.groups:
                if name != group_name:
                    continue
                offset = index + 1 - b
                if (offset == 0 if a == 0 else (offset / a >= 0 and not offset % a)):
                    return True
            return False
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
    text_properties = (
        'text_decoration_color', 'text_decoration_style', 'text_decoration_thickness')
    if key in text_properties:
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
                     font_config, counter_style, color_profiles, page_rules, layers):
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
                page_rules=page_rules, color_profiles=color_profiles, layers=layers)
            yield css
        elif element.tag == 'link' and element.get('href'):
            if not element_has_link_type(element, 'stylesheet') or \
                    element_has_link_type(element, 'alternate'):
                continue
            href = get_url_attribute(element, 'href', base_url)
            if href is not None:
                try:
                    yield CSS(
                        url=href, url_fetcher=url_fetcher, media_type=device_media_type,
                        font_config=font_config, counter_style=counter_style,
                        color_profiles=color_profiles, page_rules=page_rules,
                        layers=layers, _check_mime_type=True)
                except URLFetchingError as exception:
                    LOGGER.error('Failed to load stylesheet at %s: %s', href, exception)
                    LOGGER.debug('Error while loading stylesheet:', exc_info=exception)


def find_style_attributes(tree, presentational_hints=False, base_url=None):
    """Yield ``specificity, (element, declaration, base_url)`` rules.

    Rules from "style" attribute are returned with specificity
    ``(1, 0, 0)``.

    If ``presentational_hints`` is ``True``, rules from presentational hints
    are returned with specificity ``(0, 0, 0)``.

    """
    def check_style_attribute(element, style_attribute):
        declarations = tinycss2.parse_blocks_contents(style_attribute)
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
                        style_attribute = f'margin-{position}:{element.get(prop)}px'
                        break
                if style_attribute:
                    yield specificity, check_style_attribute(element, style_attribute)
            if element.get('background'):
                style_attribute = f'background-image:url({element.get("background")})'
                yield specificity, check_style_attribute(element, style_attribute)
            if element.get('bgcolor'):
                style_attribute = f'background-color:{element.get("bgcolor")}'
                yield specificity, check_style_attribute(element, style_attribute)
            if element.get('text'):
                style_attribute = f'color:{element.get("text")}'
                yield specificity, check_style_attribute(element, style_attribute)
            # TODO: we should support link, vlink, alink
        elif element.tag == 'center':
            yield specificity, check_style_attribute(element, 'text-align:center')
        elif element.tag == 'div':
            align = element.get('align', '').lower()
            if align == 'middle':
                yield specificity, check_style_attribute(element, 'text-align:center')
            elif align in ('center', 'left', 'right', 'justify'):
                yield specificity, check_style_attribute(element, f'text-align:{align}')
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
                yield specificity, check_style_attribute(element, style_attribute)
            if element.get('height'):
                style_attribute = f'height:{element.get("height")}'
                if element.get('height').isdigit():
                    style_attribute += 'px'
                yield specificity, check_style_attribute(element, style_attribute)
            if element.get('background'):
                style_attribute = (
                    f'background-image:url({element.get("background")})')
                yield specificity, check_style_attribute(element, style_attribute)
            if element.get('bgcolor'):
                style_attribute = f'background-color:{element.get("bgcolor")}'
                yield specificity, check_style_attribute(element, style_attribute)
            if element.get('bordercolor'):
                style_attribute = f'border-color:{element.get("bordercolor")}'
                yield specificity, check_style_attribute(element, style_attribute)
            if element.get('border'):
                style_attribute = f'border-width:{element.get("border")}px'
                yield specificity, check_style_attribute(element, style_attribute)
        elif element.tag in ('tr', 'td', 'th', 'thead', 'tbody', 'tfoot'):
            align = element.get('align', '').lower()
            # TODO: we should align descendants too
            if align == 'middle':
                yield specificity, check_style_attribute(
                    element, 'text-align:center')
            elif align in ('center', 'left', 'right', 'justify'):
                yield specificity, check_style_attribute(element, f'text-align:{align}')
            if element.get('background'):
                style_attribute = f'background-image:url({element.get("background")})'
                yield specificity, check_style_attribute(element, style_attribute)
            if element.get('bgcolor'):
                style_attribute = f'background-color:{element.get("bgcolor")}'
                yield specificity, check_style_attribute(element, style_attribute)
            if element.tag in ('tr', 'td', 'th'):
                if element.get('height'):
                    style_attribute = f'height:{element.get("height")}'
                    if element.get('height').isdigit():
                        style_attribute += 'px'
                    yield specificity, check_style_attribute(element, style_attribute)
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
                yield specificity, check_style_attribute(element, 'text-align:center')
            elif align in ('center', 'left', 'right', 'justify'):
                yield specificity, check_style_attribute(element, f'text-align:{align}')
        elif element.tag == 'col':
            if element.get('width'):
                style_attribute = f'width:{element.get("width")}'
                if element.get('width').isdigit():
                    style_attribute += 'px'
                yield specificity, check_style_attribute(element, style_attribute)
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
                yield specificity, check_style_attribute(element, style_attribute)
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
                    yield specificity, check_style_attribute(element, style_attribute)
                if element.get('height'):
                    style_attribute = f'height:{element.get("height")}'
                    if element.get('height').isdigit():
                        style_attribute += 'px'
                    yield specificity, check_style_attribute(element, style_attribute)
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


def resolve_var(computed, token, parent_style, known_variables=None):
    """Return token with resolved CSS variables."""
    if not check_var(token):
        return

    if known_variables is None:
        known_variables = set()

    if token.type == '() block' or token.lower_name != 'var':
        items = []
        token_items = token.arguments if token.type == 'function' else token.content
        for i, argument in enumerate(token_items):
            if argument.type in ('function', '() block'):
                resolved = resolve_var(
                    computed, argument, parent_style, known_variables.copy())
                items.extend((argument,) if resolved is None else resolved)
            else:
                items.append(argument)
        if token.type == '() block':
            token = tinycss2.ast.ParenthesesBlock(
                token.source_line, token.source_column, items)
        else:
            token = tinycss2.ast.FunctionBlock(
                token.source_line, token.source_column, token.name, items)
        return resolve_var(computed, token, parent_style, known_variables) or (token,)

    function = Function(token)
    arguments = function.split_comma(single_tokens=False, trailing=True)
    if not arguments or len(arguments[0]) != 1:
        return []
    variable_name = arguments[0][0].value.replace('-', '_')  # first arg is name
    if variable_name in known_variables:
        return []  # endless recursion
    else:
        known_variables.add(variable_name)
    default = arguments[1] if len(arguments) > 1 else []
    computed_value = []
    for value in (computed[variable_name] or default):
        resolved = resolve_var(computed, value, parent_style, known_variables.copy())
        computed_value.extend((value,) if resolved is None else resolved)
    return computed_value


def _resolve_calc_sum(computed, tokens, property_name, refer_to):
    groups = [[]]
    for token in tokens:
        if token.type == 'literal' and token.value in '+-':
            groups.append(token.value)
            groups.append([])
        elif token.type == '() block':
            content = remove_whitespace(token.content)
            result = _resolve_calc_sum(computed, content, property_name, refer_to)
            if result is None:
                return
            groups[-1].append(result)
        else:
            groups[-1].append(token)

    value, sign, unit = 0, '+', None
    exception = None
    while groups:
        if sign is None:
            sign = groups.pop(0)
            assert sign in '+-'
        else:
            group = groups.pop(0)
            assert group
            assert isinstance(group, list)
            try:
                product = _resolve_calc_product(
                    computed, group, property_name, refer_to)
            except FontUnitInMath as font_exception:
                # FontUnitInMath raised, assume that we got pixels and continue to find
                # if we have to raise PercentageInMath first.
                if unit == '%':
                    raise PercentageInMath
                exception = font_exception
                unit = 'px'
                sign = None
                continue
            else:
                if product is None:
                    return
            if product.type == 'dimension':
                if unit is None:
                    unit = product.unit.lower()
                elif unit == '%':
                    raise PercentageInMath
                elif unit != product.unit.lower():
                    return
            elif product.type == 'percentage':
                if refer_to is not None:
                    product.value = product.value / 100 * refer_to
                    unit = 'px'
                else:
                    if unit is None or unit == '%':
                        unit = '%'
                    else:
                        raise PercentageInMath
            if sign == '+':
                value += product.value
            else:
                value -= product.value
            sign = None

    # Raise FontUnitInMath, only if we didn’t raise PercentageInMath before.
    if exception:
        raise exception

    return tokenize(value, unit=unit)


def _resolve_calc_product(computed, tokens, property_name, refer_to):
    groups = [[]]
    for token in tokens:
        if token.type == 'literal' and token.value in '*/':
            groups.append(token.value)
            groups.append([])
        elif token.type == 'number':
            groups[-1].append(token)
        elif token.type == 'dimension' and token.unit.lower() in LENGTH_UNITS:
            if computed is None and token.unit.lower() in FONT_UNITS:
                raise FontUnitInMath
            pixels = to_pixels(token, computed, property_name)
            groups[-1].append(tokenize(pixels, unit='px'))
        elif token.type == 'dimension' and token.unit.lower() in ANGLE_UNITS:
            groups[-1].append(tokenize(to_radians(token), unit='rad'))
        elif token.type == 'percentage':
            groups[-1].append(tokenize(token.value, unit='%'))
        elif token.type == 'ident':
            groups[-1].append(token)
        else:
            return

    value, sign, unit = 1, '*', None
    while groups:
        if sign is None:
            sign = groups.pop(0)
            assert sign in '*/'
        else:
            group = groups.pop(0)
            assert isinstance(group, list)
            calc = _resolve_calc_value(computed, group)
            if calc is None:
                return
            if calc.type == 'dimension':
                if unit is None or unit == '%':
                    unit = calc.unit.lower()
                else:
                    return
            elif calc.type == 'percentage':
                if unit is None:
                    unit = '%'
            if sign == '*':
                value *= calc.value
            else:
                value /= calc.value
            sign = None

    return tokenize(value, unit=unit)


def _resolve_calc_value(computed, tokens):
    if len(tokens) == 1:
        token, = tokens
        if token.type in ('number', 'dimension', 'percentage'):
            return token
        elif token.type == 'ident':
            if token.lower_value == 'e':
                return E
            elif token.lower_value == 'pi':
                return PI
            elif token.lower_value == 'infinity':
                return PLUS_INFINITY
            elif token.lower_value == '-infinity':
                return MINUS_INFINITY
            elif token.lower_value == 'nan':
                return NAN


def resolve_math(token, computed=None, property_name=None, refer_to=None):
    """Return token with resolved math functions.

    Raise, in order of priority, ``PercentageInMath`` if percentages are mixed with
    other values with no ``refer_to`` size, or ``FontUnitInMath`` if no ``computed``
    style is available to get font size.

    ``PercentageInMath`` has to be raised before FontUnitInMath so that it can be used
    to discard validation of properties that don’t accept percentages.

    """
    if not check_math(token):
        return

    args = []
    original_token = token
    function = Function(token)
    if function.name is None:
        return
    for part in function.split_comma(single_tokens=False):
        args.append([])
        for arg in part:
            if check_math(arg):
                arg = resolve_math(arg, computed, property_name, refer_to)
                if arg is None:
                    return
            args[-1].append(arg)

    if function.name == 'calc':
        result = _resolve_calc_sum(computed, args[0], property_name, refer_to)
        if result is None:
            return original_token
        else:
            return tokenize(result)

    elif function.name in ('min', 'max'):
        target_value = target_token = unit = None
        for tokens in args:
            token = _resolve_calc_sum(computed, tokens, property_name, refer_to)
            if token is None:
                return
            if token.type == 'percentage':
                if refer_to is None:
                    if unit in ('px', ''):
                        raise PercentageInMath
                    unit = '%'
                    value = token
                else:
                    unit = 'px'
                    token = value = tokenize(token.value / 100 * refer_to, unit='px')
            elif token.type == 'number':
                if unit == '%':
                    raise PercentageInMath
                elif unit == 'px':
                    return
                unit = ''
                value = tokenize(token.value, unit='px')
            else:
                if unit == '%':
                    raise PercentageInMath
                elif unit == '':
                    return
                unit = 'px'
                value = tokenize(to_pixels(token, computed, property_name), unit='px')
            update_condition = (
                target_value is None or
                (function.name == 'min' and value.value < target_value.value) or
                (function.name == 'max' and value.value > target_value.value))
            if update_condition:
                target_value, target_token = value, token
        return tokenize(target_token)

    elif function.name == 'round':
        strategy, multiple = 'nearest', 1
        if len(args) == 1:
            number_token = _resolve_calc_sum(computed, args[0], property_name, refer_to)
        elif len(args) == 2:
            strategies = ('nearest', 'up', 'down', 'to-zero')
            if len(args[0]) == 1 and args[0][0].value in strategies:
                strategy = args[0][0].value
                number_token = _resolve_calc_sum(
                    computed, args[1], property_name, refer_to)
                if number_token is None:
                    return
            else:
                number_token = _resolve_calc_sum(
                    computed, args[0], property_name, refer_to)
                multiple_token = _resolve_calc_sum(
                    computed, args[1], property_name, refer_to)
                if None in (number_token, multiple_token):
                    return
                if number_token.type != multiple_token.type:
                    return
                multiple = multiple_token.value
        elif len(args) == 3:
            strategy = args[0][0].value
            number_token = _resolve_calc_sum(computed, args[1], property_name, refer_to)
            multiple_token = _resolve_calc_sum(
                computed, args[2], property_name, refer_to)
            if None in (number_token, multiple_token):
                return
            if number_token.type != multiple_token.type:
                return
            multiple = multiple_token.value
        if strategy == 'nearest':
            # TODO: always round x.5 to +inf, see
            # https://drafts.csswg.org/css-values-4/#combine-integers.
            function = round
        elif strategy == 'up':
            function = math.ceil
        elif strategy == 'down':
            function = math.floor
        elif strategy == 'to-zero':
            function = math.floor if number_token.value > 0 else math.ceil
        else:
            return
        return tokenize(number_token, lambda x: function(x / multiple) * multiple)

    elif function.name in ('mod', 'rem'):
        number_token = _resolve_calc_sum(computed, args[0], property_name, refer_to)
        parameter_token = _resolve_calc_sum(computed, args[1], property_name, refer_to)
        if None in (number_token, parameter_token):
            return
        if number_token.type != parameter_token.type:
            return
        number = number_token.value
        parameter = parameter_token.value
        value = number % parameter
        if function.name == 'rem' and number * parameter < 0:
            value += abs(parameter)
        return tokenize(number_token, lambda x: value)

    elif function.name in ('sin', 'cos', 'tan'):
        number_token = _resolve_calc_sum(computed, args[0], property_name, refer_to)
        if number_token is None:
            return
        if number_token.type == 'number':
            angle = number_token.value
        elif (angle := get_angle(number_token)) is None:
            return
        value = getattr(math, function.name)(angle)
        return tokenize(value)

    elif function.name in ('asin', 'acos', 'atan'):
        number_token = _resolve_calc_sum(computed, args[0], property_name, refer_to)
        if number_token is None or number_token.type != 'number':
            return
        try:
            value = getattr(math, function.name)(number_token.value)
        except ValueError:
            return
        return tokenize(value, unit='rad')

    elif function.name == 'atan2':
        y_token, x_token = [
            _resolve_calc_sum(computed, arg, property_name, refer_to) for arg in args]
        if None in (y_token, x_token):
            return
        if {y_token.type, x_token.type} != {'number'}:
            return
        y, x = y_token.value, x_token.value
        return tokenize(math.atan2(y, x), unit='rad')

    elif function.name == 'clamp':
        pixels_list = []
        unit = None
        for tokens in args:
            token = _resolve_calc_sum(computed, tokens, property_name, refer_to)
            if token is None:
                return
            if token.type == 'percentage':
                if refer_to is None:
                    if unit == 'px':
                        raise PercentageInMath
                    unit = '%'
                    value = token
                else:
                    unit = 'px'
                    token = tokenize(token.value / 100 * refer_to, unit='px')
            else:
                if unit == '%':
                    raise PercentageInMath
                unit = 'px'
                pixels = to_pixels(token, computed, property_name)
                value = tokenize(pixels, unit='px')
            pixels_list.append(value)
        min_token, token, max_token = pixels_list
        if token.value < min_token.value:
            token = min_token
        if token.value > max_token.value:
            token = max_token
        return tokenize(token)

    elif function.name == 'pow':
        number_token, power_token = [
            _resolve_calc_sum(computed, arg, property_name, refer_to) for arg in args]
        if None in (number_token, power_token):
            return
        if {number_token.type, power_token.type} != {'number'}:
            return
        return tokenize(number_token, lambda x: x ** power_token.value)

    elif function.name == 'sqrt':
        number_token = _resolve_calc_sum(computed, args[0], property_name, refer_to)
        if number_token is None or number_token.type != 'number':
            return
        return tokenize(number_token, lambda x: x ** 0.5)

    elif function.name == 'hypot':
        resolved = [
            _resolve_calc_sum(computed, tokens, property_name, refer_to)
            for tokens in args]
        if None in resolved:
            return
        value = math.hypot(*[token.value for token in resolved])
        return tokenize(resolved[0], lambda x: value)

    elif function.name == 'log':
        number_token = _resolve_calc_sum(computed, args[0], property_name, refer_to)
        if number_token is None or number_token.type != 'number':
            return
        if len(args) == 2:
            base_token = _resolve_calc_sum(computed, args[1], property_name, refer_to)
            if base_token is None or base_token.type != 'number':
                return
            base = base_token.value
        else:
            base = math.e
        return tokenize(number_token, lambda x: math.log(x, base))

    elif function.name == 'exp':
        number_token = _resolve_calc_sum(computed, args[0], property_name, refer_to)
        if number_token is None or number_token.type != 'number':
            return
        return tokenize(number_token, math.exp)

    elif function.name == 'abs':
        number_token = _resolve_calc_sum(computed, args[0], property_name, refer_to)
        if number_token is None:
            return
        return tokenize(number_token, abs)

    elif function.name == 'sign':
        number_token = _resolve_calc_sum(computed, args[0], property_name, refer_to)
        if number_token is None:
            return
        return tokenize(
            number_token.value, lambda x: 0 if x == 0 else 1 if x > 0 else -1)

    arguments = []
    for i, argument in enumerate(token.arguments):
        if argument.type == 'function':
            result = resolve_math(argument, computed, property_name, refer_to)
            if result is None:
                return
            arguments.append(result)
        else:
            arguments.append(argument)
    token = tinycss2.ast.FunctionBlock(
        token.source_line, token.source_column, token.name, arguments)
    return resolve_math(token, computed, property_name, refer_to) or token


class InitialStyle(dict):
    """Dummy computed style used to store initial values."""
    def __init__(self, font_config):
        self.parent_style = None
        self.specified = self
        self.cache = {}
        self.font_config = font_config

    def __missing__(self, key):
        value = self[key] = INITIAL_VALUES[key]
        return value


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
        self.is_root_element = False
        self.specified = self
        self.cache = parent_style.cache
        self.font_config = parent_style.font_config

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
                key, INITIAL_VALUES[key], self.parent_style[key], cascaded=False)
        else:
            value = INITIAL_VALUES[key]
            if key in INITIAL_NOT_COMPUTED:
                # Value not computed yet: compute.
                value = self[key] = COMPUTER_FUNCTIONS[key](self, key, value)
            else:
                # The value is the same as when computed.
                self[key] = value
        return value


class ComputedStyle(dict):
    """Computed style used for non-anonymous boxes."""
    def __init__(self, parent_style, cascaded, element, pseudo_type,
                 root_style, base_url, font_config):
        self.specified = {}
        self.parent_style = parent_style
        self.cascaded = cascaded
        self.is_root_element = parent_style is None
        self.element = element
        self.pseudo_type = pseudo_type
        self.root_style = root_style
        self.base_url = base_url
        self.font_config = font_config
        self.cache = parent_style.cache if parent_style else {}

    def copy(self):
        copy = ComputedStyle(
            self.parent_style, self.cascaded, self.element, self.pseudo_type,
            self.root_style, self.base_url, self.font_config)
        copy.update(self)
        copy.specified = self.specified.copy()
        return copy

    def __missing__(self, key):
        if key == 'float':
            # Set specified value for position, needed for computed value.
            self['position']
        elif key == 'display':
            # Set specified value for float, needed for computed value.
            self['float']

        parent_style = self.parent_style

        if key in self.cascaded:
            # Property defined in cascaded properties.
            value = self.cascaded[key][0]
            pending = isinstance(value, Pending)
        else:
            # Property not defined in cascaded properties, define as inherited
            # or initial value.
            if key in INHERITED or key[:2] == '__':
                value = 'inherit'
            else:
                value = 'initial'
            pending = False

        if value == 'inherit' and parent_style is None:
            # On the root element, 'inherit' from initial values
            value = 'initial'

        if pending:
            # Property with pending values, validate them.
            solved_tokens = []
            for token in value.tokens:
                tokens = resolve_var(self, token, parent_style)
                if tokens is None:
                    solved_tokens.append(token)
                else:
                    solved_tokens.extend(tokens)
            original_key = key.replace('_', '-')
            try:
                value = value.solve(solved_tokens, original_key)
            except InvalidValues:
                if key in INHERITED and parent_style is not None:
                    # Values in parent_style are already computed.
                    self[key] = value = parent_style[key]
                else:
                    value = INITIAL_VALUES[key]
                    if key not in INITIAL_NOT_COMPUTED:
                        # The value is the same as when computed.
                        self[key] = value

        if value == 'initial':
            value = [] if key[:2] == '__' else INITIAL_VALUES[key]
            if key not in INITIAL_NOT_COMPUTED:
                # The value is the same as when computed.
                self[key] = value
        elif value == 'inherit':
            # Values in parent_style are already computed.
            self[key] = value = parent_style[key]

        if key[:16] == 'text_decoration_' and parent_style is not None:
            # Text decorations are not inherited but propagated. See
            # https://www.w3.org/TR/css-text-decor-3/#line-decoration.
            if key in COMPUTER_FUNCTIONS:
                value = COMPUTER_FUNCTIONS[key](self, key, value)
            self[key] = text_decoration(
                key, value, parent_style[key], key in self.cascaded)
        elif key == 'page' and value == 'auto':
            # The page property does not inherit. However, if the page value on
            # an element is auto, then its used value is the value specified on
            # its nearest ancestor with a non-auto value. When specified on the
            # root element, the used value for auto is the empty string. See
            # https://www.w3.org/TR/css-page-3/#using-named-pages.
            value = '' if parent_style is None else parent_style['page']
            if key in self:
                del self[key]
        elif key in ('position', 'float', 'display'):
            # Save specified values to define computed values for these
            # specific properties. See
            # https://www.w3.org/TR/CSS21/visuren.html#dis-pos-flo.
            self.specified[key] = value

        if check_math(value):
            function = value
            solved_tokens = []
            try:
                try:
                    token = resolve_math(function, self, key)
                except PercentageInMath:
                    token = None
                if token is None:
                    solved_tokens.append(function)
                else:
                    solved_tokens.append(token)
                original_key = key.replace('_', '-')
                value = validate_non_shorthand(solved_tokens, original_key)[0][1]
            except Exception:
                LOGGER.warning(
                    'Invalid math function at %d:%d: %s',
                    function.source_line, function.source_column, function.serialize())
                if key in INHERITED and parent_style is not None:
                    # Values in parent_style are already computed.
                    self[key] = value = parent_style[key]
                else:
                    value = INITIAL_VALUES[key]
                    if key not in INITIAL_NOT_COMPUTED:
                        # The value is the same as when computed.
                        self[key] = value

        if key in self:
            # Value already computed and saved: return.
            return self[key]

        if key in COMPUTER_FUNCTIONS:
            # Value not computed yet: compute.
            value = COMPUTER_FUNCTIONS[key](self, key, value)

        self[key] = value
        return value


class ColorProfile:
    def __init__(self, file_object, descriptors):
        self.src = descriptors['src'][1]
        self.renderingintent = descriptors['rendering-intent']
        self.components = descriptors['components']
        self._profile = ImageCmsProfile(file_object)

    @property
    def name(self):
        return (
            self._profile.profile.model or
            self._profile.profile.profile_description)

    @property
    def content(self):
        return self._profile.tobytes()


def _add_layer(layer, layers):
    """Add layer to list of layers, handling order."""
    index = None
    parts = layer.split('.')
    full_layer = ''
    for part in parts:
        if full_layer:
            full_layer += '.'
        full_layer += part
        if full_layer in layers:
            index = layers.index(full_layer)
            continue
        if index is None:
            layers.append(full_layer)
            index = len(layers) - 1
        else:
            layers.insert(index, full_layer)
            index -= 1


def computed_from_cascaded(element, cascaded, parent_style, pseudo_type=None,
                           root_style=None, base_url=None,
                           target_collector=None):
    """Get a dict of computed style mixed from parent and cascaded styles."""
    if not cascaded and parent_style is not None:
        return AnonymousStyle(parent_style)


def _parse_layer(tokens):
    """Parse tokens representing a layer name."""
    if not tokens:
        return
    new_layer = ''
    last_dot = True
    for token in tokens:
        if token.type == 'ident' and last_dot:
            new_layer += token.value
            last_dot = False
        elif token.type == 'literal' and token.value == '.' and not last_dot:
            new_layer += '.'
            last_dot = True
        else:
            return
    if not last_dot:
        return new_layer


def parse_color_profile_name(prelude):
    tokens = list(remove_whitespace(prelude))

    if len(tokens) != 1:
        return

    token = tokens[0]
    if token.type != 'ident':
        return

    if token.value.startswith('--') or token.value == 'device-cmyk':
        return token.value


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
                            group = function.arguments[i + 1:]
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
                            if token.type not in ('comment', 'whitespace')]
                        if len(group) != 1:
                            return None
                        group, = group
                        if group.type != 'ident':
                            return None
                        group = group.value

                    types['index'] = (*nth_values, group)
                    # TODO: specificity is not specified yet
                    # https://github.com/w3c/csswg-drafts/issues/3524
                    types['specificity'][1] += 1
                    if group:
                        types['specificity'][0] += 1
                    continue

                return None
            elif literal.value == ',':
                if tokens and any(types['specificity']):
                    break
                else:
                    return None

        page_data.append(types)

    return page_data


def preprocess_stylesheet(device_media_type, base_url, stylesheet_rules, url_fetcher,
                          matcher, page_rules, layers, font_config, counter_style,
                          color_profiles, ignore_imports=False, layer=None):
    """Do what can be done early on stylesheet, before being in a document."""
    for rule in stylesheet_rules:
        if getattr(rule, 'content', None) is None:
            if rule.type == 'error':
                LOGGER.warning(
                    "Parse error at %d:%d: %s",
                    rule.source_line, rule.source_column, rule.message)
            if rule.type != 'at-rule':
                continue
            if rule.lower_at_keyword not in ('import', 'layer'):
                LOGGER.warning(
                    "Unknown empty rule %s at %d:%d",
                    rule, rule.source_line, rule.source_column)
                continue

        if rule.type == 'qualified-rule':
            try:
                logger_level = WARNING
                contents = tinycss2.parse_blocks_contents(rule.content)
                selectors_declarations = list(
                    preprocess_declarations(base_url, contents, rule.prelude))

                if selectors_declarations:
                    selectors_declarations = groupby(
                        selectors_declarations, key=lambda x: x[0])
                    for selectors, declarations in selectors_declarations:
                        declarations = [
                            declaration[1] for declaration in declarations]
                        for selector in selectors:
                            matcher.add_selector(selector, (declarations, layer))
                            if selector.pseudo_element not in PSEUDO_ELEMENTS:
                                prelude = tinycss2.serialize(rule.prelude)
                                if selector.pseudo_element.startswith('-'):
                                    logger_level = DEBUG
                                    raise cssselect2.SelectorError(
                                        f"'{prelude}', "
                                        'ignored prefixed pseudo-element: '
                                        f'{selector.pseudo_element}')
                                else:
                                    raise cssselect2.SelectorError(
                                        f"'{prelude}', "
                                        'unknown pseudo-element: '
                                        f'{selector.pseudo_element}')
                        ignore_imports = True
                else:
                    ignore_imports = True
            except cssselect2.SelectorError as exc:
                LOGGER.log(logger_level, 'Invalid or unsupported selector, %s', exc)
                continue

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

            new_layer = None
            next_tokens = list(tokens[1:])
            if next_tokens:
                if next_tokens[0].type == 'function' and next_tokens[0].name == 'layer':
                    function = next_tokens.pop(0)
                    if not (new_layer := _parse_layer(function.arguments)):
                        LOGGER.warning(
                            'Invalid layer name %r '
                            'the whole @import rule was ignored at %d:%d.',
                            tinycss2.serialize(function),
                            rule.source_line, rule.source_column)
                        continue
                elif next_tokens[0].type == 'ident' and next_tokens[0].value == 'layer':
                    next_tokens.pop(0)
                    new_layer = f'@anonymous{len(layers)}'
                if new_layer:
                    if layer is not None:
                        new_layer = f'{layer}.{new_layer}'
                    _add_layer(new_layer, layers)

            media = media_queries.parse_media_query(next_tokens)
            if media is None:
                LOGGER.warning(
                    'Invalid media type %r '
                    'the whole @import rule was ignored at %d:%d.',
                    tinycss2.serialize(rule.prelude),
                    rule.source_line, rule.source_column)
                continue
            if not media_queries.evaluate_media_query(media, device_media_type):
                continue
            if url is not None:
                try:
                    CSS(
                        url=url, url_fetcher=url_fetcher, media_type=device_media_type,
                        font_config=font_config, counter_style=counter_style,
                        color_profiles=color_profiles, matcher=matcher,
                        page_rules=page_rules, layers=layers, layer=new_layer)
                except URLFetchingError as exception:
                    LOGGER.error('Failed to load stylesheet at %s : %s', url, exception)
                    LOGGER.debug('Error while loading stylesheet:', exc_info=exception)

        elif rule.type == 'at-rule' and rule.lower_at_keyword == 'media':
            media = media_queries.parse_media_query(rule.prelude)
            if media is None:
                LOGGER.warning(
                    'Invalid media type %r '
                    'the whole @media rule was ignored at %d:%d.',
                    tinycss2.serialize(rule.prelude),
                    rule.source_line, rule.source_column)
                continue
            if not media_queries.evaluate_media_query(media, device_media_type):
                continue
            content_rules = tinycss2.parse_rule_list(rule.content)
            preprocess_stylesheet(
                device_media_type, base_url, content_rules, url_fetcher, matcher,
                page_rules, layers, font_config, counter_style, color_profiles,
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
            for page_data in data:
                specificity = page_data.pop('specificity')
                page_selector_type = PageSelectorType(**page_data)
                content = tinycss2.parse_blocks_contents(rule.content)
                declarations = list(preprocess_declarations(base_url, content))

                if declarations:
                    selector_list = [(specificity, None, page_selector_type)]
                    page_rules.append((rule, selector_list, declarations))

                for margin_rule in content:
                    if margin_rule.type != 'at-rule' or margin_rule.content is None:
                        continue
                    declarations = list(preprocess_declarations(
                        base_url,
                        tinycss2.parse_blocks_contents(margin_rule.content)))
                    if declarations:
                        selector_list = [(
                            specificity, f'@{margin_rule.lower_at_keyword}',
                            page_selector_type)]
                        page_rules.append((margin_rule, selector_list, declarations))

        elif rule.type == 'at-rule' and rule.lower_at_keyword == 'font-face':
            ignore_imports = True
            content = tinycss2.parse_blocks_contents(rule.content)
            rule_descriptors = dict(
                preprocess_descriptors('font-face', base_url, content))
            for key in ('src', 'font_family'):
                if key not in rule_descriptors:
                    LOGGER.warning(
                        "Missing %s descriptor in '@font-face' rule at %d:%d",
                        key.replace('_', '-'), rule.source_line, rule.source_column)
                    break
            else:
                if font_config is not None:
                    font_config.add_font_face(rule_descriptors, url_fetcher)

        elif rule.type == 'at-rule' and rule.lower_at_keyword == 'color-profile':
            ignore_imports = True

            if (name := parse_color_profile_name(rule.prelude)) is None:
                LOGGER.warning(
                    'Invalid color profile name %r, the whole '
                    '@color-profile rule was ignored at %d:%d.',
                    tinycss2.serialize(rule.prelude), rule.source_line,
                    rule.source_column)
                continue

            content = tinycss2.parse_blocks_contents(rule.content)
            rule_descriptors = preprocess_descriptors(
                'color-profile', base_url, content)

            descriptors = {
                'src': None,
                'rendering-intent': 'relative-colorimetric',
                'components': None,
            }
            for descriptor_name, descriptor_value in rule_descriptors:
                if descriptor_name in descriptors:
                    descriptors[descriptor_name] = descriptor_value
                else:
                    LOGGER.warning(
                        'Unknown descriptor %r for profile named %r at %d:%d.',
                        descriptor_name, tinycss2.serialize(rule.prelude),
                        rule.source_line, rule.source_column)

            if descriptors['src'] is None:
                LOGGER.warning(
                    'No source for profile named %r, the whole '
                    '@color-profile rule was ignored at %d:%d.',
                    tinycss2.serialize(rule.prelude), rule.source_line,
                    rule.source_column)
                continue

            with fetch(url_fetcher, descriptors['src'][1]) as response:
                try:
                    color_profile = ColorProfile(response, descriptors)
                except BaseException:
                    LOGGER.warning(
                        'Invalid profile file for profile named %r, the whole '
                        '@color-profile rule was ignored at %d:%d.',
                        tinycss2.serialize(rule.prelude), rule.source_line,
                        rule.source_column)
                    continue
                else:
                    color_profiles[name] = color_profile

        elif rule.type == 'at-rule' and rule.lower_at_keyword == 'counter-style':
            name = counters.parse_counter_style_name(rule.prelude, counter_style)
            if name is None:
                LOGGER.warning(
                    'Invalid counter style name %r, the whole '
                    '@counter-style rule was ignored at %d:%d.',
                    tinycss2.serialize(rule.prelude), rule.source_line,
                    rule.source_column)
                continue

            ignore_imports = True
            content = tinycss2.parse_blocks_contents(rule.content)
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
                            name, rule.source_line, rule.source_column, system[1])
                        continue
                elif system[1] in ('alphabetic', 'numeric'):
                    if len(counter['symbols'] or []) < 2:
                        LOGGER.warning(
                            'In counter style %r at %d:%d, '
                            'counter style %r needs at least two symbols',
                            name, rule.source_line, rule.source_column, system[1])
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

        elif rule.type == 'at-rule' and rule.lower_at_keyword == 'layer':
            new_layers = []
            prelude = remove_whitespace(rule.prelude)
            comma_separated_tokens = split_on_comma(prelude) if prelude else ()
            for tokens in comma_separated_tokens:
                if new_layer := _parse_layer(tokens):
                    if layer is not None:
                        new_layer = f'{layer}.{new_layer}'
                    new_layers.append(new_layer)
                else:
                    new_layers = None
                    break
            if new_layers is None:
                LOGGER.warning(
                    'Unsupported @layer selector %r, '
                    'the whole @layer rule was ignored at %d:%d.',
                    tinycss2.serialize(rule.prelude),
                    rule.source_line, rule.source_column)
                continue
            elif len(new_layers) > 1:
                if rule.content:
                    LOGGER.warning(
                        '@layer rule with multiple layer names, '
                        'the whole @layer rule was ignored at %d:%d.',
                        rule.source_line, rule.source_column)
                    continue
                for new_layer in new_layers:
                    _add_layer(new_layer, layers)
                continue

            if new_layers:
                new_layer, = new_layers
            else:
                new_layer = f'@anonymous{len(layers)}'
                if layer is not None:
                    new_layer = f'{layer}.{new_layer}'
            _add_layer(new_layer, layers)

            if rule.content is None:
                continue
            content_rules = tinycss2.parse_rule_list(rule.content)
            preprocess_stylesheet(
                device_media_type, base_url, content_rules, url_fetcher, matcher,
                page_rules, layers, font_config, counter_style, color_profiles,
                ignore_imports=True, layer=new_layer)

        else:
            LOGGER.warning(
                "Unknown rule %s at %d:%d",
                rule, rule.source_line, rule.source_column)


def get_all_computed_styles(html, user_stylesheets=None, presentational_hints=False,
                            font_config=None, counter_style=None, color_profiles=None,
                            page_rules=None, layers=None, target_collector=None,
                            forms=False):
    """Compute all the computed styles of all elements in ``html`` document.

    Do everything from finding author stylesheets to parsing and applying them.

    Return a ``style_for`` function that takes an element and an optional
    pseudo-element type, and return a style dict object.

    """
    # List stylesheets. Order here is not important ('origin' is).
    sheets = []
    if counter_style is None:
        counter_style = counters.CounterStyle()
    if font_config is None:
        font_config = FontConfiguration()
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
            html.base_url, font_config, counter_style, color_profiles, page_rules,
            layers):
        sheets.append((sheet, 'author', None))
    for sheet in (user_stylesheets or []):
        sheets.append((sheet, 'user', None))

    return StyleFor(html, sheets, presentational_hints, font_config, target_collector)
