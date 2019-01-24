#!/usr/bin/env python

"""
    WeasyPrint
    ==========

    WeasyPrint converts web documents to PDF.

    :copyright: Copyright 2011-2018 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import sys

from setuptools import setup

if sys.version_info.major < 3:
    raise RuntimeError(
        'WeasyPrint does not support Python 2.x anymore. '
        'Please use Python 3 or install an older version of WeasyPrint.')

setup()
