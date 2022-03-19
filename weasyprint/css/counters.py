"""Implement counter styles.

These are defined in CSS Counter Styles Level 3:
https://www.w3.org/TR/css-counter-styles-3/#counter-style-system

"""

from math import inf

from .utils import remove_whitespace


def symbol(string_or_url):
    """Create a string from a symbol."""
    # TODO: this function should handle images too, and return something else
    # than strings.
    type_, value = string_or_url
    if type_ == 'string':
        return value
    return ''


def parse_counter_style_name(tokens, counter_style):
    tokens = remove_whitespace(tokens)
    if len(tokens) == 1:
        token, = tokens
        if token.type == 'ident':
            if token.lower_value in ('decimal', 'disc'):
                if token.lower_value not in counter_style:
                    return token.value
            elif token.lower_value != 'none':
                return token.value


class CounterStyle(dict):
    """Counter styles dictionary.

    Keep a list of counter styles defined by ``@counter-style`` rules, indexed
    by their names.

    See https://www.w3.org/TR/css-counter-styles-3/.

    """
    def resolve_counter(self, counter_name, previous_types=None):
        if counter_name[0] in ('symbols()', 'string'):
            counter_type, arguments = counter_name
            if counter_type == 'string':
                system = (None, 'cyclic', None)
                symbols = (('string', arguments),)
                suffix = ('string', '')
            elif counter_type == 'symbols()':
                system = (
                    None, arguments[0], 1 if arguments[0] == 'fixed' else None)
                symbols = tuple(
                    ('string', argument) for argument in arguments[1:])
                suffix = ('string', ' ')
            return {
                'system': system,
                'negative': (('string', '-'), ('string', '')),
                'prefix': ('string', ''),
                'suffix': suffix,
                'range': 'auto',
                'pad': (0, ''),
                'fallback': 'decimal',
                'symbols': symbols,
                'additive_symbols': (),
            }
        elif counter_name in self:
            # Avoid circular fallbacks
            if previous_types is None:
                previous_types = []
            elif counter_name in previous_types:
                return
            previous_types.append(counter_name)

            counter = self[counter_name].copy()
            if counter['system']:
                extends, system, _ = counter['system']
            else:
                extends, system = None, 'symbolic'

            # Handle extends
            while extends:
                if system in self:
                    extended_counter = self[system]
                    counter['system'] = extended_counter['system']
                    previous_types.append(system)
                    if counter['system']:
                        extends, system, _ = counter['system']
                    else:
                        extends, system = None, 'symbolic'
                    if extends and system in previous_types:
                        extends, system = 'extends', 'decimal'
                        continue
                    for name, value in extended_counter.items():
                        if counter[name] is None and value is not None:
                            counter[name] = value
                else:
                    return counter

            return counter

    def render_value(self, counter_value, counter_name=None, counter=None,
                     previous_types=None):
        """Generate the counter representation.

        See https://www.w3.org/TR/css-counter-styles-3/#generate-a-counter

        """
        assert counter or counter_name
        counter = counter or self.resolve_counter(counter_name, previous_types)
        if counter is None:
            if 'decimal' in self:
                return self.render_value(counter_value, 'decimal')
            else:
                # Could happen if the UA stylesheet is not used
                return ''

        if counter['system']:
            extends, system, fixed_number = counter['system']
        else:
            extends, system, fixed_number = None, 'symbolic', None

        # Avoid circular fallbacks
        if previous_types is None:
            previous_types = []
        elif system in previous_types:
            return self.render_value(counter_value, 'decimal')
        previous_types.append(counter_name)

        # Handle extends
        while extends:
            if system in self:
                extended_counter = self[system]
                counter['system'] = extended_counter['system']
                if counter['system']:
                    extends, system, fixed_number = counter['system']
                else:
                    extends, system, fixed_number = None, 'symbolic', None
                if system in previous_types:
                    return self.render_value(counter_value, 'decimal')
                previous_types.append(system)
                for name, value in extended_counter.items():
                    if counter[name] is None and value is not None:
                        counter[name] = value
            else:
                return self.render_value(counter_value, 'decimal')

        # Step 2
        if counter['range'] in ('auto', None):
            min_range, max_range = -inf, inf
            if system in ('alphabetic', 'symbolic'):
                min_range = 1
            elif system == 'additive':
                min_range = 0
            counter_ranges = ((min_range, max_range),)
        else:
            counter_ranges = counter['range']
        for min_range, max_range in counter_ranges:
            if min_range <= counter_value <= max_range:
                break
        else:
            return self.render_value(
                counter_value, counter['fallback'] or 'decimal',
                previous_types=previous_types)

        # Step 3
        initial = None
        is_negative = counter_value < 0
        if is_negative:
            negative_prefix, negative_suffix = (
                symbol(character) for character
                in counter['negative'] or (('string', '-'), ('string', '')))
            use_negative = (
                system in
                ('symbolic', 'alphabetic', 'numeric', 'additive'))
            if use_negative:
                counter_value = abs(counter_value)

        # TODO: instead of using the decimal fallback when we have the wrong
        # number of symbols, we should discard the whole counter. The problem
        # only happens when extending from another style, it is easily refused
        # during validation otherwise.

        if system == 'cyclic':
            length = len(counter['symbols'])
            if length < 1:
                return self.render_value(counter_value, 'decimal')
            index = (counter_value - 1) % length
            initial = symbol(counter['symbols'][index])

        elif system == 'fixed':
            length = len(counter['symbols'])
            if length < 1:
                return self.render_value(counter_value, 'decimal')
            index = counter_value - fixed_number
            if 0 <= index < length:
                initial = symbol(counter['symbols'][index])
            else:
                return self.render_value(
                    counter_value, counter['fallback'] or 'decimal',
                    previous_types=previous_types)

        elif system == 'symbolic':
            length = len(counter['symbols'])
            if length < 1:
                return self.render_value(counter_value, 'decimal')
            index = (counter_value - 1) % length
            repeat = (counter_value - 1) // length + 1
            initial = symbol(counter['symbols'][index]) * repeat

        elif system == 'alphabetic':
            length = len(counter['symbols'])
            if length < 2:
                return self.render_value(counter_value, 'decimal')
            reversed_parts = []
            while counter_value != 0:
                counter_value -= 1
                reversed_parts.append(symbol(
                    counter['symbols'][counter_value % length]))
                counter_value //= length
            initial = ''.join(reversed(reversed_parts))

        elif system == 'numeric':
            if counter_value == 0:
                initial = symbol(counter['symbols'][0])
            else:
                reversed_parts = []
                length = len(counter['symbols'])
                if length < 2:
                    return self.render_value(counter_value, 'decimal')
                counter_value = abs(counter_value)
                while counter_value != 0:
                    reversed_parts.append(symbol(
                        counter['symbols'][counter_value % length]))
                    counter_value //= length
                initial = ''.join(reversed(reversed_parts))

        elif system == 'additive':
            if counter_value == 0:
                for weight, symbol_string in counter['additive_symbols']:
                    if weight == 0:
                        initial = symbol(symbol_string)
            else:
                parts = []
                if len(counter['additive_symbols']) < 1:
                    return self.render_value(counter_value, 'decimal')
                for weight, symbol_string in counter['additive_symbols']:
                    repetitions = counter_value // weight
                    parts.extend([symbol(symbol_string)] * repetitions)
                    counter_value -= weight * repetitions
                    if counter_value == 0:
                        initial = ''.join(parts)
                        break
            if initial is None:
                return self.render_value(
                    counter_value, counter['fallback'] or 'decimal',
                    previous_types=previous_types)

        assert initial is not None

        # Step 4
        pad = counter['pad'] or (0, '')
        pad_difference = pad[0] - len(initial)
        if is_negative and use_negative:
            pad_difference -= len(negative_prefix) + len(negative_suffix)
        if pad_difference > 0:
            initial = pad_difference * symbol(pad[1]) + initial

        # Step 5
        if is_negative and use_negative:
            initial = negative_prefix + initial + negative_suffix

        # Step 6
        return initial

    def render_marker(self, counter_name, counter_value):
        """Generate the content of a ::marker pseudo-element."""
        counter = self.resolve_counter(counter_name)
        if counter is None:
            if 'decimal' in self:
                return self.render_marker('decimal', counter_value)
            else:
                # Could happen if the UA stylesheet is not used
                return ''

        prefix = symbol(counter['prefix'] or ('string', ''))
        suffix = symbol(counter['suffix'] or ('string', '. '))

        value = self.render_value(counter_value, counter_name=counter_name)
        assert value is not None
        return prefix + value + suffix

    def copy(self):
        # Values are dicts but they are never modified, no need to deepcopy
        return CounterStyle(super().copy())
