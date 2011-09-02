"""
WeasyPrint
----------

WeasyPrint converts web documents (HTML, CSS, SVG, ...) to PDF.

See the documentation at http://weasyprint.org/

"""

from setuptools import setup

setup(
    name='WeasyPrint',
    version='0.1dev',
    url='http://weasyprint.org/',
    license='GNU Affero General Public License',
    description='WeasyPrint converts web documents to PDF.',
    long_description=__doc__,
    packages=['weasy'],
    zip_safe=False,
    install_requires=[
        'lxml',
        'cssutils',
        'PIL',
        # Tricky to compile: 'pycairo'
        # Not on PyPI: 'rsvg',
        # Also depends on Pango with introspection
    ],
    test_loader='attest:FancyReporter.test_loader',
    test_suite='weasy.tests.tests',
    entry_points={
        'console_scripts': [
            'weasyprint = weasy:main',
        ],
    }
)
