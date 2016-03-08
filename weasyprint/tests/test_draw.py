# coding: utf-8
"""
    weasyprint.tests.test_draw
    --------------------------

    Test the final, drawn results and compare PNG images pixel per pixel.

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import sys
import os.path
import tempfile
import shutil
import itertools
import functools

import cairocffi as cairo
import pytest

from ..compat import xrange, izip, ints_from_bytes
from ..urls import ensure_url
from ..html import HTML_HANDLERS
from .. import HTML
from .testing_utils import (
    resource_filename, TestHTML, FONTS, assert_no_logs, capture_logs)


# RGBA to native-endian ARGB
as_pixel = (
    lambda x: x[:-1][::-1] + x[-1:]
    if sys.byteorder == 'little' else
    lambda x: x[-1:] + x[:-1])

# Short variable names are OK here
# pylint: disable=C0103

_ = as_pixel(b'\xff\xff\xff\xff')  # white
r = as_pixel(b'\xff\x00\x00\xff')  # red
B = as_pixel(b'\x00\x00\xff\xff')  # blue


def save_pixels_to_png(pixels, width, height, filename):
    """Save raw pixels to a PNG file."""
    cairo.ImageSurface(
        cairo.FORMAT_ARGB32, width, height,
        data=bytearray(pixels), stride=width * 4
    ).write_to_png(filename)


def requires_cairo(version):
    tuple_version = [0, 0, 0]
    for i, number in enumerate(version.split('.')):
        tuple_version[i] = int(number)
    version_number = int(''.join('%02i' % number for number in tuple_version))

    def require_cairo_version(test):
        @functools.wraps(test)
        def decorated_test():
            if cairo.cairo_version() < version_number:
                print('Running cairo %s but this test requires %s+' % (
                    cairo.cairo_version_string(), version))
                pytest.xfail()
            test()
        return decorated_test

    return require_cairo_version


def assert_pixels(name, expected_width, expected_height, expected_pixels,
                  html):
    """Helper testing the size of the image and the pixels values."""
    assert len(expected_pixels) == expected_height
    assert len(expected_pixels[0]) == expected_width * 4
    expected_raw = b''.join(expected_pixels)
    _doc, pixels = html_to_pixels(name, expected_width, expected_height, html)
    assert_pixels_equal(name, expected_width, expected_height, pixels,
                        expected_raw)


def assert_same_rendering(expected_width, expected_height, documents,
                          tolerance=0):
    """
    Render HTML documents to PNG and check that they render the same,
    pixel-per-pixel.

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
    """
    Render HTML documents to PNG and check that no two documents render
    the same.

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
    directory = os.path.join(os.path.dirname(__file__), 'test_results')
    if not os.path.isdir(directory):
        os.mkdir(directory)
    filename = os.path.join(directory, basename + '.png')
    save_pixels_to_png(pixels, width, height, filename)


def html_to_pixels(name, expected_width, expected_height, html):
    """
    Render an HTML document to PNG, checks its size and return pixel data.

    Also return the document to aid debugging.
    """
    document = TestHTML(
        string=html,
        # Dummy filename, but in the right directory.
        base_url=resource_filename('<test>'))
    pixels = document_to_pixels(
        document, name, expected_width, expected_height)
    return document, pixels


def document_to_pixels(document, name, expected_width, expected_height):
    """
    Render an HTML document to PNG, checks its size and return pixel data.
    """
    surface = document.write_image_surface()
    return image_to_pixels(surface, expected_width, expected_height)


def image_to_pixels(surface, width, height):
    assert (surface.get_width(), surface.get_height()) == (width, height)
    # RGB24 is actually the same as ARGB32, with A unused.
    assert surface.get_format() in (cairo.FORMAT_ARGB32, cairo.FORMAT_RGB24)
    pixels = surface.get_data()[:]
    stride = surface.get_stride()
    row_bytes = width * 4
    if stride != row_bytes:
        assert stride > row_bytes
        pixels = b''.join(pixels[i:i + row_bytes]
                          for i in xrange(0, height * stride, stride))
    assert len(pixels) == width * height * 4
    return pixels


def assert_pixels_equal(name, width, height, raw, expected_raw, tolerance=0):
    """
    Take 2 matrices of height by width pixels and assert that they
    are the same.
    """
    if raw != expected_raw:  # pragma: no cover
        for i, (value, expected) in enumerate(izip(
            ints_from_bytes(raw),
            ints_from_bytes(expected_raw)
        )):
            if abs(value - expected) > tolerance:
                write_png(name, raw, width, height)
                write_png(name + '.expected', expected_raw,
                          width, height)
                pixel_n = i // 4
                x = pixel_n // width
                y = pixel_n % width
                i % 4
                pixel = tuple(ints_from_bytes(raw[i:i + 4]))
                expected_pixel = tuple(ints_from_bytes(
                    expected_raw[i:i + 4]))
                assert 0, (
                    'Pixel (%i, %i) in %s: expected rgba%s, got rgba%s'
                    % (x, y, name, expected_pixel, pixel))


@assert_no_logs
def test_canvas_background():
    """Test the background applied on ``<html>`` and/or ``<body>`` tags."""
    assert_pixels('all_blue', 10, 10, (10 * [10 * B]), '''
        <style>
            @page { size: 10px }
            /* body’s background propagates to the whole canvas */
            body { margin: 2px; background: #00f; height: 5px }
        </style>
        <body>
    ''')

    assert_pixels('blocks', 10, 10, [
        r+r+r+r+r+r+r+r+r+r,
        r+r+r+r+r+r+r+r+r+r,
        r+r+B+B+B+B+B+B+r+r,
        r+r+B+B+B+B+B+B+r+r,
        r+r+B+B+B+B+B+B+r+r,
        r+r+B+B+B+B+B+B+r+r,
        r+r+B+B+B+B+B+B+r+r,
        r+r+r+r+r+r+r+r+r+r,
        r+r+r+r+r+r+r+r+r+r,
        r+r+r+r+r+r+r+r+r+r,

    ], '''
        <style>
            @page { size: 10px }
            /* html’s background propagates to the whole canvas */
            html { padding: 1px; background: #f00 }
            /* html has a background, so body’s does not propagate */
            body { margin: 1px; background: #00f; height: 5px }
        </style>
        <body>
    ''')


@assert_no_logs
def test_background_image():
    """Test background images."""
    # pattern.png looks like this:

    #    r+B+B+B,
    #    B+B+B+B,
    #    B+B+B+B,
    #    B+B+B+B,

    for name, css, pixels in [
        ('repeat', 'url(pattern.png)', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+r+B+B+B+r+B+B+B+r+B+_+_,
            _+_+B+B+B+B+B+B+B+B+B+B+_+_,
            _+_+B+B+B+B+B+B+B+B+B+B+_+_,
            _+_+B+B+B+B+B+B+B+B+B+B+_+_,
            _+_+r+B+B+B+r+B+B+B+r+B+_+_,
            _+_+B+B+B+B+B+B+B+B+B+B+_+_,
            _+_+B+B+B+B+B+B+B+B+B+B+_+_,
            _+_+B+B+B+B+B+B+B+B+B+B+_+_,
            _+_+r+B+B+B+r+B+B+B+r+B+_+_,
            _+_+B+B+B+B+B+B+B+B+B+B+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('repeat_x', 'url(pattern.png) repeat-x', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+r+B+B+B+r+B+B+B+r+B+_+_,
            _+_+B+B+B+B+B+B+B+B+B+B+_+_,
            _+_+B+B+B+B+B+B+B+B+B+B+_+_,
            _+_+B+B+B+B+B+B+B+B+B+B+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('repeat_y', 'url(pattern.png) repeat-y', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+r+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+r+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+r+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),

        ('left_top', 'url(pattern.png) no-repeat 0 0%', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+r+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('center_top', 'url(pattern.png) no-repeat 50% 0px', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+r+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('right_top', 'url(pattern.png) no-repeat 6px top', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+r+B+B+B+_+_,
            _+_+_+_+_+_+_+_+B+B+B+B+_+_,
            _+_+_+_+_+_+_+_+B+B+B+B+_+_,
            _+_+_+_+_+_+_+_+B+B+B+B+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('bottom_6_right_0', 'url(pattern.png) no-repeat bottom 6px right 0', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+r+B+B+B+_+_,
            _+_+_+_+_+_+_+_+B+B+B+B+_+_,
            _+_+_+_+_+_+_+_+B+B+B+B+_+_,
            _+_+_+_+_+_+_+_+B+B+B+B+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('left_center', 'url(pattern.png) no-repeat left center', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+r+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('center_left', 'url(pattern.png) no-repeat center left', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+r+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('center_center', 'url(pattern.png) no-repeat 3px 3px', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+r+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('right_center', 'url(pattern.png) no-repeat 100% 50%', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+r+B+B+B+_+_,
            _+_+_+_+_+_+_+_+B+B+B+B+_+_,
            _+_+_+_+_+_+_+_+B+B+B+B+_+_,
            _+_+_+_+_+_+_+_+B+B+B+B+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),

        ('left_bottom', 'url(pattern.png) no-repeat 0% bottom', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+r+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('center_bottom', 'url(pattern.png) no-repeat center 6px', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+r+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('bottom_center', 'url(pattern.png) no-repeat bottom center', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+r+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('right_bottom', 'url(pattern.png) no-repeat 6px 100%', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+r+B+B+B+_+_,
            _+_+_+_+_+_+_+_+B+B+B+B+_+_,
            _+_+_+_+_+_+_+_+B+B+B+B+_+_,
            _+_+_+_+_+_+_+_+B+B+B+B+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),

        ('repeat_x_1px_2px', 'url(pattern.png) repeat-x 1px 2px', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+B+r+B+B+B+r+B+B+B+r+_+_,
            _+_+B+B+B+B+B+B+B+B+B+B+_+_,
            _+_+B+B+B+B+B+B+B+B+B+B+_+_,
            _+_+B+B+B+B+B+B+B+B+B+B+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('repeat_y_local_2px_1px', 'url(pattern.png) repeat-y local 2px 1px', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+B+B+B+B+_+_+_+_+_+_,
            _+_+_+_+r+B+B+B+_+_+_+_+_+_,
            _+_+_+_+B+B+B+B+_+_+_+_+_+_,
            _+_+_+_+B+B+B+B+_+_+_+_+_+_,
            _+_+_+_+B+B+B+B+_+_+_+_+_+_,
            _+_+_+_+r+B+B+B+_+_+_+_+_+_,
            _+_+_+_+B+B+B+B+_+_+_+_+_+_,
            _+_+_+_+B+B+B+B+_+_+_+_+_+_,
            _+_+_+_+B+B+B+B+_+_+_+_+_+_,
            _+_+_+_+r+B+B+B+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),

        ('fixed', 'url(pattern.png) no-repeat fixed', [
            # The image is actually here:
            #######
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,  #
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,  #
            _+_+B+B+_+_+_+_+_+_+_+_+_+_,  #
            _+_+B+B+_+_+_+_+_+_+_+_+_+_,  #
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('fixed_right', 'url(pattern.png) no-repeat fixed right 3px', [
            #                   x x x x
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+r+B+_+_,  # x
            _+_+_+_+_+_+_+_+_+_+B+B+_+_,  # x
            _+_+_+_+_+_+_+_+_+_+B+B+_+_,  # x
            _+_+_+_+_+_+_+_+_+_+B+B+_+_,  # x
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('fixed_center_center', 'url(pattern.png)no-repeat fixed 50%center', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+r+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+B+B+B+B+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('multi_under', '''url(pattern.png) no-repeat,
                           url(pattern.png) no-repeat 2px 1px''', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+r+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+B+B+B+B+_+_+_+_+_+_,
            _+_+B+B+B+B+B+B+_+_+_+_+_+_,
            _+_+B+B+B+B+B+B+_+_+_+_+_+_,
            _+_+_+_+B+B+B+B+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
        ('multi_over', '''url(pattern.png) no-repeat 2px 1px,
                          url(pattern.png) no-repeat''', [
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+r+B+B+B+_+_+_+_+_+_+_+_,
            _+_+B+B+r+B+B+B+_+_+_+_+_+_,
            _+_+B+B+B+B+B+B+_+_+_+_+_+_,
            _+_+B+B+B+B+B+B+_+_+_+_+_+_,
            _+_+_+_+B+B+B+B+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        ]),
    ]:
        assert_pixels('background_' + name, 14, 16, pixels, '''
            <style>
                @page { size: 14px 16px }
                html { background: #fff }
                body { margin: 2px; height: 10px;
                       background: %s }
                p { background: none }
            </style>
            <body>
            <p>&nbsp;
        ''' % (css,))

    # Regression test for https://github.com/Kozea/WeasyPrint/issues/217
    assert_pixels('zero_size_background', 10, 10, [
        _+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 10px }
            html { background: #fff }
            body { background: url(pattern.png);
                   background-size: cover;
                   display: inline-block }
        </style>
        <body>
    ''')


@assert_no_logs
def test_background_origin():
    """Test the background-origin property."""
    def test_value(value, pixels, css=None):
        assert_pixels('background_origin_' + value, 12, 12, pixels, '''
            <style>
                @page { size: 12px }
                html { background: #fff }
                body { margin: 1px; padding: 1px; height: 6px;
                       border: 1px solid  transparent;
                       background: url(pattern.png) bottom right no-repeat;
                       background-origin: %s }
            </style>
            <body>
        ''' % (css or value,))

    test_value('border-box', [
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+r+B+B+B+_,
        _+_+_+_+_+_+_+B+B+B+B+_,
        _+_+_+_+_+_+_+B+B+B+B+_,
        _+_+_+_+_+_+_+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
    ])
    test_value('padding-box', [
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+r+B+B+B+_+_,
        _+_+_+_+_+_+B+B+B+B+_+_,
        _+_+_+_+_+_+B+B+B+B+_+_,
        _+_+_+_+_+_+B+B+B+B+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
    ])
    test_value('content-box', [
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+r+B+B+B+_+_+_,
        _+_+_+_+_+B+B+B+B+_+_+_,
        _+_+_+_+_+B+B+B+B+_+_+_,
        _+_+_+_+_+B+B+B+B+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
    ])

    test_value('border-box_clip', [
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+r+B+_+_+_,
        _+_+_+_+_+_+_+B+B+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
    ], css='border-box; background-clip: content-box')


@assert_no_logs
def test_background_repeat_space():
    """Test for background-repeat: space"""
    assert_pixels('background_repeat_space', 12, 16, [
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+r+B+B+B+_+_+r+B+B+B+_,
        _+B+B+B+B+_+_+B+B+B+B+_,
        _+B+B+B+B+_+_+B+B+B+B+_,
        _+B+B+B+B+_+_+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+r+B+B+B+_+_+r+B+B+B+_,
        _+B+B+B+B+_+_+B+B+B+B+_,
        _+B+B+B+B+_+_+B+B+B+B+_,
        _+B+B+B+B+_+_+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+r+B+B+B+_+_+r+B+B+B+_,
        _+B+B+B+B+_+_+B+B+B+B+_,
        _+B+B+B+B+_+_+B+B+B+B+_,
        _+B+B+B+B+_+_+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 12px 16px }
            html { background: #fff }
            body { margin: 1px; height: 14px;
                   background: url(pattern.png) space; }
        </style>
        <body>
    ''')

    assert_pixels('background_repeat_space', 12, 14, [
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+r+B+B+B+_+_+r+B+B+B+_,
        _+B+B+B+B+_+_+B+B+B+B+_,
        _+B+B+B+B+_+_+B+B+B+B+_,
        _+B+B+B+B+_+_+B+B+B+B+_,
        _+r+B+B+B+_+_+r+B+B+B+_,
        _+B+B+B+B+_+_+B+B+B+B+_,
        _+B+B+B+B+_+_+B+B+B+B+_,
        _+B+B+B+B+_+_+B+B+B+B+_,
        _+r+B+B+B+_+_+r+B+B+B+_,
        _+B+B+B+B+_+_+B+B+B+B+_,
        _+B+B+B+B+_+_+B+B+B+B+_,
        _+B+B+B+B+_+_+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 12px 14px }
            html { background: #fff }
            body { margin: 1px; height: 12px;
                   background: url(pattern.png) space; }
        </style>
        <body>
    ''')

    assert_pixels('background_repeat_space', 12, 13, [
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+r+B+B+B+r+B+B+B+r+B+_,
        _+B+B+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+r+B+B+B+r+B+B+B+r+B+_,
        _+B+B+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 12px 13px }
            html { background: #fff }
            body { margin: 1px; height: 11px;
                   background: url(pattern.png) repeat space; }
        </style>
        <body>
    ''')


@assert_no_logs
def test_background_repeat_round():
    """Test for background-repeat: round"""
    assert_pixels('background_repeat_round', 10, 14, [
        _+_+_+_+_+_+_+_+_+_,
        _+r+r+B+B+B+B+B+B+_,
        _+r+r+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+r+r+B+B+B+B+B+B+_,
        _+r+r+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 10px 14px }
            html { background: #fff }
            body { margin: 1px; height: 12px;
                   image-rendering: optimizeSpeed;
                   background: url(pattern.png) top/6px round repeat; }
        </style>
        <body>
    ''')

    assert_pixels('background_repeat_round', 10, 18, [
        _+_+_+_+_+_+_+_+_+_,
        _+r+r+B+B+B+B+B+B+_,
        _+r+r+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+r+r+B+B+B+B+B+B+_,
        _+r+r+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 10px 18px }
            html { background: #fff }
            body { margin: 1px; height: 16px;
                   image-rendering: optimizeSpeed;
                   background: url(pattern.png) center/auto 8px repeat round; }
        </style>
        <body>
    ''')

    assert_pixels('background_repeat_round', 10, 14, [
        _+_+_+_+_+_+_+_+_+_,
        _+r+r+B+B+B+B+B+B+_,
        _+r+r+B+B+B+B+B+B+_,
        _+r+r+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 10px 14px }
            html { background: #fff }
            body { margin: 1px; height: 12px;
                   image-rendering: optimizeSpeed;
                   background: url(pattern.png) center/6px 9px round; }
        </style>
        <body>
    ''')

    assert_pixels('background_repeat_round', 10, 14, [
        _+_+_+_+_+_+_+_+_+_,
        _+r+B+B+B+r+B+B+B+_,
        _+r+B+B+B+r+B+B+B+_,
        _+r+B+B+B+r+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 10px 14px }
            html { background: #fff }
            body { margin: 1px; height: 12px;
                   image-rendering: optimizeSpeed;
                   background: url(pattern.png) center/5px 9px round; }
        </style>
        <body>
    ''')


@assert_no_logs
def test_background_clip():
    """Test the background-clip property."""
    def test_value(value, pixels):
        assert_pixels('background_clip_' + value, 8, 8, pixels, '''
            <style>
                @page { size: 8px }
                html { background: #fff }
                body { margin: 1px; padding: 1px; height: 2px;
                       border: 1px solid  transparent;
                       background: %s }
            </style>
            <body>
        ''' % (value,))

    test_value('#00f border-box', [
        _+_+_+_+_+_+_+_,
        _+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+_,
        _+_+_+_+_+_+_+_,
    ])
    test_value('#00f padding-box', [
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
    ])
    test_value('#00f content-box', [
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+B+B+_+_+_,
        _+_+_+B+B+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
    ])
    G = as_pixel(b'\x00\xff\x00\xff')  # lime green
    test_value('url(pattern.png) padding-box, #0f0', [
        _+_+_+_+_+_+_+_,
        _+G+G+G+G+G+G+_,
        _+G+r+B+B+B+G+_,
        _+G+B+B+B+B+G+_,
        _+G+B+B+B+B+G+_,
        _+G+B+B+B+B+G+_,
        _+G+G+G+G+G+G+_,
        _+_+_+_+_+_+_+_,
    ])


@assert_no_logs
def test_background_size():
    """Test the background-size property."""
    assert_pixels('background_size', 12, 12, [
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+r+r+B+B+B+B+B+B+_,
        _+_+_+r+r+B+B+B+B+B+B+_,
        _+_+_+B+B+B+B+B+B+B+B+_,
        _+_+_+B+B+B+B+B+B+B+B+_,
        _+_+_+B+B+B+B+B+B+B+B+_,
        _+_+_+B+B+B+B+B+B+B+B+_,
        _+_+_+B+B+B+B+B+B+B+B+_,
        _+_+_+B+B+B+B+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 12px }
            html { background: #fff }
            body { margin: 1px; height: 10px;
                   /* Use nearest neighbor algorithm for image resizing: */
                   image-rendering: optimizeSpeed;
                   background: url(pattern.png) no-repeat
                               bottom right / 80% 8px; }
        </style>
        <body>
    ''')

    assert_pixels('background_size_auto', 12, 12, [
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+r+B+B+B+_,
        _+_+_+_+_+_+_+B+B+B+B+_,
        _+_+_+_+_+_+_+B+B+B+B+_,
        _+_+_+_+_+_+_+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 12px }
            html { background: #fff }
            body { margin: 1px; height: 10px;
                   /* Use nearest neighbor algorithm for image resizing: */
                   image-rendering: optimizeSpeed;
                   background: url(pattern.png) bottom right/auto no-repeat }
        </style>
        <body>
    ''')

    assert_pixels('background_size_contain', 14, 10, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+r+r+B+B+B+B+B+B+_+_+_+_+_,
        _+r+r+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 14px 10px }
            html { background: #fff }
            body { margin: 1px; height: 8px;
                   /* Use nearest neighbor algorithm for image resizing: */
                   image-rendering: optimizeSpeed;
                   background: url(pattern.png) no-repeat;
                   background-size: contain }
        </style>
        <body>
    ''')

    assert_pixels('background_size_mixed', 14, 10, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+r+r+B+B+B+B+B+B+_+_+_+_+_,
        _+r+r+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 14px 10px }
            html { background: #fff }
            body { margin: 1px; height: 8px;
                   /* Use nearest neighbor algorithm for image resizing: */
                   image-rendering: optimizeSpeed;
                   background: url(pattern.png) no-repeat left / auto 8px;
                   clip: auto; /* no-op to cover more validation */ }
        </style>
        <body>
    ''')

    assert_pixels('background_size_double', 14, 10, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+r+r+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 14px 10px }
            html { background: #fff }
            body { margin: 1px; height: 8px;
                   /* Use nearest neighbor algorithm for image resizing: */
                   image-rendering: optimizeSpeed;
                   background: url(pattern.png) no-repeat 0 0 / 8px 4px;
                   clip: auto; /* no-op to cover more validation */ }
        </style>
        <body>
    ''')

    assert_pixels('background_size_cover', 14, 10, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+r+r+r+B+B+B+B+B+B+B+B+B+_,
        _+r+r+r+B+B+B+B+B+B+B+B+B+_,
        _+r+r+r+B+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 14px 10px }
            html { background: #fff }
            body { margin: 1px; height: 8px;
                   /* Use nearest neighbor algorithm for image resizing: */
                   image-rendering: optimizeSpeed;
                   background: url(pattern.png) no-repeat right 0/cover }
        </style>
        <body>
    ''')


@assert_no_logs
def test_list_style_image():
    """Test images as list markers."""
    for position, pixels in [
        ('outside',
         #  ++++++++++++++      ++++  <li> horizontal margins: 7px 2px
         #                ######      <li> width: 12 - 7 - 2 = 3px
         #              --            list marker margin: 0.5em = 2px
         #      ********              list marker image is 4px wide
         [
            _+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_,
            _+_+r+B+B+B+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_,
            _+_+B+B+B+B+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_,
         ]),
        ('inside',
         #  ++++++++++++++      ++++  <li> horizontal margins: 7px 2px
         #                ######      <li> width: 12 - 7 - 2 = 3px
         #                ********    list marker image is 4px wide: overflow
         [
            _+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+r+B+B+B+_,
            _+_+_+_+_+_+_+B+B+B+B+_,
            _+_+_+_+_+_+_+B+B+B+B+_,
            _+_+_+_+_+_+_+B+B+B+B+_,
            _+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_,
            _+_+_+_+_+_+_+_+_+_+_+_,
         ])
    ]:
        assert_pixels('list_style_image_' + position, 12, 10, pixels, '''
            <style>
                @page { size: 12px 10px }
                body { margin: 0; background: white; font-family: %s }
                ul { margin: 2px 2px 0 7px; list-style: url(pattern.png) %s;
                     font-size: 2px }
            </style>
            <ul><li></li></ul>
        ''' % (FONTS, position))

    assert_pixels('list_style_none', 10, 10, [
        _+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 10px }
            body { margin: 0; background: white; font-family: %s }
            ul { margin: 0 0 0 5px; list-style: none; font-size: 2px; }
        </style>
        <ul><li>
    ''' % (FONTS,))


@assert_no_logs
def test_images():
    """Test images sizes, positions and pixels."""
    centered_image = [
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+r+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
    ]
    # JPG is lossy...
    b = as_pixel(b'\x00\x00\xfe\xff')
    blue_image = [
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+b+b+b+b+_+_,
        _+_+b+b+b+b+_+_,
        _+_+b+b+b+b+_+_,
        _+_+b+b+b+b+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
    ]
    no_image = [
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
    ]
    for filename, image in [
            ('pattern.svg', centered_image),
            ('pattern.png', centered_image),
            ('pattern.palette.png', centered_image),
            ('pattern.gif', centered_image),
            ('blue.jpg', blue_image)]:
        assert_pixels('inline_image_' + filename, 8, 8, image, '''
            <style>
                @page { size: 8px }
                body { margin: 2px 0 0 2px; background: #fff; font-size: 0 }
            </style>
            <div><img src="%s"></div>
        ''' % filename)
    assert_pixels('block_image', 8, 8, centered_image, '''
        <style>
            @page { size: 8px }
            body { margin: 0; background: #fff; font-size: 0 }
            img { display: block; margin: 2px auto 0 }
        </style>
        <div><img src="pattern.png"></div>
    ''')
    with capture_logs() as logs:
        assert_pixels('image_not_found', 8, 8, no_image, '''
            <style>
                @page { size: 8px }
                body { margin: 0; background: #fff; font-size: 0 }
                img { display: block; margin: 2px auto 0 }
            </style>
            <div><img src="inexistent1.png" alt=""></div>
        ''')
    assert len(logs) == 1
    assert 'WARNING: Failed to load image' in logs[0]
    assert 'inexistent1.png' in logs[0]
    assert_pixels('image_no_src', 8, 8, no_image, '''
        <style>
            @page { size: 8px }
            body { margin: 0; background: #fff; font-size: 0 }
            img { display: block; margin: 2px auto 0 }
        </style>
        <div><img alt=""></div>
    ''')
    with capture_logs() as logs:
        assert_same_rendering(200, 30, [
            (name, '''
                <style>
                    @page { size: 200px 30px }
                    body { margin: 0; background: #fff; font-size: 0 }
                </style>
                <div>%s</div>
            ''' % html)
            for name, html in [
                ('image_alt_text_reference', 'Hello, world!'),
                ('image_alt_text_not_found',
                    '<img src="inexistent2.png" alt="Hello, world!">'),
                ('image_alt_text_no_src',
                    '<img alt="Hello, world!">'),
                ('image_svg_no_intrinsic_size',
                    '''<img src="data:image/svg+xml,<svg></svg>"
                            alt="Hello, world!">'''),
            ]
        ])
    assert len(logs) == 1
    assert 'WARNING: Failed to load image' in logs[0]
    assert 'inexistent2.png' in logs[0]

    assert_pixels('image_0x1', 8, 8, no_image, '''
        <style>
            @page { size: 8px }
            body { margin: 2px; background: #fff; font-size: 0 }
        </style>
        <div><img src="pattern.png" alt="not shown"
                  style="width: 0; height: 1px"></div>
    ''')
    assert_pixels('image_1x0', 8, 8, no_image, '''
        <style>
            @page { size: 8px }
            body { margin: 2px; background: #fff; font-size: 0 }
        </style>
        <div><img src="pattern.png" alt="not shown"
                  style="width: 1px; height: 0"></div>
    ''')
    assert_pixels('image_0x0', 8, 8, no_image, '''
        <style>
            @page { size: 8px }
            body { margin: 2px; background: #fff; font-size: 0 }
        </style>
        <div><img src="pattern.png" alt="not shown"
                  style="width: 0; height: 0"></div>
    ''')

    page_break = [
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+r+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,

        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,

        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+r+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
    ]
    assert_pixels('image_page_break', 8, 3 * 8, page_break, '''
        <style>
            @page { size: 8px; margin: 2px; background: #fff }
            body { font-size: 0 }
        </style>
        <div><img src="pattern.png"></div>
        <div style="page-break-before: right"><img src="pattern.png"></div>
    ''')

    # Regression test: padding used to be ignored on images
    assert_pixels('image_with_padding', 8, 8, centered_image, '''
        <style>
            @page { size: 8px; background: #fff }
            body { font-size: 0 }
        </style>
        <div style="line-height: 1px">
            <img src=pattern.png style="padding: 2px 0 0 2px">
        </div>
    ''')

    # Regression test: this used to cause an exception
    assert_pixels('image_in_inline_block', 8, 8, centered_image, '''
        <style>
            @page { size: 8px }
            body { margin: 2px 0 0 2px; background: #fff; font-size: 0 }
        </style>
        <div style="display: inline-block">
            <p><img src=pattern.png></p>
        </div>
    ''')

    # The same image is used in a repeating background,
    # then in a non-repating <img>.
    # If Pattern objects are shared carelessly, the image will be repeated.
    assert_pixels('image_shared_pattern', 12, 12, [
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+b+b+b+b+b+b+b+b+_+_,
        _+_+b+b+b+b+b+b+b+b+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+b+b+b+b+_+_+_+_+_+_,
        _+_+b+b+b+b+_+_+_+_+_+_,
        _+_+b+b+b+b+_+_+_+_+_+_,
        _+_+b+b+b+b+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 12px }
            body { margin: 2px; background: #fff; font-size: 0 }
        </style>
        <div style="background: url(blue.jpg);
                    height: 2px; margin-bottom: 1px"></div>
        <img src=blue.jpg>
    ''')


def test_image_resolution():
    assert_same_rendering(20, 20, [
        ('image_resolution_ref', '''
            <style>@page { size: 20px; margin: 2px; background: #fff }</style>
            <div style="font-size: 0">
                <img src="pattern.png" style="width: 8px"></div>
        '''),
        ('image_resolution_img', '''
            <style>@page { size: 20px; margin: 2px; background: #fff }</style>
            <div style="image-resolution: .5dppx; font-size: 0">
                <img src="pattern.png"></div>
        '''),
        ('image_resolution_content', '''
            <style>@page { size: 20px; margin: 2px; background: #fff }
                   div::before { content: url(pattern.png) }
            </style>
            <div style="image-resolution: .5dppx; font-size: 0"></div>
        '''),
        ('image_resolution_background', '''
            <style>@page { size: 20px; margin: 2px; background: #fff }
            </style>
            <div style="height: 16px; image-resolution: .5dppx;
                        background: url(pattern.png) no-repeat"></div>
        '''),
    ])


@assert_no_logs
def test_visibility():
    source = '''
        <style>
            @page { size: 12px 7px }
            body { background: #fff; font: 1px/1 serif }
            img { margin: 1px 0 0 1px; }
            %(extra_css)s
        </style>
        <div>
            <img src="pattern.png">
            <span><img src="pattern.png"></span>
        </div>
    '''
    assert_pixels('visibility_reference', 12, 7, [
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+r+B+B+B+_+r+B+B+B+_+_,
        _+B+B+B+B+_+B+B+B+B+_+_,
        _+B+B+B+B+_+B+B+B+B+_+_,
        _+B+B+B+B+_+B+B+B+B+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
    ], source % {'extra_css': ''})

    assert_pixels('visibility_hidden', 12, 7, [
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
    ], source % {'extra_css': 'div { visibility: hidden }'})

    assert_pixels('visibility_mixed', 12, 7, [
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+r+B+B+B+_+_,
        _+_+_+_+_+_+B+B+B+B+_+_,
        _+_+_+_+_+_+B+B+B+B+_+_,
        _+_+_+_+_+_+B+B+B+B+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
    ], source % {'extra_css': '''div { visibility: hidden }
                                 span { visibility: visible } '''})


@assert_no_logs
@requires_cairo('1.12')
def test_tables():
    # TODO: refactor colspan/rowspan into CSS:
    # td, th { column-span: attr(colspan integer) }
    HTML_HANDLERS['x-td'] = HTML_HANDLERS['td']
    HTML_HANDLERS['x-th'] = HTML_HANDLERS['th']

    source = '''
        <style>
            @page { size: 28px; background: #fff }
            x-table { margin: 1px; padding: 1px; border-spacing: 1px;
                      border: 1px solid transparent }
            x-td { width: 2px; height: 2px; padding: 1px;
                   border: 1px solid transparent }
            %(extra_css)s
        </style>
        <x-table>
            <x-colgroup>
                <x-col></x-col>
                <x-col></x-col>
            </x-colgroup>
            <x-col></x-col>
            <x-tbody>
                <x-tr>
                    <x-td></x-td>
                    <x-td rowspan=2></x-td>
                    <x-td></x-td>
                </x-tr>
                <x-tr>
                    <x-td colspan=2></x-td>
                    <x-td></x-td>
                </x-tr>
            </x-tbody>
            <x-tr>
                <x-td></x-td>
                <x-td></x-td>
            </x-tr>
        </x-table>
    '''
    # rgba(255, 0, 0, 0.5) above #fff
    r = as_pixel(b'\xff\x7f\x7f\xff')
    # r above r above #fff
    R = as_pixel(b'\xff\x3f\x3f\xff')
    # rgba(0, 255, 0, 0.5) above #fff
    g = as_pixel(b'\x7f\xff\x7f\xff')
    # r above B above #fff.
    b = as_pixel(b'\x80\x00\x7f\xff')
    # r above r above B above #fff.
    p = as_pixel(b'\xc0\x00\x3f\xff')

    assert_pixels('table_borders', 28, 28, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+B+_,
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+B+_,
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+B+_,
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+_+_+_+_+r+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+r+R+r+r+r+r+R+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+r+_+_+_+_+_+_+r+_+_+_+_+R+_+r+_+_+_+_+r+_+_+B+_,
        _+B+_+_+r+_+_+_+_+_+_+r+_+_+_+_+R+_+r+_+_+_+_+r+_+_+B+_,
        _+B+_+_+r+_+_+_+_+_+_+r+_+_+_+_+R+_+r+_+_+_+_+r+_+_+B+_,
        _+B+_+_+r+_+_+_+_+_+_+r+_+_+_+_+R+_+r+_+_+_+_+r+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+r+R+R+R+R+R+R+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ], source % {'extra_css': '''
        x-table { border-color: #00f; table-layout: fixed }
        x-td { border-color: rgba(255, 0, 0, 0.5) }
    '''})

    assert_pixels('table_collapsed_borders', 28, 28, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+_+_+_+_,
        _+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+_+_+_+_,
        _+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+_+_+_+_,
        _+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+_+_+_+_,
        _+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+_+_+_+_,
        _+B+B+r+r+r+r+r+_+_+_+_+r+r+r+r+r+B+B+_+_+_+_+_+_+_+_+_,
        _+B+B+_+_+_+_+_+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+_+_+_+_,
        _+B+B+_+_+_+_+_+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+_+_+_+_,
        _+B+B+_+_+_+_+_+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+_+_+_+_,
        _+B+B+_+_+_+_+_+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+_+_+_+_,
        _+B+B+r+r+r+r+r+r+r+r+r+r+r+r+r+r+B+B+_+_+_+_+_+_+_+_+_,
        _+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+_+_+_+_,
        _+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+_+_+_+_,
        _+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+_+_+_+_,
        _+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ], source % {'extra_css': '''
        x-table { border: 2px solid #00f; table-layout: fixed;
                  border-collapse: collapse }
        x-td { border-color: #ff7f7f }
    '''})

    assert_pixels('table_collapsed_borders_paged', 28, 52, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+_,
        _+g+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+g+_,
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+r+r+r+r+r+_+_+_+_+r+r+r+r+r+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+_+_+_+_+_+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+_+_+_+_+_+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+_+_+_+_+_+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+_+_+_+_+_+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+r+r+r+r+r+r+r+r+r+r+r+r+r+r+B+B+_+_+_+_+_+g+_,
        _+g+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+g+_,
        _+g+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+g+_,
        _+g+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+g+_,
        _+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+_,
        _+g+_+B+B+r+r+r+r+r+r+r+r+r+r+r+r+r+r+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,
        _+g+_+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_+_+_+_+_+g+_,
        _+g+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+g+_,
        _+g+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+g+_,
        _+g+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+g+_,
        _+g+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+g+_,
        _+g+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+g+_,
        _+g+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+g+_,
        _+g+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+g+_,
        _+g+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+g+_,
        _+g+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+g+_,
        _+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+g+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ], source % {'extra_css': '''
        x-table { border: solid #00f; border-width: 8px 2px;
                  table-layout: fixed; border-collapse: collapse }
        x-td { border-color: #ff7f7f }
        @page { size: 28px 26px; margin: 1px;
                border: 1px solid rgba(0, 255, 0, 0.5); }
    '''})

    assert_pixels('table_td_backgrounds', 28, 28, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+r+R+R+R+R+R+R+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+r+R+R+R+R+R+R+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+r+R+R+R+R+R+R+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+r+R+R+R+R+R+R+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+r+R+R+R+R+R+R+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+r+R+R+R+R+R+R+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ], source % {'extra_css': '''
        x-table { border-color: #00f; table-layout: fixed }
        x-td { background: rgba(255, 0, 0, 0.5) }
    '''})

    assert_pixels('table_row_backgrounds', 28, 28, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+b+b+b+b+b+b+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+b+p+p+p+p+p+p+_+b+b+b+b+b+b+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+b+p+p+p+p+p+p+_+b+b+b+b+b+b+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+b+p+p+p+p+p+p+_+b+b+b+b+b+b+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+b+p+p+p+p+p+p+_+b+b+b+b+b+b+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+b+p+p+p+p+p+p+_+b+b+b+b+b+b+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+b+p+p+p+p+p+p+_+b+b+b+b+b+b+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ], source % {'extra_css': '''
        x-table { border-color: #00f; table-layout: fixed }
        x-tbody { background: rgba(0, 0, 255, 1) }
        x-tr { background: rgba(255, 0, 0, 0.5) }
    '''})

    assert_pixels('table_column_backgrounds', 28, 28, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+b+b+b+b+b+b+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+b+p+p+p+p+p+p+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+b+p+p+p+p+p+p+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+b+p+p+p+p+p+p+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+b+p+p+p+p+p+p+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+b+p+p+p+p+p+p+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+b+p+p+p+p+p+p+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ], source % {'extra_css': '''
        x-table { border-color: #00f; table-layout: fixed }
        x-colgroup { background: rgba(0, 0, 255, 1) }
        x-col { background: rgba(255, 0, 0, 0.5) }
    '''})

    assert_pixels('table_borders_and_row_backgrounds', 28, 28, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+b+b+b+b+b+b+_+_+B+_,
        _+B+_+_+b+B+B+B+B+b+_+b+B+B+B+B+b+_+b+B+B+B+B+b+_+_+B+_,
        _+B+_+_+b+B+B+B+B+b+_+b+B+B+B+B+b+_+b+B+B+B+B+b+_+_+B+_,
        _+B+_+_+b+B+B+B+B+b+_+b+B+B+B+B+b+_+b+B+B+B+B+b+_+_+B+_,
        _+B+_+_+b+B+B+B+B+b+_+b+B+B+B+B+b+_+b+B+B+B+B+b+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+_+b+B+B+B+B+b+_+b+b+b+b+b+b+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+b+B+B+B+B+b+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+r+p+b+b+b+b+p+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+r+_+_+_+_+_+_+b+B+B+B+B+p+_+r+_+_+_+_+r+_+_+B+_,
        _+B+_+_+r+_+_+_+_+_+_+b+B+B+B+B+p+_+r+_+_+_+_+r+_+_+B+_,
        _+B+_+_+r+_+_+_+_+_+_+b+B+B+B+B+p+_+r+_+_+_+_+r+_+_+B+_,
        _+B+_+_+r+_+_+_+_+_+_+b+B+B+B+B+p+_+r+_+_+_+_+r+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+r+p+p+p+p+p+p+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ], source % {'extra_css': '''
        x-table { border-color: #00f; table-layout: fixed }
        x-tr:first-child { background: blue }
        x-td { border-color: rgba(255, 0, 0, 0.5) }
    '''})

    assert_pixels('table_borders_and_column_backgrounds', 28, 28, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+_+r+r+r+r+r+r+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+b+B+B+B+B+b+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+B+_,
        _+B+_+_+b+B+B+B+B+b+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+B+_,
        _+B+_+_+b+B+B+B+B+b+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+B+_,
        _+B+_+_+b+B+B+B+B+b+_+r+_+_+_+_+r+_+r+_+_+_+_+r+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+_+r+_+_+_+_+r+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+b+p+b+b+b+b+p+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+b+B+B+B+B+B+B+b+B+B+B+B+p+_+r+_+_+_+_+r+_+_+B+_,
        _+B+_+_+b+B+B+B+B+B+B+b+B+B+B+B+p+_+r+_+_+_+_+r+_+_+B+_,
        _+B+_+_+b+B+B+B+B+B+B+b+B+B+B+B+p+_+r+_+_+_+_+r+_+_+B+_,
        _+B+_+_+b+B+B+B+B+B+B+b+B+B+B+B+p+_+r+_+_+_+_+r+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+b+p+p+p+p+p+p+_+r+r+r+r+r+r+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+b+B+B+B+B+b+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+b+B+B+B+B+b+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+b+B+B+B+B+b+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+b+B+B+B+B+b+_+r+_+_+_+_+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+b+b+b+b+b+b+_+r+r+r+r+r+r+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ], source % {'extra_css': '''
        x-table { border-color: #00f; table-layout: fixed }
        x-col:first-child { background: blue }
        x-td { border-color: rgba(255, 0, 0, 0.5) }
    '''})

    r = as_pixel(b'\xff\x00\x00\xff')
    assert_pixels('collapsed_border_thead', 22, 36, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+B+_,
        _+B+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+B+_,
        _+B+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+_+r+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+r+_+_,
        _+_+r+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+r+_+_,
        _+_+r+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+r+_+_,
        _+_+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+_+_,
        _+_+r+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+r+_+_,
        _+_+r+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+r+_+_,
        _+_+r+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+r+_+_,
        _+_+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+B+_,
        _+B+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+B+_,
        _+B+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+_+r+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+r+_+_,
        _+_+r+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+r+_+_,
        _+_+r+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+r+_+_,
        _+_+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 22px 18px; margin: 1px; background: #fff }
            td { border: 1px red solid; width: 4px; height: 3px; }
        </style>
        <table style="table-layout: fixed; border-collapse: collapse">
            <thead style="border: blue solid; border-width: 2px 3px;
                "><td></td><td></td><td></td></thead>
            <tr><td></td><td></td><td></td></tr>
            <tr><td></td><td></td><td></td></tr>
            <tr><td></td><td></td><td></td></tr>
    ''')

    assert_pixels('collapsed_border_tfoot', 22, 36, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+_+_,
        _+_+r+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+r+_+_,
        _+_+r+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+r+_+_,
        _+_+r+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+r+_+_,
        _+_+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+_+_,
        _+_+r+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+r+_+_,
        _+_+r+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+r+_+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+B+_,
        _+B+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+B+_,
        _+B+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+r+_+_,
        _+_+r+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+r+_+_,
        _+_+r+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+r+_+_,
        _+_+r+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+_+r+_+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+B+_,
        _+B+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+B+_,
        _+B+B+B+_+_+_+_+r+_+_+_+_+r+_+_+_+_+B+B+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 22px 18px; margin: 1px; background: #fff }
            td { border: 1px red solid; width: 4px; height: 3px; }
        </style>
        <table style="table-layout: fixed; margin-left: 1px;
                      border-collapse: collapse">
            <tr><td></td><td></td><td></td></tr>
            <tr><td></td><td></td><td></td></tr>
            <tr><td></td><td></td><td></td></tr>
            <tfoot style="border: blue solid; border-width: 2px 3px;
                "><td></td><td></td><td></td></tfoot>
    ''')

    # Regression test for inline table with collapsed border and alignment
    # rendering borders incorrectly
    # https://github.com/Kozea/WeasyPrint/issues/82
    assert_pixels('inline_text_align', 20, 10, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+r+r+r+r+r+r+r+r+r+r+r+_,
        _+_+_+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+r+_,
        _+_+_+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+r+_,
        _+_+_+_+_+_+_+_+r+_+_+_+_+r+_+_+_+_+r+_,
        _+_+_+_+_+_+_+_+r+r+r+r+r+r+r+r+r+r+r+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 20px 10px; margin: 1px; background: #fff }
            body { text-align: right; font-size: 0 }
            table { display: inline-table; width: 11px }
            td { border: 1px red solid; width: 4px; height: 3px }
        </style>
        <table style="table-layout: fixed; border-collapse: collapse">
            <tr><td></td><td></td></tr>
    ''')


@assert_no_logs
def test_before_after():
    assert_same_rendering(300, 30, [
        ('pseudo_before', '''
            <style>
                @page { size: 300px 30px }
                body { margin: 0; background: #fff }
                a[href]:before { content: '[' attr(href) '] ' }
            </style>
            <p><a href="some url">some content</a></p>
        '''),
        ('pseudo_before_reference', '''
            <style>
                @page { size: 300px 30px }
                body { margin: 0; background: #fff }
            </style>
            <p><a href="another url"><span>[some url] </span>some content</p>
        ''')
    ], tolerance=10)

    assert_same_rendering(500, 30, [
        ('pseudo_quotes', '''
            <style>
                @page { size: 500px 30px }
                body { margin: 0; background: #fff; quotes: '«' '»' '“' '”' }
                q:before { content: open-quote ' '}
                q:after { content: ' ' close-quote }
            </style>
            <p><q>Lorem ipsum <q>dolor</q> sit amet</q></p>
        '''),
        ('pseudo_quotes_reference', '''
            <style>
                @page { size: 500px 30px }
                body { margin: 0; background: #fff }
                q:before, q:after { content: none }
            </style>
            <p><span><span>« </span>Lorem ipsum
                <span><span>“ </span>dolor<span> ”</span></span>
                sit amet<span> »</span></span></p>
        ''')
    ], tolerance=10)

    assert_same_rendering(100, 30, [
        ('pseudo_url', '''
            <style>
                @page { size: 100px 30px }
                body { margin: 0; background: #fff; }
                p:before { content: 'a' url(pattern.png) 'b'}
            </style>
            <p>c</p>
        '''),
        ('pseudo_url_reference', '''
            <style>
                @page { size: 100px 30px }
                body { margin: 0; background: #fff }
            </style>
            <p><span>a<img src="pattern.png" alt="Missing image">b</span>c</p>
        ''')
    ], tolerance=10)


@assert_no_logs
def test_borders(margin='10px', prop='border'):
    """Test the rendering of borders"""
    source = '''
        <style>
            @page { size: 140px 110px }
            html { background: #fff }
            body { width: 100px; height: 70px;
                   margin: %s; %s: 10px %s blue }
        </style>
        <body>
    '''

    # Do not test the exact rendering of earch border style but at least
    # check that they do not do the same.
    assert_different_renderings(140, 110, [
        ('%s_%s' % (prop, border_style), source % (margin, prop, border_style))
        for border_style in [
            'none', 'solid', 'dashed', 'dotted', 'double',
            'inset', 'outset', 'groove', 'ridge',
        ]
    ])

    css_margin = margin
    width = 140
    height = 110
    margin = 10
    border = 10
    solid_pixels = [[_] * width for y in xrange(height)]
    for x in xrange(margin, width - margin):
        for y in itertools.chain(
                range(margin, margin + border),
                range(height - margin - border, height - margin)):
            solid_pixels[y][x] = B
    for y in xrange(margin, height - margin):
        for x in itertools.chain(
                range(margin, margin + border),
                range(width - margin - border, width - margin)):
            solid_pixels[y][x] = B
    solid_pixels = [b''.join(line) for line in solid_pixels]
    assert_pixels(
        prop + '_solid', 140, 110, solid_pixels,
        source % (css_margin, prop, 'solid')
    )


def test_outlines():
    return test_borders(margin='20px', prop='outline')


@assert_no_logs
def test_small_borders():
    # Regression test for ZeroDivisionError on dashed or dotted borders
    # smaller than a dash/dot.
    # https://github.com/Kozea/WeasyPrint/issues/49
    html = '''
        <style>
            @page { size: 50px 50px }
            html { background: #fff }
            body { margin: 5px; height: 0; border: 10px %s blue }
        </style>
        <body>'''
    for style in ['none', 'solid', 'dashed', 'dotted']:
        HTML(string=html % style).write_image_surface()

    # Regression test for ZeroDivisionError on dashed or dotted borders
    # smaller than a dash/dot.
    # https://github.com/Kozea/WeasyPrint/issues/146
    html = '''
        <style>
            @page { size: 50px 50px }
            html { background: #fff }
            body { height: 0; width: 0; border-width: 1px 0; border-style: %s }
        </style>
        <body>'''
    for style in ['none', 'solid', 'dashed', 'dotted']:
        HTML(string=html % style).write_image_surface()


@assert_no_logs
def test_margin_boxes():
    """Test the rendering of margin boxes"""
    _ = as_pixel(b'\xff\xff\xff\xff')  # white
    R = as_pixel(b'\xff\x00\x00\xff')  # red
    G = as_pixel(b'\x00\xff\x00\xff')  # green
    B = as_pixel(b'\x00\x00\xff\xff')  # blue
    g = as_pixel(b'\x00\x80\x00\xff')  # half green
    b = as_pixel(b'\x00\x00\x80\xff')  # half blue
    assert_pixels('margin_boxes', 15, 15, [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+G+G+G+_+_+_+_+_+_+B+B+B+B+_,
        _+G+G+G+_+_+_+_+_+_+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+R+R+R+R+_+_+_+_+_+_,
        _+_+_+_+_+R+R+R+R+_+_+_+_+_+_,
        _+_+_+_+_+R+R+R+R+_+_+_+_+_+_,
        _+_+_+_+_+R+R+R+R+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+b+b+b+_+_+_+_+_+_+g+g+g+g+_,
        _+b+b+b+_+_+_+_+_+_+g+g+g+g+_,
        _+b+b+b+_+_+_+_+_+_+g+g+g+g+_,
        _+b+b+b+_+_+_+_+_+_+g+g+g+g+_,
        _+b+b+b+_+_+_+_+_+_+g+g+g+g+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            html { height: 100% }
            body { background: #f00; height: 100% }
            @page {
                size: 15px;
                margin: 4px 6px 7px 5px;
                background: white;

                @top-left-corner {
                    margin: 1px;
                    content: " ";
                    background: #0f0;
                }
                @top-right-corner {
                    margin: 1px;
                    content: " ";
                    background: #00f;
                }
                @bottom-right-corner {
                    margin: 1px;
                    content: " ";
                    background: #008000;
                }
                @bottom-left-corner {
                    margin: 1px;
                    content: " ";
                    background: #000080;
                }
            }
        </style>
        <body>
    ''')


@assert_no_logs
def test_unicode():
    """Test non-ASCII filenames (URLs)"""
    text = 'I løvë Unicode'
    style = '''
        @page {
            background: #fff;
            size: 200px 50px;
        }
        p { color: blue }
    '''
    _doc, expected_lines = html_to_pixels('unicode_reference', 200, 50, '''
        <style>{0}</style>
        <p><img src="pattern.png"> {1}</p>
    '''.format(style, text))

    temp = tempfile.mkdtemp(prefix=text + '-')
    try:
        stylesheet = os.path.join(temp, 'style.css')
        image = os.path.join(temp, 'pattern.png')
        html = os.path.join(temp, 'doc.html')
        with open(stylesheet, 'wb') as fd:
            fd.write(style.encode('utf8'))
        with open(resource_filename('pattern.png'), 'rb') as fd:
            image_content = fd.read()
        with open(image, 'wb') as fd:
            fd.write(image_content)
        with open(html, 'wb') as fd:
            html_content = '''
                <link rel=stylesheet href="{0}">
                <p><img src="{1}"> {2}</p>
            '''.format(
                ensure_url(stylesheet), ensure_url(image), text
            )
            fd.write(html_content.encode('utf8'))

        # TODO: change this back to actually read from a file
        document = TestHTML(html, encoding='utf8')
        lines = document_to_pixels(document, 'unicode', 200, 50)
        assert_pixels_equal('unicode', 200, 50, lines, expected_lines)
    finally:
        shutil.rmtree(temp)


@assert_no_logs
def test_overflow():
    """Test the overflow property."""
    # See test_images
    assert_pixels('inline_image_overflow', 8, 8, [
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+r+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 8px }
            body { margin: 2px 0 0 2px; background: #fff; font-size:0 }
            div { height: 2px; overflow: hidden }
        </style>
        <div><img src="pattern.png"></div>
    ''')

    # <body> is only 1px high, but its overflow is propageted to the viewport
    # ie. the padding edge of the page box.
    assert_pixels('inline_image_viewport_overflow', 8, 8, [
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+r+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 8px; background: #fff;
                    margin: 2px;
                    padding-bottom: 2px;
                    border-bottom: 1px transparent solid; }
            body { height: 1px; overflow: hidden; font-size: 0 }
        </style>
        <div><img src="pattern.png"></div>
    ''')

    # Assert that the border is not clipped by overflow: hidden
    assert_pixels('border_box_overflow', 8, 8, [
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+_+_+B+_+_,
        _+_+B+_+_+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 8px; background: #fff; margin: 2px; }
            div { width: 2px; height: 2px; overflow: hidden;
                  border: 1px solid blue; }
        </style>
        <div></div>
    ''')


@assert_no_logs
@requires_cairo('1.12')
def test_clip():
    """Test the clip property."""
    num = [0]

    def clip(css, pixels):
        num[0] += 1
        name = 'background_repeat_clipped_%s' % num[0]
        assert_pixels(name, 14, 16, pixels, '''
            <style>
                @page { size: 14px 16px; background: #fff }
                div { margin: 1px; border: 1px green solid;
                      background: url(pattern.png);
                      position: absolute; /* clip only applies on abspos */
                      top: 0; bottom: 2px; left: 0; right: 0;
                      clip: rect(%s); }
            </style>
            <div>
        ''' % (css,))

    g = as_pixel(b'\x00\x80\x00\xff')  # green
    clip('5px, 5px, 9px, auto', [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+r+B+B+B+r+B+g+_,
        _+_+_+_+_+_+B+B+B+B+B+B+g+_,
        _+_+_+_+_+_+B+B+B+B+B+B+g+_,
        _+_+_+_+_+_+B+B+B+B+B+B+g+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ])
    clip('5px, 5px, auto, 10px', [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+r+B+B+B+r+_+_+_,
        _+_+_+_+_+_+B+B+B+B+B+_+_+_,
        _+_+_+_+_+_+B+B+B+B+B+_+_+_,
        _+_+_+_+_+_+B+B+B+B+B+_+_+_,
        _+_+_+_+_+_+r+B+B+B+r+_+_+_,
        _+_+_+_+_+_+B+B+B+B+B+_+_+_,
        _+_+_+_+_+_+g+g+g+g+g+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ])
    clip('5px, auto, 9px, 10px', [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+g+r+B+B+B+r+B+B+B+r+_+_+_,
        _+g+B+B+B+B+B+B+B+B+B+_+_+_,
        _+g+B+B+B+B+B+B+B+B+B+_+_+_,
        _+g+B+B+B+B+B+B+B+B+B+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ])
    clip('auto, 5px, 9px, 10px', [
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+g+g+g+g+g+_+_+_,
        _+_+_+_+_+_+r+B+B+B+r+_+_+_,
        _+_+_+_+_+_+B+B+B+B+B+_+_+_,
        _+_+_+_+_+_+B+B+B+B+B+_+_+_,
        _+_+_+_+_+_+B+B+B+B+B+_+_+_,
        _+_+_+_+_+_+r+B+B+B+r+_+_+_,
        _+_+_+_+_+_+B+B+B+B+B+_+_+_,
        _+_+_+_+_+_+B+B+B+B+B+_+_+_,
        _+_+_+_+_+_+B+B+B+B+B+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_+_+_,
    ])


@assert_no_logs
def test_opacity():
    """Test the opacity property."""
    template = '''
        <style>
            @page { size: 60px 60px }
            body { margin: 0; background: #fff }
            div { background: #000; width: 20px; height: 20px }
        </style>
        %s
    '''
    assert_same_rendering(60, 60, [
        ('opacity_0_reference', template % '''
            <div></div>
        '''),
        ('opacity_0', template % '''
            <div></div>
            <div style="opacity: 0"></div>
        '''),
    ])
    assert_same_rendering(60, 60, [
        ('opacity_color_reference', template % '''
            <div style="background: rgb(102, 102, 102)"></div>
        '''),
        ('opacity_color', template % '''
            <div style="opacity: 0.6"></div>
        '''),
    ])
    assert_same_rendering(60, 60, [
        ('opacity_multiplied_reference', template % '''
            <div style="background: rgb(102, 102, 102)"></div>
        '''),
        ('opacity_multiplied', template % '''
            <div style="opacity: 0.6"></div>
        '''),
        ('opacity_multiplied_2', template % '''
            <div style="background: none; opacity: 0.666666">
                <div style="opacity: 0.9"></div>
            </div>
        '''),  # 0.9 * 0.666666 == 0.6
    ])


@assert_no_logs
def test_current_color():
    """Test inheritance of the currentColor keyword."""
    G = b'\x00\xff\x00\xff'  # lime (light green)
    assert_pixels('background_current_color', 2, 2, [G+G, G+G], '''
        <style>
            @page { size: 2px }
            html, body { height: 100%; margin: 0 }
            html { color: red; background: currentColor }
            body { color: lime; background: inherit }
        </style>
        <body>
    ''')
    assert_pixels('border_current_color', 2, 2, [G+G, G+G], '''
        <style>
            @page { size: 2px }
            html { color: red; border-color: currentColor }
            body { color: lime; border: 1px solid; border-color: inherit;
                   margin: 0 }
        </style>
        <body>
    ''')
    assert_pixels('outline_current_color', 2, 2, [G+G, G+G], '''
        <style>
            @page { size: 2px }
            html { color: red; outline-color: currentColor }
            body { color: lime; outline: 1px solid; outline-color: inherit;
                   margin: 1px }
        </style>
        <body>
    ''')
    assert_pixels('border_collapse_current_color', 2, 2, [G+G, G+G], '''
        <style>
            @page { size: 2px }
            html { color: red; border-color: currentColor; }
            body { margin: 0 }
            table { border-collapse: collapse;
                    color: lime; border: 1px solid; border-color: inherit }
        </style>
        <table><td>
    ''')


@assert_no_logs
def test_2d_transform():
    """Test 2D transformations."""
    assert_pixels('image_rotate90', 8, 8, [
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+B+B+B+r+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 8px; margin: 2px; background: #fff; }
            div { transform: rotate(90deg); font-size: 0 }
        </style>
        <div><img src="pattern.png"></div>
    ''')

    assert_pixels('image_translateX_rotate90', 12, 12, [
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+B+B+B+r+_+_+_,
        _+_+_+_+_+B+B+B+B+_+_+_,
        _+_+_+_+_+B+B+B+B+_+_+_,
        _+_+_+_+_+B+B+B+B+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 12px; margin: 2px; background: #fff; }
            div { transform: translateX(3px) rotate(90deg);
                  font-size: 0; width: 4px }
        </style>
        <div><img src="pattern.png"></div>
    ''')
    # A translateX after the rotation is actually a translateY
    assert_pixels('image_rotate90_translateX', 12, 12, [
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+B+B+B+r+_+_+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 12px; margin: 2px; background: #fff; }
            div { transform: rotate(90deg) translateX(3px);
                  font-size: 0; width: 4px }
        </style>
        <div><img src="pattern.png"></div>
    ''')
    assert_pixels('nested_rotate90_translateX', 12, 12, [
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+B+B+B+r+_+_+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 12px; margin: 2px; background: #fff; }
            div { transform: rotate(90deg); font-size: 0; width: 4px }
            img { transform: translateX(3px) }
        </style>
        <div><img src="pattern.png"></div>
    ''')

    assert_pixels('image_reflection', 8, 8, [
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+B+B+B+r+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 8px; margin: 2px; background: #fff; }
            div { transform: matrix(-1, 0, 0, 1, 0, 0); font-size: 0 }
        </style>
        <div><img src="pattern.png"></div>
    ''')

    assert_pixels('image_translate', 8, 8, [
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+r+B+B+B+_,
        _+_+_+B+B+B+B+_,
        _+_+_+B+B+B+B+_,
        _+_+_+B+B+B+B+_,
    ], '''
        <style>
            @page { size: 8px; margin: 2px; background: #fff; }
            div { transform: translate(1px, 2px); font-size: 0 }
        </style>
        <div><img src="pattern.png"></div>
    ''')

    assert_pixels('image_translate_percentage', 8, 8, [
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+r+B+B+B+_,
        _+_+_+B+B+B+B+_,
        _+_+_+B+B+B+B+_,
        _+_+_+B+B+B+B+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 8px; margin: 2px; background: #fff; }
            div { transform: translate(25%, 0); font-size: 0 }
        </style>
        <div><img src="pattern.png"></div>
    ''')

    assert_pixels('image_translateX', 8, 8, [
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+r+B+B,
        _+_+_+_+_+B+B+B,
        _+_+_+_+_+B+B+B,
        _+_+_+_+_+B+B+B,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 8px; margin: 2px; background: #fff; }
            div { transform: translateX(0.25em); font-size: 12px }
            div div { font-size: 0 }
        </style>
        <div><div><img src="pattern.png"></div></div>
    ''')

    assert_pixels('image_translateY', 8, 8, [
        _+_+_+_+_+_+_+_,
        _+_+r+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+B+B+B+B+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 8px; margin: 2px; background: #fff; }
            div { transform: translateY(-1px); font-size: 0 }
        </style>
        <div><img src="pattern.png"></div>
    ''')

    assert_pixels('image_scale', 10, 10, [
        _+_+_+_+_+_+_+_+_+_,
        _+r+r+B+B+B+B+B+B+_,
        _+r+r+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 10px; margin: 2px; background: #fff; }
            div { transform: scale(2, 2);
                  transform-origin: 1px 1px;
                  image-rendering: optimizeSpeed;
                  font-size: 0 }
        </style>
        <div><img src="pattern.png"></div>
    ''')

    assert_pixels('image_scale12', 10, 10, [
        _+_+_+_+_+_+_+_+_+_,
        _+_+r+B+B+B+_+_+_+_,
        _+_+r+B+B+B+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 10px; margin: 2px; background: #fff; }
            div { transform: scale(1, 2);
                  transform-origin: 1px 1px;
                  image-rendering: optimizeSpeed;
                  font-size: 0 }
        </style>
        <div><img src="pattern.png"></div>
    ''')

    assert_pixels('image_scaleY', 10, 10, [
        _+_+_+_+_+_+_+_+_+_,
        _+_+r+B+B+B+_+_+_+_,
        _+_+r+B+B+B+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_,
        _+_+B+B+B+B+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 10px; margin: 2px; background: #fff; }
            div { transform: scaleY(2);
                  transform-origin: 1px 1px;
                  image-rendering: optimizeSpeed;
                  font-size: 0 }
        </style>
        <div><img src="pattern.png"></div>
    ''')

    assert_pixels('image_scaleX', 10, 10, [
        _+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
        _+r+r+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+B+B+B+B+B+B+B+B+_,
        _+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
        _+_+_+_+_+_+_+_+_+_,
    ], '''
        <style>
            @page { size: 10px; margin: 2px; background: #fff; }
            div { transform: scaleX(2);
                  transform-origin: 1px 1px;
                  image-rendering: optimizeSpeed;
                  font-size: 0 }
        </style>
        <div><img src="pattern.png"></div>
    ''')


@assert_no_logs
@requires_cairo('1.12')
def test_acid2():
    """A local version of http://acid2.acidtests.org/"""
    def render(filename):
        return HTML(resource_filename(filename)).render(enable_hinting=True)

    with capture_logs():
        # This is a copy of http://www.webstandards.org/files/acid2/test.html
        document = render('acid2-test.html')
        intro_page, test_page = document.pages
        # Ignore the intro page: it is not in the reference
        test_image, width, height = document.copy(
            [test_page]).write_image_surface()

    # This is a copy of http://www.webstandards.org/files/acid2/reference.html
    ref_image, ref_width, ref_height = render(
        'acid2-reference.html').write_image_surface()

    assert (width, height) == (ref_width, ref_height)
    assert_pixels_equal(
        'acid2', width, height, image_to_pixels(test_image, width, height),
        image_to_pixels(ref_image, width, height), tolerance=2)


