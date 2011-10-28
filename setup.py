"""
WeasyPrint
----------

WeasyPrint converts web documents (HTML, CSS, SVG, ...) to PDF.

See the documentation at http://weasyprint.org/

"""

from setuptools import setup, find_packages

setup(
    name='WeasyPrint',
    version='0.1',  # Also change this in weasy/__init__.py
    url='http://weasyprint.org/',
    license='GNU Affero General Public License',
    description='WeasyPrint converts web documents to PDF.',
    long_description=__doc__,
    packages=find_packages(),
    package_data={
        'weasy.tests': ['resources/*',
                        # Make sure the directories are created
                        '*_results/.gitignore'],
        'weasy.css': ['*.css']},
    zip_safe=False,
    install_requires=[
        # Keep this in sync with the "install" documentation
        'lxml',
        'cssutils>=0.9.8a3',
        'PIL',
        # Not installable by pip:
        #  Pango>=1.29.3
        #  PyGObject
        #  PyCairo
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
