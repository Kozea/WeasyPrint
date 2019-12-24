"""
    weasyprint.css.counters
    -----------------------

    Implement counter styles.

    These are defined in CSS Counter Styles Level 3:
    https://www.w3.org/TR/css-counter-styles-3/#counter-style-system

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""


class CounterStyle(dict):
    def render_value(self, counter_type, counter_value):
        if counter_type == 'none':
            return ''

        string = ''
        counter = self[counter_type]

        if counter['system'] == 'cyclic':
            string += counter['symbols'][
                (counter_value - 1) % len(counter['symbols'])]
        if counter['system'] == 'fixed':
            if counter_value >= len(counter['symbols']):
                string += self.render(counter['fallback'], counter_value)
            else:
                string += counter['symbols'][
                    (counter_value - 1) % len(counter['symbols'])]
        elif counter['system'] == 'symbolic':
            string += counter['symbols'][
                counter_value % len(counter['symbols'])]
        elif counter['system'] == 'numeric':
            is_negative = counter_value < 0
            if is_negative:
                counter_value = abs(counter_value)
                prefix, suffix = counter['negative']
                reversed_parts = [suffix]
            else:
                reversed_parts = []
            length = len(counter['symbols'])
            counter_value = abs(counter_value)
            while counter_value != 0:
                reversed_parts.append(
                    counter['symbols'][counter_value % length])
                counter_value //= length
            if is_negative:
                reversed_parts.append(prefix)
            string += ''.join(reversed(reversed_parts))
        elif counter['system'] == 'alphabetic':
            length = len(counter['symbols'])
            reversed_parts = []
            while counter_value != 0:
                counter_value -= 1
                reversed_parts.append(
                    counter['symbols'][counter_value % length])
                counter_value //= length
            string += ''.join(reversed(reversed_parts))
        elif counter['system'] == 'additive':
            is_negative = counter_value < 0
            if is_negative:
                counter_value = abs(counter_value)
                prefix, suffix = counter['negative']
                parts = [prefix]
            else:
                parts = []
            for weight, symbol in counter['additive-symbols']:
                repetitions = counter_value // weight
                parts.extend([symbol] * repetitions)
                counter_value -= weight * repetitions
                if counter_value == 0:
                    if is_negative:
                        parts.append(suffix)
                    string += ''.join(parts)
                    break

        return string

    def render(self, counter_type, counter_value):
        if counter_type == 'none':
            return ''

        if counter_type not in self:
            counter_type = 'decimal'

        counter = self[counter_type]
        string = ''

        if counter['prefix']:
            string += counter['prefix']

        string += self.render_value(counter_type, counter_value)

        if counter['suffix']:
            string += counter['suffix']

        return string
