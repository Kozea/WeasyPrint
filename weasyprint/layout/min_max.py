"""Decorators handling min- and max- widths and heights."""

import functools


def handle_min_max_width(function):
    """Decorate a function setting used width, handling {min,max}-width."""
    @functools.wraps(function)
    def wrapper(box, *args):
        result = function(box, *args)
        if box.width > box.max_width:
            box.width = box.max_width
            result = function(box, *args)
        if box.width < box.min_width:
            box.width = box.min_width
            result = function(box, *args)
        return result
    wrapper.without_min_max = function
    return wrapper


def handle_min_max_height(function):
    """Decorate a function setting used height, handling {min,max}-height."""
    @functools.wraps(function)
    def wrapper(box, *args):
        result = function(box, *args)
        if box.height > box.max_height:
            box.height = box.max_height
            result = function(box, *args)
        if box.height < box.min_height:
            box.height = box.min_height
            result = function(box, *args)
        return result
    wrapper.without_min_max = function
    return wrapper
