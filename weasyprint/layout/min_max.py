"""
    weasyprint.layout.min_max
    -------------------------

"""

import functools


def handle_min_max_width(function):
    """Decorate a function that sets the used width of a box to handle
    {min,max}-width.
    """
    @functools.wraps(function)
    def wrapper(box, *args):
        computed_margins = box.margin_left, box.margin_right
        result = function(box, *args)
        if box.width > box.max_width:
            box.width = box.max_width
            box.margin_left, box.margin_right = computed_margins
            result = function(box, *args)
        if box.width < box.min_width:
            box.width = box.min_width
            box.margin_left, box.margin_right = computed_margins
            result = function(box, *args)
        return result
    wrapper.without_min_max = function
    return wrapper


def handle_min_max_height(function):
    """Decorate a function that sets the used height of a box to handle
    {min,max}-height.
    """
    @functools.wraps(function)
    def wrapper(box, *args):
        computed_margins = box.margin_top, box.margin_bottom
        result = function(box, *args)
        if box.height > box.max_height:
            box.height = box.max_height
            box.margin_top, box.margin_bottom = computed_margins
            result = function(box, *args)
        if box.height < box.min_height:
            box.height = box.min_height
            box.margin_top, box.margin_bottom = computed_margins
            result = function(box, *args)
        return result
    wrapper.without_min_max = function
    return wrapper
