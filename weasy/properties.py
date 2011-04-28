"""
SHORTHANDS is a dict of property_name: expander_function pairs for all known
shorthand properties. For example, `margin` is a shorthand for all of
margin-top, margin-right, margin-bottom and margin-left.
Expander functions take a Property and yield expanded Property objects.
"""

from cssutils.css import Property


def four_sides_lengths(property):
    """
    Expand properties that set a dimension for each of the four sides of a box.
    """
    values = list(property.propertyValue)
    # Make sure we have 4 values
    if len(values) == 1:
        values *= 4
    elif len(values) == 2:
        values *= 2 # (bottom, left) defaults to (top, right) 
    elif len(values) == 3:
        values.append(values[1]) # left defaults to right
    elif len(values) != 4:
        raise ValueError('Invalid number of value components for %s: %s'
            % (property.name, property.value))
    for suffix, value in zip(('-top', '-right', '-bottom', '-left'), values):
        yield Property(name=property.name + suffix, value=value.cssText,
                       priority=property.priority)

SHORTHANDS = {
    'margin': four_sides_lengths,
    'padding': four_sides_lengths,
    'border-width': four_sides_lengths,
}
