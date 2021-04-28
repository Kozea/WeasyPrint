"""
    weasyprint.tests.conftest
    -------------------------

    Configuration for WeasyPrint tests.

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

MAGIC_NUMBER = b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a'


def document_write_png(self, target=None, resolution=96, antialiasing=1,
                       zoom=4/30):
    # Use temporary files because gs on Windows doesn’t accept binary on stdin
    with NamedTemporaryFile(delete=False) as pdf:
        pdf.write(self.write_pdf(zoom=zoom))
    command = [
        'gs', '-q', '-dNOPAUSE', f'-dTextAlphaBits={antialiasing}',
        f'-dGraphicsAlphaBits={antialiasing}', '-sDEVICE=png16m',
        f'-r{resolution / zoom}', '-sOutputFile=-', pdf.name]
    pngs = run(command, stdout=PIPE).stdout
    os.remove(pdf.name)

    assert pngs.startswith(MAGIC_NUMBER), (
        'Ghostscript error: '
        f'{pngs.split(MAGIC_NUMBER)[0].decode("ascii").strip()}')

    # TODO: use a different way to find PNG files in stream
    magic_numbers = pngs.count(MAGIC_NUMBER)
    if magic_numbers == 1:
        if target is None:
            return pngs
        png = io.BytesIO(pngs)
    else:
        images = []
        for i, png in enumerate(pngs[8:].split(MAGIC_NUMBER)):
            images.append(Image.open(io.BytesIO(MAGIC_NUMBER + png)))

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


def html_write_png(self, target=None, stylesheets=None, resolution=96,
                   presentational_hints=False, optimize_size=('fonts',),
                   font_config=None, counter_style=None, image_cache=None):
    return self.render(
        stylesheets, presentational_hints=presentational_hints,
        optimize_size=optimize_size, font_config=font_config,
        counter_style=counter_style, image_cache=image_cache).write_png(
            target, resolution)


@pytest.fixture(autouse=True)
def monkey_write_png(monkeypatch):
    Document.write_png = document_write_png
    HTML.write_png = html_write_png
