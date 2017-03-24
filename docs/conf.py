# -*- coding: utf-8 -*-
#
# WeasyPrint documentation build configuration file.

import codecs
import os
import re

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']
autodoc_member_order = 'bysource'

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'WeasyPrint'
copyright = u'2011-2017, Simon Sapin and contributors, see AUTHORs'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The full version, including alpha/beta/rc tags.
release = re.search("VERSION = '([^']+)'", codecs.open(
    os.path.join(
        os.path.dirname(__file__), os.pardir, 'weasyprint', '__init__.py'),
    encoding="utf-8",
).read().strip()).group(1)

# The short X.Y version.
version = '.'.join(release.split('.')[:2])

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['_themes']

html_context = {
    'extra_css_files': ['_static/custom.css']
}

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
html_logo = '_static/logo.png'

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
html_favicon = 'icon.ico'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Output file base name for HTML help builder.
htmlhelp_basename = 'WeasyPrintdoc'

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'weasyprint', u'WeasyPrint Documentation',
     [u'Simon Sapin and contributors, see AUTHORs'], 1)
]

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [(
    'index', 'WeasyPrint', u'WeasyPrint Documentation',
    u'Simon Sapin and contributors, see AUTHORs',
    'WeasyPrint', 'One line description of project.',
    'Miscellaneous'),
]

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    'python': ('http://docs.python.org/', None),
    'pycairo': ('http://www.cairographics.org/documentation/pycairo/2/', None),
    'cairocffi': ('http://pythonhosted.org/cairocffi/', None),
}
