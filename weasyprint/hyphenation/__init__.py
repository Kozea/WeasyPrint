# coding: utf8
"""
    weasyprint.hyphenation
    ----------------------

    Hyphenation function.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import os

try:
    from hyphenator import Hyphenator
except ImportError:
    hyphenize = lambda word, style: ((word, ''),)
else:
    DICTIONARIES_FOLDER = os.environ.get(
        'WEASYPRINT_DICTIONARIES_FOLDER', os.path.dirname(__file__))
    HYPHENATORS = {}

    def hyphenize(word, style):
        """Return an iterator of possible (start, end) couples for word."""
        # TODO: get lang from style
        lang = 'en'
        if lang not in HYPHENATORS:
            HYPHENATORS[lang] = None
            if DICTIONARIES_FOLDER:
                for filename in os.listdir(DICTIONARIES_FOLDER):
                    if filename.startswith('hyph_' + lang):
                        HYPHENATORS[lang] = Hyphenator(os.path.join(
                            DICTIONARIES_FOLDER, filename))
                        break
        if HYPHENATORS[lang]:
            return HYPHENATORS[lang].iterate(word)
        else:
            return ((word, ''),)
