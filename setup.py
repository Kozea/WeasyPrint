#!/usr/bin/env python

"""
    WeasyPrint
    ==========

    WeasyPrint converts web documents to PDF.

"""

import sys

from setuptools import setup

if sys.version_info.major < 3:
    raise RuntimeError(
        'WeasyPrint does not support Python 2.x anymore. '
        'Please use Python 3 or install an older version of WeasyPrint.')

setup()
