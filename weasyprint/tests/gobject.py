# coding: utf8
"""
    weasyprint.tests.gobject
    ------------------------

    Check which method WeasyPrint is using to access GObject stuff:
    PyGObject introspection or PyGTK.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

import sys

from weasyprint.text import USING_INTROSPECTION


if __name__ == '__main__':
    if '-h' in sys.argv or '--help' in sys.argv:
        print('Usage:')
        print('    python -m weasyprint.tests.gobject assert_introspection')
        print('    python -m weasyprint.tests.gobject assert_pygtk')
        print('The exit code is accordingly.')
        print('')

    if USING_INTROSPECTION:
        print('Using PyGObject introspection.')
    else:
        print('Using PyGTK.')

    if 'assert_introspection' in sys.argv:
        sys.exit(0 if USING_INTROSPECTION else 1)
    elif 'assert_pygtk' in sys.argv:
        sys.exit(1 if USING_INTROSPECTION else 0)
