"""
    weasyprint.css.counters
    -----------------------

    Implement counter styles.

    These are defined in CSS Counter Styles Level 3:
    https://www.w3.org/TR/css-counter-styles-3/#counter-style-system

    :copyright: Copyright 2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""


class CounterStyle(dict):
    def render(self, counter_type, counter_value):
        if counter_type not in self:
            counter_type = 'decimal'
        counter = self[counter_type]
        string = ''

        if counter['prefix']:
            string += counter['prefix']

        if counter['system'] == 'cyclic':
            string += counter['symbols'][
                (counter_value - 1) % len(counter['symbols'])]
        elif counter['system'] == 'numeric':
            string += counter['symbols'][
                counter_value % len(counter['symbols'])]

        if counter['suffix']:
            string += counter['suffix']

        return string
