"""CSS functions parsers."""

from .properties import Dimension
from .units import ANGLE_UNITS, LENGTH_UNITS

ATTR_FALLBACKS = {
    'string': ('string', ''),
    'color': ('ident', 'currentcolor'),
    'url': ('external', 'about:invalid'),
    'integer': ('number', 0),
    'number': ('number', 0),
    '%': ('number', 0),
}
for unit in LENGTH_UNITS:
    ATTR_FALLBACKS[unit] = ('length', Dimension('0', unit))
for unit in ANGLE_UNITS:
    ATTR_FALLBACKS[unit] = ('angle', Dimension('0', unit))


def parse_function(function_token):
    """Parse functional notation.

    Return ``(name, args)`` if the given token is a function with comma- or
    space-separated arguments. Return ``None`` otherwise.

    """
    if function_token.type != 'function':
        return

    content = list(function_token.arguments)
    arguments = []
    last_is_comma = False
    while content:
        token = content.pop(0)
        if token.type in ('whitespace', 'comment'):
            continue
        is_comma = token.type == 'literal' and token.value == ','
        if last_is_comma and is_comma:
            return
        if is_comma:
            last_is_comma = True
        else:
            last_is_comma = False
            if token.type == 'function':
                argument_function = parse_function(token)
                if argument_function is None:
                    return
            arguments.append(token)
    if last_is_comma:
        return
    return function_token.lower_name, arguments


def check_attr(token, allowed_type=None):
    function = parse_function(token)
    if function is None:
        return
    name, args = function
    if name == 'attr' and len(args) in (1, 2, 3):
        if args[0].type != 'ident':
            return
        attr_name = args[0].value
        if len(args) == 1:
            type_or_unit = 'string'
            fallback = ''
        else:
            if args[1].type != 'ident':
                return
            type_or_unit = args[1].value
            if type_or_unit not in ATTR_FALLBACKS:
                return
            if len(args) == 2:
                fallback = ATTR_FALLBACKS[type_or_unit]
            else:
                fallback_type = args[2].type
                if fallback_type == 'string':
                    fallback = args[2].value
                else:
                    # TODO: handle other fallback types
                    return
        if allowed_type in (None, type_or_unit):
            return ('attr()', (attr_name, type_or_unit, fallback))


def check_counter(token, allowed_type=None):
    from .validation.properties import list_style_type

    function = parse_function(token)
    if function is None:
        return
    name, args = function
    arguments = []
    if (name == 'counter' and len(args) in (1, 2)) or (
            name == 'counters' and len(args) in (2, 3)):
        ident = args.pop(0)
        if ident.type != 'ident':
            return
        arguments.append(ident.value)

        if name == 'counters':
            string = args.pop(0)
            if string.type != 'string':
                return
            arguments.append(string.value)

        if args:
            counter_style = list_style_type((args.pop(0),))
            if counter_style is None:
                return
            arguments.append(counter_style)
        else:
            arguments.append('decimal')

        return (f'{name}()', tuple(arguments))


def check_content(token):
    function = parse_function(token)
    if function is None:
        return
    name, args = function
    if name == 'content':
        if len(args) == 0:
            return ('content()', 'text')
        elif len(args) == 1:
            ident = args.pop(0)
            if ident.type == 'ident' and ident.lower_value in (
                    'text', 'before', 'after', 'first-letter', 'marker'):
                return ('content()', ident.lower_value)


def check_string_or_element(string_or_element, token):
    function = parse_function(token)
    if function is None:
        return
    name, args = function
    if name == string_or_element and len(args) in (1, 2):
        custom_ident = args.pop(0)
        if custom_ident.type != 'ident':
            return
        custom_ident = custom_ident.value

        if args:
            ident = args.pop(0)
            if ident.type != 'ident' or ident.lower_value not in (
                    'first', 'start', 'last', 'first-except'):
                return
            ident = ident.lower_value
        else:
            ident = 'first'

        return (f'{string_or_element}()', (custom_ident, ident))


def check_var(token):
    if function := parse_function(token):
        name, args = function
        if name == 'var' and args:
            ident = args.pop(0)
            # TODO: we should check authorized tokens
            # https://drafts.csswg.org/css-syntax-3/#typedef-declaration-value
            return ident.type == 'ident' and ident.value.startswith('--')
        for arg in args:
            if check_var(arg):
                return True
