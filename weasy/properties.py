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
    value = property.propertyValue
    if len(value) == 1:
        top = right = bottom = left = value[0]
    elif len(value) == 2:
        top = bottom = value[0]
        right = left = value[1]
    elif len(value) == 3:
        top = value[0]
        right = left = value[1]
        bottom = value[2]
    elif len(value) == 4:
        top = value[0]
        right = value[1]
        bottom = value[2]
        left = value[3]
    else:
        raise ValueError('Invalid number of value components for %s: %s'
            % (property.name, value.cssText))
    for suffix, value in (('-top', top), ('-right', right),
                          ('-bottom', bottom), ('-left', left)):
        yield Property(name=property.name + suffix, value=value.cssText,
                       priority=property.priority)

SHORTHANDS = {
    'margin': four_sides_lengths,
    'padding': four_sides_lengths,
    'border-width': four_sides_lengths,
}
