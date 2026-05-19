#!/usr/bin/env python3
"""Generate subset fonts used by SVG text tests."""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlretrieve
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]
RESOURCES = Path(__file__).resolve().parent
SVG_TEXT_TESTS = ROOT / 'tests' / 'draw' / 'svg' / 'test_text.py'
WORKDIR = Path('/tmp/weasyprint-font-subsets')

HTML_ENTITY_PATTERN = re.compile(
    r'&(?!(?:[a-zA-Z][a-zA-Z0-9]+|#[0-9]+|#x[0-9a-fA-F]+);)')
STYLE_DECLARATION_PATTERN = re.compile(r'([-\w]+)\s*:\s*([^;]+)')


@dataclass(frozen=True)
class FontSubset:
    family: str
    source_url: str
    source_filename: str
    output_filename: str
    desubroutinize: bool = False


SUBSETS = (
    FontSubset(
        family='weasyprint-noto-hebrew',
        source_url=(
            'https://raw.githubusercontent.com/notofonts/noto-sans-hebrew/'
            'main/instance_ttf/NotoSansHebrew-Regular.ttf'),
        source_filename='NotoSansHebrew-Regular.ttf',
        output_filename='noto-hebrew-subset.woff'),
    FontSubset(
        family='weasyprint-amiri-arabic',
        source_url=(
            'https://raw.githubusercontent.com/aliftype/amiri/'
            '1.003/fonts/Amiri-Regular.ttf'),
        source_filename='Amiri-1.003-Regular.ttf',
        output_filename='amiri-arabic-subset.woff'),
    FontSubset(
        family='weasyprint-noto-devanagari',
        source_url=(
            'https://cdn.jsdelivr.net/gh/notofonts/notofonts.github.io/'
            'fonts/NotoSansDevanagari/unhinted/ttf/'
            'NotoSansDevanagari-Regular.ttf'),
        source_filename='NotoSansDevanagari-Regular.ttf',
        output_filename='noto-devanagari-subset.woff'),
    FontSubset(
        family='weasyprint-noto-cjk',
        source_url=(
            'https://raw.githubusercontent.com/notofonts/noto-cjk/'
            'main/Sans/OTF/Korean/NotoSansCJKkr-Regular.otf'),
        source_filename='NotoSansCJKkr-Regular.otf',
        output_filename='noto-cjk-subset.woff',
        desubroutinize=True),
)


def svg_test_documents():
    """Yield SVG test document strings from assert_same_renderings calls."""
    tree = ast.parse(SVG_TEXT_TESTS.read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            function = node.func
            if (
                    isinstance(function, ast.Name) and
                    function.id == 'assert_same_renderings'):
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        yield arg.value


def _families_from_value(value):
    """Yield font family names from a CSS/SVG font-family value."""
    for family in value.split(','):
        yield family.strip().strip('"\'')


def element_font_families(element):
    """Yield subset font families used by ``element``."""
    if family := element.attrib.get('font-family'):
        yield from _families_from_value(family)
    for name, value in STYLE_DECLARATION_PATTERN.findall(
            element.attrib.get('style', '')):
        if name == 'font-family':
            yield from _families_from_value(value)
        elif name == 'font':
            parts = value.strip().split(maxsplit=1)
            if len(parts) == 2:
                yield from _families_from_value(parts[1])


def used_characters_by_family():
    """Return visible SVG text characters grouped by subset font family."""
    characters = {subset.family: set() for subset in SUBSETS}
    for document in svg_test_documents():
        document = HTML_ENTITY_PATTERN.sub('&amp;', document)
        try:
            root = ElementTree.fromstring(f'<root>{document}</root>')
        except ElementTree.ParseError as exception:
            raise SystemExit(f'Cannot parse SVG test document: {exception}')
        for element in root.iter():
            for family in element_font_families(element):
                if family not in characters:
                    continue
                for text in element.itertext():
                    characters[family].update(
                        character for character in text
                        if not character.isspace())
    return characters


def download_sources():
    """Download source fonts into the work directory."""
    WORKDIR.mkdir(parents=True, exist_ok=True)
    for subset in SUBSETS:
        source = WORKDIR / subset.source_filename
        if not source.exists():
            print(f'Downloading {subset.source_filename}')  # noqa: T201
            urlretrieve(subset.source_url, source)


def subset_font(subset, characters):
    """Generate a WOFF subset for a font."""
    text_file = WORKDIR / f'{Path(subset.output_filename).stem}.txt'
    source = WORKDIR / subset.source_filename
    output = RESOURCES / subset.output_filename

    text = ''.join(sorted(characters))
    if not text:
        raise SystemExit(f'No characters found for {subset.family}')
    text_file.write_text(text, encoding='utf-8')

    command = [
        sys.executable, '-m', 'fontTools.subset', str(source),
        f'--text-file={text_file}',
        '--layout-features=*',
        '--no-hinting',
        '--flavor=woff',
        f'--output-file={output}',
    ]
    if subset.desubroutinize:
        command.insert(-2, '--desubroutinize')

    print(f'Generating {subset.output_filename}: {text}')  # noqa: T201
    subprocess.run(command, check=True)


def main():
    download_sources()
    characters = used_characters_by_family()
    for subset in SUBSETS:
        subset_font(subset, characters[subset.family])


if __name__ == '__main__':
    main()
