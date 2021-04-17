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
    _=(255, 255, 255),  # white
    R=(255, 0, 0),  # red
    B=(0, 0, 255),  # blue
    G=(0, 255, 0),  # lime green
    V=(191, 0, 64),  # average of 1*B and 3*R.
    S=(255, 63, 63),  # R above R above #fff
    r=(255, 0, 0),  # red
    g=(0, 128, 0),  # half green
    b=(0, 0, 128),  # half blue
    v=(128, 0, 128),  # average of B and R.
    h=(64, 0, 64),  # half average of B and R.
    a=(0, 0, 254),  # JPG is lossy...
    p=(192, 0, 63),  # R above R above B above #fff.
    z=None,
)

# NOTE: "r" is not half red on purpose. In the pixel strings it has
# better contrast with "B" than does "R". eg. "rBBBrrBrB" vs "RBBBRRBRB".


def parse_pixels(pixels, pixels_overrides=None):
    chars = dict(PIXELS_BY_CHAR, **(pixels_overrides or {}))
    lines = (line.split('#')[0].strip() for line in pixels.splitlines())
    return tuple(chars[char] for line in lines if line for char in line)


def assert_pixels(name, expected_width, expected_height, expected_pixels,
                  html):
    """Helper testing the size of the image and the pixels values."""
    if isinstance(expected_pixels, str):
        expected_pixels = parse_pixels(expected_pixels)
    assert len(expected_pixels) == expected_height * expected_width, (
        f'Expected {len(expected_pixels)} pixels, '
        f'got {expected_height * expected_width}')
    pixels = html_to_pixels(name, expected_width, expected_height, html)
    assert_pixels_equal(
        name, expected_width, expected_height, pixels, expected_pixels)


def assert_same_rendering(expected_width, expected_height, documents,
                          tolerance=0):
    """Render HTML documents to PNG and check that they render the same.

    Each document is passed as a (name, html_source) tuple.

    """
    pixels_list = []

    for name, html in documents:
        pixels = html_to_pixels(
            name, expected_width, expected_height, html)
        pixels_list.append((name, pixels))

    _name, reference = pixels_list[0]
    for name, pixels in pixels_list[1:]:
        assert_pixels_equal(
            name, expected_width, expected_height, pixels, reference,
            tolerance)


def assert_different_renderings(expected_width, expected_height, documents):
    """Render HTML documents to PNG and check that they don't render the same.

    Each document is passed as a (name, html_source) tuple.

    """
    pixels_list = []

    for name, html in documents:
        pixels = html_to_pixels(name, expected_width, expected_height, html)
        pixels_list.append((name, pixels))

    for i, (name_1, pixels_1) in enumerate(pixels_list):
        for name_2, pixels_2 in pixels_list[i + 1:]:
            if pixels_1 == pixels_2:  # pragma: no cover
                write_png(name_1, pixels_1, expected_width, expected_height)
                # Same as "assert pixels_1 != pixels_2" but the output of
                # the assert hook would be gigantic and useless.
                assert False, f'{name_1} and {name_2} are the same'


def write_png(basename, pixels, width, height):  # pragma: no cover
    """Take a pixel matrix and write a PNG file."""
    directory = os.path.join(os.path.dirname(__file__), 'results')
    if not os.path.isdir(directory):
        os.mkdir(directory)
    filename = os.path.join(directory, basename + '.png')
    image = Image.new('RGB', (width, height))
    image.putdata(pixels)
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
    return pixels


def document_to_pixels(document, name, expected_width, expected_height):
    """Render an HTML document to PNG, check its size and return pixel data."""
    return Image.open(io.BytesIO(document.write_png())).getdata()


def assert_pixels_equal(name, width, height, raw, expected_raw, tolerance=0):
    """Take 2 matrices of pixels and assert that they are the same."""
    if raw != expected_raw:  # pragma: no cover
        for i, (value, expected) in enumerate(zip(raw, expected_raw)):
            if expected is None:
                continue
            if any(abs(value - expected) > tolerance
                   for value, expected in zip(value, expected)):
                write_png(name, raw, width, height)
                expected_raw = [
                    pixel or (255, 255, 255) for pixel in expected_raw]
                write_png(name + '.expected', expected_raw, width, height)
                x = i % width
                y = i // width
                assert 0, (
                    f'Pixel ({x}, {y}) in {name}: '
                    f'expected rgba{expected}, got rgba{value}')
