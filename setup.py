"""
WeasyPrint
----------

WeasyPrint converts web documents (HTML, CSS, SVG, ...) to PDF.

See the documentation at http://weasyprint.org/

"""

import re
import sys
from os import path
from setuptools import setup, find_packages

with open(path.join(path.dirname(__file__), 'weasyprint', '__init__.py')) as fd:
    VERSION = re.search("VERSION = '([^']+)'", fd.read().strip()).group(1)


REQUIRES = [
        # Keep this in sync with the "install" documentation
        'lxml',
        'pystacia',
        'cssutils>=0.9.9',
        'CairoSVG>=0.3',
        # Not installable by pip:
        #  Pango>=1.29.3
        #  PyGObject
        #  PyCairo
]
if sys.version_info < (2, 7) or (3,) <= sys.version_info < (3, 2):
    # In the stdlib from 2.7:
    REQUIRES.append('argparse')

setup(
    name='WeasyPrint',
    version=VERSION,
    url='http://weasyprint.org/',
    license='GNU Affero General Public License v3',
    description='WeasyPrint converts web documents to PDF.',
    long_description=__doc__,
    author='Simon Sapin',
    author_email='simon.sapin@kozea.fr',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Text Processing :: Markup :: HTML',
        'Topic :: Printing',
    ],
    packages=find_packages(),
    package_data={
        'weasyprint.tests': ['resources/*'],
        'weasyprint.css': ['*.css']},
    zip_safe=False,
    install_requires=REQUIRES,
    test_suite='weasy.tests',
    entry_points={
        'console_scripts': [
            'weasyprint = weasyprint.__main__:main',
        ],
    },
)
