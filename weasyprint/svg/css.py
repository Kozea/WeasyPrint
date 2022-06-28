"""Apply CSS to SVG documents."""

from urllib.parse import urljoin

import cssselect2
import tinycss2

from ..logger import LOGGER
from .utils import parse_url


def find_stylesheets_rules(tree, stylesheet_rules, url):
    """Find rules among stylesheet rules and imports."""
    for rule in stylesheet_rules:
        if rule.type == 'at-rule':
            if rule.lower_at_keyword == 'import' and rule.content is None:
                # TODO: support media types in @import
                url_token = tinycss2.parse_one_component_value(rule.prelude)
                if url_token.type not in ('string', 'url'):
                    continue
                css_url = parse_url(urljoin(url, url_token.value))
                stylesheet = tinycss2.parse_stylesheet(
                    tree.fetch_url(css_url, 'text/css').decode())
                url = css_url.geturl()
                yield from find_stylesheets_rules(tree, stylesheet, url)
            # TODO: support media types
            # if rule.lower_at_keyword == 'media':
        elif rule.type == 'qualified-rule':
            yield rule
        # TODO: warn on error
        # if rule.type == 'error':


def parse_declarations(input):
    """Parse declarations in a given rule content."""
    normal_declarations = []
    important_declarations = []
    for declaration in tinycss2.parse_declaration_list(input):
        # TODO: warn on error
        # if declaration.type == 'error':
        if (declaration.type == 'declaration' and
                not declaration.name.startswith('-')):
            # Serializing perfectly good tokens just to re-parse them later :(
            value = tinycss2.serialize(declaration.value).strip()
            declarations = (
                important_declarations if declaration.important
                else normal_declarations)
            declarations.append((declaration.lower_name, value))
    return normal_declarations, important_declarations


def parse_stylesheets(tree, url):
    """Find stylesheets and return rule matchers in given tree."""
    normal_matcher = cssselect2.Matcher()
    important_matcher = cssselect2.Matcher()

    # Find stylesheets
    # TODO: support contentStyleType on <svg>
    stylesheets = []
    for element in tree.etree_element.iter():
        # https://www.w3.org/TR/SVG/styling.html#StyleElement
        if (element.tag == '{http://www.w3.org/2000/svg}style' and
                element.get('type', 'text/css') == 'text/css' and
                element.text):
            # TODO: pass href for relative URLs
            # TODO: support media types
            # TODO: what if <style> has children elements?
            stylesheets.append(tinycss2.parse_stylesheet(
                element.text, skip_comments=True, skip_whitespace=True))

    # Parse rules and fill matchers
    for stylesheet in stylesheets:
        for rule in find_stylesheets_rules(tree, stylesheet, url):
            normal_declarations, important_declarations = parse_declarations(
                rule.content)
            try:
                selectors = cssselect2.compile_selector_list(rule.prelude)
            except cssselect2.parser.SelectorError as exception:
                LOGGER.warning(
                    'Failed to apply CSS rule in SVG rule: %s', exception)
                break
            for selector in selectors:
                if (selector.pseudo_element is None and
                        not selector.never_matches):
                    if normal_declarations:
                        normal_matcher.add_selector(
                            selector, normal_declarations)
                    if important_declarations:
                        important_matcher.add_selector(
                            selector, important_declarations)

    return normal_matcher, important_matcher
