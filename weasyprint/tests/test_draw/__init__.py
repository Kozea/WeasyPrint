"""
    weasyprint.tests.test_draw
    --------------------------

    Test the final, drawn results and compare PNG images pixel per pixel.

"""

import io
import os

from PIL import Image

from ..testing_utils import FakeHTML, resource_filename

PIXELS_BY_CHAR = dict(
    _=b'\xff\xff\xff\xff',  # white
    R=b'\xff\x00\x00\xff',  # red
    B=b'\x00\x00\xff\xff',  # blue
    G=b'\x00\xff\x00\xff',  # lime green
    V=b'\xBF\x00\x40\xff',  # average of 1*B and 3*R.
    S=b'\xff\x3f\x3f\xff',  # R above R above #fff
    r=b'\xff\x00\x00\xff',  # red
    g=b'\x00\x80\x00\xff',  # half green
    b=b'\x00\x00\x80\xff',  # half blue
    v=b'\x80\x00\x80\xff',  # average of B and R.
    h=b'\x40\x00\x40\xff',  # half average of B and R.
    a=b'\x00\x00\xfe\xff',  # JPG is lossy...
    p=b'\xc0\x00\x3f\xff',  # R above R above B above #fff.
)

# NOTE: "r" is not half red on purpose. In the pixel strings it has
# better contrast with "B" than does "R". eg. "rBBBrrBrB" vs "RBBBRRBRB".


def parse_pixels(pixels, pixels_overrides=None):
    chars = dict(PIXELS_BY_CHAR, **(pixels_overrides or {}))
    lines = [line.split('#')[0].strip() for line in pixels.splitlines()]
    return [b''.join(chars[char] for char in line) for line in lines if line]


def assert_pixels(name, expected_width, expected_height, expected_pixels,
                  html):
    """Helper testing the size of the image and the pixels values."""
    if isinstance(expected_pixels, str):
        expected_pixels = parse_pixels(expected_pixels)
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
    output_pixels = []
    for i in range(int(len(pixels) / 4)):
        output_pixels.append(tuple(pixels[4*i:4*i+4]))
    image = Image.new('RGBA', (width, height))
    image.putdata(tuple(output_pixels))
    image.save(filename)


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
    image = Image.open(io.BytesIO(document.write_png()))
    image.putalpha(255)
    return image_to_pixels(image, expected_width, expected_height)


def image_to_pixels(image, width, height):
    assert (image.width, image.height) == (width, height)
    pixels = []
    for pixel in image.getdata():
        pixels.extend(pixel)
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
