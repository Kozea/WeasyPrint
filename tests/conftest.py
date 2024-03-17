"""Configuration for WeasyPrint tests.

This module adds a PNG export based on Ghostscript.

Note that Ghostscript is released under AGPL.

"""

import io
import os
import shutil
from subprocess import PIPE, run
from tempfile import NamedTemporaryFile

import pytest
from PIL import Image

from weasyprint import HTML
from weasyprint.document import Document

from . import draw

MAGIC_NUMBER = b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a'


def document_write_png(document, target=None, resolution=96, antialiasing=1,
                       zoom=4/30, split_images=False):
    # Use temporary files because gs on Windows doesn’t accept binary on stdin
    with NamedTemporaryFile(delete=False) as pdf:
        document.write_pdf(pdf, zoom=zoom)
    command = (
        'gs', '-q', '-sDEVICE=png16m', f'-dTextAlphaBits={antialiasing}',
        f'-dGraphicsAlphaBits={antialiasing}', '-dBATCH', '-dNOPAUSE',
        '-dPDFSTOPONERROR', f'-r{resolution / zoom}', '-sOutputFile=-',
        pdf.name)
    pngs = run(command, stdout=PIPE).stdout
    os.remove(pdf.name)

    error = pngs.split(MAGIC_NUMBER)[0].decode().strip() or 'no output'
    assert pngs.startswith(MAGIC_NUMBER), f'Ghostscript error: {error}'

    if split_images:
        assert target is None

    # TODO: use a different way to find PNG files in stream
    magic_numbers = pngs.count(MAGIC_NUMBER)
    if magic_numbers == 1:
        if target is None:
            return [pngs] if split_images else pngs
        png = io.BytesIO(pngs)
    else:
        images = [MAGIC_NUMBER + png for png in pngs[8:].split(MAGIC_NUMBER)]
        if split_images:
            return images
        images = [Image.open(io.BytesIO(image)) for image in images]
        width = max(image.width for image in images)
        height = sum(image.height for image in images)
        output_image = Image.new('RGBA', (width, height))
        top = 0
        for image in images:
            output_image.paste(image, (int((width - image.width) / 2), top))
            top += image.height
        png = io.BytesIO()
        output_image.save(png, format='png')

    png.seek(0)

    if target is None:
        return png.read()

    if hasattr(target, 'write'):
        shutil.copyfileobj(png, target)
    else:
        with open(target, 'wb') as fd:
            shutil.copyfileobj(png, fd)


def html_write_png(document, target=None, font_config=None, counter_style=None,
                   resolution=96, **options):
    document = document.render(font_config, counter_style, **options)
    return document.write_png(target, resolution)


Document.write_png = document_write_png
HTML.write_png = html_write_png


def test_filename(filename):
    return ''.join(
        character if character.isalnum() else '_'
        for character in filename[5:50]).rstrip('_')


@pytest.fixture
def assert_pixels(request, *args, **kwargs):
    return lambda *args, **kwargs: draw.assert_pixels(
        test_filename(request.node.name), *args, **kwargs)


@pytest.fixture
def assert_same_renderings(request, *args, **kwargs):
    return lambda *args, **kwargs: draw.assert_same_renderings(
        test_filename(request.node.name), *args, **kwargs)


@pytest.fixture
def assert_different_renderings(request, *args, **kwargs):
    return lambda *args, **kwargs: draw.assert_different_renderings(
        test_filename(request.node.name), *args, **kwargs)


@pytest.fixture
def assert_pixels_equal(request, *args, **kwargs):
    return lambda *args, **kwargs: draw.assert_pixels_equal(
        test_filename(request.node.name), *args, **kwargs)