@assert_no_logs
@requires_cairo('1.14')
def test_linear_gradients():
    assert_pixels('linear_gradient', 5, 9, [
        _+_+_+_+_,
        _+_+_+_+_,
        _+_+_+_+_,
        B+B+B+B+B,
        B+B+B+B+B,
        r+r+r+r+r,
        r+r+r+r+r,
        r+r+r+r+r,
        r+r+r+r+r,
    ], '''<style>@page { size: 5px 9px; background: linear-gradient(
        white, white 3px, blue 0, blue 5px, red 0, red
    )''')
    assert_pixels('linear_gradient', 5, 9, [
        _+_+_+_+_,
        _+_+_+_+_,
        _+_+_+_+_,
        B+B+B+B+B,
        B+B+B+B+B,
        r+r+r+r+r,
        r+r+r+r+r,
        r+r+r+r+r,
        r+r+r+r+r,
    ], '''<style>@page { size: 5px 9px; background: linear-gradient(
        white 3px, blue 0, blue 5px, red 0
    )''')
    assert_pixels('linear_gradient', 9, 5, [
        _+_+_+B+B+r+r+r+r,
        _+_+_+B+B+r+r+r+r,
        _+_+_+B+B+r+r+r+r,
        _+_+_+B+B+r+r+r+r,
        _+_+_+B+B+r+r+r+r,
    ], '''<style>@page { size: 9px 5px; background: linear-gradient(
        to right, white 3px, blue 0, blue 5px, red 0
    )''')
    assert_pixels('linear_gradient', 10, 5, [
        B+B+B+B+B+B+r+r+r+r,
        B+B+B+B+B+B+r+r+r+r,
        B+B+B+B+B+B+r+r+r+r,
        B+B+B+B+B+B+r+r+r+r,
        B+B+B+B+B+B+r+r+r+r,
    ], '''<style>@page { size: 10px 5px; background: linear-gradient(
        to right, blue 5px, blue 6px, red 6px, red 9px
    )''')
    assert_pixels('linear_gradient', 10, 5, [
        r+B+r+r+r+B+r+r+r+B,
        r+B+r+r+r+B+r+r+r+B,
        r+B+r+r+r+B+r+r+r+B,
        r+B+r+r+r+B+r+r+r+B,
        r+B+r+r+r+B+r+r+r+B,
    ], '''<style>@page { size: 10px 5px; background: repeating-linear-gradient(
        to right, blue 50%, blue 60%, red 60%, red 90%
    )''')
    assert_pixels('linear_gradient', 9, 5, [
        B+B+B+r+r+r+r+r+r,
        B+B+B+r+r+r+r+r+r,
        B+B+B+r+r+r+r+r+r,
        B+B+B+r+r+r+r+r+r,
        B+B+B+r+r+r+r+r+r,
    ], '''<style>@page { size: 9px 5px; background: linear-gradient(
        to right, blue 3px, blue 3px, red 3px, red 3px
    )''')
    v = as_pixel(b'\x80\x00\x80\xff')  # Average of B and r.
    assert_pixels('linear_gradient', 9, 5, [
        v+v+v+v+v+v+v+v+v,
        v+v+v+v+v+v+v+v+v,
        v+v+v+v+v+v+v+v+v,
        v+v+v+v+v+v+v+v+v,
        v+v+v+v+v+v+v+v+v,
    ], '''<style>@page { size: 9px 5px; background: repeating-linear-gradient(
        to right, blue 3px, blue 3px, red 3px, red 3px
    )''')
    V = as_pixel(b'\xBF\x00\x40\xff')  # Average of 1*B and 3*r.
    assert_pixels('linear_gradient', 9, 5, [
        V+V+V+V+V+V+V+V+V,
        V+V+V+V+V+V+V+V+V,
        V+V+V+V+V+V+V+V+V,
        V+V+V+V+V+V+V+V+V,
        V+V+V+V+V+V+V+V+V,
    ], '''<style>@page { size: 9px 5px; background: repeating-linear-gradient(
            to right, blue 50%, blue 60%, red 60%, red 90%);
        background-size: 1px 1px;
    ''')


