"""
    weasyprint.tests.test_draw
    --------------------------

    Test the final, drawn results and compare PNG images pixel per pixel.

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import os
import sys

import cairocffi as cairo

from ..testing_utils import FakeHTML, resource_filename

# RGBA to native-endian ARGB
as_pixel = (
    lambda x: x[:-1][::-1] + x[-1:]
    if sys.byteorder == 'little' else
    lambda x: x[-1:] + x[:-1])

_ = as_pixel(b'\xff\xff\xff\xff')  # white
R = as_pixel(b'\xff\x00\x00\xff')  # red
B = as_pixel(b'\x00\x00\xff\xff')  # blue
G = as_pixel(b'\x00\xff\x00\xff')  # lime green
V = as_pixel(b'\xBF\x00\x40\xff')  # Average of 1*B and 3*r.
S = as_pixel(b'\xff\x3f\x3f\xff')  # r above r above #fff
r = as_pixel(b'\xff\x00\x00\xff')  # red
g = as_pixel(b'\x00\x80\x00\xff')  # half green
b = as_pixel(b'\x00\x00\x80\xff')  # half blue
v = as_pixel(b'\x80\x00\x80\xff')  # Average of B and r.
a = as_pixel(b'\x00\x00\xfe\xff')  # JPG is lossy...
p = as_pixel(b'\xc0\x00\x3f\xff')  # r above r above B above #fff.


def assert_pixels(name, expected_width, expected_height, expected_pixels,
                  html):
    """Helper testing the size of the image and the pixels values."""
    assert len(expected_pixels) == expected_height
    assert len(expected_pixels[0]) == expected_width * 4
    expected_raw = b''.join(expected_pixels)
    _doc, pixels = html_to_pixels(name, expected_width, expected_height, html)
    assert_pixels_equal(
        name, expected_width, expected_height, pixels, expected_raw)


def assert_same_rendering(expected_width, expected_height, documents,
                          tolerance=0):
    """Render HTML documents to PNG and check that they render the same.

    Each document is passed as a (name, html_source) tuple.

    """
    pixels_list = []

    for name, html in documents:
        _doc, pixels = html_to_pixels(
            name, expected_width, expected_height, html)
        pixels_list.append((name, pixels))

    _name, reference = pixels_list[0]
    for name, pixels in pixels_list[1:]:
        assert_pixels_equal(name, expected_width, expected_height,
                            reference, pixels, tolerance)


def assert_different_renderings(expected_width, expected_height, documents):
    """Render HTML documents to PNG and check that they don't render the same.

    Each document is passed as a (name, html_source) tuple.

    """
    pixels_list = []

    for name, html in documents:
        _doc, pixels = html_to_pixels(
            name, expected_width, expected_height, html)
        pixels_list.append((name, pixels))

    for i, (name_1, pixels_1) in enumerate(pixels_list):
        for name_2, pixels_2 in pixels_list[i + 1:]:
            if pixels_1 == pixels_2:  # pragma: no cover
                write_png(name_1, pixels_1, expected_width, expected_height)
                # Same as "assert pixels_1 != pixels_2" but the output of
                # the assert hook would be gigantic and useless.
                assert False, '%s and %s are the same' % (name_1, name_2)


def write_png(basename, pixels, width, height):  # pragma: no cover
    """Take a pixel matrix and write a PNG file."""
    directory = os.path.join(os.path.dirname(__file__), 'results')
    if not os.path.isdir(directory):
        os.mkdir(directory)
    filename = os.path.join(directory, basename + '.png')
    cairo.ImageSurface(
        cairo.FORMAT_ARGB32, width, height,
        data=bytearray(pixels), stride=width * 4
    ).write_to_png(filename)


def html_to_pixels(name, expected_width, expected_height, html):
    """Render an HTML document to PNG, checks its size and return pixel data.

    Also return the document to aid debugging.

    """
    document = FakeHTML(
        string=html,
        # Dummy filename, but in the right directory.
        base_url=resource_filename('<test>'))
    pixels = document_to_pixels(
        document, name, expected_width, expected_height)
    return document, pixels


def document_to_pixels(document, name, expected_width, expected_height):
    """Render an HTML document to PNG, check its size and return pixel data."""
    surface = document.write_image_surface()
    return image_to_pixels(surface, expected_width, expected_height)


def image_to_pixels(surface, width, height):
    assert (surface.get_width(), surface.get_height()) == (width, height)
    # RGB24 is actually the same as ARGB32, with A unused.
    assert surface.get_format() in (cairo.FORMAT_ARGB32, cairo.FORMAT_RGB24)
    pixels = surface.get_data()[:]
    assert len(pixels) == width * height * 4
    return pixels


def assert_pixels_equal(name, width, height, raw, expected_raw, tolerance=0):
    """Take 2 matrices of pixels and assert that they are the same."""
    if raw != expected_raw:  # pragma: no cover
        for i, (value, expected) in enumerate(zip(raw, expected_raw)):
            if abs(value - expected) > tolerance:
                write_png(name, raw, width, height)
                write_png(name + '.expected', expected_raw,
                          width, height)
                pixel_n = i // 4
                x = pixel_n // width
                y = pixel_n % width
                i % 4
                pixel = tuple(list(raw[i:i + 4]))
                expected_pixel = tuple(list(
                    expected_raw[i:i + 4]))
                assert 0, (
                    'Pixel (%i, %i) in %s: expected rgba%s, got rgba%s'
                    % (x, y, name, expected_pixel, pixel))
