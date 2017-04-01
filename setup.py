#!/usr/bin/env python
# coding: utf-8

"""
    WeasyPrint
    ==========

    WeasyPrint converts web documents to PDF.

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import codecs
import re
import sys
from os import path

from setuptools import find_packages, setup

VERSION = re.search("VERSION = '([^']+)'", codecs.open(
    path.join(path.dirname(__file__), 'weasyprint', '__init__.py'),
    encoding="utf-8",
).read().strip()).group(1)

LONG_DESCRIPTION = open(path.join(path.dirname(__file__), 'README.rst')).read()


REQUIREMENTS = [
    # XXX: Keep this in sync with docs/install.rst
    'lxml>=3.0',
    'html5lib>=0.999999999',
    'tinycss2>=0.5',
    'cssselect>=0.6',
    'cffi>=0.6',
    'cairocffi>=0.5',
    'Pyphen>=0.8'
    # C dependencies: Gdk-Pixbuf (optional), Pango, cairo.
]

if sys.version_info < (3,):
    REQUIREMENTS.append('CairoSVG >= 1.0.20, < 2.0.0')
else:
    REQUIREMENTS.append('CairoSVG >= 1.0.20')


needs_pytest = {'pytest', 'test', 'ptr'}.intersection(sys.argv)
pytest_runner = ['pytest-runner'] if needs_pytest else []

setup(
    name='WeasyPrint',
    version=VERSION,
    url='http://weasyprint.org/',
    license='BSD',
    description='WeasyPrint converts web documents to PDF.',
    long_description=LONG_DESCRIPTION,
    author='Simon Sapin',
    author_email='simon.sapin@kozea.fr',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Text Processing :: Markup :: HTML',
        'Topic :: Multimedia :: Graphics :: Graphics Conversion',
        'Topic :: Printing',
    ],
    packages=find_packages(),
    package_data={
        'weasyprint.tests': ['resources/*.*', 'resources/*/*'],
        'weasyprint.css': ['*.css']},
    zip_safe=False,
    install_requires=REQUIREMENTS,
    setup_requires=pytest_runner,
    test_suite='weasyprint.tests',
    tests_require=[
        "pytest-runner", "pytest-cov", "pytest-flake8", "pytest-isort"],
    extras_require={"test": [
        "pytest-runner", "pytest-cov", "pytest-flake8", "pytest-isort"]},
    entry_points={
        'console_scripts': [
            'weasyprint = weasyprint.__main__:main',
        ],
    },
)
