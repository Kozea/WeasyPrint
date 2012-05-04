# coding: utf8
"""
    WeasyPrint
    ==========

    WeasyPrint converts web documents to PDF.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import re
import sys
from os import path
from setuptools import setup, find_packages

with open(path.join(path.dirname(__file__), 'weasyprint', '__init__.py')) as fd:
    VERSION = re.search("VERSION = '([^']+)'", fd.read().strip()).group(1)

with open(path.join(path.dirname(__file__), 'README')) as fd:
    LONG_DESCRIPTION = fd.read()


REQUIREMENTS = [
        # Keep this in sync with the "install" documentation
        'lxml',
        'pystacia',
        'tinycss>=0.2',
        'cssselect>=0.6',
        'CairoSVG>=0.4.1',
        # Not installable by pip:
        #  Pango>=1.29.3
        #  PyGObject
        #  PyCairo
]
if sys.version_info < (2, 7) or (3,) <= sys.version_info < (3, 2):
    # In the stdlib from 2.7:
    REQUIREMENTS.append('argparse')

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
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
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
    test_suite='weasyprint.tests',
    entry_points={
        'console_scripts': [
            'weasyprint = weasyprint.__main__:main',
        ],
    },
)
