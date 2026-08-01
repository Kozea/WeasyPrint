"""Functions for CSS text transformations."""

# Rules defined in
# https://www.unicode.org/versions/latest/core-spec/chapter-3/#G33992
# https://www.unicode.org/Public/UCD/latest/ucd/SpecialCasing.txt
# https://w3c.github.io/i18n-tests/results/text-transform

# Common transformations should be handled by common algorithm in Python, special casing
# and tailoring should be done here when it depends on the language and not on only on
# the glyphs.

import re
import unicodedata

# https://stackoverflow.com/questions/16317534/
ASCII_TO_WIDE = {i: chr(i + 0xfee0) for i in range(0x21, 0x7f)}
ASCII_TO_WIDE.update({0x20: '\u3000', 0x2D: '\u2212'})

LINE_FEED_RE = re.compile('\r\n?')
TAB_RE = re.compile('[\t ]*\n[\t ]*')
SPACE_RE = re.compile('[\t ]+')


def transform(function, text, lang_code):
    return {
        'uppercase': uppercase,
        'lowercase': lowercase,
        'capitalize': capitalize,
        'full-width': full_width,
    }[function](text, lang_code)


def uppercase(text, lang_code):
    mapper = {}

    if lang_code == 'el':
        # https://w3c.github.io/i18n-tests/css-text/text-transform/
        #   text-transform-tailoring-003.html
        # https://en.wikiversity.org/wiki/Greek_Language/Diphthongs
        mapper = {
            'άι': 'ΑΪ',
            'άυ': 'ΑΫ',
            'όι': 'ΟΪ',
            'όυ': 'ΟΫ',
            'έυ': 'ΗΫ',
        }
    elif lang_code in ('tr', 'az'):
        # https://github.com/unicode-org/cldr/blob/main/common/transforms/tr-Upper.xml
        mapper = {
            'i': 'İ',
        }

    for key, value in mapper.items():
        text = text.replace(key, value)

    if lang_code == 'el':
        # Remove diacritics in Greek.
        # https://github.com/unicode-org/cldr/blob/main/common/transforms/el-Upper.xml
        # TODO: we should keep tonos on disjunctive eta.
        # https://w3c.github.io/i18n-tests/css-text/text-transform/
        #   text-transform-tailoring-005.html
        text = unicodedata.normalize('NFD', text)
        for char in '\u0313\u0314\u0301\u0300\u0306\u0342\u0304\u0345':
            text = text.replace(char, '')
        text = unicodedata.normalize('NFC', text)

    return text.upper()


def lowercase(text, lang_code):
    mapper = {}

    if lang_code in ('tr', 'az'):
        # https://github.com/unicode-org/cldr/blob/main/common/transforms/tr-Lower.xml
        mapper = {
            'I': 'ı',
            'İ': 'i',
        }
    elif lang_code == 'lt':
        # https://github.com/unicode-org/cldr/blob/main/common/transforms/lt-Lower.xml
        mapper = {
            'Ì': 'i̇̀',
            'Í': 'i̇́',
            'Ĩ': 'i̇̃',
        }

    for key, value in mapper.items():
        text = text.replace(key, value)

    return text.lower()


def capitalize(text, lang_code):
    letter_found = False
    skip_next_letter = False
    output = ''
    for i, letter in enumerate(text):
        if skip_next_letter:
            skip_next_letter = False
            continue
        category = unicodedata.category(letter)[0]
        if not letter_found and category in ('L', 'N'):
            letter_found = True
            if lang_code == 'nl' and text[i:i+2] == 'ij':
                skip_next_letter = True
                letter = 'IJ'
            elif lang_code in ('tr', 'az'):
                letter = uppercase(letter, lang_code)
            else:
                letter = letter.upper()
        elif category == 'Z':
            letter_found = False
        output += letter
    return output


def full_width(text, lang_code):
    return text.translate(ASCII_TO_WIDE)


def get_first_letter(text):
    character_found = False
    first_letter = ''
    for letter in text:
        category = unicodedata.category(letter)
        if category not in ('Ps', 'Pe', 'Pi', 'Pf', 'Po'):
            if character_found:
                break
            character_found = True
        first_letter += letter
    return first_letter
