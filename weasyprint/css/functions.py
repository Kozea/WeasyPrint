"""CSS functions parsers."""

class Function:
    """CSS function."""
    # See https://drafts.csswg.org/css-values-4/#functional-notation.

    def __init__(self, token):
        """Create Function from function token."""
        self.name = token.lower_name
        self.arguments = token.arguments

    def split_space(self):
        """Split arguments on spaces."""
        return [
            argument for argument in self.arguments
            if argument.type not in ('whitespace', 'comment')]

    def split_comma(self, single_tokens=True, trailing=False):
        """Split arguments on commas.

        Spaces in parentheses and after commas are removed.

        If ``single_tokens`` is ``True``, check that only a single token is between
        commas and flatten returned list.

        If ``trailing`` is ``True``, allow a bare comma at the end.

        """
        parts = [[]]
        for token in self.arguments:
            if token.type == 'literal' and token.value == ',':
                parts.append([])
                continue
            if token.type not in ('comment', 'whitespace'):
                parts[-1].append(token)

        if trailing:
            if single_tokens:
                if all(len(part) == 1 for part in parts[:-1]):
                    if len(parts[-1]) in (0, 1):
                        return [part[0] if part else None for part in parts[:-1]]
            elif all(parts[:-1]):
                return parts
        else:
            if single_tokens:
                if all(len(part) == 1 for part in parts):
                    return [part[0] for part in parts]
            elif all(parts):
                return parts
        return []


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
                if parse_function(token) is None:
                    return
            arguments.append(token)
    if last_is_comma:
        return
    return Function(function_token)


def check_attr(token, allowed_type=None):
    if not (function := parse_function(token)) or function.name != 'attr':
        return

    if len(parts := function.split_comma(single_tokens=False, trailing=True)) == 1:
        name_and_type, fallback = parts[0], ''
    elif len(parts) == 2:
        name_and_type, fallback = parts
    else:
        return

    if any(token.type != 'ident' for token in name_and_type):
        return
    # TODO: follow new syntax, see https://drafts.csswg.org/css-values-5/#attr-notation.

    name = name_and_type[0].value
    type_or_unit = name_and_type[1].value if len(name_and_type) == 2 else 'string'
    if allowed_type in (None, type_or_unit):
        return ('attr()', (name, type_or_unit, fallback))


def check_counter(token, allowed_type=None):
    from .validation.properties import list_style_type

    if not (function := parse_function(token)):
        return

    args = function.split_comma()

    if function.name == 'counter':
        if len(args) not in (1, 2):
            return
    elif function.name == 'counters':
        if len(args) not in (2, 3):
            return
    else:
        return

    result = []
    ident = args.pop(0)
    if ident.type != 'ident':
        return
    result.append(ident.value)

    if function.name == 'counters':
        string = args.pop(0)
        if string.type != 'string':
            return
        result.append(string.value)

    if args:
        counter_style = list_style_type((args.pop(0),))
        if counter_style is None:
            return
        result.append(counter_style)
    else:
        result.append('decimal')

    return (f'{function.name}()', tuple(result))


def check_content(token):
    if (function := parse_function(token)) is None:
        return
    args = function.split_comma()
    if function.name == 'content':
        if len(args) == 0:
            return ('content()', 'text')
        elif len(args) == 1:
            ident = args.pop(0)
            values = ('text', 'before', 'after', 'first-letter', 'marker')
            if ident.type == 'ident' and ident.lower_value in values:
                return ('content()', ident.lower_value)


def check_string_or_element(string_or_element, token):
    if (function := parse_function(token)) is None:
        return
    args = function.split_comma()
    if function.name == string_or_element and len(args) in (1, 2):
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
    if not (function := parse_function(token)):
        return
    arguments = function.split_space()
    if function.name == 'var':
        ident = arguments[0]
        # TODO: we should check authorized tokens
        # https://drafts.csswg.org/css-syntax-3/#typedef-declaration-value
        return ident.type == 'ident' and ident.value.startswith('--')
    return any(check_var(argument) for argument in arguments)
