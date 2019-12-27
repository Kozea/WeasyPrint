"""
    weasyprint.css.counters
    -----------------------

    Implement counter styles.

    These are defined in CSS Counter Styles Level 3:
    https://www.w3.org/TR/css-counter-styles-3/#counter-style-system

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""


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
    """Dictionary storing counter styles defined by @counter-style rules.

    See https://www.w3.org/TR/css-counter-styles-3/

    """
    def render_value(self, counter_type, counter_value):
        """Generate the counter representation.

        See https://www.w3.org/TR/css-counter-styles-3/#generate-a-counter

        """
        # Step 1
        if counter_type not in self:
            if 'decimal' in self:
                return self.render_value('decimal', counter_value)
            else:
                # Could happen if the UA stylesheet is not used
                return ''

        counter = self[counter_type]
        system, fixed_number = counter['system']

        # Step 2
        if counter['range'] == 'auto':
            min_range, max_range = -float('inf'), float('inf')
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
            return self.render_value(counter['fallback'], counter_value)

        # Step 3
        initial = None
        is_negative = counter_value < 0
        if is_negative:
            negative_prefix, negative_suffix = (
                symbol(character) for character in counter['negative'])
            use_negative = (
                system in
                ('symbolic', 'alphabetic', 'numeric', 'additive'))
            if use_negative:
                counter_value = abs(counter_value)

        if system == 'cyclic':
            index = (counter_value - 1) % len(counter['symbols'])
            initial = symbol(counter['symbols'][index])

        elif system == 'fixed':
            index = counter_value - fixed_number
            if 0 <= index < len(counter['symbols']):
                initial = symbol(counter['symbols'][index])
            else:
                return self.render_value(counter['fallback'], counter_value)

        elif system == 'symbolic':
            index = counter_value % len(counter['symbols'])
            initial = symbol(counter['symbols'][index])

        elif system == 'alphabetic':
            length = len(counter['symbols'])
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
                for weight, symbol_string in counter['additive_symbols']:
                    repetitions = counter_value // weight
                    parts.extend([symbol(symbol_string)] * repetitions)
                    counter_value -= weight * repetitions
                    if counter_value == 0:
                        initial = ''.join(parts)
                        break
            if initial is None:
                return self.render_value(counter['fallback'], counter_value)

        assert initial is not None

        # Step 4
        pad_difference = counter['pad'][0] - len(initial)
        if is_negative and use_negative:
            pad_difference -= len(negative_prefix) + len(negative_suffix)
        if pad_difference > 0:
            initial = pad_difference * symbol(counter['pad'][1]) + initial

        # Step 5
        if is_negative and use_negative:
            initial = negative_prefix + initial + negative_suffix

        # Step 6
        return initial

    def render_marker(self, counter_type, counter_value):
        """Generate the content of a ::marker pseudo-element."""
        if counter_type not in self:
            return self.render_marker('decimal', counter_value)

        prefix = symbol(self[counter_type]['prefix'])
        suffix = symbol(self[counter_type]['suffix'])

        value = self.render_value(counter_type, counter_value)
        if value is not None:
            return prefix + value + suffix

        # TODO: print warning, return something else?

    def copy(self):
        return CounterStyle(self)
