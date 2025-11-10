"""CSS functions parsers."""


class Function:
    """CSS function."""
    # See https://drafts.csswg.org/css-values-4/#functional-notation.

    def __init__(self, token):
        """Create Function from function token."""
        if getattr(token, 'type', None) == 'function':
            self.name = token.lower_name
            self.arguments = token.arguments
        else:
            self.name = self.arguments = None

    def split_space(self):
        """Split arguments on spaces."""
        if self.arguments is not None:
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
        if self.arguments is None:
            return

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


def check_attr(token, allowed_type=None):
    function = Function(token)
    if function.name != 'attr':
        return

    parts = function.split_comma(single_tokens=False, trailing=True)
    if len(parts) == 1:
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

    function = Function(token)
    arguments = function.split_comma()
    if function.name == 'counter':
        if len(arguments) not in (1, 2):
            return
    elif function.name == 'counters':
        if len(arguments) not in (2, 3):
            return
    else:
        return

    result = []
    ident = arguments.pop(0)
    if ident.type != 'ident':
        return
    result.append(ident.value)

    if function.name == 'counters':
        string = arguments.pop(0)
        if string.type != 'string':
            return
        result.append(string.value)

    if arguments:
        counter_style = list_style_type((arguments.pop(0),))
        if counter_style is None:
            return
        result.append(counter_style)
    else:
        result.append('decimal')

    return (f'{function.name}()', tuple(result))


def check_content(token):
    function = Function(token)
    if function.name == 'content':
        arguments = function.split_comma()
        if len(arguments) == 0:
            return ('content()', 'text')
        elif len(arguments) == 1:
            ident = arguments.pop(0)
            values = ('text', 'before', 'after', 'first-letter', 'marker')
            if ident.type == 'ident' and ident.lower_value in values:
                return ('content()', ident.lower_value)


def check_string_or_element(string_or_element, token):
    function = Function(token)
    arguments = function.split_comma()
    if function.name == string_or_element and len(arguments) in (1, 2):
        custom_ident = arguments.pop(0)
        if custom_ident.type != 'ident':
            return
        custom_ident = custom_ident.value

        if arguments:
            ident = arguments.pop(0)
            if ident.type != 'ident':
                return
            if ident.lower_value not in ('first', 'start', 'last', 'first-except'):
                return
            ident = ident.lower_value
        else:
            ident = 'first'

        return (f'{string_or_element}()', (custom_ident, ident))


def check_var(token):
    if token.type == '() block':
        return any(check_var(item) for item in token.content)
    function = Function(token)
    if function.name is None:
        return
    arguments = function.split_space()
    if function.name == 'var':
        ident = arguments[0]
        # TODO: we should check authorized tokens
        # https://drafts.csswg.org/css-syntax-3/#typedef-declaration-value
        return ident.type == 'ident' and ident.value.startswith('--')
    return any(check_var(argument) for argument in arguments)


def check_math(token):
    # TODO: validate for real.
    function = Function(token)
    if (name := function.name) is None:
        return
    arguments = function.split_comma(single_tokens=False)
    if name == 'calc':
        return len(arguments) == 1
    elif name in ('min', 'max'):
        return len(arguments) >= 1
    elif name == 'clamp':
        return len(arguments) == 3
    elif name == 'round':
        return 1 <= len(arguments) <= 3
    elif name in ('mod', 'rem'):
        return len(arguments) == 2
    elif name in ('sin', 'cos', 'tan'):
        return len(arguments) == 1
    elif name in ('asin', 'acos', 'atan'):
        return len(arguments) == 1
    elif name == 'atan2':
        return len(arguments) == 2
    elif name == 'pow':
        return len(arguments) == 2
    elif name == 'sqrt':
        return len(arguments) == 1
    elif name == 'hypot':
        return len(arguments) >= 1
    elif name == 'log':
        return 1 <= len(arguments) <= 2
    elif name == 'exp':
        return len(arguments) == 1
    elif name in ('abs', 'sign'):
        return len(arguments) == 1
    arguments = function.split_space()
    return any(check_math(argument) for argument in arguments)
