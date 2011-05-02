# coding: utf8

#  WeasyPrint converts web documents (HTML, CSS, ...) to PDF.
#  Copyright (C) 2011  Simon Sapin
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
from weasy.tests import all

if __name__ == '__main__':
    if '--cover' in sys.argv:
        sys.argv.remove('--cover') # Attest complains on unknown options
        from coverage import coverage
        cover = coverage()
        cover.start()
        all.main()
        cover.stop()
        cover.report([module for name, module in sys.modules.iteritems()
                             # Imported modules end up in sys.modules as None
                             # eg. sys.modules['weasy.css.cssutils'] == None
                             # Is it because of the Attest import hook?
                             if module and name.startswith('weasy')])
    else:
        all.main()
