"""
    weasyprint.calc
    -----------------------------

    Resolve percentages into fixed values.

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""


def percentage(value, refer_to):
    """Return the percentage of the reference value, or the value unchanged.

    ``refer_to`` is the length for 100%. If ``refer_to`` is not a number, it
    just replaces percentages.

    """
    if value is None or value == 'auto':
        return value
    elif value.unit == 'px':
        return value.value
    else:
        assert value.unit == '%'
        return refer_to * value.value / 100.
