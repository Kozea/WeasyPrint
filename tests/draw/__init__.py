"""Test the final, drawn results and compare PNG images pixel per pixel."""

import io
import os
from itertools import zip_longest

from PIL import Image

from ..testing_utils import FakeHTML, resource_filename

# NOTE: "r" is not half red on purpose. In the pixel strings it has
# better contrast with "B" than does "R". eg. "rBBBrrBrB" vs "RBBBRRBRB".
PIXELS_BY_CHAR = dict(
    _=(255, 255, 255),  # white
    R=(255, 0, 0),  # red
    B=(0, 0, 255),  # blue
    G=(0, 255, 0),  # lime green
    V=(191, 0, 64),  # average of 1*B and 3*R.
    S=(255, 63, 63),  # R above R above _
    K=(0, 0, 0),  # black
    r=(255, 0, 0),  # red
    g=(0, 128, 0),  # half green
    b=(0, 0, 128),  # half blue
    v=(128, 0, 128),  # average of B and R.
    s=(255, 127, 127),  # R above _
    t=(127, 255, 127),  # G above _
    u=(128, 0, 127),  # r above B above _
    h=(64, 0, 64),  # half average of B and R.
    a=(0, 0, 254),  # R in lossy JPG
    p=(192, 0, 63),  # R above R above B above _
    z=None,
)


def parse_pixels(pixels):
    lines = (line.split('#')[0].strip() for line in pixels.splitlines())
    lines = tuple(line for line in lines if line)
    widths = {len(line) for line in lines}
    assert len(widths) == 1, 'All lines of pixels must have the same width'
    width = widths.pop()
    height = len(lines)
    pixels = tuple(PIXELS_BY_CHAR[char] for line in lines for char in line)
    return width, height, pixels


def assert_pixels(name, expected_pixels, html):
    """Helper testing the size of the image and the pixels values."""
    expected_width, expected_height, expected_pixels = parse_pixels(
        expected_pixels)
    width, height, pixels = html_to_pixels(html)
    assert (expected_width, expected_height) == (width, height), (
        'Images do not have the same sizes:\n'
        f'- expected: {expected_width} × {expected_height}\n'
        f'- result: {width} × {height}')
    assert_pixels_equal(name, width, height, pixels, expected_pixels)


def assert_same_renderings(name, *documents, tolerance=0):
    """Render HTML documents to PNG and check that they're the same."""
    pixels_list = []

    for html in documents:
        width, height, pixels = html_to_pixels(html)
        pixels_list.append(pixels)

    reference = pixels_list[0]
    for i, pixels in enumerate(pixels_list[1:], start=1):
        assert_pixels_equal(
            f'{name}_{i}', width, height, pixels, reference, tolerance)


def assert_different_renderings(name, *documents):
    """Render HTML documents to PNG and check that they’re different."""
    pixels_list = []

    for html in documents:
        width, height, pixels = html_to_pixels(html)
        pixels_list.append(pixels)

    for i, pixels_1 in enumerate(pixels_list, start=1):
        for j, pixels_2 in enumerate(pixels_list[i:], start=i+1):
            if pixels_1 == pixels_2:  # pragma: no cover
                name_1, name_2 = f'{name}_{i}', f'{name}_{j}'
                write_png(name_1, pixels_1, width, height)
                assert False, f'{name_1} and {name_2} are the same'


def assert_pixels_equal(name, width, height, raw, expected_raw, tolerance=0):
    """Take 2 matrices of pixels and assert that they are the same."""
    if raw != expected_raw:  # pragma: no cover
        pixels = zip_longest(raw, expected_raw, fillvalue=(-1, -1, -1))
        for i, (value, expected) in enumerate(pixels):
            if expected is None:
                continue
            if any(abs(value - expected) > tolerance
                   for value, expected in zip(value, expected)):
                actual_height = len(raw) // width
                write_png(name, raw, width, actual_height)
                expected_raw = [
                    pixel or (255, 255, 255) for pixel in expected_raw]
                write_png(f'{name}.expected', expected_raw, width, height)
                x = i % width
                y = i // width
                assert 0, (
                    f'Pixel ({x}, {y}) in {name}: '
                    f'expected rgba{expected}, got rgba{value}')


def write_png(basename, pixels, width, height):  # pragma: no cover
    """Take a pixel matrix and write a PNG file."""
    directory = os.path.join(os.path.dirname(__file__), 'results')
    if not os.path.isdir(directory):
        os.mkdir(directory)
    filename = os.path.join(directory, f'{basename}.png')
    image = Image.new('RGB', (width, height))
    image.putdata(pixels)
    image.save(filename)


def html_to_pixels(html):
    """Render an HTML document to PNG, checks its size and return pixel data.

    Also return the document to aid debugging.

    """
    document = FakeHTML(
        string=html,
        # Dummy filename, but in the right directory.
        base_url=resource_filename('<test>'))
    return document_to_pixels(document)


def document_to_pixels(document):
    """Render an HTML document to PNG, check its size and return pixel data."""
    image = Image.open(io.BytesIO(document.write_png()))
    return image.width, image.height, image.getdata()
