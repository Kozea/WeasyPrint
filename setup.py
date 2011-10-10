"""
WeasyPrint
----------

WeasyPrint converts web documents (HTML, CSS, SVG, ...) to PDF.

See the documentation at http://weasyprint.org/

"""

from setuptools import setup, find_packages

setup(
    name='WeasyPrint',
    version='0.1dev',
    url='http://weasyprint.org/',
    license='GNU Affero General Public License',
    description='WeasyPrint converts web documents to PDF.',
    long_description=__doc__,
    packages=find_packages(),
    package_data={
        'weasy.tests': ['resources/*',
                        # Make sure the directories are created
                        '*_results/.gitignore'],
        'weasy.html': ['*.css']},
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
    test_suite='weasy.tests',
    entry_points={
        'console_scripts': [
            'weasyprint = weasy:main',
        ],
    },
    use_2to3=True
)
