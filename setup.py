#!/usr/bin/env python

"""
    WeasyPrint
    ==========

    WeasyPrint converts web documents to PDF.

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import re
import sys
from os import path

from setuptools import find_packages, setup

if sys.version_info.major < 3:
    raise RuntimeError(
        'WeasyPrint does not support Python 2.x anymore. '
        'Please use Python 3 or install an older version of WeasyPrint.')

VERSION = re.search(b"VERSION = '([^']+)'", open(
    path.join(path.dirname(__file__), 'weasyprint', '__init__.py'), 'rb',
).read().strip()).group(1).decode('ascii')

LONG_DESCRIPTION = open(path.join(path.dirname(__file__), 'README.rst')).read()


REQUIREMENTS = [
    # XXX: Keep this in sync with docs/install.rst
    'cffi>=0.6',
    'html5lib>=0.999999999',
    'cairocffi>=0.9.0',
    'tinycss2>=0.5',
    'cssselect2>=0.1',
    'CairoSVG>=1.0.20',
    'Pyphen>=0.8',
    # C dependencies: Gdk-Pixbuf (optional), Pango, cairo.
]

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
        'Programming Language :: Python :: 3',
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
        'pytest-runner', 'pytest-cov', 'pytest-flake8', 'pytest-isort'],
    extras_require={
        'test': [
            'pytest-runner', 'pytest-cov', 'pytest-flake8', 'pytest-isort']},
    entry_points={
        'console_scripts': [
            'weasyprint = weasyprint.__main__:main',
        ],
    },
)
