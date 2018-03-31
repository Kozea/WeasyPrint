"""
    weasyprint.css.functions
    ------------------------

    Validate CSS functions.
    See https://drafts.csswg.org/css-values-3/#functional-notation

    :copyright: Copyright 2011-2018 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from .utils import remove_whitespace


def parse_function(function_token):
    """Parse functional notation.

    Return ``(name, args)`` if the given token is a function with comma- or
    space-separated arguments. Return ``None`` otherwise.

    """
    if not getattr(function_token, 'type', None) == 'function':
        return

    content = list(remove_whitespace(function_token.arguments))
    arguments = []
    last_is_comma = False
    while content:
        token = content.pop(0)
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
    return function_token.lower_name, arguments