@assert_no_logs
def test_radial_gradients():
    assert_pixels('radial_gradient', 6, 6, [
        B+B+B+B+B+B,
        B+B+B+B+B+B,
        B+B+B+B+B+B,
        B+B+B+B+B+B,
        B+B+B+B+B+B,
        B+B+B+B+B+B,
    ], '''<style>@page { size: 6px; background:
        radial-gradient(red -30%, blue -10%)''')
    assert_pixels('radial_gradient', 6, 6, [
        r+r+r+r+r+r,
        r+r+r+r+r+r,
        r+r+r+r+r+r,
        r+r+r+r+r+r,
        r+r+r+r+r+r,
        r+r+r+r+r+r,
    ], '''<style>@page { size: 6px; background:
        radial-gradient(red 110%, blue 130%)''')
    for thin, gradient in ((False, 'red 20%, blue 80%'),
                           (True, 'red 50%, blue 50%')):
        _, pixels = html_to_pixels(
            'radial_gradient_' + gradient, 10, 16,
            '<style>@page { size: 10px 16px; background: radial-gradient(%s)'
            % gradient)

        def pixel(x, y):
            i = (x + 10 * y) * 4
            return pixels[i:i + 4]
        assert pixel(0, 0) == B
        assert pixel(9, 0) == B
        assert pixel(0, 15) == B
        assert pixel(9, 15) == B
        assert pixel(4, 7) == r
        assert pixel(4, 8) == r
        assert pixel(5, 7) == r
        assert pixel(5, 8) == r
        assert (pixel(3, 5) not in (B, r)) ^ thin
        assert (pixel(3, 9) not in (B, r)) ^ thin
        assert (pixel(7, 5) not in (B, r)) ^ thin
        assert (pixel(7, 9) not in (B, r)) ^ thin
